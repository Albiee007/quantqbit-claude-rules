#!/bin/bash
# ============================================================================
# check-file-size.sh — warn (never error) on .ts/.tsx files over 500 lines.
#
# Invoked by `npm run lint:size` and appended to `npm run lint` so a size
# warning never causes a non-zero exit. Exits 0 unconditionally — warnings
# are surfaced for review, not enforcement.
# ============================================================================

set -uo pipefail

find src \( -name '*.ts' -o -name '*.tsx' \) -type f 2>/dev/null \
  | xargs wc -l 2>/dev/null \
  | awk '$1 > 500 && $2 != "total" { print "[WARN] " $2 " has " $1 " lines (cap: 500)" }'

exit 0
