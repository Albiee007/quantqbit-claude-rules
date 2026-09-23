#!/bin/bash
# ============================================================================
# Render Library (backend) — stamp Node + TypeScript starter into the target
#
# Walks ${SCRIPT_DIR}/templates/_shared/ + ${SCRIPT_DIR}/templates/backend/
# recursively, computes each output path under the target directory, performs
# ${VAR} substitution + conditional-block processing, and writes the result.
# The `_feature_template/` tree inside the backend template is iterated once
# per feature in FEATURES_CSV (or stamped literally if FEATURES_CSV is empty).
#
# Substitution variables (exported by init-scaffold.sh + prompt-scaffold.sh):
#   PROJECT_NAME, PROJECT_SLUG, SRC_DIR, API_VERSION, FEATURES_CSV,
#   WITH_I18N, WITH_AUTH, TIMESTAMP, PLATFORM, TARGET_DIR, FORCE, BACKUP_TS
#
# Conditional-block syntax inside templates (re-used from render.sh):
#   <!-- {{IF WITH_I18N}} -->
#   ...lines emitted only when WITH_I18N=true...
#   <!-- {{ENDIF}} -->
#
# Path tokens:
#   Directories named exactly `__API_VERSION__` are renamed at stamp time to
#   the resolved ${API_VERSION} value (e.g. v1). Directories named exactly
#   `__FEATURE__` are iterated per-feature when FEATURES_CSV is non-empty
#   (one rendered copy per feature, with FEATURE_NAME substituted into the
#   file contents). When FEATURES_CSV is empty the `_feature_template/` tree
#   is stamped literally so the user can rename it manually.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-backend.sh"
#   render_backend_all "/path/to/target"
# ============================================================================

set -euo pipefail

# Resolve our own dir so templates/ is locatable even if this lib is sourced
# stand-alone. SCRIPT_DIR is normally set by init-scaffold.sh.
RENDER_BACKEND_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_BACKEND_SCAFFOLD_DIR="$(cd "${RENDER_BACKEND_LIB_DIR}/.." && pwd)"
SCRIPT_DIR="${SCRIPT_DIR:-${RENDER_BACKEND_SCAFFOLD_DIR}}"

# ----------------------------------------------------------------------------
# render_backend_export_vars — normalise / export every var .tmpl files use
# ----------------------------------------------------------------------------
render_backend_export_vars() {
  # Stack vars consumed by shared templates copied from render.sh's vocabulary.
  # Backend templates are stamped from a known stack so we hardwire HAS_BASH
  # to true (lint.sh is bash) and leave the others false. Conditional-block
  # logic re-uses these so the shared docs keep working.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="true"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="node, typescript, express"

  # Boolean flags driving optional blocks inside backend templates.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — these should be filled by prompt-scaffold.sh, but we
  # want the renderer to work even when invoked directly in tests.
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

# ----------------------------------------------------------------------------
# render_backend_should_skip — drop templates that don't apply
# Args: $1 = path relative to the backend/ template root
# ----------------------------------------------------------------------------
render_backend_should_skip() {
  local rel="$1"
  case "$rel" in
    src/config/i18n/*)
      [[ "$WITH_I18N" != "true" ]] && return 0
      ;;
  esac
  return 1
}

# ----------------------------------------------------------------------------
# render_backend_substitute — strip conditional blocks + envsubst on stdin
# Args: $1 = source file
# Echoes the rendered content. The conditional-block stripper is the same
# AWK logic used by lib/render.sh but extended with the WITH_I18N / WITH_AUTH
# flags this renderer cares about.
# ----------------------------------------------------------------------------
render_backend_substitute() {
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
  # TypeScript / JS code are left alone. We add FEATURE_NAME + FEATURE_SLUG
  # for the per-feature stamping pass below.
  printf '%s\n' "$processed" | envsubst \
    '${PROJECT_NAME} ${PROJECT_SLUG} ${SRC_DIR} ${API_VERSION}
     ${FEATURES_CSV} ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${FEATURE_NAME} ${FEATURE_SLUG}'
}

# ----------------------------------------------------------------------------
# render_backend_write_file — emit a single file into the target, with backup
# Args: $1 = source template (already chosen), $2 = target absolute path
# ----------------------------------------------------------------------------
render_backend_write_file() {
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
      render_backend_substitute "$src" > "$out_path"
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
# render_backend_target_relpath — convert a template-relative path to its
# output-relative path. Strips the trailing .tmpl, swaps __API_VERSION__ for
# the resolved ${API_VERSION} value, and swaps __FEATURE__ for the value
# passed in $2 (when iterating features).
# Args: $1 = template relpath, $2 = feature name (or empty)
# ----------------------------------------------------------------------------
render_backend_target_relpath() {
  local rel="$1"
  local feature="${2:-}"

  # Strip .tmpl suffix.
  local stripped="${rel%.tmpl}"

  # Dotfile renames — templates store these without a leading dot so they
  # aren't accidentally hidden in the templates directory.
  case "$stripped" in
    editorconfig)              stripped=".editorconfig" ;;
    gitignore)                 stripped=".gitignore" ;;
    env.example|.env.example)  stripped=".env.example" ;;
  esac

  # __API_VERSION__ in directory segments → real API version.
  stripped="${stripped//__API_VERSION__/${API_VERSION}}"

  # __FEATURE__ in directory segments → real feature (when iterating).
  if [[ -n "$feature" ]]; then
    stripped="${stripped//__FEATURE__/${feature}}"
  fi

  printf '%s' "$stripped"
}

# ----------------------------------------------------------------------------
# render_backend_stamp_shared — pass 1: stamp _shared/ templates
# ----------------------------------------------------------------------------
render_backend_stamp_shared() {
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
      mcp.json.tmpl)              out_rel=".mcp.json" ;;  # Claude Code reads project MCP from root .mcp.json
      docs/*.tmpl)
        out_rel="${rel%.tmpl}"
        ;;
      *)
        out_rel="${rel%.tmpl}"
        ;;
    esac

    out_path="${target}/${out_rel}"
    # Project-owned instruction files are write-if-absent (never clobbered,
    # even by --force). CLAUDE.md is also skipped next to an AGENTS.md, since
    # Claude Code stops reading AGENTS.md once a CLAUDE.md exists.
    case "$out_rel" in
      CLAUDE.md|AI_RULES.md|.mcp.json)
        if [[ -e "$out_path" ]]; then
          echo "[INFO] kept existing project file: ${out_rel}"
          continue
        fi
        if [[ "$out_rel" == "CLAUDE.md" && -e "${target}/AGENTS.md" ]]; then
          echo "[INFO] skipped CLAUDE.md: AGENTS.md exists (a CLAUDE.md would stop Claude Code reading it)"
          continue
        fi ;;
    esac
    render_backend_write_file "$tmpl" "$out_path"
  done < <(find "$shared_dir" -type f -name '*.tmpl' -print0)

  # docs/plans/ should exist with a .gitkeep — kept by the shared layer.
  mkdir -p "${target}/docs/plans"
  if [[ ! -f "${target}/docs/plans/.gitkeep" ]]; then
    : > "${target}/docs/plans/.gitkeep"
    CREATED_FILES+=("${target}/docs/plans/.gitkeep")
  fi
}

# ----------------------------------------------------------------------------
# render_backend_stamp_main — pass 2: stamp backend/ non-_feature_template/
# files (everything except the _feature_template/ subtree).
# ----------------------------------------------------------------------------
render_backend_stamp_main() {
  local target="$1"
  local backend_dir="${SCRIPT_DIR}/templates/backend"

  if [[ ! -d "$backend_dir" ]]; then
    echo "[FAIL] backend/ template dir not found: ${backend_dir}" >&2
    return 1
  fi

  echo "[INFO] Stamping backend/ templates (main pass)"
  local src rel out_rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${backend_dir}/}"

    # Skip _feature_template/ subtree — handled separately.
    case "$rel" in
      */_feature_template/*|_feature_template/*) continue ;;
    esac

    if render_backend_should_skip "$rel"; then
      echo "[INFO]   skip ${rel}"
      continue
    fi

    out_rel="$(render_backend_target_relpath "$rel" "")"
    out_path="${target}/${out_rel}"
    render_backend_write_file "$src" "$out_path"
  done < <(find "$backend_dir" -type f -print0)
}

# ----------------------------------------------------------------------------
# render_backend_stamp_feature_template — pass 3
#
# Walk the _feature_template/ subtree once per feature in FEATURES_CSV (or
# once literally if FEATURES_CSV is empty). When iterating, the destination
# folder is the feature name and FEATURE_NAME / FEATURE_SLUG are exported so
# .tmpl bodies can reference them.
# ----------------------------------------------------------------------------
render_backend_stamp_feature_template() {
  local target="$1"
  local backend_dir="${SCRIPT_DIR}/templates/backend"
  local ft_dir="${backend_dir}/src/api/__API_VERSION__/_feature_template"

  if [[ ! -d "$ft_dir" ]]; then
    echo "[WARN] _feature_template/ not found under backend templates: ${ft_dir}"
    return 0
  fi

  if [[ -z "${FEATURES_CSV:-}" ]]; then
    echo "[INFO] FEATURES_CSV empty — stamping _feature_template/ literally"
    _render_backend_stamp_feature_template_one "$target" "$ft_dir" "_feature_template" ""
    return 0
  fi

  echo "[INFO] FEATURES_CSV='${FEATURES_CSV}' — iterating per-feature stamps"
  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local features=( $FEATURES_CSV )
  IFS="$old_ifs"

  local feature
  for feature in "${features[@]}"; do
    feature="$(printf '%s' "$feature" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$feature" ]] && continue
    _render_backend_stamp_feature_template_one "$target" "$ft_dir" "$feature" "$feature"
  done
}

# Internal helper — stamp _feature_template/ once into <api>/<dest_folder>/.
# Args: $1 = target, $2 = template _feature_template/ dir, $3 = destination
#       folder name (e.g. "users" or "_feature_template"), $4 = feature name
#       to substitute into bodies (empty when stamping literally).
_render_backend_stamp_feature_template_one() {
  local target="$1"
  local ft_dir="$2"
  local dest_folder="$3"
  local feature="$4"

  # Export FEATURE_NAME / FEATURE_SLUG so .tmpl bodies can use them.
  FEATURE_NAME="${feature:-_feature_template}"
  FEATURE_SLUG="$(printf '%s' "$FEATURE_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [[ -z "$FEATURE_SLUG" ]] && FEATURE_SLUG="$FEATURE_NAME"
  export FEATURE_NAME FEATURE_SLUG

  local src rel inside out_rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${ft_dir}/}"

    # inside = path inside the feature folder (e.g. "routes/health.routes.ts.tmpl").
    inside="$rel"

    # When iterating features, file basenames containing __FEATURE__ get
    # swapped to the feature name (so e.g. __FEATURE__.routes.ts.tmpl becomes
    # users.routes.ts in the output). When stamping literally we keep the
    # __FEATURE__ token in the filename so the user can rename later.
    if [[ -n "$feature" ]]; then
      inside="${inside//__FEATURE__/${feature}}"
    fi

    # Strip the .tmpl suffix.
    inside="${inside%.tmpl}"

    out_rel="${SRC_DIR}/api/${API_VERSION}/${dest_folder}/${inside}"
    out_path="${target}/${out_rel}"
    render_backend_write_file "$src" "$out_path"
  done < <(find "$ft_dir" -type f -print0)

  # Unset feature vars between iterations so the next pass starts clean.
  unset FEATURE_NAME FEATURE_SLUG
}

# ----------------------------------------------------------------------------
# render_backend_ensure_dirs — guarantee every architectural folder exists
# even if the templates didn't populate a leaf file. Mirrors the
# BACKEND_REQUIRED_DIRS contract expected by validate-scaffold.sh.
# ----------------------------------------------------------------------------
render_backend_ensure_dirs() {
  local target="$1"

  # BACKEND_REQUIRED_DIRS is the source of truth — split it, mkdir each one.
  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local dirs=( $BACKEND_REQUIRED_DIRS )
  IFS="$old_ifs"

  local d
  for d in "${dirs[@]}"; do
    d="$(printf '%s' "$d" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$d" ]] && continue
    mkdir -p "${target}/${d}"
  done
}

# ----------------------------------------------------------------------------
# render_backend_all — public entrypoint
# Args: $1 = target directory (absolute)
# ----------------------------------------------------------------------------
render_backend_all() {
  local target="$1"

  if [[ -z "$target" ]]; then
    echo "[FAIL] render_backend_all requires a target dir" >&2
    return 1
  fi

  render_backend_export_vars

  # Export the required-dirs contract BEFORE rendering so validate-scaffold.sh
  # has a value if the renderer aborts mid-flight.
  BACKEND_REQUIRED_DIRS="${SRC_DIR},${SRC_DIR}/config,${SRC_DIR}/middlewares,${SRC_DIR}/models,${SRC_DIR}/lib,${SRC_DIR}/api/${API_VERSION},${SRC_DIR}/api/${API_VERSION}/health,${SRC_DIR}/types,${SRC_DIR}/tests,docs,migrations/postgres,scripts"
  export BACKEND_REQUIRED_DIRS

  render_backend_stamp_shared "$target"
  render_backend_stamp_main "$target"
  render_backend_stamp_feature_template "$target"
  render_backend_ensure_dirs "$target"
}

export -f render_backend_all
