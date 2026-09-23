# XML Sitemaps

A sitemap lists the canonical URLs you want indexed and when they last meaningfully changed. It aids discovery (especially for new, large, deep, or poorly linked sites) but does not guarantee indexing and does not replace internal links.

## Rules

- **Limits**: 50,000 URLs **or** 50 MB uncompressed per file (gzip allowed for transfer). Beyond that, split and use a sitemap index (an index can list up to 50,000 sitemaps).
- **UTF-8**, entity-escaped (`&amp;` in URLs), fully qualified **absolute URLs** on the same host (unless cross-submitted via Search Console).
- **Canonical URLs only**: 200 status, indexable, self-canonical. Exclude redirects, 404/410, `noindex`, parameter/facet duplicates, paginated deep pages (optional), and URLs blocked by robots.txt.
- **`<lastmod>`**: W3C datetime (`2026-09-23` or `2026-09-23T08:15:00+00:00`). Google uses it only when it is consistently and verifiably accurate — set it when content, structured data, or important links change significantly; not on every build, not for footer/copyright changes. Identical `lastmod` on every URL teaches Google to ignore it.
- **`<priority>` and `<changefreq>` are ignored by Google** — omit them.
- Scope: a sitemap at the root can cover the whole host; one in `/blog/` only covers `/blog/` unless submitted through Search Console.
- Formats: XML (preferred; supports image/video/news/hreflang extensions), RSS/Atom (fine for recent updates from a CMS), plain text (URLs only).

## Submission and discovery

- `Sitemap: https://example.com/sitemap.xml` line in robots.txt (any position, repeatable).
- Search Console Sitemaps report (and API) — shows fetch status, discovered URLs, and errors. **Submitting is an external action — requires user approval** (SKILL.md rule 1); adding the robots.txt line in code is a normal repo change.
- The old Google "ping" endpoint was deprecated in 2023 and now does nothing — remove ping calls rather than adding them.
- For Bing and other IndexNow engines, see IndexNow in technical.md.

## Structure for larger sites

```
/sitemap.xml                → sitemap index
/sitemaps/pages.xml         → static/marketing pages
/sitemaps/blog-2026.xml     → posts by year (keeps files stable)
/sitemaps/products-1.xml    → products, chunked at ≤50k
/sitemaps/categories.xml
/sitemaps/locations.xml
```

Split by type/template so Search Console coverage per sitemap shows which templates have indexing problems.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemaps/pages.xml</loc>
    <lastmod>2026-09-20</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemaps/blog-2026.xml</loc>
    <lastmod>2026-09-22</lastmod>
  </sitemap>
</sitemapindex>
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://example.com/guides/canonical-tags</loc>
    <lastmod>2026-09-18</lastmod>
    <image:image><image:loc>https://cdn.example.com/og/canonical-tags.png</image:loc></image:image>
  </url>
</urlset>
```

Hreflang in sitemaps: see international-hreflang.md. News sitemaps (`news:` namespace) only for recent articles (last ~2 days) on news publishers.

## Generating in code

- Build from the same source of truth as routing (CMS, DB, route manifest) — never hand-maintained lists.
- Filter by the same rules that decide indexability (published, not noindex, canonical == self).
- `lastmod` from the content's real `updatedAt` (content changes only).
- Next.js App Router: `app/sitemap.ts` (and `generateSitemaps` for chunking) + `app/robots.ts`. Nuxt: `@nuxtjs/sitemap`. Astro: `@astrojs/sitemap`. SvelteKit/Remix: a server route returning `application/xml`. Static sites: build-step generator.
- Serve with `Content-Type: application/xml` (or `text/xml`), 200, cacheable; regenerate on publish or on a schedule.
- Add a test: sitemap parses, every URL is absolute, unique, same host, and (in an integration test or crawl) returns 200 with self-canonical.

## Audit checks

| Issue | Severity | Fix |
|---|---|---|
| No sitemap on a large/new site | Medium | Generate from routing/CMS |
| Sitemap URLs return 3xx/4xx/5xx | High | Regenerate from canonical source; fix filters |
| `noindex` or non-canonical URLs listed | High | Align filters with indexability rules |
| >50k URLs or >50 MB in one file | High | Split + index |
| Important templates missing from sitemap | Medium | Add |
| All `lastmod` identical / build time | Low–Medium | Use real content update times |
| `priority`/`changefreq` present | Info | Remove (ignored) |
| Not referenced in robots.txt or Search Console | Low | Add `Sitemap:` line |
| HTTP URLs on an HTTPS site; wrong host | High | Fix base URL config |
| Sitemap blocked by robots.txt or returns HTML | High | Serve XML with 200 |

Compare sitemap URLs vs crawled URLs vs Search Console indexed pages: listed-but-not-linked = orphan pages; linked-but-not-listed = coverage gap; listed-but-not-indexed = quality or duplication issue.

## Sources
- https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping
- https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt
- https://developers.google.com/search/docs/appearance/google-images
- claude-seo v1.9.9 `seo-sitemap` skill (AgriciDaniel, MIT) — common-issues table
