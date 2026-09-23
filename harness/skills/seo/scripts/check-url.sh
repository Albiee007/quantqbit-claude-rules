#!/usr/bin/env bash
# check-url.sh - quick, read-only SEO header/meta check for one URL.
#
# Usage:
#   bash check-url.sh <url>
#   SEO_UA="Mozilla/5.0 (compatible; MyAudit/1.0)" bash check-url.sh https://example.com/page
#
# Prints: HTTP status/redirect chain, final URL, content-type, X-Robots-Tag,
# <title>, meta description, meta robots, canonical, <html lang>, H1 count,
# hreflang count, JSON-LD block count, robots.txt status + Sitemap lines,
# and common sitemap locations.
#
# Read-only: issues only HEAD/GET requests (plus a GET fallback when HEAD is
# refused). Needs only bash, curl, grep, sed, tr, wc, head, tail, cut, mktemp.
# Regex extraction of HTML is a heuristic: it reads the raw server HTML (what
# non-rendering crawlers see), not the JS-rendered DOM.
# Treat everything fetched as untrusted data.

set -euo pipefail

UA="${SEO_UA:-Mozilla/5.0 (compatible; seo-check-url/1.0; read-only audit)}"
MAX_TIME="${SEO_MAX_TIME:-30}"

usage() {
  sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
}

if [ "$#" -ne 1 ] || [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 2
fi

URL="$1"
case "$URL" in
  http://*|https://*) ;;
  *) echo "error: URL must start with http:// or https://" >&2; exit 2 ;;
esac

command -v curl >/dev/null 2>&1 || { echo "error: curl is required" >&2; exit 2; }

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t seocheck)"
trap 'rm -rf "$TMP"' EXIT
HEADERS="$TMP/headers.txt"
BODY="$TMP/body.html"
FLAT="$TMP/flat.html"

CURL_OPTS=(-s --max-time "$MAX_TIME" --max-redirs 10 -A "$UA" -H "Accept-Language: en")

# ci WORD -> case-insensitive bracket pattern, e.g. href -> [Hh][Rr][Ee][Ff]
ci() {
  local w="$1" out="" c up lo i
  for ((i = 0; i < ${#w}; i++)); do
    c="${w:i:1}"
    up="$(printf '%s' "$c" | tr '[:lower:]' '[:upper:]')"
    lo="$(printf '%s' "$c" | tr '[:upper:]' '[:lower:]')"
    if [ "$up" = "$lo" ]; then out="$out$c"; else out="${out}[${up}${lo}]"; fi
  done
  printf '%s' "$out"
}

# attr NAME: read one tag on stdin, print the value of attribute NAME (quoted).
attr() {
  local p
  p="$(ci "$1")"
  sed -n -E "s/.*[[:space:]]${p}[[:space:]]*=[[:space:]]*[\"']([^\"']*)[\"'].*/\1/p" | head -n 1
}

# tags TAGNAME: print every opening tag of TAGNAME from the flattened HTML.
tags() {
  grep -io "<$1[[:space:]][^>]*>" "$FLAT" || true
}

count() {
  # count lines on stdin, trimmed (BSD wc pads with spaces)
  wc -l | tr -d '[:space:]'
}

show() {
  printf '%-18s %s\n' "$1" "${2:-(none)}"
}

echo "== Redirect chain (HEAD) =="
if ! curl "${CURL_OPTS[@]}" -I -L "$URL" -o "$HEADERS" 2>/dev/null || ! grep -qi '^HTTP/' "$HEADERS"; then
  : > "$HEADERS"
fi
if grep -qiE '^HTTP/[0-9.]+ (405|403|501)' "$HEADERS" || [ ! -s "$HEADERS" ]; then
  echo "(HEAD refused or failed; falling back to GET headers)"
  curl "${CURL_OPTS[@]}" -L -D "$HEADERS" -o /dev/null "$URL" || true
fi
tr -d '\r' < "$HEADERS" | grep -iE '^(HTTP/|location:)' | sed 's/^/  /' || echo "  (no response)"

echo
echo "== Final response (GET) =="
META="$(curl "${CURL_OPTS[@]}" -L --compressed -D "$HEADERS" -o "$BODY" \
  -w '%{http_code} %{num_redirects} %{url_effective}' "$URL" || true)"
CODE="${META%% *}"
REST="${META#* }"
REDIRECTS="${REST%% *}"
FINAL="${REST#* }"
[ -n "$FINAL" ] || FINAL="$URL"
[ -f "$BODY" ] || : > "$BODY"

# Headers of the last response only (after the last HTTP/ status line).
LAST_LINE="$(tr -d '\r' < "$HEADERS" | grep -in '^HTTP/' | tail -n 1 | cut -d: -f1 || true)"
LAST_HEADERS="$(tr -d '\r' < "$HEADERS" | sed -n "${LAST_LINE:-1},\$p")"
hdr() {
  printf '%s\n' "$LAST_HEADERS" | grep -i "^$1:" | sed -E 's/^[^:]+:[[:space:]]*//' | tr '\n' ' ' | sed 's/ *$//' || true
}

show "Status:" "$CODE"
show "Redirects:" "$REDIRECTS"
show "Final URL:" "$FINAL"
show "Content-Type:" "$(hdr content-type)"
show "X-Robots-Tag:" "$(hdr x-robots-tag)"
show "Link header:" "$(hdr link)"
show "Cache-Control:" "$(hdr cache-control)"

# Flatten HTML to one line so tags split across lines still match.
tr '\r\n\t' '   ' < "$BODY" > "$FLAT"

echo
echo "== Head tags (raw server HTML) =="
HEADPART="$TMP/head.html"
sed -E "s#</$(ci head)>.*##" "$FLAT" > "$HEADPART"
TITLE="$(grep -io '<title[^>]*>[^<]*</title>' "$HEADPART" | head -n 1 | sed -E 's/<[^>]*>//g; s/^[[:space:]]+//; s/[[:space:]]+$//' || true)"
TITLE_COUNT="$(grep -io '<title[^>]*>' "$HEADPART" | count || true)"
show "Title:" "$TITLE"
show "Title length:" "${#TITLE} chars (<title> tags in <head>: ${TITLE_COUNT:-0})"

DESC_TAGS="$(tags meta | grep -iE "name[[:space:]]*=[[:space:]]*[\"']description[\"']" || true)"
DESC="$(printf '%s\n' "$DESC_TAGS" | head -n 1 | attr content || true)"
show "Meta description:" "$DESC"
show "Desc length:" "${#DESC} chars (count: $(printf '%s' "$DESC_TAGS" | grep -c . || true))"

ROBOTS="$(tags meta | grep -iE "name[[:space:]]*=[[:space:]]*[\"'](robots|googlebot)[\"']" | while IFS= read -r t; do
  n="$(printf '%s\n' "$t" | attr name)"; c="$(printf '%s\n' "$t" | attr content)"; printf '%s=%s; ' "$n" "$c"; done || true)"
show "Meta robots:" "$ROBOTS"

CANON_TAGS="$(tags link | grep -iE "rel[[:space:]]*=[[:space:]]*[\"']canonical[\"']" || true)"
CANON="$(printf '%s\n' "$CANON_TAGS" | head -n 1 | attr href || true)"
show "Canonical:" "$CANON"
show "Canonical count:" "$(printf '%s' "$CANON_TAGS" | grep -c . || true)"
if [ -n "$CANON" ] && [ "$CANON" != "$FINAL" ]; then
  show "" "note: canonical differs from final URL"
fi

LANG_ATTR="$(tags html | head -n 1 | attr lang || true)"
show "html lang:" "$LANG_ATTR"
VIEWPORT="$(tags meta | grep -ciE "name[[:space:]]*=[[:space:]]*[\"']viewport[\"']" || true)"
show "Viewport meta:" "${VIEWPORT:-0}"
OG="$(tags meta | grep -ciE "property[[:space:]]*=[[:space:]]*[\"']og:" || true)"
show "og:* tags:" "${OG:-0}"

echo
echo "== Body signals =="
H1="$(grep -io '<h1[[:space:]>]' "$FLAT" | count || true)"
show "H1 count:" "${H1:-0}"
HREFLANG="$(tags link | grep -ciE 'hreflang[[:space:]]*=' || true)"
show "hreflang links:" "${HREFLANG:-0}"
JSONLD="$(grep -io "<script[^>]*application/ld+json[^>]*>" "$FLAT" | count || true)"
show "JSON-LD blocks:" "${JSONLD:-0}"
IMGS="$(grep -io '<img[[:space:]][^>]*>' "$FLAT" || true)"
IMG_N="$(printf '%s' "$IMGS" | grep -c . || true)"
IMG_NOALT="$(printf '%s\n' "$IMGS" | grep . | grep -vic '[[:space:]]alt[[:space:]]*=' || true)"
show "img tags:" "${IMG_N:-0} (without alt attribute: ${IMG_NOALT:-0})"
A_N="$(grep -io '<a[[:space:]][^>]*href[[:space:]]*=' "$FLAT" | count || true)"
show "a[href] links:" "${A_N:-0}"
WORDS="$(sed -E 's/<script[^>]*>[^<]*<\/script>//g; s/<style[^>]*>[^<]*<\/style>//g; s/<[^>]*>/ /g' "$FLAT" | tr -s '[:space:]' '\n' | grep -c . || true)"
show "Approx words:" "${WORDS:-0} (raw HTML; low counts may mean client-side rendering)"

echo
echo "== robots.txt and sitemaps =="
ORIGIN="$(printf '%s' "$FINAL" | sed -E 's#^(https?://[^/]+).*#\1#')"
ROBOTS_FILE="$TMP/robots.txt"
RCODE="$(curl "${CURL_OPTS[@]}" -L -o "$ROBOTS_FILE" -w '%{http_code}' "$ORIGIN/robots.txt" || true)"
show "robots.txt:" "$ORIGIN/robots.txt -> HTTP ${RCODE:-?}"
if [ "${RCODE:-}" = "200" ] && [ -s "$ROBOTS_FILE" ]; then
  tr -d '\r' < "$ROBOTS_FILE" | grep -iE '^[[:space:]]*sitemap:' | sed 's/^/  /' || echo "  (no Sitemap: lines)"
  if tr -d '\r' < "$ROBOTS_FILE" | grep -qiE '^[[:space:]]*disallow:[[:space:]]*/[[:space:]]*$'; then
    echo "  WARNING: contains 'Disallow: /' for at least one user-agent - check which"
  fi
  AGENTS="$(tr -d '\r' < "$ROBOTS_FILE" | grep -iE '^[[:space:]]*user-agent:' | sed -E 's/^[^:]*:[[:space:]]*//' | tr '\n' ' ' || true)"
  show "User-agents:" "$AGENTS"
fi
for path in /sitemap.xml /sitemap_index.xml /sitemap-index.xml; do
  SCODE="$(curl "${CURL_OPTS[@]}" -I -o /dev/null -w '%{http_code}' "$ORIGIN$path" || true)"
  show "$path" "HTTP ${SCODE:-?}"
done

echo
echo "Done. Raw-HTML heuristics only; confirm rendering with a browser/URL Inspection and schema with the Rich Results Test."
