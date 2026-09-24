#!/usr/bin/env bash
# ============================================================================
# harness sync — vendor the agent harness into a project, transactionally
# ============================================================================
# Copies the versioned harness files into <project>/.claude/ and records them
# in .claude/harness/lock so that updates are safe to repeat and safe to merge:
#
#   * All-or-nothing: the new state is built in a staging dir and validated,
#     then applied file-by-file with a journal. Any failure rolls every change
#     back, and the lock is written last as the commit point.
#   * Never clobbers local work: a harness file edited in the project (its hash
#     differs from the lock) or a pre-existing unmanaged file at a harness path
#     aborts the sync. --keep (edited files only) or --theirs (overwrite; a copy
#     is kept in .claude/harness/.backup/) resolve it.
#   * Never downgrades: a source older than the installed harness is refused
#     unless --allow-downgrade is passed.
#   * Ownership split: the harness only writes paths it owns. Project files
#     (CLAUDE.md, AGENTS.md, .claude/rules/project/, settings.project.json)
#     are never modified, except: a pre-existing settings.json is migrated into
#     settings.project.json once, and --profiles updates harness.config.
#     Seed files are written once, only if absent.
#   * settings.json is generated from harness base + .claude/settings.project.json.
#   * Deterministic lock (no timestamps, canonical source URL), so developers
#     who sync the same version produce byte-identical files.
#
# Usage: bash scaffold/sync.sh [options]
#   --target DIR       project root (default: current directory)
#   --profiles LIST    comma list of web,mobile,backend,infra,all. Saved to
#                      .claude/harness.config (default: from that file, else
#                      auto-detected on first install)
#   --dry-run          show the plan and exit without writing
#   --diff             like --dry-run, plus unified diffs for updates
#   --keep             keep locally modified harness files (marked kept-local)
#   --theirs           overwrite locally modified or unmanaged files; the old
#                      copies are saved under .claude/harness/.backup/<time>/
#   --no-seed          do not write seed files on first install
#   --commit           git add + commit the synced paths on the current branch
#   --uninstall        remove unmodified harness files and the lock
#   --allow-dirty      skip the "harness paths have uncommitted changes" guard
#   --allow-downgrade  allow syncing from a source older than the installed one
#   --force-unlock     clear a stale sync mutex left by a crashed run
#   -h, --help
# Exit codes: 0 ok, 1 refused (conflicts / dirty tree / downgrade; nothing
# written), 2 error (rolled back).
# ============================================================================
set -euo pipefail
# Native git.exe/python.exe need MSYS path conversion; never inherit an override.
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

SYNC_SRC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$SYNC_SRC_ROOT/harness"
# shellcheck source=../harness/bin/harness-lib.sh
source "$H/bin/harness-lib.sh"

# ---------------------------------------------------------------- arguments
target="."; profiles_arg=""; dry=0; diffmode=0; keep=0; theirs=0; seed=1
commit=0; uninstall=0; allow_dirty=0; allow_downgrade=0; force_unlock=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) target="${2:?--target needs a dir}"; shift 2 ;;
    --target=*) target="${1#*=}"; shift ;;
    --profiles) profiles_arg="${2:?--profiles needs a list}"; shift 2 ;;
    --profiles=*) profiles_arg="${1#*=}"; shift ;;
    --dry-run) dry=1; shift ;;
    --diff) diffmode=1; dry=1; shift ;;
    --keep) keep=1; shift ;;
    --theirs) theirs=1; shift ;;
    --no-seed) seed=0; shift ;;
    --seed) seed=1; shift ;;
    --commit) commit=1; shift ;;
    --uninstall) uninstall=1; shift ;;
    --allow-dirty) allow_dirty=1; shift ;;
    --allow-downgrade) allow_downgrade=1; shift ;;
    --force-unlock) force_unlock=1; shift ;;
    -h|--help) awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) hc_die "unknown option: $1 (see --help)" ;;
  esac
done
[[ $keep -eq 1 && $theirs -eq 1 ]] && hc_die "--keep and --theirs are mutually exclusive"

[[ -d "$target" ]] || hc_die "target is not a directory: $target"
T="$(cd "$target" && pwd)"
[[ "$T" == "$SYNC_SRC_ROOT" ]] && hc_die "refusing to sync the harness into its own source repo"
CL="$T/.claude"
HD="$CL/harness"
TMPD="$HD/.tmp"
LOCK="$HD/lock"
CFG="$CL/harness.config"
PROJ="$CL/settings.project.json"
VERSION="$(tr -d '[:space:]' < "$SYNC_SRC_ROOT/VERSION")"
MANIFEST="$H/manifest.tsv"
[[ -f "$MANIFEST" ]] || hc_die "harness/manifest.tsv missing — run scaffold/lib/release.sh in the harness repo"

# ---------------------------------------------------------------- preflight (no writes)
old_ver=""
[[ -f "$LOCK" ]] && old_ver="$(tr -d '\r' < "$LOCK" | awk -F'\t' '$1 == "harness_version" { print $2; exit }')"
first_install=0
[[ -f "$LOCK" ]] || first_install=1

if [[ $uninstall -eq 0 ]] && hc_ver_lt "$VERSION" "$old_ver"; then
  if [[ $allow_downgrade -eq 1 ]]; then
    hc_warn "downgrading harness v$old_ver → v$VERSION (--allow-downgrade)"
  else
    hc_fail "harness source $SYNC_SRC_ROOT is v$VERSION, older than the installed v$old_ver — nothing was written."
    hc_info "Update the source first (claude plugin marketplace update quantqbit && claude plugin update quantqbit-claude-rules@quantqbit, or git pull in your clone), or pass --allow-downgrade to roll back on purpose."
    exit 1
  fi
fi

sync_detect_profiles() {
  local p="" pkg="$T/package.json"
  if [[ -f "$pkg" ]] && grep -qE '"(react|react-dom|next|vue|nuxt|svelte|@sveltejs/kit|astro|@angular/core|solid-js|gatsby|remix|@remix-run/react)"' "$pkg"; then
    p="web"
  elif [[ -f "$T/index.html" || -f "$T/public/index.html" ]]; then
    p="web"
  fi
  if { [[ -f "$pkg" ]] && grep -qE '"(react-native|expo)"' "$pkg"; } || [[ -d "$T/android" || -d "$T/ios" ]] \
     || ls "$T"/*.xcodeproj >/dev/null 2>&1 \
     || grep -qs 'com.android' "$T/build.gradle" "$T/build.gradle.kts" "$T/app/build.gradle" "$T/app/build.gradle.kts"; then
    p="${p:+$p,}mobile"
  fi
  if { [[ -f "$pkg" ]] && grep -qE '"(express|fastify|@nestjs/core|koa|hono|@hapi/hapi|mongoose|pg|prisma|typeorm|sequelize)"' "$pkg"; } \
     || [[ -f "$T/requirements.txt" || -f "$T/pyproject.toml" || -f "$T/go.mod" || -f "$T/pom.xml" \
           || -f "$T/Gemfile" || -f "$T/composer.json" || -f "$T/Cargo.toml" ]]; then
    p="${p:+$p,}backend"
  fi
  if [[ -d "$T/ansible" || -d "$T/terraform" ]] || ls "$T"/docker-compose*.y*ml "$T"/compose*.y*ml "$T"/Dockerfile* >/dev/null 2>&1 \
     || ls "$T"/*.tf >/dev/null 2>&1; then
    p="${p:+$p,}infra"
  fi
  echo "${p:-all}"
}

cfg_profiles="$(hc_config_get "$CFG" profiles)"
if [[ -n "$profiles_arg" ]]; then
  PROFILES="$profiles_arg"
elif [[ -n "$cfg_profiles" ]]; then
  PROFILES="$cfg_profiles"
elif [[ -f "$LOCK" ]] && lock_profiles="$(tr -d '\r' < "$LOCK" | awk -F'\t' '$1 == "profiles" { print $2; exit }')" && [[ -n "$lock_profiles" ]]; then
  PROFILES="$lock_profiles"
else
  PROFILES="$(sync_detect_profiles)"
fi
PROFILES="${PROFILES// /}"
[[ "$PROFILES" =~ ^(all|web|mobile|backend|infra)(,(web|mobile|backend|infra))*$ ]] \
  || hc_die "invalid profiles '$PROFILES' (allowed: all, or a comma list of web,mobile,backend,infra)"
# --profiles is persisted to the project-owned harness.config (transactionally).
cfg_update=0
if [[ -n "$profiles_arg" && $uninstall -eq 0 && "$cfg_profiles" != "$PROFILES" ]]; then
  # Rewrite the profiles= line of an existing config; create a minimal config
  # when there is none (unless this first install seeds one anyway).
  if [[ -f "$CFG" || $first_install -eq 0 || $seed -eq 0 ]]; then cfg_update=1; fi
fi

in_git=0
if git -C "$T" rev-parse --is-inside-work-tree >/dev/null 2>&1; then in_git=1; fi

# Guard: refuse when any path this sync may write has uncommitted changes, so a
# rollback or --commit can never mix with unrelated work. Only harness-owned
# paths are checked (the project's own agents/skills are not).
if [[ $in_git -eq 1 && $allow_dirty -eq 0 ]]; then
  guard_paths=()
  while IFS= read -r p; do [[ -n "$p" ]] && guard_paths+=("$p"); done < <(
    { tr -d '\r' < "$MANIFEST" | awk -F'\t' '!/^#/ && NF >= 2 { print $2 }'
      [[ -f "$LOCK" ]] && tr -d '\r' < "$LOCK" | awk -F'\t' '$1 == "managed" || $1 == "generated" { print $2 }'
      echo ".claude/settings.json"; echo ".claude/harness/lock"
      [[ $cfg_update -eq 1 ]] && echo ".claude/harness.config"
    } | LC_ALL=C sort -u)
  dirty="$(git -C "$T" status --porcelain -- "${guard_paths[@]}" 2>/dev/null | grep -v '\.claude/harness/\.tmp' || true)"
  if [[ -n "$dirty" && $dry -eq 1 ]]; then
    hc_warn "harness-managed paths have uncommitted changes; the real run will refuse until they are committed or stashed:"
    printf '%s\n' "$dirty" >&2
  elif [[ -n "$dirty" ]]; then
    hc_fail "harness-managed paths have uncommitted changes (commit or stash them first, or pass --allow-dirty):"
    printf '%s\n' "$dirty" >&2
    exit 1
  fi
fi

created_hd=0; created_cl=0
[[ -d "$CL" ]] || created_cl=1
[[ -d "$HD" ]] || created_hd=1
mkdir -p "$TMPD"
MUTEX="$TMPD/sync.lock.d"
if ! mkdir "$MUTEX" 2>/dev/null; then
  if [[ $force_unlock -eq 1 ]]; then
    rm -rf "$MUTEX"; mkdir "$MUTEX"
  else
    hc_die "another harness sync appears to be running ($(cat "$MUTEX/owner" 2>/dev/null || echo unknown)). If it crashed, re-run with --force-unlock."
  fi
fi
printf 'pid=%s host=%s\n' "$$" "$(hostname 2>/dev/null || echo ?)" > "$MUTEX/owner"

W="$TMPD/work.$$"
STAGE="$W/stage"
BACKUP="$W/backup"
JOURNAL="$W/journal.tsv"
mkdir -p "$STAGE" "$BACKUP"
: > "$JOURNAL"
applying=0

sync_cleanup() {
  local rc=$?
  if [[ $applying -eq 1 ]]; then
    hc_fail "sync failed mid-apply — rolling back"
    if ! sync_rollback; then
      hc_fail "ROLLBACK INCOMPLETE — inspect $W (kept for recovery)"
      rm -rf "$MUTEX"
      exit 2
    fi
    rc=2
  fi
  rm -rf "$W" "$MUTEX"
  rmdir "$TMPD" 2>/dev/null || true
  if [[ $dry -eq 1 || $rc -ne 0 ]]; then
    [[ $created_hd -eq 1 ]] && rmdir "$HD" 2>/dev/null || true
    [[ $created_cl -eq 1 ]] && rmdir "$CL" 2>/dev/null || true
  fi
  exit "$rc"
}
trap sync_cleanup EXIT
trap 'exit 2' INT TERM

# sync_rollback — replay the journal in reverse order.
sync_rollback() {
  local act path ok=0
  while IFS=$'\t' read -r act path; do
    case "$act" in
      restore) mkdir -p "$(dirname "$T/$path")" && cp -p "$BACKUP/$path" "$T/$path" || ok=1 ;;
      delete)  rm -f "$T/$path" || ok=1 ;;
    esac
  done < <(awk '{ l[NR] = $0 } END { for (i = NR; i >= 1; i--) print l[i] }' "$JOURNAL")
  if [[ $ok -eq 0 ]]; then
    applying=0
    rm -rf "$W"
    hc_ok "rollback complete — project is unchanged"
  fi
  return $ok
}

# ---------------------------------------------------------------- old lock rows
LOCK_ROWS="$W/lock_rows.tsv"
: > "$LOCK_ROWS"
if [[ -f "$LOCK" ]]; then
  if grep -qE '^(<<<<<<<|=======|>>>>>>>)' "$LOCK"; then
    hc_warn "lock has git merge-conflict markers; rebuilding it from disk state"
  fi
  tr -d '\r' < "$LOCK" | awk -F'\t' '($1 == "managed" || $1 == "generated" || $1 == "seed") && NF >= 5' \
    | LC_ALL=C sort -t$'\t' -k2,2 -u > "$LOCK_ROWS"
fi

# ---------------------------------------------------------------- desired state
# desired.tsv: dest  kind  file_version  (staged file lives at $STAGE/dest)
DESIRED="$W/desired.tsv"
: > "$DESIRED"
SEEDS="$W/seeds.tsv"
: > "$SEEDS"
migrate_settings=0

if [[ $uninstall -eq 0 ]]; then
  # Batch staging: one list, one mkdir, one awk (per-file forks are slow on Windows).
  STAGE_LIST="$W/stage.tsv"; STAGE_DIRS="$W/stage-dirs.txt"
  : > "$STAGE_LIST"; : > "$STAGE_DIRS"
  while IFS=$'\t' read -r src dest ver _sha prof; do
    [[ -z "$src" || "$src" == \#* ]] && continue
    hc_profile_match "$prof" "$PROFILES" || continue
    [[ -f "$H/$src" ]] || hc_die "manifest lists missing file harness/$src — re-run release.sh"
    printf '%s\t%s\t%s\t%s\n' "$H/$src" "$STAGE/$dest" "$ver" "$src" >> "$STAGE_LIST"
    printf '%s\n' "$STAGE/${dest%/*}" >> "$STAGE_DIRS"
    printf '%s\tmanaged\t%s\n' "$dest" "$ver" >> "$DESIRED"
  done < <(tr -d '\r' < "$MANIFEST")
  LC_ALL=C sort -u "$STAGE_DIRS" | tr '\n' '\0' | xargs -0 mkdir -p
  hc_inject_headers "$STAGE_LIST"

  # Generated settings.json = base + project overrides.
  has_settings_row=0
  grep -q $'^generated\t.claude/settings.json\t' "$LOCK_ROWS" && has_settings_row=1
  mkdir -p "$STAGE/.claude"
  if [[ -f "$CL/settings.json" && $has_settings_row -eq 0 ]]; then
    # First install into a project that already has settings.json: preserve it
    # by folding it (and any existing settings.project.json) into the
    # project-owned settings.project.json. v0.x harness leftovers are dropped.
    migrate_settings=1
    hc_python >/dev/null || hc_die "python 3 is required to migrate .claude/settings.json (install Python 3; on Windows the 'py' launcher also works)"
    hc_py "$SYNC_SRC_ROOT/scaffold/lib/settings_merge.py" --migrate "$CL/settings.json" \
      "$( [[ -f "$PROJ" ]] && echo "$PROJ" || echo - )" "$STAGE/.claude/settings.project.json" \
      || hc_die "could not migrate .claude/settings.json: it must be strict JSON (no comments or trailing commas); fix it and re-run"
    printf '.claude/settings.project.json\tseed\n' >> "$SEEDS"
    proj_in="$STAGE/.claude/settings.project.json"
  elif [[ -f "$PROJ" ]]; then
    proj_in="$PROJ"
  else
    proj_in=""
  fi
  if [[ -n "$proj_in" ]]; then
    hc_python >/dev/null || hc_die "python 3 is required to merge .claude/settings.project.json (install Python 3; on Windows the 'py' launcher also works)"
    hc_py "$SYNC_SRC_ROOT/scaffold/lib/settings_merge.py" "$H/settings.base.json" "$proj_in" "$STAGE/.claude/settings.json" \
      || exit 2
  else
    tr -d '\r' < "$H/settings.base.json" > "$STAGE/.claude/settings.json"
  fi
  printf '.claude/settings.json\tgenerated\t%s\n' "$VERSION" >> "$DESIRED"

  # Seeds: project-owned starter files, written once, only if absent.
  if [[ $seed -eq 1 && $first_install -eq 1 ]]; then
    SEED_SRC="$SYNC_SRC_ROOT/scaffold/templates/seed"
    if [[ ! -e "$CFG" ]]; then
      sed "s/^profiles=.*/profiles=$PROFILES/" "$SEED_SRC/harness.config" > "$STAGE/.claude/harness.config"
      printf '.claude/harness.config\tseed\n' >> "$SEEDS"
    fi
    if [[ ! -e "$CL/rules/project/README.md" ]]; then
      mkdir -p "$STAGE/.claude/rules/project"
      cp "$SEED_SRC/rules-project-README.md" "$STAGE/.claude/rules/project/README.md"
      printf '.claude/rules/project/README.md\tseed\n' >> "$SEEDS"
    fi
    # Never create CLAUDE.md next to an AGENTS.md: Claude Code would then stop
    # reading AGENTS.md. Harness rules load from .claude/rules/ either way.
    if [[ ! -e "$T/CLAUDE.md" && ! -e "$T/AGENTS.md" && ! -e "$CL/CLAUDE.md" ]]; then
      sed "s/{{PROJECT_NAME}}/$(basename "$T" | sed 's/[&/\]/\\&/g')/g" "$SEED_SRC/CLAUDE.md" > "$STAGE/CLAUDE.md"
      printf 'CLAUDE.md\tseed\n' >> "$SEEDS"
    fi
  fi

  # --profiles: rewrite only the profiles= line of the project's harness.config.
  if [[ $cfg_update -eq 1 && ! -f "$CFG" ]]; then
    printf '# .claude/harness.config - project-owned (see .claude/harness/README.md)\nprofiles=%s\n' "$PROFILES" > "$STAGE/.claude/harness.config"
  elif [[ $cfg_update -eq 1 ]]; then
    if grep -qE '^[[:space:]]*profiles[[:space:]]*=' "$CFG"; then
      tr -d '\r' < "$CFG" | sed -E "s/^[[:space:]]*profiles[[:space:]]*=.*/profiles=$PROFILES/" > "$STAGE/.claude/harness.config"
    else
      { tr -d '\r' < "$CFG"; printf '\nprofiles=%s\n' "$PROFILES"; } > "$STAGE/.claude/harness.config"
    fi
  fi
fi
LC_ALL=C sort -t$'\t' -k1,1 -o "$DESIRED" "$DESIRED"

# ---------------------------------------------------------------- hashing
NEWH="$W/new.tsv"; CURH="$W/cur.tsv"
cut -f1 "$DESIRED" | hc_hash_list "$STAGE" > "$NEWH"
{ cut -f1 "$DESIRED"; cut -f2 "$LOCK_ROWS"; } | LC_ALL=C sort -u | hc_hash_list "$T" > "$CURH"

# ---------------------------------------------------------------- classify
# ops.tsv: op  dest  kind  lock_version  lock_hash  status
OPS="$W/ops.tsv"
awk -F'\t' -v OFS='\t' -v keep="$keep" -v theirs="$theirs" -v migrate="$migrate_settings" \
    -v uninstall="$uninstall" '
  FILENAME == ARGV[1] { dk[$1] = $2; dv[$1] = $3; all[$1] = 1; next }        # desired
  FILENAME == ARGV[2] { nh[$2] = $1; next }                                  # new hashes
  FILENAME == ARGV[3] { ch[$2] = $1; next }                                  # current hashes
  FILENAME == ARGV[4] { lk[$2] = $1; lv[$2] = $3; lh[$2] = $4; ls[$2] = $5; all[$2] = 1; next }
  END {
    for (p in all) {
      d = (p in dk); l = (p in lk) && lk[p] != "seed"; c = (p in ch) ? ch[p] : "-"
      if ((p in lk) && lk[p] == "seed") {           # project-owned since seeding
        if (!d) { print "SEED-KEEP", p, "seed", lv[p], lh[p], ls[p]; continue }
        l = 0
      }
      # A generated file whose content did not change keeps its file_version.
      v = dv[p]
      if (d && dk[p] == "generated" && (p in lh) && lh[p] == nh[p]) v = lv[p]
      if (uninstall) {
        if (!l) continue
        if (c == "-")            print "GONE", p, lk[p], lv[p], lh[p], ls[p]
        else if (c == lh[p])     print (p == ".claude/settings.json" ? "UNINSTALL-SETTINGS" : "REMOVE"), p, lk[p], lv[p], lh[p], ls[p]
        else                     print "LEAVE-MODIFIED", p, lk[p], lv[p], lh[p], ls[p]
        continue
      }
      if (d && l) {
        if (c == "-")            print "RESTORE", p, dk[p], v, nh[p], "clean"
        else if (c == nh[p])     print "NOOP", p, dk[p], v, nh[p], "clean"
        else if (c == lh[p])     print "UPDATE", p, dk[p], v, nh[p], "clean"
        else if (theirs)         print "OVERWRITE", p, dk[p], v, nh[p], "clean"
        else if (keep || ls[p] == "kept-local") print "KEEP", p, lk[p], lv[p], lh[p], "kept-local"
        else                     print "CONFLICT-MODIFIED", p, dk[p], v, nh[p], "-"
      } else if (d) {
        if (c == "-")            print "ADD", p, dk[p], v, nh[p], "clean"
        else if (c == nh[p])     print "ADOPT", p, dk[p], v, nh[p], "clean"
        else if (p == ".claude/settings.json" && migrate) print "MIGRATE-SETTINGS", p, dk[p], v, nh[p], "clean"
        else if (theirs)         print "OVERWRITE", p, dk[p], v, nh[p], "clean"
        else                     print "CONFLICT-UNMANAGED", p, dk[p], v, nh[p], "-"
      } else if (l) {
        if (c == "-")            print "GONE", p, lk[p], lv[p], lh[p], ls[p]
        else if (c == lh[p])     print "REMOVE", p, lk[p], lv[p], lh[p], ls[p]
        else                     print "ORPHAN-KEPT", p, lk[p], lv[p], lh[p], ls[p]
      }
    }
  }' "$DESIRED" "$NEWH" "$CURH" "$LOCK_ROWS" | LC_ALL=C sort -t$'\t' -k2,2 > "$OPS"

# Seeds become ops too (write-if-absent; lock row "seed … project").
while IFS=$'\t' read -r dest _k; do
  [[ -z "$dest" ]] && continue
  printf 'SEED\t%s\tseed\t%s\t-\tproject\n' "$dest" "$VERSION" >> "$OPS"
done < "$SEEDS"

count() { awk -F'\t' -v o="$1" '$1 == o' "$OPS" | wc -l | tr -d ' '; }

# ---------------------------------------------------------------- report
if [[ $uninstall -eq 1 ]]; then mode="uninstall"; else mode="sync ${old_ver:-<none>} → $VERSION"; fi
hc_info "harness $mode  |  target: $T  |  profiles: $PROFILES"
awk -F'\t' '$1 != "NOOP" && $1 != "SEED-KEEP" { printf "  %-18s %s\n", $1, $2 }' "$OPS" >&2
[[ $cfg_update -eq 1 ]] && printf '  %-18s %s\n' "CONFIG" ".claude/harness.config (profiles=$PROFILES, was ${cfg_profiles:-unset})" >&2
summary="$(awk -F'\t' '{ n[$1]++ } END { for (o in n) printf "%s=%d ", o, n[o] }' "$OPS")"
hc_info "plan: ${summary:-nothing to do}"

# v0.x leftovers: files the old /init-project-rules stamped, now superseded.
legacy=()
for f in .claude/hooks/session-start-context.sh .claude/hooks/post-edit-lint.sh \
         .claude/rules/bash.md .claude/rules/ansible.md .claude/rules/compose.md .claude/rules/terraform.md \
         .claude/.scaffold-manifest-rules.txt; do
  [[ -e "$T/$f" ]] && legacy+=("$f")
done
if [[ ${#legacy[@]} -gt 0 && $uninstall -eq 0 ]]; then
  hc_warn "v0.x leftovers found (superseded by .claude/rules/harness/ and .claude/harness/hooks/); review and delete them:"
  printf '    %s\n' "${legacy[@]}" >&2
fi

if [[ $uninstall -eq 0 && -d "$CL/agents" ]]; then
  while IFS= read -r af; do
    an="$(awk '/^name:/ { sub(/^name:[[:space:]]*/, ""); print; exit }' "$af")"
    case "$an" in explorer|implementor|infra-implementor|verifier|reviewer)
      [[ "${af##*/}" == "$an.md" ]] || hc_warn "${af#"$T"/} declares the reserved agent name '$an'; change its name: field too" ;;
    esac
  done < <(find "$CL/agents" -maxdepth 1 -name '*.md' -type f 2>/dev/null)
fi

conflicts=$(( $(count CONFLICT-MODIFIED) + $(count CONFLICT-UNMANAGED) ))
if [[ $conflicts -gt 0 ]]; then
  hc_fail "$conflicts conflict(s) — nothing was written."
  awk -F'\t' '$1 ~ /^CONFLICT/ { print "  " $1 ": " $2 }' "$OPS" >&2
  [[ $(count CONFLICT-MODIFIED) -gt 0 ]] && cat >&2 <<'EOF'
  CONFLICT-MODIFIED  : a harness file was edited in this project. Move the change into
                       .claude/rules/project/ (or settings.project.json), then re-run with
                       --theirs (take the harness version; your copy is saved under
                       .claude/harness/.backup/) or --keep (keep yours as kept-local;
                       harness-doctor keeps reporting it).
EOF
  [[ $(count CONFLICT-UNMANAGED) -gt 0 ]] && cat >&2 <<'EOF'
  CONFLICT-UNMANAGED : a file of yours sits at a path the harness owns. Reserved names:
                       agents explorer, implementor, infra-implementor, verifier, reviewer;
                       skills coding-standards, design-patterns, ui-ux, seo, harness.
                       Rename yours and change its name: field (recommended), commit the
                       rename, then re-run; or re-run with --theirs (yours is saved under
                       .claude/harness/.backup/). --keep does not apply.
EOF
  exit 1
fi

if [[ $dry -eq 1 ]]; then
  if [[ $diffmode -eq 1 ]]; then
    while IFS=$'\t' read -r op p _; do
      case "$op" in UPDATE|OVERWRITE|MIGRATE-SETTINGS)
        git --no-pager diff --no-index -- "$T/$p" "$STAGE/$p" || true ;;
      esac
    done < "$OPS"
  fi
  hc_ok "dry run — no changes written"
  exit 0
fi

# ---------------------------------------------------------------- apply
changed="$W/changed.txt"
: > "$changed"
n_applied=0
sync_apply_one() { # op path
  local op="$1" p="$2"
  if [[ -n "${HARNESS_FAIL_AFTER:-}" && $n_applied -ge ${HARNESS_FAIL_AFTER} ]]; then
    hc_fail "HARNESS_FAIL_AFTER=${HARNESS_FAIL_AFTER} (test fault injection)"
    return 1
  fi
  local d="${p%/*}"; [[ "$d" == "$p" ]] && d="."
  if [[ -e "$T/$p" ]]; then
    [[ -d "$BACKUP/$d" ]] || mkdir -p "$BACKUP/$d"
    cp -p "$T/$p" "$BACKUP/$p"
    printf 'restore\t%s\n' "$p" >> "$JOURNAL"
  else
    printf 'delete\t%s\n' "$p" >> "$JOURNAL"
  fi
  case "$op" in
    REMOVE)
      rm -f "$T/$p" ;;
    UNINSTALL-SETTINGS)
      if [[ -f "$PROJ" ]]; then cp "$PROJ" "$T/$p"; else rm -f "$T/$p"; fi ;;
    *)
      [[ -d "$T/$d" ]] || mkdir -p "$T/$d"
      mv -f "$STAGE/$p" "$T/$p" ;;
  esac
  printf '%s\n' "$p" >> "$changed"
  n_applied=$((n_applied + 1))
}

applying=1
while IFS=$'\t' read -r op p _; do
  case "$op" in
    ADD|RESTORE|UPDATE|OVERWRITE|MIGRATE-SETTINGS|SEED|REMOVE|UNINSTALL-SETTINGS)
      sync_apply_one "$op" "$p" ;;
  esac
done < "$OPS"
[[ $cfg_update -eq 1 ]] && sync_apply_one CONFIG .claude/harness.config

# Write the new lock (commit point). Deterministic: sorted, no timestamps,
# canonical source URL (never this machine's checkout remote).
if [[ $uninstall -eq 1 ]]; then
  if [[ -f "$LOCK" ]]; then
    mkdir -p "$(dirname "$BACKUP/.claude/harness/lock")"
    cp -p "$LOCK" "$BACKUP/.claude/harness/lock"
    printf 'restore\t%s\n' ".claude/harness/lock" >> "$JOURNAL"
    rm -f "$LOCK"
    printf '%s\n' ".claude/harness/lock" >> "$changed"
  fi
else
  {
    echo "# harness lock - generated by harness sync; do not edit by hand."
    echo "# Git merge conflict here? Keep either side, then re-run harness sync; it re-derives this file."
    printf 'harness_version\t%s\n' "$VERSION"
    printf 'source\t%s\n' "$HARNESS_UPSTREAM_URL"
    printf 'profiles\t%s\n' "$PROFILES"
    printf '#kind\tpath\tfile_version\tsha256\tstatus\n'
    awk -F'\t' -v OFS='\t' '
      $1 == "ORPHAN-KEPT" || $1 == "GONE" || $1 == "REMOVE" { next }
      { print $3, $2, $4, $5, $6 }' "$OPS" | LC_ALL=C sort -t$'\t' -k2,2
  } > "$TMPD/lock.new"
  if [[ -f "$LOCK" ]] && cmp -s <(tr -d '\r' < "$LOCK") "$TMPD/lock.new"; then
    rm -f "$TMPD/lock.new"
  else
    if [[ -f "$LOCK" ]]; then
      mkdir -p "$(dirname "$BACKUP/.claude/harness/lock")"
      cp -p "$LOCK" "$BACKUP/.claude/harness/lock"
      printf 'restore\t%s\n' ".claude/harness/lock" >> "$JOURNAL"
    else
      printf 'delete\t%s\n' ".claude/harness/lock" >> "$JOURNAL"
    fi
    mv -f "$TMPD/lock.new" "$LOCK"
    printf '%s\n' ".claude/harness/lock" >> "$changed"
  fi
fi
applying=0

# Keep overwritten files (--theirs) beyond the transaction: .claude/harness/.backup/
if [[ $(count OVERWRITE) -gt 0 ]]; then
  keep_dir="$HD/.backup/$(date -u +%Y%m%dT%H%M%SZ)"
  while IFS=$'\t' read -r op p _; do
    [[ "$op" == OVERWRITE && -f "$BACKUP/$p" ]] || continue
    mkdir -p "$(dirname "$keep_dir/$p")"
    cp -p "$BACKUP/$p" "$keep_dir/$p"
  done < "$OPS"
  hc_info "previous versions of overwritten files saved in ${keep_dir#"$T"/} (gitignored)"
fi

# Tidy directories emptied by removals (never above .claude/).
while IFS=$'\t' read -r op p _; do
  [[ "$op" == REMOVE || "$op" == UNINSTALL-SETTINGS ]] || continue
  d="$(dirname "$T/$p")"
  while [[ "$d" != "$T" && "$d" != "$CL" && "$d" == "$CL"/* ]]; do
    rmdir "$d" 2>/dev/null || break
    d="$(dirname "$d")"
  done
done < "$OPS"
if [[ $uninstall -eq 1 ]]; then
  rmdir "$TMPD" 2>/dev/null || true
  [[ -d "$HD/.backup" ]] && hc_info "kept .claude/harness/.backup/ (copies saved by earlier --theirs runs); delete it when no longer needed"
  rmdir "$HD" "$CL/rules/harness" 2>/dev/null || true
  left="$(awk -F'\t' '$1 == "SEED-KEEP" { printf "%s ", $2 }' "$OPS")"
  [[ -n "$left" ]] && hc_info "project-owned files left in place: $left(CLAUDE.md may still mention .claude/rules/harness/)"
fi

awk -F'\t' '$1 == "ORPHAN-KEPT" { print "  kept (modified, now project-owned): " $2 }' "$OPS" >&2
awk -F'\t' '$1 == "KEEP" { print "  kept-local (modified; harness-doctor will keep reporting): " $2 }' "$OPS" >&2
awk -F'\t' '$1 == "LEAVE-MODIFIED" { print "  left in place (modified): " $2 }' "$OPS" >&2
[[ $migrate_settings -eq 1 ]] && hc_info "existing .claude/settings.json folded into .claude/settings.project.json (project-owned); settings.json is now generated"
[[ $cfg_update -eq 1 ]] && hc_info "saved profiles=$PROFILES in .claude/harness.config"
n_changed=$(wc -l < "$changed" | tr -d ' ')
hc_ok "harness ${mode}: $n_changed file(s) changed"

# ---------------------------------------------------------------- commit
if [[ $commit -eq 1 ]]; then
  if [[ $in_git -eq 0 ]]; then
    hc_warn "--commit ignored: target is not a git repository"
  else
    paths=()
    while IFS= read -r p; do paths+=("$p"); done < "$changed"
    # Commit the regenerated settings.json together with its project-owned source.
    if [[ -f "$PROJ" && -n "$(git -C "$T" status --porcelain -- .claude/settings.project.json)" ]] \
       && ! grep -qxF '.claude/settings.project.json' "$changed"; then
      if grep -qxF '.claude/settings.json' "$changed"; then
        paths+=(".claude/settings.project.json")
      else
        hc_warn ".claude/settings.project.json has uncommitted edits that did not change settings.json; not committed"
      fi
    fi
    if [[ ${#paths[@]} -gt 0 ]]; then
      git -C "$T" add -- "${paths[@]}"
      if [[ $uninstall -eq 1 ]]; then msg="chore(harness): uninstall agent harness"; else msg="chore(harness): sync agent harness to v$VERSION"; fi
      git -C "$T" commit -q -m "$msg" -- "${paths[@]}"
      hc_ok "committed on $(git -C "$T" rev-parse --abbrev-ref HEAD): $(git -C "$T" log -1 --format='%h %s')"
    fi
  fi
fi
exit 0
