# Website and webapp launch checklist

Use this before a public website or web product goes live, after a migration or redesign (full playbook: [migration.md](migration.md)), and as the recurring health check in section 18. It covers indexing, sitemaps, performance, accessibility, security, privacy, measurement and webapp concerns. Where a topic has a deep reference, the item links to it instead of repeating it. Facts checked against official sources as of 2026-10-12; re-verify the items marked *(changes often)* every quarter.

**How to grade.** Each item says **how to verify** it. Mark every item PASS, FAIL, NOT-VERIFIABLE or N/A, with evidence (URL, header, report screenshot, tool output).

**Tags.**
- **Site**: marketing sites, blogs, docs, landing pages.
- **App**: logged-in web products, dashboards, PWAs.
- **Both**: applies to both.
- **P0**: launch blocker. **P1**: fix in the first sprint after launch. **P2**: backlog.

Most webapps have both surfaces: public pages that should rank, and an app behind login that should not. Grade each surface separately.

**Verification tools.**
- [check-url.sh](../scripts/check-url.sh) `<url>` prints status, redirects, robots, canonical, title, description, H1, hreflang, JSON-LD, `lang` and viewport, images without alt, plus robots.txt and sitemap status.
- `curl -sI <url>` for response headers.
- Google Search Console (GSC) and Bing Webmaster Tools.
- Rich Results Test.
- PageSpeed Insights (PSI) and CrUX.
- Lighthouse and axe.

Submitting anything to an external service (GSC, Bing, IndexNow, directories) needs the user's explicit approval (seo skill, safety rule 1).

## 1. Domain, hosting, HTTPS
- [ ] **One canonical host** (www or apex). The other host, `http://` and any old domains 301 to it in one hop. **P0 · Both.** Verify: run `check-url.sh` on each variant; the redirect chain has one hop.
- [ ] **HTTPS everywhere, no mixed content.** TLS 1.2+ and a certificate that renews automatically. **P0 · Both.** Verify: browser console shows no mixed-content warnings; check the certificate expiry date and renewal job.
- [ ] **HSTS** (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) once HTTPS is stable on every subdomain. Preload is optional. **P1 · Both.** Verify: `curl -sI`.
- [ ] **Compression and protocol:** Brotli or gzip for text, HTTP/2 or HTTP/3. **P1 · Both.** Verify: `content-encoding` header; protocol column in DevTools.
- [ ] **Caching:** hashed static assets get `Cache-Control: public, max-age=31536000, immutable`. HTML is short-lived or revalidated. No `no-store` on public pages, because it blocks the back/forward cache. **P1 · Both.** Verify: `Cache-Control` in `check-url.sh` output and `curl -sI` on an asset.
- [ ] **CDN or edge caching** for static assets and public pages. Bot-protection settings reviewed (see section 9). **P2 · Both.**

## 2. Crawling and indexing
Deep reference: [technical.md](technical.md).
- [ ] **robots.txt** returns 200 and is under 500 KiB. No `Disallow: /` on production. CSS, JS, fonts and images are not blocked. It has an absolute `Sitemap:` line. It is not used to hide pages; use `noindex` or auth for that. **P0 · Both.** Verify: robots section of `check-url.sh`; GSC robots.txt report.
- [ ] **No stray `noindex`** in meta robots or `X-Robots-Tag` on pages meant to rank. If a page might be indexed, keep `noindex` out of the original HTML; Google may not render the page to see JS remove it. Google reads robots meta even outside `<head>`, so a stray tag in the body still counts. **P0 · Both.** Verify: `check-url.sh` per template; GSC URL Inspection.
- [ ] **Real status codes.**
  - Missing pages return 404, or 410 if gone for good. No soft 404s (a 200 page saying "not found"), and nothing redirects everything to home.
  - Pages you want indexed return 200. Google may not render non-200 responses at all.
  - 429 and 503 responses include `Retry-After`.

  **P0 · Both.** Verify: request a nonsense URL and check the status.
- [ ] **Staging and preview environments** sit behind HTTP auth and send `X-Robots-Tag: noindex`. Production never links to them. **P0 · Both.** Verify: request a staging URL without credentials; it returns 401.
- [ ] **Search Console and Bing Webmaster Tools verified** for the canonical host, as a Domain property where possible. The owner list is reviewed. **P0 · Site.** Verify: property settings.
- [ ] **Sitemap submitted** in GSC and Bing. Done by a human or with approval. **P1 · Site.** Verify: GSC Sitemaps report shows "Success" and the discovered URL count.
- [ ] **Key templates inspected** with URL Inspection: live test, rendered HTML, the canonical Google chose, crawl allowed. **P1 · Site.**
- [ ] **Page indexing report** reviewed after launch. Every "Not indexed" reason is either intended (noindex, alternate canonical, redirect) or ticketed. **P1 · Site.** Verify: GSC report, re-checked at T+7 and T+30.
- [ ] **IndexNow** for Bing, Yandex and similar engines when Bing traffic matters. **P2 · Site.**

## 3. XML sitemaps
Deep reference: [sitemaps.md](sitemaps.md).
- [ ] **Generated from routes or CMS data**, served as `application/xml` in UTF-8, with absolute same-host URLs. **P0 · Site.** Verify: fetch it and check the `content-type`.
- [ ] **Only canonical, 200, indexable URLs.** No redirects, 404s, noindex, parameter or app URLs. **P0 · Site.** Verify: sample 20 URLs with `check-url.sh`.
- [ ] **At most 50,000 URLs and 50 MB uncompressed per file.** Use a sitemap index beyond that; large sites split by template. **P0 · Site.**
- [ ] **`<lastmod>` in W3C format**, changed only when content really changes. No `priority` or `changefreq` (Google ignores both). No ping calls; the ping endpoints are retired. **P1 · Site.**
- [ ] **Image, video or news sitemaps** (or extensions) where those are the content. hreflang alternates can live in the sitemap instead of the `<head>`. **P2 · Site.**
- [ ] **Unit test** that the sitemap parses and its URLs are absolute, unique and same-host. **P1 · Site.**

## 4. URLs, canonicals, redirects, pagination, facets
Deep reference: [technical.md](technical.md).
- [ ] **URLs are lowercase, hyphenated and readable.** One trailing-slash policy, enforced by 301. **P1 · Site.**
- [ ] **Canonical tags.** One absolute, self-referencing canonical per page. It returns 200, is identical in the raw HTML and after hydration, and is never combined with `noindex`. **P0 · Site.** Verify: canonical count and match in `check-url.sh`.
- [ ] **Redirects.** Server-side, single-hop 301 or 308. No chains or loops. Internal links point to the final URLs. A migration redirect map is kept for at least a year. **P0 · Both.**
- [ ] **Pagination.** One URL per page, a self-canonical on each, and `<a href>` links between pages. **P1 · Site.**
- [ ] **Facets, sort orders and internal search results** are not indexable. Filter combinations with zero results return 404. **P1 · Site.**

## 5. Rendering and JavaScript
Deep reference: [technical.md](technical.md) §4.
- [ ] **Indexable content, links and head tags rendered on the server:** SSR, SSG, ISR or prerender. **P0 · Site.** Verify: view-source, or `curl`, shows the content; the word count in `check-url.sh` is not near zero.
- [ ] **Navigation uses real `<a href="/path">` links.** No onclick-only links and no `#!` routes. Lazy content loads without scrolling or clicking. **P0 · Site.** Verify: `a[href]` count in `check-url.sh`; test with JS disabled.
- [ ] **JS paywalls and gated content** follow Google's paywalled-content guidance (`isAccessibleForFree` markup), so they are not treated as cloaking. **P2 · Site.**

## 6. On-page metadata and social cards
Deep reference: [on-page.md](on-page.md).
- [ ] **Title.** One unique `<title>` per page, topic first, brand last, about 50–60 characters. **P0 · Site.** Verify: `check-url.sh`.
- [ ] **Meta description.** One unique description, about 120–160 characters. No `meta keywords`. **P1 · Site.**
- [ ] **Headings.** Exactly one `<h1>`, then a logical H2→H3 structure. Semantic landmarks (`<main>`, `<nav>`, `<header>`, `<footer>`). **P1 · Site.**
- [ ] **Document basics.** `<html lang>`, `<meta charset>`, and the viewport tag `width=device-width, initial-scale=1`. **P0 · Both.**
- [ ] **Open Graph and Twitter.**
  - `og:title`, `og:description`, `og:url`, `og:type` and `og:site_name`.
  - `og:image` as an absolute URL, at least 1200×630 and under 5 MB.
  - `twitter:card=summary_large_image`.

  **P1 · Both** (shared app links need these too). Verify: `og:` count in `check-url.sh`; preview the link in Slack or LinkedIn.
- [ ] **Favicon and site name.** A square favicon of 48 px or more at a stable, crawlable URL. WebSite JSON-LD `name` and `alternateName` control the site name shown in results. **P1 · Site.** Icon sizes: [icon-specs.md](../../app-icons/references/icon-specs.md).
- [ ] **Breadcrumbs** on deep hierarchies, with BreadcrumbList markup. **P2 · Site.**

## 7. Structured data
Deep reference: [schema.md](schema.md), templates in [schema-templates.json](schema-templates.json).
- [ ] **JSON-LD in the initial HTML**, built from the same data as the visible content. No leftover `{{` placeholders. **P1 · Site.** Verify: JSON-LD count in `check-url.sh`; Rich Results Test and Schema Markup Validator for each template.
- [ ] **Right types per page.**
  - Home: Organization (with `sameAs`) and WebSite.
  - Articles: Article, with an author linked to a Person.
  - Products: Product with Offer, shipping and returns.
  - Also as relevant: BreadcrumbList, LocalBusiness, VideoObject, SoftwareApplication.

  **P1 · Site.**
- [ ] **Don't build retired rich results.** *(changes often)* None of these show in Search any more, so don't expect results from them:
  - FAQ: stopped showing 2026-05-07; docs removed 2026-06-15.
  - HowTo.
  - Practice problem.
  - Course info.
  - Estimated salary.
  - Learning video.
  - Special announcement.
  - Vehicle listing.
  - ClaimReview.
  - Book actions.

  Keep valid markup only if another consumer uses it. **P1 · Site.**
- [ ] **Reviews and ratings.** No ratings on your own business's markup. No fake reviews, and no undisclosed incentivized reviews (review-snippet guideline added 2026-07-24). **P0 · Site.**

## 8. Content, E-E-A-T and trust pages
Deep reference: [content-eeat.md](content-eeat.md).
- [ ] **People-first content** that matches the search intent. No thin, duplicate or scaled auto-generated pages. **P1 · Site.**
- [ ] **Trust pages exist and are linked from the footer:** About, Contact, Privacy policy, Terms, and Refund/Returns for commerce. Editorial policy for publishers. **P0 · Both.**
- [ ] **Authorship and dates.** Bylines link to author pages. Pages show published and updated dates. Ads and affiliate links are disclosed. YMYL topics are reviewed by an expert. **P1 · Site.**

## 9. AI search (AI Overviews, AI Mode, answer engines)
Deep reference: [geo-ai-search.md](geo-ai-search.md).
- [ ] **No special work is needed for Google's AI features.** A page that is indexed and eligible for a snippet is eligible for AI Overviews and AI Mode. No AI-specific file or markup is required. **P1 · Site.**
- [ ] **Search bots are allowed through robots.txt and the WAF/CDN:** Googlebot, Bingbot, `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`. Watch for default "block AI bots" toggles. *(changes often)* **P0 · Site.** Verify: robots.txt user-agents in `check-url.sh`; CDN bot settings.
- [ ] **Training-bot and `Google-Extended` policy** recorded as a business decision. Blocking them does not remove you from Search. **P2 · Site.**
- [ ] **Snippet controls are deliberate:** `nosnippet`, `data-nosnippet`, `max-snippet`. They also limit what AI features show. **P2 · Site.**
- [ ] **Citable structure.** Each section opens with a direct answer, cites its facts, shows visible dates, and has clear entity data (Organization/Person `sameAs`). **P2 · Site.**
- [ ] **llms.txt is optional.** Google Search does not use it (clarified 2026-06-15). Its absence is not a defect. Worth adding for developer docs. **P2 · Site.**

## 10. Images and video
Deep reference: [images.md](images.md).
- [ ] **Image markup.** Meaningful images use `<img>` with descriptive `alt`; decorative ones use `alt=""`. Every image has `width`/`height` or `aspect-ratio`. **P0 · Both.** Verify: images-without-alt in `check-url.sh`.
- [ ] **LCP image** is eager-loaded with `fetchpriority="high"`. Lazy-load only below the fold. AVIF or WebP with `srcset`/`sizes`. Hero image ≤ 200 KB. **P1 · Both.**
- [ ] **Video.** Each video has a stable watch page, VideoObject markup and a thumbnail. Embeds use a facade. **P2 · Site.**
- [ ] **User uploads** have GPS/EXIF data stripped. **P1 · App.**

## 11. Conditional areas
- [ ] **Multilingual or multi-region:**
  - One URL per locale.
  - Reciprocal hreflang that includes the page itself and `x-default`.
  - No automatic redirects by IP or `Accept-Language`.

  See [international-hreflang.md](international-hreflang.md). **P0 if applicable · Site.**
- [ ] **Local business:**
  - NAP (name, address, phone) matches everywhere.
  - One page per real location.
  - Specific LocalBusiness subtype.
  - Google Business Profile kept current.

  See [local.md](local.md). **P1 if applicable · Site.**
- [ ] **E-commerce:**
  - Product + Offer markup with GTIN, shipping and returns.
  - Out-of-stock pages stay live with a 200.
  - Discontinued products 301 to a successor, or return 404/410.
  - Merchant Center feed matches the page.

  See [ecommerce.md](ecommerce.md). **P1 if applicable · Site.**
- [ ] **Programmatic pages** meet the uniqueness thresholds and are piloted on 50–100 pages first. See [programmatic.md](programmatic.md). **P0 if applicable · Site.**

## 12. Performance and Core Web Vitals
Deep reference: [core-web-vitals.md](core-web-vitals.md), [performance.md](../../coding-standards/references/performance.md).
- [ ] **Core Web Vitals at p75, mobile and desktop:** LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1. Supporting targets: TTFB ≤ 0.8 s, FCP < 1.8 s. **P0 · Both** (P1 until field data exists). Verify: PSI field data or CrUX; lab Lighthouse before launch.
- [ ] **Budgets enforced in CI:**
  - About 170 KB compressed first-party JS on content pages.
  - Code-split routes in apps.
  - Lighthouse CI or a bundle-size check fails the build when over budget.

  **P1 · Both.**
- [ ] **Third parties.** No render-blocking third-party scripts and no anti-flicker snippets. Chat widgets, video and maps load behind facades. A tag-manager owner reviews new tags. **P1 · Both.**
- [ ] **Fonts.** Self-hosted, `font-display: swap` or `optional`, with fallback metric overrides. Preload only the one or two critical fonts. **P1 · Both.**
- [ ] **No layout shift.** Space is reserved for ads, embeds and banners. The cookie banner overlays the page instead of pushing it down. **P1 · Both.**
- [ ] **bfcache-eligible:** no `unload` handlers and no `no-store` on public HTML. **P2 · Both.** Verify: DevTools › Application › Back/forward cache.
- [ ] **Real-user monitoring** with the `web-vitals` library (including INP attribution) sent to analytics or RUM. **P1 · Both.**

## 13. Accessibility (WCAG 2.2 AA)
Deep reference: [wcag-22-aa.md](../../ui-ux/references/wcag-22-aa.md).
- [ ] **WCAG 2.2 AA is the target.** It also covers 2.1 AA, which most laws reference. **P0 · Both.**
- [ ] **Top failures fixed:**
  - Contrast: 4.5:1 for text, 3:1 for large text and UI parts.
  - Form inputs labelled.
  - Alt text present.
  - Visible focus that is not hidden by sticky headers, cookie banners or chat (2.4.11).
  - Targets at least 24×24 px (2.5.8).
  - Pages reflow at 320 px wide and still work at 200% text size.
  - Skip link.
  - Status messages use `aria-live`.
  - Paste allowed in password and OTP fields (3.3.8).
  - Dragging has a single-pointer alternative (2.5.7).

  **P0 · Both.** Verify: axe with zero serious or critical issues on key templates; a keyboard-only pass; a screen-reader pass (NVDA or VoiceOver); 400% zoom.
- [ ] **European Accessibility Act**, in force since 2025-06-28, if you sell to EU consumers (e-commerce, banking, e-books, transport, communications). Meet EN 301 549 (WCAG-based) and publish an accessibility statement covering conformance, known gaps and a feedback contact. Microenterprise service providers are exempt; confirm scope with legal. **P0 if in scope · Both.**
- [ ] **Reduced motion respected** (`prefers-reduced-motion`). No content flashes more than 3 times per second. **P1 · Both.**

## 14. Security
Deep reference: the `security` rule and [security-owasp.md](../../coding-standards/references/security-owasp.md).
- [ ] **Security headers.**
  - `Content-Security-Policy`: nonce- or hash-based, with `frame-ancestors`. Start in report-only mode if needed.
  - `Strict-Transport-Security`.
  - `X-Content-Type-Options: nosniff`.
  - `Referrer-Policy: strict-origin-when-cross-origin`.
  - `Permissions-Policy`, which denies camera, microphone, geolocation and the like unless used.
  - `Cross-Origin-Opener-Policy: same-origin` for apps.

  **P0 · App, P1 · Site.** Verify: `curl -sI`, or a header scanner.
- [ ] **Cookies and sessions.** Session cookies are `HttpOnly; Secure; SameSite=Lax` (or `Strict`). CSRF protection on state-changing requests. Sessions expire and are revoked on logout or password change. **P0 · App.**
- [ ] **Authentication.**
  - Rate limiting and lockout or backoff on login, OTP and password reset.
  - MFA available; passkeys where feasible.
  - No account enumeration through error messages.
  - Password managers and paste work.

  **P0 · App.**
- [ ] **Authorization** checked on the server for every object and route (Broken Access Control is OWASP A01:2025). **P0 · App.**
- [ ] **Errors and logs.** No stack traces or internal details in responses (OWASP A10:2025, Mishandling of Exceptional Conditions). Security events are logged and alerted. **P0 · App.**
- [ ] **Supply chain.**
  - Dependency and secret scanning in CI.
  - Lockfiles committed.
  - SRI on third-party scripts loaded from CDNs.
  - Third-party scripts kept to a minimum (OWASP A03:2025, Software Supply Chain Failures).

  **P1 · Both.**
- [ ] **`/.well-known/security.txt`** (RFC 9116) with a `Contact` and `Expires` field. **P2 · Both.**
- [ ] **OWASP Top 10:2025 review**, or a pentest for apps handling personal or payment data, before launch. **P1 · App.**

## 15. Privacy and consent
- [ ] **Consent before non-essential cookies and tags** (analytics, ads, pixels) where GDPR/ePrivacy or similar laws apply.
  - Use a consent management platform (CMP).
  - "Reject" carries the same weight as "Accept".
  - No pre-checked boxes.
  - Consent can be withdrawn as easily as it was given.
  - Choices are logged.

  **P0 · Both** for EU/UK traffic. Verify: in a fresh profile, no tracking requests fire before a choice (DevTools Network).
- [ ] **Google Consent Mode v2** when using Google tags with EEA/UK traffic: `ad_storage`, `analytics_storage`, `ad_user_data` and `ad_personalization`, wired to the CMP. Choose basic or advanced mode with legal. **P0 if applicable · Both.**
- [ ] **US state laws.** Honour Global Privacy Control (GPC) as an opt-out where required (e.g. California). Provide "Do not sell or share" where applicable. **P1 if applicable · Both.**
- [ ] **India DPDP Act 2023 / DPDP Rules 2025** (notified November 2025). *(changes often)*
  - Standalone, plain-language notices that itemise the data and its purpose.
  - Consent that can be withdrawn.
  - Breach reporting duties.

  Most of these obligations apply from about May 2027; consent-manager rules from about November 2026. Build to them now. **P1 · Both.**
- [ ] **Privacy policy and cookie policy** that match the code: every SDK, analytics tool and processor is listed. **P0 · Both.**
- [ ] **Data subject rights.** Account deletion and data export paths for apps. A contact route for requests. A data retention schedule. **P0 · App.**
- [ ] **No third-party requests that leak personal data** without consent: self-hosted fonts, no embedded trackers on logged-in pages. **P1 · Both.**

## 16. Analytics, monitoring and operations
- [ ] **Analytics.**
  - Defined conversion events (signup, trial, purchase, lead).
  - Internal traffic filtered.
  - GSC linked to the analytics property.
  - UTM conventions documented.

  **P1 · Both.**
- [ ] **Error tracking** (e.g. Sentry) on frontend and backend, with source maps uploaded privately. **P0 · App, P1 · Site.**
- [ ] **Uptime and certificate-expiry monitoring** with alerts to a person. A status page for apps. **P0 · App, P1 · Site.**
- [ ] **Branded 404 and 500 pages** that return the correct status and offer search or navigation. **P1 · Both.**
- [ ] **Backups and restore tested.** A rollback plan for deploys. Rate limits on public APIs and forms. Bot protection on forms (CAPTCHA only as a fallback, and accessible). **P0 · App.**
- [ ] **Transactional email** has SPF, DKIM and DMARC configured, and links use the canonical host. **P1 · Both.**

## 17. Webapp and product specifics
- [ ] **Separate the public marketing surface from the app.**
  - Public pages (home, pricing, features, docs, blog, changelog, help) are server-rendered and indexable.
  - Authenticated routes redirect to login, or return 401/403, and send `X-Robots-Tag: noindex`. Never serve a 200 empty shell for every route.

  **P0 · App.** Verify: request an app URL logged out; check the status and `X-Robots-Tag`.
- [ ] **No app URLs in the sitemap.** Login, signup and reset pages are indexable only if they are useful landing pages; otherwise noindex them. **P1 · App.**
- [ ] **Shareable public objects** (public profiles, shared docs, reports) get a server-rendered page, a canonical and an OG image, or `noindex` if private by default. **P1 · App.**
- [ ] **Web app manifest** (`site.webmanifest`):
  - `name`, `short_name`, `start_url`, `scope`, `display`.
  - `theme_color` and `background_color`.
  - Icons at 192 and 512 px, plus a 512 px maskable icon.
  - Linked from every page, alongside `<meta name="theme-color">`.

  **P1 · App.** Icon specs: [icon-specs.md](../../app-icons/references/icon-specs.md).
- [ ] **Service worker**, if used:
  - Scoped correctly.
  - Never caches authenticated API responses across users.
  - Versioned, with an update flow.
  - Has an offline fallback page.

  **P1 · App.**
- [ ] **Permission prompts** (notifications, location, camera) only appear in context after a user action. Never ask on page load. **P1 · App.**
- [ ] **Deep links and app links.** Deep links work after login. iOS/Android association files are served if native apps exist (`apple-app-site-association`, `assetlinks.json`). **P2 · App.**
- [ ] **Product hygiene:** a public changelog, help center and status page, so prospects and AI answers find accurate product facts. **P2 · App.**

## 18. Launch gates and ongoing roadmap
**T-14 days**
- Run the whole checklist on staging.
- Every P0 is PASS or has a signed-off exception.
- Build the redirect map for any migration.
- Draft the GSC and Bing verification.

**T-0 (launch)**
- Remove staging `noindex` and auth from production only.
- Re-run `check-url.sh` on the home page and one URL per template.
- Confirm robots.txt and the sitemap on production.
- Submit the sitemap (with approval).
- Smoke-test consent, analytics events, error tracking and uptime alerts.

**T+7 days**
- GSC: Page indexing report, crawl stats, Sitemaps status.
- 404s and redirect errors from logs.
- First RUM data.

**T+30 days**
- CrUX/PSI field CWV.
- Indexed-page count vs sitemap count.
- Top queries and pages in GSC.
- Close the P1s.

**Monthly**
- GSC Page indexing and CWV reports.
- Broken internal links.
- New 404s.
- Uptime and error trends.
- Dependency alerts.

**Quarterly**
- Re-check the *(changes often)* items against Google's Search Central "Latest updates" page: rich-result eligibility, crawler tokens, AI-bot list.
- Content refresh of the top pages.
- Security header and CSP review.
- Privacy policy vs actual SDKs.

**Yearly**
- Full WCAG audit and updated accessibility statement.
- Pentest for apps.
- Redirect map clean-up (keep migration redirects at least a year).
- Legal review of privacy and consent against current law.

## Sources
- https://developers.google.com/search/updates (FAQ removal, non-200 rendering, JS canonical/noindex guidance, robots meta outside head, llms.txt clarification, review-snippet guideline)
- https://developers.google.com/search/docs/appearance/ai-features
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/search/docs/crawling-indexing/robots/intro
- https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- https://developers.google.com/search/docs/appearance/structured-data/paywalled-content
- https://web.dev/articles/vitals
- https://www.w3.org/TR/WCAG22/
- https://eur-lex.europa.eu/eli/dir/2019/882/oj (European Accessibility Act) and ETSI EN 301 549
- https://owasp.org/Top10/2025/
- https://www.rfc-editor.org/rfc/rfc9116
- https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest
- https://developers.google.com/tag-platform/security/guides/consent
- https://globalprivacycontrol.org/
- https://www.meity.gov.in/ (Digital Personal Data Protection Rules, 2025)
