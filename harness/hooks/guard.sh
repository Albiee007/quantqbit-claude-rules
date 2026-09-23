#!/usr/bin/env bash
# === harness guard (PreToolUse) ===
# Blocks, deterministically:
#   1. Agent/Task calls that request a non-Opus model (harness Opus policy).
#   2. Read/Edit/Write of real .env files (.env, .env.local, .env.production…).
#      Allowed: .env.example, .env.template, .env.sample, .env.dist, .env.defaults.
#   3. Bash commands that reference a real .env file.
# Never fails open with an error: any parsing miss simply allows the call.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload

ENV_OK_RE='^\.env\.(example|template|sample|dist|defaults|schema)$|\.example$|\.template$|\.sample$'

is_secret_env_name() { # basename
  local b="$1"
  [[ "$b" == ".env" || "$b" == .env.* ]] || return 1
  [[ "$b" =~ $ENV_OK_RE ]] && return 1
  return 0
}

hh_get tool_name; tool="$HH_V"

case "$tool" in
  Agent|Task)
    hh_get model "$HH_TI"; model="$HH_V"
    if [[ -n "$model" && "$model" != "inherit" ]]; then
      shopt -s nocasematch
      if [[ ! "$model" =~ opus ]]; then
        hh_deny "Harness policy: sub-agents must run on Opus. Re-issue this Agent call with model \"opus\" (requested: \"$model\")."
      fi
    fi
    ;;
  Read|Edit|Write|MultiEdit|NotebookEdit)
    hh_get file_path "$HH_TI"; p="$HH_V"
    if [[ -z "$p" ]]; then hh_get notebook_path "$HH_TI"; p="$HH_V"; fi
    p="${p//\\//}"
    base="${p##*/}"
    if [[ -n "$base" ]] && is_secret_env_name "$base"; then
      hh_deny "Harness policy: .env files hold secrets and are never read or modified by agents (tried: $base). Use .env.example, or ask the user."
    fi
    ;;
  Bash)
    hh_get command "$HH_TI"; cmd="$HH_V"
    rest="$cmd"
    re='(^|[[:space:]/=\"'"'"'<>:])(\.env(\.[A-Za-z0-9_.-]+)?)($|[[:space:]\"'"'"';|&)>])'
    while [[ "$rest" =~ $re ]]; do
      name="${BASH_REMATCH[2]}"
      if is_secret_env_name "$name"; then
        hh_deny "Harness policy: this command touches a secret .env file ($name). Agents never read, copy, stage or modify .env files. Ask the user to do it."
      fi
      rest="${rest#*"${BASH_REMATCH[0]}"}"
    done
    ;;
esac
exit 0
