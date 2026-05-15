#!/bin/bash
# ============================================================================
# Scaffold Prompt Library — collect per-platform scaffold inputs
#
# Drives the interactive flow that fills in the substitution variables every
# render-<platform>.sh expects:
#
#   PROJECT_NAME      — human-readable project name (required)
#   PROJECT_SLUG      — derived kebab-case slug (lowercase + [^a-z0-9]+ → '-')
#   SRC_DIR           — source directory (default: src)
#   API_VERSION       — backend API version (default: v1; pattern: ^v[0-9]+$)
#   FEATURES_CSV      — optional CSV of feature names (alphanumeric + _ -)
#   ANDROID_PACKAGE   — android-only; reverse-DNS package id
#   WITH_I18N         — "true" / "false"
#   WITH_AUTH         — "true" / "false"
#   TIMESTAMP         — date +%Y-%m-%d for stamp-time docs
#
# In --non-interactive mode (IS_NON_INTERACTIVE=true) the function reads
# defaults from QQPS_* env vars instead of prompting. The umbrella dispatcher
# (init-scaffold.sh) is responsible for setting IS_NON_INTERACTIVE and for
# pre-loading CLI-flag values into the variables before calling
# prompt_scaffold_collect.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/prompt-scaffold.sh"
#   prompt_scaffold_collect "<platform>"   # platform = backend|frontend|mobile|android
# ============================================================================

set -euo pipefail

# Defaults — these are set here so the library is safe to source even if the
# caller hasn't pre-declared them. The umbrella script overrides via CLI flags.
PROJECT_NAME="${PROJECT_NAME:-${QQPS_PROJECT_NAME:-}}"
PROJECT_SLUG="${PROJECT_SLUG:-}"
SRC_DIR="${SRC_DIR:-${QQPS_SRC_DIR:-src}}"
API_VERSION="${API_VERSION:-${QQPS_API_VERSION:-v1}}"
FEATURES_CSV="${FEATURES_CSV:-${QQPS_FEATURES:-}}"
ANDROID_PACKAGE="${ANDROID_PACKAGE:-${QQPS_ANDROID_PACKAGE:-}}"
WITH_I18N="${WITH_I18N:-${QQPS_WITH_I18N:-false}}"
WITH_AUTH="${WITH_AUTH:-${QQPS_WITH_AUTH:-false}}"
TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"

# ----------------------------------------------------------------------------
# _prompt_scaffold_trim — strip leading + trailing whitespace from $1
# ----------------------------------------------------------------------------
_prompt_scaffold_trim() {
  printf '%s' "$1" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g'
}

# ----------------------------------------------------------------------------
# prompt_scaffold_slugify — derive a kebab-case slug from a project name
# Args: $1 = source string
# Echoes the slug. Lowercases, replaces any run of [^a-z0-9] with '-', and
# strips leading / trailing '-'.
# ----------------------------------------------------------------------------
prompt_scaffold_slugify() {
  local raw="$1"
  # tr first so the regex stage only handles lowercase ASCII.
  local lower
  lower="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  # Replace any run of non-alphanumeric with a single dash, then trim dashes.
  printf '%s' "$lower" | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

# ----------------------------------------------------------------------------
# prompt_scaffold_validate_api_version — true if $1 matches ^v[0-9]+$
# ----------------------------------------------------------------------------
prompt_scaffold_validate_api_version() {
  [[ "$1" =~ ^v[0-9]+$ ]]
}

# ----------------------------------------------------------------------------
# prompt_scaffold_validate_features — true if $1 is empty OR a clean CSV of
# [a-zA-Z0-9_-]+ tokens.
# ----------------------------------------------------------------------------
prompt_scaffold_validate_features() {
  local val="$1"
  [[ -z "$val" ]] && return 0
  [[ "$val" =~ ^[a-zA-Z0-9_-]+(,[a-zA-Z0-9_-]+)*$ ]]
}

# ----------------------------------------------------------------------------
# prompt_scaffold_validate_android_pkg — true if $1 looks like a reverse-DNS
# package id (e.g. com.acme.app). Allows lowercase letters, digits, underscore
# segments; requires at least two segments.
# ----------------------------------------------------------------------------
prompt_scaffold_validate_android_pkg() {
  [[ "$1" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$ ]]
}

# ----------------------------------------------------------------------------
# _prompt_scaffold_yes_no — read y/N answer, normalise to "true" / "false"
# Args: $1 = question, $2 = default ("true" or "false")
# ----------------------------------------------------------------------------
_prompt_scaffold_yes_no() {
  local question="$1"
  local default="$2"
  local hint="[y/N]"
  [[ "$default" == "true" ]] && hint="[Y/n]"

  local reply
  read -r -p "${question} ${hint} " reply
  reply="${reply:-$default}"
  case "$reply" in
    true|[Yy]|[Yy][Ee][Ss]) echo "true" ;;
    false|[Nn]|[Nn][Oo])    echo "false" ;;
    *)                      echo "$default" ;;
  esac
}

# ----------------------------------------------------------------------------
# prompt_scaffold_collect — gather inputs (interactive or non-interactive)
# Args: $1 = platform (backend|frontend|mobile|android)
# ----------------------------------------------------------------------------
prompt_scaffold_collect() {
  local platform="$1"
  local non_interactive="${IS_NON_INTERACTIVE:-false}"

  if [[ "$non_interactive" == "true" ]]; then
    _prompt_scaffold_collect_non_interactive "$platform"
  else
    _prompt_scaffold_collect_interactive "$platform"
  fi

  # Derive PROJECT_SLUG from the final PROJECT_NAME if not already set.
  if [[ -z "$PROJECT_SLUG" ]]; then
    PROJECT_SLUG="$(prompt_scaffold_slugify "$PROJECT_NAME")"
  fi
  if [[ -z "$PROJECT_SLUG" ]]; then
    echo "[FAIL] Could not derive PROJECT_SLUG from PROJECT_NAME='${PROJECT_NAME}'" >&2
    exit 1
  fi

  # Refresh TIMESTAMP so a long interactive session still stamps today's date.
  TIMESTAMP="$(date +%Y-%m-%d)"

  export PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION FEATURES_CSV \
         ANDROID_PACKAGE WITH_I18N WITH_AUTH TIMESTAMP
}

# ----------------------------------------------------------------------------
# _prompt_scaffold_collect_non_interactive — validate env-supplied values
# Fails fast (exit 1) on any missing-required / format-invalid input so the
# caller doesn't proceed to render with garbage.
# ----------------------------------------------------------------------------
_prompt_scaffold_collect_non_interactive() {
  local platform="$1"

  echo "[INFO] Non-interactive mode — reading QQPS_* env vars + CLI flags."

  PROJECT_NAME="$(_prompt_scaffold_trim "${PROJECT_NAME}")"
  SRC_DIR="$(_prompt_scaffold_trim "${SRC_DIR}")"
  API_VERSION="$(_prompt_scaffold_trim "${API_VERSION}")"
  FEATURES_CSV="$(_prompt_scaffold_trim "${FEATURES_CSV}")"
  ANDROID_PACKAGE="$(_prompt_scaffold_trim "${ANDROID_PACKAGE}")"

  [[ -z "$SRC_DIR" ]]      && SRC_DIR="src"
  [[ -z "$API_VERSION" ]]  && API_VERSION="v1"

  if [[ -z "$PROJECT_NAME" ]]; then
    echo "[FAIL] PROJECT_NAME is required (set --project-name= or QQPS_PROJECT_NAME)" >&2
    exit 1
  fi

  if ! prompt_scaffold_validate_api_version "$API_VERSION"; then
    echo "[FAIL] API_VERSION='${API_VERSION}' must match ^v[0-9]+$" >&2
    exit 1
  fi

  if ! prompt_scaffold_validate_features "$FEATURES_CSV"; then
    echo "[FAIL] FEATURES='${FEATURES_CSV}' must be an empty string or CSV of [a-zA-Z0-9_-]+" >&2
    exit 1
  fi

  if [[ "$platform" == "android" ]]; then
    if [[ -z "$ANDROID_PACKAGE" ]]; then
      echo "[FAIL] ANDROID_PACKAGE is required for --platform=android (set --android-package= or QQPS_ANDROID_PACKAGE)" >&2
      exit 1
    fi
    if ! prompt_scaffold_validate_android_pkg "$ANDROID_PACKAGE"; then
      echo "[FAIL] ANDROID_PACKAGE='${ANDROID_PACKAGE}' must match ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+\$" >&2
      exit 1
    fi
  fi

  # Normalise boolean-ish env values to "true" / "false".
  case "$WITH_I18N" in true|1|y|Y|yes|YES) WITH_I18N="true" ;; *) WITH_I18N="false" ;; esac
  case "$WITH_AUTH" in true|1|y|Y|yes|YES) WITH_AUTH="true" ;; *) WITH_AUTH="false" ;; esac

  echo "[INFO]   PROJECT_NAME    = ${PROJECT_NAME}"
  echo "[INFO]   SRC_DIR         = ${SRC_DIR}"
  echo "[INFO]   API_VERSION     = ${API_VERSION}"
  echo "[INFO]   FEATURES_CSV    = ${FEATURES_CSV:-<none>}"
  [[ "$platform" == "android" ]] && echo "[INFO]   ANDROID_PACKAGE = ${ANDROID_PACKAGE}"
  echo "[INFO]   WITH_I18N       = ${WITH_I18N}"
  echo "[INFO]   WITH_AUTH       = ${WITH_AUTH}"
}

# ----------------------------------------------------------------------------
# _prompt_scaffold_collect_interactive — drive the read -p loop
# Loops on each value until validation passes, then asks for confirmation;
# `n` restarts the whole loop (matches the existing prompt.sh UX).
# ----------------------------------------------------------------------------
_prompt_scaffold_collect_interactive() {
  local platform="$1"
  local confirmed=""
  local reply

  while [[ "$confirmed" != "y" ]]; do
    echo ""
    echo "[INFO] Scaffold inputs for platform '${platform}':"

    # PROJECT_NAME — required, non-empty.
    while true; do
      read -r -p "  Project name [${PROJECT_NAME}]: " reply
      reply="${reply:-$PROJECT_NAME}"
      reply="$(_prompt_scaffold_trim "$reply")"
      if [[ -n "$reply" ]]; then
        PROJECT_NAME="$reply"
        break
      fi
      echo "[WARN] Project name cannot be empty."
    done

    # SRC_DIR — default 'src', non-empty after trim.
    while true; do
      read -r -p "  Source directory [${SRC_DIR}]: " reply
      reply="${reply:-$SRC_DIR}"
      reply="$(_prompt_scaffold_trim "$reply")"
      if [[ -n "$reply" ]]; then
        SRC_DIR="$reply"
        break
      fi
      echo "[WARN] Source directory cannot be empty."
    done

    # API_VERSION — only meaningful for backend, but we still collect to
    # keep the substitution variable populated for shared docs.
    while true; do
      read -r -p "  API version [${API_VERSION}]: " reply
      reply="${reply:-$API_VERSION}"
      reply="$(_prompt_scaffold_trim "$reply")"
      if prompt_scaffold_validate_api_version "$reply"; then
        API_VERSION="$reply"
        break
      fi
      echo "[WARN] API version must match ^v[0-9]+\$ (e.g. v1, v2)."
    done

    # FEATURES_CSV — optional. Empty is allowed.
    while true; do
      read -r -p "  Features CSV (optional) [${FEATURES_CSV}]: " reply
      # If the user just hits enter, keep the previous value.
      if [[ -z "$reply" ]]; then
        reply="$FEATURES_CSV"
      fi
      reply="$(_prompt_scaffold_trim "$reply")"
      if prompt_scaffold_validate_features "$reply"; then
        FEATURES_CSV="$reply"
        break
      fi
      echo "[WARN] Features must be a CSV of [a-zA-Z0-9_-]+ tokens (or empty)."
    done

    # ANDROID_PACKAGE — only when platform=android.
    if [[ "$platform" == "android" ]]; then
      while true; do
        read -r -p "  Android package [${ANDROID_PACKAGE:-com.example.app}]: " reply
        reply="${reply:-${ANDROID_PACKAGE:-com.example.app}}"
        reply="$(_prompt_scaffold_trim "$reply")"
        if prompt_scaffold_validate_android_pkg "$reply"; then
          ANDROID_PACKAGE="$reply"
          break
        fi
        echo "[WARN] Android package must look like com.acme.app (reverse-DNS, lowercase)."
      done
    fi

    WITH_I18N="$(_prompt_scaffold_yes_no "  Enable i18n stub?" "$WITH_I18N")"
    WITH_AUTH="$(_prompt_scaffold_yes_no "  Enable auth stub?" "$WITH_AUTH")"

    # Preview
    echo ""
    echo "[INFO] You entered:"
    echo "    PROJECT_NAME    = ${PROJECT_NAME}"
    echo "    SRC_DIR         = ${SRC_DIR}"
    echo "    API_VERSION     = ${API_VERSION}"
    echo "    FEATURES_CSV    = ${FEATURES_CSV:-<none>}"
    [[ "$platform" == "android" ]] && echo "    ANDROID_PACKAGE = ${ANDROID_PACKAGE}"
    echo "    WITH_I18N       = ${WITH_I18N}"
    echo "    WITH_AUTH       = ${WITH_AUTH}"

    read -r -p "  Looks good? [Y/n] " reply
    reply="${reply:-y}"
    case "$reply" in
      [Yy]|[Yy][Ee][Ss]) confirmed="y" ;;
      *)                 echo "[INFO] Let's try again." ;;
    esac
  done
}
