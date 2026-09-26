#!/bin/bash
# ============================================================================
# Render Library (mobile) — stamp Expo + React Native + TypeScript starter
#
# Describes the mobile platform for lib/render-core.sh, which walks
# templates/_shared/ + templates/mobile/ and writes the target tree.
# The `_screen_template/` tree under src/screens/ is iterated once per screen
# in FEATURES_CSV (or stamped literally if it is empty); the per-iteration
# token is __SCREEN__. WITH_AUTH gates src/features/auth/.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-mobile.sh"
#   render_mobile_all "/path/to/target"
# ============================================================================

set -euo pipefail

RENDER_MOBILE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=render-core.sh
source "${RENDER_MOBILE_LIB_DIR}/render-core.sh"

render_mobile_export_vars() {
  # Stack vars consumed by the shared templates' conditional blocks.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="false"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="expo, react-native, typescript"

  # Mobile ignores WITH_I18N today; exported so shared conditionals resolve.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — normally filled by prompt-scaffold.sh.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  SRC_DIR="${SRC_DIR:-src}"
  FEATURES_CSV="${FEATURES_CSV:-}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"
  # Mobile is screen-oriented, not REST-versioned; empty unless provided.
  API_VERSION="${API_VERSION:-}"

  # Reverse-DNS-safe form of PROJECT_SLUG for app.json (Android package names
  # disallow hyphens).
  PROJECT_PACKAGE_ID="$(printf '%s' "$PROJECT_SLUG" | tr '[:upper:]-' '[:lower:]_')"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG PROJECT_PACKAGE_ID SRC_DIR API_VERSION \
         FEATURES_CSV TIMESTAMP
}

# shellcheck disable=SC2034  # descriptor globals are read by render-core.sh
render_mobile_describe() {
  # shellcheck disable=SC2016
  RC_ENVSUBST_VARS='${PROJECT_NAME} ${PROJECT_SLUG} ${PROJECT_PACKAGE_ID} ${SRC_DIR} ${API_VERSION}
     ${FEATURES_CSV} ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${SCREEN_NAME} ${SCREEN_SLUG}'
  RC_SRC_REMAP="true"
  RC_REQUIRED_DIRS_VAR="MOBILE_REQUIRED_DIRS"
  RC_ITEM_DIR="src/screens/_screen_template"
  RC_ITEM_LITERAL="_screen_template"
  RC_ITEM_TOKEN="__SCREEN__"
  RC_ITEM_VAR="SCREEN"
  RC_ITEM_NOUN="screen"
  RC_ITEM_PREFIX="${SRC_DIR}/screens"
}

render_mobile_required_dirs() {
  MOBILE_REQUIRED_DIRS="${SRC_DIR},${SRC_DIR}/config,${SRC_DIR}/navigation,${SRC_DIR}/screens,${SRC_DIR}/screens/home,${SRC_DIR}/features,${SRC_DIR}/components,${SRC_DIR}/hooks,${SRC_DIR}/lib,${SRC_DIR}/api,${SRC_DIR}/types,assets,docs"
  export MOBILE_REQUIRED_DIRS
}

render_mobile_should_skip() {
  case "$1" in
    src/features/auth/*) [[ "$WITH_AUTH" != "true" ]] && return 0 ;;
  esac
  return 1
}

render_mobile_all() { rc_render_all mobile "${1:-}"; }

export -f render_mobile_all
