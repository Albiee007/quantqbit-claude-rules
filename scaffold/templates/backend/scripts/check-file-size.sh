#!/bin/bash
# ============================================================================
# check-file-size.sh — warn (never error) on .ts files over 500 lines.
#
# Invoked by `npm run lint:size`. Exits 0 unconditionally so it never fails
# CI; warnings are surfaced to the user for review.
# ============================================================================

set -uo pipefail

find src -name '*.ts' -type f 2>/dev/null \
  | xargs wc -l 2>/dev/null \
  | awk '$1 > 500 && $2 != "total" { print "[WARN] " $2 " has " $1 " lines (cap: 500)" }'

exit 0
