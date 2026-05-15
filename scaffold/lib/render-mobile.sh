#!/bin/bash
# ============================================================================
# Render Library (mobile) — stamp Expo + React Native + TypeScript starter
#
# Walks ${SCRIPT_DIR}/templates/_shared/ + ${SCRIPT_DIR}/templates/mobile/
# recursively, computes each output path under the target directory, performs
# ${VAR} substitution + conditional-block processing, and writes the result.
# The `_screen_template/` tree inside the mobile template is iterated once
# per screen in FEATURES_CSV (or stamped literally if FEATURES_CSV is empty).
#
# Mirrors render-backend.sh — same conditional-block syntax, same envsubst
# whitelist behaviour, same backup-on-clobber discipline. The differences
# are mobile-specific: no API_VERSION (mobile is screen-oriented, not
# REST-versioned), the working example is `screens/home/` instead of
# `api/v1/health/`, and the per-iteration token is __SCREEN__ rather than
# __FEATURE__.
#
# Substitution variables (exported by init-scaffold.sh + prompt-scaffold.sh):
#   PROJECT_NAME, PROJECT_SLUG, SRC_DIR, FEATURES_CSV,
#   WITH_AUTH, TIMESTAMP, PLATFORM, TARGET_DIR, FORCE, BACKUP_TS
#
# Conditional-block syntax inside templates (re-used from render.sh):
#   <!-- {{IF WITH_AUTH}} -->
#   ...lines emitted only when WITH_AUTH=true...
#   <!-- {{ENDIF}} -->
#
# Path tokens:
#   Directories named exactly `__SCREEN__` are iterated per-screen when
#   FEATURES_CSV is non-empty (one rendered copy per screen, with SCREEN_NAME
#   substituted into the file contents). When FEATURES_CSV is empty the
#   `_screen_template/` tree is stamped literally so the user can rename it.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-mobile.sh"
#   render_mobile_all "/path/to/target"
# ============================================================================

set -euo pipefail

# Resolve our own dir so templates/ is locatable even if this lib is sourced
# stand-alone. SCRIPT_DIR is normally set by init-scaffold.sh.
RENDER_MOBILE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_MOBILE_SCAFFOLD_DIR="$(cd "${RENDER_MOBILE_LIB_DIR}/.." && pwd)"
SCRIPT_DIR="${SCRIPT_DIR:-${RENDER_MOBILE_SCAFFOLD_DIR}}"

# ----------------------------------------------------------------------------
# render_mobile_export_vars — normalise / export every var .tmpl files use
# ----------------------------------------------------------------------------
render_mobile_export_vars() {
  # Stack vars consumed by shared templates copied from render.sh's vocabulary.
  # Mobile templates are stamped from a known stack so we hardwire HAS_BASH
  # to true (lint runs via bash) and leave the others false. Conditional-block
  # logic re-uses these so the shared docs keep working.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="false"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="expo, react-native, typescript"

  # Boolean flag driving optional blocks inside mobile templates. WITH_I18N
  # isn't currently consumed by mobile templates but we still export it so
  # the shared conditional-block stripper has a value to read.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — these should be filled by prompt-scaffold.sh, but we
  # want the renderer to work even when invoked directly in tests.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  SRC_DIR="${SRC_DIR:-src}"
  FEATURES_CSV="${FEATURES_CSV:-}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"

  # API_VERSION isn't used by mobile templates but the shared conditional-
  # block stripper / envsubst whitelist references it; default to empty so
  # nothing breaks when shared templates reference ${API_VERSION}.
  API_VERSION="${API_VERSION:-}"

  # PROJECT_PACKAGE_ID — Android/iOS reverse-DNS-safe form of PROJECT_SLUG.
  # Android package names disallow hyphens; iOS bundle ids accept them but
  # convention prefers underscores. We compute it once here so app.json
  # stays in sync across both platforms.
  PROJECT_PACKAGE_ID="$(printf '%s' "$PROJECT_SLUG" | tr '[:upper:]-' '[:lower:]_')"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG PROJECT_PACKAGE_ID SRC_DIR API_VERSION \
         FEATURES_CSV TIMESTAMP
}

# ----------------------------------------------------------------------------
# render_mobile_should_skip — drop templates that don't apply
# Args: $1 = path relative to the mobile/ template root
# ----------------------------------------------------------------------------
render_mobile_should_skip() {
  local rel="$1"
  case "$rel" in
    src/features/auth/*)
      [[ "$WITH_AUTH" != "true" ]] && return 0
      ;;
  esac
  return 1
}

# ----------------------------------------------------------------------------
# render_mobile_substitute — strip conditional blocks + envsubst on stdin
# Args: $1 = source file
# Echoes the rendered content. The conditional-block stripper is the same
# AWK logic used by lib/render.sh extended with the flags this renderer
# cares about.
# ----------------------------------------------------------------------------
render_mobile_substitute() {
  local src="$1"

  local processed
  processed="$(awk -v with_i18n="$WITH_I18N" \
                   -v with_auth="$WITH_AUTH" \
                   -v has_bash="$HAS_BASH" \
                   -v has_ansible="$HAS_ANSIBLE" \
                   -v has_compose="$HAS_COMPOSE" \
                   -v has_terraform="$HAS_TERRAFORM" \
                   -v has_git="$HAS_GIT" \
                   -v no_stacks="$NO_STACKS" '
    BEGIN { skip = 0 }
    /^[[:space:]]*(#|\/\/|<!--)[[:space:]]*\{\{IF [A-Z_]+\}\}([[:space:]]*-->)?[[:space:]]*$/ {
      match($0, /\{\{IF [A-Z_]+\}\}/)
      var = substr($0, RSTART + 5, RLENGTH - 7)
      val = "false"
      if (var == "WITH_I18N")     val = with_i18n
      if (var == "WITH_AUTH")     val = with_auth
      if (var == "HAS_BASH")      val = has_bash
      if (var == "HAS_ANSIBLE")   val = has_ansible
      if (var == "HAS_COMPOSE")   val = has_compose
      if (var == "HAS_TERRAFORM") val = has_terraform
      if (var == "HAS_GIT")       val = has_git
      if (var == "NO_STACKS")     val = no_stacks
      if (val != "true") { skip = 1 }
      next
    }
    /^[[:space:]]*(#|\/\/|<!--)[[:space:]]*\{\{ENDIF\}\}([[:space:]]*-->)?[[:space:]]*$/ {
      skip = 0
      next
    }
    { if (!skip) print }
  ' "$src")"

  # envsubst with an explicit whitelist so literal `$X` references inside
  # TypeScript / JS code are left alone. We add SCREEN_NAME + SCREEN_SLUG
  # for the per-screen stamping pass below.
  printf '%s\n' "$processed" | envsubst \
    '${PROJECT_NAME} ${PROJECT_SLUG} ${PROJECT_PACKAGE_ID} ${SRC_DIR} ${API_VERSION}
     ${FEATURES_CSV} ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${SCREEN_NAME} ${SCREEN_SLUG}'
}

# ----------------------------------------------------------------------------
# render_mobile_write_file — emit a single file into the target, with backup
# Args: $1 = source template (already chosen), $2 = target absolute path
# ----------------------------------------------------------------------------
render_mobile_write_file() {
  local src="$1"
  local out_path="$2"

  if [[ "${FORCE:-false}" == "true" && -e "$out_path" ]]; then
    local rel="${out_path#${TARGET_DIR}/}"
    local backup_path="${TARGET_DIR}/.claude.bak/${BACKUP_TS}/${rel}"
    mkdir -p "$(dirname "$backup_path")"
    cp "$out_path" "$backup_path"
    BACKUP_MADE="true"
    export BACKUP_MADE
    echo "[INFO] Backed up ${rel} to .claude.bak/${BACKUP_TS}/"
  fi

  mkdir -p "$(dirname "$out_path")"

  case "$src" in
    *.tmpl)
      render_mobile_substitute "$src" > "$out_path"
      ;;
    *)
      # Plain copy — no substitution. We still go through the staging path so
      # the file lands atomically.
      cp "$src" "$out_path"
      ;;
  esac

  CREATED_FILES+=("$out_path")
  echo "[OK]   wrote ${out_path}"
}

# ----------------------------------------------------------------------------
# render_mobile_target_relpath — convert a template-relative path to its
# output-relative path. Strips the trailing .tmpl, renames dotfile templates,
# and swaps __SCREEN__ for the value passed in $2 (when iterating screens).
# Args: $1 = template relpath, $2 = screen name (or empty)
# ----------------------------------------------------------------------------
render_mobile_target_relpath() {
  local rel="$1"
  local screen="${2:-}"

  # Strip .tmpl suffix.
  local stripped="${rel%.tmpl}"

  # Dotfile renames — templates store these without a leading dot so they
  # aren't accidentally hidden in the templates directory.
  case "$stripped" in
    editorconfig)              stripped=".editorconfig" ;;
    gitignore)                 stripped=".gitignore" ;;
    env.example|.env.example)  stripped=".env.example" ;;
  esac

  # __SCREEN__ in directory segments → real screen (when iterating).
  if [[ -n "$screen" ]]; then
    stripped="${stripped//__SCREEN__/${screen}}"
  fi

  printf '%s' "$stripped"
}

# ----------------------------------------------------------------------------
# render_mobile_stamp_shared — pass 1: stamp _shared/ templates
# ----------------------------------------------------------------------------
render_mobile_stamp_shared() {
  local target="$1"
  local shared_dir="${SCRIPT_DIR}/templates/_shared"

  if [[ ! -d "$shared_dir" ]]; then
    echo "[WARN] _shared/ template dir not found: ${shared_dir}"
    return 0
  fi

  echo "[INFO] Stamping _shared/ templates"
  local tmpl rel out_rel out_path
  while IFS= read -r -d '' tmpl; do
    rel="${tmpl#${shared_dir}/}"

    # Map _shared filenames to their final on-disk names.
    case "$rel" in
      CLAUDE.md.tmpl)             out_rel="CLAUDE.md" ;;
      AI_RULES.md.tmpl)           out_rel="AI_RULES.md" ;;
      README.md.tmpl)             out_rel="README.md" ;;
      editorconfig.tmpl)          out_rel=".editorconfig" ;;
      gitignore.tmpl)             out_rel=".gitignore" ;;
      mcp.json.tmpl)              out_rel=".claude/mcp.json" ;;
      docs/*.tmpl)
        out_rel="${rel%.tmpl}"
        ;;
      *)
        out_rel="${rel%.tmpl}"
        ;;
    esac

    out_path="${target}/${out_rel}"
    render_mobile_write_file "$tmpl" "$out_path"
  done < <(find "$shared_dir" -type f -name '*.tmpl' -print0)

  # docs/plans/ should exist with a .gitkeep — kept by the shared layer.
  mkdir -p "${target}/docs/plans"
  if [[ ! -f "${target}/docs/plans/.gitkeep" ]]; then
    : > "${target}/docs/plans/.gitkeep"
    CREATED_FILES+=("${target}/docs/plans/.gitkeep")
  fi
}

# ----------------------------------------------------------------------------
# render_mobile_stamp_main — pass 2: stamp mobile/ non-_screen_template/
# files (everything except the _screen_template/ subtree).
# ----------------------------------------------------------------------------
render_mobile_stamp_main() {
  local target="$1"
  local mobile_dir="${SCRIPT_DIR}/templates/mobile"

  if [[ ! -d "$mobile_dir" ]]; then
    echo "[FAIL] mobile/ template dir not found: ${mobile_dir}" >&2
    return 1
  fi

  echo "[INFO] Stamping mobile/ templates (main pass)"
  local src rel out_rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${mobile_dir}/}"

    # Skip _screen_template/ subtree — handled separately.
    case "$rel" in
      */_screen_template/*|_screen_template/*) continue ;;
    esac

    if render_mobile_should_skip "$rel"; then
      echo "[INFO]   skip ${rel}"
      continue
    fi

    out_rel="$(render_mobile_target_relpath "$rel" "")"
    out_path="${target}/${out_rel}"
    render_mobile_write_file "$src" "$out_path"
  done < <(find "$mobile_dir" -type f -print0)
}

# ----------------------------------------------------------------------------
# render_mobile_stamp_screen_template — pass 3
#
# Walk the _screen_template/ subtree once per screen in FEATURES_CSV (or
# once literally if FEATURES_CSV is empty). When iterating, the destination
# folder is the screen name and SCREEN_NAME / SCREEN_SLUG are exported so
# .tmpl bodies can reference them.
# ----------------------------------------------------------------------------
render_mobile_stamp_screen_template() {
  local target="$1"
  local mobile_dir="${SCRIPT_DIR}/templates/mobile"
  local st_dir="${mobile_dir}/src/screens/_screen_template"

  if [[ ! -d "$st_dir" ]]; then
    echo "[WARN] _screen_template/ not found under mobile templates: ${st_dir}"
    return 0
  fi

  if [[ -z "${FEATURES_CSV:-}" ]]; then
    echo "[INFO] FEATURES_CSV empty — stamping _screen_template/ literally"
    _render_mobile_stamp_screen_template_one "$target" "$st_dir" "_screen_template" ""
    return 0
  fi

  echo "[INFO] FEATURES_CSV='${FEATURES_CSV}' — iterating per-screen stamps"
  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local screens=( $FEATURES_CSV )
  IFS="$old_ifs"

  local screen
  for screen in "${screens[@]}"; do
    screen="$(printf '%s' "$screen" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$screen" ]] && continue
    _render_mobile_stamp_screen_template_one "$target" "$st_dir" "$screen" "$screen"
  done
}

# Internal helper — stamp _screen_template/ once into <screens>/<dest_folder>/.
# Args: $1 = target, $2 = template _screen_template/ dir, $3 = destination
#       folder name (e.g. "settings" or "_screen_template"), $4 = screen name
#       to substitute into bodies (empty when stamping literally).
_render_mobile_stamp_screen_template_one() {
  local target="$1"
  local st_dir="$2"
  local dest_folder="$3"
  local screen="$4"

  # Export SCREEN_NAME / SCREEN_SLUG so .tmpl bodies can use them.
  SCREEN_NAME="${screen:-_screen_template}"
  SCREEN_SLUG="$(printf '%s' "$SCREEN_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [[ -z "$SCREEN_SLUG" ]] && SCREEN_SLUG="$SCREEN_NAME"
  export SCREEN_NAME SCREEN_SLUG

  local src rel inside out_rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${st_dir}/}"

    # inside = path inside the screen folder.
    inside="$rel"

    # When iterating screens, file basenames containing __SCREEN__ get
    # swapped to the screen name. When stamping literally we keep the
    # __SCREEN__ token in the filename so the user can rename later.
    if [[ -n "$screen" ]]; then
      inside="${inside//__SCREEN__/${screen}}"
    fi

    # Strip the .tmpl suffix.
    inside="${inside%.tmpl}"

    out_rel="${SRC_DIR}/screens/${dest_folder}/${inside}"
    out_path="${target}/${out_rel}"
    render_mobile_write_file "$src" "$out_path"
  done < <(find "$st_dir" -type f -print0)

  # Unset screen vars between iterations so the next pass starts clean.
  unset SCREEN_NAME SCREEN_SLUG
}

# ----------------------------------------------------------------------------
# render_mobile_ensure_dirs — guarantee every architectural folder exists
# even if the templates didn't populate a leaf file. Mirrors the
# MOBILE_REQUIRED_DIRS contract expected by validate-scaffold.sh.
# ----------------------------------------------------------------------------
render_mobile_ensure_dirs() {
  local target="$1"

  # MOBILE_REQUIRED_DIRS is the source of truth — split it, mkdir each one.
  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local dirs=( $MOBILE_REQUIRED_DIRS )
  IFS="$old_ifs"

  local d
  for d in "${dirs[@]}"; do
    d="$(printf '%s' "$d" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$d" ]] && continue
    mkdir -p "${target}/${d}"
  done
}

# ----------------------------------------------------------------------------
# render_mobile_all — public entrypoint
# Args: $1 = target directory (absolute)
# ----------------------------------------------------------------------------
render_mobile_all() {
  local target="$1"

  if [[ -z "$target" ]]; then
    echo "[FAIL] render_mobile_all requires a target dir" >&2
    return 1
  fi

  render_mobile_export_vars

  # Export the required-dirs contract BEFORE rendering so validate-scaffold.sh
  # has a value if the renderer aborts mid-flight.
  MOBILE_REQUIRED_DIRS="${SRC_DIR},${SRC_DIR}/config,${SRC_DIR}/navigation,${SRC_DIR}/screens,${SRC_DIR}/screens/home,${SRC_DIR}/features,${SRC_DIR}/components,${SRC_DIR}/hooks,${SRC_DIR}/lib,${SRC_DIR}/api,${SRC_DIR}/types,assets,docs"
  export MOBILE_REQUIRED_DIRS

  render_mobile_stamp_shared "$target"
  render_mobile_stamp_main "$target"
  render_mobile_stamp_screen_template "$target"
  render_mobile_ensure_dirs "$target"
}

export -f render_mobile_all
