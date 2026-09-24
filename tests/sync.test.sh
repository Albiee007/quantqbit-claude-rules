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
f="$R6/.claude/rules/harness/00-core.md"; awk '{ printf "%s\r\n", $0 }' "$f" > "$f.crlf" && mv "$f.crlf" "$f"
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

echo "15. downgrade refused unless --allow-downgrade"
R9="$(new_repo downgrade)"; run "$R9" --profiles all --commit
lk="$R9/.claude/harness/lock"
awk -F'\t' -v OFS='\t' '$1 == "harness_version" { $2 = "99.0.0" } 1' "$lk" > "$lk.t" && mv "$lk.t" "$lk"
git -C "$R9" commit -qam "pretend newer"
before="$(tree_sum "$R9")"
run "$R9"; check "older source refused (exit 1)" test $? -eq 1
check "refusal explains" grep -q 'older than the installed' "$WORK/out.log"
check "tree unchanged" test "$before" = "$(tree_sum "$R9")"
run "$R9" --allow-downgrade; check "--allow-downgrade proceeds" test $? -eq 0

echo "16. edit settings.project.json, then sync (documented flow, no commit first)"
R10="$(new_repo projsettings)"; run "$R10" --profiles all --commit
printf '{"permissions":{"allow":["Bash(npm test)"]}}\n' > "$R10/.claude/settings.project.json"
run "$R10" --commit; check "sync accepts uncommitted settings.project.json" test $? -eq 0
check "merged into settings.json" grep -q 'Bash(npm test)' "$R10/.claude/settings.json"
check "commit includes settings.project.json" test -z "$(git -C "$R10" status --porcelain -- .claude/settings.project.json)"

echo "17. --profiles is persisted to harness.config"
run "$R10" --profiles backend --commit; check "profile change ok" test $? -eq 0
check "harness.config updated" grep -qx 'profiles=backend' "$R10/.claude/harness.config"
run "$R10"; check "plain re-sync keeps profile" grep -q '0 file(s) changed' "$WORK/out.log"
check "ui-ux still absent" test ! -e "$R10/.claude/skills/ui-ux"

echo "18. existing settings.json + settings.project.json + v0.x entries migrate safely"
R11="$(new_repo migrate)"; mkdir -p "$R11/.claude"
cat > "$R11/.claude/settings.json" <<'JSON'
{"model":"sonnet","permissions":{"allow":["Bash(make build)"],"deny":["Edit(**/.env.*)","Write(**/.env.*)","Bash(curl*)"]},
 "hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"bash .claude/hooks/session-start-context.sh"}]}],
          "PostToolUse":[{"matcher":"Edit","hooks":[{"type":"command","command":"bash .claude/hooks/post-edit-lint.sh"},{"type":"command","command":"echo keep-me"}]}]}}
JSON
printf '{"permissions":{"deny":["Bash(git push *main*)"]}}\n' > "$R11/.claude/settings.project.json"
git -C "$R11" add -A; git -C "$R11" commit -qm s
run "$R11" --profiles all; check "migration ok (exit 0)" test $? -eq 0
p="$R11/.claude/settings.project.json"; s="$R11/.claude/settings.json"
check "team allow kept" grep -q 'Bash(make build)' "$p"
check "existing project deny kept" grep -q 'git push \*main\*' "$p"
check "custom deny kept" grep -q 'Bash(curl\*)' "$p"
check "v0.x .env.* deny dropped" test -z "$(grep 'Edit(\*\*/.env.\*)' "$p")"
check "v0.x hooks dropped" test -z "$(grep 'session-start-context' "$p")"
check "unrelated hook kept" grep -q 'keep-me' "$p"
check "non-Opus model dropped" test -z "$(grep '"model"' "$p")"
check "generated settings has harness guard" grep -q 'guard.sh' "$s"

echo "19. --theirs keeps a persistent backup"
R12="$(new_repo backup)"; mkdir -p "$R12/.claude/agents"; echo "my reviewer" > "$R12/.claude/agents/reviewer.md"
git -C "$R12" add -A; git -C "$R12" commit -qm own
run "$R12" --profiles all --theirs; check "theirs ok" test $? -eq 0
check "backup exists" test -n "$(grep -rl 'my reviewer' "$R12/.claude/harness/.backup" 2>/dev/null)"
check "backup dir is gitignored" git -C "$R12" check-ignore -q "$R12/.claude/harness/.backup/x"

echo "20. lock is identical from different source checkouts"
R13="$(new_repo lockA)"; R14="$(new_repo lockB)"
C2="$WORK/srccopy"; mkdir -p "$C2"; (cd "$SRC" && tar cf - --exclude=./.git --exclude=./Agent-Harness .) | (cd "$C2" && tar xf -)
run "$R13" --profiles all; bash "$C2/scaffold/sync.sh" --target "$R14" --profiles all >/dev/null 2>&1
check "same lock bytes from repo and non-git copy" cmp -s "$R13/.claude/harness/lock" "$R14/.claude/harness/lock"
check "lock source is canonical https" grep -q $'^source\thttps://github.com/' "$R13/.claude/harness/lock"

echo "21. Windows clone keeps scripts LF (shipped .claude/.gitattributes)"
R15="$(new_repo eol)"; run "$R15" --profiles all --commit
git -c core.autocrlf=true clone -q "$R15" "$WORK/eolclone"
check ".claude/.gitattributes shipped" test -f "$R15/.claude/.gitattributes"
check "guard.sh checked out LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.claude/harness/hooks/guard.sh")"
check "lock checked out LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.claude/harness/lock")"
bash "$WORK/eolclone/.claude/harness/bin/harness-doctor.sh" >/dev/null 2>&1; check "doctor healthy on autocrlf clone" test $? -eq 0

echo "22. --help prints usage and writes nothing"
H1="$WORK/helpcwd"; mkdir -p "$H1"
(cd "$H1" && bash "$SYNC" --help > "$WORK/help.txt" 2>&1); check "help exits 0" test $? -eq 0
check "help lists --dry-run" grep -q -- '--dry-run' "$WORK/help.txt"
check "help lists exit codes" grep -q 'Exit codes' "$WORK/help.txt"
check "help created no .claude" test ! -e "$H1/.claude"

echo "23. --commit does not sweep unrelated settings.project.json edits"
R16="$(new_repo commitscope)"; mkdir -p "$R16/.claude"
printf '{"permissions":{"allow":["Bash(npm test)"]}}\n' > "$R16/.claude/settings.project.json"
git -C "$R16" add -A; git -C "$R16" commit -qm p
run "$R16" --profiles all --commit
head_before="$(git -C "$R16" rev-parse HEAD)"
printf '{"permissions":{"allow":["Bash(npm test)"]} }\n' > "$R16/.claude/settings.project.json"   # whitespace-only edit
run "$R16" --commit; check "sync ok" test $? -eq 0
check "no commit created" test "$head_before" = "$(git -C "$R16" rev-parse HEAD)"
check "edit left uncommitted" test -n "$(git -C "$R16" status --porcelain -- .claude/settings.project.json)"

echo "24. --profiles without harness.config is saved"
R17="$(new_repo profnocfg)"; run "$R17" --no-seed --commit
check "no config after --no-seed" test ! -e "$R17/.claude/harness.config"
run "$R17" --profiles backend --commit; check "profile change ok" test $? -eq 0
check "config created with profile" grep -qx 'profiles=backend' "$R17/.claude/harness.config"
run "$R17"; check "plain sync keeps backend" grep -q '0 file(s) changed' "$WORK/out.log"

echo "25. invalid settings.json at migration gets a clear message"
R18="$(new_repo badjson)"; mkdir -p "$R18/.claude"; printf '{ // comment\n "a": 1, }\n' > "$R18/.claude/settings.json"
git -C "$R18" add -A; git -C "$R18" commit -qm j
run "$R18" --profiles all; check "refused (exit 2)" test $? -eq 2
check "says strict JSON" grep -q 'strict JSON' "$WORK/out.log"

echo "26. dry-run warns about a dirty tree the real run would refuse"
rm -f "$R16/.claude/harness/README.md"   # dirty but not a conflict (sync would restore it)
run "$R16" --dry-run; check "dry-run exits 0" test $? -eq 0
check "dry-run warns" grep -q 'real run will refuse' "$WORK/out.log"
run "$R16"; check "real run refuses dirty tree (exit 1)" test $? -eq 1
git -C "$R16" checkout -q -- .claude/harness/README.md

echo "27. doctor's CRLF recovery command works"
git -c core.autocrlf=false clone -q "$R15" "$WORK/crlffix"
g="$WORK/crlffix/.claude/harness/hooks/guard.sh"; awk '{ printf "%s\r\n", $0 }' "$g" > "$g.t" && mv "$g.t" "$g"
(cd "$WORK/crlffix" && git rm -r --cached -q .claude && git checkout HEAD -- .claude); check "command exits 0" test $? -eq 0
check "guard.sh back to LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$g")"
check "tree clean afterwards" test -z "$(git -C "$WORK/crlffix" status --porcelain)"
check "ps1 checked out LF on autocrlf clone" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.claude/harness/bin/harness-sync.ps1")"

echo "28. a .gitignore rule hiding harness files is refused before writing"
R19="$(new_repo ignored)"; printf '/.claude/skills/\n' > "$R19/.gitignore"
git -C "$R19" add .gitignore; git -C "$R19" commit -qm ignore
before="$(tree_sum "$R19")"
run "$R19" --profiles all --dry-run; check "dry-run exits 0" test $? -eq 0
check "dry-run warns about ignored files" grep -q 'real run will refuse until the rule' "$WORK/out.log"
run "$R19" --profiles all --commit; check "real run refuses (exit 1)" test $? -eq 1
check "names the rule" grep -q '.gitignore:1:/.claude/skills/' "$WORK/out.log"
check "nothing written" test "$before" = "$(tree_sum "$R19")"
printf '/.claude/skills/*\n!/.claude/skills/coding-standards/\n!/.claude/skills/design-patterns/\n!/.claude/skills/harness/\n!/.claude/skills/seo/\n!/.claude/skills/ui-ux/\n' > "$R19/.gitignore"
git -C "$R19" commit -qam narrow
run "$R19" --profiles all --commit; check "suggested fix works (exit 0)" test $? -eq 0
check "skills committed" test -n "$(git -C "$R19" ls-files .claude/skills/seo/SKILL.md)"
check "tree clean" test -z "$(git -C "$R19" status --porcelain)"
R20="$(new_repo ignoredlater)"; run "$R20" --profiles all
printf '/.claude/skills/\n' > "$R20/.gitignore"
bash "$R20/.claude/harness/bin/harness-doctor.sh" > "$WORK/doc.log" 2>&1; check "doctor flags ignored harness files (exit 2)" test $? -eq 2
check "doctor names the path" grep -q '.claude/skills/' "$WORK/doc.log"

echo
echo "sync tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
