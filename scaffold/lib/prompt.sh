#!/bin/bash
# ============================================================================
# Prompt Library — collect user input for the scaffold
#
# Drives the interactive flow that fills in PROJECT_NAME, CODE_SUBDIR, and
# the two opt-in deny toggles (destructive ops, push-to-main). Skipped
# entirely when the orchestrator runs in --non-interactive mode.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/prompt.sh"
#   prompt_collect
#   echo "$PROJECT_NAME $CODE_SUBDIR $OPT_IN_DESTRUCTIVE $OPT_IN_PUSH_MAIN"
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# prompt_yes_no — read a y/N answer and normalise to "y" or "n"
# Args: $1 = prompt text, $2 = default ("y" or "n")
# Echoes the normalised answer.
# ----------------------------------------------------------------------------
prompt_yes_no() {
  local question="$1"
  local default="$2"
  local hint="[y/N]"
  [[ "$default" == "y" ]] && hint="[Y/n]"

  local reply
  read -r -p "${question} ${hint} " reply
  reply="${reply:-$default}"
  # Fix E9: accept any case-variant of yes (Yes, yEs, YES, y, Y, ...). The
  # previous explicit list missed mixed-case answers.
  case "$reply" in
    [Yy]|[Yy][Ee][Ss]) echo "y" ;;
    *)                 echo "n" ;;
  esac
}

# ----------------------------------------------------------------------------
# prompt_collect — gather scaffold inputs interactively
# Sets PROJECT_NAME, CODE_SUBDIR, OPT_IN_DESTRUCTIVE, OPT_IN_PUSH_MAIN.
# Loops until the user confirms the entered values.
# ----------------------------------------------------------------------------
prompt_collect() {
  while true; do
    echo ""
    echo "[INFO] Tell us about your project:"

    # Project name (required)
    while true; do
      read -r -p "  Project name: " PROJECT_NAME
      # Fix E9: strip leading/trailing whitespace so trailing spaces don't
      # leak into rendered files. A pure-whitespace answer becomes "" and
      # re-prompts.
      PROJECT_NAME="$(printf '%s' "$PROJECT_NAME" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
      if [[ -n "$PROJECT_NAME" ]]; then
        break
      fi
      echo "[WARN] Project name cannot be empty."
    done

    # Code subdir (default ./)
    read -r -p "  Code subdir [./]: " CODE_SUBDIR
    CODE_SUBDIR="${CODE_SUBDIR:-./}"

    # Opt-in: destructive ops
    OPT_IN_DESTRUCTIVE="$(prompt_yes_no \
      "  Block 'terraform destroy', 'docker system prune', 'rm -rf /'?" "n")"

    # Opt-in: push to main/master
    OPT_IN_PUSH_MAIN="$(prompt_yes_no \
      "  Block 'git push *main*' and 'git push *master*'?" "n")"

    # Confirmation
    echo ""
    echo "[INFO] You entered:"
    echo "    PROJECT_NAME       = ${PROJECT_NAME}"
    echo "    CODE_SUBDIR        = ${CODE_SUBDIR}"
    echo "    OPT_IN_DESTRUCTIVE = ${OPT_IN_DESTRUCTIVE}"
    echo "    OPT_IN_PUSH_MAIN   = ${OPT_IN_PUSH_MAIN}"

    local confirmed
    confirmed="$(prompt_yes_no "  Looks good?" "y")"
    if [[ "$confirmed" == "y" ]]; then
      break
    fi
    echo "[INFO] Let's try again."
  done

  export PROJECT_NAME CODE_SUBDIR OPT_IN_DESTRUCTIVE OPT_IN_PUSH_MAIN
}
