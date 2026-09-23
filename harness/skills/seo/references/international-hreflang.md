# International SEO and hreflang

`hreflang` tells Google which language/regional version of a page to show a given user. It does not consolidate ranking signals (that is canonicalisation), and it cannot fix untranslated or duplicate content.

## Choosing a URL structure

| Structure | Example | Notes |
|---|---|---|
| ccTLD | `example.de` | Strongest country signal; separate domains to build and maintain |
| Subdirectory | `example.com/de/` | Easiest to maintain; shares domain signals. Default choice. |
| Subdomain | `de.example.com` | Workable; more infra overhead |
| URL parameter `?lang=de` | — | Not recommended |

Keep the language in the URL. Do **not** serve different languages at the same URL based on cookies, `Accept-Language`, or IP — most Google crawls originate from US IPs and Google doesn't vary crawl location to detect variants, so Googlebot will usually see only one version. Do not auto-redirect by IP/language; show a dismissible language/region suggestion banner instead and let users switch via links.

## hreflang rules

1. **Codes**: language in ISO 639-1 (`en`, `de`, `ja`, `zh`), optional region in ISO 3166-1 alpha-2 (`en-GB`, `pt-BR`, `es-MX`), optional script in ISO 15924 (`zh-Hant`, `zh-Hans`, `zh-Hant-TW`). Case-insensitive, but conventionally `en-GB`.
   Common errors: `en-UK` (use `en-GB`), `jp` (use `ja`), `es-LA`/`en-EU` (not countries), region alone (`GB`), `eng` (ISO 639-2).
2. **Self-reference + full set**: every version lists itself and every alternate.
3. **Bidirectional**: if A lists B, B must list A — otherwise annotations may be ignored.
4. **Absolute URLs** with protocol; exactly the canonical URL of each version (same trailing slash, host, protocol).
5. **Canonical alignment**: each language version is self-canonical. Never canonicalise `/de/page` to `/en/page` — that tells Google to drop the German page, and hreflang on a non-canonical URL is ignored.
6. **`x-default`**: fallback for users matching no listed locale — typically a language selector or the global/English version. One per set, included in every version's set.
7. Only indexable, 200-status pages in hreflang sets; no redirecting, noindexed, or 404 URLs.
8. Pick **one** method per page (HTML, HTTP header, or sitemap); mixing is allowed but invites contradictions.

## Implementation methods

HTML (in `<head>`, server-rendered):

```html
<link rel="alternate" hreflang="en-US" href="https://example.com/pricing/" />
<link rel="alternate" hreflang="en-GB" href="https://example.com/uk/pricing/" />
<link rel="alternate" hreflang="de" href="https://example.com/de/preise/" />
<link rel="alternate" hreflang="x-default" href="https://example.com/pricing/" />
```

HTTP header (non-HTML such as PDFs):

```
Link: <https://example.com/doc.pdf>; rel="alternate"; hreflang="en", <https://example.com/de/doc.pdf>; rel="alternate"; hreflang="de"
```

XML sitemap (best for many locales or cross-domain setups; each `<url>` repeats the full set):

```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
  <url>
    <loc>https://example.com/pricing/</loc>
    <xhtml:link rel="alternate" hreflang="en-US" href="https://example.com/pricing/"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://example.com/de/preise/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://example.com/pricing/"/>
  </url>
  <url>
    <loc>https://example.com/de/preise/</loc>
    <xhtml:link rel="alternate" hreflang="en-US" href="https://example.com/pricing/"/>
    <xhtml:link rel="alternate" hreflang="de" href="https://example.com/de/preise/"/>
    <xhtml:link rel="alternate" hreflang="x-default" href="https://example.com/pricing/"/>
  </url>
</urlset>
```

Framework helpers: Next.js `alternates.languages` in metadata (plus i18n routing); Nuxt i18n module `useLocaleHead()`; Astro i18n routing with a shared head component. Generate hreflang from one locale→URL map so sets are always complete and reciprocal; unit-test reciprocity.

## Localisation quality

- Translate fully: title, meta description, H1, body, alt text, structured data text, URL slugs where sensible, and UI chrome. Machine translation needs human review; unreviewed auto-translation at scale can be scaled content abuse.
- Localise, not just translate: currency, prices, units, date/number formats, phone formats, addresses, legal pages, payment methods, trust marks, examples, and CTAs appropriate to the market.
- Same-language regional variants (`en-US`/`en-GB`/`en-AU`) may be near-duplicates; that's acceptable with hreflang, but differentiate where it matters (prices, spelling, shipping).
- Google detects page language from visible content, not `lang` attributes or URLs — keep one language per page. Still set `<html lang>` correctly for accessibility and other consumers. Geo meta tags are ignored.
- Content parity: key pages should exist in every locale you target; a missing translation should not hreflang to a different-language page (omit it from the set instead).

## Audit checklist

| Check | Severity if failing |
|---|---|
| Language versions served at distinct URLs (no IP/cookie switching) | Critical |
| Cross-language canonicals (`/de/` → `/en/`) | Critical |
| Missing return links | High |
| Invalid language/region codes | High |
| hreflang URLs that redirect/404/noindex | High |
| Missing self-reference | High |
| Missing `x-default` | Medium |
| hreflang URL ≠ canonical (slash/protocol/host) | Medium |
| Untranslated boilerplate, wrong currency | Medium |
| `<html lang>` mismatch / mixed-language pages | Low / Medium |

Use `scripts/check-url.sh` (hreflang count) per locale for a quick sample; a full check requires crawling each set and verifying reciprocity.

## Sources
- https://developers.google.com/search/docs/specialty/international/localized-versions
- https://developers.google.com/search/docs/specialty/international/managing-multi-regional-sites
- https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- claude-seo v1.9.9 `seo-hreflang` skill (AgriciDaniel, MIT) — validation checklist and common-mistakes table
