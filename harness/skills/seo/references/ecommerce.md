# E-commerce SEO

Product, category, and brand pages are templates multiplied by thousands. Get the template right and the catalogue follows; get it wrong and you create index bloat and thin pages at scale.

## Site structure

- Hierarchy: Home → Category → Subcategory → Product, each reachable via crawlable `<a href>` navigation and breadcrumbs (with BreadcrumbList schema).
- One canonical URL per product regardless of the category path used to reach it (`/p/black-chelsea-boot`, not `/men/boots/black-chelsea-boot` and `/sale/black-chelsea-boot` both indexable).
- Readable URLs; avoid session IDs and tracking params in internal links.
- Keep important categories shallow; link high-value products from categories and related-product modules.

## Product pages

- **Unique content**: write your own description (use cases, materials, sizing, care, comparisons). Manufacturer copy duplicated across retailers adds nothing; thin affiliate pages violate spam policy.
- **Title**: `{Product name} – {key attribute} | {Brand}`; H1 = product name.
- **Specs table** (HTML table), price, availability, shipping and returns info visible on the page.
- **Images**: multiple high-quality images (≥800 px, ideally ≥1200 px) with descriptive alt text and filenames; zoomable; primary image in `og:image` and structured data. AI-generated product images must carry IPTC `DigitalSourceType` `TrainedAlgorithmicMedia`.
- **Reviews**: genuine, on-page, with pros/cons where possible; never fabricated or gated.
- **Structured data**: `Product` + `Offer` (price, `priceCurrency`, `availability`, `url`), `shippingDetails`, `hasMerchantReturnPolicy`, identifiers (`gtin`, `mpn`, `sku`), `brand`; `aggregateRating`/`review` only when real and visible. Server-render it — JS-injected Product markup is processed late and prices go stale.
- **Variants** (size/colour): either one URL per variant (with `ProductGroup` + `hasVariant` + `variesBy` and a shared `productGroupID`) or one URL with selectable options. Variant URLs usually self-canonical if they have distinct demand (colour); size-only variants often canonical to the main product. Be consistent.
- Merchant return policy and loyalty program can also be defined once at `Organization` level (and in Search Console/Merchant Center).

## Product snippets vs merchant listings

| Experience | For | Required |
|---|---|---|
| Product snippet (stars, price in web results) | Pages about a product, incl. editorial reviews | `name` + one of `review`, `aggregateRating`, `offers` |
| Merchant listing (Shopping tab, product knowledge panel, popular products) | Pages where the product can be bought | `name`, `image`, `offers.price`, `offers.priceCurrency` |

Merchant Center feeds complement (not replace) on-page markup; keep price/availability consistent between feed, markup, and page, or listings get disapproved. Submitting feeds or changing Merchant Center settings is an external action — approval required.

## Availability lifecycle

| Situation | Do |
|---|---|
| Temporarily out of stock | Keep the page live (200), show status and restock/notify option, `availability: OutOfStock` (or `BackOrder`/`PreOrder`). Don't `noindex` or 404 it. |
| Seasonal / recurring product | Keep the URL year-round; update availability and content. |
| Permanently discontinued with a direct successor | 301 to the successor (or closely equivalent product). |
| Permanently discontinued, no equivalent | 404/410, or keep an informational page if it still gets traffic/links (specs, "replaced by", support) — don't redirect everything to home or a generic category (soft 404). |
| Empty category | `noindex` while temporarily empty; 404 if removed from navigation for good. |

## Category pages

Often the highest-value commercial pages.
- Unique H1 and title matching the category's search intent; short, useful intro copy (buying guidance, key distinctions) above or below the grid — not keyword-stuffed filler.
- Paginated with unique, self-canonical URLs and `<a href>` next/previous links (see technical.md). Don't canonicalise page 2+ to page 1.
- Product grid links must be real anchors to canonical product URLs.
- ItemList/Carousel markup is not needed for most retail categories; Product markup belongs on product pages.

## Faceted navigation

Facets (colour, size, price, brand, sort) generate combinatorial URLs. Strategy:
1. Decide which facet pages have real search demand (e.g. "men's black boots", "nike running shoes"). Give those clean, static, indexable URLs with unique titles/H1/intro, self-canonicals, internal links, and sitemap entries.
2. Everything else: prevent crawling — robots.txt `Disallow` for facet parameters or fragment-based filters (`#size=10`); secondary signals: `rel="canonical"` to the unfiltered category, `rel="nofollow"` on facet links.
3. Sorting, view modes, and price sliders: never indexable.
4. Consistent parameter order and `&` separators; zero-result combinations return 404.
5. Multi-select facets (two brands at once) are almost never worth indexing.

## Internal search

Internal search result pages: `noindex`, disallow crawling of the search path, and don't link to them from crawlable navigation. Use search logs to discover demand for new category/facet landing pages.

## Performance

Product and category templates carry heavy JS (recommendation widgets, reviews, personalisation, tag managers). Budget them (core-web-vitals.md): server-render price and primary image, lazy-load reviews and recommendations below the fold with reserved space, defer third-party scripts.

## International and marketplaces

- Multiple currencies/regions: separate URLs per locale with hreflang (international-hreflang.md); prices in markup must match the locale shown.
- Marketplace listings (Amazon etc.) are separate channels; avoid publishing identical descriptions everywhere if you want your own site to rank.

## E-commerce audit checklist

| Check | Severity |
|---|---|
| Product pages client-rendered only / markup injected by JS | High |
| Product markup price/availability mismatches page | High |
| Faceted URLs crawlable at scale | High |
| Out-of-stock pages 404/noindexed | High |
| Duplicate product URLs across category paths without canonical | High |
| Manufacturer-copy descriptions site-wide | Medium |
| Missing shipping/return policy markup | Medium |
| Category pages without unique intro/title | Medium |
| Missing GTIN/brand | Low–Medium |
| Pagination canonicalised to page 1 | Medium |

Scoring (adapted from claude-seo's e-commerce weights): schema completeness 25, content quality 20, images 20, title/meta 15, internal linking 10, technical 10.

## Sources
- https://developers.google.com/search/docs/appearance/structured-data/product
- https://developers.google.com/search/docs/specialty/ecommerce
- https://developers.google.com/search/docs/specialty/ecommerce/pagination-and-incremental-page-loading
- https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation
- https://developers.google.com/search/docs/crawling-indexing/pause-online-business
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/essentials/spam-policies
- claude-seo v1.9.9 `seo-ecommerce` skill (AgriciDaniel; original author Matej Marjanovic, MIT)
