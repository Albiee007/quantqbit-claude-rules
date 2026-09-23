# Technical SEO

Goal: every URL you want in search is discoverable, crawlable, renderable, indexable, and consolidated to one canonical; everything else is excluded cleanly.

Search works in three stages: **crawl** (discover URLs via links and sitemaps, fetch them), **index** (render, parse, pick a canonical, store), **serve** (rank). A failure at any stage caps everything downstream, which is why technical issues get Critical/High severity.

## 1. Crawlability

### robots.txt
- Lives at the root of each host/protocol: `https://example.com/robots.txt`. Subdomains need their own.
- Google reads up to 500 KiB; content beyond that is ignored. `Crawl-delay` is ignored by Google (some other crawlers honour it).
- Purpose is **crawl traffic management**, not index control. A disallowed URL can still be indexed (without content) if linked from elsewhere. To keep a page out of results use `noindex` (and allow crawling so the directive is seen) or authentication.
- Never disallow CSS, JS, fonts, or image paths needed to render the page.
- `noindex` inside robots.txt is not supported.
- Reference sitemaps: `Sitemap: https://example.com/sitemap.xml` (absolute URL, may repeat).
- Status handling: 4xx (except 429) on robots.txt → treated as "no restrictions"; 5xx/unreachable → Google stops crawling the site for ~12 h, then falls back to a cached copy for up to 30 days. Keep it served reliably with 200. Google caches robots.txt for up to ~24 h, so changes are not instant.
- Only `user-agent`, `allow`, `disallow`, `sitemap` are supported by Google; `*` and `$` wildcards work in paths; the most specific (longest) matching rule wins.

Check: `Disallow: /` left over from staging (Critical); blocking `/_next/`, `/static/`, `/assets/` (High); wildcard rules blocking parameterised canonical URLs.

### Meta robots and X-Robots-Tag
- `<meta name="robots" content="noindex, nofollow">` in HTML; `X-Robots-Tag: noindex` HTTP header for non-HTML (PDFs, images) or edge-level control.
- Useful directives: `noindex`, `nofollow`, `nosnippet`, `max-snippet:N`, `max-image-preview:large`, `unavailable_after:<date>`. `data-nosnippet` attribute hides specific elements from snippets.
- Conflicting directives: the most restrictive wins.
- Bot-specific: `<meta name="googlebot" content="…">`.

### Link discovery
- Google follows `<a href>` links. Buttons with JS handlers, `onclick` navigation, and hash-bang routes are not reliably crawled.
- Keep important pages ≤3 clicks from home; avoid orphans (pages only in the sitemap).
- `rel="nofollow"`, `rel="sponsored"` (paid/affiliate), `rel="ugc"` (user content) are hints for outbound links.

### Crawl budget
Only relevant for large (roughly 10k+ URL) or fast-changing sites. Waste comes from: faceted/parameter URLs, infinite calendars, session IDs, redirect chains, soft 404s, and slow servers. Monitor Search Console Crawl Stats and server logs.

## 2. Indexability and canonicalisation

### Canonical signals (strongest → weakest)
1. 301/308 redirect to the canonical.
2. `<link rel="canonical" href="https://…">` (or `Link: <…>; rel="canonical"` header).
3. Inclusion in the sitemap.
Internal linking consistency and HTTPS also influence selection. Canonical is a hint; Google may choose differently if signals conflict.

Rules:
- Absolute URLs, one canonical per page, same value in every method (tag, header, sitemap, hreflang, internal links).
- Self-referencing canonical on every indexable page.
- Do not use robots.txt or `noindex` to canonicalise within a site; do not use the URL removal tool for it.
- Never combine `noindex` with a canonical pointing elsewhere (mixed signal).
- Canonical target must return 200, be indexable, and not redirect.
- Cross-domain canonicals are allowed for syndicated content.

### Duplicate content sources
`http` vs `https`, `www` vs apex, trailing slash vs none, upper vs lower case, `index.html`, tracking parameters (`utm_*`, `gclid`), sort/filter params, printer versions, staging hosts, and CMS tag/archive pages. Pick one form, 301 the rest, and link internally only to the canonical form.

### Thin and low-value pages
Empty category/tag archives, search result pages, zero-result filter pages, near-duplicate location pages. Either improve, consolidate (301), `noindex`, or return 404. Internal site search results should be `noindex` and ideally disallowed.

## 3. HTTP status codes

| Code | Use |
|---|---|
| 200 | Real content. |
| 301 / 308 | Permanent move; passes signals. Use for migrations, slug changes, canonical host/slash normalisation. |
| 302 / 307 | Temporary (A/B, geo, maintenance). Long-lived 302s are eventually treated as 301 but do not rely on it. |
| 304 | Conditional GET not modified; fine. |
| 404 | Not found. Correct for missing pages; do not redirect all 404s to home (Google treats as soft 404). |
| 410 | Gone permanently; slightly faster removal than 404. |
| 429 / 503 | Temporary overload/maintenance; add `Retry-After`. Prolonged 5xx leads to deindexing. |
| 5xx | Server error; Critical if on important templates. |

**Soft 404**: a 200 response whose content says "not found" or is empty. SPAs are the usual culprit — fix by making the server return 404, or client-side redirect to a URL that returns 404, or inject `noindex`.

**Redirects**: single hop, server-side (not meta refresh or JS when avoidable), map old → most relevant new URL (not home), keep redirects for at least a year after migrations, update internal links, canonicals, sitemaps, and hreflang to final URLs. Avoid loops and chains of 3+.

## 4. JavaScript rendering

Google renders pages with a recent headless Chromium, but rendering is queued after crawling and other crawlers (most AI crawlers, social preview bots) generally do not execute JS. Therefore:

- **Prefer SSR, SSG, ISR, or prerendering** for all indexable content, links, and metadata. Client-side rendering only for app-like, non-indexable surfaces (dashboards behind login).
- Title, meta description, canonical, meta robots, hreflang, and JSON-LD must be in the **initial HTML**. If a canonical is set by JS, it must equal the one in raw HTML (or be absent from raw HTML).
- Do not ship `noindex` in raw HTML expecting JS to remove it — Google may skip rendering on seeing `noindex`.
- Return correct HTTP status from the server; do not rely on JS-injected content on error pages.
- Use the History API for routes (real paths), never `#` fragments for distinct content.
- Links as `<a href>`; lazy-loaded content must load without user interaction (scroll events are not triggered by Googlebot) — use IntersectionObserver or native lazy loading.
- Do not block rendering resources in robots.txt; keep bundle URLs stable enough for caching (content hashing is fine).
- Hydration mismatches can change visible content between raw and rendered HTML; keep them equal.
- Dynamic rendering (serving bots a different prerendered version) is a deprecated workaround; prefer real SSR. Serving different content to bots than users is cloaking.

Framework notes:
- **Next.js (App Router)**: server components by default; use `generateMetadata`/`metadata` export, `app/sitemap.ts`, `app/robots.ts`; `notFound()` returns a real 404; `redirect()`/`permanentRedirect()` for 307/308. Avoid `"use client"` at page root for content pages.
- **Nuxt**: SSR on by default (`ssr: true`); `useHead`/`useSeoMeta`; use route rules for prerender/ISR.
- **SvelteKit / Remix / Astro**: SSR or static by default; ensure `+page.server`/loaders set status via `error(404)`.
- **Angular**: use SSR (`@angular/ssr`) for public pages; `Meta`/`Title` services.
- **Vite + React SPA**: add prerendering or move public pages to an SSR framework.

Verification: compare `curl -s URL` (raw) with the URL Inspection tool's rendered HTML or a headless browser snapshot; content, links, and head tags should match.

## 5. URL structure

- Readable, lowercase, hyphen-separated words; no spaces, underscores, or session IDs.
- Hierarchy reflects IA only where helpful (`/guides/seo/canonical-tags`), not deep for its own sake.
- Stable: changing URLs costs signals; if you must, 301.
- Keep parameters for filtering/sorting/tracking, not for primary content identity. Consistent parameter order.
- One trailing-slash policy, enforced by 301. One case policy (lowercase), enforced by 301.
- Non-ASCII paths are allowed (UTF-8, percent-encoded in HTML) — keep them consistent.

## 6. Pagination and infinite scroll

- Each page gets a unique URL (`/blog?page=2` or `/blog/page/2`) and a **self-referencing canonical**. Do not canonicalise all pages to page 1.
- Link sequentially with `<a href>` (next/previous and ideally numbered links). Google no longer uses `rel="next"/"prev"`; harmless to keep for other engines.
- Infinite scroll: back it with paginated URLs that are crawlable and update the URL via History API as the user scrolls.
- "View all" page can be the canonical only if it is fast and actually shows all items.

## 7. Faceted navigation (filters, sort)

Preferred: prevent crawling of facet combinations that have no search demand.
- `Disallow` facet parameter patterns in robots.txt, or implement filters with URL fragments (`#color=red`) that crawlers ignore.
- Less effective alternatives: `rel="canonical"` to the unfiltered category, `rel="nofollow"` on facet links.
- If some facets deserve indexing (e.g. "red running shoes" has demand), give them clean static URLs, unique titles/H1/copy, self-canonicals, and include them in the sitemap.
- Use consistent parameter order and `&` separators; return **404 for zero-result filter combinations**.

## 8. HTTPS and security

- HTTPS everywhere; 301 `http` → `https`; valid certificate; no mixed content.
- HSTS (`Strict-Transport-Security`) once HTTPS is stable.
- Security headers (CSP, X-Content-Type-Options, Referrer-Policy, frame-ancestors) are not ranking factors but protect against hacked-content spam, which is.
- Monitor Search Console Security Issues; hacked pages → Critical.

## 9. Mobile-first indexing

Google indexes the mobile rendering of every site. The mobile version must contain the same primary content, headings, structured data, metadata, images (with alt), and internal links as desktop. Avoid content hidden behind interactions that require clicks to load (tabs/accordions are fine if the content is in the DOM). Responsive design with a viewport meta tag is the default approach; avoid separate m-dot sites.

## 10. Server logs

Logs are the ground truth of crawling. Useful analyses:
- Googlebot hits by status code and template; time spent on parameter/facet URLs.
- Important URLs never crawled; orphan URLs crawled but not linked.
- Verify real Googlebot via reverse DNS (`*.googlebot.com`/`*.google.com`) or Google's published IP ranges — user-agent strings are spoofed.
- Response time trends (slow TTFB reduces crawl rate).

## 11. IndexNow

Protocol to notify participating engines (e.g. Bing, Yandex, Naver, Seznam) of URL changes; participants share submissions with each other. **Google does not participate** — use sitemaps with accurate `lastmod` for Google.
- Host a key file (`/<key>.txt`, 8–128 hex chars) or declare `keyLocation`.
- Single URL: `GET https://api.indexnow.org/indexnow?url=<url>&key=<key>`; bulk: `POST /indexnow` JSON `{host, key, keyLocation?, urlList}` up to 10,000 URLs.
- Submit only on real add/update/delete events. **Submitting is an external side effect — requires explicit user approval** (SKILL.md safety rule 1). In code, wire it into the publish pipeline behind a config flag rather than calling it ad hoc.

## 12. Other checks

- **International**: see international-hreflang.md.
- **Structured data**: see schema.md.
- **Internal search / preview URLs**: `noindex`.
- **Staging**: HTTP auth + `noindex` header; never rely on robots.txt alone.
- **Migrations**: crawl old site, build a 1:1 redirect map, keep old sitemap submitted briefly so Google recrawls redirects, monitor 404s and index coverage for weeks.
- **Search Console**: Page indexing report (reasons: "Crawled – currently not indexed", "Duplicate, Google chose different canonical", "Blocked by robots.txt", "Soft 404"), URL Inspection for live tests.

## Severity cheat-sheet

| Finding | Severity |
|---|---|
| Site-wide `noindex` or `Disallow: /` on production | Critical |
| Canonical pointing to another host/staging/404 | Critical |
| Key templates return 5xx or soft 404 | Critical |
| Indexable content only rendered client-side | High |
| Redirect chains ≥3 hops / loops | High |
| Mixed canonical signals (tag vs sitemap vs links) | High |
| Faceted URLs crawlable at scale | High (large sites) / Medium |
| Pagination canonicalised to page 1 | Medium |
| Trailing slash/case not normalised | Medium |
| Missing IndexNow | Low (only if Bing traffic matters) |

## Sources
- https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/docs/crawling-indexing/robots/intro
- https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading
- https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation
- https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
- https://developers.google.com/search/updates
- https://www.indexnow.org/documentation
- claude-seo v1.9.9 `seo-technical` skill (AgriciDaniel, MIT) — category structure
