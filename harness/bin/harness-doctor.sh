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
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

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

# Scripts must have LF endings, or non-MSYS bash (Linux, WSL, containers) fails.
while IFS= read -r f; do
  warn "CRLF line endings in $f: re-checkout (git rm -r --cached -q .claude && git checkout -- .claude); the shipped .claude/.gitattributes keeps them LF"
done < <(find "$ROOT/.claude/harness" "$ROOT/.claude/skills" -name '*.sh' -type f 2>/dev/null \
           | while IFS= read -r f; do awk -v BINMODE=3 -v r="${f#"$ROOT"/}" '/\r$/ { print r; exit }' "$f"; done)

# v0.x leftovers superseded by the harness.
for f in .claude/hooks/session-start-context.sh .claude/hooks/post-edit-lint.sh \
         .claude/rules/bash.md .claude/rules/ansible.md .claude/rules/compose.md .claude/rules/terraform.md; do
  if [[ -e "$ROOT/$f" ]]; then warn "v0.x leftover $f (superseded by the harness; review and delete it)"; fi
done

# Newer harness available locally? (plugin copy, HARNESS_HOME, ~/.local/share clone)
best="$(hc_find_sources | head -n 1 || true)"
if [[ -n "$best" ]]; then
  up="${best%%$'\t'*}"; src="${best#*$'\t'}"
  if hc_ver_lt "$ver" "$up"; then
    warn "installed harness v$ver, a newer v$up is available at $src - run: bash .claude/harness/bin/harness-sync.sh --dry-run"
  elif hc_ver_lt "$up" "$ver"; then
    hc_info "local source at $src is v$up, older than the installed v$ver - update that source before syncing from it"
  fi
fi

if [[ $errors -eq 0 && $warns -eq 0 ]]; then
  [[ $quiet -eq 1 ]] || hc_ok "harness v$ver healthy ($(wc -l < "$rows" | tr -d ' ') files verified)"
  exit 0
fi
hc_info "harness v$ver: $errors error(s), $warns warning(s)"
[[ $errors -gt 0 ]] && exit 2
exit 1
