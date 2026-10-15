#!/usr/bin/env bash
# ============================================================================
# harness sync — vendor the agent harness into a project, transactionally
# ============================================================================
# Copies the versioned harness files into <project>/.claude/ and records them
# in .agents/harness/lock so that updates are safe to repeat and safe to merge:
#
#   * All-or-nothing: the new state is built in a staging dir and validated,
#     then applied file-by-file with a journal. Any failure rolls every change
#     back, and the lock is written last as the commit point.
#   * Never clobbers local work: a harness file edited in the project (its hash
#     differs from the lock) or a pre-existing unmanaged file at a harness path
#     aborts the sync. --keep (edited files only) or --theirs (overwrite; a copy
#     is kept in .agents/harness/.backup/) resolve it.
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
#                      .agents/harness.config (default: from that file, else
#                      auto-detected on first install)
#   --targets LIST     the agents to render the harness for, replacing the
#                      installed set (comma list; see scaffold/targets/). Saved
#                      to harness.config. Default: harness.config targets=, else
#                      the lock, else claude. Detection never applies on its own.
#   --add-target T     add one agent to the installed set
#   --remove-target T  remove one agent; its files go, shared files stay while
#                      any target is left (use --uninstall to remove everything)
#   --detect-targets   print the agents this project shows signs of, and exit
#   --dry-run          show the plan and exit without writing
#   --diff             like --dry-run, plus unified diffs for updates
#   --keep             keep locally modified harness files (marked kept-local)
#   --theirs           overwrite locally modified or unmanaged files; the old
#                      copies are saved under .agents/harness/.backup/<time>/
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
# shellcheck source=targets/lib.sh
source "$SYNC_SRC_ROOT/scaffold/targets/lib.sh"

# ---------------------------------------------------------------- arguments
target="."; profiles_arg=""; dry=0; diffmode=0; keep=0; theirs=0; seed=1
commit=0; uninstall=0; allow_dirty=0; allow_downgrade=0; force_unlock=0
targets_arg=""; add_targets=(); remove_targets=(); detect_targets=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) target="${2:?--target needs a dir}"; shift 2 ;;
    --target=*) target="${1#*=}"; shift ;;
    --profiles) profiles_arg="${2:?--profiles needs a list}"; shift 2 ;;
    --profiles=*) profiles_arg="${1#*=}"; shift ;;
    --targets) targets_arg="${2:?--targets needs a list}"; shift 2 ;;
    --targets=*) targets_arg="${1#*=}"; shift ;;
    --add-target) add_targets+=("${2:?--add-target needs a target}"); shift 2 ;;
    --add-target=*) add_targets+=("${1#*=}"); shift ;;
    --remove-target) remove_targets+=("${2:?--remove-target needs a target}"); shift 2 ;;
    --remove-target=*) remove_targets+=("${1#*=}"); shift ;;
    --detect-targets) detect_targets=1; shift ;;
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
AG="$T/.agents"
HD="$AG/harness"          # the runtime every target shares (hooks, snippets, lib, lock)
TMPD="$HD/.tmp"
LOCK="$HD/lock"
CFG="$AG/harness.config"
# 1.x kept the runtime, lock and config under .claude/. A sync reads them from
# there once and moves them (the old lock rows become REMOVE ops, the config is
# carried over, the old lock is deleted at the commit point).
OLD_LOCK="$CL/harness/lock"
OLD_CFG="$CL/harness.config"
LOCK_IN="$LOCK"; migrate_layout=0
if [[ ! -f "$LOCK" && -f "$OLD_LOCK" ]]; then LOCK_IN="$OLD_LOCK"; migrate_layout=1; fi
CFG_IN="$CFG"; cfg_move=0
if [[ ! -f "$CFG" && -f "$OLD_CFG" ]]; then CFG_IN="$OLD_CFG"; cfg_move=1; fi
PROJ="$CL/settings.project.json"
VERSION="$(tr -d '[:space:]' < "$SYNC_SRC_ROOT/VERSION")"
MANIFEST="$H/manifest.tsv"
[[ -f "$MANIFEST" ]] || hc_die "harness/manifest.tsv missing — run scaffold/lib/release.sh in the harness repo"

# ---------------------------------------------------------------- preflight (no writes)
source "$SYNC_SRC_ROOT/scaffold/lib/safe-path.sh"
for p in .agents/harness/.tmp .agents/harness/.backup .agents/harness/lock .agents/harness.config .claude/harness/lock .claude/harness.config .claude/settings.project.json .claude/settings.json .claude/rules/project/README.md CLAUDE.md; do
  safe_relative_path "$T" "$p" || hc_die "unsafe or symlinked target path: $p"
done
while IFS=$'\t' read -r src dest _; do
  [[ -z "$src" || "$src" == \#* ]] && continue
  safe_relative_path "$H" "$src" || hc_die "unsafe manifest source: $src"
  [[ "$dest" =~ ^[a-z]+:[^/] ]] || hc_die "manifest destination is not logical (<kind>:<path>): $dest - re-run release.sh"
done < <(tr -d '\r' < "$MANIFEST")
# Every project path any target may write starts with one of these roots; lock
# paths of targets removed since are checked against the same set.
ROOTS=" $(tg_roots | tr '\n' ' ')CLAUDE.md "
sync_root_ok() { local top="${1%%/*}"; [[ "$ROOTS" == *" $top "* ]]; }
if [[ -f "$LOCK_IN" ]]; then
  while IFS=$'\t' read -r kind p _; do
    case "$kind" in managed|generated|seed)
      sync_root_ok "$p" && safe_relative_path "$T" "$p" \
        || hc_die "unsafe lock path: $p" ;;
    esac
  done < <(tr -d '\r' < "$LOCK_IN")
fi
old_ver=""
# awk reads the lock itself: `tr … | awk '… exit'` can die of SIGPIPE under
# pipefail once the lock is larger than the pipe buffer (16 KB on macOS).
[[ -f "$LOCK_IN" ]] && old_ver="$(awk -F'\t' '{ sub(/\r$/, "") } $1 == "harness_version" { print $2; exit }' "$LOCK_IN")"
first_install=0
[[ -f "$LOCK_IN" ]] || first_install=1

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

cfg_profiles="$(hc_config_get "$CFG_IN" profiles)"
if [[ -n "$profiles_arg" ]]; then
  PROFILES="$profiles_arg"
elif [[ -n "$cfg_profiles" ]]; then
  PROFILES="$cfg_profiles"
elif [[ -f "$LOCK_IN" ]] && lock_profiles="$(awk -F'\t' '{ sub(/\r$/, "") } $1 == "profiles" { print $2; exit }' "$LOCK_IN")" && [[ -n "$lock_profiles" ]]; then
  PROFILES="$lock_profiles"
else
  PROFILES="$(sync_detect_profiles)"
fi
PROFILES="${PROFILES// /}"
[[ "$PROFILES" =~ ^(all|web|mobile|backend|infra)(,(web|mobile|backend|infra))*$ ]] \
  || hc_die "invalid profiles '$PROFILES' (allowed: all, or a comma list of web,mobile,backend,infra)"
if [[ $detect_targets -eq 1 ]]; then
  found="$(tg_detect "$T")"
  hc_info "this project shows signs of: $found"
  hc_info "nothing was changed; to render the harness for them, run harness sync --targets $found"
  exit 0
fi

# Targets: explicit flag > harness.config > lock > claude. Detection is never applied.
cfg_targets="$(hc_config_get "$CFG_IN" targets)"
lock_targets=""
[[ -f "$LOCK_IN" ]] && lock_targets="$(awk -F'\t' '{ sub(/\r$/, "") } $1 == "targets" { print $2; exit }' "$LOCK_IN")"
if [[ -n "$targets_arg" ]]; then TARGETS="$targets_arg"
elif [[ -n "$cfg_targets" ]]; then TARGETS="$cfg_targets"
elif [[ -n "$lock_targets" ]]; then TARGETS="$lock_targets"
else TARGETS="claude"
fi
TARGETS="$(tg_normalize "$TARGETS")" || exit 2
for t in ${add_targets[@]+"${add_targets[@]}"}; do TARGETS="$(tg_add "$TARGETS" "$t")" || exit 2; done
for t in ${remove_targets[@]+"${remove_targets[@]}"}; do
  tg_normalize "$t" >/dev/null || exit 2
  TARGETS="$(tg_remove "$TARGETS" "$t")"
done
[[ -n "$TARGETS" ]] || hc_die "no target would be left; to remove the harness completely use --uninstall"
targets_flag=0
[[ -n "$targets_arg" || ${#add_targets[@]} -gt 0 || ${#remove_targets[@]} -gt 0 ]] && targets_flag=1
has_target() { [[ ",$TARGETS," == *",$1,"* ]]; }

# --profiles / --targets are persisted to the project-owned harness.config (transactionally).
cfg_update=0
if [[ $uninstall -eq 0 ]] && { { [[ -n "$profiles_arg" && "$cfg_profiles" != "$PROFILES" ]]; } \
     || { [[ $targets_flag -eq 1 && "$cfg_targets" != "$TARGETS" ]]; }; }; then
  # Rewrite the profiles= / targets= lines of an existing config; create a minimal
  # config when there is none (unless this first install seeds one anyway).
  if [[ -f "$CFG_IN" || $first_install -eq 0 || $seed -eq 0 ]]; then cfg_update=1; fi
fi

# The desired file set: src  dest  file_version  renderer  targets
PLAN_ROWS="$(tg_plan "$MANIFEST" "$TARGETS" "$PROFILES")" || hc_die "could not map the manifest to targets $TARGETS"
while IFS=$'\t' read -r _s dest _; do
  [[ -z "$dest" ]] && continue
  sync_root_ok "$dest" && safe_relative_path "$T" "$dest" || hc_die "unsafe destination: $dest"
done <<< "$PLAN_ROWS"

in_git=0
if git -C "$T" rev-parse --is-inside-work-tree >/dev/null 2>&1; then in_git=1; fi

# Guard: refuse when any path this sync may write has uncommitted changes, so a
# rollback or --commit can never mix with unrelated work. Only harness-owned
# paths are checked (the project's own agents/skills are not).
if [[ $in_git -eq 1 && $allow_dirty -eq 0 ]]; then
  guard_paths=()
  while IFS= read -r p; do [[ -n "$p" ]] && guard_paths+=("$p"); done < <(
    { printf '%s\n' "$PLAN_ROWS" | cut -f2
      [[ -f "$LOCK_IN" ]] && tr -d '\r' < "$LOCK_IN" | awk -F'\t' '$1 == "managed" || $1 == "generated" { print $2 }'
      has_target claude && echo ".claude/settings.json"
      tg_configs "$TARGETS" | cut -f2
      echo ".agents/harness/lock"
      [[ $cfg_update -eq 1 ]] && echo ".agents/harness.config"
      [[ $migrate_layout -eq 1 ]] && echo ".claude/harness/lock"
      [[ $cfg_move -eq 1 ]] && echo ".claude/harness.config"
    } | LC_ALL=C sort -u)
  dirty="$(git -C "$T" status --porcelain -- "${guard_paths[@]}" 2>/dev/null | grep -v '\.agents/harness/\.tmp' || true)"
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
created_ag=0
[[ -d "$CL" ]] || created_cl=1
[[ -d "$AG" ]] || created_ag=1
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
  # The work dir lived inside the runtime dir, so an uninstall can only drop it now.
  [[ $uninstall -eq 1 && $rc -eq 0 && $dry -eq 0 ]] && { rmdir "$HD" 2>/dev/null || true; }
  if [[ $dry -eq 1 || $rc -ne 0 ]]; then
    [[ $created_hd -eq 1 ]] && rmdir "$HD" 2>/dev/null || true
    [[ $created_cl -eq 1 ]] && rmdir "$CL" 2>/dev/null || true
    [[ $created_ag -eq 1 ]] && rmdir "$AG" 2>/dev/null || true
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
if [[ -f "$LOCK_IN" ]]; then
  if grep -qE '^(<<<<<<<|=======|>>>>>>>)' "$LOCK_IN"; then
    hc_warn "lock has git merge-conflict markers; rebuilding it from disk state"
  fi
  tr -d '\r' < "$LOCK_IN" | awk -F'\t' '($1 == "managed" || $1 == "generated" || $1 == "seed") && NF >= 5' \
    | LC_ALL=C sort -t$'\t' -k2,2 -u > "$LOCK_ROWS"
fi

# ---------------------------------------------------------------- desired state
# desired.tsv: dest  kind  file_version  (staged file lives at $STAGE/dest)
DESIRED="$W/desired.tsv"
: > "$DESIRED"
SEEDS="$W/seeds.tsv"
BLOCKS="$W/blocks.tsv"   # path  sha of the block found  sha of the block written
: > "$BLOCKS"
: > "$SEEDS"
migrate_settings=0

if [[ $uninstall -eq 0 ]]; then
  # Batch staging: one list, one mkdir, one awk (per-file forks are slow on Windows).
  STAGE_LIST="$W/stage.tsv"; STAGE_DIRS="$W/stage-dirs.txt"
  : > "$STAGE_LIST"; : > "$STAGE_DIRS"
  RENDER_LIST="$W/render.tsv"; CORE_LIST="$W/claude-core.txt"
  : > "$RENDER_LIST"; : > "$CORE_LIST"
  while IFS=$'\t' read -r src dest ver renderer tgts logical; do
    [[ -z "$src" ]] && continue
    [[ -f "$H/$src" ]] || hc_die "manifest lists missing file harness/$src — re-run release.sh"
    printf '%s\t%s\t%s\t%s\n' "$H/$src" "$STAGE/$dest" "$ver" "$src" >> "$STAGE_LIST"
    printf '%s\n' "$STAGE/${dest%/*}" >> "$STAGE_DIRS"
    printf '%s\tmanaged\t%s\t%s\tfile\n' "$dest" "$ver" "$tgts" >> "$DESIRED"
    case "$renderer" in
      -) ;;
      claude-core) printf '%s\n' "$STAGE/$dest" >> "$CORE_LIST" ;;
      # Relative to the stage: native Windows Python can't open MSYS /c/… paths.
      *) printf '%s\t%s\t%s\t%s\n' "$renderer" "$tgts" "$dest" "$logical" >> "$RENDER_LIST" ;;
    esac
  done <<< "$PLAN_ROWS"
  LC_ALL=C sort -u "$STAGE_DIRS" | tr '\n' '\0' | xargs -0 mkdir -p
  hc_inject_headers "$STAGE_LIST"
  # Target renderers (scaffold/targets/render.py). claude-core only keeps the
  # <!-- agent:claude --> blocks of the core rules; it runs here, so a Claude-only
  # install needs no Python.
  while IFS= read -r f; do
    awk '/^<!-- agent:[a-z]+ -->$/ { a = $0; sub(/^<!-- agent:/, "", a); sub(/ -->$/, "", a); blk = a; next }
         /^<!-- \/agent -->$/ { blk = ""; next }
         blk == "" || blk == "claude"' "$f" > "$f.r" && mv -f "$f.r" "$f"
  done < "$CORE_LIST"
  if [[ -s "$RENDER_LIST" ]]; then
    hc_python >/dev/null || hc_die "python 3 is required to render the harness for $TARGETS (install Python 3; on Windows the 'py' launcher also works)"
    (cd "$STAGE" && hc_py "$SYNC_SRC_ROOT/scaffold/targets/render.py" "$RENDER_LIST") || exit 2
  fi

  # Generated settings.json = base + project overrides (Claude Code only).
  if has_target claude; then
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
    printf '.claude/settings.project.json\tseed\tclaude\n' >> "$SEEDS"
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
  printf '.claude/settings.json\tgenerated\t%s\tclaude\tfile\n' "$VERSION" >> "$DESIRED"
  fi

  # Files the project owns that the harness writes into: other agents' hook
  # configs (owner "entries": only the harness entries are its own) and
  # instruction files (owner "block": only the marked block of AGENTS.md /
  # GEMINI.md). Everything else in them is kept as it is.
  while IFS=$'\t' read -r tgt cpath flavor ctype; do
    [[ -z "$cpath" ]] && continue
    grep -q "^$cpath"$'\t' "$DESIRED" && continue   # two targets, one file (AGENTS.md)
    hc_python >/dev/null || hc_die "python 3 is required to write the harness into $cpath"
    mkdir -p "$(dirname "$STAGE/$cpath")"
    cur="-"; [[ -f "$T/$cpath" ]] && cur="$T/$cpath"
    if [[ "$ctype" == block ]]; then
      shas="$(cd "$STAGE" && hc_py "$SYNC_SRC_ROOT/scaffold/targets/blocks.py" "$flavor" "$cur" "$cpath" .agents/harness/rules "$VERSION")" || exit 2
      printf '%s\t%s\t%s\n' "$cpath" "${shas% *}" "${shas#* }" >> "$BLOCKS"
      printf '%s\tgenerated\t%s\t%s\tblock\n' "$cpath" "$VERSION" "$(tg_configs "$TARGETS" | awk -F'\t' -v p="$cpath" '$2 == p { t = t (t == "" ? "" : ",") $1 } END { print t }')" >> "$DESIRED"
    else
      hc_py "$SYNC_SRC_ROOT/scaffold/targets/hooks_merge.py" "$flavor" "$cur" "$STAGE/$cpath" || exit 2
      printf '%s\tgenerated\t%s\t%s\tentries\n' "$cpath" "$VERSION" "$tgt" >> "$DESIRED"
    fi
  done < <(tg_configs "$TARGETS")

  # Seeds: project-owned starter files, written once, only if absent.
  if [[ $seed -eq 1 && $first_install -eq 1 ]]; then
    SEED_SRC="$SYNC_SRC_ROOT/scaffold/templates/seed"
    if [[ ! -e "$CFG_IN" ]]; then
      sed -e "s/^profiles=.*/profiles=$PROFILES/" -e "s/^targets=.*/targets=$TARGETS/" "$SEED_SRC/harness.config" > "$STAGE/.agents/harness.config"
      printf '.agents/harness.config\tseed\t%s\n' "$TARGETS" >> "$SEEDS"
    fi
    if has_target claude && [[ ! -e "$CL/rules/project/README.md" ]]; then
      mkdir -p "$STAGE/.claude/rules/project"
      cp "$SEED_SRC/rules-project-README.md" "$STAGE/.claude/rules/project/README.md"
      printf '.claude/rules/project/README.md\tseed\tclaude\n' >> "$SEEDS"
    fi
    # Never create CLAUDE.md next to an AGENTS.md: Claude Code would then stop
    # reading AGENTS.md. Harness rules load from .claude/rules/ either way.
    if has_target claude && [[ ! -e "$T/CLAUDE.md" && ! -e "$T/AGENTS.md" && ! -e "$CL/CLAUDE.md" ]]; then
      sed "s/{{PROJECT_NAME}}/$(basename "$T" | sed 's/[&/\]/\\&/g')/g" "$SEED_SRC/CLAUDE.md" > "$STAGE/CLAUDE.md"
      printf 'CLAUDE.md\tseed\tclaude\n' >> "$SEEDS"
    fi
  fi

  # A 1.x config moves to .agents/ (written like a seed; the old file is deleted).
  if [[ $cfg_move -eq 1 ]]; then
    mkdir -p "$STAGE/.agents"
    tr -d '\r' < "$OLD_CFG" > "$STAGE/.agents/harness.config"
    printf '.agents/harness.config\tseed\t%s\n' "$TARGETS" >> "$SEEDS"
  fi
  # --profiles / --targets: rewrite only those lines of the project's harness.config.
  if [[ $cfg_update -eq 1 && ! -f "$CFG_IN" ]]; then
    printf '# .agents/harness.config - project-owned (see .agents/harness/README.md)\nprofiles=%s\n' "$PROFILES" > "$STAGE/.agents/harness.config"
    [[ $targets_flag -eq 1 ]] && printf 'targets=%s\n' "$TARGETS" >> "$STAGE/.agents/harness.config"
  elif [[ $cfg_update -eq 1 ]]; then
    [[ $cfg_move -eq 1 ]] || tr -d '\r' < "$CFG_IN" > "$STAGE/.agents/harness.config"
    for kv in "profiles=$PROFILES" "targets=$TARGETS"; do
      k="${kv%%=*}"
      [[ "$k" == targets && $targets_flag -eq 0 ]] && continue
      if grep -qE "^[[:space:]]*$k[[:space:]]*=" "$STAGE/.agents/harness.config"; then
        sed -E "s/^[[:space:]]*$k[[:space:]]*=.*/$kv/" "$STAGE/.agents/harness.config" > "$W/cfg.tmp"
      else
        { cat "$STAGE/.agents/harness.config"; printf '\n%s\n' "$kv"; } > "$W/cfg.tmp"
      fi
      mv -f "$W/cfg.tmp" "$STAGE/.agents/harness.config"
    done
  fi
fi
LC_ALL=C sort -t$'\t' -k1,1 -o "$DESIRED" "$DESIRED"

# Project files the harness wrote into before but no longer should (a removed
# target, or --uninstall): stage the file with only the harness part removed.
UNMERGE="$W/unmerge.tsv"; : > "$UNMERGE"
while IFS=$'\t' read -r _k cpath _v _h _s _t owner; do
  [[ ( "$owner" == entries || "$owner" == block ) && -f "$T/$cpath" ]] || continue
  grep -q "^$cpath"$'\t' "$DESIRED" && continue
  row="$(tg_configs "$(tg_known | tr '\n' ',')" | awk -F'\t' -v p="$cpath" '$2 == p && f == "" { f = $3 "\t" $4 } END { print f }')"  # no early exit: SIGPIPE under pipefail
  flavor="${row%%$'\t'*}"; ctype="${row#*$'\t'}"
  [[ -n "$flavor" ]] || hc_die "no target knows how to take the harness out of $cpath"
  hc_python >/dev/null || hc_die "python 3 is required to take the harness out of $cpath"
  mkdir -p "$(dirname "$STAGE/$cpath")"
  if [[ "$ctype" == block ]]; then
    shas="$(cd "$STAGE" && hc_py "$SYNC_SRC_ROOT/scaffold/targets/blocks.py" "$flavor" "$T/$cpath" "$cpath" .agents/harness/rules "$VERSION" --remove)" || exit 2
    printf '%s\t%s\t-\n' "$cpath" "${shas% *}" >> "$BLOCKS"
  else
    hc_py "$SYNC_SRC_ROOT/scaffold/targets/hooks_merge.py" "$flavor" "$T/$cpath" "$STAGE/$cpath" --remove || exit 2
  fi
  empty=0; [[ -s "$STAGE/$cpath" ]] || empty=1
  printf '%s\t%s\n' "$cpath" "$empty" >> "$UNMERGE"
done < "$LOCK_ROWS"

# ---------------------------------------------------------------- hashing
NEWH="$W/new.tsv"; CURH="$W/cur.tsv"
cut -f1 "$DESIRED" | hc_hash_list "$STAGE" > "$NEWH"
{ cut -f1 "$DESIRED"; cut -f2 "$LOCK_ROWS"; } | LC_ALL=C sort -u | hc_hash_list "$T" > "$CURH"

# ---------------------------------------------------------------- classify
# ops.tsv: op  dest  kind  lock_version  lock_hash  status
OPS="$W/ops.tsv"
awk -F'\t' -v OFS='\t' -v keep="$keep" -v theirs="$theirs" -v migrate="$migrate_settings" \
    -v uninstall="$uninstall" '
  # Every op row: op  path  kind  version  hash  status  targets  owner
  function out(op, p, k, v, h, s, t, o) { print op, p, k, v, h, s, t, o }
  function des(op, p, v, s) { out(op, p, dk[p], v, nh[p], s, dt[p], dow[p]) }
  function old(op, p, s) { out(op, p, lk[p], lv[p], lh[p], s, lt[p], low[p]) }
  FILENAME == ARGV[1] { dk[$1] = $2; dv[$1] = $3; dt[$1] = $4; dow[$1] = $5; all[$1] = 1; next }  # desired
  FILENAME == ARGV[2] { nh[$2] = $1; next }                                  # new hashes
  FILENAME == ARGV[3] { ch[$2] = $1; next }                                  # current hashes
  FILENAME == ARGV[4] { lk[$2] = $1; lv[$2] = $3; lh[$2] = $4; ls[$2] = $5; all[$2] = 1   # lock
                        lt[$2] = (NF >= 6 && $6 != "" ? $6 : "claude"); low[$2] = (NF >= 7 && $7 != "" ? $7 : "file"); next }
  FILENAME == ARGV[5] { um[$1] = $2; next }                                  # staged unmerges
  FILENAME == ARGV[6] { bo[$1] = $2; bn[$1] = $3; next }                     # blocks: old, new sha
  END {
    for (p in all) {
      d = (p in dk); l = (p in lk) && lk[p] != "seed"; c = (p in ch) ? ch[p] : "-"
      if ((p in lk) && lk[p] == "seed") {           # project-owned since seeding
        if (!d) { old("SEED-KEEP", p, ls[p]); continue }
        l = 0
      }
      # A generated file whose content did not change keeps its file_version.
      v = dv[p]
      if (d && dk[p] == "generated" && (p in lh) && lh[p] == nh[p]) v = lv[p]
      # A project file holding harness entries: never a conflict, since the merge
      # keeps every entry of the project. "created" = the harness made the file.
      # A block (AGENTS.md, GEMINI.md): the lock hash is that of the block, so a hand
      # edit inside the block is a conflict, and edits outside it never are.
      ob = (d && dow[p] == "entries") || (!d && l && low[p] == "entries")
      bk = (d && dow[p] == "block") || (!d && l && low[p] == "block")
      if (ob || bk) {
        edited = bk && (p in lk) && (p in bo) && bo[p] != "-" && bo[p] != lh[p]
        if (d && !uninstall) {
          st = (p in ls) ? ls[p] : (c == "-" ? "created" : "merged")
          h = bk ? bn[p] : nh[p]
          if (edited && !theirs) out("CONFLICT-BLOCK", p, dk[p], v, h, "-", dt[p], dow[p])
          else if (c == nh[p])   out("NOOP", p, dk[p], v, h, st, dt[p], dow[p])
          else                   out(c == "-" ? "ADD" : "MERGE", p, dk[p], v, h, st, dt[p], dow[p])
        } else if (c == "-")     old("GONE", p, ls[p])
        else if (edited && !theirs) old("BLOCK-KEPT", p, ls[p])
        else if (um[p] == 1 && ls[p] == "created") old("REMOVE", p, ls[p])
        else if (p in um)        old("UNMERGE", p, ls[p])
        continue
      }
      if (uninstall) {
        if (!l) continue
        if (c == "-")            old("GONE", p, ls[p])
        else if (c == lh[p])     old(p == ".claude/settings.json" ? "UNINSTALL-SETTINGS" : "REMOVE", p, ls[p])
        else                     old("LEAVE-MODIFIED", p, ls[p])
        continue
      }
      if (d && l) {
        if (c == "-")            des("RESTORE", p, v, "clean")
        else if (c == nh[p])     des("NOOP", p, v, "clean")
        else if (c == lh[p])     des("UPDATE", p, v, "clean")
        else if (theirs)         des("OVERWRITE", p, v, "clean")
        else if (keep || ls[p] == "kept-local") out("KEEP", p, lk[p], lv[p], lh[p], "kept-local", dt[p], dow[p])
        else                     des("CONFLICT-MODIFIED", p, v, "-")
      } else if (d) {
        if (c == "-")            des("ADD", p, v, "clean")
        else if (c == nh[p])     des("ADOPT", p, v, "clean")
        else if (p == ".claude/settings.json" && migrate) des("MIGRATE-SETTINGS", p, v, "clean")
        else if (theirs)         des("OVERWRITE", p, v, "clean")
        else                     des("CONFLICT-UNMANAGED", p, v, "-")
      } else if (l) {
        # No longer desired: a removed target or profile, or a file dropped upstream.
        if (c == "-")            old("GONE", p, ls[p])
        else if (c == lh[p])     old(p == ".claude/settings.json" ? "UNINSTALL-SETTINGS" : "REMOVE", p, ls[p])
        else                     old("ORPHAN-KEPT", p, ls[p])
      }
    }
  }' "$DESIRED" "$NEWH" "$CURH" "$LOCK_ROWS" "$UNMERGE" "$BLOCKS" | LC_ALL=C sort -t$'	' -k2,2 > "$OPS"

# Seeds become ops too (write-if-absent; lock row "seed … project").
while IFS=$'\t' read -r dest _k tgts; do
  [[ -z "$dest" ]] && continue
  printf 'SEED\t%s\tseed\t%s\t-\tproject\t%s\tfile\n' "$dest" "$VERSION" "$tgts" >> "$OPS"
done < "$SEEDS"

# A moved 1.x config: the old file is deleted (the SEED op above writes the new one).
if [[ $cfg_move -eq 1 && $uninstall -eq 0 ]]; then
  awk -F'\t' -v OFS='\t' '$2 == ".claude/harness.config" { next } { print }' "$OPS" > "$OPS.tmp" && mv -f "$OPS.tmp" "$OPS"
  printf 'MOVE-OUT\t.claude/harness.config\tseed\t-\t-\tproject\t-\t-\n' >> "$OPS"
fi

count() { awk -F'\t' -v o="$1" '$1 == o' "$OPS" | wc -l | tr -d ' '; }

# ---------------------------------------------------------------- report
if [[ $uninstall -eq 1 ]]; then mode="uninstall"; else mode="sync ${old_ver:-<none>} → $VERSION"; fi
hc_info "harness $mode  |  target: $T  |  profiles: $PROFILES  |  agents: $TARGETS"
awk -F'\t' '$1 != "NOOP" && $1 != "SEED-KEEP" { printf "  %-18s %s\n", $1, $2 }' "$OPS" >&2
[[ $cfg_update -eq 1 ]] && printf '  %-18s %s\n' "CONFIG" ".agents/harness.config (profiles=$PROFILES, was ${cfg_profiles:-unset}; targets=$TARGETS, was ${cfg_targets:-unset})" >&2
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
  hc_warn "v0.x leftovers found (superseded by .claude/rules/harness/ and .agents/harness/hooks/); review and delete them:"
  printf '    %s\n' "${legacy[@]}" >&2
fi

if [[ $uninstall -eq 0 && -d "$CL/agents" ]]; then
  while IFS= read -r af; do
    an="$(awk '/^name:/ { sub(/^name:[[:space:]]*/, ""); print; exit }' "$af")"
    case "$an" in explorer|implementor|infra-implementor|verifier|reviewer|screen-capturer|store-creative|listing-copywriter|store-precheck-auditor|icon-creator|brand-asset-creator|illustrator|creative-director|video-creative|motion-designer)
      [[ "${af##*/}" == "$an.md" ]] || hc_warn "${af#"$T"/} declares the reserved agent name '$an'; change its name: field too" ;;
    esac
  done < <(find "$CL/agents" -maxdepth 1 -name '*.md' -type f 2>/dev/null)
fi

conflicts=$(( $(count CONFLICT-MODIFIED) + $(count CONFLICT-UNMANAGED) + $(count CONFLICT-BLOCK) ))
if [[ $conflicts -gt 0 ]]; then
  hc_fail "$conflicts conflict(s) — nothing was written."
  awk -F'\t' '$1 ~ /^CONFLICT/ { print "  " $1 ": " $2 }' "$OPS" >&2
  [[ $(count CONFLICT-MODIFIED) -gt 0 ]] && cat >&2 <<'EOF'
  CONFLICT-MODIFIED  : a harness file was edited in this project. Move the change into
                       .claude/rules/project/ (or settings.project.json), then re-run with
                       --theirs (take the harness version; your copy is saved under
                       .agents/harness/.backup/) or --keep (keep yours as kept-local;
                       harness-doctor keeps reporting it).
EOF
  [[ $(count CONFLICT-BLOCK) -gt 0 ]] && cat >&2 <<'EOF'
  CONFLICT-BLOCK     : the harness block (between <!-- harness:begin --> and
                       <!-- harness:end -->) was edited by hand. Move your text outside
                       the block, then re-run, or re-run with --theirs to rewrite it.
EOF
  [[ $(count CONFLICT-UNMANAGED) -gt 0 ]] && cat >&2 <<'EOF'
  CONFLICT-UNMANAGED : a file of yours sits at a path the harness owns. Reserved names:
                       agents explorer, implementor, infra-implementor, verifier, reviewer,
                       screen-capturer, store-creative, listing-copywriter,
                       store-precheck-auditor, icon-creator, brand-asset-creator, illustrator,
                       creative-director, video-creative, motion-designer; skills coding-standards,
                       design-patterns, ui-ux, typography, color-science, seo, harness,
                       mobile-screen-capture, store-mockups, store-listing,
                       store-submission-precheck, app-icons, brand-assets, story-art,
                       creative-direction, brand-video, motion-ui.
                       Rename yours and change its name: field (recommended), commit the
                       rename, then re-run; or re-run with --theirs (yours is saved under
                       .agents/harness/.backup/). --keep does not apply.
EOF
  exit 1
fi

# Guard: a harness file hidden by the project's .gitignore never reaches
# teammates (and breaks --commit), so refuse before writing anything.
if [[ $in_git -eq 1 && $uninstall -eq 0 ]]; then
  ignored="$( { awk -F'\t' '$1 !~ /^(REMOVE|GONE|LEAVE-MODIFIED|SEED-KEEP|ORPHAN-KEPT)$/ { print $2 }' "$OPS"
                echo ".agents/harness/lock"; } \
              | git -C "$T" check-ignore -v --stdin 2>/dev/null \
              | grep -vE ':[0-9]+:!' || true)"  # -v also reports paths re-included by a !negation
  if [[ -n "$ignored" ]]; then
    if [[ $dry -eq 1 ]]; then
      hc_warn "these harness files are ignored by git; the real run will refuse until the rule is changed:"
    else
      hc_fail "these harness files are ignored by git, so teammates would never get them — nothing was written:"
    fi
    printf '%s\n' "$ignored" | awk -F'\t' '{ printf "    %-50s (rule %s)\n", $2, $1 }' >&2
    # A rule that hides all of .claude/ gets its own advice: the harness is meant to be committed,
    # and only Claude Code's per-person files stay ignored.
    if printf '%s\n' "$ignored" | cut -f1 | sed 's/^[^:]*:[0-9]*://' \
         | grep -qxE '/?\.claude(/|/\*|/\*\*)?'; then
      {
        printf '  Fix: a rule ignores all of .claude/, but the harness is meant to be committed so every\n'
        printf '       teammate and session gets the same rules. Replace that line with\n'
        printf '         .claude/settings.local.json\n'
        printf '       (per-person settings stay private), then re-run.\n'
      } >&2
      if [[ $dry -eq 1 ]]; then ignored=""; else exit 1; fi
    fi
    # Likewise a rule hiding a whole folder another agent reads (.agents/ holds the shared
    # runtime and skills since 2.0; .cursor/, .codex/, .gemini/ their rules and hooks).
    whole="$(printf '%s\n' "$ignored" | cut -f1 | sed 's/^[^:]*:[0-9]*://' \
               | grep -xE '/?\.(agents|cursor|codex|gemini)(/|/\*|/\*\*)?' | head -1 || true)"
    if [[ -n "$whole" && -n "$ignored" ]]; then
      {
        printf '  Fix: the rule "%s" ignores a whole agent folder, but the harness files in it are meant\n' "$whole"
        printf '       to be committed so every teammate and agent gets them. Delete that line (or narrow it\n'
        printf '       to your own files there), then re-run.\n'
      } >&2
      if [[ $dry -eq 1 ]]; then ignored=""; else exit 1; fi
    fi
  fi
  if [[ -n "$ignored" ]] && ! printf '%s\n' "$ignored" | cut -f2 | grep -q '^\.claude/skills/'; then
    printf '  Fix: narrow the rules named above so the harness paths are not ignored, then re-run.\n' >&2
    [[ $dry -eq 1 ]] || exit 1
  elif [[ -n "$ignored" ]]; then
    # The suggested exceptions name the harness skills this profile actually installs.
    {
      printf '  Fix: narrow that rule so the harness paths are not ignored. For example, replace\n'
      printf '         /.claude/skills/\n       with\n         /.claude/skills/*\n'
      awk -F'\t' '$2 ~ /^\.claude\/skills\/[^\/]+\// { split($2, a, "/"); print a[3] }' "$OPS" \
        | LC_ALL=C sort -u | while IFS= read -r sk; do printf '         !/.claude/skills/%s/\n' "$sk"; done
      # Files directly in .claude/skills/ (its .gitignore) need their own exception.
      awk -F'\t' '$2 ~ /^\.claude\/skills\/[^\/]+$/ { print $2 }' "$OPS" \
        | LC_ALL=C sort -u | while IFS= read -r f; do printf '         !/%s\n' "$f"; done
      printf '       then re-run.\n'
    } >&2
    [[ $dry -eq 1 ]] || exit 1
  fi
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
    REMOVE|MOVE-OUT)
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
    ADD|RESTORE|UPDATE|OVERWRITE|MIGRATE-SETTINGS|SEED|REMOVE|UNINSTALL-SETTINGS|MOVE-OUT|MERGE|UNMERGE)
      sync_apply_one "$op" "$p" ;;
  esac
done < "$OPS"
[[ $cfg_update -eq 1 && $cfg_move -eq 0 ]] && sync_apply_one CONFIG .agents/harness.config

# Write the new lock (commit point). Deterministic: sorted, no timestamps,
# canonical source URL (never this machine's checkout remote).
# sync_drop_file <relpath> — delete a file inside the transaction (journaled).
sync_drop_file() {
  [[ -f "$T/$1" ]] || return 0
  mkdir -p "$(dirname "$BACKUP/$1")"
  cp -p "$T/$1" "$BACKUP/$1"
  printf 'restore\t%s\n' "$1" >> "$JOURNAL"
  rm -f "$T/$1"
  printf '%s\n' "$1" >> "$changed"
}
if [[ $uninstall -eq 1 ]]; then
  sync_drop_file .agents/harness/lock
  sync_drop_file .claude/harness/lock
else
  # The 1.x lock is replaced by .agents/harness/lock.
  [[ $migrate_layout -eq 1 ]] && sync_drop_file .claude/harness/lock
  {
    echo "# harness lock - generated by harness sync; do not edit by hand."
    echo "# Git merge conflict here? Keep either side, then re-run harness sync; it re-derives this file."
    printf 'lock_format\t2\n'
    printf 'harness_version\t%s\n' "$VERSION"
    printf 'source\t%s\n' "$HARNESS_UPSTREAM_URL"
    printf 'profiles\t%s\n' "$PROFILES"
    printf 'targets\t%s\n' "$TARGETS"
    printf '#kind\tpath\tfile_version\tsha256\tstatus\ttargets\towner\n'
    awk -F'\t' -v OFS='\t' '
      $1 == "ORPHAN-KEPT" || $1 == "GONE" || $1 == "REMOVE" || $1 == "UNINSTALL-SETTINGS" || $1 == "UNMERGE" || $1 == "BLOCK-KEPT" { next }
      { print $3, $2, $4, $5, $6, $7, $8 }' "$OPS" | LC_ALL=C sort -t$'\t' -k2,2
  } > "$TMPD/lock.new"
  if [[ -f "$LOCK" ]] && cmp -s <(tr -d '\r' < "$LOCK") "$TMPD/lock.new"; then
    rm -f "$TMPD/lock.new"
  else
    if [[ -f "$LOCK" ]]; then
      mkdir -p "$(dirname "$BACKUP/.agents/harness/lock")"
      cp -p "$LOCK" "$BACKUP/.agents/harness/lock"
      printf 'restore\t%s\n' ".agents/harness/lock" >> "$JOURNAL"
    else
      printf 'delete\t%s\n' ".agents/harness/lock" >> "$JOURNAL"
    fi
    mv -f "$TMPD/lock.new" "$LOCK"
    printf '%s\n' ".agents/harness/lock" >> "$changed"
  fi
fi
# Keep overwritten files (--theirs) beyond the transaction: .agents/harness/.backup/
if [[ $(count OVERWRITE) -gt 0 ]]; then
  keep_dir="$HD/.backup/$(date -u +%Y%m%dT%H%M%SZ).$$"
  while IFS=$'\t' read -r op p _; do
    [[ "$op" == OVERWRITE && -f "$BACKUP/$p" ]] || continue
    mkdir -p "$(dirname "$keep_dir/$p")"
    cp -p "$BACKUP/$p" "$keep_dir/$p"
  done < "$OPS"
  hc_info "previous versions of overwritten files saved in ${keep_dir#"$T"/} (gitignored)"
fi
# A failed persistent-backup copy must still roll back the applied changes.
applying=0

# Tidy directories emptied by removals (never a top-level directory such as .claude/).
while IFS=$'\t' read -r op p _; do
  [[ "$op" == REMOVE || "$op" == UNINSTALL-SETTINGS ]] || continue
  d="$(dirname "$T/$p")"
  while [[ "$d" == "$T"/*/* ]]; do
    rmdir "$d" 2>/dev/null || break
    d="$(dirname "$d")"
  done
done < "$OPS"
if [[ $uninstall -eq 1 ]]; then
  rmdir "$TMPD" 2>/dev/null || true
  [[ -d "$HD/.backup" ]] && hc_info "kept .agents/harness/.backup/ (copies saved by earlier --theirs runs); delete it when no longer needed"
  rmdir "$HD" "$CL/rules/harness" "$CL/harness" 2>/dev/null || true
  left="$(awk -F'\t' '$1 == "SEED-KEEP" { printf "%s ", $2 }' "$OPS")"
  [[ -n "$left" ]] && hc_info "project-owned files left in place: $left(CLAUDE.md may still mention .claude/rules/harness/)"
fi

awk -F'\t' '$1 == "ORPHAN-KEPT" { print "  kept (modified, now project-owned): " $2 }' "$OPS" >&2
awk -F'\t' '$1 == "KEEP" { print "  kept-local (modified; harness-doctor will keep reporting): " $2 }' "$OPS" >&2
awk -F'\t' '$1 == "LEAVE-MODIFIED" { print "  left in place (modified): " $2 }' "$OPS" >&2
awk -F'\t' '$1 == "BLOCK-KEPT" { print "  harness block left in place (edited by hand; delete it yourself): " $2 }' "$OPS" >&2
[[ $migrate_layout -eq 1 ]] && hc_info "moved the harness runtime and lock from .claude/harness/ to .agents/harness/ (shared by every agent)"
[[ $cfg_move -eq 1 && $uninstall -eq 0 ]] && hc_info "moved .claude/harness.config to .agents/harness.config (project-owned; commit it)"
[[ $migrate_settings -eq 1 ]] && hc_info "existing .claude/settings.json folded into .claude/settings.project.json (project-owned); settings.json is now generated"
[[ $cfg_update -eq 1 ]] && hc_info "saved profiles=$PROFILES targets=$TARGETS in .agents/harness.config"
n_changed=$(wc -l < "$changed" | tr -d ' ')
hc_ok "harness ${mode}: $n_changed file(s) changed"

# Writing a hook file does not make it run: say per agent whether it will (trust,
# hook review, feature switches). Informational; trust is never set for the user.
if [[ $uninstall -eq 0 && "$TARGETS" != claude ]] && hc_python >/dev/null 2>&1; then
  hc_info "agent hooks (configured is not active until the agent trusts them):"
  hc_py "$H/bin/harness-activation.py" "$T" "$TARGETS" 2>/dev/null \
    | awk -F'\t' '{ printf "  %-12s %-21s %s\n", $1, $2, $3 }' >&2 || true
fi

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
      if [[ $uninstall -eq 1 ]]; then msg="chore(harness): uninstall agent harness"; else msg="chore(harness): sync agent harness to v$VERSION"; fi
      if ! git -C "$T" add -- "${paths[@]}" || ! git -C "$T" commit -q -m "$msg" -- "${paths[@]}"; then
        hc_fail "the sync was applied, but the git commit failed (see git's message above)."
        hc_fail "fix the cause, then commit the .claude/ changes yourself with: $msg"
        exit 1
      fi
      hc_ok "committed on $(git -C "$T" rev-parse --abbrev-ref HEAD): $(git -C "$T" log -1 --format='%h %s')"
    fi
  fi
fi
exit 0
