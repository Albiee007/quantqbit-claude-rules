# Core Web Vitals

Core Web Vitals are part of Google's page experience signals. They rarely beat relevance, but they break ties between comparable pages and affect conversions directly. Treat the thresholds as **build budgets**.

## Metrics and thresholds

Assessed at the **75th percentile** of real page loads, segmented by mobile and desktop. A URL/origin passes when all three are "good".

| Metric | Measures | Good | Needs improvement | Poor |
|---|---|---|---|---|
| **LCP** Largest Contentful Paint | Loading: render time of the largest image/text block in the viewport | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s |
| **INP** Interaction to Next Paint | Responsiveness: latency of (nearly) the worst click/tap/key interaction in the visit | ≤ 200 ms | 200–500 ms | > 500 ms |
| **CLS** Cumulative Layout Shift | Visual stability: largest burst of unexpected layout shifts | ≤ 0.1 | 0.1–0.25 | > 0.25 |

INP replaced FID as a Core Web Vital in March 2024; FID is retired. Never report FID. Supporting diagnostics (not Core Web Vitals): TTFB (aim < 0.8 s), FCP (< 1.8 s), Total Blocking Time (lab proxy for INP).

## Measuring

| Source | Type | Use |
|---|---|---|
| CrUX (Chrome UX Report) — API, BigQuery, CrUX Vis | Field, 28-day rolling | What Google uses. Needs enough traffic; otherwise origin-level only or none. |
| PageSpeed Insights | Field (CrUX) + lab (Lighthouse) | Quick per-URL check; field section is the verdict, lab section the diagnosis. |
| Search Console → Core Web Vitals report | Field, grouped by similar URLs | Template-level status and trends. |
| `web-vitals` JS library | Your own RUM | Attribute builds report the LCP element, INP interaction target, and shift sources. Send to analytics. |
| Lighthouse / Chrome DevTools Performance panel | Lab | Reproduce and debug. Lab has no real INP; use TBT and DevTools interaction traces. |
| WebPageTest | Lab | Filmstrips, waterfalls, connection throttling. |

Rules: field data decides pass/fail; lab data explains why. Test mobile with throttling. Low-traffic pages without CrUX data: rely on RUM or lab and say so in the report.

```js
import { onLCP, onINP, onCLS } from 'web-vitals/attribution';
const send = (m) => navigator.sendBeacon('/rum', JSON.stringify({ name: m.name, value: m.value, rating: m.rating, id: m.id, attribution: m.attribution }));
onLCP(send); onINP(send); onCLS(send);
```

## LCP: diagnosis by subpart

LCP = **TTFB + resource load delay + resource load duration + element render delay**. Healthy split: ~40% TTFB, <10% load delay, ~40% load duration, <10% render delay.

| Subpart too large | Typical causes | Fixes |
|---|---|---|
| TTFB | Slow backend/DB, no caching, redirects, cold serverless starts, far origin | CDN/edge caching of HTML (SSG/ISR), cache headers, avoid redirect hops, keep URLs cache-friendly (no unique query params), stream HTML |
| Resource load delay | LCP image discovered late: CSS background, JS-inserted, `loading="lazy"`, `data-src` lazy loader, client-rendered | Put the LCP `<img>` in server HTML, `fetchpriority="high"`, never lazy-load it, `<link rel="preload">` if not in HTML (e.g. CSS background), same-origin or `preconnect` |
| Resource load duration | Oversized image, legacy format, no responsive sizes | AVIF/WebP, correct `srcset`/`sizes`, compress, CDN image resizing |
| Element render delay | Render-blocking CSS/JS, web fonts hiding text, hydration before paint, A/B test scripts hiding the page | Inline critical CSS, `defer`/`async` scripts, `font-display: swap` or `optional` + preload key fonts, SSR the LCP element, remove anti-flicker snippets |

## INP: diagnosis by phase

INP = **input delay + processing duration + presentation delay**.

| Phase | Causes | Fixes |
|---|---|---|
| Input delay | Main thread busy with long tasks (script evaluation, hydration, third parties, timers) | Break up long tasks (>50 ms); yield with `scheduler.yield()` (fallback `setTimeout(…, 0)`); defer non-critical JS; code-split; lazy hydrate/islands |
| Processing duration | Heavy event handlers, synchronous state updates re-rendering large trees, sync storage/XHR | Do the minimum before next paint, defer the rest; memoise; `startTransition`/`useDeferredValue` in React; debounce input handlers; move work to Web Workers |
| Presentation delay | Large DOM, layout thrashing (read-after-write), expensive style recalcs | Keep DOM small; batch reads then writes; `content-visibility: auto` for off-screen sections; virtualise long lists; avoid animating layout properties |

Third-party scripts (tag managers, chat widgets, A/B tools, ad scripts) are the most common INP and LCP drag: audit them, load after interaction or idle, use facades for embeds (YouTube, chat), and set a third-party budget.

## CLS: causes and fixes

| Cause | Fix |
|---|---|
| Images/video/iframes without dimensions | `width`/`height` attributes or CSS `aspect-ratio` on every media element |
| Ads, embeds, cookie banners injected above content | Reserve space with `min-height`; overlay banners (fixed position) instead of pushing content |
| Web fonts swapping with different metrics | `size-adjust`/`ascent-override` fallback font metrics (e.g. `next/font`, Fontaine), preload critical fonts |
| Content inserted after load (recommendations, "you may also like", async price) | Placeholders/skeletons with final size; insert below the viewport; never above existing content unless in response to input |
| Animations using `top`/`left`/`width` | Use `transform`/`opacity` |
| bfcache-ineligible pages re-rendering on back | Avoid `unload` handlers, `Cache-Control: no-store` on public pages |

Shifts within 500 ms of a user input don't count.

## Framework notes

- **Next.js**: `next/image` with `priority` (or `fetchPriority="high"`) on the LCP image and `sizes` set; `next/font` for zero-CLS fonts; keep pages as server components, push `"use client"` down to leaves; `next/script` with `strategy="lazyOnload"` or `"afterInteractive"` for third parties; `dynamic()` for heavy client widgets; static/ISR for public pages.
- **Nuxt**: `<NuxtImg preload>` for hero, `@nuxt/fonts`, lazy components (`<LazyFoo>`), `nuxt-scripts` for third parties, route rules for prerender/SWR.
- **Astro**: islands by default; use `client:visible`/`client:idle` rather than `client:load`; `<Image>` component with `loading="eager"` + `fetchpriority="high"` for the hero.
- **SvelteKit / Remix**: SSR by default; watch bundle size and preload link behaviour; stream data.
- **Angular**: SSR + hydration (incremental/deferrable views with `@defer`), `NgOptimizedImage` with `priority`.
- **WordPress**: limit plugins, page-cache + CDN, disable lazy-load on the hero image, remove unused block CSS, host fonts locally.
- **SPAs**: CWV for soft navigations are not yet part of Google's assessment; still measure route-change responsiveness with RUM.

## Performance budget (per template, mobile)

| Budget | Target |
|---|---|
| LCP (p75 field) | ≤ 2.5 s |
| INP (p75 field) | ≤ 200 ms |
| CLS (p75 field) | ≤ 0.1 |
| TTFB | ≤ 0.8 s |
| JS shipped (compressed) on content pages | ≤ ~170 KB first-party as a starting point; justify more |
| LCP image | ≤ ~200 KB, modern format |
| Third-party requests before interaction | Minimise; none render-blocking |

Enforce with Lighthouse CI or bundle-size checks in CI; alert on RUM regressions.

## Audit scoring (CWV category)

Field data available: 100 if all three good on mobile and desktop; subtract ~25 per metric "needs improvement", ~40 per metric "poor" (mobile weighted higher). No field data: score lab data + source inspection conservatively and flag the gap.

## Sources
- https://web.dev/articles/vitals
- https://web.dev/articles/optimize-lcp
- https://web.dev/articles/optimize-inp
- https://web.dev/articles/optimize-cls
- https://developers.google.com/search/docs/appearance/core-web-vitals
- claude-seo v1.9.9 `cwv-thresholds.md`, `seo-performance` agent (AgriciDaniel, MIT)
