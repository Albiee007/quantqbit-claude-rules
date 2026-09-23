#!/usr/bin/env bash
# === harness hook tests ===
# Feeds hook JSON payloads to each hook and asserts on the output.
# Usage: bash tests/hooks.test.sh
set -uo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HK="$SRC/harness/hooks"
P="$(mktemp -d "${TMPDIR:-/tmp}/harness-hooks.XXXXXX")"
export TMPDIR="$P/tmp"; mkdir -p "$TMPDIR"
trap 'rm -rf "$P"' EXIT
mkdir -p "$P/.claude/harness/snippets"
cp "$SRC"/harness/snippets/*.md "$P/.claude/harness/snippets/"
export CLAUDE_PROJECT_DIR="$P"
pass=0; fail=0

run() { printf '%s' "$2" | bash "$HK/$1" 2>/dev/null; }
expect() { # desc, hook, payload, grep-pattern ("" = expect empty output)
  local out; out="$(run "$2" "$3")"
  if [[ -z "$4" ]]; then
    [[ -z "$out" ]] && { pass=$((pass+1)); echo "  [OK] $1"; } || { fail=$((fail+1)); echo "  [FAIL] $1 — got: ${out:0:120}"; }
  else
    grep -q -- "$4" <<<"$out" && { pass=$((pass+1)); echo "  [OK] $1"; } || { fail=$((fail+1)); echo "  [FAIL] $1 — got: ${out:0:120}"; }
  fi
}

echo "guard"
expect "deny sonnet sub-agent"   guard.sh '{"tool_name":"Agent","tool_input":{"subagent_type":"x","model":"sonnet"}}' '"permissionDecision":"deny"'
expect "deny haiku via Task"     guard.sh '{"tool_name":"Task","tool_input":{"model":"claude-haiku-4-5"}}' 'deny'
expect "allow opus"              guard.sh '{"tool_name":"Agent","tool_input":{"model":"opus"}}' ''
expect "allow no model"          guard.sh '{"tool_name":"Agent","tool_input":{"subagent_type":"explorer"}}' ''
expect "top-level model ignored" guard.sh '{"model":"sonnet","tool_name":"Agent","tool_input":{"model":"opus"}}' ''
expect "deny Read .env"          guard.sh '{"tool_name":"Read","tool_input":{"file_path":"/p/.env"}}' 'deny'
expect "deny Edit .env.production (win path)" guard.sh '{"tool_name":"Edit","tool_input":{"file_path":"C:\p\.env.production"}}' 'deny'
expect "allow .env.example"      guard.sh '{"tool_name":"Write","tool_input":{"file_path":"/p/.env.example"}}' ''
expect "allow .envrc-like names" guard.sh '{"tool_name":"Read","tool_input":{"file_path":"/p/src/env.ts"}}' ''
expect "deny cat .env"           guard.sh '{"tool_name":"Bash","tool_input":{"command":"cat .env"}}' 'deny'
expect "deny git add .env.local" guard.sh '{"tool_name":"Bash","tool_input":{"command":"git add app/.env.local"}}' 'deny'
expect "allow cp .env.example x" guard.sh '{"tool_name":"Bash","tool_input":{"command":"diff .env.example .env.template"}}' ''
expect "allow process.env"       guard.sh '{"tool_name":"Bash","tool_input":{"command":"node -e \"console.log(process.env.HOME)\""}}' ''
expect "allow unrelated tool"    guard.sh '{"tool_name":"Glob","tool_input":{"pattern":"**/.env"}}' ''

echo "prompt-router"
expect "UI prompt → ui checklist"      prompt-router.sh '{"session_id":"a1","prompt":"Make the login screen responsive"}' 'ui-ux'
expect "same topic not repeated"       prompt-router.sh '{"session_id":"a1","prompt":"tweak the button color"}' ''
expect "SEO prompt → seo checklist"    prompt-router.sh '{"session_id":"a2","prompt":"add meta description and sitemap"}' 'Load skill: seo'
expect "pattern prompt → gate"         prompt-router.sh '{"session_id":"a3","prompt":"Should we add a factory here?"}' 'design-patterns'
expect "design pattern ≠ UI"           prompt-router.sh '{"session_id":"a4","prompt":"which design pattern fits?"}' 'design-patterns'
out="$(run prompt-router.sh '{"session_id":"a5","prompt":"which design pattern fits?"}')"
grep -q 'ui-ux' <<<"$out" && { fail=$((fail+1)); echo "  [FAIL] design pattern prompt injected UI"; } || { pass=$((pass+1)); echo "  [OK] design pattern prompt has no UI checklist"; }
expect "plain prompt → nothing"        prompt-router.sh '{"session_id":"a6","prompt":"what does this function return?"}' ''
expect "valid JSON escaping"           prompt-router.sh '{"session_id":"a7","prompt":"fix \"auth\" token\nflow"}' '"additionalContext":"Harness'

echo "file-context"
expect "new .tsx → ui"       file-context.sh '{"session_id":"b1","tool_name":"Write","tool_input":{"file_path":"/p/src/components/Card.tsx"}}' 'ui-ux'
expect "robots.txt → seo"    file-context.sh '{"session_id":"b2","tool_name":"Write","tool_input":{"file_path":"/p/public/robots.txt"}}' 'seo'
expect "auth route → security" file-context.sh '{"session_id":"b3","tool_name":"Edit","tool_input":{"file_path":"/p/src/auth/login.ts"}}' 'security'
expect "plain .go → nothing" file-context.sh '{"session_id":"b4","tool_name":"Edit","tool_input":{"file_path":"/p/internal/math/add.go"}}' ''

echo "session-start"
expect "summary without lock warns" session-start.sh '{"session_id":"c1","source":"startup"}' 'lock is missing'
printf 'harness_version\t9.9.9\nprofiles\tweb\nmanaged\tx\t1\th\tkept-local\n' > "$P/.claude/harness/lock"
expect "reads version"      session-start.sh '{"session_id":"c1"}' 'v9.9.9'
expect "reports kept-local" session-start.sh '{"session_id":"c1"}' 'kept-local'
run prompt-router.sh '{"session_id":"c2","prompt":"style the navbar"}' >/dev/null
run session-start.sh '{"session_id":"c2","source":"compact"}' >/dev/null
expect "compact resets dedupe" prompt-router.sh '{"session_id":"c2","prompt":"style the navbar"}' 'ui-ux'

echo "post-edit-lint"
printf 'if [ x\n' > "$P/bad.sh"
expect "bash syntax error reported" post-edit-lint.sh "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$P/bad.sh\"}}" 'bash -n'
printf 'echo ok\n' > "$P/good.sh"
expect "clean file → nothing" post-edit-lint.sh "{\"tool_name\":\"Write\",\"tool_input\":{\"file_path\":\"$P/good.sh\"}}" ''

echo "JSON validity"
if PY="$(command -v python3 || command -v python)"; then
  bad=0
  for pl in '{"tool_name":"Agent","tool_input":{"model":"sonnet"}}' '{"session_id":"z","prompt":"UI \ back\"slash"}'; do
    for h in guard.sh prompt-router.sh; do
      o="$(run "$h" "$pl")"; [[ -z "$o" ]] && continue
      "$PY" -c 'import json,sys; json.loads(sys.stdin.read())' <<<"$o" || bad=1
    done
  done
  [[ $bad -eq 0 ]] && { pass=$((pass+1)); echo "  [OK] hook output parses as JSON"; } || { fail=$((fail+1)); echo "  [FAIL] invalid JSON output"; }
fi

echo "performance"
start=$(date +%s%N 2>/dev/null || echo 0)
for _ in 1 2 3 4 5 6 7 8 9 10; do run guard.sh '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' >/dev/null; done
end=$(date +%s%N 2>/dev/null || echo 0)
if [[ "$start" != 0 && "$start" != *N ]]; then
  ms=$(( (end - start) / 10000000 ))
  # Informational only: shared CI runners are noisy. Correctness is asserted above.
  if [[ $ms -lt 300 ]]; then echo "  [OK] guard avg ${ms}ms (<300ms incl. bash startup)"
  else echo "  [WARN] guard avg ${ms}ms (>300ms; slow or busy runner?)"; fi
fi

echo; echo "hook tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
