#!/bin/bash
# ============================================================================
# Claude Scaffold — Umbrella Dispatcher
#
# Stamps a buildable per-platform project starter (backend / frontend /
# mobile / android) into a target workspace. Sister scaffolder to init.sh:
#   - init.sh         stamps the operational .claude/ rules layer
#   - init-scaffold.sh stamps the application skeleton on top
#
# Pipeline:
#   detect → check existing → prompt → render → validate → report
#
# This file is the dispatcher only. The per-platform tree is rendered by
# lib/render-<platform>.sh, sourced lazily after the platform is known. The
# renderer is responsible for the actual file emission; this script handles
# argument parsing, platform selection, prompt orchestration, conflict
# checks, backup namespacing, and the final report.
#
# Requires: bash, sed (always present); envsubst (gettext-base); jq OR python
#           (recommended — improves detect-platform package.json parsing).
#
# Usage:
#   bash init-scaffold.sh [options]
#
# Options:
#   -h, --help                 Print this help and exit.
#   --platform=<name>          backend | frontend | mobile | android.
#                              Skips auto-detection; overrides any detected
#                              shape.
#   --target=<path>            Target workspace dir (default: current dir).
#   --project-name=<name>      Pre-fill project name.
#   --src-dir=<dir>            Source directory (default: src).
#   --api-version=<v#>         Backend API version (default: v1; ^v[0-9]+$).
#   --features=<a,b,c>         CSV of feature folders to scaffold.
#   --android-package=<id>     Reverse-DNS package id (android only).
#   --with-i18n                Enable the optional i18n stub.
#   --with-auth                Enable the optional auth stub.
#   --non-interactive          Skip prompts; read remaining values from
#                              QQPS_PROJECT_NAME, QQPS_SRC_DIR,
#                              QQPS_API_VERSION, QQPS_FEATURES,
#                              QQPS_ANDROID_PACKAGE, QQPS_WITH_I18N,
#                              QQPS_WITH_AUTH.
#   --force                    Overwrite existing files. Clobbered files are
#                              first backed up to
#                                <target>/.claude.bak/<timestamp>/<relative>
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Resolve script + target directories
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(pwd)"

# Defaults — CLI flags + env overrides land here.
IS_NON_INTERACTIVE="false"
FORCE="false"
UNINSTALL="false"
PLATFORM=""
PROJECT_NAME="${QQPS_PROJECT_NAME:-}"
SRC_DIR="${QQPS_SRC_DIR:-src}"
API_VERSION="${QQPS_API_VERSION:-v1}"
FEATURES_CSV="${QQPS_FEATURES:-}"
ANDROID_PACKAGE="${QQPS_ANDROID_PACKAGE:-}"
WITH_I18N="${QQPS_WITH_I18N:-false}"
WITH_AUTH="${QQPS_WITH_AUTH:-false}"

# Tracking — populated by renderers (they append to CREATED_FILES via the
# shared convention used by init.sh / render.sh).
CREATED_FILES=()
export CREATED_FILES

# Explicit-flag markers — distinguish "not passed" from "passed empty".
TARGET_EXPLICIT="false"
PROJECT_NAME_EXPLICIT="false"
SRC_DIR_EXPLICIT="false"
API_VERSION_EXPLICIT="false"
FEATURES_EXPLICIT="false"
ANDROID_PACKAGE_EXPLICIT="false"
PLATFORM_EXPLICIT="false"

# A single timestamp per invocation, exported so renderers reuse it for all
# --force backups. Matches the init.sh convention.
BACKUP_TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_MADE="false"
export BACKUP_TS BACKUP_MADE

# ----------------------------------------------------------------------------
# init_scaffold_print_help — emit the usage block (HEREDOC, not self-grep)
# ----------------------------------------------------------------------------
init_scaffold_print_help() {
  cat <<'EOF'
============================================================================
Claude Scaffold — Umbrella Dispatcher

Stamps a buildable per-platform project starter (backend / frontend /
mobile / android) into a target workspace.

Pipeline:
  detect -> check existing -> prompt -> render -> validate -> report

Usage:
  bash init-scaffold.sh [options]

Options:
  -h, --help                 Print this help and exit.
  --platform=<name>          backend | frontend | mobile | android.
                             Skips auto-detection; overrides any detected
                             shape.
  --target=<path>            Target workspace dir (default: current dir).
  --project-name=<name>      Pre-fill project name.
  --src-dir=<dir>            Source directory (default: src).
  --api-version=<v#>         Backend API version (default: v1; ^v[0-9]+$).
  --features=<a,b,c>         CSV of feature folders to scaffold.
  --android-package=<id>     Reverse-DNS package id (android only).
  --with-i18n                Enable the optional i18n stub.
  --with-auth                Enable the optional auth stub.
  --non-interactive          Skip prompts; read remaining values from
                             QQPS_PROJECT_NAME, QQPS_SRC_DIR,
                             QQPS_API_VERSION, QQPS_FEATURES,
                             QQPS_ANDROID_PACKAGE, QQPS_WITH_I18N,
                             QQPS_WITH_AUTH.
  --force                    Overwrite existing files. Clobbered files are
                             first backed up to
                               <target>/.claude.bak/<timestamp>/<relative>
  --uninstall                Reverse a previous stamp. Reads the manifest at
                             <target>/.claude/.scaffold-manifest-scaffold.txt
                             and removes every file listed, then prunes empty
                             parent directories. Backups in .claude.bak/ are
                             preserved so a manual restore is still possible.
============================================================================
EOF
}

# ----------------------------------------------------------------------------
# init_scaffold_parse_args — populate globals from CLI flags
# ----------------------------------------------------------------------------
init_scaffold_parse_args() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      -h|--help)
        init_scaffold_print_help
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
      --with-i18n)
        WITH_I18N="true"
        ;;
      --with-auth)
        WITH_AUTH="true"
        ;;
      --platform=*)
        PLATFORM="${arg#*=}"
        PLATFORM_EXPLICIT="true"
        ;;
      --target=*)
        TARGET_DIR="${arg#*=}"
        TARGET_EXPLICIT="true"
        ;;
      --project-name=*)
        PROJECT_NAME="${arg#*=}"
        PROJECT_NAME_EXPLICIT="true"
        ;;
      --src-dir=*)
        SRC_DIR="${arg#*=}"
        SRC_DIR_EXPLICIT="true"
        ;;
      --api-version=*)
        API_VERSION="${arg#*=}"
        API_VERSION_EXPLICIT="true"
        ;;
      --features=*)
        FEATURES_CSV="${arg#*=}"
        FEATURES_EXPLICIT="true"
        ;;
      --android-package=*)
        ANDROID_PACKAGE="${arg#*=}"
        ANDROID_PACKAGE_EXPLICIT="true"
        ;;
      *)
        echo "[FAIL] Unknown argument: ${arg}" >&2
        echo "Run with --help for usage." >&2
        exit 1
        ;;
    esac
  done

  # Explicit-but-empty values are user errors, mirroring init.sh.
  if [[ "$PLATFORM_EXPLICIT" == "true" && -z "$PLATFORM" ]]; then
    echo "[FAIL] --platform requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$TARGET_EXPLICIT" == "true" && -z "$TARGET_DIR" ]]; then
    echo "[FAIL] --target requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$PROJECT_NAME_EXPLICIT" == "true" && -z "$PROJECT_NAME" ]]; then
    echo "[FAIL] --project-name requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$SRC_DIR_EXPLICIT" == "true" && -z "$SRC_DIR" ]]; then
    echo "[FAIL] --src-dir requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$API_VERSION_EXPLICIT" == "true" && -z "$API_VERSION" ]]; then
    echo "[FAIL] --api-version requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$ANDROID_PACKAGE_EXPLICIT" == "true" && -z "$ANDROID_PACKAGE" ]]; then
    echo "[FAIL] --android-package requires a non-empty value" >&2
    exit 1
  fi

  # Validate platform value when provided.
  if [[ -n "$PLATFORM" ]]; then
    case "$PLATFORM" in
      backend|frontend|mobile|android) ;;
      *)
        echo "[FAIL] --platform must be one of: backend, frontend, mobile, android (got '${PLATFORM}')" >&2
        exit 1
        ;;
    esac
  fi
}

# ----------------------------------------------------------------------------
# init_scaffold_resolve_platform — fill PLATFORM if not set by --platform=
#
# Order:
#   1. --platform flag wins.
#   2. detect_platform output (DETECTED_PLATFORM) if it isn't 'unknown'.
#   3. In --non-interactive mode, fail with a clear message — auto-detect
#      can't guess against an empty dir without input.
#   4. Otherwise prompt the user with detected candidates as hints.
# ----------------------------------------------------------------------------
init_scaffold_resolve_platform() {
  if [[ -n "$PLATFORM" ]]; then
    echo "[INFO] Platform forced via --platform=${PLATFORM}"
    return 0
  fi

  if [[ "$DETECTED_PLATFORM" != "unknown" ]]; then
    PLATFORM="$DETECTED_PLATFORM"
    echo "[INFO] Platform auto-detected: ${PLATFORM}"
    return 0
  fi

  if [[ "$IS_NON_INTERACTIVE" == "true" ]]; then
    echo "[FAIL] Could not auto-detect platform and no --platform= was given." >&2
    echo "       Pass --platform=backend|frontend|mobile|android." >&2
    exit 1
  fi

  local hint="backend|frontend|mobile|android"
  [[ -n "$DETECTED_CANDIDATES" ]] && hint="${DETECTED_CANDIDATES} (detected) | ${hint}"

  local reply
  while true; do
    read -r -p "  Platform [${hint}]: " reply
    case "$reply" in
      backend|frontend|mobile|android)
        PLATFORM="$reply"
        break
        ;;
      "")
        echo "[WARN] Platform is required."
        ;;
      *)
        echo "[WARN] Platform must be one of: backend, frontend, mobile, android."
        ;;
    esac
  done
}

# ----------------------------------------------------------------------------
# init_scaffold_check_existing — Phase 0 status dashboard + clobber check.
#
# Prints a ✓/✗ dashboard of every file the renderer cares about so the user
# sees the full state of the workspace before any writes happen. When --force
# is NOT set and any candidate already exists, exits 1 with a clear message.
# When --force IS set, prints the dashboard for transparency and returns
# (the renderer will back up clobbered files individually).
# ----------------------------------------------------------------------------
init_scaffold_check_existing() {
  local candidates=(
    "package.json"
    "build.gradle.kts"
    "build.gradle"
    "app.json"
    "src"
    "app"
    "docs"
  )

  local present=() missing=()
  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -e "${TARGET_DIR}/${candidate}" ]]; then
      present+=("${candidate}")
    else
      missing+=("${candidate}")
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
    echo "[WARN] ${#present[@]} existing file(s) will be backed up to .claude.bak/${BACKUP_TS}/ before overwrite."
    return 0
  fi

  echo "[FAIL] ${#present[@]} existing file(s) would be overwritten." >&2
  echo "       Re-run with --force (auto-backup), or move them aside first." >&2
  echo "       Or run with --uninstall to remove a previous stamp first." >&2
  exit 1
}

# ----------------------------------------------------------------------------
# init_scaffold_report — final summary
# ----------------------------------------------------------------------------
init_scaffold_report() {
  echo ""
  echo "===== Scaffold complete ====="
  echo "Target  : ${TARGET_DIR}"
  echo "Platform: ${PLATFORM}"
  echo ""
  if [[ ${#CREATED_FILES[@]} -eq 0 ]]; then
    echo "[WARN] No files were tracked as created (renderer did not record them)."
    return
  fi
  echo "Created ${#CREATED_FILES[@]} file(s)."
  if [[ "${BACKUP_MADE:-false}" == "true" ]]; then
    echo "[OK] Backups available at ${TARGET_DIR}/.claude.bak/${BACKUP_TS}/"
  fi
}

# ----------------------------------------------------------------------------
# _on_exit — EXIT trap so partial failures still surface what was created.
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
    echo "[WARN] init-scaffold.sh aborted early; you may need to clean up these files manually." >&2
  fi
}

# ----------------------------------------------------------------------------
# Manifest helpers — delegate to the shared lib/manifest.sh so init.sh and
# init-scaffold.sh share the same on-disk format. Each dispatcher writes its
# own manifest file so the two scaffolders coexist + uninstall independently.
# ----------------------------------------------------------------------------
INIT_SCAFFOLD_MANIFEST_NAME=".claude/.scaffold-manifest-scaffold.txt"

init_scaffold_write_manifest() {
  local target="$1"
  if [[ ${#CREATED_FILES[@]} -eq 0 ]]; then
    echo "[WARN] No files in CREATED_FILES; skipping manifest." >&2
    return 0
  fi
  manifest_write "${target}/${INIT_SCAFFOLD_MANIFEST_NAME}" \
    "Generated by init-scaffold.sh" \
    "Platform: ${PLATFORM}" \
    "Stamped: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    "Use 'init-scaffold.sh --uninstall --target=<dir>' to reverse" \
    -- \
    "${CREATED_FILES[@]}"
}

init_scaffold_uninstall() {
  local target="$1"
  local manifest="${target}/${INIT_SCAFFOLD_MANIFEST_NAME}"
  echo "[INFO] Uninstall via manifest: ${manifest}"
  if manifest_uninstall "$manifest"; then
    if [[ -d "${target}/.claude.bak" ]]; then
      echo "[INFO] Backups preserved at: ${target}/.claude.bak/"
    fi
    return 0
  fi
  echo "[INFO] Look for backups under ${target}/.claude.bak/<timestamp>/ to restore manually." >&2
  return 1
}

# ============================================================================
# Main
# ============================================================================

trap '_on_exit' EXIT

init_scaffold_parse_args "$@"

# Manifest helpers — needed by both the stamp path (write) and the uninstall
# fast-path (read). Sourced early so the uninstall branch below can call it.
# shellcheck source=lib/manifest.sh
source "${SCRIPT_DIR}/lib/manifest.sh"

# --uninstall is short-circuit: no envsubst, no detect, no prompt, no render.
# Just read the manifest written by a previous stamp and reverse it.
if [[ "$UNINSTALL" == "true" ]]; then
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "[FAIL] --target does not exist: ${TARGET_DIR}" >&2
    exit 1
  fi
  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
  echo "[INFO] Uninstalling from: ${TARGET_DIR}"
  init_scaffold_uninstall "$TARGET_DIR"
  exit $?
fi

# envsubst is hard-required because per-platform renderers will use it for
# .tmpl substitution. Fail fast with the same message style as init.sh.
if ! command -v envsubst >/dev/null 2>&1; then
  echo "[FAIL] envsubst is required for templating but not installed." >&2
  echo "       On Debian/Ubuntu: apt install gettext-base" >&2
  echo "       On macOS: brew install gettext (and link)" >&2
  echo "       On Windows + Git Bash: typically present; check 'where envsubst'" >&2
  exit 1
fi

# Resolve target dir. If it doesn't exist we create it — scaffolding into a
# brand-new directory is a normal flow.
if [[ ! -d "$TARGET_DIR" ]]; then
  echo "[INFO] Target dir does not exist; creating: ${TARGET_DIR}"
  mkdir -p "$TARGET_DIR"
fi
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "[INFO] Claude project scaffold"
echo "[INFO] Source : ${SCRIPT_DIR}"
echo "[INFO] Target : ${TARGET_DIR}"

# Source detect + prompt + validate libs up-front; they have no platform
# dependency. Renderers are sourced lazily once platform is known.
# shellcheck source=lib/detect-platform.sh
source "${SCRIPT_DIR}/lib/detect-platform.sh"
# shellcheck source=lib/prompt-scaffold.sh
source "${SCRIPT_DIR}/lib/prompt-scaffold.sh"
# shellcheck source=lib/validate-scaffold.sh
source "${SCRIPT_DIR}/lib/validate-scaffold.sh"

# 1. detect
detect_platform "$TARGET_DIR"

# 2. resolve platform (flag → detected → prompt)
init_scaffold_resolve_platform

# 3. refuse to clobber without --force
init_scaffold_check_existing

# 4. prompt for the remaining substitution variables. prompt_scaffold_collect
#    honours IS_NON_INTERACTIVE on its own.
prompt_scaffold_collect "$PLATFORM"

# Re-export everything renderers need (idempotent; covers both paths).
export PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION FEATURES_CSV \
       ANDROID_PACKAGE WITH_I18N WITH_AUTH TIMESTAMP \
       PLATFORM TARGET_DIR FORCE IS_NON_INTERACTIVE BACKUP_TS

# 5. source the per-platform renderer lazily. The dispatcher errors cleanly
#    if the lib is missing (renderers land in Subtasks 3-6).
RENDERER_LIB="${SCRIPT_DIR}/lib/render-${PLATFORM}.sh"
if [[ ! -f "$RENDERER_LIB" ]]; then
  echo "[FAIL] renderer lib not found: lib/render-${PLATFORM}.sh" >&2
  echo "       Expected at: ${RENDERER_LIB}" >&2
  echo "       This platform's renderer has not been implemented yet." >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$RENDERER_LIB"

# Each renderer exposes a render_<platform>_all function.
RENDER_FN="render_${PLATFORM}_all"
if ! declare -F "$RENDER_FN" >/dev/null 2>&1; then
  echo "[FAIL] renderer lib '${RENDERER_LIB}' did not define '${RENDER_FN}'" >&2
  exit 1
fi

# 6. render
"$RENDER_FN" "$TARGET_DIR"

# 6b. persist manifest so a future --uninstall can reverse this stamp
init_scaffold_write_manifest "$TARGET_DIR"

# 7. validate
validate_scaffold_all "$TARGET_DIR" "$PLATFORM"

# 8. report
init_scaffold_report
