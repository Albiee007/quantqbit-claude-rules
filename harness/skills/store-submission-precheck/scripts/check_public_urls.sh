#!/usr/bin/env bash
# check_public_urls.sh - check that store-required public URLs return HTTP 200.
#
# Usage:
#   bash check_public_urls.sh <url> [<url> ...]
#   bash check_public_urls.sh -f urls.txt        # one URL per line, # comments allowed
#
# Stores reject listings whose privacy policy, terms, support or data-deletion
# links do not load. Redirects are followed; the final status must be 200.
# Read-only: GET requests only. Needs bash and curl.
# Exit: 0 all 200, 1 any other status, 2 bad arguments.

set -euo pipefail

usage() {
  awk 'NR == 1 { next } /harness:managed/ { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
}

urls=()
case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  -f)
    [[ -f "${2:-}" ]] || { usage >&2; exit 2; }
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%%#*}"; line="${line//[[:space:]]/}"
      [[ -n "$line" ]] && urls+=("$line")
    done < "$2" ;;
  '') usage >&2; exit 2 ;;
  *) urls=("$@") ;;
esac
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 2; }

failed=0
for u in "${urls[@]}"; do
  case "$u" in http://*|https://*) ;; *) echo "not a URL: $u" >&2; exit 2 ;; esac
  code="$(curl -sS -L -o /dev/null -w '%{http_code}' --max-time 20 \
            -A 'Mozilla/5.0 (compatible; store-precheck/1.0)' "$u" 2>/dev/null || echo 000)"
  if [[ "$code" == "200" ]]; then
    printf '  200  %s\n' "$u"
  else
    printf '  %s  %s  <- FAIL\n' "$code" "$u"
    failed=$((failed + 1))
  fi
done
if [[ $failed -gt 0 ]]; then
  echo "$failed URL(s) did not return 200" >&2
  exit 1
fi
echo "all ${#urls[@]} URL(s) returned 200"
