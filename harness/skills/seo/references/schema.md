# Structured Data (Schema.org / JSON-LD)

Structured data helps search engines and other machine readers understand entities on a page and makes pages **eligible** (never guaranteed) for rich results. It is not a general ranking boost. Templates: [schema-templates.json](schema-templates.json).

## Rules

1. **Format: JSON-LD** in `<script type="application/ld+json">` (Google recommends it; Microdata/RDFa also accepted). One or more blocks per page; use `@graph` to connect entities.
2. **Server-render it.** Put JSON-LD in the initial HTML. JS-injected markup is processed after rendering and may be delayed — unacceptable for Product/Offer data that changes often.
3. **Mark up only what is visible** on the page and true. Prices, ratings, availability, dates, and FAQs in markup must match what users see. No hidden or misleading markup — violations can earn a manual action that removes rich result eligibility.
4. **Relevance and specificity.** Use the most specific type that fits (`Restaurant` not `LocalBusiness`, `BlogPosting` or `NewsArticle` where apt). Don't label a page as something it isn't.
5. **Completeness.** Include every *required* property for the feature you target; add *recommended* ones where you have the data.
6. **Place markup on the page it describes.** Site-wide entities (Organization, WebSite) belong on the home page (Organization may also be on About/contact); don't stamp Product markup on category pages for every product unless using a supported list pattern.
7. **Absolute URLs**, ISO 8601 dates (`2026-09-23` or `2026-09-23T10:00:00+05:30`), ISO 4217 currency codes, `https://schema.org` context.
8. **Stable `@id`s** (e.g. `https://example.com/#organization`) so entities are referenced, not duplicated, across pages.
9. **Reviews/ratings**: only genuine reviews from real customers, shown on the page. No self-serving LocalBusiness/Organization review stars on your own site (not eligible). Never fabricate `aggregateRating`.
10. **No placeholders in production.** The `{{…}}` tokens in the templates must all be replaced or the property removed.

## Rich result eligibility status (verified Sept 2026)

Currently listed in Google's search gallery: Article, Breadcrumb, Carousel (with Recipe/Course/Restaurant/Movie), Course list, Dataset (Dataset Search only, not Google Search), Discussion forum, Education Q&A, Employer aggregate rating, Event, Image metadata, Job posting, Local business, Math solver, Movie, Organization, Product (product snippets, merchant listings, variants, shipping/return policies, loyalty programs), Profile page, Q&A, Recipe, Review snippet, Software app, Speakable, Subscription/paywalled content, Vacation rental, Video.

| Type / feature | Status | Guidance |
|---|---|---|
| **FAQPage** | Google FAQ rich results **discontinued** (deprecation notice May 2026; feature no longer shown and docs removed June 2026). Previously limited to authoritative government/health sites since Aug 2023. | Don't add FAQPage expecting a Google result. Existing valid markup that mirrors a visible FAQ is harmless and can still be read by other engines/parsers — flag as Info, not an error. Keep visible Q&A content; it is useful to users and answer engines. |
| **HowTo** | Rich result removed (Sept 2023). | Don't recommend. Write clear numbered steps in HTML. |
| Sitelinks search box (`WebSite.potentialAction` SearchAction) | Removed Nov 2024. | Not needed; harmless if present. |
| Course info, Estimated salary, Learning video, Special announcement, Vehicle listing | Docs removed Sept 2025 (banners from June 2025). | Don't recommend for Google. Use VideoObject for videos. |
| ClaimReview (fact check), Book actions, Practice problem | Not listed in the current gallery (phase-out banners 2025). | Don't recommend for Google rich results; check the gallery before any new work. |
| Dataset | Only used by Dataset Search. | Use only for genuine datasets. |

Recheck https://developers.google.com/search/docs/appearance/structured-data/search-gallery and the Search Central changelog before promising any rich result — the list changes several times a year.

## What to use by page type

| Page | Types |
|---|---|
| Home | `Organization` (logo, `sameAs`, contact) + `WebSite` (`name`, `alternateName` for site name) |
| Any inner page | `BreadcrumbList`; `WebPage` optional |
| Article / blog / news | `Article` / `BlogPosting` / `NewsArticle` with `author` (Person with `url`), `datePublished`, `dateModified`, `image` |
| Author page | `ProfilePage` with `mainEntity` Person |
| Product (buyable) | `Product` + `Offer` (price, currency, availability) + shipping/return policy; `aggregateRating`/`review` only if real |
| Product variants | `ProductGroup` with `hasVariant`, `variesBy`, `productGroupID` |
| Software / SaaS | `SoftwareApplication` (or `WebApplication`) with `offers`, `applicationCategory`, `operatingSystem` |
| Local business | Most specific `LocalBusiness` subtype, one per location page, unique `@id` |
| Event | `Event` with `startDate` (with timezone), `location` (Place with `address`), `eventStatus`, `offers` |
| Video page | `VideoObject` (`name`, `thumbnailUrl`, `uploadDate`, `contentUrl`/`embedUrl`, `duration`); `Clip`/`SeekToAction` for key moments |
| Job | `JobPosting` (remove or set `validThrough` when filled) |
| Forum / community | `DiscussionForumPosting` / `QAPage` |
| Recipe | `Recipe` |

## Required properties (common Google features)

| Feature | Required | Key recommended |
|---|---|---|
| Article | none strictly required | `headline`, `image`, `datePublished`, `dateModified`, `author.name` + `author.url` |
| Breadcrumb | `itemListElement` with `position`, `name`, `item` (item optional on last) | — |
| Product snippet | `name` + one of `review`, `aggregateRating`, `offers` | `image`, `brand`, `gtin`/`sku` |
| Merchant listing | `name`, `image`, `offers.price`, `offers.priceCurrency` | `availability`, `shippingDetails`, `hasMerchantReturnPolicy`, `gtin`, `brand` |
| Organization | none | `name`, `url`, `logo`, `sameAs`, `address`, `contactPoint` |
| Local business | `name`, `address` | `geo`, `telephone`, `openingHoursSpecification`, `url`, `priceRange` (<100 chars), `menu`, `servesCuisine`; `review`/`aggregateRating` only for sites that review *other* businesses |
| Event | `name`, `startDate`, `location` (Place) with `location.address` | `description`, `endDate`, `eventStatus`, `image` (≥720 px wide), `offers`, `organizer`, `performer`, `previousStartDate` |
| Software app | `name`, `offers.price` (0 if free; `priceCurrency` when >0), and `aggregateRating` or `review` | `applicationCategory`, `operatingSystem`; `WebApplication`/`MobileApplication` subtypes supported |
| Video | `name`, `thumbnailUrl`, `uploadDate` | `description`, `contentUrl`, `embedUrl`, `duration` |
| Profile page | `mainEntity` (Person or Organization) with `name` | `sameAs`, `image`, `description` |

Always confirm against the feature's current doc page; requirements evolve.

## Validation workflow

1. Parse check: JSON must parse (`python -c "import json,sys; json.load(sys.stdin)"` on the extracted block, or `JSON.parse` in a unit test).
2. **Rich Results Test** (https://search.google.com/test/rich-results) — Google eligibility, required/recommended property errors; test live URL and code snippet.
3. **Schema Markup Validator** (https://validator.schema.org/) — generic schema.org conformance (types not supported by Google still validate here).
4. Search Console **enhancement reports** after deployment for site-wide errors.
5. In code: snapshot or unit-test the generated JSON-LD per template (valid JSON, no `{{`, absolute URLs, dates ISO 8601).

## Common errors

| Error | Fix |
|---|---|
| Invalid JSON (trailing commas, unescaped quotes from CMS text) | Serialise with `JSON.stringify`/`json.dumps`; never string-concatenate; escape `</script>` as `<\/script>` |
| `http://schema.org` or missing `@context` | `"@context": "https://schema.org"` |
| Relative URLs | Absolute URLs |
| Price with currency symbol (`"$19"`) | `"price": "19.00"`, `"priceCurrency": "USD"` |
| Availability as free text | `https://schema.org/InStock` etc. |
| Markup not visible on page / mismatched values | Render from the same data source as the UI |
| Fake or self-serving review stars | Remove |
| Duplicate conflicting Organization blocks from plugins + theme | One source of truth with `@id` |
| Deprecated types recommended (HowTo, SpecialAnnouncement) | Remove from recommendations |
| Dates without timezone for events | Include offset |

## Framework patterns

- React/Next.js: `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, '\\u003c') }} />` in a server component.
- Nuxt: `useHead({ script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(data) }] })`.
- Astro: `<script type="application/ld+json" set:html={JSON.stringify(data)} />`.
- Build JSON-LD from the same typed object that renders the page, so markup and content cannot drift.

## Sources
- https://developers.google.com/search/docs/appearance/structured-data/search-gallery
- https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- https://developers.google.com/search/docs/appearance/structured-data/faqpage
- https://developers.google.com/search/docs/appearance/structured-data/product
- https://developers.google.com/search/docs/appearance/structured-data/software-app
- https://developers.google.com/search/docs/appearance/structured-data/event
- https://developers.google.com/search/docs/appearance/structured-data/local-business
- https://developers.google.com/search/docs/appearance/site-names
- https://developers.google.com/search/updates
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- claude-seo v1.9.9 `seo-schema`, `schema-types.md`, `schema/templates.json` (AgriciDaniel, MIT)
