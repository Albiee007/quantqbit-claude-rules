#!/bin/bash
# ============================================================================
# Render Library (backend) — stamp Node + TypeScript + Express starter
#
# Describes the backend platform for lib/render-core.sh, which walks
# templates/_shared/ + templates/backend/ and writes the target tree.
# The `_feature_template/` tree under src/api/__API_VERSION__/ is iterated
# once per feature in FEATURES_CSV (or stamped literally if it is empty).
#
# Path tokens: `__API_VERSION__` → ${API_VERSION} (e.g. v1); `__FEATURE__` →
# the feature name while iterating.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-backend.sh"
#   render_backend_all "/path/to/target"
# ============================================================================

set -euo pipefail

RENDER_BACKEND_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=render-core.sh
source "${RENDER_BACKEND_LIB_DIR}/render-core.sh"

render_backend_export_vars() {
  # Stack vars consumed by the shared templates' conditional blocks.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="true"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="node, typescript, express"

  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — normally filled by prompt-scaffold.sh.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  SRC_DIR="${SRC_DIR:-src}"
  API_VERSION="${API_VERSION:-v1}"
  FEATURES_CSV="${FEATURES_CSV:-}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION FEATURES_CSV TIMESTAMP
}

# shellcheck disable=SC2034  # descriptor globals are read by render-core.sh
render_backend_describe() {
  # shellcheck disable=SC2016
  RC_ENVSUBST_VARS='${PROJECT_NAME} ${PROJECT_SLUG} ${SRC_DIR} ${API_VERSION}
     ${FEATURES_CSV} ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${FEATURE_NAME} ${FEATURE_SLUG}'
  RC_SRC_REMAP="true"
  RC_REQUIRED_DIRS_VAR="BACKEND_REQUIRED_DIRS"
  RC_ITEM_DIR="src/api/__API_VERSION__/_feature_template"
  RC_ITEM_LITERAL="_feature_template"
  RC_ITEM_TOKEN="__FEATURE__"
  RC_ITEM_VAR="FEATURE"
  RC_ITEM_NOUN="feature"
  RC_ITEM_PREFIX="${SRC_DIR}/api/${API_VERSION}"
}

render_backend_required_dirs() {
  BACKEND_REQUIRED_DIRS="${SRC_DIR},${SRC_DIR}/config,${SRC_DIR}/middlewares,${SRC_DIR}/models,${SRC_DIR}/lib,${SRC_DIR}/api/${API_VERSION},${SRC_DIR}/api/${API_VERSION}/health,${SRC_DIR}/types,${SRC_DIR}/tests,docs,migrations/postgres,scripts"
  export BACKEND_REQUIRED_DIRS
}

render_backend_should_skip() {
  case "$1" in
    src/config/i18n/*) [[ "$WITH_I18N" != "true" ]] && return 0 ;;
  esac
  return 1
}

render_backend_map_tokens() {
  RC_REL="${RC_REL//__API_VERSION__/${API_VERSION}}"
}

render_backend_all() { rc_render_all backend "${1:-}"; }

export -f render_backend_all
