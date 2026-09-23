#!/bin/bash
# ============================================================================
# Claude Rules Scaffold — Orchestrator (/init-project-rules)
#
# v1.0: two steps.
#   1. Stamps lint tooling (.editorconfig, .shellcheckrc, .yamllint,
#      .ansible-lint, scripts/lint.sh, Makefile) under CODE_SUBDIR, tailored
#      to the detected stacks. Write-if-absent: existing files are kept.
#   2. Installs the agent harness via scaffold/sync.sh: core rules, skills,
#      agents, hooks and generated settings.json. The harness owns these files;
#      see harness/README.md. CLAUDE.md / AGENTS.md stay project-owned.
#
# Pipeline:
#   detect → check existing → prompt → render lint tooling → validate → report
#   → project opt-in denies → harness sync
#
# Requires: bash, sed (always present); envsubst (gettext-base); jq OR python
#           (for JSON validate). envsubst is hard-required as of v0.1.1.
#
# Usage:
#   bash init.sh [options]
#
# Options:
#   -h, --help              Print this help and exit.
#   --target=<path>         Target workspace dir (default: current directory).
#   --non-interactive       Skip prompts; read defaults from environment:
#                             QQR_PROJECT_NAME, QQR_CODE_SUBDIR,
#                             QQR_OPT_IN_DESTRUCTIVE, QQR_OPT_IN_PUSH_MAIN
#   --project-name=<name>   Pre-fill project name (overrides env).
#   --code-subdir=<dir>     Pre-fill code subdir (overrides env).
#   --force                 Overwrite existing lint tooling files. They are
#                           FIRST backed up to
#                           <target>/.claude.bak/<timestamp>/<relative-path>.
#                           Without --force, existing files are kept.
#   --no-harness            Only stamp lint tooling; skip the harness sync.
#   --uninstall             Remove unmodified stamped lint files (manifest).
#                           For the harness: bash scaffold/sync.sh --uninstall
# ============================================================================

set -euo pipefail
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

# ----------------------------------------------------------------------------
# Resolve script + target directories
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(pwd)"

# Defaults for prompt values (may be overridden by env or flags)
IS_NON_INTERACTIVE="false"
FORCE="false"
UNINSTALL="false"
NO_HARNESS="false"
PROJECT_NAME="${QQR_PROJECT_NAME:-}"
CODE_SUBDIR="${QQR_CODE_SUBDIR:-./}"
OPT_IN_DESTRUCTIVE="${QQR_OPT_IN_DESTRUCTIVE:-n}"
OPT_IN_PUSH_MAIN="${QQR_OPT_IN_PUSH_MAIN:-n}"

# Tracking — populated as we go
CREATED_FILES=()

# Fix E1: track which flags were explicitly passed so we can distinguish
# "not passed" from "passed with empty value" (the latter is an error).
TARGET_EXPLICIT="false"
PROJECT_NAME_EXPLICIT="false"
CODE_SUBDIR_EXPLICIT="false"

# Fix 5: a single timestamp per init.sh invocation, used to namespace backups
# of files clobbered by --force. Set once here so every backup in this run
# lands under the same .claude.bak/<ts>/ directory.
BACKUP_TS="$(date +%Y%m%d-%H%M%S)"
# Set to "true" by render.sh when at least one file was backed up.
BACKUP_MADE="false"

# ----------------------------------------------------------------------------
# init_print_help — emit the usage block
# Fix E3: use a HEREDOC instead of grepping lines out of this file. The
# previous sed-based approach broke whenever the banner changed.
# ----------------------------------------------------------------------------
init_print_help() {
  # Print the header comment block (single source of truth for usage).
  sed -n '2,/^# =====*$/{s/^# \{0,1\}//;p;}' "${BASH_SOURCE[0]}" | sed -n '2,$p'
}

# ----------------------------------------------------------------------------
# init_parse_args — parse CLI args into globals
# ----------------------------------------------------------------------------
init_parse_args() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      -h|--help)
        init_print_help
        exit 0
        ;;
      --non-interactive)
        IS_NON_INTERACTIVE="true"
        ;;
      --force)
        FORCE="true"
        ;;
      --uninstall)
        UNINSTALL="true"
        ;;
      --no-harness)
        NO_HARNESS="true"
        ;;
      --target=*)
        TARGET_DIR="${arg#*=}"
        TARGET_EXPLICIT="true"
        ;;
      --project-name=*)
        PROJECT_NAME="${arg#*=}"
        PROJECT_NAME_EXPLICIT="true"
        ;;
      --code-subdir=*)
        CODE_SUBDIR="${arg#*=}"
        CODE_SUBDIR_EXPLICIT="true"
        ;;
      *)
        echo "[FAIL] Unknown argument: ${arg}"
        echo "Run with --help for usage."
        exit 1
        ;;
    esac
  done

  # Fix E1: explicit-but-empty flag values are user errors, not silent defaults.
  # If a user passed `--target=`, `--project-name=`, or `--code-subdir=` with
  # no value, fail with a clear message instead of silently using "" / the
  # current directory / etc.
  if [[ "$TARGET_EXPLICIT" == "true" && -z "$TARGET_DIR" ]]; then
    echo "[FAIL] --target requires a non-empty value"
    exit 1
  fi
  if [[ "$PROJECT_NAME_EXPLICIT" == "true" && -z "$PROJECT_NAME" ]]; then
    echo "[FAIL] --project-name requires a non-empty value"
    exit 1
  fi
  if [[ "$CODE_SUBDIR_EXPLICIT" == "true" && -z "$CODE_SUBDIR" ]]; then
    echo "[FAIL] --code-subdir requires a non-empty value"
    exit 1
  fi
}

# ----------------------------------------------------------------------------
# init_check_existing — Phase 0 status dashboard + clobber check.
#
# Prints a ✓/✗ dashboard of every file/dir the rules layer cares about so the
# user can see the full workspace state before any writes happen. When --force
# is NOT set and any candidate already exists, exits 1. When --force IS set,
# prints the dashboard for transparency and returns (render.sh backs up
# clobbered files individually).
# ----------------------------------------------------------------------------
init_check_existing() {
  local candidates=(
    "${CODE_SUBDIR%/}/scripts/lint.sh"
    "${CODE_SUBDIR%/}/Makefile"
    ".editorconfig"
  )

  local present=()
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -e "${TARGET_DIR}/${candidate}" ]]; then
      present+=("${candidate}")
    fi
  done

  echo ""
  echo "[INFO] Status check for: ${TARGET_DIR}"
  for candidate in "${candidates[@]}"; do
    if [[ -e "${TARGET_DIR}/${candidate}" ]]; then
      printf "  \xe2\x9c\x93 %s\n" "${candidate}"
    else
      printf "  \xe2\x9c\x97 %s (would be stamped)\n" "${candidate}"
    fi
  done
  echo ""

  if [[ ${#present[@]} -eq 0 ]]; then
    echo "[OK] Clean workspace — proceeding with stamp."
    return 0
  fi

  if [[ "$FORCE" == "true" ]]; then
    echo "[WARN] ${#present[@]} existing path(s) will be backed up to .claude.bak/${BACKUP_TS}/ before overwrite."
    return 0
  fi
  echo "[INFO] ${#present[@]} existing path(s) will be kept as-is (write-if-absent)."
  return 0

  echo "[FAIL] ${#present[@]} existing path(s) would be overwritten."
  echo "       Re-run with --force (auto-backup), or move them aside first."
  echo "       Or run with --uninstall to remove a previous stamp first."
  exit 1
}

# ----------------------------------------------------------------------------
# init_report — final summary of created files
# ----------------------------------------------------------------------------
init_report() {
  echo ""
  echo "===== Scaffold complete ====="
  echo "Target: ${TARGET_DIR}"
  echo ""
  if [[ ${#CREATED_FILES[@]} -eq 0 ]]; then
    echo "[WARN] No files were created."
    return
  fi
  echo "Created ${#CREATED_FILES[@]} file(s):"
  local f
  for f in "${CREATED_FILES[@]}"; do
    echo "  - ${f}"
  done

  # Fix 5: surface backup directory if --force clobbered any pre-existing
  # files. render.sh sets BACKUP_MADE=true after copying the original aside.
  if [[ "${BACKUP_MADE:-false}" == "true" ]]; then
    echo ""
    echo "[OK] Backups available at ${TARGET_DIR}/.claude.bak/${BACKUP_TS}/"
  fi
}

# ----------------------------------------------------------------------------
# _on_exit — EXIT trap handler (Fix E4)
# Runs regardless of exit status so the user always sees the list of files
# that were created before init.sh aborted. Without this, `set -e` would
# abort the script and init_report would never run, leaving the user with no
# idea what to clean up after a partial failure.
# ----------------------------------------------------------------------------
_on_exit() {
  local rc=$?
  if [[ ${#CREATED_FILES[@]} -gt 0 ]]; then
    echo ""
    echo "[INFO] Created files (before exit):"
    local f
    for f in "${CREATED_FILES[@]}"; do
      echo "  - ${f}"
    done
  fi
  if [[ $rc -ne 0 ]]; then
    echo "[WARN] init.sh aborted early; you may need to clean up these files manually."
  fi
}

# ----------------------------------------------------------------------------
# Manifest helpers — delegate to the shared lib/manifest.sh. init.sh writes
# its manifest to .claude/.scaffold-manifest-rules.txt; init-scaffold.sh
# writes its own under .claude/.scaffold-manifest-scaffold.txt. The two
# coexist + uninstall independently.
# ----------------------------------------------------------------------------
INIT_MANIFEST_NAME=".claude/.scaffold-manifest-rules.txt"

init_write_manifest() {
  local target="$1"
  if [[ ${#CREATED_FILES[@]} -eq 0 ]]; then
    echo "[WARN] No files in CREATED_FILES; skipping manifest."
    return 0
  fi
  manifest_write "${target}/${INIT_MANIFEST_NAME}" \
    "Generated by init.sh" \
    "Stamped: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "Use 'init.sh --uninstall --target=<dir>' to reverse" \
    -- \
    "${CREATED_FILES[@]}"
}

init_uninstall() {
  local target="$1"
  local manifest="${target}/${INIT_MANIFEST_NAME}"
  echo "[INFO] Uninstall via manifest: ${manifest}"
  if manifest_uninstall "$manifest"; then
    if [[ -d "${target}/.claude.bak" ]]; then
      echo "[INFO] Backups preserved at: ${target}/.claude.bak/"
    fi
    return 0
  fi
  echo "[INFO] Look for backups under ${target}/.claude.bak/<timestamp>/ to restore manually."
  return 1
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

# Fix E4: install EXIT trap as early as possible so partial-failure reports
# always show what was created. render.sh layers staging-dir cleanup onto
# this via its own trap definition.
trap '_on_exit' EXIT

init_parse_args "$@"

# Manifest helpers — sourced early so the uninstall fast-path can use them
# before any other lib (envsubst, detect, prompt) is needed.
# shellcheck source=lib/manifest.sh
source "${SCRIPT_DIR}/lib/manifest.sh"

# --uninstall short-circuit: no envsubst, no detect, no prompt, no render.
if [[ "$UNINSTALL" == "true" ]]; then
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "[FAIL] --target does not exist: ${TARGET_DIR}"
    exit 1
  fi
  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
  echo "[INFO] Uninstalling from: ${TARGET_DIR}"
  init_uninstall "$TARGET_DIR"
  exit $?
fi

# Fix 2: hard-require envsubst. The pure-sed fallback in render.sh could not
# safely substitute multi-line values (e.g. DENY_DESTRUCTIVE) — they triggered
# `unterminated 's' command` errors. Rather than build a sentinel-based
# workaround, refuse to start without envsubst (a 200KB gettext binary).
if ! command -v envsubst >/dev/null 2>&1; then
  echo "[FAIL] envsubst is required for templating but not installed."
  echo "       On Debian/Ubuntu: apt install gettext-base"
  echo "       On macOS: brew install gettext (and link)"
  echo "       On Windows + Git Bash: typically present; check 'where envsubst'"
  exit 1
fi

# Resolve target dir to absolute
if [[ ! -d "$TARGET_DIR" ]]; then
  echo "[FAIL] Target directory does not exist: ${TARGET_DIR}"
  exit 1
fi
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "[INFO] Claude rules scaffold"
echo "[INFO] Source : ${SCRIPT_DIR}"
echo "[INFO] Target : ${TARGET_DIR}"

# Source the helper libraries
# shellcheck source=lib/detect.sh
source "${SCRIPT_DIR}/lib/detect.sh"
# shellcheck source=lib/prompt.sh
source "${SCRIPT_DIR}/lib/prompt.sh"
# shellcheck source=lib/render.sh
source "${SCRIPT_DIR}/lib/render.sh"
# shellcheck source=lib/validate.sh
source "${SCRIPT_DIR}/lib/validate.sh"

# Detect stacks (exports DETECTED_* and CITATION_*)
detect_stacks "$TARGET_DIR"

# Pre-flight: refuse to clobber unless --force
init_check_existing

# Prompt the user (unless --non-interactive)
if [[ "$IS_NON_INTERACTIVE" == "true" ]]; then
  echo "[INFO] Non-interactive mode — using env defaults."
  if [[ -z "$PROJECT_NAME" ]]; then
    echo "[FAIL] PROJECT_NAME is required (set --project-name= or QQR_PROJECT_NAME)."
    exit 1
  fi
else
  prompt_collect
fi

# Fix E2: normalise CODE_SUBDIR so it never has a trailing slash. Default
# "./" → "."; "./infra/" → "./infra". This keeps template interpolation
# clean (no `.//docs/` doubling).
#
# Convention: CODE_SUBDIR is normalised to have NO trailing slash. Templates
# must add a leading slash after.
CODE_SUBDIR="${CODE_SUBDIR%/}"
# Edge case: a bare "/" would normalise to "" — fall back to "." so the
# downstream interpolation still resolves to a usable path.
[[ -z "$CODE_SUBDIR" ]] && CODE_SUBDIR="."

# Bug 1 fix: ensure scaffold variables are exported on ALL paths.
# In interactive mode prompt_collect already exports them, but re-exporting
# here is harmless and gives non-interactive mode a single source of truth so
# render.sh sees PROJECT_NAME / CODE_SUBDIR / OPT_IN_* regardless of how they
# were supplied (CLI flag, env var, or interactive prompt).
export PROJECT_NAME CODE_SUBDIR OPT_IN_DESTRUCTIVE OPT_IN_PUSH_MAIN

# Render every template into the target
render_all "$TARGET_DIR"

# Persist manifest so a future --uninstall can reverse this stamp
init_write_manifest "$TARGET_DIR"

# Validate stamped output
validate_all "$TARGET_DIR"

# Final report
init_report

# Opt-in deny rules go into the project-owned settings file (never into the
# generated settings.json). Written only if the project has none yet.
init_write_project_settings() {
  local f="${TARGET_DIR}/.claude/settings.project.json" denies=()
  case "${OPT_IN_DESTRUCTIVE:-}" in y|yes|true|1)
    denies+=('"Bash(terraform destroy*)"' '"Bash(docker system prune*)"' '"Bash(docker volume prune*)"') ;; esac
  case "${OPT_IN_PUSH_MAIN:-}" in y|yes|true|1)
    denies+=('"Bash(git push *main*)"' '"Bash(git push *master*)"') ;; esac
  [[ ${#denies[@]} -eq 0 ]] && return 0
  if [[ -e "$f" ]]; then
    echo "[INFO] ${f} exists; add these to permissions.deny yourself: ${denies[*]}"
    return 0
  fi
  mkdir -p "$(dirname "$f")"
  local IFS=','
  printf '{
  "permissions": {
    "deny": [%s]
  }
}
' "${denies[*]}" > "$f"
  echo "[OK]   wrote ${f} (project-owned opt-in deny rules)"
}

# Agent rules, skills, agents, hooks and settings come from the agent harness.
if [[ "${NO_HARNESS:-false}" != "true" ]]; then
  init_write_project_settings
  echo ""
  echo "[INFO] Installing the agent harness (scaffold/sync.sh)"
  trap - EXIT
  bash "${SCRIPT_DIR}/sync.sh" --target "$TARGET_DIR"
fi
