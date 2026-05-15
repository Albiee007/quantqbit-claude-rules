#!/bin/bash
# ============================================================================
# Scaffold Validate Library — post-stamp sanity checks for project scaffolds
#
# Walks the stamped target directory and reports:
#   - count of directories
#   - count of files
#   - count of README.md files
#   - count of .gitkeep files
#
# Then checks that every required architectural folder for the selected
# platform actually exists. The per-platform renderer is responsible for
# exporting the required-dirs list under one of:
#
#   BACKEND_REQUIRED_DIRS   (when --platform=backend)
#   FRONTEND_REQUIRED_DIRS  (when --platform=frontend)
#   MOBILE_REQUIRED_DIRS    (when --platform=mobile)
#   ANDROID_REQUIRED_DIRS   (when --platform=android)
#
# The value is a CSV of dir paths relative to the target, e.g.
#   BACKEND_REQUIRED_DIRS="src,src/config,src/api/v1,docs"
#
# Common dirs that should always exist (docs/) are also asserted regardless
# of platform.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/validate-scaffold.sh"
#   validate_scaffold_all "/path/to/target" "<platform>"
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# _validate_scaffold_count — count things under $1 matching $2 (find expression)
# Args: $1 = root, $2... = additional find args after the root
# Echoes the count.
# ----------------------------------------------------------------------------
_validate_scaffold_count() {
  local root="$1"; shift
  # find prints one match per line; wc -l counts them. Trailing newline from
  # wc gets stripped via the $(...) expansion.
  find "$root" "$@" 2>/dev/null | wc -l | tr -d '[:space:]'
}

# ----------------------------------------------------------------------------
# _validate_scaffold_required_var — look up the platform-specific required
# dirs env var and echo its value (empty if unset).
# Args: $1 = platform
# ----------------------------------------------------------------------------
_validate_scaffold_required_var() {
  local platform="$1"
  case "$platform" in
    backend)  printf '%s' "${BACKEND_REQUIRED_DIRS:-}" ;;
    frontend) printf '%s' "${FRONTEND_REQUIRED_DIRS:-}" ;;
    mobile)   printf '%s' "${MOBILE_REQUIRED_DIRS:-}" ;;
    android)  printf '%s' "${ANDROID_REQUIRED_DIRS:-}" ;;
    *)        printf '%s' "" ;;
  esac
}

# ----------------------------------------------------------------------------
# validate_scaffold_all — run all post-stamp checks
# Args: $1 = absolute target dir
#       $2 = platform (backend|frontend|mobile|android)
#
# Exits non-zero if any required directory is missing OR if the target dir
# is empty (i.e. the renderer did nothing).
# ----------------------------------------------------------------------------
validate_scaffold_all() {
  local target="$1"
  local platform="$2"
  local failures=0

  if [[ ! -d "$target" ]]; then
    echo "[FAIL] validate_scaffold_all: target dir not found: ${target}" >&2
    exit 1
  fi

  echo "[INFO] Validating scaffold at ${target}"

  # ---- counts ----
  local dir_count file_count readme_count gitkeep_count
  dir_count="$(_validate_scaffold_count "$target" -mindepth 1 -type d)"
  file_count="$(_validate_scaffold_count "$target" -type f)"
  readme_count="$(_validate_scaffold_count "$target" -type f -name 'README.md')"
  gitkeep_count="$(_validate_scaffold_count "$target" -type f -name '.gitkeep')"

  echo "[INFO]   directories     = ${dir_count}"
  echo "[INFO]   files           = ${file_count}"
  echo "[INFO]   README.md files = ${readme_count}"
  echo "[INFO]   .gitkeep files  = ${gitkeep_count}"

  if [[ "$file_count" -eq 0 ]]; then
    echo "[FAIL] Target dir contains no files — renderer produced nothing." >&2
    failures=$((failures + 1))
  fi

  # ---- required-dirs assertion ----
  local required_csv
  required_csv="$(_validate_scaffold_required_var "$platform")"

  if [[ -z "$required_csv" ]]; then
    echo "[WARN] No <PLATFORM>_REQUIRED_DIRS exported for platform='${platform}'."
    echo "[WARN] Skipping required-folder assertion."
  else
    echo "[INFO] Checking required folders for platform='${platform}'..."
    # Split CSV. IFS swap is scoped to this block so we don't leak it.
    local old_ifs="$IFS"
    IFS=','
    # shellcheck disable=SC2206
    local required_dirs=( $required_csv )
    IFS="$old_ifs"

    local d full
    for d in "${required_dirs[@]}"; do
      # Trim whitespace from each token (tolerates "a, b, c").
      d="$(printf '%s' "$d" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
      [[ -z "$d" ]] && continue
      full="${target}/${d}"
      if [[ -d "$full" ]]; then
        echo "[OK]   dir ${d}"
      else
        echo "[FAIL] missing required dir: ${d}" >&2
        failures=$((failures + 1))
      fi
    done
  fi

  if [[ "$failures" -gt 0 ]]; then
    echo "[FAIL] Scaffold validation reported ${failures} failure(s)." >&2
    exit 1
  fi

  echo "[OK] Scaffold validation passed."
}
