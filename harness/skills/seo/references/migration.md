# Site Migrations

A migration is any change that moves indexed URLs or changes how they are served: new domain or subdomain, HTTP → HTTPS, new URL structure, new CMS or framework (rendering changes count), merging sites, or splitting one. Traffic loss in migrations almost always comes from missing or wrong redirects, leftover `noindex`/robots blocks, or several big changes shipped at once.

Rule zero: **change one thing at a time.** A domain move, a redesign and a CMS swap in one release make every drop undiagnosable. Avoid launching in the business's peak season.

## 1. Inventory (before any build work)

- [ ] Old URL list from **every** source: XML sitemaps, a full crawl (Screaming Frog or similar), server/CDN logs (URLs bots and people actually request), analytics landing pages, Search Console top pages and the Links report (externally linked URLs), and the CMS export. Include images, PDFs and other files that get search traffic.
- [ ] Baseline per template: clicks, impressions, indexed pages, top 100 pages by clicks and by referring links, Core Web Vitals. Save the exports with the date; the post-launch checks compare against them.
- [ ] Both old and new properties verified in Search Console and Bing Webmaster Tools, including every variant (http/https, www/non-www, subdomains).
- [ ] Bought domain? Check it for manual actions and leftover URL removals first.

## 2. Map every old URL

Run [`scripts/redirect_map.py`](../scripts/redirect_map.py) `<old list> <new list>`. It matches exact paths, then normalised paths, unique slugs and titles, and lists what it could not map.

- [ ] Each old URL → its **most relevant** new equivalent. Never a blanket redirect to the home page or a category: Google treats irrelevant redirects as soft 404s.
- [ ] Content not carried over returns **404 or 410**, deliberately. Decide per URL, using traffic and links from the inventory.
- [ ] Review every non-exact match by hand (the report lists them).
- [ ] Validate the final map: `redirect_map.py --check map.csv --new new_crawl.csv` (no chains, loops, self-redirects, or targets that 404).
- [ ] Update canonicals, hreflang, internal links, structured data URLs and XML sitemaps to the **new** URLs. Redirects are a safety net, not the linking strategy.

## 3. Staging checks

- [ ] Staging behind auth + `noindex`; production robots.txt and meta robots prepared separately (the most common migration failure is shipping staging's `noindex` or `Disallow: /`).
- [ ] Crawl staging with the redirect rules active: every old URL → one hop → 200.
- [ ] `scripts/lint_html.py` over the build output; `check-url.sh` on one URL per template.
- [ ] Rendering parity: titles, canonicals, content and links present in raw HTML (see technical.md §4).
- [ ] Server capacity for a crawl spike (Googlebot recrawls old and new URLs).

## 4. Launch day

- [ ] Redirects live: server-side **301/308**, single hop, straight to the final URL.
- [ ] Remove staging `noindex`/auth from production only; confirm robots.txt and `X-Robots-Tag`.
- [ ] Submit the new sitemap; keep a sitemap of the **old** URLs available briefly so crawlers find the redirects (redirect warnings on it are expected), then remove it.
- [ ] **Change of Address** in Search Console for domain or subdomain moves, submitted for **every verified variant** of the old site (www, non-www, subdomains, even unused ones). Not used for HTTP → HTTPS, www changes or path-only moves. Use it after the redirects are live; it needs owner access to both properties and lasts 180 days. In Bing Webmaster Tools, report the move with the Site Move tool and push changed URLs with IndexNow.
- [ ] Analytics, consent and conversion tracking firing on the new site; annotations added.
- [ ] Spot-check the top 50 old URLs by traffic and links: one hop, right destination, 200.
- [ ] Update the URLs you control elsewhere: Business Profile, social profiles, paid campaigns, email templates, app deep links, partner and directory listings.

## 5. After launch (dated checks)

| When | Check |
|---|---|
| T+1 day | Server logs: Googlebot/Bingbot hitting old URLs and getting 301s, no 5xx spike ([`bot_log_audit.py`](../scripts/bot_log_audit.py)); 404 report from logs; top pages spot-checked again |
| T+7 days | Search Console Page indexing (new URLs rising), Sitemaps report, crawl stats; fix every unexpected 404 with a mapped redirect |
| T+14 days | Clicks and impressions per template vs baseline ([`gsc_analyze.py decay`](../scripts/gsc_analyze.py) with equal periods); redirect map re-checked against fresh crawl |
| T+30 days | Old URLs dropping out of the index, new URLs ranking for the old queries; CWV field data for the new templates |
| T+90 days | Traffic recovered to baseline (adjusted for season)? If not, compare per template and per query set; check for lost content or internal links |
| T+365 days | Keep redirects at least a year (indefinitely is fine and safest when links point to old URLs); renew the old domain |

Expect fluctuations for a few weeks on small and medium sites, longer on large ones. Googlebot must recrawl every old and new URL before the move settles.

## Rollback criteria

Agree before launch what triggers a rollback or hotfix: e.g. site-wide `noindex`/robots block, more than 5% of top-traffic old URLs not redirecting correctly, a 5xx rate above normal, or conversions broken. A partial rollback that changes URLs again is worse than fixing forward; prefer fixing redirects and indexing signals in place.

## Sources
- https://developers.google.com/search/docs/crawling-indexing/site-move-with-url-changes
- https://developers.google.com/search/docs/crawling-indexing/site-move-no-url-changes
- https://support.google.com/webmasters/answer/9370220 (Change of Address tool)
- https://developers.google.com/search/updates (2026-06-17: Change of Address for all subdomain variants)
- https://blogs.bing.com/webmaster/2020/12/Website-Migration-with-Bing/ (Bing Site Move tool)
