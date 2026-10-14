#!/usr/bin/env bash
# === harness sync scenario tests ===
# Each scenario builds a throwaway git repo, runs scaffold/sync.sh and asserts
# on the outcome. Portable: Linux, macOS, Windows Git Bash.
# Usage: bash tests/sync.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC="$SRC/scaffold/sync.sh"
source "$SRC/harness/bin/harness-lib.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/harness-tests.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0

ok()   { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
# A failure also shows the tail of the last command's output (sync or doctor).
bad()  { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"
         [[ -s "$WORK/out.log" ]] && tail -15 "$WORK/out.log" | sed 's/^/        | /'; annotate "$*"; return 0; }
annotate() { # on GitHub Actions, a failure also becomes an annotation (readable without the log)
  [[ "${GITHUB_ACTIONS:-}" == "true" ]] || return 0
  local body; body="$(tail -n 8 "$WORK/out.log" 2>/dev/null | cut -c1-300 | sed -e 's/%/%25/g' | awk '{ printf "%s%%0A", $0 }')"
  printf '::error title=sync: %s::%s\n' "${1//::/ }" "$body"
}
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; return 1; fi; }

new_repo() { # name [extra setup cmd]
  local r="$WORK/$1"
  mkdir -p "$r" && git -C "$r" init -q && git -C "$r" config user.email t@t && git -C "$r" config user.name t \
    && git -C "$r" config core.autocrlf false
  echo "# readme" > "$r/README.md"
  git -C "$r" add README.md && git -C "$r" commit -qm init
  printf '%s' "$r"
}
tree_sum() { # repo -> checksum of every file except .git
  hc_py - "$1" <<'PY'
import hashlib
import os
import sys
from pathlib import Path
root = Path(sys.argv[1])
files = []
for directory, dirs, names in os.walk(root):
    dirs[:] = [d for d in dirs if d != '.git']
    files.extend(Path(directory) / name for name in names)
digest = hashlib.sha256()
for file in sorted(files, key=lambda f: f.relative_to(root).as_posix()):
    digest.update(file.relative_to(root).as_posix().encode('utf-8'))
    digest.update(b'\0')
    digest.update(hashlib.sha256(file.read_bytes()).digest())
print(digest.hexdigest())
PY
}
run() { bash "$SYNC" --target "$1" "${@:2}" >"$WORK/out.log" 2>&1; }

echo "1. fresh install, seeds, idempotent re-sync"
R="$(new_repo fresh)"
run "$R" --profiles all --commit; check "install exits 0" test $? -eq 0
check "lock written" test -f "$R/.agents/harness/lock"
check "CLAUDE.md seeded (no AGENTS.md)" test -f "$R/CLAUDE.md"
check "core rule present" test -f "$R/.claude/rules/harness/00-core.md"
check "the creative-director, its skill and the media library are installed" test -f "$R/.claude/agents/creative-director.md" -a -f "$R/.claude/skills/creative-direction/SKILL.md" -a -f "$R/.agents/harness/lib/harnesslib/color.py"
check "the media library imports from its installed path" bash -c "cd '$R' && PYTHONDONTWRITEBYTECODE=1 python '$R/.claude/skills/creative-direction/scripts/direction.py' --help >/dev/null 2>&1 || PYTHONDONTWRITEBYTECODE=1 python3 '$R/.claude/skills/creative-direction/scripts/direction.py' --help >/dev/null 2>&1"
check "tree committed clean" test -z "$(git -C "$R" status --porcelain)"
run "$R"; check "re-sync exits 0" test $? -eq 0
check "re-sync changes nothing" grep -q '0 file(s) changed' "$WORK/out.log"
bash "$R/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor healthy" test $? -eq 0

echo "2. AGENTS.md project: no CLAUDE.md created"
R2="$(new_repo agents)"; echo "# agents" > "$R2/AGENTS.md"; git -C "$R2" add AGENTS.md; git -C "$R2" commit -qm a
run "$R2" --profiles backend; check "install ok" test $? -eq 0
check "CLAUDE.md NOT created" test ! -e "$R2/CLAUDE.md"
check "backend profile skips ui-ux skill" test ! -e "$R2/.claude/skills/ui-ux"
check "backend skips surfaces-and-cards reference" test ! -e "$R2/.claude/skills/ui-ux/references/surfaces-and-cards.md"
check "backend profile skips store agents" test ! -e "$R2/.claude/agents/store-creative.md"
check "backend profile skips motion-ui and its agent" test ! -e "$R2/.claude/skills/motion-ui" -a ! -e "$R2/.claude/agents/motion-designer.md"
check "backend profile skips store skills" test ! -e "$R2/.claude/skills/store-mockups"
check "backend profile skips creative direction and the media library" test ! -e "$R2/.claude/agents/creative-director.md" -a ! -e "$R2/.claude/skills/creative-direction" -a ! -e "$R2/.agents/harness/lib"

echo "3. locally modified harness file aborts, nothing written"
echo "local tweak" >> "$R/.claude/rules/harness/coding.md"; git -C "$R" commit -qam tweak
before="$(tree_sum "$R")"
run "$R"; check "exit 1 on conflict" test $? -eq 1
check "conflict reported" grep -q 'CONFLICT-MODIFIED' "$WORK/out.log"
check "tree unchanged" test "$before" = "$(tree_sum "$R")"
bash "$R/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor flags it (exit 2)" test $? -eq 2

echo "4. --keep marks kept-local; later syncs don't re-abort"
run "$R" --keep --commit; check "keep exits 0" test $? -eq 0
check "file still has tweak" grep -q 'local tweak' "$R/.claude/rules/harness/coding.md"
check "lock row kept-local" grep -q $'\tkept-local\t' "$R/.agents/harness/lock"
run "$R"; check "subsequent sync ok" test $? -eq 0

echo "5. --theirs restores upstream"
run "$R" --theirs --commit; check "theirs exits 0" test $? -eq 0
check "tweak gone" test -z "$(grep 'local tweak' "$R/.claude/rules/harness/coding.md")"
bash "$R/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor healthy again" test $? -eq 0

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
check "no lock left" test ! -e "$R4/.agents/harness/lock"
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
check "orphan dropped from lock" test -z "$(grep 'skills/seo/SKILL.md' "$R/.agents/harness/lock")"

echo "9. concurrent run refused"
R5="$(new_repo mutex)"; mkdir -p "$R5/.agents/harness/.tmp/sync.lock.d"
run "$R5" --profiles all; check "refused while locked" test $? -ne 0
check "message mentions --force-unlock" grep -q 'force-unlock' "$WORK/out.log"
run "$R5" --profiles all --force-unlock; check "--force-unlock proceeds" test $? -eq 0

echo "10. CRLF checkout is not 'modified'"
R6="$(new_repo crlf)"; run "$R6" --profiles all --commit
f="$R6/.claude/rules/harness/00-core.md"; awk '{ printf "%s\r\n", $0 }' "$f" > "$f.crlf" && mv "$f.crlf" "$f"
bash "$R6/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor ignores CRLF" test $? -eq 0
run "$R6" --allow-dirty; check "sync treats CRLF as unchanged" grep -q '0 file(s) changed' "$WORK/out.log"

echo "11. dirty harness paths block sync"
echo "x" >> "$R6/.agents/harness/README.md"
run "$R6"; check "dirty tree refused (exit 1)" test $? -eq 1
git -C "$R6" checkout -q -- .agents/harness/README.md

echo "12. project settings merge + Opus lock"
R7="$(new_repo settings)"; mkdir -p "$R7/.claude"
printf '{"model":"sonnet"}\n' > "$R7/.claude/settings.project.json"; git -C "$R7" add -A; git -C "$R7" commit -qm s
run "$R7" --profiles all; check "non-Opus project model rejected" test $? -ne 0
printf '{"disableAllHooks":true}
' > "$R7/.claude/settings.project.json"; git -C "$R7" commit -qam d
run "$R7" --profiles all; check "project disableAllHooks rejected" test $? -ne 0
check "rejection names the key" grep -q 'disableAllHooks' "$WORK/out.log"
printf '{"env":{"CLAUDE_CODE_SUBAGENT_MODEL":"haiku","FOO":"1"},"permissions":{"allow":["Bash(make test)"]}}\n' > "$R7/.claude/settings.project.json"
git -C "$R7" commit -qam s2
run "$R7" --profiles all; check "merge ok" test $? -eq 0
check "project allow merged" grep -q 'Bash(make test)' "$R7/.claude/settings.json"
check "subagent model stays opus" grep -q '"CLAUDE_CODE_SUBAGENT_MODEL": "opus"' "$R7/.claude/settings.json"
check "project env kept" grep -q '"FOO": "1"' "$R7/.claude/settings.json"
printf '{"disableAllHooks": true}
' > "$R7/.claude/settings.local.json"
HOME="$WORK/home" bash "$R7/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1
check "doctor warns about personal disableAllHooks" grep -q 'hooks off: .*settings.local.json' "$WORK/out.log"
rm -f "$R7/.claude/settings.local.json"

echo "13. path with spaces"
R8="$(new_repo "with space")"; run "$R8" --profiles all; check "install ok" test $? -eq 0
bash "$R8/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor healthy" test $? -eq 0

echo "14. uninstall leaves modified files, removes the rest"
echo "keepme" >> "$R8/.claude/agents/verifier.md"
run "$R8" --uninstall --allow-dirty; check "uninstall ok" test $? -eq 0
check "lock removed" test ! -e "$R8/.agents/harness/lock"
check "clean file removed" test ! -e "$R8/.claude/rules/harness/00-core.md"
check "modified file kept" grep -q keepme "$R8/.claude/agents/verifier.md"
check "seed kept (project-owned)" test -f "$R8/.agents/harness.config"

echo "15. downgrade refused unless --allow-downgrade"
R9="$(new_repo downgrade)"; run "$R9" --profiles all --commit
lk="$R9/.agents/harness/lock"
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
check "harness.config updated" grep -qx 'profiles=backend' "$R10/.agents/harness.config"
run "$R10"; check "plain re-sync keeps profile" grep -q '0 file(s) changed' "$WORK/out.log"
check "ui-ux still absent" test ! -e "$R10/.claude/skills/ui-ux"

echo "18. existing settings.json + settings.project.json + v0.x entries migrate safely"
R11="$(new_repo migrate)"; mkdir -p "$R11/.claude"
cat > "$R11/.claude/settings.json" <<'JSON'
{"model":"sonnet","disableAllHooks":true,"permissions":{"allow":["Bash(make build)"],"deny":["Edit(**/.env.*)","Write(**/.env.*)","Bash(curl*)"]},
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
check "disableAllHooks dropped" test -z "$(grep 'disableAllHooks' "$p" "$s")"
check "generated settings has harness guard" grep -q 'guard.sh' "$s"

echo "19. --theirs keeps a persistent backup"
R12="$(new_repo backup)"; mkdir -p "$R12/.claude/agents"; echo "my reviewer" > "$R12/.claude/agents/reviewer.md"
git -C "$R12" add -A; git -C "$R12" commit -qm own
run "$R12" --profiles all --theirs; check "theirs ok" test $? -eq 0
check "backup exists" test -n "$(grep -rl 'my reviewer' "$R12/.agents/harness/.backup" 2>/dev/null)"
check "backup dir is gitignored" git -C "$R12" check-ignore -q "$R12/.agents/harness/.backup/x"

echo "19b. failed persistent backup rolls back local files and the lock"
RB="$(new_repo backupfail)"
mkdir -p "$RB/.claude/agents" "$RB/.agents/harness"
echo 'local reviewer' > "$RB/.claude/agents/reviewer.md"
echo 'blocks backup directory creation' > "$RB/.agents/harness/.backup"
git -C "$RB" add -A; git -C "$RB" commit -qm own
before="$(tree_sum "$RB")"
run "$RB" --profiles backend --theirs; check "backup failure exits 2" test $? -eq 2
check "backup failure rolls back" grep -q 'rollback complete' "$WORK/out.log"
check "local files unchanged" test "$before" = "$(tree_sum "$RB")"

echo "20. lock is identical from different source checkouts"
R13="$(new_repo lockA)"; R14="$(new_repo lockB)"
C2="$WORK/srccopy"; mkdir -p "$C2"; (cd "$SRC" && tar cf - --exclude=./.git --exclude=./Agent-Harness .) | (cd "$C2" && tar xf -)
run "$R13" --profiles all; bash "$C2/scaffold/sync.sh" --target "$R14" --profiles all >/dev/null 2>&1
check "same lock bytes from repo and non-git copy" cmp -s "$R13/.agents/harness/lock" "$R14/.agents/harness/lock"
check "lock source is canonical https" grep -q $'^source\thttps://github.com/' "$R13/.agents/harness/lock"

echo "21. Windows clone keeps scripts LF (shipped .claude/.gitattributes)"
R15="$(new_repo eol)"; run "$R15" --profiles all --commit
{ git -c core.autocrlf=true clone --no-local "$R15" "$WORK/eolclone" 2>&1; echo "clone rc=$?"
  git -C "$R15" branch -a 2>&1; git -C "$R15" log --oneline -3 2>&1; git -C "$R15" status --porcelain 2>&1 | head -5
  git -C "$WORK/eolclone" ls-files 2>&1 | grep -c '^\.claude/'; } > "$WORK/out.log"
check "the autocrlf clone has the harness files" test -f "$WORK/eolclone/.agents/harness/hooks/guard.sh"
check ".claude/.gitattributes shipped" test -f "$R15/.claude/.gitattributes"
check "guard.sh checked out LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.agents/harness/hooks/guard.sh")"
check "lock checked out LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.agents/harness/lock")"
bash "$WORK/eolclone/.agents/harness/bin/harness-doctor.sh" >"$WORK/out.log" 2>&1; check "doctor healthy on autocrlf clone" test $? -eq 0

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
check "no config after --no-seed" test ! -e "$R17/.agents/harness.config"
run "$R17" --profiles backend --commit; check "profile change ok" test $? -eq 0
check "config created with profile" grep -qx 'profiles=backend' "$R17/.agents/harness.config"
run "$R17"; check "plain sync keeps backend" grep -q '0 file(s) changed' "$WORK/out.log"

echo "25. invalid settings.json at migration gets a clear message"
R18="$(new_repo badjson)"; mkdir -p "$R18/.claude"; printf '{ // comment\n "a": 1, }\n' > "$R18/.claude/settings.json"
git -C "$R18" add -A; git -C "$R18" commit -qm j
run "$R18" --profiles all; check "refused (exit 2)" test $? -eq 2
check "says strict JSON" grep -q 'strict JSON' "$WORK/out.log"

echo "26. dry-run warns about a dirty tree the real run would refuse"
rm -f "$R16/.agents/harness/README.md"   # dirty but not a conflict (sync would restore it)
run "$R16" --dry-run; check "dry-run exits 0" test $? -eq 0
check "dry-run warns" grep -q 'real run will refuse' "$WORK/out.log"
run "$R16"; check "real run refuses dirty tree (exit 1)" test $? -eq 1
git -C "$R16" checkout -q -- .agents/harness/README.md

echo "27. doctor's CRLF recovery command works"
git -c core.autocrlf=false clone -q --no-local "$R15" "$WORK/crlffix"
g="$WORK/crlffix/.agents/harness/hooks/guard.sh"; awk '{ printf "%s\r\n", $0 }' "$g" > "$g.t" && mv "$g.t" "$g"
(cd "$WORK/crlffix" && git rm -r --cached -q .agents && git checkout HEAD -- .agents); check "command exits 0" test $? -eq 0
check "guard.sh back to LF" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$g")"
check "tree clean afterwards" test -z "$(git -C "$WORK/crlffix" status --porcelain)"
check "ps1 checked out LF on autocrlf clone" test -z "$(awk -v BINMODE=3 '/\r$/ { print; exit }' "$WORK/eolclone/.agents/harness/bin/harness-sync.ps1")"

echo "28. a .gitignore rule hiding harness files is refused before writing"
R19="$(new_repo ignored)"; printf '/.claude/skills/\n' > "$R19/.gitignore"
git -C "$R19" add .gitignore; git -C "$R19" commit -qm ignore
before="$(tree_sum "$R19")"
run "$R19" --profiles all --dry-run; check "dry-run exits 0" test $? -eq 0
check "dry-run warns about ignored files" grep -q 'real run will refuse until the rule' "$WORK/out.log"
run "$R19" --profiles all --commit; check "real run refuses (exit 1)" test $? -eq 1
check "names the rule" grep -q '.gitignore:1:/.claude/skills/' "$WORK/out.log"
check "nothing written" test "$before" = "$(tree_sum "$R19")"
{ printf '/.claude/skills/*\n'; sed -n 's#^ *\(!/.claude/skills/[a-z.-]*/*\)$#\1#p' "$WORK/out.log"; } > "$R19/.gitignore"
check "suggestion lists store skills too" grep -q '!/.claude/skills/store-mockups/' "$R19/.gitignore"
check "suggestion lists the skills .gitignore" grep -qx '!/.claude/skills/.gitignore' "$R19/.gitignore"
git -C "$R19" commit -qam narrow
run "$R19" --profiles all --commit; check "suggested fix works (exit 0)" test $? -eq 0
check "skills committed" test -n "$(git -C "$R19" ls-files .claude/skills/seo/SKILL.md)"
check "tree clean" test -z "$(git -C "$R19" status --porcelain)"
bash "$R19/.agents/harness/bin/harness-doctor.sh" > "$WORK/doc.log" 2>&1
check "doctor accepts files re-included by a !rule" bash -c "! grep -q 'gitignored' '$WORK/doc.log'"
R20="$(new_repo ignoredlater)"; run "$R20" --profiles all
printf '/.claude/skills/\n' > "$R20/.gitignore"
bash "$R20/.agents/harness/bin/harness-doctor.sh" > "$WORK/doc.log" 2>&1; check "doctor flags ignored harness files (exit 2)" test $? -eq 2
check "doctor names the path" grep -q '.claude/skills/' "$WORK/doc.log"
R19b="$(new_repo ignoredall)"; printf 'dist\n.claude/\n' > "$R19b/.gitignore"
git -C "$R19b" add .gitignore; git -C "$R19b" commit -qm ignore
run "$R19b" --profiles all --commit; check "a rule hiding all of .claude/ is refused (exit 1)" test $? -eq 1
check "and the fix keeps only the local settings ignored" grep -q 'Replace that line with' "$WORK/out.log"
check "without the skills-only example" bash -c "! grep -q 'For example, replace' '$WORK/out.log'"
printf 'dist\n.claude/settings.local.json\n' > "$R19b/.gitignore"; git -C "$R19b" commit -qam narrow
run "$R19b" --profiles all --commit; check "that fix works (exit 0)" test $? -eq 0

echo "29. mobile profile installs the store and brand agents and skills"
R21="$(new_repo mobile)"
run "$R21" --profiles mobile; check "mobile install exits 0" test $? -eq 0
check "mobile gets surfaces-and-cards reference" test -f "$R21/.claude/skills/ui-ux/references/surfaces-and-cards.md"
for a in creative-director screen-capturer store-creative listing-copywriter store-precheck-auditor icon-creator brand-asset-creator illustrator video-creative motion-designer; do
  check "agent $a installed" test -f "$R21/.claude/agents/$a.md"
done
for s in creative-direction mobile-screen-capture store-mockups store-listing store-submission-precheck app-icons brand-assets story-art brand-video motion-ui; do
  check "skill $s installed" test -f "$R21/.claude/skills/$s/SKILL.md"
done
check "store snippet installed" test -f "$R21/.agents/harness/snippets/store.md"
check "art snippet installed" test -f "$R21/.agents/harness/snippets/art.md"
check "media snippet installed" test -f "$R21/.agents/harness/snippets/media.md"
check "the media library and its schemas are installed" test -f "$R21/.agents/harness/lib/harnesslib/schemas/direction.schema.json" -a -f "$R21/.agents/harness/lib/media/artdir.js"
check "the frozen 1.6 engine is installed" test -f "$R21/.claude/skills/store-mockups/templates/legacy-1.6/frame.html"
check "kit template copied verbatim" grep -q 'window.FRAMES' "$R21/.claude/skills/store-mockups/templates/frame.html"
check "seo skill not in mobile" test ! -e "$R21/.claude/skills/seo"
R22="$(new_repo webonly)"
run "$R22" --profiles web; check "web install exits 0" test $? -eq 0
check "web gets surfaces-and-cards reference" test -f "$R22/.claude/skills/ui-ux/references/surfaces-and-cards.md"
check "web gets brand-assets" test -f "$R22/.claude/skills/brand-assets/SKILL.md"
check "web gets the creative-director and the media library" test -f "$R22/.claude/agents/creative-director.md" -a -f "$R22/.agents/harness/lib/harnesslib/direction.py"
check "web gets no store agents" test ! -e "$R22/.claude/agents/store-creative.md"
check "web gets story-art" test -f "$R22/.claude/skills/story-art/scripts/export_art.py"
check "web gets illustrator" test -f "$R22/.claude/agents/illustrator.md"
check "web gets brand-video and the video-creative" test -f "$R22/.claude/skills/brand-video/scripts/render_video.py" -a -f "$R22/.claude/agents/video-creative.md"
check "web gets motion-ui and the motion-designer" test -f "$R22/.claude/skills/motion-ui/scripts/motion.py" -a -f "$R22/.claude/agents/motion-designer.md"
check "web gets the motion library and the virtual clock" test -f "$R22/.agents/harness/lib/harnesslib/motioncap.py" -a -f "$R22/.agents/harness/lib/media/clock.js" -a -f "$R22/.agents/harness/lib/harnesslib/schemas/motion.schema.json"
check "web gets the motion snippet" test -f "$R22/.agents/harness/snippets/motion.md"
check "web gets the video runtime" test -f "$R22/.agents/harness/lib/media/timeline.js" -a -f "$R22/.agents/harness/lib/harnesslib/cdp.py"
check "web skips store-mockups" test ! -e "$R22/.claude/skills/store-mockups"
check "web gets the art snippet" test -f "$R22/.agents/harness/snippets/art.md"
check "web skips the store snippet" test ! -e "$R22/.agents/harness/snippets/store.md"

echo "30. typography and color-science ship with web and mobile only"
for s in typography color-science; do
  check "web gets $s" test -f "$R22/.claude/skills/$s/SKILL.md"
  check "web gets $s references" test -f "$R22/.claude/skills/$s/references/sources.md"
  check "mobile gets $s" test -f "$R21/.claude/skills/$s/SKILL.md"
  check "backend skips $s" test ! -e "$R2/.claude/skills/$s"
done
R23="$(new_repo infraonly)"
run "$R23" --profiles infra; check "infra install exits 0" test $? -eq 0
check "infra skips typography" test ! -e "$R23/.claude/skills/typography"
check "infra skips color-science" test ! -e "$R23/.claude/skills/color-science"
R24="$(new_repo webshrink)"
run "$R24" --profiles web --commit; check "web install (commit) ok" test $? -eq 0
run "$R24" --profiles backend --commit; check "web → backend ok" test $? -eq 0
check "profile shrink removes typography" test ! -e "$R24/.claude/skills/typography"
check "profile shrink removes color-science" test ! -e "$R24/.claude/skills/color-science"
# An install made by a release without the two skills gains them on update.
OLD="$WORK/src-old"; mkdir -p "$OLD"
cp -R "$SRC/harness" "$SRC/scaffold" "$OLD/"
rm -rf "$OLD/harness/skills/typography" "$OLD/harness/skills/color-science"
grep -v -e '^skills/typography/' -e '^skills/color-science/' "$SRC/harness/profiles.tsv" > "$OLD/harness/profiles.tsv"
echo 1.5.0 > "$OLD/VERSION"
grep -v -e 'skills/typography/' -e 'skills/color-science/' "$SRC/harness/manifest.tsv" > "$OLD/harness/manifest.tsv"
bash "$OLD/scaffold/lib/release.sh" >"$WORK/out.log" 2>&1; check "old source manifest built" test $? -eq 0
R25="$(new_repo upgrade)"
bash "$OLD/scaffold/sync.sh" --target "$R25" --profiles web --commit >"$WORK/out.log" 2>&1
check "old release installs without the skills" test ! -e "$R25/.claude/skills/typography"
run "$R25" --commit; check "update exits 0" test $? -eq 0
check "update adds typography" test -f "$R25/.claude/skills/typography/SKILL.md"
check "update adds color-science" test -f "$R25/.claude/skills/color-science/SKILL.md"
check "update records them in the lock" grep -q 'skills/color-science/SKILL.md' "$R25/.agents/harness/lock"
R26="$(new_repo ownskill)"; mkdir -p "$R26/.claude/skills/typography"
echo "mine" > "$R26/.claude/skills/typography/SKILL.md"
git -C "$R26" add -A; git -C "$R26" commit -qm own
run "$R26" --profiles web; check "own typography skill blocks (exit 1)" test $? -eq 1
check "CONFLICT-UNMANAGED names typography" grep -q 'CONFLICT-UNMANAGED.*skills/typography' "$WORK/out.log"
check "reserved list names color-science" grep -q 'color-science' "$WORK/out.log"
R27="$(new_repo owndirector)"; mkdir -p "$R27/.claude/agents"
echo "mine" > "$R27/.claude/agents/creative-director.md"
git -C "$R27" add -A; git -C "$R27" commit -qm own
run "$R27" --profiles web; check "own creative-director agent blocks (exit 1)" test $? -eq 1
check "the reserved list names creative-direction" grep -q 'creative-direction' "$WORK/out.log"
check "the reserved list names brand-video and video-creative" bash -c "grep -q 'brand-video' '$WORK/out.log' && grep -q 'video-creative' '$WORK/out.log'"
check "the reserved list names motion-ui and motion-designer" bash -c "grep -q 'motion-ui' '$WORK/out.log' && grep -q 'motion-designer' '$WORK/out.log'"

echo "30. targets: selection, precedence, shared files, removal, uninstall"
# A second, test-only target proves the multi-target paths before real adapters exist.
MS="$WORK/multisrc"; mkdir -p "$MS"; cp -R "$SRC/harness" "$SRC/scaffold" "$SRC/VERSION" "$MS/"
printf '#key\tdest\trenderer\ncore\t.testagent/rules/\t-\nrule\t.testagent/rules/\t-\nskill\t.agents/skills/\t-\n' > "$MS/scaffold/targets/testagent.map"
mrun() { bash "$MS/scaffold/sync.sh" --target "$1" "${@:2}" >"$WORK/out.log" 2>&1; }
RT="$(new_repo targets)"
mrun "$RT" --profiles backend --commit; check "default install is claude only" grep -qx $'targets\tclaude' "$RT/.agents/harness/lock"
check "no other agent's files" test ! -e "$RT/.testagent" -a ! -e "$RT/.agents/skills"
sum="$(tree_sum "$RT")"
mkdir -p "$RT/.cursor"; mrun "$RT" --detect-targets; check "--detect-targets exits 0" test $? -eq 0
check "--detect-targets proposes but writes nothing" test "$(rmdir "$RT/.cursor"; tree_sum "$RT")" = "$sum"
mrun "$RT" --targets claude,nope; check "unknown target refused (exit 2)" test $? -eq 2
check "an unknown target writes nothing" test "$(tree_sum "$RT")" = "$sum"
mrun "$RT" --add-target testagent --commit; check "--add-target exits 0" test $? -eq 0
check "testagent rules rendered" test -f "$RT/.testagent/rules/00-core.md"
check "shared skill dir rendered" test -f "$RT/.agents/skills/coding-standards/SKILL.md"
check "claude files stay" test -f "$RT/.claude/rules/harness/00-core.md" -a -f "$RT/.claude/settings.json"
check "lock lists both targets" grep -qx $'targets\tclaude,testagent' "$RT/.agents/harness/lock"
check "config saves the targets" grep -qx 'targets=claude,testagent' "$RT/.agents/harness.config"
check "runtime rows belong to both targets" grep -q $'^managed\t.agents/harness/hooks/guard.sh\t.*\tclaude,testagent\tfile$' "$RT/.agents/harness/lock"
check "agent rows belong to their target" grep -q $'^managed\t.testagent/rules/00-core.md\t.*\ttestagent\tfile$' "$RT/.agents/harness/lock"
mrun "$RT"; check "plain re-sync keeps both (config)" bash -c "grep -q 'NOOP=' '$WORK/out.log' && ! grep -qE 'REMOVE|ADD' '$WORK/out.log'"
sed -i.bak '/^targets=/d' "$RT/.agents/harness.config" && rm -f "$RT/.agents/harness.config.bak"
mrun "$RT"; check "without targets= the lock decides" bash -c "! grep -qE '^ +REMOVE' '$WORK/out.log'"
git -C "$RT" checkout -q -- .agents/harness.config
echo "my note" >> "$RT/.testagent/rules/00-core.md"; edited=".testagent/rules/00-core.md"
git -C "$RT" commit -qam "edit a testagent rule"
mrun "$RT" --remove-target testagent --commit; check "--remove-target exits 0" test $? -eq 0
check "removed target's unedited files are gone" test ! -e "$RT/.testagent/rules/compose.md"
check "shared-dir skills of the removed target are gone" test ! -e "$RT/.agents/skills/coding-standards/SKILL.md"
check "the edited file is kept" test -f "$RT/$edited"
check "kept file reported" grep -q 'kept (modified' "$WORK/out.log"
check "runtime stays for claude" test -f "$RT/.agents/harness/hooks/guard.sh"
check "runtime rows now belong to claude only" grep -q $'^managed\t.agents/harness/hooks/guard.sh\t.*\tclaude\tfile$' "$RT/.agents/harness/lock"
check "lock and config list claude only" bash -c "grep -qx \$'targets\tclaude' '$RT/.agents/harness/lock' && grep -qx 'targets=claude' '$RT/.agents/harness.config'"
mrun "$RT" --remove-target claude; check "removing the last target is refused" test $? -eq 2
git -C "$RT" rm -q "$edited" && git -C "$RT" commit -qm "drop the kept rule"
mrun "$RT" --targets testagent --commit; check "--targets replaces the set" test $? -eq 0
check "claude-only files removed, settings.json restored/removed" test ! -e "$RT/.claude/rules/harness/00-core.md" -a ! -e "$RT/.claude/settings.json"
check "shared runtime kept for testagent" test -f "$RT/.agents/harness/hooks/guard.sh"
echo "mine" >> "$RT/$edited"; git -C "$RT" commit -qam "edit again"
mrun "$RT" --uninstall; check "uninstall exits 0" test $? -eq 0
check "uninstall removes every target's files" test ! -e "$RT/.testagent/rules/compose.md" -a ! -e "$RT/.agents/harness/hooks/guard.sh"
check "uninstall keeps the edited file" test -f "$RT/$edited"

echo "31. 1.x → 2.0 layout migration (.claude/harness → .agents/harness)"
LEGACY_REF="${LEGACY_REF:-v1.14.0}"
LS="$WORK/legacysrc"; mkdir -p "$LS"
if git -C "$SRC" archive "$LEGACY_REF" 2>/dev/null | tar -x -C "$LS" 2>/dev/null && [[ -f "$LS/scaffold/sync.sh" ]]; then
  RM="$(new_repo legacy-migrate)"
  bash "$LS/scaffold/sync.sh" --target "$RM" --profiles web --commit >"$WORK/out.log" 2>&1
  check "1.x install in the old layout" test -f "$RM/.claude/harness/lock" -a -f "$RM/.claude/harness.config"
  echo "dev_url=http://localhost:5173" >> "$RM/.claude/harness.config"
  echo "local tweak" >> "$RM/.claude/harness/README.md"
  git -C "$RM" commit -qam "project edits"
  run "$RM" --commit; rc=$?
  check "2.0 sync over 1.x exits 0" test $rc -eq 0
  check "runtime now in .agents/harness" test -f "$RM/.agents/harness/hooks/guard.sh" -a -f "$RM/.agents/harness/lock"
  check "old lock removed" test ! -e "$RM/.claude/harness/lock"
  check "old unedited runtime removed" test ! -e "$RM/.claude/harness/hooks/guard.sh"
  check "edited old runtime file kept" grep -q 'local tweak' "$RM/.claude/harness/README.md"
  check "config moved with the project's edits" bash -c "grep -q 'dev_url=http://localhost:5173' '$RM/.agents/harness.config' && test ! -e '$RM/.claude/harness.config'"
  check "settings.json points hooks at .agents/harness" grep -q '.agents/harness/hooks/guard.sh' "$RM/.claude/settings.json"
  check "lock is format 2 with targets" bash -c "grep -qx \$'lock_format\t2' '$RM/.agents/harness/lock' && grep -qx \$'targets\tclaude' '$RM/.agents/harness/lock'"
  check "migration message" grep -q 'moved the harness runtime' "$WORK/out.log"
  run "$RM"; check "re-sync after migration is a no-op" bash -c "grep -q 'harness sync .*: 0 file(s) changed' '$WORK/out.log'"
  sum="$(tree_sum "$RM")"
  RF="$(new_repo legacy-migratefail)"
  bash "$LS/scaffold/sync.sh" --target "$RF" --profiles backend --commit >"$WORK/out.log" 2>&1
  before="$(tree_sum "$RF")"
  HARNESS_FAIL_AFTER=5 run "$RF"; check "failed migration exits 2" test $? -eq 2
  check "failed migration leaves the 1.x install intact" test "$(tree_sum "$RF")" = "$before"
else
  echo "  [SKIP] $LEGACY_REF not available (shallow clone?); migration not tested"
fi

echo "32. cursor and copilot: native rules, agents, merged hook configs"
RC="$(new_repo cursorcopilot)"; mkdir -p "$RC/.cursor"
printf '{\n  "version": 1,\n  "hooks": {\n    "stop": [\n      {\n        "command": "echo mine"\n      }\n    ]\n  }\n}\n' > "$RC/.cursor/hooks.json"
cp "$RC/.cursor/hooks.json" "$WORK/user-hooks.json"
git -C "$RC" add -A; git -C "$RC" commit -qm "own cursor hooks"
run "$RC" --profiles web --targets claude,cursor,copilot --commit; check "install for three agents exits 0" test $? -eq 0
check "cursor rules are .mdc" grep -q '^alwaysApply: true' "$RC/.cursor/rules/harness/00-core.mdc"
check "path rules get globs (braces expanded)" grep -q '^globs: \*\*/\*\.tsx,\*\*/\*\.jsx' "$RC/.cursor/rules/harness/ui-ux.mdc"
check "copilot path instructions get applyTo" grep -q '^applyTo: ' "$RC/.github/instructions/harness/seo.instructions.md"
check "copilot agents map tools" grep -q '^tools: \["read", "edit", "search", "execute"\]' "$RC/.github/agents/implementor.agent.md"
check "no model is pinned outside claude" bash -c "! grep -rq '^model:' '$RC/.github/agents' '$RC/.cursor/agents'"
check "claude agents keep opus" grep -q '^model: opus' "$RC/.claude/agents/implementor.md"
check "shared skills use shared paths" bash -c "! grep -q '\.claude/skills/' '$RC/.agents/skills/ui-ux/SKILL.md'"
check "core for other agents drops the Opus section" bash -c "! grep -q 'CLAUDE_CODE_SUBAGENT_MODEL' '$RC/.agents/harness/rules/00-core.md' && grep -q 'CLAUDE_CODE_SUBAGENT_MODEL' '$RC/.claude/rules/harness/00-core.md'"
check "claude core keeps no agent markers" bash -c "! grep -q 'agent:other' '$RC/.claude/rules/harness/00-core.md'"
check "user's cursor hook kept" grep -q 'echo mine' "$RC/.cursor/hooks.json"
check "harness cursor hooks merged" grep -q 'harness/hooks/guard.sh' "$RC/.cursor/hooks.json"
check "copilot hook file created" grep -q 'guard.sh --agent copilot' "$RC/.github/hooks/harness.json"
check "lock marks merged configs as entries" grep -q $'^generated\t.cursor/hooks.json\t.*\tmerged\tcursor\tentries$' "$RC/.agents/harness/lock"
echo '{"version":1,"hooks":{"stop":[{"command":"echo mine"},{"command":"echo two"}]}}' > "$RC/.cursor/hooks.json"
git -C "$RC" commit -qam "user adds a hook"
run "$RC" --commit; check "a user edit of a merged config is no conflict" test $? -eq 0
check "both user hooks kept and harness re-merged" bash -c "grep -q 'echo two' '$RC/.cursor/hooks.json' && grep -q 'guard.sh' '$RC/.cursor/hooks.json'"
echo '{"version":1,"hooks":{"stop":[{"command":"echo mine"}]}} trailing' > "$RC/.cursor/hooks.json"
git -C "$RC" commit -qam "broken json"
run "$RC"; check "invalid JSON refused (exit 2)" test $? -eq 2
check "says strict JSON" grep -q 'strict JSON' "$WORK/out.log"
cp "$WORK/user-hooks.json" "$RC/.cursor/hooks.json"; git -C "$RC" commit -qam "restore"
run "$RC" --remove-target cursor --commit; check "--remove-target cursor exits 0" test $? -eq 0
check "removing cursor restores the user's hooks.json byte for byte" cmp -s "$RC/.cursor/hooks.json" "$WORK/user-hooks.json"
check "cursor rules removed" test ! -e "$RC/.cursor/rules/harness/00-core.mdc"
check "shared skills stay for copilot" test -f "$RC/.agents/skills/ui-ux/SKILL.md"
run "$RC" --uninstall; check "uninstall exits 0" test $? -eq 0
check "copilot hook file deleted (the harness created it)" test ! -e "$RC/.github/hooks/harness.json"
check "user's hooks.json untouched by uninstall" cmp -s "$RC/.cursor/hooks.json" "$WORK/user-hooks.json"

echo "33. codex, gemini, antigravity: blocks in AGENTS.md / GEMINI.md, TOML agents, Antigravity rules"
RX="$(new_repo threeagents)"
printf '# My project\n\nOur own instructions.\n' > "$RX/AGENTS.md"; cp "$RX/AGENTS.md" "$WORK/user-agents.md"
git -C "$RX" add -A; git -C "$RX" commit -qm "own AGENTS.md"
run "$RX" --profiles web --targets codex,gemini,antigravity --commit; check "install for codex, gemini, antigravity exits 0" test $? -eq 0
check "no Claude files" test ! -e "$RX/.claude/settings.json" -a ! -e "$RX/CLAUDE.md"
check "AGENTS.md keeps the project's text" grep -q 'Our own instructions.' "$RX/AGENTS.md"
check "AGENTS.md gets one harness block with the core rules" bash -c "[[ \$(grep -c 'harness:begin' '$RX/AGENTS.md') == 1 ]] && grep -q '## 8. Secrets' '$RX/AGENTS.md'"
check "the block indexes the path rules" grep -q 'read `.agents/harness/rules/ui-ux.md` first' "$RX/AGENTS.md"
check "GEMINI.md imports the core rules" grep -q '^@./.agents/harness/rules/00-core.md' "$RX/GEMINI.md"
check "codex agents are TOML" bash -c "grep -q '^developer_instructions = \"\"\"' '$RX/.codex/agents/implementor.toml' && grep -q '^name = \"implementor\"' '$RX/.codex/agents/implementor.toml'"
check "gemini agents map tools" grep -q '"run_shell_command"' "$RX/.gemini/agents/implementor.md"
check "antigravity rules: top-level files with triggers" bash -c "grep -q '^trigger: always_on' '$RX/.agents/rules/harness-00-core.md' && grep -q '^trigger: glob' '$RX/.agents/rules/harness-ui-ux.md'"
check "antigravity hooks name the event" grep -q 'guard.sh --agent antigravity --event PreToolUse' "$RX/.agents/hooks.json"
check "codex hooks merged" grep -q 'guard.sh\\" --agent codex' "$RX/.codex/hooks.json"
check "gemini settings hooks merged" grep -q '"harness-guard"' "$RX/.gemini/settings.json"
check "lock records the block" grep -q $'^generated\tAGENTS.md\t.*\tmerged\tcodex\tblock$' "$RX/.agents/harness/lock"
printf '\nMore of ours.\n' >> "$RX/AGENTS.md"; git -C "$RX" commit -qam "edit outside the block"
run "$RX" --commit; check "an edit outside the block is fine" test $? -eq 0
check "it is kept" grep -q 'More of ours.' "$RX/AGENTS.md"
sed -i.bak 's/^## 8\. Secrets/## 8. Secrets (edited)/' "$RX/AGENTS.md" && rm -f "$RX/AGENTS.md.bak"
git -C "$RX" commit -qam "edit inside the block"
run "$RX"; check "an edit inside the block is a conflict (exit 1)" test $? -eq 1
check "CONFLICT-BLOCK reported" grep -q 'CONFLICT-BLOCK' "$WORK/out.log"
run "$RX" --theirs --commit; check "--theirs rewrites the block" bash -c "! grep -q 'Secrets (edited)' '$RX/AGENTS.md'"
run "$RX" --remove-target codex --commit; check "--remove-target codex exits 0" test $? -eq 0
check "removing codex takes the block out of AGENTS.md" bash -c "! grep -q 'harness:begin' '$RX/AGENTS.md' && grep -q 'More of ours.' '$RX/AGENTS.md'"
check "codex agents removed" test ! -e "$RX/.codex/agents/implementor.toml"
run "$RX" --uninstall; check "uninstall exits 0" test $? -eq 0
check "GEMINI.md deleted (the harness created it)" test ! -e "$RX/GEMINI.md"
check "antigravity rules and hooks removed" test ! -e "$RX/.agents/rules/harness-00-core.md" -a ! -e "$RX/.agents/hooks.json"

echo
echo "sync tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
