# On-Page SEO

On-page elements tell users and search engines what a page is about and why to click it. None of them rescue weak content, but mistakes on templates repeat across thousands of pages.

## Title element

- Unique per page; describes this page specifically. Avoid "Home", "Untitled", or one title across a template.
- Lead with the primary topic; brand at the end with a delimiter: `Canonical Tags Explained: A Developer Guide | Acme`.
- Length: Google truncates by pixel width (device-dependent), not characters. ~50–60 characters is a practical target; longer is allowed but the tail may be cut.
- No keyword stuffing or repeated boilerplate prefixes.
- Google may rewrite title links using the H1, `og:title`, prominent text, or anchor text — a clear H1 that agrees with the title reduces rewrites.
- Pagination/facets: include the differentiator ("Page 2", "Red") so titles are not duplicated.

## Meta description

- Unique, accurate summary of the page; write to earn the click (what the user gets, key specifics like price, date, author).
- No length limit; snippets truncate as needed. ~120–160 characters is a display guide.
- Google often generates snippets from page content matching the query; a good description is still used when it describes the page better.
- Don't stuff keywords; don't reuse one description site-wide. If you cannot write unique ones at scale, omitting is better than duplicating (Google will generate).

## Headings

- One `<h1>` per page, matching the title's intent.
- H2 for main sections, H3 for sub-sections; don't skip levels for styling; don't use headings for non-heading text (badges, prices). Google says heading order is not a ranking factor, but a logical outline helps accessibility and helps every parser (including AI systems) understand sections.
- Descriptive, scannable headings; question-form headings work well when the section answers that question.

## Body content signals

- Cover the topic the searcher expects (see content-eeat.md). Put the answer or value early.
- Use the primary term naturally in the title, H1, opening paragraph, and URL; use synonyms and related entities elsewhere. There is no target keyword density and no magic word count — write for readers.
- Don't use `<meta name="keywords">` (ignored by Google).
- Lists, tables, and definitions for structured information.
- Visible dates (published/updated) on time-sensitive content.

## URL slug

Short, readable, hyphenated, lowercase: `/guides/canonical-tags`. Remove stop-word noise only if it stays readable. Never change live slugs without a 301.

## Internal linking

- Every indexable page receives at least one contextual link from a relevant page; hubs link to all children; children link back to the hub and to siblings where genuinely related.
- Descriptive anchor text naming the target topic, readable out of context; vary naturally. Avoid "click here" / "read more" as the whole anchor — change the visible text rather than relying on `aria-label`.
- Link to canonical URLs directly (no redirected or parameterised variants).
- Keep navigation crawlable (`<a href>`), including mega-menus and footers.
- Breadcrumbs with BreadcrumbList schema for hierarchical sites.
- Practical density: a few relevant contextual links per ~1,000 words; prioritise relevance over counts.

## External links

- Cite primary sources for claims (increases trust for readers).
- `rel="sponsored"` for paid/affiliate links, `rel="ugc"` for user-submitted links, `rel="nofollow"` when you don't vouch for a link.
- `target="_blank"` is a UX choice, not an SEO one; add `rel="noopener"` when used.

## Social and sharing tags

```html
<meta property="og:type" content="article">
<meta property="og:title" content="Canonical Tags Explained">
<meta property="og:description" content="How rel=canonical works and when to use it.">
<meta property="og:url" content="https://example.com/guides/canonical-tags">
<meta property="og:image" content="https://example.com/og/canonical-tags.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="Acme">
<meta name="twitter:card" content="summary_large_image">
```

Absolute URLs; image ≥1200×630, <5 MB, representative (not just the logo). Social bots don't run JS — these must be in server HTML. `og:image` can also serve as Google's preferred page image.

## Other head essentials

- `<html lang="en">` (language of the content), `<meta charset="utf-8">`, viewport meta.
- Favicon (`<link rel="icon">` on the home page) — shown next to results; square, larger than 48×48 recommended, stable URL, crawlable by Googlebot and Googlebot-Image.
- Site name: WebSite JSON-LD with `name` (and `alternateName`) on the home page influences the site name shown in results.
- `<meta name="robots">` only when intentional.

## Framework metadata APIs

- **Next.js App Router**: `export const metadata` or `generateMetadata()` per route; set `metadataBase` in the root layout so relative OG/canonical URLs resolve absolutely; `alternates: { canonical, languages }` for canonical + hreflang; `robots` field for directives.
- **Next.js Pages Router**: `next/head` inside each page; avoid duplicate tags from layout + page (use `key`).
- **Nuxt**: `useSeoMeta({ title, description, ogImage })`, `useHead({ link: [{ rel: 'canonical', href }] })`.
- **Astro**: set in a shared `<BaseHead>` component with props; `Astro.url` + `Astro.site` for canonicals.
- **SvelteKit**: `<svelte:head>` in `+page.svelte`, data from `+page.server.ts`.
- **Remix/React Router**: `meta` export; `links` export for canonical.
- **Static HTML**: one include/partial for head tags; lint for duplicates.

Validate: exactly one `<title>`, one description, one canonical per rendered page — layouts plus pages often produce duplicates.

## Single-page review checklist

| Element | Pass criteria |
|---|---|
| Title | Present, unique, topic-first, not truncated mid-meaning |
| Description | Present, unique, accurate |
| H1 | Exactly one, agrees with title |
| Heading tree | Logical, no skipped levels |
| Canonical | Absolute, self (or correct target), 200 |
| Robots | Indexable unless intentional |
| Links | Crawlable `<a href>`, descriptive anchors, no broken links |
| Images | Alt, dimensions, lazy below fold |
| Schema | Matches page type, valid |
| Social | OG + Twitter tags with absolute image |
| lang / viewport | Present |

## Sources
- https://developers.google.com/search/docs/appearance/title-link
- https://developers.google.com/search/docs/appearance/snippet
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- https://developers.google.com/search/docs/appearance/site-names
- https://developers.google.com/search/docs/appearance/favicon-in-search
- claude-seo v1.9.9 `seo-page` skill and `quality-gates.md` (AgriciDaniel, MIT)
