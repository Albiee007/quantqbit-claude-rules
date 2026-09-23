#!/usr/bin/env bash
# === harness validator ===
# Static checks on the harness source (harness/) that keep vendored content
# safe, small and policy-compliant. Run in CI and before every release.
#
#   model      every agent is model: opus; no sonnet/haiku/fable model keys;
#              base settings force Opus sub-agents
#   frontmatter agents: name == file, description, tools, model
#              skills: name == folder, description with a "Use when" clause,
#              only known keys (catches typos such as user-invokable)
#              rules: only 00-core.md may omit paths:
#   budgets    core <= 150 lines, SKILL.md <= 250, rules <= 100, snippets <= 15
#   hygiene    LF only, no absolute user paths, no .venv/__pycache__,
#              no harness:managed marker in source (sync injects it),
#              every relative markdown link resolves
#   syntax     bash -n (+ shellcheck if installed), JSON parses
#   release    VERSION == plugin.json == marketplace.json == CHANGELOG head;
#              manifest.tsv up to date
# Usage: bash scaffold/lib/validate-harness.sh [--no-release]
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
H="$ROOT/harness"
# shellcheck source=../../harness/bin/harness-lib.sh
source "$H/bin/harness-lib.sh"
check_release=1; [[ "${1:-}" == "--no-release" ]] && check_release=0

errors=0
e() { hc_fail "$*"; errors=$((errors + 1)); }

fm() { # file -> frontmatter body (between the first two --- lines)
  awk 'NR == 1 && !/^---\r?$/ { exit } NR == 1 { next } /^---\r?$/ { exit } { print }' "$1"
}
fm_key() { fm "$1" | awk -v k="$2" -F': *' '$1 == k { sub(/^[^:]*: */, ""); print; exit }'; }

# ------------------------------------------------------------------ model
for f in "$H"/agents/*.md; do
  n="$(basename "$f" .md)"
  [[ "$(fm_key "$f" name)" == "$n" ]] || e "agent $n: frontmatter name must equal file name"
  [[ -n "$(fm_key "$f" description)" ]] || e "agent $n: missing description"
  [[ -n "$(fm_key "$f" tools)" ]] || e "agent $n: missing tools allow-list"
  [[ "$(fm_key "$f" model)" == "opus" ]] || e "agent $n: model must be 'opus' (got '$(fm_key "$f" model)')"
done
while IFS= read -r hit; do
  e "non-Opus model reference: $hit"
done < <(grep -rnE '^[[:space:]]*"?model"?[[:space:]]*[:=][[:space:]]*"?(sonnet|haiku|fable|claude-(sonnet|haiku|fable))' \
           "$H" --include='*.md' --include='*.json' --include='*.sh' 2>/dev/null || true)
grep -q '"CLAUDE_CODE_SUBAGENT_MODEL": "opus"' "$H/settings.base.json" || e "settings.base.json must set CLAUDE_CODE_SUBAGENT_MODEL=opus"
grep -q '"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"' "$H/settings.base.json" || e "settings.base.json must set CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1"

# ------------------------------------------------------------------ skills
SKILL_KEYS=" name description when_to_use argument-hint arguments allowed-tools disallowed-tools paths user-invocable disable-model-invocation license compatibility metadata effort context agent "
for d in "$H"/skills/*/ "$ROOT"/skills/*/; do
  [[ -d "$d" ]] || continue
  s="$d/SKILL.md"; n="$(basename "$d")"
  [[ -f "$s" ]] || { e "skill $n: missing SKILL.md"; continue; }
  [[ "$(fm_key "$s" name)" == "$n" ]] || e "skill $n: frontmatter name must equal folder name"
  desc="$(fm_key "$s" description)"
  [[ -n "$desc" ]] || e "skill $n: missing description"
  [[ "$desc" == *"Use when"* || "$desc" == *"use when"* ]] || e "skill $n: description needs a 'Use when …' clause"
  [[ ${#desc} -le 1024 ]] || e "skill $n: description is ${#desc} chars (max 1024)"
  while IFS= read -r k; do
    [[ -z "$k" ]] && continue
    [[ "$SKILL_KEYS" == *" $k "* ]] || e "skill $n: unknown frontmatter key '$k'"
  done < <(fm "$s" | awk -F':' '/^[A-Za-z_-]+:/ { print $1 }')
  [[ -z "$(fm_key "$s" model)" ]] || e "skill $n: do not set model in skills"
  lines=$(wc -l < "$s"); [[ $lines -le 250 ]] || e "skill $n: SKILL.md is $lines lines (max 250)"
done

# ------------------------------------------------------------------ rules / budgets
core="$H/core/00-core.md"
lines=$(wc -l < "$core"); [[ $lines -le 150 ]] || e "core/00-core.md is $lines lines (max 150)"
[[ -z "$(fm "$core")" ]] || e "core/00-core.md must have no frontmatter (it loads unconditionally)"
for f in "$H"/rules/*.md; do
  n="$(basename "$f")"
  fm "$f" | grep -q '^paths:' || e "rules/$n: must declare paths: (only core/00-core.md loads unconditionally)"
  lines=$(wc -l < "$f"); [[ $lines -le 100 ]] || e "rules/$n is $lines lines (max 100)"
done
for f in "$H"/snippets/*.md; do
  lines=$(wc -l < "$f"); [[ $lines -le 15 ]] || e "snippets/$(basename "$f") is $lines lines (max 15)"
done

# ------------------------------------------------------------------ hygiene
# awk -v BINMODE=3, not grep: MSYS grep/awk read in text mode and hide CRs.
# BINMODE makes gawk read raw bytes; other awks ignore it.
while IFS= read -r f; do e "CRLF line endings: ${f#"$ROOT"/}"; done \
  < <(find "$H" "$ROOT/skills" "$ROOT/scaffold/sync.sh" "$ROOT/scaffold/lib" -type f \
        \( -name '*.md' -o -name '*.sh' -o -name '*.json' -o -name '*.tsv' -o -name '*.py' \) 2>/dev/null \
      | while IFS= read -r f; do awk -v BINMODE=3 '/\r/ { print FILENAME; exit }' "$f"; done)
while IFS= read -r hit; do e "absolute user path: $hit"; done \
  < <(grep -rnIE '[A-Za-z]:\\\\?Users\\\\?[A-Za-z]|/Users/[a-z][a-z0-9_-]+/|/home/[a-z][a-z0-9_-]+/' "$H" "$ROOT/skills" 2>/dev/null \
        | grep -vE '/home/user/|/Users/you/|/home/<' || true)
while IFS= read -r f; do e "junk in harness: ${f#"$ROOT"/}"; done \
  < <(find "$H" \( -name .venv -o -name __pycache__ -o -name node_modules -o -name '*.pyc' \) 2>/dev/null)
while IFS= read -r f; do e "source file must not carry a harness:managed marker (sync injects it): ${f#"$ROOT"/}"; done \
  < <(grep -rl 'harness:managed v[0-9]' "$H" --include='*.md' --include='*.sh' --include='*.ps1' 2>/dev/null \
        | grep -v '/bin/harness-lib.sh$' || true)
# relative markdown links
while IFS= read -r f; do
  dir="$(dirname "$f")"
  while IFS= read -r link; do
    target="${link%%#*}"
    [[ -z "$target" ]] && continue
    [[ -e "$dir/$target" ]] || e "broken link in ${f#"$ROOT"/}: $link"
  done < <(awk '/^[[:space:]]*```/ { c = !c; next } !c' "$f" | sed -E 's/`[^`]*`//g' \
             | grep -oE '\]\([^)[:space:]]+\)' | sed -E 's/^\]\(//; s/\)$//' \
             | grep -vE '^(https?:|mailto:|#|/|\$|<)' || true)
done < <(find "$H" "$ROOT/skills" -name '*.md' 2>/dev/null)

# ------------------------------------------------------------------ syntax
while IFS= read -r f; do
  bash -n "$f" 2>/dev/null || e "bash syntax error: ${f#"$ROOT"/}"
done < <(find "$H" "$ROOT/scaffold" "$ROOT/tests" -name '*.sh' 2>/dev/null)
if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    shellcheck -S warning -x "$f" >/dev/null 2>&1 || e "shellcheck warnings: ${f#"$ROOT"/} (run: shellcheck -x $f)"
  done < <(find "$H" "$ROOT/scaffold/sync.sh" "$ROOT/scaffold/lib/release.sh" "$ROOT/scaffold/lib/validate-harness.sh" -name '*.sh' 2>/dev/null)
else
  hc_warn "shellcheck not installed — skipped (CI runs it)"
fi
if hc_python >/dev/null; then
  while IFS= read -r f; do
    hc_py -c 'import json,sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$f" 2>/dev/null || e "invalid JSON: ${f#"$ROOT"/}"
  done < <(find "$H" "$ROOT/.claude-plugin" -name '*.json' 2>/dev/null)
else
  hc_warn "python not found — JSON parse checks skipped"
fi

# ------------------------------------------------------------------ release consistency
if [[ $check_release -eq 1 ]]; then
  v="$(tr -d '[:space:]' < "$ROOT/VERSION")"
  grep -q "\"version\": \"$v\"" "$ROOT/.claude-plugin/plugin.json" || e "plugin.json version != VERSION ($v)"
  # Version lives in plugin.json only (a marketplace entry version would silently
  # lose to it and drift).
  grep -q '"version"' "$ROOT/.claude-plugin/marketplace.json" 2>/dev/null \
    && e "marketplace.json must not set a plugin version (keep it in plugin.json)"
  # Claude Code's manifest schema: repository is a string (an npm-style object
  # makes 'claude plugin install' fail for everyone).
  grep -qE '"repository"[[:space:]]*:[[:space:]]*"' "$ROOT/.claude-plugin/plugin.json" \
    || e "plugin.json repository must be a string URL"
  if command -v claude >/dev/null 2>&1; then
    vcfg="$(mktemp -d "${TMPDIR:-/tmp}/harness-validate-cfg.XXXXXX")"
    for m in "$ROOT" "$ROOT/.claude-plugin/plugin.json"; do
      CLAUDE_CONFIG_DIR="$vcfg" claude plugin validate --strict "$m" >"$vcfg/out" 2>&1 \
        || { e "claude plugin validate --strict ${m#"$ROOT"} failed:"; sed 's/^/    /' "$vcfg/out" >&2; }
    done
    rm -rf "$vcfg"
  else
    hc_warn "claude CLI not found — 'claude plugin validate' skipped"
  fi
  head_v="$(grep -m1 -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' "$ROOT/CHANGELOG.md" 2>/dev/null | tr -d '#[] ')"
  [[ "$head_v" == "$v" ]] || e "CHANGELOG.md top entry ($head_v) != VERSION ($v)"
  bash "$ROOT/scaffold/lib/release.sh" --check >/dev/null 2>&1 || e "harness/manifest.tsv is stale — run: bash scaffold/lib/release.sh"
fi

if [[ $errors -gt 0 ]]; then
  hc_fail "validate-harness: $errors problem(s)"
  exit 1
fi
hc_ok "validate-harness: all checks passed"
