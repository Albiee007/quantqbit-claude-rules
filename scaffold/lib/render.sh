#!/bin/bash
# ============================================================================
# Render Library — stamp .tmpl files into the target workspace
#
# Walks ${SCRIPT_DIR}/templates/ recursively, computes each output path under
# the target directory, performs ${VAR} substitution + conditional-block
# processing, and writes the result. Adds executable bits to hook scripts.
#
# Substitution variables (set by the orchestrator + detect.sh + prompt.sh):
#   PROJECT_NAME, CODE_SUBDIR, STACK_LIST,
#   HAS_BASH, HAS_ANSIBLE, HAS_COMPOSE, HAS_TERRAFORM, HAS_GIT,
#   CITATION_BASH, CITATION_ANSIBLE, CITATION_COMPOSE, CITATION_TERRAFORM,
#   DENY_DESTRUCTIVE, DENY_PUSH_MAIN
#
# Conditional-block syntax inside templates:
#   # {{IF HAS_ANSIBLE}}
#   ...lines emitted only when HAS_ANSIBLE=true...
#   # {{ENDIF}}
# Marker lines themselves are stripped from the output.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/render.sh"
#   render_all "/path/to/target"
# ============================================================================

set -euo pipefail

# Fix E6: resolve our own dir for templates/. The orchestrator (init.sh) sets
# SCRIPT_DIR before sourcing us, but anyone sourcing render.sh standalone
# would crash on `${SCRIPT_DIR}/templates/...`. Fall back to a self-resolved
# path so this lib works either way.
RENDER_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENDER_SCAFFOLD_DIR="$(cd "${RENDER_LIB_DIR}/.." && pwd)"
SCRIPT_DIR="${SCRIPT_DIR:-${RENDER_SCAFFOLD_DIR}}"

# ----------------------------------------------------------------------------
# render_export_vars — build the substitution environment
# Reads DETECTED_*, CITATION_*, OPT_IN_*, PROJECT_NAME, CODE_SUBDIR.
# Sets HAS_*, STACK_LIST, HAS_GIT, DENY_DESTRUCTIVE, DENY_PUSH_MAIN.
# ----------------------------------------------------------------------------
render_export_vars() {
  local target="$1"

  HAS_BASH="${DETECTED_BASH:-false}"
  HAS_ANSIBLE="${DETECTED_ANSIBLE:-false}"
  HAS_COMPOSE="${DETECTED_COMPOSE:-false}"
  HAS_TERRAFORM="${DETECTED_TERRAFORM:-false}"

  # Derived: NO_STACKS is true when none of the HAS_* flags are true. Templates
  # use this to emit a friendly "(no recognised stacks detected)" sentinel
  # instead of a series of empty IF blocks.
  if [[ "$HAS_BASH" != "true" && "$HAS_ANSIBLE" != "true" \
        && "$HAS_COMPOSE" != "true" && "$HAS_TERRAFORM" != "true" ]]; then
    NO_STACKS="true"
  else
    NO_STACKS="false"
  fi

  # Build STACK_LIST as a human-readable comma-joined list of detected stacks
  local parts=()
  [[ "$HAS_BASH"      == "true" ]] && parts+=("bash")
  [[ "$HAS_ANSIBLE"   == "true" ]] && parts+=("ansible")
  [[ "$HAS_COMPOSE"   == "true" ]] && parts+=("docker")
  [[ "$HAS_TERRAFORM" == "true" ]] && parts+=("terraform")
  if [[ ${#parts[@]} -eq 0 ]]; then
    STACK_LIST="(none — empty workspace?)"
  else
    # Bug 7 fix: IFS only takes the first character, so the previous
    # IFS=', ' produced "bash,docker" instead of "bash, docker". Build the
    # list manually with printf and trim the trailing ", ".
    STACK_LIST="$(printf '%s, ' "${parts[@]}")"
    STACK_LIST="${STACK_LIST%, }"
  fi

  # Git workspace?
  HAS_GIT="false"
  if (cd "$target" && git rev-parse --is-inside-work-tree >/dev/null 2>&1); then
    HAS_GIT="true"
  fi

  # Opt-in deny blocks — emitted only when user opted in.
  # Fix 3: accept any of y|Y|yes|YES|true|TRUE|1 (INSTALL.md documents
  # QQR_OPT_IN_DESTRUCTIVE=true, but the previous check only matched "y", so
  # every CI/non-interactive caller using docs got no protection). Lower-case
  # via tr for bash 3 compatibility, then match against an extended set.
  local oid opm
  oid="$(printf '%s' "${OPT_IN_DESTRUCTIVE:-n}" | tr '[:upper:]' '[:lower:]')"
  opm="$(printf '%s' "${OPT_IN_PUSH_MAIN:-n}" | tr '[:upper:]' '[:lower:]')"

  DENY_DESTRUCTIVE=""
  case "$oid" in
    y|yes|true|1)
      DENY_DESTRUCTIVE=',
        "Bash(terraform destroy*)",
        "Bash(docker system prune*)",
        "Bash(rm -rf /*)"'
      ;;
  esac

  DENY_PUSH_MAIN=""
  case "$opm" in
    y|yes|true|1)
      DENY_PUSH_MAIN=',
        "Bash(git push *main*)",
        "Bash(git push *master*)"'
      ;;
  esac

  # Fix 1: shell-quote PROJECT_NAME for safe inclusion in bash hook scripts.
  # Wraps the value in single quotes and escapes any embedded single quotes
  # via the standard '\'' dance. The result is a complete bash literal that
  # supplies its own surrounding quotes.
  PROJECT_NAME_BASH_QUOTED="'$(printf %s "${PROJECT_NAME:-}" | sed "s/'/'\\\\''/g")'"

  export HAS_BASH HAS_ANSIBLE HAS_COMPOSE HAS_TERRAFORM HAS_GIT NO_STACKS
  export STACK_LIST DENY_DESTRUCTIVE DENY_PUSH_MAIN
  export PROJECT_NAME_BASH_QUOTED
}

# ----------------------------------------------------------------------------
# render_should_skip — true if a template should not be stamped by init.sh.
# Two reasons to skip:
#   1. Stack-gated rule files whose stack isn't present in the workspace.
#   2. v0.2.0 project-scaffold templates that share the templates/ dir but are
#      stamped by init-scaffold.sh (a separate dispatcher) — init.sh walks
#      templates/ recursively, so we must explicitly exclude these subtrees.
# ----------------------------------------------------------------------------
render_not_mine() {
  # Templates that belong to other generators: the project-scaffold platform
  # trees (init-scaffold.sh) and the agent harness seeds (sync.sh). v1.0+:
  # agent rules, hooks, settings and CLAUDE.md come from the harness; init.sh
  # stamps lint tooling only.
  case "$1" in
    _shared/*|backend/*|frontend/*|mobile/*|android/*) return 0 ;;
    seed/*|rules/*|hooks/*|CLAUDE.md.tmpl|settings.json.tmpl) return 0 ;;
  esac
  return 1
}

render_should_skip() {
  # Stack-gated lint configs: only stamp configs for stacks that were detected.
  case "$1" in
    shellcheckrc.tmpl)  [[ "${HAS_BASH:-false}" != "true" ]] && return 0 ;;
    ansible-lint.tmpl)  [[ "${HAS_ANSIBLE:-false}" != "true" ]] && return 0 ;;
    yamllint.tmpl)      [[ "${HAS_ANSIBLE:-false}" != "true" && "${HAS_COMPOSE:-false}" != "true" ]] && return 0 ;;
  esac
  return 1
}

# ----------------------------------------------------------------------------
# render_target_path — convert a template relpath to its output path
# templates/CLAUDE.md.tmpl                       → CLAUDE.md
# templates/settings.json.tmpl                   → .claude/settings.json
# templates/hooks/x.sh.tmpl                      → .claude/hooks/x.sh
# templates/rules/bash.md.tmpl                   → .claude/rules/bash.md
# Anything else: stripped of .tmpl, kept under TARGET_DIR root.
# ----------------------------------------------------------------------------
render_target_path() {
  local tmpl_relpath="$1"
  local stripped="${tmpl_relpath%.tmpl}"
  # Lint tooling lives with the code it lints: under CODE_SUBDIR ("." = root).
  local sub="${CODE_SUBDIR:-.}"
  sub="${sub#./}"; sub="${sub%/}"
  local pre=""
  [[ -n "$sub" && "$sub" != "." ]] && pre="${sub}/"
  case "$stripped" in
    # Bug 5 fix: lint.sh is invoked by Makefile as `bash scripts/lint.sh`,
    # so route it under scripts/ rather than the project root.
    lint.sh)       echo "${pre}scripts/lint.sh" ;;
    Makefile)      echo "${pre}Makefile" ;;
    # Bug 4 fix: dotfile templates are stored without the leading dot in the
    # repo (so they don't get mistakenly hidden / picked up by tooling on the
    # rules-package side). Re-add the leading dot when stamping.
    editorconfig)  echo ".editorconfig" ;;
    shellcheckrc|yamllint|ansible-lint)
      echo "${pre}.${stripped}" ;;
    *)             echo "${stripped}" ;;
  esac
}

# ----------------------------------------------------------------------------
# render_substitute — perform variable + conditional substitution on stdin
# Reads from $1 (file), writes to stdout.
# ----------------------------------------------------------------------------
render_substitute() {
  local src="$1"

  # Step 1: process conditional blocks. AWK is more reliable than sed here
  # because it handles multi-line state cleanly.
  #
  # Marker styles supported (Bug 2 fix):
  #   # {{IF VAR}} ... # {{ENDIF}}              (bash, sh, lint configs)
  #   <!-- {{IF VAR}} --> ... <!-- {{ENDIF}} -->  (markdown)
  # The marker line itself is always stripped. The contained block is emitted
  # only when VAR == "true".
  local processed
  processed="$(awk -v has_bash="$HAS_BASH" \
                   -v has_ansible="$HAS_ANSIBLE" \
                   -v has_compose="$HAS_COMPOSE" \
                   -v has_terraform="$HAS_TERRAFORM" \
                   -v has_git="$HAS_GIT" \
                   -v no_stacks="$NO_STACKS" '
    BEGIN { skip = 0 }
    /^[[:space:]]*(#|<!--)[[:space:]]*\{\{IF [A-Z_]+\}\}([[:space:]]*-->)?[[:space:]]*$/ {
      match($0, /\{\{IF [A-Z_]+\}\}/)
      var = substr($0, RSTART + 5, RLENGTH - 7)
      val = "false"
      if (var == "HAS_BASH")      val = has_bash
      if (var == "HAS_ANSIBLE")   val = has_ansible
      if (var == "HAS_COMPOSE")   val = has_compose
      if (var == "HAS_TERRAFORM") val = has_terraform
      if (var == "HAS_GIT")       val = has_git
      if (var == "NO_STACKS")     val = no_stacks
      if (val != "true") { skip = 1 }
      next
    }
    /^[[:space:]]*(#|<!--)[[:space:]]*\{\{ENDIF\}\}([[:space:]]*-->)?[[:space:]]*$/ {
      skip = 0
      next
    }
    { if (!skip) print }
  ' "$src")"

  # Step 2: variable substitution via envsubst.
  # Fix 2: the pure-sed fallback could not handle multi-line values
  # (DENY_DESTRUCTIVE, DENY_PUSH_MAIN) and triggered `unterminated 's' command`.
  # init.sh now hard-requires envsubst, so the fallback is intentionally gone.
  printf '%s\n' "$processed" | envsubst \
    '${PROJECT_NAME} ${PROJECT_NAME_BASH_QUOTED} ${CODE_SUBDIR} ${STACK_LIST}
     ${HAS_BASH} ${HAS_ANSIBLE} ${HAS_COMPOSE} ${HAS_TERRAFORM} ${HAS_GIT}
     ${CITATION_BASH} ${CITATION_ANSIBLE} ${CITATION_COMPOSE} ${CITATION_TERRAFORM}
     ${DENY_DESTRUCTIVE} ${DENY_PUSH_MAIN}'
}

# ----------------------------------------------------------------------------
# render_all — stamp every template under SCRIPT_DIR/templates into target
#
# Fix 6: render is atomic. We render every file into a staging directory
# first; only after ALL renders succeed do we copy into the target. If any
# template fails mid-render, the trap cleans up staging and the target is
# left untouched. The previous implementation wrote each file directly into
# the target and could leave the user half-stamped on failure.
#
# Fix 5: when --force is in effect, any pre-existing target file is copied
# aside to <target>/.claude.bak/<BACKUP_TS>/<rel>/ BEFORE being overwritten,
# so user customisations are never silently lost. BACKUP_TS / BACKUP_MADE are
# set in init.sh; init_report surfaces the backup directory at the end.
# ----------------------------------------------------------------------------
render_all() {
  local target="$1"
  local templates_dir="${SCRIPT_DIR}/templates"

  if [[ ! -d "$templates_dir" ]]; then
    echo "[FAIL] Templates dir not found: ${templates_dir}"
    return 1
  fi

  render_export_vars "$target"

  # Staging dir — every render lands here first, then copied to target
  # atomically once all renders succeed. Trap guarantees cleanup on any exit.
  # Fix E4: init.sh installs an _on_exit trap that lists created files on
  # any exit path. Compose with it here rather than clobber it: capture the
  # original exit code first, clean staging, then call _on_exit (if defined)
  # so the user always sees the created-files report with the correct rc.
  local staging_dir
  staging_dir="$(mktemp -d "${TMPDIR:-/tmp}/qqr-render-XXXXXX")"
  # shellcheck disable=SC2064
  # The trap captures the original exit code, cleans the staging dir, then
  # invokes _on_exit via `bash -c` with $_rc as $? so the report sees the
  # right code. Finally re-exits with $_rc so the parent script sees it too.
  trap "_rc=\$?; rm -rf '${staging_dir}'; if declare -F _on_exit >/dev/null; then (exit \$_rc); _on_exit; fi; exit \$_rc" EXIT

  echo "[INFO] Rendering templates from ${templates_dir}"
  echo "[INFO] Staging dir: ${staging_dir}"

  local tmpl tmpl_relpath out_relpath staged_path
  local rendered_pairs=()  # "out_relpath\tstaged_path" entries to commit later
  while IFS= read -r -d '' tmpl; do
    tmpl_relpath="${tmpl#${templates_dir}/}"

    render_not_mine "$tmpl_relpath" && continue
    if render_should_skip "$tmpl_relpath"; then
      echo "[INFO]   skip ${tmpl_relpath} (stack not detected)"
      continue
    fi

    out_relpath="$(render_target_path "$tmpl_relpath")"
    staged_path="${staging_dir}/${out_relpath}"

    mkdir -p "$(dirname "$staged_path")"
    if ! render_substitute "$tmpl" > "$staged_path"; then
      echo "[FAIL] Render aborted on ${tmpl_relpath}; staging cleaned up; target was not modified."
      return 1
    fi

    rendered_pairs+=("${out_relpath}"$'\t'"${staged_path}")
  done < <(find "$templates_dir" -type f -name '*.tmpl' -print0)

  # All renders succeeded — commit to target. For each file: if --force is
  # in effect AND the target file already exists, back it up first (Fix 5),
  # then copy the staged version into place.
  local pair out_path rel_dir backup_path
  for pair in "${rendered_pairs[@]}"; do
    out_relpath="${pair%%$'\t'*}"
    staged_path="${pair#*$'\t'}"
    out_path="${target}/${out_relpath}"

    # Write-if-absent: existing project files are never overwritten unless
    # --force (then backed up first).
    if [[ "${FORCE:-false}" != "true" && -e "$out_path" ]]; then
      echo "[INFO] kept existing ${out_relpath} (use --force to replace; a backup is made)"
      continue
    fi
    if [[ "${FORCE:-false}" == "true" && -e "$out_path" ]]; then
      backup_path="${target}/.claude.bak/${BACKUP_TS}/${out_relpath}"
      mkdir -p "$(dirname "$backup_path")"
      cp "$out_path" "$backup_path"
      BACKUP_MADE="true"
      echo "[INFO] Backed up ${out_relpath} to .claude.bak/${BACKUP_TS}/"
    fi

    rel_dir="$(dirname "$out_path")"
    mkdir -p "$rel_dir"
    cp "$staged_path" "$out_path"

    case "$out_relpath" in
      *.sh) chmod +x "$out_path" ;;
    esac

    echo "[OK]   wrote ${out_path}"
    CREATED_FILES+=("$out_path")
  done
  # Clean staging now: callers (init.sh) may replace the EXIT trap afterwards.
  rm -rf "$staging_dir"
}
