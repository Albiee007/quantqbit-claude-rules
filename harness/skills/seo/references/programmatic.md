# Programmatic SEO

Programmatic SEO = generating many pages from structured data through templates (integrations, locations, glossary terms, product specs, comparisons, statistics). It is legitimate when each page gives users something distinct and useful; it becomes **scaled content abuse** ("many pages are generated for the primary purpose of manipulating search rankings and not helping users") or **doorway abuse** when pages differ only by a swapped keyword. The method (templates, AI, humans) doesn't matter — the value does.

## The standalone value test

Before building, every page type must pass:
1. Would this page be worth publishing if it were the only one of its kind?
2. Does each page contain information a user can't get from the sibling pages (unique data, not just a different noun)?
3. Is there real search demand for this pattern (not just keyword permutations)?
4. Can we keep the data accurate and fresh?
If any answer is no, don't generate the page — consolidate into one stronger page, or keep the data on-site but `noindex`.

## Safe vs risky patterns

| Usually safe at scale | Risky / likely abuse |
|---|---|
| Integration pages with real setup steps, screenshots, API details per integration | "{Service} in {City}" pages with the same copy and the city swapped |
| Product/spec pages from a genuine catalogue with unique attributes | "Best {tool} for {industry}" with no industry-specific substance |
| Glossary/definition pages with substantive definitions, examples, related terms | "{Competitor} alternative" pages with no real comparison data |
| Data pages where each record has unique stats, charts, analysis (e.g. per-city cost indexes from real data) | AI-written articles for thousands of keyword variants without review |
| Templates/tools/calculators with a functional asset per page | Pages that are >60% shared boilerplate |
| User-generated profiles with substantial unique content | Hosting third-party programmatic content on your domain for rankings (site reputation abuse) |

## Template design

- **Unique data slots** drive the page: numbers, attributes, lists, media, and text that differ per record. Conditional sections: hide empty sections rather than printing "N/A" filler.
- **Shared copy** limited to navigation, short explanations, and methodology.
- Title, H1, meta description, and alt text generated from the record — varied, accurate, not keyword-stuffed.
- **Supplementary value**: related records, comparisons, calculators, FAQs derived from data, contextual tips.
- JSON-LD per page type from the same record (see schema.md).
- Server-rendered/statically generated; stable URLs from slugs; uniqueness enforced at build time.

## Quality gates (enforce in the build/publish pipeline)

Adapted from claude-seo's programmatic gates:

| Gate | Threshold | Action |
|---|---|---|
| Records lacking enough unique fields | Any | Don't generate a page for that record; aggregate instead |
| Unique content vs siblings | < 40% | Warn; flag as thin |
| Unique content vs siblings | < 30% | Hard stop — don't publish |
| Main-content words | < ~300 | Review for sufficiency (not a Google rule) |
| Pages without human sample review | ≥ 100 | Warn — review a 5–10% sample first |
| New pages in one release | ≥ 500 without explicit sign-off | Hard stop — require user justification |
| Location pages | ≥ 30 warn / ≥ 50 require justification | Must reflect real presence and ≥ majority unique local content |

Uniqueness % = words unique to this page's main content ÷ total main-content words, compared against the other pages in the set (exclude global header/footer/nav; include template body copy).

## Rollout

1. Pilot a batch (e.g. 50–100 pages) of the best records.
2. Monitor for 2–4 weeks: indexing rate (Search Console page indexing), impressions, engagement, "Crawled – currently not indexed" counts.
3. Improve the template based on data; expand in batches only if pilots index and perform.
4. Low-performing or thin records: improve, merge, `noindex`, or remove.
5. Continuous: refresh data, update `lastmod` only on real changes, prune dead records (404/410 or 301 to the closest relevant page).

Publishing batches to production is a deploy — normal team approval rules apply; never bulk-publish to external CMSs without explicit approval (SKILL.md rule 1).

## URLs, canonicals, linking, sitemaps

- Patterns: `/integrations/{app}`, `/glossary/{term}`, `/{category}/{item}`, `/locations/{city}` — lowercase, hyphenated, < ~100 chars, consistent trailing slash.
- Self-referencing canonicals; if a programmatic page overlaps an editorial page, the stronger editorial page wins (merge or canonicalise to it).
- Hub pages (index by letter/category/region) linking to every child via `<a href>`; children link back to the hub and to 3–5 related siblings based on shared attributes; BreadcrumbList schema.
- Separate sitemap(s) for programmatic pages so Search Console shows their indexing rate independently; exclude `noindex`ed records.

## Index bloat controls

- `noindex` records that fail gates but are useful to users.
- Don't index sort/filter/pagination permutations of hubs (see technical.md faceted navigation).
- Monthly: indexed count vs intended count; investigate large "Discovered/Crawled – currently not indexed" buckets — usually a quality signal, not a technical bug.

## Audit output

Score 0–100 across: data quality, template uniqueness, URL structure, internal linking, thin-content risk, index management. Report percentages (uniqueness samples), counts, and the pages/records that fail each gate.

## Sources
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/crawling-indexing/crawling-managing-faceted-navigation
- claude-seo v1.9.9 `seo-programmatic` skill and `quality-gates.md` (AgriciDaniel, MIT)
