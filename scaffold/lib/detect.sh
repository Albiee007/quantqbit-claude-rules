#!/bin/bash
# ============================================================================
# Stack Detection Library — auto-detect what's in a target workspace
#
# Walks a target directory and sets DETECTED_* flags + CITATION_* exemplar
# paths for each stack the scaffold understands: bash, ansible, docker
# compose, terraform.
#
# All detection is best-effort — we never fail; missing matches just produce
# DETECTED_*=false and a graceful placeholder citation string.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/detect.sh"
#   detect_stacks "/path/to/target"
#   echo "$DETECTED_BASH $CITATION_BASH"
# ============================================================================

set -euo pipefail

# Exported by detect_stacks
DETECTED_BASH="false"
DETECTED_ANSIBLE="false"
DETECTED_COMPOSE="false"
DETECTED_TERRAFORM="false"

CITATION_PLACEHOLDER="see your project's primary script library"
CITATION_BASH="${CITATION_PLACEHOLDER}"
CITATION_ANSIBLE="${CITATION_PLACEHOLDER}"
CITATION_COMPOSE="${CITATION_PLACEHOLDER}"
CITATION_TERRAFORM="${CITATION_PLACEHOLDER}"

# ----------------------------------------------------------------------------
# _detect_prune_args — print the shared find prune expression to stdout
# Fix E8: hoisted out of the two callsites so the prune list lives in one
# place. Matches common vendored / cache / build dirs at ANY depth (using
# -path '*/name' rather than './name' so nested matches are also skipped).
# ----------------------------------------------------------------------------
_detect_prune_args() {
  printf '%s' "\
    \( \
         -path '*/.git' \
      -o -path '*/node_modules' \
      -o -path '*/.cache' \
      -o -path '*/.venv' \
      -o -path '*/venv' \
      -o -path '*/.claude/worktrees' \
      -o -path '*/dist' \
      -o -path '*/build' \
      -o -path '*/.tox' \
      -o -path '*/__pycache__' \
      -o -path '*/target' \
      -o -path '*/vendor' \
      -o -path '*/.terraform' \
      -o -path '*/.next' \
      -o -path '*/.nuxt' \
      -o -path '*/coverage' \
    \) -prune -o"
}

# ----------------------------------------------------------------------------
# detect_first_match — find the first file matching a name pattern, relative
# Args: $1 = name pattern (find -name)
# Echoes the relative path of the first hit, or empty.
# Fix E7: run inside a subshell so cwd auto-restores on exit (vs the old
# pushd/popd dance which was skipped on any non-zero step).
# ----------------------------------------------------------------------------
detect_first_match() {
  local pattern="$1"
  # NB: _detect_prune_args is interpolated unquoted because the inner -path
  # tokens must be re-tokenised by the shell.
  # shellcheck disable=SC2046
  find . $(_detect_prune_args) \
    -type f -name "$pattern" -print 2>/dev/null \
    | head -n1 \
    | sed 's|^\./||'
}

# ----------------------------------------------------------------------------
# detect_dir_exists — true if a relative dir exists under cwd
# ----------------------------------------------------------------------------
detect_dir_exists() {
  [[ -d "$1" ]]
}

# ----------------------------------------------------------------------------
# detect_stacks — populate DETECTED_* and CITATION_* for the given target dir
#
# Fix E7: each probe runs inside a `( cd "$target"; ... )` subshell so cwd
# is auto-restored on any exit path. The previous pushd/popd dance was
# skipped on any non-zero step inside.
#
# Fix E8: single find walk that emits every candidate file in one pass. The
# loop body sorts each file into the right bucket and records the FIRST hit
# per stack as the citation. Uses process substitution (< <(...)) so the
# while-loop body runs in the parent shell — a regular pipeline would put
# the body in a subshell and the var assignments would vanish.
# ----------------------------------------------------------------------------
detect_stacks() {
  local target="$1"

  if [[ ! -d "$target" ]]; then
    echo "[FAIL] detect_stacks: target dir not found: ${target}"
    return 1
  fi

  echo "[INFO] Detecting stacks in ${target}"

  # ansible/ dir is a cheap stat — do it outside the find walk.
  if ( cd "$target" && detect_dir_exists "ansible" ); then
    DETECTED_ANSIBLE="true"
    CITATION_ANSIBLE="ansible/"
  fi

  # Single-pass walk. Each match updates the right DETECTED_* / CITATION_*.
  # Loop body uses process substitution so var assignments propagate.
  local f
  while IFS= read -r -d '' f; do
    # Strip leading ./
    f="${f#./}"
    case "$f" in
      */playbooks/*.yml|playbooks/*.yml)
        DETECTED_ANSIBLE="true"
        # First playbook found becomes the citation, overriding the dir stub.
        [[ "$CITATION_ANSIBLE" == "ansible/" || "$CITATION_ANSIBLE" == "$CITATION_PLACEHOLDER" ]] && CITATION_ANSIBLE="$f"
        ;;
      *.sh)
        if [[ "$DETECTED_BASH" != "true" ]]; then
          DETECTED_BASH="true"
          CITATION_BASH="$f"
        fi
        ;;
      docker-compose*.yml|*/docker-compose*.yml|compose.yml|*/compose.yml)
        if [[ "$DETECTED_COMPOSE" != "true" ]]; then
          DETECTED_COMPOSE="true"
          CITATION_COMPOSE="$f"
        fi
        ;;
      *.tf)
        if [[ "$DETECTED_TERRAFORM" != "true" ]]; then
          DETECTED_TERRAFORM="true"
          CITATION_TERRAFORM="$f"
        fi
        ;;
    esac
  done < <(
    cd "$target" && \
    eval "find . $(_detect_prune_args) -type f \
      \( -name '*.sh' \
         -o -name '*.tf' \
         -o -name 'docker-compose*.yml' \
         -o -name 'compose.yml' \
         -o -path '*/playbooks/*.yml' \
      \) -print0" 2>/dev/null
  )

  echo "[INFO]   bash      = ${DETECTED_BASH} (${CITATION_BASH})"
  echo "[INFO]   ansible   = ${DETECTED_ANSIBLE} (${CITATION_ANSIBLE})"
  echo "[INFO]   compose   = ${DETECTED_COMPOSE} (${CITATION_COMPOSE})"
  echo "[INFO]   terraform = ${DETECTED_TERRAFORM} (${CITATION_TERRAFORM})"

  export DETECTED_BASH DETECTED_ANSIBLE DETECTED_COMPOSE DETECTED_TERRAFORM
  export CITATION_BASH CITATION_ANSIBLE CITATION_COMPOSE CITATION_TERRAFORM
}
