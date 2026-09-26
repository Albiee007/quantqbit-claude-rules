#!/bin/bash
# ============================================================================
# Render Library (android) — stamp Kotlin + Compose + Retrofit starter
#
# Describes the android platform for lib/render-core.sh, which walks
# templates/_shared/ + templates/android/ and writes the target tree.
# Android has no per-item pass: `_feature_template/` is stamped literally as a
# renamable folder (features are usually added one at a time in Android
# Studio), and the android tree is not remapped under SRC_DIR.
#
# Stack non-goals (per review decision #6): no Hilt, no Room, no KSP. DI is a
# plain `core/di/AppGraph.kt` service-locator wired in by the Application
# class.
#
# Path tokens: `__PACKAGE_PATH__` → the package path (dots → slashes, e.g.
# com/acme/app for ANDROID_PACKAGE=com.acme.app).
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-android.sh"
#   render_android_all "/path/to/target"
# ============================================================================

set -euo pipefail

RENDER_ANDROID_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=render-core.sh
source "${RENDER_ANDROID_LIB_DIR}/render-core.sh"

render_android_export_vars() {
  # Stack vars consumed by the shared templates' conditional blocks. No
  # Docker Compose: the Gradle build is the canonical entry point.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="false"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="kotlin, compose, retrofit"

  # Unused by android templates; exported so shared conditionals resolve.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — normally filled by prompt-scaffold.sh.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  ANDROID_PACKAGE="${ANDROID_PACKAGE:-com.example.app}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"
  # The shared README/CLAUDE.md mention these; android paths never embed them.
  SRC_DIR="${SRC_DIR:-app/src/main}"
  API_VERSION="${API_VERSION:-v1}"

  # Derived: com.acme.app → com/acme/app, for __PACKAGE_PATH__ tokens.
  ANDROID_PACKAGE_PATH="${ANDROID_PACKAGE//./\/}"
  # Derived: application-class prefix, casing kept as given (MyAppApplication).
  APP_CLASS_PREFIX="${PROJECT_NAME}"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION TIMESTAMP \
         ANDROID_PACKAGE ANDROID_PACKAGE_PATH APP_CLASS_PREFIX
}

# shellcheck disable=SC2034  # descriptor globals are read by render-core.sh
render_android_describe() {
  # Kotlin string templates (`$variable`) survive: only these are substituted.
  # shellcheck disable=SC2016
  RC_ENVSUBST_VARS='${PROJECT_NAME} ${PROJECT_SLUG} ${SRC_DIR} ${API_VERSION}
     ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${ANDROID_PACKAGE} ${ANDROID_PACKAGE_PATH} ${APP_CLASS_PREFIX}'
  RC_EXEC_GLOBS='*/gradlew *.sh'
  RC_REQUIRED_DIRS_VAR="ANDROID_REQUIRED_DIRS"
}

render_android_required_dirs() {
  ANDROID_REQUIRED_DIRS="app,app/src/main,app/src/main/java,app/src/main/java/__PACKAGE_PATH__,app/src/main/java/__PACKAGE_PATH__/core,app/src/main/java/__PACKAGE_PATH__/features,app/src/main/java/__PACKAGE_PATH__/features/home,app/src/main/java/__PACKAGE_PATH__/navigation,app/src/main/res,docs"
  ANDROID_REQUIRED_DIRS="${ANDROID_REQUIRED_DIRS//__PACKAGE_PATH__/${ANDROID_PACKAGE_PATH}}"
  export ANDROID_REQUIRED_DIRS
}

render_android_map_tokens() {
  RC_REL="${RC_REL//__PACKAGE_PATH__/${ANDROID_PACKAGE_PATH}}"
}

render_android_all() { rc_render_all android "${1:-}"; }

export -f render_android_all
