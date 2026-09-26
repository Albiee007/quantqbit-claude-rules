#!/usr/bin/env bash
# Regression coverage for batches containing no non-empty files.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/harness/bin/harness-lib.sh"
W="$(mktemp -d)"
trap 'rm -rf "$W"' EXIT
: > "$W/empty"
printf 'hello\n' > "$W/text"
[[ "$(hc_hash_file "$W/empty")" == "$HARNESS_EMPTY_SHA" ]]
[[ "$(hc_hash_file "$W/missing")" == '-' ]]
[[ "$(printf 'empty\nmissing\n' | hc_hash_list "$W" | wc -l | tr -d ' ')" == 2 ]]
[[ "$(printf 'text\nempty\nmissing\n' | hc_hash_list "$W" | wc -l | tr -d ' ')" == 3 ]]
[[ -z "$(printf '' | hc_hash_list "$W")" ]]
source "$ROOT/scaffold/lib/safe-path.sh"
safe_relative_path "$W" 'normal/file.txt'
for invalid in '../outside' 'normal/../../outside' '/absolute' 'C:/outside' 'a//b'; do
  if safe_relative_path "$W" "$invalid"; then echo "[FAIL] accepted $invalid"; exit 1; fi
done
source "$ROOT/scaffold/lib/manifest.sh"
mkdir -p "$W/project/.claude"
printf 'keep\n' > "$W/project/keep"
printf 'outside\n' > "$W/outside"
printf '%s\n%s\n' "$W/project/keep" "$W/outside" > "$W/project/.claude/manifest"
if manifest_uninstall "$W/project/.claude/manifest"; then echo '[FAIL] unsafe uninstall accepted'; exit 1; fi
[[ -f "$W/project/keep" && -f "$W/outside" && ! -e "$W/project/.claude/.scaffold-tmp" ]]
# manifest_rows normalises legacy, v1 and v2 rows to hash, rel, origin, backup.
P="$W/rows"; mkdir -p "$P/.claude"
printf '# c\n%s/legacy.txt\nabc\tv1.txt\ndef\tv2.txt\toverwritten\t.claude.bak/t/v2.txt\n-\tsrc\tdir\t-\n' "$P" \
  > "$P/.claude/m"
[[ "$(manifest_rows "$P/.claude/m")" == "$(printf -- '-\tlegacy.txt\tcreated\t-\nabc\tv1.txt\tcreated\t-\ndef\tv2.txt\toverwritten\t.claude.bak/t/v2.txt\n-\tsrc\tdir\t-')" ]]
for row in 'x\ta\tbogus\t-' 'x\ta\toverwritten\t../out' 'x\ta\tcreated\t-\textra'; do
  printf "$row\n" > "$P/.claude/m"
  if manifest_rows "$P/.claude/m" 2>/dev/null; then echo "[FAIL] accepted manifest row $row"; exit 1; fi
done
printf 'managed\t../../outside\t1.0.0\tx\tclean\n' > "$W/project/.claude/lock"
mkdir -p "$W/project/.claude/harness"
mv "$W/project/.claude/lock" "$W/project/.claude/harness/lock"
if bash "$ROOT/scaffold/sync.sh" --target "$W/project" --uninstall > "$W/sync.log" 2>&1; then
  echo '[FAIL] unsafe sync lock accepted'; exit 1
fi
grep -q 'unsafe lock path' "$W/sync.log"
[[ -f "$W/outside" && ! -d "$W/project/.claude/harness/.tmp" ]]
echo 'helper tests passed'
