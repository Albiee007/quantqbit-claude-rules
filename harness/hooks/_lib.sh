# shellcheck shell=bash
# === harness hook library ===
# Sourced by every harness hook. The hot path uses pure bash built-ins and NO
# command substitutions: each $(...) forks, which costs ~20 ms on Windows Git
# Bash. Functions therefore return values in HH_V instead of printing them.
# Bash 3.2 compatible.

HH_DIR="${BASH_SOURCE[0]%/*}"
[[ "$HH_DIR" == "${BASH_SOURCE[0]}" ]] && HH_DIR="."
HH_ROOT="${CLAUDE_PROJECT_DIR:-$HH_DIR/../../..}"
HH_SNIPPETS="$HH_ROOT/.claude/harness/snippets"
HH_PAYLOAD=""
HH_TI=""
HH_V=""

# hh_read_payload — slurp the hook JSON from stdin (builtin read, no cat), and
# split out the text from "tool_input" onward into HH_TI so that keys such as
# "model" / "file_path" resolve inside tool_input.
hh_read_payload() {
  IFS= read -r -d '' HH_PAYLOAD || true
  HH_TI="${HH_PAYLOAD#*\"tool_input\"}"
  [[ "$HH_TI" == "$HH_PAYLOAD" ]] && HH_TI=""
  return 0
}

# hh_get <key> [haystack] — sets HH_V to the first string value for "key"
# (JSON-unescaped), or empty. The default haystack is the whole payload.
hh_get() {
  local k="$1" hay="${2-$HH_PAYLOAD}" bs='\'
  local re="\"$k\"[[:space:]]*:[[:space:]]*\"(([^\"\\\\]|\\\\.)*)\""
  HH_V=""
  [[ "$hay" =~ $re ]] || return 0
  HH_V="${BASH_REMATCH[1]}"
  HH_V="${HH_V//\\\\/$'\x01'}"
  HH_V="${HH_V//\\\"/\"}"
  HH_V="${HH_V//\\\//\/}"
  HH_V="${HH_V//\\n/$'\n'}"
  HH_V="${HH_V//\\t/$'\t'}"
  HH_V="${HH_V//\\r/}"
  HH_V="${HH_V//$'\x01'/$bs}"
}

# hh_json_escape <text> — sets HH_V to text escaped for a JSON string value.
hh_json_escape() {
  HH_V="$1"
  HH_V="${HH_V//\\/\\\\}"
  HH_V="${HH_V//\"/\\\"}"
  HH_V="${HH_V//$'\r'/}"
  HH_V="${HH_V//$'\t'/\\t}"
  HH_V="${HH_V//$'\n'/\\n}"
}

# hh_emit_context <event> <text> — add text to Claude's context.
hh_emit_context() {
  [[ -z "$2" ]] && return 0
  hh_json_escape "$2"
  printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$1" "$HH_V"
}

# hh_deny <reason> — PreToolUse: block the tool call with a reason, then exit.
hh_deny() {
  hh_json_escape "$1"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$HH_V"
  exit 0
}

# hh_marker_prefix — sets HH_V to the per-session dedupe marker prefix.
hh_marker_prefix() {
  hh_get session_id
  local sid="${HH_V//[^A-Za-z0-9_-]/}"
  HH_V="${TMPDIR:-/tmp}/claude-harness-${sid:-nosession}-"
}

# HH_OUT accumulates snippet text; hh_add_snippet <topic> appends a topic's
# snippet at most once per session.
HH_OUT=""
hh_add_snippet() {
  local topic="$1" f m line body=""
  f="$HH_SNIPPETS/$topic.md"
  [[ -f "$f" ]] || return 0
  hh_marker_prefix
  m="$HH_V$topic"
  [[ -e "$m" ]] && return 0
  : > "$m" 2>/dev/null || true
  while IFS= read -r line || [[ -n "$line" ]]; do
    body+="${line%$'\r'}"$'\n'
  done < "$f"
  HH_OUT+="$body"$'\n'
}
