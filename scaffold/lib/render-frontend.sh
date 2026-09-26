#!/bin/bash
# ============================================================================
# Render Library (frontend) — stamp Vite + React + TypeScript starter
#
# Describes the frontend platform for lib/render-core.sh, which walks
# templates/_shared/ + templates/frontend/ and writes the target tree.
# The `_feature_template/` tree under src/features/ is iterated once per
# feature in FEATURES_CSV (or stamped literally if it is empty). WITH_AUTH
# gates the optional src/features/auth/ stub.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-frontend.sh"
#   render_frontend_all "/path/to/target"
# ============================================================================

set -euo pipefail

RENDER_FRONTEND_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=render-core.sh
source "${RENDER_FRONTEND_LIB_DIR}/render-core.sh"

render_frontend_export_vars() {
  # Stack vars consumed by the shared templates' conditional blocks.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="false"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="react, typescript, vite"

  # Frontend ignores WITH_I18N today; exported so shared conditionals resolve.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — normally filled by prompt-scaffold.sh.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  SRC_DIR="${SRC_DIR:-src}"
  FEATURES_CSV="${FEATURES_CSV:-}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"
  # The shared README mentions API_VERSION; frontend paths never embed it.
  API_VERSION="${API_VERSION:-v1}"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION FEATURES_CSV TIMESTAMP
}

# shellcheck disable=SC2034  # descriptor globals are read by render-core.sh
render_frontend_describe() {
  # shellcheck disable=SC2016
  RC_ENVSUBST_VARS='${PROJECT_NAME} ${PROJECT_SLUG} ${SRC_DIR} ${API_VERSION}
     ${FEATURES_CSV} ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${FEATURE_NAME} ${FEATURE_SLUG}'
  RC_SRC_REMAP="true"
  RC_REQUIRED_DIRS_VAR="FRONTEND_REQUIRED_DIRS"
  RC_ITEM_DIR="src/features/_feature_template"
  RC_ITEM_LITERAL="_feature_template"
  RC_ITEM_TOKEN="__FEATURE__"
  RC_ITEM_VAR="FEATURE"
  RC_ITEM_NOUN="feature"
  RC_ITEM_PREFIX="${SRC_DIR}/features"
}

render_frontend_required_dirs() {
  FRONTEND_REQUIRED_DIRS="${SRC_DIR},${SRC_DIR}/config,${SRC_DIR}/components,${SRC_DIR}/features,${SRC_DIR}/features/health,${SRC_DIR}/hooks,${SRC_DIR}/lib,${SRC_DIR}/routes,${SRC_DIR}/styles,${SRC_DIR}/types,${SRC_DIR}/tests,docs"
  export FRONTEND_REQUIRED_DIRS
}

render_frontend_should_skip() {
  case "$1" in
    src/features/auth/*) [[ "$WITH_AUTH" != "true" ]] && return 0 ;;
  esac
  return 1
}

render_frontend_all() { rc_render_all frontend "${1:-}"; }

export -f render_frontend_all
