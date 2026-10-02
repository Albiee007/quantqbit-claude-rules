#!/bin/bash
# ============================================================================
# Render Core — shared stamping logic for the per-platform renderers
#
# render-{backend,frontend,mobile,android}.sh each describe one platform and
# delegate the work here. A platform renderer defines:
#
#   render_<p>_export_vars      normalise / export every var its .tmpl files use
#   render_<p>_describe         set the RC_* descriptor globals below
#   render_<p>_required_dirs    export <P>_REQUIRED_DIRS (read by validate-scaffold.sh)
#   render_<p>_should_skip      (optional) rel → 0 to drop a template
#   render_<p>_map_tokens       (optional) rewrite path tokens in RC_REL in place
#
# Descriptor globals (set by render_<p>_describe, after export_vars):
#   RC_TEMPLATE_DIR       ${SCRIPT_DIR}/templates/<p>
#   RC_ENVSUBST_VARS      envsubst whitelist — literal `$X` in code stays intact
#   RC_SRC_REMAP          true → template `src/*` lands under ${SRC_DIR}/*
#   RC_EXEC_GLOBS         case patterns made executable (default: */gradlew *.sh)
#   RC_REQUIRED_DIRS_VAR  name of the <P>_REQUIRED_DIRS variable
#   RC_ITEM_DIR           template-relative per-item tree ("" = none)
#   RC_ITEM_LITERAL       basename of that tree (e.g. _feature_template)
#   RC_ITEM_TOKEN         path token swapped for the item name (e.g. __FEATURE__)
#   RC_ITEM_VAR           exported as ${RC_ITEM_VAR}_NAME / _SLUG while stamping
#   RC_ITEM_NOUN          word used in log lines (feature / screen)
#   RC_ITEM_PREFIX        output dir that receives one folder per item
#
# Passes: _shared/ templates, the platform tree (minus the item tree), the item
# tree once per entry in FEATURES_CSV (or literally when empty), then every
# required directory.
#
# The renderer only ever writes into a staging directory (the target given to
# rc_render_all). init-scaffold.sh plans, validates and applies the staged tree
# to the real project transactionally. RC_LIVE_TARGET names that real project
# so project-owned files (CLAUDE.md, AI_RULES.md, .mcp.json) are staged only
# when absent there. Bash 3.2 compatible.
# ============================================================================

set -euo pipefail

RENDER_CORE_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="${SCRIPT_DIR:-$(cd "${RENDER_CORE_LIB_DIR}/.." && pwd)}"

# rc_hook <name> [args...] — call render_<platform>_<name> when defined.
# Returns 1 for an undefined hook so optional predicates default to "no".
rc_hook() {
  local fn="render_${RC_PLATFORM}_$1"
  shift
  declare -F "$fn" >/dev/null 2>&1 || return 1
  "$fn" "$@"
}

# ----------------------------------------------------------------------------
# rc_substitute — strip conditional blocks + envsubst
# Args: $1 = source file. Echoes the rendered content.
#
# Conditional-block syntax inside templates:
#   <!-- {{IF WITH_I18N}} -->   (also `# {{IF X}}` and `// {{IF X}}`)
#   ...lines emitted only when WITH_I18N=true...
#   <!-- {{ENDIF}} -->
# ----------------------------------------------------------------------------
rc_substitute() {
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

  printf '%s\n' "$processed" | envsubst "$RC_ENVSUBST_VARS"
}

# ----------------------------------------------------------------------------
# rc_write_file — render one file into the staging tree
# Args: $1 = source template, $2 = staged absolute path
# Two templates producing the same path is a renderer bug, not a conflict.
# ----------------------------------------------------------------------------
rc_write_file() {
  local src="$1"
  local out_path="$2"

  if [[ -e "$out_path" ]]; then
    echo "[FAIL] two templates render to the same path: ${out_path}" >&2
    return 1
  fi

  mkdir -p "$(dirname "$out_path")"

  case "$src" in
    *.tmpl) rc_substitute "$src" > "$out_path" ;;
    *)      cp "$src" "$out_path" ;;
  esac

  # Scripts are executable on every platform. Case patterns are matched
  # without pathname expansion, so `*.sh` is safe here.
  local globs=() glob
  read -r -a globs <<< "${RC_EXEC_GLOBS:-}"
  for glob in ${globs[@]+"${globs[@]}"}; do
    # shellcheck disable=SC2254
    case "$out_path" in
      $glob) chmod +x "$out_path" 2>/dev/null || true; break ;;
    esac
  done
}

# ----------------------------------------------------------------------------
# rc_target_relpath — template-relative path → output-relative path in RC_REL.
# Strips .tmpl, applies the src/ remap, renames dotfile templates (stored
# without the dot so they aren't hidden in templates/), then lets the
# platform's map_tokens hook rewrite RC_REL in place. No subshell per file.
# ----------------------------------------------------------------------------
rc_target_relpath() {
  RC_REL="${1%.tmpl}"

  if [[ "$RC_SRC_REMAP" == "true" ]]; then
    case "$RC_REL" in src/*) RC_REL="${SRC_DIR}/${RC_REL#src/}" ;; esac
  fi

  case "$RC_REL" in
    editorconfig)              RC_REL=".editorconfig" ;;
    gitignore)                 RC_REL=".gitignore" ;;
    dockerignore)              RC_REL=".dockerignore" ;;
    env.example|.env.example)  RC_REL=".env.example" ;;
    eslintrc.cjs)              RC_REL=".eslintrc.cjs" ;;
    prettierrc)                RC_REL=".prettierrc" ;;
  esac

  rc_hook map_tokens || true
}

# ----------------------------------------------------------------------------
# rc_stamp_shared — pass 1: stamp _shared/ templates
# ----------------------------------------------------------------------------
rc_stamp_shared() {
  local target="$1"
  local shared_dir="${SCRIPT_DIR}/templates/_shared"
  local live="${RC_LIVE_TARGET:-$target}"

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
      CLAUDE.md.tmpl)    out_rel="CLAUDE.md" ;;
      AI_RULES.md.tmpl)  out_rel="AI_RULES.md" ;;
      README.md.tmpl)    out_rel="README.md" ;;
      editorconfig.tmpl) out_rel=".editorconfig" ;;
      gitignore.tmpl)    out_rel=".gitignore" ;;
      mcp.json.tmpl)     out_rel=".mcp.json" ;;  # Claude Code reads project MCP from root .mcp.json
      *)                 out_rel="${rel%.tmpl}" ;;
    esac

    out_path="${target}/${out_rel}"
    # Project-owned instruction files are write-if-absent (never clobbered,
    # even by --force). CLAUDE.md is also skipped next to an AGENTS.md, since
    # Claude Code stops reading AGENTS.md once a CLAUDE.md exists.
    case "$out_rel" in
      CLAUDE.md|AI_RULES.md|.mcp.json)
        if [[ -e "${live}/${out_rel}" ]]; then
          echo "[INFO] kept existing project file: ${out_rel}"
          continue
        fi
        if [[ "$out_rel" == "CLAUDE.md" && -e "${live}/AGENTS.md" ]]; then
          echo "[INFO] skipped CLAUDE.md: AGENTS.md exists (a CLAUDE.md would stop Claude Code reading it)"
          continue
        fi ;;
    esac
    rc_write_file "$tmpl" "$out_path"
  done < <(find "$shared_dir" -type f -name '*.tmpl' -print0)

  # docs/plans/ should exist with a .gitkeep — kept by the shared layer.
  mkdir -p "${target}/docs/plans"
  [[ -f "${target}/docs/plans/.gitkeep" ]] || : > "${target}/docs/plans/.gitkeep"
}

# ----------------------------------------------------------------------------
# rc_stamp_main — pass 2: stamp the platform tree, minus the per-item tree
# ----------------------------------------------------------------------------
rc_stamp_main() {
  local target="$1"
  local tmpl_dir="$RC_TEMPLATE_DIR"

  if [[ ! -d "$tmpl_dir" ]]; then
    echo "[FAIL] ${RC_PLATFORM}/ template dir not found: ${tmpl_dir}" >&2
    return 1
  fi

  echo "[INFO] Stamping ${RC_PLATFORM}/ templates (main pass)"
  local src rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${tmpl_dir}/}"

    if [[ -n "$RC_ITEM_DIR" ]]; then
      case "$rel" in
        */"$RC_ITEM_LITERAL"/*|"$RC_ITEM_LITERAL"/*) continue ;;
      esac
    fi

    if rc_hook should_skip "$rel"; then
      echo "[INFO]   skip ${rel}"
      continue
    fi

    rc_target_relpath "$rel"
    out_path="${target}/${RC_REL}"
    rc_write_file "$src" "$out_path"
  done < <(find "$tmpl_dir" -type f -print0)
}

# ----------------------------------------------------------------------------
# rc_stamp_items — pass 3: stamp the per-item tree once per FEATURES_CSV entry
# (or once literally, under its own name, when FEATURES_CSV is empty).
# ----------------------------------------------------------------------------
rc_stamp_items() {
  local target="$1"
  [[ -z "$RC_ITEM_DIR" ]] && return 0
  local item_dir="${RC_TEMPLATE_DIR}/${RC_ITEM_DIR}"

  if [[ ! -d "$item_dir" ]]; then
    echo "[WARN] ${RC_ITEM_LITERAL}/ not found under ${RC_PLATFORM} templates: ${item_dir}"
    return 0
  fi

  if [[ -z "${FEATURES_CSV:-}" ]]; then
    echo "[INFO] FEATURES_CSV empty — stamping ${RC_ITEM_LITERAL}/ literally"
    _rc_stamp_item_one "$target" "$item_dir" "$RC_ITEM_LITERAL" ""
    return 0
  fi

  echo "[INFO] FEATURES_CSV='${FEATURES_CSV}' — iterating per-${RC_ITEM_NOUN} stamps"
  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local items=( $FEATURES_CSV )
  IFS="$old_ifs"

  local item
  for item in ${items[@]+"${items[@]}"}; do
    item="$(printf '%s' "$item" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$item" ]] && continue
    _rc_stamp_item_one "$target" "$item_dir" "$item" "$item"
  done
}

# Internal — stamp the item tree once into ${RC_ITEM_PREFIX}/<dest_folder>/.
# Args: $1 = target, $2 = item template dir, $3 = destination folder name,
#       $4 = item name to substitute (empty when stamping literally).
_rc_stamp_item_one() {
  local target="$1"
  local item_dir="$2"
  local dest_folder="$3"
  local item="$4"

  local name slug
  name="${item:-$RC_ITEM_LITERAL}"
  slug="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [[ -z "$slug" ]] && slug="$name"
  printf -v "${RC_ITEM_VAR}_NAME" '%s' "$name"
  printf -v "${RC_ITEM_VAR}_SLUG" '%s' "$slug"
  export "${RC_ITEM_VAR}_NAME" "${RC_ITEM_VAR}_SLUG"

  local src inside out_path
  while IFS= read -r -d '' src; do
    inside="${src#${item_dir}/}"
    # Iterated stamps swap the token in file/dir names (e.g.
    # __FEATURE__.routes.ts → users.routes.ts); literal stamps keep it so the
    # user can rename later.
    if [[ -n "$item" ]]; then
      inside="${inside//${RC_ITEM_TOKEN}/${item}}"
    fi
    inside="${inside%.tmpl}"

    out_path="${target}/${RC_ITEM_PREFIX}/${dest_folder}/${inside}"
    rc_write_file "$src" "$out_path"
  done < <(find "$item_dir" -type f -print0)

  unset "${RC_ITEM_VAR}_NAME" "${RC_ITEM_VAR}_SLUG"
}

# ----------------------------------------------------------------------------
# rc_ensure_dirs — guarantee every architectural folder in <P>_REQUIRED_DIRS
# exists even if no template populated it.
# ----------------------------------------------------------------------------
rc_ensure_dirs() {
  local target="$1"

  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local dirs=( ${!RC_REQUIRED_DIRS_VAR} )
  IFS="$old_ifs"

  local d
  for d in ${dirs[@]+"${dirs[@]}"}; do
    d="$(printf '%s' "$d" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$d" ]] && continue
    mkdir -p "${target}/${d}"
  done
}

# ----------------------------------------------------------------------------
# rc_render_all — public entrypoint used by render_<p>_all
# Args: $1 = platform, $2 = target directory (absolute)
# ----------------------------------------------------------------------------
rc_render_all() {
  RC_PLATFORM="$1"
  local target="${2:-}"

  if [[ -z "$target" ]]; then
    echo "[FAIL] render_${RC_PLATFORM}_all requires a target dir" >&2
    return 1
  fi

  RC_TEMPLATE_DIR="${SCRIPT_DIR}/templates/${RC_PLATFORM}"
  RC_SRC_REMAP="false"
  RC_EXEC_GLOBS='*/gradlew *.sh'
  RC_ITEM_DIR=""
  RC_ITEM_LITERAL=""
  RC_ITEM_TOKEN=""
  RC_ITEM_VAR=""
  RC_ITEM_NOUN=""
  RC_ITEM_PREFIX=""

  "render_${RC_PLATFORM}_export_vars"
  "render_${RC_PLATFORM}_describe"
  "render_${RC_PLATFORM}_required_dirs"

  rc_stamp_shared "$target"
  rc_stamp_main "$target"
  rc_stamp_items "$target"
  rc_ensure_dirs "$target"
}
