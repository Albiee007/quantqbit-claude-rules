#!/usr/bin/env bash
# === harness guard (PreToolUse) ===
# Blocks, deterministically (best-effort pattern matching, case-insensitive):
#   1. Agent/Task calls that request a non-Opus model (harness Opus policy).
#   2. Read/Edit/Write/NotebookEdit of real .env files (.env, .env.local,
#      .env.staging, .ENV …) and Grep calls whose path/glob targets them.
#      Allowed: .env.example, .env.template, .env.sample, .env.dist, .env.defaults,
#      .env.schema and names ending .example/.template/.sample. Core §8 lists
#      the same set; tests/hooks.test.sh keeps the two in step.
#   3. Bash/PowerShell commands that name a real .env file or a .env* glob.
#      Exclusion arguments (--exclude=.env*, -g '!.env') and read-only metadata
#      commands (ls, stat, test, git status/check-ignore/ls-files) are allowed.
#   4. A sub-agent running `direction.py approve`: owner approvals are recorded by
#      the main session after the owner decides (skill creative-direction).
#   5. A sub-agent running `render_video.py generate`: a generation provider (voice,
#      alignment, b-roll) runs only from the main session, when the owner asked for it.
# It cannot see indirect reads (grep -r ., find -exec cat …): keep .env* files
# gitignored. Any parsing miss simply allows the call.
set -uo pipefail
# shellcheck source=_lib.sh
_hd="${BASH_SOURCE[0]%/*}"; [[ "$_hd" == "${BASH_SOURCE[0]}" ]] && _hd=.
source "$_hd/_lib.sh"
hh_read_payload "$@"
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

# The checks run on the normalised operation (_lib.sh hh_normalize): every path
# of a multi-file patch or a move is checked, and a deny on any one denies all.
case "$HH_OP" in
  spawn)
    # The Opus policy is Claude Code's; other agents keep the model their user chose.
    if [[ "$HH_AGENT" == claude ]]; then
      hh_get model "$HH_TI"; model="$HH_V"
      if [[ -n "$model" && "$model" != "inherit" && ! "$model" =~ opus ]]; then
        hh_deny "Harness policy: sub-agents must run on Opus. Re-issue this Agent call with model \"opus\" (requested: \"$model\")."
      fi
    fi
    ;;
  read|write|rename)
    for p in ${HH_PATHS[@]+"${HH_PATHS[@]}"}; do deny_path "$p" "$HH_TOOL"; done
    ;;
  exec)
    cmd="$HH_CMD"
    # Only a known sub-agent is refused; where the agent can't say (unknown), the
    # check is a documented gap (scaffold/targets/SPEC.md), not a guess.
    approve_re='direction\.py[^|;&]*[[:space:]]approve([[:space:]]|$)'
    if [[ "$cmd" =~ $approve_re && "$HH_SUBAGENT" == 1 ]]; then
      hh_deny "Harness: only the main session records owner approvals (direction.py approve), after the owner has decided. Return the decision you need to your parent instead."
    fi
    generate_re="render_video\\.py[^|;&]*[[:space:]][\"']?generate[\"']?([[:space:]]|\$)"
    if [[ "$cmd" =~ $generate_re && "$HH_SUBAGENT" == 1 ]]; then
      hh_deny "Harness: only the main session runs a generation provider (render_video.py generate: voice, alignment, b-roll), after the owner has asked for it; it may cost money and sends the script or prompt to the provider. Return the request to your parent instead."
    fi
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
