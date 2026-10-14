# Page Types That Win Decisions

How to build the pages people use to decide: comparisons, alternatives, "best for" lists, buyer's guides, category and product pages, listicles and calculators. Each serves a commercial or decision-stage intent (content-eeat.md §Search intent). They rank and get cited when they help someone choose. Pages that exist only to rank don't.

## Rules for every decision page

- **Honesty first.** Criteria are stated before the verdict. Every option gets real trade-offs, including your own product's weaknesses and who it is *not* for. No invented rankings, awards, prices, review counts or test results (safety rule 5).
- **Disclose interest.** If you make one of the products, or earn affiliate commission, say so near the top, in plain words.
- **First-hand evidence.** Screenshots, test notes, measured numbers and named reviewers beat rewritten spec sheets. Mark where the author's own expertise must go when drafting.
- **Date it.** Show the date the prices and features were checked, and refresh at least quarterly (`dateModified` only for substantive changes).
- **Answer first.** The opening paragraph gives the short answer ("For a 5-person sales team, X; for…"), then the detail. This is also the passage AI answers lift.
- **Structure for scanning.** Comparison tables in HTML (`<table>`, not images), consistent rows, units in headers.

## Comparison: "X vs Y"

Sections:
1. The verdict in two sentences, by use case.
2. A table of criteria.
3. One section per criterion.
4. Who should pick each.
5. Pricing as of a date.
6. How we compared.

Compare on what buyers weigh: price model, key capabilities, integrations, limits, support, migration effort. Link to each product's own page; don't link to competitors from money pages unless the comparison itself is the page.

## Alternatives: "X alternatives"

The searcher is unhappy with X. Start with *why* people leave X (sourced from reviews or support conversations, not invented). Then give 4–8 genuine options, each with "best for", a key trade-off and a price model. Include your product once, ranked honestly, with the disclosure.

## "Best X for Y" and listicles

- Each item needs: a one-line verdict (a micro-summary an answer engine can quote), who it suits, evidence (test result, data point, quote with source), a trade-off, and a price model.
- The order follows the stated criteria. Explain how the list was made.
- Mark up the list with `ItemList` only when the items are visible on the page. FAQ and HowTo markup no longer produce rich results (schema.md).

## Buyer's guide

For buyers who don't yet know their options. Cover:
- the decision criteria in priority order;
- questions to ask vendors;
- red flags;
- a short checklist.

Link to comparisons and category pages for the next step. It is the hub of a decision cluster (content-eeat.md §Topic clusters).

## Category pages (e-commerce and directories)

A product grid alone is thin. Add decision support above or below the grid, without pushing products out of view:
- A short intro (2–4 sentences) on what's in the range and how to choose.
- A compact buying guide or "how to choose" block (3–5 criteria).
- A comparison table of the top sub-types or best sellers.
- Visible FAQs only where buyers really ask them.
- `ItemList` or `CollectionPage` markup that matches what's shown, plus BreadcrumbList.

Facets and filters follow ecommerce.md §Faceted navigation. The category text must be original, not repeated across categories.

## Product pages

Check these eight points:
1. Unique description, written for the buyer's use case (not the manufacturer copy).
2. Key specs in a table.
3. Price, availability and shipping/returns visible and matching the Offer markup.
4. Real images (multiple angles, in-use), with alt text.
5. Reviews from verified buyers, with response to criticism.
6. Answers to the questions support hears most.
7. Product + Offer JSON-LD with GTIN/brand/MPN where they exist (ecommerce.md).
8. Machine-readable for shopping agents: price, variants and add-to-cart are real HTML controls, not canvas or script-only widgets (ecommerce.md §Agentic commerce).

## Calculators and tools

Calculators earn links and answer "how much / how many" queries, but only when the tool is real and the page explains it:
- Server-render the explainer: what it calculates, the formula and assumptions, sources for any rates, and a worked example. The interactive part can be client-side; the explanation must be in the initial HTML.
- Accessible inputs: labels, units, keyboard use, error messages; results announced with `aria-live` (ui-ux skill).
- No hidden data capture. Asking for an email to show the result is a choice that costs rankings and trust.
- Keep rates and defaults current, and show the date they were checked.

## Persona (ICP) fit review

Before publishing a commercial page, check it against the buyer personas the business has defined (never invent personas):
- Which of each persona's top questions does the page answer, and which are missing?
- Does the tone and vocabulary match how they describe the problem (from sales calls, support tickets, reviews)?
- Is the next step obvious for them (demo, trial, pricing, contact)?
- If a converted lead's actual path is available, does this page answer what they asked before buying?

Report it as: answered questions, missing questions, tone fit (one line) and three concrete edits.

## Sources
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/specialty/ecommerce/write-high-quality-reviews
- https://developers.google.com/search/docs/appearance/structured-data/product
- https://developers.google.com/search/docs/specialty/ecommerce/help-google-understand-your-ecommerce-site-structure
- https://developers.google.com/search/docs/appearance/structured-data/carousel (ItemList)
