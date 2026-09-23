#!/usr/bin/env bash
# === harness doctor — check vendored harness health in this project ===
# Reports, without changing anything:
#   modified   harness file edited locally (hash differs from lock)
#   missing    harness file listed in the lock but not on disk
#   kept-local file deliberately kept diverged (sync --keep)
#   unmanaged  file inside a harness-owned dir that the lock doesn't know
#   conflict   git merge-conflict markers in the lock
#   ignore     CLAUDE.local.md / settings.local.json not gitignored
#   behind     a newer harness version is available (if the source is found)
# Usage: bash .claude/harness/bin/harness-doctor.sh [--quiet]
# Exit: 0 healthy, 1 warnings, 2 errors.
set -euo pipefail

BIN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$BIN/../../.." && pwd)"
# shellcheck source=harness-lib.sh
source "$BIN/harness-lib.sh"
LOCK="$ROOT/.claude/harness/lock"
quiet=0; [[ "${1:-}" == "--quiet" ]] && quiet=1

errors=0; warns=0
err()  { hc_fail "$*"; errors=$((errors + 1)); }
warn() { hc_warn "$*"; warns=$((warns + 1)); }

[[ -f "$LOCK" ]] || { err "no .claude/harness/lock — the harness is not installed (run harness sync)"; exit 2; }

if grep -qE '^(<<<<<<<|=======|>>>>>>>)' "$LOCK"; then
  err "lock has git merge-conflict markers — keep either side, then re-run harness sync"
fi

ver="$(tr -d '\r' < "$LOCK" | awk -F'\t' '$1 == "harness_version" { print $2; exit }')"
rows="$(mktemp "${TMPDIR:-/tmp}/harness-doctor.XXXXXX")"
trap 'rm -f "$rows" "$rows".*' EXIT
tr -d '\r' < "$LOCK" | awk -F'\t' '($1 == "managed" || $1 == "generated") && NF >= 5' > "$rows"

cut -f2 "$rows" | hc_hash_list "$ROOT" > "$rows.cur"
awk -F'\t' '
  FNR == NR { cur[$2] = $1; next }
  {
    c = cur[$2]
    if (c == "-")            print "missing\t" $2
    else if ($5 == "kept-local") print "kept-local\t" $2
    else if (c != $4)        print "modified\t" $2
  }' "$rows.cur" "$rows" > "$rows.issues"

while IFS=$'\t' read -r kind p; do
  case "$kind" in
    missing)    err  "missing: $p (re-run harness sync to restore)" ;;
    modified)   if [[ "$p" == ".claude/settings.json" ]]; then
                  err "modified: $p is generated — move edits to .claude/settings.project.json and re-sync"
                else
                  err "modified: $p — move the change to .claude/rules/project/, then sync --theirs (or --keep)"
                fi ;;
    kept-local) warn "kept-local: $p diverges from harness v$ver" ;;
  esac
done < "$rows.issues"

# Unmanaged files inside wholly harness-owned directories.
for d in .claude/rules/harness .claude/harness/hooks .claude/harness/snippets .claude/harness/bin; do
  [[ -d "$ROOT/$d" ]] || continue
  while IFS= read -r f; do
    rel="${f#"$ROOT"/}"
    grep -qF $'\t'"$rel"$'\t' "$rows" || warn "unmanaged file in harness-owned dir: $rel (move it to .claude/rules/project/)"
  done < <(find "$ROOT/$d" -type f)
done

# Personal files must stay out of git.
if git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  for f in CLAUDE.local.md .claude/settings.local.json; do
    if [[ -e "$ROOT/$f" ]] && ! git -C "$ROOT" check-ignore -q "$ROOT/$f"; then
      warn "$f exists but is not gitignored (personal settings would be committed)"
    fi
  done
fi

# Behind upstream? Only if a local harness source can be found.
for s in "${HARNESS_HOME:-}" "${CLAUDE_PLUGIN_ROOT:-}" "$HOME/.local/share/quantqbit-claude-rules"; do
  if [[ -n "$s" && -f "$s/VERSION" && -f "$s/harness/manifest.tsv" ]]; then
    up="$(tr -d '[:space:]' < "$s/VERSION")"
    if [[ "$up" != "$ver" ]]; then
      warn "installed harness v$ver, source at $s is v$up — run harness sync"
    fi
    break
  fi
done

if [[ $errors -eq 0 && $warns -eq 0 ]]; then
  [[ $quiet -eq 1 ]] || hc_ok "harness v$ver healthy ($(wc -l < "$rows" | tr -d ' ') files verified)"
  exit 0
fi
hc_info "harness v$ver: $errors error(s), $warns warning(s)"
[[ $errors -gt 0 ]] && exit 2
exit 1
