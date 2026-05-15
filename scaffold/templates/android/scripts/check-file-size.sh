#!/bin/bash
# ============================================================================
# check-file-size.sh — warn (never error) on .kt files over 500 lines.
#
# Invoked by the Gradle `checkFileSize` task which runs after `ktlintCheck`.
# Exits 0 unconditionally so it never fails CI; warnings are surfaced for
# review. Files like generated API clients, Compose preview-heavy screens,
# and central registries legitimately go over 500 lines, so this stays
# warning-only by design.
# ============================================================================

set -uo pipefail

find app/src -name '*.kt' -type f 2>/dev/null \
  | xargs wc -l 2>/dev/null \
  | awk '$1 > 500 && $2 != "total" { print "[WARN] " $2 " has " $1 " lines (cap: 500)" }'

exit 0
