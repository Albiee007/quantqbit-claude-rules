#!/usr/bin/env bash
# === seo data tool tests (stdlib Python only) ===
# gsc_analyze (striking, ctr, decay, cannibal, update), crawl_triage, redirect_map (build and
# check), bot_log_audit, ai_citations and lint_html against fixtures with known answers, plus
# JSON output, header overrides and bad-input exit codes.
# Usage: bash tests/seo.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
S="$ROOT/harness/skills/seo/scripts"
F="$ROOT/tests/fixtures/seo"
W="$(mktemp -d "${TMPDIR:-/tmp}/seo-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 12 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
run()   { local rc; hc_py "$@" > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
rc()    { [[ "$(cat "$W/rc")" == "$1" ]]; }
has()   { grep -qF -- "$1" "$W/out"; }
row()   { grep -F -- "$1" "$W/out" | grep -qF -- "$2"; }  # a line holding both strings
lacks() { ! grep -qF -- "$1" "$W/out"; }

echo "== gsc_analyze"
run "$S/gsc_analyze.py" striking "$F/query-page.csv"
check "striking: exit 0, 8 queries" eval 'rc 0 && has "8 queries on 8 pages"'
check "striking: weak CTR at pos 5 -> title tweak" row "crm for startups" "title tweak"
check "striking: pos 12 -> internal links" row "crm integrations" "internal links"
check "striking: pos 8 with normal CTR -> on-page addition" row "crm reports" "on-page addition"
check "striking: pos 1-3 excluded" eval 'lacks "| best crm |"'

run "$S/gsc_analyze.py" ctr "$F/query-page.csv"
check "ctr: site curve printed" has "pos 1: 30.0%"
check "ctr: two gaps found" eval 'row "crm for startups" "4.2%" && row "acme crm" "5.0%"'
check "ctr: healthy rows not flagged" eval 'lacks "crm demo"'

run "$S/gsc_analyze.py" decay "$F/decay-recent.csv" "$F/decay-previous.csv"
check "decay: both down -> rewrite" row "ex.com/a |" "| rewrite |"
check "decay: CTR down at stable position -> rewrite title/meta" row "ex.com/b |" "rewrite title/meta"
check "decay: rankings down -> refresh" row "ex.com/c |" "refresh"
check "decay: traffic gone -> investigate" row "ex.com/d |" "investigate"
check "decay: page missing from recent -> investigate" row "ex.com/i |" "investigate"
check "decay: demand down -> leave" row "ex.com/e |" "leave"
check "decay: position > 20 -> consolidate" row "ex.com/f |" "consolidate"
check "decay: small and stable pages skipped" eval 'lacks "ex.com/g |" && lacks "ex.com/h |"'

run "$S/gsc_analyze.py" cannibal "$F/query-page.csv" --brand acme
check "cannibal: one true case, one harmless overlap" eval 'has "1 queries where" && has "1 more queries show harmless overlap"'
check "cannibal: keeper by clicks" has "Keeper: https://ex.com/blog/crm-vs (53% of clicks)"
check "cannibal: close competitor -> consolidate or differentiate" has "consolidate the competing page"
run "$S/gsc_analyze.py" cannibal "$F/query-page.csv"
check "cannibal: brand query counted as overlap without --brand" has "2 more queries show harmless overlap"

run "$S/gsc_analyze.py" update "$F/update-daily.csv" --date 2026-08-20
check "update: winners/losers/flat counted" has "2 winners, 4 losers, 3 flat."
check "update: /blog/ section flagged as the loser pattern" row "| /blog/ |" "100.0%"
run "$S/gsc_analyze.py" update "$F/update-daily.csv" --date 2025-01-01
check "update: date outside the data exits 2" eval 'rc 2 && has "no rows in both windows"'

run "$S/gsc_analyze.py" striking "$F/query-page.csv" --json
check "json output parses and counts" eval 'rc 0 && hc_py -c "import json,sys; d=json.load(open(sys.argv[1])); assert d[\"count\"] == 8" "$W/out"'
sed 's/^query,page,clicks,impressions,ctr,position$/Suchanfrage,Seite,Klicks,Impressionen,CTR,Position/' "$F/query-page.csv" > "$W/de.csv"
run "$S/gsc_analyze.py" striking "$W/de.csv"
check "unknown headers exit 2 and point at --map" eval 'rc 2 && has "needs a query or page column" && has "--map query="'
run "$S/gsc_analyze.py" striking "$W/de.csv" --map query=Suchanfrage --map page=Seite --map clicks=Klicks --map impressions=Impressionen
check "--map overrides make localised exports work" eval 'rc 0 && has "8 queries on 8 pages"'
printf 'url,query,clicks,impressions,sum_position\nhttps://ex.com/x,crm api,5,200,1000\n' > "$W/bq.csv"
run "$S/gsc_analyze.py" striking "$W/bq.csv" --min-impressions 1
check "BigQuery sum_position becomes 1-based average position" row "crm api" "| 6 |"
run "$S/gsc_analyze.py" decay "$F/decay-recent.csv"
check "wrong file count exits 2" rc 2

echo "== crawl_triage"
run "$S/crawl_triage.py" "$F/crawl-internal-all.csv"
check "crawl: 12 issues in 10 types" has "16 URLs, 12 issues in 10 types"
check "crawl: equity-weighted top fix is the linked 404" has "1. **Update or remove internal links to 4xx"
check "crawl: second fix is the redirect chain" has "2. **Collapse chains"
check "crawl: canonical to another host is Critical" row "canon-bad" "Critical"
check "crawl: loop detected on both URLs" eval 'row "loop1" "redirect loop" && row "loop2" "redirect loop"'
check "crawl: orphan without depth detected" row "| orphan |" "Medium"
check "crawl: healthy pages not listed" eval 'lacks "ex.com/pricing |"'
run "$S/crawl_triage.py" "$F/robots.txt"
check "crawl: non-table input exits 2" rc 2

echo "== redirect_map"
run "$S/redirect_map.py" "$F/migrate-old.csv" "$F/migrate-new.csv"
check "map: 5 mapped, 1 unmapped, exit 1" eval 'rc 1 && has "5 mapped, 1 unmapped"'
check "map: all four match kinds used" has "exact 2, normalised 1, slug 1, title 1"
check "map: unmapped page listed, never sent home" eval 'row "old.ex.com/careers" "Careers" && lacks "careers | https://www.ex.com/ |"'
run "$S/redirect_map.py" "$F/migrate-old.csv" "$F/migrate-new.csv" --format next
check "map: next.js format is JSON with permanent redirects" eval 'hc_py -c "import json,sys; t=open(sys.argv[1]).read(); d=json.loads(t[t.index(\"[\"):]); assert all(r[\"permanent\"] for r in d) and len(d)==5" "$W/out"'
run "$S/redirect_map.py" --check "$F/redirect-map.csv" --new "$F/redirect-new.txt"
check "check: chain, loop, self and missing target found" eval 'rc 1 && has "chain: 2 hops" && has "redirect loop" && has "redirects to itself" && has "target not in the new site list"'
check "check: clean rule not flagged" eval 'lacks "/ok |"'

echo "== bot_log_audit"
run "$S/bot_log_audit.py" "$F/access.log" "$F/cdn.jsonl" --robots "$F/robots.txt" --ranges "Claude-SearchBot=$F/ranges-claude.json"
check "bots: combined log + JSON lines read" has "18 requests read; 16 from known search/AI bots."
check "bots: 403s -> blocked, training-bot advice" eval 'row "| GPTBot |" "blocked" && has "business decision"'
check "bots: 429s -> throttled" row "| ClaudeBot |" "throttled"
check "bots: 5xx -> erroring" row "| PerplexityBot |" "erroring"
check "bots: disallowed path -> robots" row "| Googlebot |" "robots"
check "bots: IP ranges verify identity" row "| Claude-SearchBot |" "50% of 2"
check "bots: unseen search bot reported" has "Search bots never seen: Applebot."
check "bots: unclassified bot listed" has "SomeBot/1.0"
check "bots: humans ignored" eval 'lacks "Chrome/130"'
printf 'not a log line\n' > "$W/junk.log"
run "$S/bot_log_audit.py" "$W/junk.log"
check "bots: unrecognised log exits 2" rc 2

echo "== ai_citations"
run "$S/ai_citations.py" --bing-queries "$F/bing-grounding.csv" --search "$F/search-queries.csv" --prompts "$F/prompt-results.csv"
check "citations: bucket counts" has "owned: 2 | contested: 1 | under-represented: 2 | absent: 1"
check "citations: ranking but rarely cited -> under-represented" eval 'row "crm pricing comparison" "| 1 |" && row "crm integrations list" "| 0 |"'
check "citations: competitor in the answer -> contested" row "best crm for startups | 1 | 1" "HubSpot"
check "citations: never cited -> absent with competitor" row "crm for law firms" "Clio"
check "citations: low-impression query skipped" eval 'lacks "obscure query"'
check "citations: Bing citation share shown when exported" row "best crm for startups | 3 | 500 | 12" "40%"
run "$S/ai_citations.py" --search "$F/search-queries.csv"
check "citations: needs bing or prompts input" rc 2

echo "== lint_html"
run "$S/lint_html.py" "$F/site"
check "lint: errors exit 1" eval 'rc 1 && has "5 pages, 6 errors"'
check "lint: relative canonical, noindex, alt and placeholder caught" eval 'row "blog/post.html" "relative canonical" && row "blog/post.html" "meta robots noindex" && row "blog/post.html" "without alt" && row "blog/post.html" "placeholder"'
check "lint: duplicate titles are errors" row "dup/a.html" "title shared with 1 other page"
check "lint: 404 page skips canonical and noindex" eval '! grep "^| 404.html" "$W/out" | grep -qE "canonical|noindex"'
run "$S/lint_html.py" "$F/site/index.html"
check "lint: good page passes (SVG <title> is not a second page title)" eval 'rc 0 && has "All pages pass."'
run "$S/lint_html.py" "$F/site" --exclude "blog/**" --exclude "dup/*"
check "lint: --exclude removes pages" eval 'rc 0 && has "2 pages, 0 errors"'
run "$S/lint_html.py" "$W/nowhere"
check "lint: missing path exits 2" rc 2

echo "== shared bot list"
hc_py - "$ROOT/harness/skills/seo/references" > "$W/out" 2>&1 <<'PY'
import json, sys
from pathlib import Path
ref = Path(sys.argv[1])
bots = json.loads((ref / "ai-bots.json").read_text(encoding="utf-8"))["bots"]
doc = (ref / "geo-ai-search.md").read_text(encoding="utf-8").lower()
missing = [b["token"] for b in bots if "`" + b["token"].lower() + "`" not in doc]
bad = [b["token"] for b in bots if b["purpose"] not in ("search", "training", "user", "control")]
print("missing from geo-ai-search.md:", missing, "bad purpose:", bad)
sys.exit(1 if missing or bad else 0)
PY
bots_rc=$?
check "ai-bots.json matches the crawler table in geo-ai-search.md" eval '[[ $bots_rc -eq 0 ]]'

echo
echo "seo tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
