#!/bin/bash
# ============================================================================
# Claude Scaffold — Umbrella Dispatcher
#
# Stamps a buildable per-platform project starter (backend / frontend /
# mobile / android) into a target workspace. Sister scaffolder to init.sh:
#   - init.sh         stamps the operational .claude/ rules layer
#   - init-scaffold.sh stamps the application skeleton on top
#
# Pipeline:
#   detect → prompt → validate inputs → render into a staging tree →
#   validate the staged tree → plan (refuse on conflicts) → apply → manifest
#
# The whole stamp is one transaction (lib/txn.sh): nothing touches the
# project until the staged tree is complete and valid, every change is
# journaled, and any failure before the manifest is written rolls the project
# back to exactly how it was. The per-platform tree is rendered by
# lib/render-<platform>.sh (sourced lazily); this script handles arguments,
# platform selection, prompts, planning, backups and the final report.
#
# Exit codes: 0 ok (or --dry-run); 1 refused, nothing written (bad input,
# files in the way, already scaffolded); 2 failed and rolled back, or locked.
#
# Requires: bash, sed (always present); envsubst (gettext-base); jq OR python
#           (recommended — improves detect-platform package.json parsing).
#
# Usage:
#   bash init-scaffold.sh [options]
#
# Options:
#   -h, --help                 Print this help and exit.
#   --platform=<name>          backend | frontend | mobile | android.
#                              Skips auto-detection; overrides any detected
#                              shape.
#   --target=<path>            Target workspace dir (default: current dir).
#   --project-name=<name>      Pre-fill project name.
#   --src-dir=<dir>            Source directory (default: src).
#   --api-version=<v#>         Backend API version (default: v1; ^v[0-9]+$).
#   --features=<a,b,c>         CSV of feature folders to scaffold.
#   --android-package=<id>     Reverse-DNS package id (android only).
#   --with-i18n                Enable the optional i18n stub.
#   --with-auth                Enable the optional auth stub.
#   --non-interactive          Skip prompts; read remaining values from
#                              QQPS_PROJECT_NAME, QQPS_SRC_DIR,
#                              QQPS_API_VERSION, QQPS_FEATURES,
#                              QQPS_ANDROID_PACKAGE, QQPS_WITH_I18N,
#                              QQPS_WITH_AUTH.
#   --force                    Overwrite existing files. Originals are backed
#                              up to <target>/.claude.bak/<timestamp>/<relative>
#                              and restored by --uninstall.
#   --dry-run                  Print the plan; write nothing.
#   --force-unlock             Clear a lock left by a crashed run.
#   --uninstall                Reverse a previous stamp (see --help).
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# Resolve script + target directories
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$(pwd)"

# Defaults — CLI flags + env overrides land here.
IS_NON_INTERACTIVE="false"
FORCE="false"
UNINSTALL="false"
DRY_RUN="false"
FORCE_UNLOCK="false"
PLATFORM=""
PROJECT_NAME="${QQPS_PROJECT_NAME:-}"
SRC_DIR="${QQPS_SRC_DIR:-src}"
API_VERSION="${QQPS_API_VERSION:-v1}"
FEATURES_CSV="${QQPS_FEATURES:-}"
ANDROID_PACKAGE="${QQPS_ANDROID_PACKAGE:-}"
WITH_I18N="${QQPS_WITH_I18N:-false}"
WITH_AUTH="${QQPS_WITH_AUTH:-false}"

# Directories this run created for --target (removed again if it fails).
CREATED_TARGET_DIRS=""
SCAFFOLD_PHASE=""

# Explicit-flag markers — distinguish "not passed" from "passed empty".
TARGET_EXPLICIT="false"
PROJECT_NAME_EXPLICIT="false"
SRC_DIR_EXPLICIT="false"
API_VERSION_EXPLICIT="false"
ANDROID_PACKAGE_EXPLICIT="false"
PLATFORM_EXPLICIT="false"

# One backup folder per invocation for --force originals; the pid keeps two
# runs in the same second apart.
BACKUP_TS="$(date +%Y%m%d-%H%M%S).$$"
export BACKUP_TS

# ----------------------------------------------------------------------------
# init_scaffold_print_help — emit the usage block (HEREDOC, not self-grep)
# ----------------------------------------------------------------------------
init_scaffold_print_help() {
  cat <<'EOF'
============================================================================
Claude Scaffold — Umbrella Dispatcher

Stamps a buildable per-platform project starter (backend / frontend /
mobile / android) into a target workspace.

Pipeline:
  detect -> prompt -> render into a staging tree -> validate -> plan ->
  apply -> write manifest. One transaction: any failure leaves the project
  exactly as it was. Exit codes: 0 ok, 1 refused (nothing written),
  2 failed and rolled back (or another run holds the lock).

Usage:
  bash init-scaffold.sh [options]

Options:
  -h, --help                 Print this help and exit.
  --platform=<name>          backend | frontend | mobile | android.
                             Skips auto-detection; overrides any detected
                             shape.
  --target=<path>            Target workspace dir (default: current dir).
  --project-name=<name>      Pre-fill project name.
  --src-dir=<dir>            Source directory (default: src).
  --api-version=<v#>         Backend API version (default: v1; ^v[0-9]+$).
  --features=<a,b,c>         CSV of feature folders to scaffold.
  --android-package=<id>     Reverse-DNS package id (android only).
  --with-i18n                Enable the optional i18n stub.
  --with-auth                Enable the optional auth stub.
  --non-interactive          Skip prompts; read remaining values from
                             QQPS_PROJECT_NAME, QQPS_SRC_DIR,
                             QQPS_API_VERSION, QQPS_FEATURES,
                             QQPS_ANDROID_PACKAGE, QQPS_WITH_I18N,
                             QQPS_WITH_AUTH.
  --force                    Replace existing files that are in the way (and
                             re-stamp over an earlier scaffold). Originals are
                             backed up to
                               <target>/.claude.bak/<timestamp>/<relative>
                             Without --force, any existing file the starter
                             would replace stops the run before anything is
                             written; README.md, .gitignore, .editorconfig,
                             .env.example and docs/ files are kept instead.
                             CLAUDE.md, AI_RULES.md and .mcp.json are never
                             replaced.
  --dry-run                  Show what would be written; change nothing.
  --force-unlock             Clear the lock left by a crashed run.
  --uninstall                Reverse a previous stamp using
                             <target>/.claude/.scaffold-manifest-scaffold.txt:
                             removes the files it created (unless you have
                             edited them), restores originals it replaced
                             with --force, and removes the directories it
                             created once empty. All or nothing.
============================================================================
EOF
}

# ----------------------------------------------------------------------------
# init_scaffold_parse_args — populate globals from CLI flags
# ----------------------------------------------------------------------------
init_scaffold_parse_args() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      -h|--help)
        init_scaffold_print_help
        exit 0
        ;;
      --non-interactive)
        IS_NON_INTERACTIVE="true"
        ;;
      --force)
        FORCE="true"
        ;;
      --uninstall)
        UNINSTALL="true"
        ;;
      --dry-run)
        DRY_RUN="true"
        ;;
      --force-unlock)
        FORCE_UNLOCK="true"
        ;;
      --with-i18n)
        WITH_I18N="true"
        ;;
      --with-auth)
        WITH_AUTH="true"
        ;;
      --platform=*)
        PLATFORM="${arg#*=}"
        PLATFORM_EXPLICIT="true"
        ;;
      --target=*)
        TARGET_DIR="${arg#*=}"
        TARGET_EXPLICIT="true"
        ;;
      --project-name=*)
        PROJECT_NAME="${arg#*=}"
        PROJECT_NAME_EXPLICIT="true"
        ;;
      --src-dir=*)
        SRC_DIR="${arg#*=}"
        SRC_DIR_EXPLICIT="true"
        ;;
      --api-version=*)
        API_VERSION="${arg#*=}"
        API_VERSION_EXPLICIT="true"
        ;;
      --features=*)
        FEATURES_CSV="${arg#*=}"
        ;;
      --android-package=*)
        ANDROID_PACKAGE="${arg#*=}"
        ANDROID_PACKAGE_EXPLICIT="true"
        ;;
      *)
        echo "[FAIL] Unknown argument: ${arg}" >&2
        echo "Run with --help for usage." >&2
        exit 1
        ;;
    esac
  done

  # Explicit-but-empty values are user errors, mirroring init.sh.
  if [[ "$PLATFORM_EXPLICIT" == "true" && -z "$PLATFORM" ]]; then
    echo "[FAIL] --platform requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$TARGET_EXPLICIT" == "true" && -z "$TARGET_DIR" ]]; then
    echo "[FAIL] --target requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$PROJECT_NAME_EXPLICIT" == "true" && -z "$PROJECT_NAME" ]]; then
    echo "[FAIL] --project-name requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$SRC_DIR_EXPLICIT" == "true" && -z "$SRC_DIR" ]]; then
    echo "[FAIL] --src-dir requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$API_VERSION_EXPLICIT" == "true" && -z "$API_VERSION" ]]; then
    echo "[FAIL] --api-version requires a non-empty value" >&2
    exit 1
  fi
  if [[ "$ANDROID_PACKAGE_EXPLICIT" == "true" && -z "$ANDROID_PACKAGE" ]]; then
    echo "[FAIL] --android-package requires a non-empty value" >&2
    exit 1
  fi

  # Validate platform value when provided.
  if [[ -n "$PLATFORM" ]]; then
    case "$PLATFORM" in
      backend|frontend|mobile|android) ;;
      *)
        echo "[FAIL] --platform must be one of: backend, frontend, mobile, android (got '${PLATFORM}')" >&2
        exit 1
        ;;
    esac
  fi
}

# ----------------------------------------------------------------------------
# init_scaffold_resolve_platform — fill PLATFORM if not set by --platform=
#
# Order:
#   1. --platform flag wins.
#   2. detect_platform output (DETECTED_PLATFORM) if it isn't 'unknown'.
#   3. In --non-interactive mode, fail with a clear message — auto-detect
#      can't guess against an empty dir without input.
#   4. Otherwise prompt the user with detected candidates as hints.
# ----------------------------------------------------------------------------
init_scaffold_resolve_platform() {
  if [[ -n "$PLATFORM" ]]; then
    echo "[INFO] Platform forced via --platform=${PLATFORM}"
    return 0
  fi

  if [[ "$DETECTED_PLATFORM" != "unknown" ]]; then
    PLATFORM="$DETECTED_PLATFORM"
    echo "[INFO] Platform auto-detected: ${PLATFORM}"
    return 0
  fi

  if [[ "$IS_NON_INTERACTIVE" == "true" ]]; then
    echo "[FAIL] Could not auto-detect platform and no --platform= was given." >&2
    echo "       Pass --platform=backend|frontend|mobile|android." >&2
    exit 1
  fi

  local hint="backend|frontend|mobile|android"
  [[ -n "$DETECTED_CANDIDATES" ]] && hint="${DETECTED_CANDIDATES} (detected) | ${hint}"

  local reply
  while true; do
    read -r -p "  Platform [${hint}]: " reply
    case "$reply" in
      backend|frontend|mobile|android)
        PLATFORM="$reply"
        break
        ;;
      "")
        echo "[WARN] Platform is required."
        ;;
      *)
        echo "[WARN] Platform must be one of: backend, frontend, mobile, android."
        ;;
    esac
  done
}

# ----------------------------------------------------------------------------
# init_scaffold_check_features — reject feature names that collide with each
# other (case-insensitively, for macOS/Windows filesystems) or with the
# example folder the templates already ship (backend/frontend health/,
# mobile home/). Android does not iterate features.
# ----------------------------------------------------------------------------
init_scaffold_check_features() {
  [[ -z "$FEATURES_CSV" || "$PLATFORM" == android ]] && return 0
  local example="health" seen="," f lower old_ifs="$IFS"
  [[ "$PLATFORM" == mobile ]] && example="home"
  IFS=','
  # shellcheck disable=SC2206
  local items=( $FEATURES_CSV )
  IFS="$old_ifs"
  for f in ${items[@]+"${items[@]}"}; do
    f="$(printf '%s' "$f" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    [[ -z "$f" ]] && continue
    lower="$(printf '%s' "$f" | tr '[:upper:]' '[:lower:]')"
    if [[ "$lower" == "$example" ]]; then
      echo "[FAIL] Feature '${f}' collides with the built-in ${example}/ example; pick another name." >&2
      exit 1
    fi
    case "$seen" in
      *",${lower},"*) echo "[FAIL] Feature '${f}' is listed more than once." >&2; exit 1 ;;
    esac
    seen="${seen}${lower},"
  done
}

# ----------------------------------------------------------------------------
# init_scaffold_fault_at <phase> — test hook: SCAFFOLD_FAIL_AT=<phase> fails
# there (stage | validate | backup | manifest).
# ----------------------------------------------------------------------------
init_scaffold_fault_at() {
  [[ "${SCAFFOLD_FAIL_AT:-}" == "$1" ]] || return 0
  echo "[FAIL] SCAFFOLD_FAIL_AT=$1 (test fault injection)" >&2
  return 1
}

# ----------------------------------------------------------------------------
# init_scaffold_plan — compare the staged tree with the project, writing
# $TXN_W/plan.tsv rows "<op><TAB><rel>":
#   MKDIR      staged directory missing from the project
#   ADD        new file
#   SAME       identical file already present (left alone)
#   UPDATE     file from an earlier stamp, unmodified since (--force re-stamp)
#   OVERWRITE  someone else's file, replaced under --force (backed up)
#   KEEP       someone else's README/.gitignore/.editorconfig/.env.example/
#              docs file, kept without --force
#   CONFLICT   someone else's file (or a file/directory mismatch) in the way
#   UNSAFE     path runs through a symlink or has an unsafe name
# $TXN_W/prev.tsv holds the earlier stamp's manifest rows, if any.
# ----------------------------------------------------------------------------
init_scaffold_plan() {
  local stage="$TXN_STAGE" t="$TARGET_DIR" rel op prev_hash
  local plan="$TXN_W/plan.tsv" prev="$TXN_W/prev.tsv"
  : > "$plan"; : > "$prev"
  if [[ -f "$t/$INIT_SCAFFOLD_MANIFEST_NAME" ]]; then
    manifest_rows "$t/$INIT_SCAFFOLD_MANIFEST_NAME" > "$prev" || return 1
  fi

  while IFS= read -r rel; do
    if ! safe_relative_path "$t" "$rel"; then op=UNSAFE
    elif [[ -d "$t/$rel" ]]; then continue
    elif [[ -e "$t/$rel" ]]; then op=CONFLICT
    else op=MKDIR
    fi
    printf '%s\t%s\n' "$op" "$rel" >> "$plan"
  done < <(cd "$stage" && find . -mindepth 1 -type d | sed 's|^\./||' | LC_ALL=C sort)

  while IFS= read -r rel; do
    if ! safe_relative_path "$t" "$rel"; then op=UNSAFE
    elif [[ ! -e "$t/$rel" ]]; then op=ADD
    elif [[ -d "$t/$rel" ]]; then op=CONFLICT
    elif cmp -s "$stage/$rel" "$t/$rel"; then op=SAME
    else
      prev_hash="$(awk -F'\t' -v r="$rel" '$2 == r && $3 != "dir" { print $1; exit }' "$prev")"
      if [[ -n "$prev_hash" && "$prev_hash" != "-" && "$(manifest_hash "$t/$rel")" == "$prev_hash" ]]; then
        op=UPDATE
      elif [[ "$FORCE" == "true" ]]; then
        op=OVERWRITE
      else
        case "$rel" in
          README.md|.editorconfig|.gitignore|.env.example|docs/*) op=KEEP ;;
          *) op=CONFLICT ;;
        esac
      fi
    fi
    printf '%s\t%s\n' "$op" "$rel" >> "$plan"
  done < <(cd "$stage" && find . -type f | sed 's|^\./||' | LC_ALL=C sort)
}

# init_scaffold_count <op> — number of plan rows with that op.
init_scaffold_count() {
  awk -F'\t' -v op="$1" '$1 == op { n++ } END { print n + 0 }' "$TXN_W/plan.tsv"
}

# ----------------------------------------------------------------------------
# init_scaffold_apply — move the staged tree into the project, journaling
# every change. Originals replaced under --force are then copied (still
# inside the transaction) to .claude.bak/<timestamp>.<pid>/.
# ----------------------------------------------------------------------------
init_scaffold_apply() {
  local op rel
  TXN_APPLYING=1
  while IFS=$'\t' read -r op rel; do
    case "$op" in
      MKDIR)                txn_mkdirs "$rel" || return 1 ;;
      ADD|OVERWRITE|UPDATE) txn_move_in "$rel" || return 1 ;;
    esac
  done < "$TXN_W/plan.tsv"
  init_scaffold_fault_at backup || return 1
  while IFS=$'\t' read -r op rel; do
    [[ "$op" == OVERWRITE ]] || continue
    txn_copy_in "$TXN_BACKUP/$rel" ".claude.bak/${BACKUP_TS}/${rel}" || return 1
  done < "$TXN_W/plan.tsv"
}

# ----------------------------------------------------------------------------
# Manifest (v2) — the commit record. One row per file this stamp owns:
#   <sha256><TAB><rel><TAB>created|overwritten<TAB><backup rel or ->
# plus "-<TAB><rel><TAB>dir<TAB>-" for each directory it created. Rows from
# an earlier stamp carry over for anything this run left untouched, so
# --uninstall still reverses both. Written to the work dir, then renamed
# into place by txn_commit_file.
# ----------------------------------------------------------------------------
INIT_SCAFFOLD_MANIFEST_NAME=".claude/.scaffold-manifest-scaffold.txt"

init_scaffold_write_manifest() {
  local new="$TXN_W/rows.new" op rel origin backup inherited
  : > "$new"
  # Directories this run created, as journaled by txn_mkdirs.
  awk -F'\t' '$1 == "rmdir" && $2 !~ /^\.claude(\.bak)?(\/|$)/ { printf "-\t%s\tdir\t-\n", $2 }' \
    "$TXN_JOURNAL" >> "$new"
  while IFS=$'\t' read -r op rel; do
    case "$op" in
      ADD)       origin="created"; backup="-" ;;
      OVERWRITE) origin="overwritten"; backup=".claude.bak/${BACKUP_TS}/${rel}" ;;
      UPDATE)
        inherited="$(awk -F'\t' -v r="$rel" '$2 == r { print $3 "\t" $4; exit }' "$TXN_W/prev.tsv")"
        origin="${inherited%%$'\t'*}"; backup="${inherited#*$'\t'}" ;;
      *) continue ;;
    esac
    printf '%s\t%s\t%s\t%s\n' "$(manifest_hash "$TARGET_DIR/$rel")" "$rel" "$origin" "$backup" >> "$new"
  done < "$TXN_W/plan.tsv"

  {
    echo "# Generated by init-scaffold.sh"
    echo "# Platform: ${PLATFORM}"
    echo "# Stamped: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "# Use 'init-scaffold.sh --uninstall --target=<dir>' to reverse"
    printf '# format: v2 sha256<TAB>relative-path<TAB>origin<TAB>backup\n'
    awk -F'\t' 'NR == FNR { seen[$2] = 1; print; next } !($2 in seen) { print }' \
      "$new" "$TXN_W/prev.tsv" | LC_ALL=C sort -t$'\t' -k2,2
  } > "$TXN_W/manifest.new"
}

# ----------------------------------------------------------------------------
# init_scaffold_print_plan — summary (and, for --dry-run, the file list).
# ----------------------------------------------------------------------------
init_scaffold_print_plan() {
  local verbose="${1:-false}"
  echo ""
  echo "[INFO] Plan for ${TARGET_DIR}:"
  printf '  %-10s %s\n' add "$(init_scaffold_count ADD)" \
    update "$(init_scaffold_count UPDATE)" overwrite "$(init_scaffold_count OVERWRITE)" \
    keep "$(init_scaffold_count KEEP)" unchanged "$(init_scaffold_count SAME)" \
    mkdir "$(init_scaffold_count MKDIR)"
  if [[ "$verbose" == "true" ]]; then
    awk -F'\t' '$1 != "SAME" { printf "  %-9s %s\n", $1, $2 }' "$TXN_W/plan.tsv"
  else
    awk -F'\t' '$1 == "OVERWRITE" || $1 == "KEEP" { printf "  %-9s %s\n", $1, $2 }' "$TXN_W/plan.tsv"
  fi
}

# ----------------------------------------------------------------------------
# init_scaffold_report — final summary
# ----------------------------------------------------------------------------
init_scaffold_report() {
  echo ""
  echo "===== Scaffold complete ====="
  echo "Target  : ${TARGET_DIR}"
  echo "Platform: ${PLATFORM}"
  echo "Wrote $(( $(init_scaffold_count ADD) + $(init_scaffold_count UPDATE) + $(init_scaffold_count OVERWRITE) )) file(s); manifest: ${INIT_SCAFFOLD_MANIFEST_NAME}"
  if [[ "$(init_scaffold_count KEEP)" -gt 0 ]]; then
    echo "[INFO] Kept your existing: $(awk -F'\t' '$1 == "KEEP" { printf "%s ", $2 }' "$TXN_W/plan.tsv")(re-run with --force to replace them)"
  fi
  if [[ "$(init_scaffold_count OVERWRITE)" -gt 0 ]]; then
    echo "[OK] Originals of overwritten files: ${TARGET_DIR}/.claude.bak/${BACKUP_TS}/ (--uninstall restores them)"
  fi
}

# ----------------------------------------------------------------------------
# _on_exit — EXIT trap. Rolls back an interrupted apply (lib/txn.sh), releases
# the lock, and removes a target directory this run created if it failed.
# ----------------------------------------------------------------------------
_on_exit() {
  local rc=$?
  [[ $rc -ne 0 && "$SCAFFOLD_PHASE" == "render" ]] && rc=2
  txn_on_exit "$rc" || rc=$?
  if [[ $rc -ne 0 || "$DRY_RUN" == "true" ]]; then
    local d
    while IFS= read -r d; do
      [[ -n "$d" ]] && { rmdir "$d" 2>/dev/null || true; }
    done <<< "$CREATED_TARGET_DIRS"
  fi
  if [[ $rc -eq 2 ]]; then
    echo "[WARN] init-scaffold.sh failed; the project was left as it was before the run." >&2
  fi
  exit "$rc"
}

init_scaffold_uninstall() {
  local target="$1"
  local manifest="${target}/${INIT_SCAFFOLD_MANIFEST_NAME}"
  echo "[INFO] Uninstall via manifest: ${manifest}"
  local rc=0
  # shellcheck disable=SC2034  # read by manifest_uninstall
  MANIFEST_FORCE_UNLOCK="$([[ "$FORCE_UNLOCK" == "true" ]] && echo 1 || echo 0)"
  manifest_uninstall "$manifest" || rc=$?
  if [[ $rc -eq 0 ]]; then
    if [[ -d "${target}/.claude.bak" ]]; then
      echo "[INFO] Backups preserved at: ${target}/.claude.bak/"
    fi
    return 0
  fi
  echo "[INFO] Nothing was changed. Backups of files replaced with --force are under ${target}/.claude.bak/." >&2
  return "$rc"
}

# ============================================================================
# Main
# ============================================================================

trap '_on_exit' EXIT
trap 'exit 2' INT TERM

init_scaffold_parse_args "$@"

# Manifest + transaction helpers — needed by both the stamp path and the
# uninstall fast-path.
# shellcheck source=lib/manifest.sh
source "${SCRIPT_DIR}/lib/manifest.sh"
# shellcheck disable=SC2034  # read by lib/txn.sh (test fault injection)
TXN_FAIL_VAR="SCAFFOLD_FAIL_AFTER"

# --uninstall is short-circuit: no envsubst, no detect, no prompt, no render.
# Just read the manifest written by a previous stamp and reverse it.
if [[ "$UNINSTALL" == "true" ]]; then
  if [[ ! -d "$TARGET_DIR" ]]; then
    echo "[FAIL] --target does not exist: ${TARGET_DIR}" >&2
    exit 1
  fi
  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
  echo "[INFO] Uninstalling from: ${TARGET_DIR}"
  uninstall_rc=0
  init_scaffold_uninstall "$TARGET_DIR" || uninstall_rc=$?
  exit "$uninstall_rc"
fi

# envsubst is hard-required because per-platform renderers will use it for
# .tmpl substitution. Fail fast with the same message style as init.sh.
if ! command -v envsubst >/dev/null 2>&1; then
  echo "[FAIL] envsubst is required for templating but not installed." >&2
  echo "       On Debian/Ubuntu: apt install gettext-base" >&2
  echo "       On macOS: brew install gettext (and link)" >&2
  echo "       On Windows + Git Bash: typically present; check 'where envsubst'" >&2
  exit 1
fi

# Resolve the target to an absolute path, but create nothing until every
# input has been validated.
case "$TARGET_DIR" in
  /*|[A-Za-z]:*) ;;
  *) TARGET_DIR="$(pwd)/${TARGET_DIR}" ;;
esac
if [[ -e "$TARGET_DIR" && ! -d "$TARGET_DIR" ]]; then
  echo "[FAIL] --target exists but is not a directory: ${TARGET_DIR}" >&2
  exit 1
fi
[[ -d "$TARGET_DIR" ]] && TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "[INFO] Claude project scaffold"
echo "[INFO] Source : ${SCRIPT_DIR}"
echo "[INFO] Target : ${TARGET_DIR}"

# Source detect + prompt + validate libs up-front; they have no platform
# dependency. Renderers are sourced lazily once platform is known.
# shellcheck source=lib/detect-platform.sh
source "${SCRIPT_DIR}/lib/detect-platform.sh"
# shellcheck source=lib/prompt-scaffold.sh
source "${SCRIPT_DIR}/lib/prompt-scaffold.sh"
# shellcheck source=lib/validate-scaffold.sh
source "${SCRIPT_DIR}/lib/validate-scaffold.sh"

# 1. detect (a target that does not exist yet has nothing to detect)
if [[ -d "$TARGET_DIR" ]]; then
  detect_platform "$TARGET_DIR"
else
  DETECTED_PLATFORM="unknown"
  DETECTED_CANDIDATES=""
fi

# 2. resolve platform (flag → detected → prompt)
init_scaffold_resolve_platform

# 3. prompt for the remaining substitution variables. prompt_scaffold_collect
#    honours IS_NON_INTERACTIVE on its own.
prompt_scaffold_collect "$PLATFORM"

# Keep generated paths inside the target, and values safe in JSON/TS templates.
if [[ ! "$SRC_DIR" =~ ^[A-Za-z_][A-Za-z0-9_-]*(/[A-Za-z_][A-Za-z0-9_-]*)*$ ]]; then
  echo '[FAIL] Source directory must be a relative path of simple directory names.' >&2
  exit 1
fi
case "$SRC_DIR/" in
  app/*)
    if [[ "$PLATFORM" != android ]]; then
      echo "[FAIL] Source directory overlaps a reserved scaffold directory." >&2; exit 1
    fi ;;
  node_modules/*|dist/*|scripts/*|docs/*|migrations/*|android/*|ios/*|assets/*)
    echo '[FAIL] Source directory overlaps a reserved scaffold directory.' >&2; exit 1 ;;
esac
if [[ ! "$PROJECT_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9\ ._-]*$ ]]; then
  echo '[FAIL] Project name must contain only letters, numbers, spaces, dots, underscores or hyphens.' >&2
  exit 1
fi
init_scaffold_check_features

# 4. one stamp per project unless re-stamping on purpose
if [[ -f "${TARGET_DIR}/${INIT_SCAFFOLD_MANIFEST_NAME}" && "$FORCE" != "true" ]]; then
  echo "[FAIL] This project was already scaffolded (${INIT_SCAFFOLD_MANIFEST_NAME} exists)." >&2
  echo "       Run --uninstall first, or --force to re-stamp over it." >&2
  exit 1
fi

# Re-export everything renderers need (idempotent; covers both paths).
export PROJECT_NAME PROJECT_SLUG SRC_DIR API_VERSION FEATURES_CSV \
       ANDROID_PACKAGE WITH_I18N WITH_AUTH TIMESTAMP \
       PLATFORM TARGET_DIR FORCE IS_NON_INTERACTIVE BACKUP_TS

# 5. source the per-platform renderer.
RENDERER_LIB="${SCRIPT_DIR}/lib/render-${PLATFORM}.sh"
if [[ ! -f "$RENDERER_LIB" ]]; then
  echo "[FAIL] renderer lib not found: lib/render-${PLATFORM}.sh" >&2
  echo "       Expected at: ${RENDERER_LIB}" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "$RENDERER_LIB"

# Each renderer exposes a render_<platform>_all function.
RENDER_FN="render_${PLATFORM}_all"
if ! declare -F "$RENDER_FN" >/dev/null 2>&1; then
  echo "[FAIL] renderer lib '${RENDERER_LIB}' did not define '${RENDER_FN}'" >&2
  exit 1
fi

# 6. create the target (inputs are valid now) and open the transaction.
if [[ ! -d "$TARGET_DIR" ]]; then
  d="$TARGET_DIR"
  while [[ ! -e "$d" ]]; do
    CREATED_TARGET_DIRS="${CREATED_TARGET_DIRS}${d}"$'\n'
    d="$(dirname "$d")"
  done
  echo "[INFO] Target dir does not exist; creating: ${TARGET_DIR}"
  mkdir -p "$TARGET_DIR"
  TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
fi
txn_begin "$TARGET_DIR" ".claude/.scaffold-tmp" scaffold \
  "$([[ "$FORCE_UNLOCK" == "true" ]] && echo 1 || echo 0)" || exit 2

# 7. render into the staging tree, then validate it — nothing in the project
#    has changed yet.
# The renderer runs under errexit; any failure exits with 2 via _on_exit.
# shellcheck disable=SC2034  # read by lib/render-core.sh
RC_LIVE_TARGET="$TARGET_DIR"
SCAFFOLD_PHASE="render"
"$RENDER_FN" "$TXN_STAGE"
SCAFFOLD_PHASE=""
init_scaffold_fault_at stage || exit 2
validate_scaffold_all "$TXN_STAGE" "$PLATFORM" || exit 2
init_scaffold_fault_at validate || exit 2

# 8. plan: refuse (writing nothing) if anything is in the way
init_scaffold_plan || exit 2
if [[ "$(init_scaffold_count CONFLICT)" -gt 0 || "$(init_scaffold_count UNSAFE)" -gt 0 ]]; then
  echo "" >&2
  echo "[FAIL] Existing paths are in the way; nothing was written:" >&2
  awk -F'\t' '$1 == "CONFLICT" { print "  exists:  " $2 } $1 == "UNSAFE" { print "  unsafe:  " $2 " (symlink or unsafe name)" }' \
    "$TXN_W/plan.tsv" >&2
  echo "       Move them aside, or re-run with --force (originals are backed up to .claude.bak/)." >&2
  exit 1
fi
if [[ "$DRY_RUN" == "true" ]]; then
  init_scaffold_print_plan true
  echo "[INFO] Dry run: nothing was written."
  exit 0
fi
init_scaffold_print_plan

# 9. apply, then commit by renaming the manifest into place
init_scaffold_apply || exit 2
init_scaffold_write_manifest
init_scaffold_fault_at manifest || exit 2
txn_commit_file "$TXN_W/manifest.new" "$INIT_SCAFFOLD_MANIFEST_NAME" || exit 2
# shellcheck disable=SC2034  # read by lib/txn.sh
TXN_APPLYING=0   # committed: nothing after this point may roll back
init_scaffold_report
txn_end
