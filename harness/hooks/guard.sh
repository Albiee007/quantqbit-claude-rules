#!/usr/bin/env bash
# === harness guard (PreToolUse) ===
# Blocks, deterministically (best-effort pattern matching, case-insensitive):
#   1. Agent/Task calls that request a non-Opus model (harness Opus policy).
#   2. Read/Edit/Write/NotebookEdit of real .env files (.env, .env.local,
#      .env.staging, .ENV …) and Grep calls whose path/glob targets them.
#      Allowed: .env.example, .env.template, .env.sample, .env.dist, .env.defaults.
#   3. Bash/PowerShell commands that name a real .env file or a .env* glob.
#      Exclusion arguments (--exclude=.env*, -g '!.env') and read-only metadata
#      commands (ls, stat, test, git status/check-ignore/ls-files) are allowed.
# It cannot see indirect reads (grep -r ., find -exec cat …): keep .env* files
# gitignored. Any parsing miss simply allows the call.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload
shopt -s nocasematch

ENV_OK_RE='^\.env\.(example|template|sample|dist|defaults|schema)$|\.example$|\.template$|\.sample$'

is_secret_env_name() { # basename
  local b="$1"
  [[ "$b" == .env* ]] || return 1
  # A glob such as .env* or .env.? may expand to a real .env file.
  [[ "$b" == *[\*\?\[]* ]] && return 0
  [[ "$b" == ".env" || "$b" == .env.* ]] || return 1
  [[ "$b" =~ $ENV_OK_RE ]] && return 1
  return 0
}

deny_path() { # path, tool label
  local p="$1" base
  p="${p//\\//}"
  base="${p##*/}"
  base="${base%%:*}"                                  # NTFS stream suffix (.env:x)
  while [[ "$base" == *[.\ ] ]]; do base="${base%?}"; done   # Windows drops trailing dots/spaces
  if [[ -n "$base" ]] && is_secret_env_name "$base"; then
    hh_deny "Harness policy: .env files hold secrets and are never read or modified by agents (tried: $base via $2). Use .env.example, or ask the user."
  fi
}

hh_get tool_name; tool="$HH_V"

case "$tool" in
  Agent|Task)
    hh_get model "$HH_TI"; model="$HH_V"
    if [[ -n "$model" && "$model" != "inherit" && ! "$model" =~ opus ]]; then
      hh_deny "Harness policy: sub-agents must run on Opus. Re-issue this Agent call with model \"opus\" (requested: \"$model\")."
    fi
    ;;
  Read|Edit|Write|MultiEdit|NotebookEdit)
    hh_get file_path "$HH_TI"; p="$HH_V"
    if [[ -z "$p" ]]; then hh_get notebook_path "$HH_TI"; p="$HH_V"; fi
    deny_path "$p" "$tool"
    ;;
  Grep)
    hh_get path "$HH_TI"; deny_path "$HH_V" "Grep path"
    hh_get glob "$HH_TI"; deny_path "$HH_V" "Grep glob"
    ;;
  Bash|PowerShell)
    hh_get command "$HH_TI"; cmd="$HH_V"
    cmd="${cmd//\\//}"
    # Read-only metadata commands (ls, stat, test, git status/check-ignore/ls-files,
    # Test-Path, Get-Item, Get-ChildItem) may name .env files: they reveal
    # existence, not content. The exemption applies per command segment: split on
    # newline, ;, &&, || and &. If the command pipes, redirects, groups or
    # substitutes anything, nothing is exempt and the whole command is scanned.
    meta_re='^[[:space:]]*(ls|dir|stat|test|\[|git[[:space:]]+(status|check-ignore|ls-files)|Test-Path|Get-Item|Get-ChildItem)([[:space:]]|$)'
    NL=$'\n'
    segs="$cmd"
    segs="${segs//&&/$NL}"; segs="${segs//||/$NL}"; segs="${segs//;/$NL}"
    segs="${segs//&/$NL}"; segs="${segs//$'\r'/$NL}"
    grouped='[|`<>(){}]'
    if [[ "$segs" =~ $grouped || "$cmd" == *'$('* ]]; then
      scan="$cmd"
    else
      scan=""
      while IFS= read -r seg || [[ -n "$seg" ]]; do
        [[ "$seg" =~ $meta_re ]] || scan+=" $seg$NL"
      done <<< "$segs"
    fi
    # Drop exclusion arguments before scanning, so safe searches are not blocked.
    excl_re="(--exclude(-dir)?[= ]|--iglob[= ]!|--glob[= ]!|-g[= ]!|:\\(exclude\\)|:!)['\"]?!?[^[:space:]'\"]*['\"]?"
    rest="$scan"
    while [[ "$rest" =~ $excl_re ]]; do
      rest="${rest/"${BASH_REMATCH[0]}"/ }"
    done
    re='(^|[[:space:]/=\"'"'"'<>:,({])(\.env([.*?[][A-Za-z0-9_.*?[-]*)?)($|[[:space:]\"'"'"';|&)>,}:])'
    while [[ "$rest" =~ $re ]]; do
      name="${BASH_REMATCH[2]}"
      if is_secret_env_name "$name"; then
        hh_deny "Harness policy: this command touches a secret .env file ($name). Agents never read, copy, stage or modify .env files. Existence checks (ls, test, git check-ignore) are allowed as their own command, not piped or grouped. Ask the user for anything else."
      fi
      rest="${rest#*"${BASH_REMATCH[0]}"}"
    done
    ;;
esac
exit 0
