#!/bin/bash
# ============================================================================
# Render Library (android) — stamp Kotlin + Compose + Retrofit starter
#
# Walks ${SCRIPT_DIR}/templates/_shared/ + ${SCRIPT_DIR}/templates/android/
# recursively, computes each output path under the target directory, performs
# ${VAR} substitution + conditional-block processing, and writes the result.
# The `_feature_template/` tree inside the android template is stamped
# literally (a renamable feature folder) — Android features are typically
# scaffolded one at a time via Android Studio's "New Feature" wizard rather
# than batch-generated from a CSV, so we do not iterate FEATURES_CSV here.
#
# Stack non-goals (per review decision #6): no Hilt, no Room, no KSP. DI is a
# plain `core/di/AppGraph.kt` service-locator wired in by the Application
# class. Compose + Retrofit are stable; everything else is intentionally bare.
#
# Substitution variables (exported by init-scaffold.sh + prompt-scaffold.sh):
#   PROJECT_NAME, PROJECT_SLUG, ANDROID_PACKAGE, TIMESTAMP,
#   PLATFORM, TARGET_DIR, FORCE, BACKUP_TS
#
# Conditional-block syntax inside templates (re-used from render-backend.sh):
#   <!-- {{IF HAS_BASH}} -->
#   ...lines emitted only when HAS_BASH=true...
#   <!-- {{ENDIF}} -->
#
# Path tokens:
#   Directories named exactly `__PACKAGE_PATH__` are renamed at stamp time to
#   the resolved package path (dots → slashes — e.g. com/acme/app for
#   ANDROID_PACKAGE=com.acme.app). This mirrors how render-backend.sh resolves
#   __API_VERSION__.
#
# Usage (sourced by init-scaffold.sh):
#   source "${SCRIPT_DIR}/lib/render-android.sh"
#   render_android_all "/path/to/target"
# ============================================================================

set -euo pipefail

# Resolve our own dir so templates/ is locatable even when sourced stand-alone.
# SCRIPT_DIR is normally set by init-scaffold.sh.
RENDER_ANDROID_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_ANDROID_SCAFFOLD_DIR="$(cd "${RENDER_ANDROID_LIB_DIR}/.." && pwd)"
SCRIPT_DIR="${SCRIPT_DIR:-${RENDER_ANDROID_SCAFFOLD_DIR}}"

# ----------------------------------------------------------------------------
# render_android_export_vars — normalise / export every var .tmpl files use
# ----------------------------------------------------------------------------
render_android_export_vars() {
  # Stack vars consumed by shared templates copied from render.sh's vocabulary.
  # The android stack is known so we hardwire HAS_BASH=true (check-file-size.sh
  # is bash) and the others false. Compose stays false because the gradle
  # build is the canonical entry point — there's no Docker Compose file.
  HAS_BASH="true"
  HAS_ANSIBLE="false"
  HAS_COMPOSE="false"
  HAS_TERRAFORM="false"
  HAS_GIT="false"
  NO_STACKS="false"
  STACK_LIST="kotlin, compose, retrofit"

  # Boolean flags exported for shared templates that test them. Android v1
  # does not use either, but we export them so conditional blocks resolve.
  WITH_I18N="${WITH_I18N:-false}"
  WITH_AUTH="${WITH_AUTH:-false}"

  # Defensive defaults — these should be filled by prompt-scaffold.sh, but we
  # want the renderer to work even when invoked directly in tests.
  PROJECT_NAME="${PROJECT_NAME:-MyApp}"
  PROJECT_SLUG="${PROJECT_SLUG:-myapp}"
  ANDROID_PACKAGE="${ANDROID_PACKAGE:-com.example.app}"
  TIMESTAMP="${TIMESTAMP:-$(date +%Y-%m-%d)}"

  # SRC_DIR / API_VERSION are exported because the shared README/CLAUDE.md
  # templates mention them. Android templates themselves never embed them.
  SRC_DIR="${SRC_DIR:-app/src/main}"
  API_VERSION="${API_VERSION:-v1}"

  # Derived: package path is the package id with dots replaced by slashes.
  # e.g. com.acme.app → com/acme/app. Used to resolve __PACKAGE_PATH__ tokens
  # in template directory segments.
  ANDROID_PACKAGE_PATH="${ANDROID_PACKAGE//./\/}"

  # Derived: a Capitalised application-class prefix (e.g. MyApp → MyApp).
  # Already capitalised by convention; we leave it untouched so the user's
  # exact casing flows into ${App}Application.kt-style identifiers.
  APP_CLASS_PREFIX="${PROJECT_NAME}"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS \
         STACK_LIST WITH_I18N WITH_AUTH \
         PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION TIMESTAMP \
         ANDROID_PACKAGE ANDROID_PACKAGE_PATH APP_CLASS_PREFIX
}

# ----------------------------------------------------------------------------
# render_android_should_skip — drop templates that don't apply
# Args: $1 = path relative to the android/ template root
# ----------------------------------------------------------------------------
render_android_should_skip() {
  local rel="$1"
  # Currently no opt-out templates for android; reserved for future flags
  # (e.g. --with-firebase). Keep the function so future additions don't
  # require a structural change.
  case "$rel" in
    *) return 1 ;;
  esac
}

# ----------------------------------------------------------------------------
# render_android_substitute — strip conditional blocks + envsubst on stdin
# Args: $1 = source file
# Echoes the rendered content. Identical conditional-block stripper to
# render-backend.sh so behaviour stays consistent across platforms.
# ----------------------------------------------------------------------------
render_android_substitute() {
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
  # Kotlin / Gradle code (e.g. Kotlin string templates `$variable`) are left
  # alone. ANDROID_PACKAGE / ANDROID_PACKAGE_PATH / APP_CLASS_PREFIX are the
  # android-specific additions over render-backend.sh's whitelist.
  printf '%s\n' "$processed" | envsubst \
    '${PROJECT_NAME} ${PROJECT_SLUG} ${SRC_DIR} ${API_VERSION}
     ${WITH_I18N} ${WITH_AUTH} ${TIMESTAMP}
     ${STACK_LIST} ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${ANDROID_PACKAGE} ${ANDROID_PACKAGE_PATH} ${APP_CLASS_PREFIX}'
}

# ----------------------------------------------------------------------------
# render_android_write_file — emit a single file into the target, with backup
# Args: $1 = source template (already chosen), $2 = target absolute path
# ----------------------------------------------------------------------------
render_android_write_file() {
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
      render_android_substitute "$src" > "$out_path"
      ;;
    *)
      # Plain copy — no substitution.
      cp "$src" "$out_path"
      ;;
  esac

  # Preserve executable bit for scripts (gradlew, *.sh).
  case "$out_path" in
    */gradlew|*.sh)
      chmod +x "$out_path" 2>/dev/null || true
      ;;
  esac

  CREATED_FILES+=("$out_path")
  echo "[OK]   wrote ${out_path}"
}

# ----------------------------------------------------------------------------
# render_android_target_relpath — convert a template-relative path to its
# output-relative path. Strips trailing .tmpl, swaps __PACKAGE_PATH__ for the
# resolved package path (com.acme.app → com/acme/app), and renames known
# dot-prefixed templates.
# Args: $1 = template relpath
# ----------------------------------------------------------------------------
render_android_target_relpath() {
  local rel="$1"

  # Strip .tmpl suffix.
  local stripped="${rel%.tmpl}"

  # Dotfile renames — templates store these without a leading dot so they
  # aren't accidentally hidden in the templates directory.
  case "$stripped" in
    editorconfig)              stripped=".editorconfig" ;;
    gitignore)                 stripped=".gitignore" ;;
  esac

  # __PACKAGE_PATH__ in directory segments → resolved package path.
  stripped="${stripped//__PACKAGE_PATH__/${ANDROID_PACKAGE_PATH}}"

  printf '%s' "$stripped"
}

# ----------------------------------------------------------------------------
# render_android_stamp_shared — pass 1: stamp _shared/ templates
# ----------------------------------------------------------------------------
render_android_stamp_shared() {
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
    render_android_write_file "$tmpl" "$out_path"
  done < <(find "$shared_dir" -type f -name '*.tmpl' -print0)

  # docs/plans/ should exist with a .gitkeep — kept by the shared layer.
  mkdir -p "${target}/docs/plans"
  if [[ ! -f "${target}/docs/plans/.gitkeep" ]]; then
    : > "${target}/docs/plans/.gitkeep"
    CREATED_FILES+=("${target}/docs/plans/.gitkeep")
  fi
}

# ----------------------------------------------------------------------------
# render_android_stamp_main — pass 2: stamp android/ templates (all of them).
# Android does not iterate features the way backend does — the per-feature
# stamping is one-shot here (the home/ example is concrete; _feature_template/
# is stamped literally for the user to rename).
# ----------------------------------------------------------------------------
render_android_stamp_main() {
  local target="$1"
  local android_dir="${SCRIPT_DIR}/templates/android"

  if [[ ! -d "$android_dir" ]]; then
    echo "[FAIL] android/ template dir not found: ${android_dir}" >&2
    return 1
  fi

  echo "[INFO] Stamping android/ templates"
  local src rel out_rel out_path
  while IFS= read -r -d '' src; do
    rel="${src#${android_dir}/}"

    if render_android_should_skip "$rel"; then
      echo "[INFO]   skip ${rel}"
      continue
    fi

    out_rel="$(render_android_target_relpath "$rel")"
    out_path="${target}/${out_rel}"
    render_android_write_file "$src" "$out_path"
  done < <(find "$android_dir" -type f -print0)
}

# ----------------------------------------------------------------------------
# render_android_ensure_dirs — guarantee every architectural folder exists
# even if the templates didn't populate a leaf file. Mirrors the
# ANDROID_REQUIRED_DIRS contract expected by validate-scaffold.sh.
#
# Each entry may contain __PACKAGE_PATH__ which we resolve here before mkdir,
# so consumers of ANDROID_REQUIRED_DIRS see the unresolved literal (matching
# how validate-scaffold.sh advertises its contract) but the on-disk dirs are
# real paths.
# ----------------------------------------------------------------------------
render_android_ensure_dirs() {
  local target="$1"

  local old_ifs="$IFS"
  IFS=','
  # shellcheck disable=SC2206
  local dirs=( $ANDROID_REQUIRED_DIRS )
  IFS="$old_ifs"

  local d resolved
  for d in "${dirs[@]}"; do
    d="$(printf '%s' "$d" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$d" ]] && continue
    resolved="${d//__PACKAGE_PATH__/${ANDROID_PACKAGE_PATH}}"
    mkdir -p "${target}/${resolved}"
  done
}

# ----------------------------------------------------------------------------
# render_android_resolve_required_dirs — re-export ANDROID_REQUIRED_DIRS with
# __PACKAGE_PATH__ resolved so validate-scaffold.sh can assert real paths.
# Called after render_android_export_vars so ANDROID_PACKAGE_PATH is set.
# ----------------------------------------------------------------------------
render_android_resolve_required_dirs() {
  ANDROID_REQUIRED_DIRS="${ANDROID_REQUIRED_DIRS//__PACKAGE_PATH__/${ANDROID_PACKAGE_PATH}}"
  export ANDROID_REQUIRED_DIRS
}

# ----------------------------------------------------------------------------
# render_android_all — public entrypoint
# Args: $1 = target directory (absolute)
# ----------------------------------------------------------------------------
render_android_all() {
  local target="$1"

  if [[ -z "$target" ]]; then
    echo "[FAIL] render_android_all requires a target dir" >&2
    return 1
  fi

  render_android_export_vars

  # Export the required-dirs contract BEFORE rendering so validate-scaffold.sh
  # has a value if the renderer aborts mid-flight. The __PACKAGE_PATH__
  # literal stays in the *advertised* value (per task spec) — we resolve it
  # for both mkdir + validate just before each consumer needs the real path.
  ANDROID_REQUIRED_DIRS="app,app/src/main,app/src/main/java,app/src/main/java/__PACKAGE_PATH__,app/src/main/java/__PACKAGE_PATH__/core,app/src/main/java/__PACKAGE_PATH__/features,app/src/main/java/__PACKAGE_PATH__/features/home,app/src/main/java/__PACKAGE_PATH__/navigation,app/src/main/res,docs"
  export ANDROID_REQUIRED_DIRS

  render_android_stamp_shared "$target"
  render_android_stamp_main "$target"

  # Resolve __PACKAGE_PATH__ into the real ANDROID_PACKAGE_PATH for the
  # directory-existence pass and the validator that runs after us.
  render_android_resolve_required_dirs
  render_android_ensure_dirs "$target"
}

export -f render_android_all
