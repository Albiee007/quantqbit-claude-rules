#!/usr/bin/env bash
# === harness target render tests ===
# Installs the harness for every target into one throwaway repo and checks what
# each agent gets: well-formed frontmatter, parseable TOML and JSON, no Claude
# Code paths left in another agent's files, no pinned models outside Claude.
# Usage: bash tests/targets.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SRC/harness/bin/harness-lib.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/harness-targets.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
pass=0; fail=0
ok()  { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad() { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; [[ -s "$WORK/out.log" ]] && tail -15 "$WORK/out.log" | sed 's/^/        | /'; return 0; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }

R="$WORK/proj"; mkdir -p "$R"
git -C "$R" init -q && git -C "$R" config user.email t@t && git -C "$R" config user.name t && git -C "$R" config core.autocrlf false
echo "# readme" > "$R/README.md"; git -C "$R" add README.md; git -C "$R" commit -qm init
ALL="claude,$(cd "$SRC/scaffold/targets" && ls *.map | sed 's/\.map$//' | grep -vxE 'shared|claude' | LC_ALL=C sort | paste -sd, -)"

echo "1. install for every target ($ALL)"
bash "$SRC/scaffold/sync.sh" --target "$R" --profiles all --targets "$ALL" >"$WORK/out.log" 2>&1
check "install exits 0" test $? -eq 0
check "lock lists every target" grep -qx $'targets\t'"$ALL" "$R/.agents/harness/lock"

echo "2. no Claude Code paths in another agent's files"
others=(.cursor .github .codex .gemini .agents/skills .agents/harness/rules .agents/rules .agents/agents AGENTS.md GEMINI.md)
hits="$(cd "$R" && grep -rnE '\.claude/(skills|rules|agents|settings)' "${others[@]}" 2>/dev/null \
          | grep -v '^\.agents/skills/harness/' || true)"   # the harness skill documents every layout
check "no .claude/skills, rules, agents or settings outside Claude's files" test -z "$hits"
[[ -n "$hits" ]] && printf '%s\n' "$hits" | head -10 | sed 's/^/        | /'

echo "3. frontmatter per agent"
mdc_bad="$(for f in "$R"/.cursor/rules/harness/*.mdc; do
  head -1 "$f" | grep -q '^---$' && grep -q '^description: ' "$f" && grep -qE '^alwaysApply: (true|false)$' "$f" || echo "$f"; done)"
check "every Cursor rule has description and alwaysApply" test -z "$mdc_bad"
check "exactly one always-on Cursor rule (the core)" test "$(grep -l '^alwaysApply: true' "$R"/.cursor/rules/harness/*.mdc | wc -l | tr -d ' ')" -eq 1
inst_bad="$(for f in "$R"/.github/instructions/harness/*.instructions.md; do grep -q '^applyTo: "' "$f" || echo "$f"; done)"
check "every Copilot instructions file has applyTo" test -z "$inst_bad"
ag_bad="$(for f in "$R"/.agents/rules/harness-*.md; do grep -qE '^trigger: (always_on|glob)$' "$f" || echo "$f"; done)"
check "every Antigravity rule has a known trigger (others are silently dropped)" test -z "$ag_bad"
check "glob lists hold no braces (comma lists can't)" bash -c "! grep -hE '^(globs|applyTo): .*[{}]' '$R'/.cursor/rules/harness/*.mdc '$R'/.github/instructions/harness/*.md '$R'/.agents/rules/harness-*.md"
n_agents="$(ls "$SRC"/harness/agents/*.md | wc -l | tr -d ' ')"
for d in .cursor/agents .github/agents .gemini/agents .agents/agents .codex/agents; do
  check "$d has all $n_agents agents" test "$(ls "$R/$d" | wc -l | tr -d ' ')" -eq "$n_agents"
done
check "no model pinned outside Claude" bash -c "! grep -rqE '^model[: ]' '$R'/.cursor/agents '$R'/.github/agents '$R'/.gemini/agents '$R'/.agents/agents '$R'/.codex/agents"
check "Claude agents keep model: opus" test "$(grep -l '^model: opus' "$R"/.claude/agents/*.md | wc -l | tr -d ' ')" -eq "$n_agents"

echo "4. TOML and JSON parse"
check "Codex agents are valid TOML with the required keys" hc_py - "$R/.codex/agents" <<'PY'
import sys, tomllib
from pathlib import Path
for f in Path(sys.argv[1]).glob("*.toml"):
    d = tomllib.loads(f.read_text(encoding="utf-8"))
    assert {"name", "description", "developer_instructions"} <= d.keys(), f
    assert d["name"] == f.stem, f
PY
check "hook configs are valid JSON" hc_py - "$R" <<'PY'
import json, sys
from pathlib import Path
for p in (".cursor/hooks.json", ".github/hooks/harness.json", ".codex/hooks.json", ".gemini/settings.json", ".agents/hooks.json", ".claude/settings.json"):
    json.loads((Path(sys.argv[1]) / p).read_text(encoding="utf-8"))
PY
check "every hook command names a shipped script" hc_py - "$R" <<'PY'
import json, re, sys
from pathlib import Path
root = Path(sys.argv[1])
for p in (".cursor/hooks.json", ".github/hooks/harness.json", ".codex/hooks.json", ".gemini/settings.json", ".agents/hooks.json"):
    for s in re.findall(r"harness/hooks/([a-z-]+\.sh)", (root / p).read_text(encoding="utf-8")):
        assert (root / ".agents/harness/hooks" / s).is_file(), (p, s)
PY

echo "5. instruction blocks"
check "AGENTS.md holds one harness block" test "$(grep -c 'harness:begin' "$R/AGENTS.md")" -eq 1
check "GEMINI.md imports a file that exists" bash -c "f=\$(sed -n 's/^@\.\///p' '$R/GEMINI.md' | head -1); test -f '$R/'\"\$f\""

echo "6. a re-sync of every target changes nothing"
git -C "$R" add -A >/dev/null 2>&1; git -C "$R" commit -qm h
bash "$SRC/scaffold/sync.sh" --target "$R" >"$WORK/out.log" 2>&1
check "re-sync exits 0 with 0 changes" grep -q ': 0 file(s) changed' "$WORK/out.log"

echo
echo "target tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
