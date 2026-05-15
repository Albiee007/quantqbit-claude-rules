#!/bin/bash
# ============================================================================
# Platform Detection Library — sniff a target dir for a known project shape
#
# Inspects the target workspace and exports:
#   DETECTED_PLATFORM     — first-hit platform (android|mobile|frontend|backend|unknown)
#   DETECTED_CANDIDATES   — CSV of every platform shape that matched; useful
#                           when a workspace is ambiguous (e.g. an RN+Expo
#                           project that also has `react` in deps and a vite
#                           config — the detector should surface both).
#
# Resolution order (first hit wins for DETECTED_PLATFORM, but ALL hits land
# in DETECTED_CANDIDATES):
#   1. build.gradle.kts OR build.gradle  → android
#   2. app.json AND `expo` in deps        → mobile
#   3. `react` in deps AND vite.config.*  → frontend
#   4. `express` OR `fastify` in deps     → backend
#   5. no package.json / build.gradle*    → unknown (caller should prompt)
#
# Detection is best-effort: missing tools (jq) trigger a regex fallback so
# the library still works in minimal environments.
#
# Usage (source in your script):
#   source "$(dirname "$0")/lib/detect-platform.sh"
#   detect_platform "/path/to/target"
#   echo "$DETECTED_PLATFORM ($DETECTED_CANDIDATES)"
# ============================================================================

set -euo pipefail

# Exported by detect_platform
DETECTED_PLATFORM="unknown"
DETECTED_CANDIDATES=""

# ----------------------------------------------------------------------------
# _detect_platform_dep_in_pkg — true if a dep name appears in package.json
# Args: $1 = absolute path to package.json
#       $2 = dep name (literal, no regex)
# Returns 0 on match, 1 otherwise. Prefers jq when present; otherwise falls
# back to a quoted-key grep that scans dependencies / devDependencies blocks.
# ----------------------------------------------------------------------------
_detect_platform_dep_in_pkg() {
  local pkg="$1"
  local dep="$2"

  [[ -f "$pkg" ]] || return 1

  if command -v jq >/dev/null 2>&1; then
    # `// {}` guards against missing blocks. `has($d)` returns true/false.
    local present
    present="$(jq -r --arg d "$dep" \
      '((.dependencies // {}) + (.devDependencies // {}) + (.peerDependencies // {})) | has($d)' \
      "$pkg" 2>/dev/null || echo "false")"
    [[ "$present" == "true" ]]
    return $?
  fi

  # Fallback: literal quoted key scan. Good enough for the four shapes we
  # care about; not a general-purpose JSON parser.
  grep -Eq "\"${dep}\"[[:space:]]*:" "$pkg"
}

# ----------------------------------------------------------------------------
# _detect_platform_append_candidate — append a name to DETECTED_CANDIDATES
# Avoids duplicates. Keeps the CSV order = order of detection.
# ----------------------------------------------------------------------------
_detect_platform_append_candidate() {
  local name="$1"
  case ",${DETECTED_CANDIDATES}," in
    *",${name},"*) return 0 ;;
  esac
  if [[ -z "$DETECTED_CANDIDATES" ]]; then
    DETECTED_CANDIDATES="$name"
  else
    DETECTED_CANDIDATES="${DETECTED_CANDIDATES},${name}"
  fi
}

# ----------------------------------------------------------------------------
# detect_platform — populate DETECTED_PLATFORM + DETECTED_CANDIDATES
# Args: $1 = absolute path to target directory
# ----------------------------------------------------------------------------
detect_platform() {
  local target="$1"

  if [[ ! -d "$target" ]]; then
    echo "[FAIL] detect_platform: target dir not found: ${target}" >&2
    return 1
  fi

  echo "[INFO] Detecting platform shape in ${target}"

  DETECTED_PLATFORM="unknown"
  DETECTED_CANDIDATES=""

  local has_gradle="false"
  local has_pkg="false"
  local has_app_json="false"
  local pkg="${target}/package.json"

  [[ -f "${target}/build.gradle.kts" || -f "${target}/build.gradle" ]] && has_gradle="true"
  [[ -f "$pkg" ]] && has_pkg="true"
  [[ -f "${target}/app.json" ]] && has_app_json="true"

  # 1. Android — gradle build file is decisive.
  if [[ "$has_gradle" == "true" ]]; then
    DETECTED_PLATFORM="android"
    _detect_platform_append_candidate "android"
  fi

  # The remaining checks require package.json.
  if [[ "$has_pkg" == "true" ]]; then
    local has_expo="false"
    local has_react="false"
    local has_vite_dep="false"
    local has_express="false"
    local has_fastify="false"
    local has_vite_cfg="false"

    _detect_platform_dep_in_pkg "$pkg" "expo"    && has_expo="true"
    _detect_platform_dep_in_pkg "$pkg" "react"   && has_react="true"
    _detect_platform_dep_in_pkg "$pkg" "vite"    && has_vite_dep="true"
    _detect_platform_dep_in_pkg "$pkg" "express" && has_express="true"
    _detect_platform_dep_in_pkg "$pkg" "fastify" && has_fastify="true"

    [[ -f "${target}/vite.config.ts" || -f "${target}/vite.config.js" ]] && has_vite_cfg="true"

    # 2. Mobile — app.json + expo in deps.
    if [[ "$has_app_json" == "true" && "$has_expo" == "true" ]]; then
      [[ "$DETECTED_PLATFORM" == "unknown" ]] && DETECTED_PLATFORM="mobile"
      _detect_platform_append_candidate "mobile"
    fi

    # 3. Frontend — react + vite config (the config file is decisive; the
    #    vite dep alone isn't enough because it ships transitively in many
    #    toolchains).
    if [[ "$has_react" == "true" && "$has_vite_cfg" == "true" ]]; then
      [[ "$DETECTED_PLATFORM" == "unknown" ]] && DETECTED_PLATFORM="frontend"
      _detect_platform_append_candidate "frontend"
    fi

    # Also surface frontend as a candidate when vite dep is present alongside
    # react, even if the config file uses a non-default name.
    if [[ "$has_react" == "true" && "$has_vite_dep" == "true" && "$has_vite_cfg" != "true" ]]; then
      _detect_platform_append_candidate "frontend"
    fi

    # 4. Backend — express OR fastify.
    if [[ "$has_express" == "true" || "$has_fastify" == "true" ]]; then
      [[ "$DETECTED_PLATFORM" == "unknown" ]] && DETECTED_PLATFORM="backend"
      _detect_platform_append_candidate "backend"
    fi
  fi

  # 5. Empty / unrecognised workspace.
  if [[ "$has_pkg" != "true" && "$has_gradle" != "true" && "$has_app_json" != "true" ]]; then
    DETECTED_PLATFORM="unknown"
    DETECTED_CANDIDATES=""
  fi

  if [[ -z "$DETECTED_CANDIDATES" ]]; then
    echo "[INFO]   platform   = ${DETECTED_PLATFORM} (no candidates)"
  else
    echo "[INFO]   platform   = ${DETECTED_PLATFORM} (candidates: ${DETECTED_CANDIDATES})"
  fi

  export DETECTED_PLATFORM DETECTED_CANDIDATES
}
