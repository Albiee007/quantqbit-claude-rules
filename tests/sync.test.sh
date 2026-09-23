#!/usr/bin/env bash
# === harness sync scenario tests ===
# Each scenario builds a throwaway git repo, runs scaffold/sync.sh and asserts
# on the outcome. Portable: Linux, macOS, Windows Git Bash.
# Usage: bash tests/sync.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC="$SRC/scaffold/sync.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/harness-tests.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0

ok()   { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()  { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }

new_repo() { # name [extra setup cmd]
  local r="$WORK/$1"
  mkdir -p "$r" && git -C "$r" init -q && git -C "$r" config user.email t@t && git -C "$r" config user.name t \
    && git -C "$r" config core.autocrlf false
  echo "# readme" > "$r/README.md"
  git -C "$r" add README.md && git -C "$r" commit -qm init
  printf '%s' "$r"
}
tree_sum() { # repo -> checksum of every file except .git
  (cd "$1" && find . -path ./.git -prune -o -type f -print | LC_ALL=C sort | while IFS= read -r f; do
     printf '%s  %s\n' "$(sha256sum < "$f" | cut -c1-64)" "$f"; done) | sha256sum | cut -c1-64
}
run() { bash "$SYNC" --target "$1" "${@:2}" >"$WORK/out.log" 2>&1; }

echo "1. fresh install, seeds, idempotent re-sync"
R="$(new_repo fresh)"
run "$R" --profiles all --commit; check "install exits 0" test $? -eq 0
check "lock written" test -f "$R/.claude/harness/lock"
check "CLAUDE.md seeded (no AGENTS.md)" test -f "$R/CLAUDE.md"
check "core rule present" test -f "$R/.claude/rules/harness/00-core.md"
check "tree committed clean" test -z "$(git -C "$R" status --porcelain)"
run "$R"; check "re-sync exits 0" test $? -eq 0
check "re-sync changes nothing" grep -q '0 file(s) changed' "$WORK/out.log"
bash "$R/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor healthy" test $? -eq 0

echo "2. AGENTS.md project: no CLAUDE.md created"
R2="$(new_repo agents)"; echo "# agents" > "$R2/AGENTS.md"; git -C "$R2" add AGENTS.md; git -C "$R2" commit -qm a
run "$R2" --profiles backend; check "install ok" test $? -eq 0
check "CLAUDE.md NOT created" test ! -e "$R2/CLAUDE.md"
check "backend profile skips ui-ux skill" test ! -e "$R2/.claude/skills/ui-ux"

echo "3. locally modified harness file aborts, nothing written"
echo "local tweak" >> "$R/.claude/rules/harness/coding.md"; git -C "$R" commit -qam tweak
before="$(tree_sum "$R")"
run "$R"; check "exit 1 on conflict" test $? -eq 1
check "conflict reported" grep -q 'CONFLICT-MODIFIED' "$WORK/out.log"
check "tree unchanged" test "$before" = "$(tree_sum "$R")"
bash "$R/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor flags it (exit 2)" test $? -eq 2

echo "4. --keep marks kept-local; later syncs don't re-abort"
run "$R" --keep --commit; check "keep exits 0" test $? -eq 0
check "file still has tweak" grep -q 'local tweak' "$R/.claude/rules/harness/coding.md"
check "lock row kept-local" grep -q $'\tkept-local$' "$R/.claude/harness/lock"
run "$R"; check "subsequent sync ok" test $? -eq 0

echo "5. --theirs restores upstream"
run "$R" --theirs --commit; check "theirs exits 0" test $? -eq 0
check "tweak gone" test -z "$(grep 'local tweak' "$R/.claude/rules/harness/coding.md")"
bash "$R/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor healthy again" test $? -eq 0

echo "6. unmanaged file at a harness path aborts"
R3="$(new_repo unmanaged)"; mkdir -p "$R3/.claude/agents"; echo "mine" > "$R3/.claude/agents/reviewer.md"
git -C "$R3" add -A; git -C "$R3" commit -qm own
run "$R3" --profiles all; check "exit 1" test $? -eq 1
check "CONFLICT-UNMANAGED reported" grep -q 'CONFLICT-UNMANAGED.*reviewer.md' "$WORK/out.log"
check "own file untouched" grep -qx 'mine' "$R3/.claude/agents/reviewer.md"

echo "7. mid-apply failure rolls back to byte-identical tree"
R4="$(new_repo rollback)"
before="$(tree_sum "$R4")"
HARNESS_FAIL_AFTER=20 run "$R4" --profiles all; rc=$?
check "exit 2 on failure" test $rc -eq 2
check "rollback reported" grep -q 'rollback complete' "$WORK/out.log"
check "tree byte-identical" test "$before" = "$(tree_sum "$R4")"
check "no lock left" test ! -e "$R4/.claude/harness/lock"
# rollback of an UPDATE on an installed project
run "$R" --profiles all --commit
before="$(tree_sum "$R")"
HARNESS_FAIL_AFTER=0 run "$R" --profiles web --allow-dirty; rc=$?
check "profile-change failure rolls back (exit 2)" test $rc -eq 2
check "installed tree byte-identical" test "$before" = "$(tree_sum "$R")"

echo "8. orphans: clean removed, modified kept"
run "$R" --profiles all --commit
echo "edit" >> "$R/.claude/skills/seo/SKILL.md" 2>/dev/null || true
git -C "$R" commit -qam "edit seo" 2>/dev/null || true
run "$R" --profiles backend --commit; check "profile shrink ok" test $? -eq 0
check "clean orphan (ui-ux rule) removed" test ! -e "$R/.claude/rules/harness/ui-ux.md"
if [[ -e "$R/.claude/skills/seo/SKILL.md" ]]; then
  check "modified orphan kept" grep -q '^edit$' "$R/.claude/skills/seo/SKILL.md"
fi
check "orphan dropped from lock" test -z "$(grep 'skills/seo/SKILL.md' "$R/.claude/harness/lock")"

echo "9. concurrent run refused"
R5="$(new_repo mutex)"; mkdir -p "$R5/.claude/harness/.tmp/sync.lock.d"
run "$R5" --profiles all; check "refused while locked" test $? -ne 0
check "message mentions --force-unlock" grep -q 'force-unlock' "$WORK/out.log"
run "$R5" --profiles all --force-unlock; check "--force-unlock proceeds" test $? -eq 0

echo "10. CRLF checkout is not 'modified'"
R6="$(new_repo crlf)"; run "$R6" --profiles all --commit
f="$R6/.claude/rules/harness/00-core.md"; sed -i.bak 's/$/\r/' "$f"; rm -f "$f.bak"
bash "$R6/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor ignores CRLF" test $? -eq 0
run "$R6" --allow-dirty; check "sync treats CRLF as unchanged" grep -q '0 file(s) changed' "$WORK/out.log"

echo "11. dirty harness paths block sync"
echo "x" >> "$R6/.claude/harness/README.md"
run "$R6"; check "dirty tree refused (exit 1)" test $? -eq 1
git -C "$R6" checkout -q -- .claude/harness/README.md

echo "12. project settings merge + Opus lock"
R7="$(new_repo settings)"; mkdir -p "$R7/.claude"
printf '{"model":"sonnet"}\n' > "$R7/.claude/settings.project.json"; git -C "$R7" add -A; git -C "$R7" commit -qm s
run "$R7" --profiles all; check "non-Opus project model rejected" test $? -ne 0
printf '{"env":{"CLAUDE_CODE_SUBAGENT_MODEL":"haiku","FOO":"1"},"permissions":{"allow":["Bash(make test)"]}}\n' > "$R7/.claude/settings.project.json"
git -C "$R7" commit -qam s2
run "$R7" --profiles all; check "merge ok" test $? -eq 0
check "project allow merged" grep -q 'Bash(make test)' "$R7/.claude/settings.json"
check "subagent model stays opus" grep -q '"CLAUDE_CODE_SUBAGENT_MODEL": "opus"' "$R7/.claude/settings.json"
check "project env kept" grep -q '"FOO": "1"' "$R7/.claude/settings.json"

echo "13. path with spaces"
R8="$(new_repo "with space")"; run "$R8" --profiles all; check "install ok" test $? -eq 0
bash "$R8/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor healthy" test $? -eq 0

echo "14. uninstall leaves modified files, removes the rest"
echo "keepme" >> "$R8/.claude/agents/verifier.md"
run "$R8" --uninstall --allow-dirty; check "uninstall ok" test $? -eq 0
check "lock removed" test ! -e "$R8/.claude/harness/lock"
check "clean file removed" test ! -e "$R8/.claude/rules/harness/00-core.md"
check "modified file kept" grep -q keepme "$R8/.claude/agents/verifier.md"
check "seed kept (project-owned)" test -f "$R8/.claude/harness.config"

echo
echo "sync tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
