# shellcheck shell=bash
# === harness hook library ===
# Sourced by every harness hook. The hot path uses pure bash built-ins and NO
# command substitutions: each $(...) forks, which costs ~20 ms on Windows Git
# Bash. Functions therefore return values in HH_V instead of printing them.
# Bash 3.2 compatible.

HH_DIR="${BASH_SOURCE[0]%/*}"
[[ "$HH_DIR" == "${BASH_SOURCE[0]}" ]] && HH_DIR="."
HH_ROOT="${CLAUDE_PROJECT_DIR:-$HH_DIR/../../..}"
HH_SNIPPETS="$HH_ROOT/.agents/harness/snippets"
# Where this project's harness skills live (named in gate messages relative to the root):
# Claude Code's folder when the claude target is installed, else the shared .agents/skills.
HH_SKILLS_REL=".claude/skills"
[[ ! -d "$HH_ROOT/.claude/skills" && -d "$HH_ROOT/.agents/skills" ]] && HH_SKILLS_REL=".agents/skills"
HH_SKILLS="$HH_ROOT/$HH_SKILLS_REL"
HH_PAYLOAD=""
HH_TI=""
HH_V=""

# The agent that runs the hook: the hook command passes --agent <name> (see
# scaffold/targets/); without it the payload is Claude Code's.
HH_AGENT="claude"
HH_ARG_EVENT=""   # --event: Antigravity's payload does not name its event

# hh_read_payload [--agent NAME] [--event EVENT] — slurp the hook JSON from stdin
# (builtin read, no cat), split out the tool arguments into HH_TI (Claude-style
# "tool_input", or Antigravity's "args") so that keys such as "model" /
# "file_path" resolve inside them, then normalise it (hh_normalize).
hh_read_payload() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --agent) HH_AGENT="${2:-claude}"; shift 2 || shift ;;
      --agent=*) HH_AGENT="${1#*=}"; shift ;;
      --event) HH_ARG_EVENT="${2:-}"; shift 2 || shift ;;
      --event=*) HH_ARG_EVENT="${1#*=}"; shift ;;
      *) shift ;;
    esac
  done
  IFS= read -r -d '' HH_PAYLOAD || true
  local key='"tool_input"'
  [[ "$HH_AGENT" == antigravity ]] && key='"args"'
  HH_TI="${HH_PAYLOAD#*$key}"
  [[ "$HH_TI" == "$HH_PAYLOAD" ]] && HH_TI=""
  hh_normalize
  return 0
}

# The normalised operation, so the policy hooks never depend on one agent's
# tool names or on a single file_path:
#   HH_EVENT      the agent's event name
#   HH_PHASE      before | after | prompt | session | other
#   HH_CAN_BLOCK  1 if this event can still stop the operation, else 0
#   HH_TOOL       the agent's tool name (for messages)
#   HH_OP         read | write | rename | exec | spawn | prompt | "" (other)
#   HH_PATHS      every path the operation touches: each file of a multi-file
#                 patch, both sides of a move, a search path and its glob
#   HH_CMD        the command, for exec
#   HH_SUBAGENT   1 (a sub-agent runs it), 0 (main session), unknown
HH_EVENT=""; HH_PHASE="other"; HH_CAN_BLOCK=0; HH_TOOL=""; HH_OP=""; HH_CMD=""; HH_SUBAGENT="unknown"
HH_PATHS=()

# hh_patch_paths <patch text> — add every file an apply_patch body names
# (*** Add/Update/Delete File:, and *** Move to: for renames) to HH_PATHS.
hh_patch_paths() {
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    case "$line" in
      '*** Add File: '*|'*** Update File: '*|'*** Delete File: '*) HH_PATHS+=("${line#*: }") ;;
      '*** Move to: '*) HH_PATHS+=("${line#*: }"); HH_OP="rename" ;;
    esac
  done <<< "$1"
}

# hh_path_arg <key>… — add the first non-empty tool_input value among the keys.
hh_path_arg() {
  local k
  for k in "$@"; do
    hh_get "$k" "$HH_TI"
    if [[ -n "$HH_V" ]]; then HH_PATHS+=("$HH_V"); return 0; fi
  done
}

# hh_normalize — fill the HH_* operation from the payload. Claude Code, Codex and
# Copilot CLI (PascalCase events) share Claude's event and tool names; Copilot
# keeps its own argument names (path, file_text). Cursor runs the Claude hooks of
# .claude/settings.json with its own payload (cursor_version, preToolUse, Shell);
# it is recognised even without --agent. Other agents get their own branch as
# their adapters land (scaffold/targets/SPEC.md).
hh_normalize() {
  local pre="${HH_PAYLOAD%%\"tool_input\"*}"
  hh_get cursor_version "$pre"; [[ -n "$HH_V" ]] && HH_AGENT="cursor"
  case "$HH_AGENT" in
    gemini) hh_normalize_gemini; return 0 ;;
    antigravity) hh_normalize_antigravity; return 0 ;;
  esac
  hh_get hook_event_name; HH_EVENT="$HH_V"
  case "$HH_EVENT" in
    PreToolUse|preToolUse|beforeShellExecution|beforeReadFile|beforeMCPExecution) HH_PHASE="before"; HH_CAN_BLOCK=1 ;;
    PostToolUse|postToolUse|afterFileEdit|afterShellExecution) HH_PHASE="after" ;;
    UserPromptSubmit|beforeSubmitPrompt|userPromptSubmitted) HH_PHASE="prompt"; HH_OP="prompt" ;;
    SessionStart|sessionStart) HH_PHASE="session" ;;
    "") HH_PHASE="before"; HH_CAN_BLOCK=1 ;;   # a bare tool payload is treated as PreToolUse
  esac
  # Cursor's dedicated events carry their arguments at the top level.
  case "$HH_EVENT" in
    beforeShellExecution|afterShellExecution)
      HH_TOOL="Shell"; HH_OP="exec"; hh_get command; HH_CMD="$HH_V"; return 0 ;;
    beforeReadFile)
      HH_TOOL="Read"; HH_OP="read"; hh_get file_path "$pre"; [[ -n "$HH_V" ]] && HH_PATHS+=("$HH_V"); return 0 ;;
    afterFileEdit)
      HH_TOOL="Write"; HH_OP="write"; hh_get file_path "$pre"; [[ -n "$HH_V" ]] && HH_PATHS+=("$HH_V"); return 0 ;;
  esac
  # The sub-agent marker is read only before tool_input, so a tool argument can't spoof it.
  hh_get agent_id "${HH_PAYLOAD%%\"tool_input\"*}"
  # Claude Code and Codex send agent_id only from a sub-agent; the others send no
  # marker at all (SPEC.md), so their sub-agent checks stay a documented gap.
  case "$HH_AGENT" in
    claude|codex) [[ -n "$HH_V" ]] && HH_SUBAGENT=1 || HH_SUBAGENT=0 ;;
  esac
  hh_get tool_name; HH_TOOL="$HH_V"
  case "$HH_TOOL" in
    Agent|Task|spawn_agent)
      HH_OP="spawn" ;;
    Read|NotebookRead)
      HH_OP="read"; hh_path_arg file_path notebook_path path ;;
    Edit|Write|MultiEdit|NotebookEdit|Delete)
      HH_OP="write"
      hh_path_arg file_path notebook_path path
      # Copilot CLI reports apply_patch as Edit; its body names every file.
      hh_get command "$HH_TI"; [[ "$HH_V" == *'*** Begin Patch'* ]] && hh_patch_paths "$HH_V" ;;
    apply_patch)
      HH_OP="write"; hh_get command "$HH_TI"; hh_patch_paths "$HH_V" ;;
    Grep)  # Glob only lists names (like ls), so it is not an operation on content.
      HH_OP="read"
      hh_get path "$HH_TI"; [[ -n "$HH_V" ]] && HH_PATHS+=("$HH_V")
      hh_get glob "$HH_TI"; [[ -n "$HH_V" ]] && HH_PATHS+=("$HH_V") ;;
    Bash|PowerShell|Shell)
      HH_OP="exec"; hh_get command "$HH_TI"; HH_CMD="$HH_V" ;;
  esac
  return 0
}

# Gemini CLI: BeforeTool/AfterTool/BeforeAgent/SessionStart, its own tool names,
# Claude-style tool_input keys. No sub-agent marker (SPEC.md).
hh_normalize_gemini() {
  hh_get hook_event_name; HH_EVENT="$HH_V"
  case "$HH_EVENT" in
    BeforeTool) HH_PHASE="before"; HH_CAN_BLOCK=1 ;;
    AfterTool) HH_PHASE="after" ;;
    BeforeAgent) HH_PHASE="prompt"; HH_OP="prompt" ;;
    SessionStart) HH_PHASE="session" ;;
  esac
  hh_get tool_name; HH_TOOL="$HH_V"
  case "$HH_TOOL" in
    run_shell_command) HH_OP="exec"; hh_get command "$HH_TI"; HH_CMD="$HH_V" ;;
    read_file) HH_OP="read"; hh_path_arg file_path absolute_path ;;
    read_many_files) HH_OP="read"; hh_json_strings paths "$HH_TI"; hh_json_strings include "$HH_TI" ;;
    write_file|replace) HH_OP="write"; hh_path_arg file_path absolute_path ;;
    grep_search|search_file_content) HH_OP="read"; hh_path_arg dir_path path; hh_path_arg include ;;
  esac
}

# Antigravity: {toolCall:{name, args:{PascalCase}}}; the event comes from the
# hook command (--event), the project from workspacePaths. No sub-agent marker.
hh_normalize_antigravity() {
  HH_EVENT="$HH_ARG_EVENT"
  case "$HH_EVENT" in
    PreToolUse) HH_PHASE="before"; HH_CAN_BLOCK=1 ;;
    PostToolUse) HH_PHASE="after" ;;
    SessionStart) HH_PHASE="session" ;;
    PreInvocation) HH_PHASE="prompt"; HH_OP="prompt" ;;
  esac
  hh_get name "${HH_PAYLOAD#*\"toolCall\"}"; HH_TOOL="$HH_V"
  case "$HH_TOOL" in
    run_command) HH_OP="exec"; hh_get CommandLine "$HH_TI"; HH_CMD="$HH_V" ;;
    view_file) HH_OP="read"; hh_path_arg AbsolutePath ;;
    write_to_file|replace_file_content|multi_replace_file_content) HH_OP="write"; hh_path_arg TargetFile ;;
    grep_search) HH_OP="read"; hh_path_arg SearchPath SearchDirectory ;;
  esac
}

# hh_json_strings <key> <haystack> — add every string of a JSON string array
# ("key": ["a", "b"]) to HH_PATHS.
hh_json_strings() {
  local re="\"$1\"[[:space:]]*:[[:space:]]*\\[([^]]*)\\]" list item
  [[ "$2" =~ $re ]] || return 0
  list="${BASH_REMATCH[1]}"
  while [[ "$list" =~ \"(([^\"\\]|\\.)*)\" ]]; do
    item="${BASH_REMATCH[1]}"
    HH_PATHS+=("${item//\\\\/\\}")
    list="${list#*"${BASH_REMATCH[0]}"}"
  done
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

# hh_emit_context <event> <text> — add text to the agent's context, in the shape
# that agent reads (SPEC.md). Claude Code, Codex, Gemini CLI and Copilot read
# hookSpecificOutput.additionalContext; Cursor reads additional_context (and maps
# hookSpecificOutput for the .claude/settings.json hooks it runs); Antigravity
# injects steps, and only at session start or before an invocation.
hh_emit_context() {
  [[ -z "$2" ]] && return 0
  hh_json_escape "$2"
  case "$HH_AGENT" in
    cursor)
      printf '{"additional_context":"%s","hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$HH_V" "$1" "$HH_V" ;;
    copilot)
      printf '{"additionalContext":"%s","hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$HH_V" "$1" "$HH_V" ;;
    antigravity)
      [[ "$HH_PHASE" == session || "$HH_PHASE" == prompt ]] && printf '{"injectSteps":[{"ephemeralMessage":"%s"}]}\n' "$HH_V" ;;
    *)
      printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$1" "$HH_V" ;;
  esac
  return 0
}

# hh_deny <reason> — block the tool call with a reason, then exit. Cursor and
# Copilot also get exit 2 with the reason on stderr, which both treat as a deny
# whatever the JSON says.
hh_deny() {
  local reason="$1"
  hh_json_escape "$reason"
  case "$HH_AGENT" in
    gemini|antigravity)
      printf '{"decision":"deny","reason":"%s"}\n' "$HH_V"; exit 0 ;;
    cursor)
      printf '{"permission":"deny","user_message":"%s","agent_message":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$HH_V" "$HH_V" "$HH_V"
      printf '%s\n' "$reason" >&2; exit 2 ;;
    copilot)
      printf '{"permissionDecision":"deny","permissionDecisionReason":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$HH_V" "$HH_V"
      printf '%s\n' "$reason" >&2; exit 2 ;;
    *)
      printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$HH_V"
      exit 0 ;;
  esac
}

# hh_marker_prefix — sets HH_V to the per-session dedupe marker prefix.
hh_marker_prefix() {
  hh_get session_id
  local sid="${HH_V//[^A-Za-z0-9_-]/}"
  HH_V="${TMPDIR:-/tmp}/claude-harness-${sid:-nosession}-"
}

# hh_topic_marker <topic> — sets HH_V to the dedupe marker for this topic in
# this agent context. Sub-agents share the parent's session_id but start with
# a fresh context, so the key includes agent_id ("main" on the main thread).
# agent_id is read only from the part of the payload before tool_input, so a
# tool argument can never spoof it.
hh_topic_marker() {
  local aid
  hh_get agent_id "${HH_PAYLOAD%%\"tool_input\"*}"
  aid="${HH_V//[^A-Za-z0-9_-]/}"
  hh_marker_prefix
  HH_V="$HH_V${aid:-main}-$1"
}

# hh_snippet_text <topic> — sets HH_V to the snippet text ("" if none).
hh_snippet_text() {
  local f="$HH_SNIPPETS/$1.md" line body=""
  if [[ -f "$f" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      body+="${line%$'\r'}"$'\n'
    done < "$f"
  fi
  # Snippets name Claude Code's paths; without the claude target the shared copies apply.
  if [[ ! -d "$HH_ROOT/.claude/rules/harness" ]]; then
    body="${body//.claude\/rules\/harness\//.agents/harness/rules/}"
    body="${body//.claude\/skills\//.agents/skills/}"
  fi
  HH_V="$body"
}

# HH_OUT accumulates snippet text; hh_add_snippet <topic> appends a topic's
# snippet at most once per agent context. Returns 1 if it was already shown.
HH_OUT=""
hh_add_snippet() {
  local topic="$1" m
  [[ -f "$HH_SNIPPETS/$topic.md" ]] || return 0
  hh_topic_marker "$topic"; m="$HH_V"
  [[ -e "$m" ]] && return 1
  : > "$m" 2>/dev/null || true
  hh_snippet_text "$topic"
  HH_OUT+="$HH_V"$'\n'
  return 0
}

# hh_config <key> — sets HH_V to KEY=VALUE from .agents/harness.config ("" if unset).
hh_config() {
  local k v line
  HH_V=""
  [[ -f "$HH_ROOT/.agents/harness.config" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" == \#* || "$line" != *=* ]] && continue
    k="${line%%=*}"; v="${line#*=}"
    k="${k//[[:space:]]/}"
    if [[ "$k" == "$1" ]]; then HH_V="${v//[[:space:]]/}"; return 0; fi
  done < "$HH_ROOT/.agents/harness.config"
}
