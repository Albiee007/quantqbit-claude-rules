#!/usr/bin/env bash
# === harness validator tests ===
# The clean tree must pass, and each injected policy violation must fail.
# Usage: bash tests/validate.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
W="$(mktemp -d "${TMPDIR:-/tmp}/harness-validate.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0

fresh() { # -> copy of the repo parts the validator reads
  rm -rf "$W/r"; mkdir -p "$W/r/scaffold"
  cp -r "$SRC/harness" "$SRC/skills" "$SRC/.claude-plugin" "$SRC/VERSION" "$SRC/CHANGELOG.md" "$W/r/"
  cp -r "$SRC/scaffold/lib" "$SRC/scaffold/sync.sh" "$W/r/scaffold/"
  mkdir -p "$W/r/tests"
}
validate() { bash "$W/r/scaffold/lib/validate-harness.sh" >"$W/out" 2>&1; }
expect_fail() { # desc, grep-pattern
  if validate; then fail=$((fail+1)); echo "  [FAIL] $1 — validator passed"; 
  elif grep -q -- "$2" "$W/out"; then pass=$((pass+1)); echo "  [OK] $1";
  else fail=$((fail+1)); echo "  [FAIL] $1 — wrong message:"; tail -3 "$W/out"; fi
}

fresh
if validate; then pass=$((pass+1)); echo "  [OK] clean tree passes"; else fail=$((fail+1)); echo "  [FAIL] clean tree"; tail -5 "$W/out"; fi

fresh; sed -i 's/^model: opus$/model: sonnet/' "$W/r/harness/agents/explorer.md"
expect_fail "agent on sonnet"           "model must be 'opus'"
fresh; sed -i 's/"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"/"X": "1"/' "$W/r/harness/settings.base.json"
expect_fail "force env removed"          "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"
fresh; sed -i '2a user-invokable: true' "$W/r/harness/skills/seo/SKILL.md"
expect_fail "frontmatter typo key"      "unknown frontmatter key 'user-invokable'"
fresh; sed -i 's/^name: ui-ux$/name: uiux/' "$W/r/harness/skills/ui-ux/SKILL.md"
expect_fail "skill name != folder"      "name must equal folder"
fresh; for i in $(seq 1 160); do echo "- filler $i" >> "$W/r/harness/core/00-core.md"; done
expect_fail "core over budget"          "00-core.md is"
fresh; printf 'a\r\nb\r\n' >> "$W/r/harness/rules/tests.md"
expect_fail "CRLF in rule"              "CRLF line endings"
fresh; echo 'see C:\Users\someone\notes' >> "$W/r/harness/rules/coding.md"
expect_fail "absolute user path"        "absolute user path"
fresh; mkdir -p "$W/r/harness/skills/seo/.venv"; echo x > "$W/r/harness/skills/seo/.venv/f"
expect_fail ".venv shipped"             "junk in harness"
fresh; echo '[missing](references/nope.md)' >> "$W/r/harness/skills/seo/SKILL.md"
expect_fail "broken link"               "broken link"
fresh; sed -i '1i <!-- harness:managed v1.0.0 -->' "$W/r/harness/rules/tests.md"
expect_fail "managed marker in source"  "must not carry a harness:managed"
fresh; awk '/^---$/ { n++ } n == 1 && (/^paths:/ || /^  - /) { next } 1' "$W/r/harness/rules/tests.md" > "$W/t" && mv "$W/t" "$W/r/harness/rules/tests.md"
expect_fail "rule without paths"        "must declare paths"
fresh; printf 'x() {\n' > "$W/r/harness/hooks/broken.sh"
expect_fail "bash syntax error"         "bash syntax error"
fresh; echo "2.0.0" > "$W/r/VERSION"
expect_fail "VERSION drift"             "plugin.json version"
fresh; echo "changed" >> "$W/r/harness/rules/coding.md"
expect_fail "stale manifest"            "manifest.tsv is stale"

echo; echo "validator tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
