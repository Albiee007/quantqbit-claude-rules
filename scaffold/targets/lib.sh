# shellcheck shell=bash
# === harness targets: which agents a project's harness is rendered for ===
# Sourced by scaffold/sync.sh (after harness-lib.sh). See SPEC.md for what each
# agent reads, and the plan in CHANGELOG 2.0.0.
#
# The manifest (harness/manifest.tsv) names every file by a LOGICAL destination,
# "<kind>:<relpath>" (core:00-core.md, rule:seo.md, skill:seo/SKILL.md,
# agent:explorer.md, runtime:hooks/guard.sh, dot:gitattributes). Each target has
# a map, scaffold/targets/<target>.map, that turns logical destinations into
# project paths:
#
#   #key            dest                     renderer  ext
#   skill           .claude/skills/          -
#   rule            .cursor/rules/           mdc       .mdc
#   dot:gitattributes .claude/.gitattributes -
#
# A key is either an exact logical destination (dest is then the whole path) or
# a kind (dest is a prefix; the relpath is appended). The exact key wins. A key
# may have several rows (the file is rendered to each). A logical destination
# with no key in a map is not shipped to that target.
# shared.map holds what every selected target uses (the hook runtime): its rows
# belong to the install, and a shared file stays until no selected target is left.
# renderer "-" copies the file (with the harness:managed header); other values
# name a transform applied after staging (scaffold/targets/render.py; claude-core
# runs in sync.sh so a Claude-only install needs no Python). ext, when set,
# replaces a trailing .md of the path (.mdc, .agent.md, .toml).

TG_DIR="${TG_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

# tg_known — the targets this source can render, one per line (canonical order:
# claude first, then alphabetical).
tg_known() {
  local f n
  [[ -f "$TG_DIR/claude.map" ]] && echo claude
  for f in "$TG_DIR"/*.map; do
    n="${f##*/}"; n="${n%.map}"
    [[ "$n" == shared || "$n" == claude ]] && continue
    echo "$n"
  done | LC_ALL=C sort
}

# tg_normalize <comma list> — validate, de-duplicate and put a target list in
# canonical order; prints the list, or fails naming the unknown target.
tg_normalize() {
  local in="${1// /}" t k out="" known
  known="$(tg_known)"
  [[ -n "$in" ]] || { hc_fail "empty target list"; return 1; }
  local IFS=','
  for t in $in; do
    [[ -n "$t" ]] || continue
    if ! printf '%s\n' "$known" | grep -qxF "$t"; then
      hc_fail "unknown target '$t' (this source supports: $(printf '%s' "$known" | tr '\n' ',' | sed 's/,$//'))"
      return 1
    fi
  done
  unset IFS
  while IFS= read -r k; do
    case ",$in," in *",$k,"*) out="${out:+$out,}$k" ;; esac
  done <<< "$known"
  echo "$out"
}

# tg_add <list> <target> / tg_remove <list> <target> — list arithmetic.
tg_add() { tg_normalize "${1:+$1,}$2"; }
tg_remove() {
  local t out=""
  local IFS=','
  for t in $1; do [[ "$t" == "$2" ]] || out="${out:+$out,}$t"; done
  echo "$out"
}

# tg_roots — every top-level path any target may write (".claude", ".cursor",
# "AGENTS.md" …), one per line. Preflight accepts manifest, lock and seed paths
# only under these, so a removed target's files are still covered.
tg_roots() {
  awk -F'\t' '!/^#/ && NF >= 2 { sub(/\r$/, ""); split($2, a, "/"); print a[1] }' "$TG_DIR"/*.map \
    | LC_ALL=C sort -u
}

# tg_detect <project> — the targets a project already shows signs of (opt-in:
# printed by --detect-targets, never applied on its own).
tg_detect() {
  local T="$1" out="claude"
  [[ -d "$T/.cursor" ]] && out="$out,cursor"
  [[ -d "$T/.codex" ]] && out="$out,codex"
  [[ -d "$T/.gemini" ]] && out="$out,gemini"
  [[ -d "$T/.agent" || -d "$T/.agents/rules" || -f "$T/.agents/hooks.json" ]] && out="$out,antigravity"
  [[ -f "$T/.github/copilot-instructions.md" || -d "$T/.github/instructions" || -d "$T/.github/agents" ]] && out="$out,copilot"
  echo "$out"
}

# tg_plan <manifest> <targets> <profiles> — the desired file set for these
# targets and profiles: "src<TAB>dest<TAB>file_version<TAB>renderer<TAB>targets<TAB>logical"
# per line, sorted by dest. Two targets mapping a file to the same path share
# one row (their names joined in the targets column, in canonical order);
# shared.map rows list every selected target.
tg_plan() {
  local manifest="$1" targets="$2" profiles="$3" t args=()
  local IFS=','
  for t in $targets; do args+=("map=$t" "$TG_DIR/$t.map"); done
  unset IFS
  [[ -f "$TG_DIR/shared.map" ]] && args+=("map=shared" "$TG_DIR/shared.map")
  awk -F'\t' -v OFS='\t' -v sel="$profiles" -v targets="$targets" '
    function profile_ok(row,   a, b, i, j, na, nb) {
      if (row == "all" || sel == "all") return 1
      na = split(row, a, ","); nb = split(sel, b, ",")
      for (i = 1; i <= na; i++) for (j = 1; j <= nb; j++) if (a[i] == b[j]) return 1
      return 0
    }
    BEGIN { nm = 0 }
    { sub(/\r$/, "") }
    /^#/ || NF < 2 { next }
    map != "" {   # a key may have several rows: the file is rendered to each dest
      if (!(map in seen)) { seen[map] = 1; ml[++nm] = map }
      j = ++cnt[map, $1]
      dst[map, $1, j] = $2; rnd[map, $1, j] = (NF >= 3 && $3 != "" ? $3 : "-")
      ext[map, $1, j] = (NF >= 4 && $4 != "-" ? $4 : "")
      next
    }
    NF < 5 || !profile_ok($5) { next }
    {
      kind = $2; sub(/:.*/, "", kind); rel = $2; sub(/^[^:]*:/, "", rel)
      for (i = 1; i <= nm; i++) {
        m = ml[i]
        if ((m SUBSEP $2) in cnt) { k = $2; exact = 1 }
        else if ((m SUBSEP kind) in cnt) { k = kind; exact = 0 }
        else continue
        who = (m == "shared") ? targets : m
        for (j = 1; j <= cnt[m, k]; j++) {
          if (exact) d = dst[m, k, j]
          else {
            r2 = rel; e = ext[m, k, j]
            if (e != "" && r2 ~ /\.md$/) sub(/\.md$/, e, r2)
            d = dst[m, k, j] r2
          }
          r = rnd[m, k, j]
          if (!(d in src)) { src[d] = $1; ver[d] = $3; ren[d] = r; own[d] = who; lg[d] = $2; order[++n] = d }
          else if (src[d] != $1 || ren[d] != r) {
            printf "[FAIL] target maps disagree: %s comes from %s and %s\n", d, src[d], $1 > "/dev/stderr"; bad = 1
          } else if (index("," own[d] ",", "," who ",") == 0) own[d] = own[d] "," who
        }
      }
    }
    END {
      if (bad) exit 3
      for (i = 1; i <= n; i++) { d = order[i]; print src[d], d, ver[d], ren[d], own[d], lg[d] }
    }
  ' "${args[@]}" map= "$manifest" | LC_ALL=C sort -t$'\t' -k2,2
}

# tg_configs <targets> — the files the project owns that the harness writes
# into, from "@hooks <path> <flavor>" (an agent's hook config: the harness owns
# its entries, scaffold/targets/hooks_merge.py) and "@block <path> <flavor>" (an
# instruction file: the harness owns its marked block, scaffold/targets/blocks.py)
# map rows: "target<TAB>path<TAB>flavor<TAB>hooks|block".
tg_configs() {
  local t
  local IFS=','
  for t in $1; do
    [[ -n "$t" ]] || continue
    awk -F'	' -v t="$t" '{ sub(/$/, "") } ($1 == "@hooks" || $1 == "@block") && NF >= 3 {
      print t "	" $2 "	" $3 "	" substr($1, 2) }' "$TG_DIR/$t.map"
  done
}
