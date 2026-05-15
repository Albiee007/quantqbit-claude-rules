#!/bin/bash
# ============================================================================
# Validate Library — sanity-check stamped output
#
# Runs cheap, fast checks on the files we just wrote:
#   - bash -n on every .sh under .claude/hooks/ and any other stamped *.sh
#   - JSON syntax check on .claude/settings.json (jq preferred, python fallback)
#
# Aggregates failures and exits non-zero if anything tripped.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/validate.sh"
#   validate_all "/path/to/target"
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# validate_json — syntax-check a JSON file
# Returns 0 on success, 1 on failure, 2 if no tool was available (skipped).
# Fix E10: returns a distinct code for "skipped" so the caller can count it
# separately from passes — previously it returned 0 on skip, lying to the user.
# ----------------------------------------------------------------------------
validate_json() {
  local file="$1"
  if command -v jq >/dev/null 2>&1; then
    # Bug 6 fix: `jq -e empty` always exits 4 because `empty` produces no
    # output and `-e` treats no-output as failure. Use `jq -e .` instead —
    # it parses the document, prints it, and exits 0 on valid JSON.
    if jq -e . "$file" >/dev/null 2>&1; then
      return 0
    fi
  elif command -v python3 >/dev/null 2>&1; then
    if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$file" >/dev/null 2>&1; then
      return 0
    fi
  elif command -v python >/dev/null 2>&1; then
    if python -c "import json,sys; json.load(open(sys.argv[1]))" "$file" >/dev/null 2>&1; then
      return 0
    fi
  else
    echo "[WARN] Neither jq nor python available — skipping JSON validation."
    return 2
  fi
  echo "[FAIL] JSON invalid: ${file}"
  return 1
}

# ----------------------------------------------------------------------------
# validate_unresolved_vars — flag leftover ${VAR} markers in stamped output
# Fix E11: `bash -n` catches syntax, not interpolation breakage. If a
# template variable goes missing from envsubst's allow-list, the output
# silently keeps the literal ${FOO}. We grep each stamped file for the known
# scaffold variable names and fail if any are still present.
#
# Caveat: markdown files may legitimately contain other ${...} shell
# expansion examples, so we only flag the known scaffold variable names —
# anything else inside ${...} is acceptable.
#
# Returns 0 if file is clean, 1 if unresolved markers are present.
# ----------------------------------------------------------------------------
validate_unresolved_vars() {
  local file="$1"
  # Known scaffold variables. Anything else in ${...} (e.g. shell expansions
  # in hook scripts, or user examples in markdown) is acceptable.
  local pattern='\$\{(PROJECT_NAME|CODE_SUBDIR|STACK_LIST|HAS_BASH|HAS_ANSIBLE|HAS_COMPOSE|HAS_TERRAFORM|HAS_GIT|CITATION_BASH|CITATION_ANSIBLE|CITATION_COMPOSE|CITATION_TERRAFORM|DENY_DESTRUCTIVE|DENY_PUSH_MAIN|PROJECT_NAME_BASH_QUOTED)\}'
  local hits
  if hits="$(grep -Eo "$pattern" "$file" 2>/dev/null | sort -u | tr '\n' ' ')"; then
    if [[ -n "$hits" ]]; then
      echo "[FAIL] Unresolved template variables in ${file}: ${hits}"
      return 1
    fi
  fi
  return 0
}

# ----------------------------------------------------------------------------
# validate_all — run every check; exit non-zero on aggregate failure
#
# Fix E10: track passed / skipped / failed separately so the final report
# is honest. Previously the validator said "passed" even when it skipped
# checks (e.g. no jq/python → JSON validation skipped silently), leaving the
# user thinking settings.json was checked.
# ----------------------------------------------------------------------------
validate_all() {
  local target="$1"
  local failures=0
  local passes=0
  local skipped=0
  local skipped_names=()

  echo "[INFO] Validating stamped output"

  # bash -n on all stamped .sh files under .claude/hooks/ and any other *.sh
  local sh
  while IFS= read -r -d '' sh; do
    if bash -n "$sh" 2>/dev/null; then
      echo "[OK]   bash -n ${sh}"
      passes=$((passes + 1))
    else
      echo "[FAIL] bash -n ${sh}"
      failures=$((failures + 1))
    fi
  done < <(find "$target/.claude/hooks" -type f -name '*.sh' -print0 2>/dev/null)

  # Lint.sh (or any other stamped *.sh in the project root that we created)
  local f
  for f in "${CREATED_FILES[@]:-}"; do
    [[ -z "$f" ]] && continue
    case "$f" in
      *.sh)
        # Skip ones already covered above
        case "$f" in
          */.claude/hooks/*) continue ;;
        esac
        if bash -n "$f" 2>/dev/null; then
          echo "[OK]   bash -n ${f}"
          passes=$((passes + 1))
        else
          echo "[FAIL] bash -n ${f}"
          failures=$((failures + 1))
        fi
        ;;
    esac
  done

  # settings.json
  local settings="${target}/.claude/settings.json"
  if [[ -f "$settings" ]]; then
    validate_json "$settings"
    case $? in
      0) echo "[OK]   json   ${settings}"; passes=$((passes + 1)) ;;
      2) skipped=$((skipped + 1)); skipped_names+=("settings.json (no jq/python)") ;;
      *) failures=$((failures + 1)) ;;
    esac
  fi

  # Fix E11: check every stamped file for unresolved ${VAR} markers from
  # the known scaffold variable set. Catches envsubst allow-list drift.
  for f in "${CREATED_FILES[@]:-}"; do
    [[ -z "$f" ]] && continue
    [[ -f "$f" ]] || continue
    if validate_unresolved_vars "$f"; then
      passes=$((passes + 1))
    else
      failures=$((failures + 1))
    fi
  done

  if [[ "$failures" -gt 0 ]]; then
    echo "[FAIL] Validation reported ${failures} failure(s)."
    exit 1
  fi
  if [[ "$skipped" -gt 0 ]]; then
    echo "[OK] Validation passed (${passes} checks ran, ${skipped} skipped)"
    echo "[INFO] Skipped checks: ${skipped_names[*]}"
  else
    echo "[OK] Validation passed (${passes} checks ran, 0 skipped)"
  fi
}
