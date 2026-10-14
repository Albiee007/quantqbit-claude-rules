# SaaS and B2B SEO

An audit lens for software products and B2B services, where buyers research for weeks, compare vendors and involve several people. Use it with the audit workflow in SKILL.md when the business type is SaaS or B2B. Most organic revenue comes from pages that match buying intent, not from top-of-funnel traffic.

## Page inventory (does each exist, rank and convert?)

| Page type | Intent it serves | Must have |
|---|---|---|
| Home | Brand, category | What it is, for whom, proof, one primary CTA; Organization + WebSite markup |
| Feature pages (one per major capability) | "<capability> software" | The job it does, screenshots or short video, how it works, limits, related integrations |
| Use-case / solution pages (by job or team) | "<tool> for <job>" | The job's problem in the buyer's words, workflow, outcome evidence |
| Industry pages | "<tool> for <industry>" | Industry-specific constraints (compliance, terms), customers in that industry. Only where you really serve it. |
| Integration pages | "<tool> <other tool> integration" | What syncs and in which direction, setup steps, limits. Never a templated page for an integration that doesn't exist (programmatic.md). |
| Comparison and alternatives | "X vs Y", "X alternatives" | See page-types.md: honest, dated, disclosed |
| Pricing | "<brand> pricing", "<category> pricing" | Plans and what they include in HTML text; FAQs on billing; no "contact us" only, if pricing is public |
| Docs and API reference | "how to <task> in <brand>", error messages | Server-rendered, indexable, versioned URLs, code samples, search |
| Changelog / release notes | Brand + feature queries, freshness | Dated entries, one URL per significant release or a stable list page |
| Help center | Support queries, "how to" | Indexable unless account-specific; linked from the product |
| Case studies | "<brand> reviews", trust | Named customer, measurable result with the baseline, the customer's quote, permission confirmed |
| Templates, calculators, free tools | Top-of-funnel, links | Real utility; explained in server HTML (page-types.md) |

## Technical specifics for SaaS sites

- **Split the marketing site and the app** (web-launch-checklist.md §17): the marketing site and docs are server-rendered and indexable. App routes return 401/403 or redirect to login with `noindex`, and stay out of sitemaps.
- **Docs platforms** (Docusaurus, Mintlify, GitBook, ReadMe, Next.js): confirm canonical host (docs.example.com vs example.com/docs), sitemap and indexability. Versioned docs canonicalise old versions to the current one, unless people still need the old versions.
- **Signup and login pages**: indexable only if they serve as landing pages; otherwise `noindex`.
- **Status page, trust center, security page**: public, linked from the footer; useful for B2B buyers and for AI answers about compliance (state only certifications actually held).
- **App marketplace listings** (Shopify, Salesforce AppExchange, Atlassian, HubSpot, Chrome Web Store): consistent name and description, linked back to the site; they are part of the entity footprint (ai-visibility.md §4).

## Product-led content

Content that shows the product doing the job beats generic articles:
- A tutorial solves a real task with the product, with screenshots.
- A template or example can be used right away.
- Benchmarks or reports built from **aggregated, anonymised** product data, with privacy and customer consent checked. These are link-earning assets (content-playbooks.md §Link earning).

Generic "what is X" posts earn little unless they carry original data or expertise (content-eeat.md §Information gain).

## B2B services (agencies, consultancies, professional services)

- **One page per service.** Each says:
  - the problem it solves;
  - the process and deliverables;
  - timeline and engagement model;
  - pricing range or what drives price;
  - who delivers it (named people with credentials);
  - relevant case studies.
- **Thought leadership with a point of view**, written or reviewed by the named expert, with bylines linking to author pages (content-eeat.md §Author pages).
- **Lead paths.** Each service page has one clear next step; forms ask only for what qualification needs; the thank-you page sets expectations.
- **Proof.** Logos only with permission, quantified outcomes with context, and reviews on third-party platforms.

## SaaS / B2B audit checklist

- [ ] Every major feature, use case and real integration has its own indexable page, linked from navigation or hubs.
- [ ] Comparison and alternatives pages exist for the top 3–5 competitors buyers actually evaluate, and they are honest and dated.
- [ ] Pricing is crawlable HTML (not an image or client-only widget).
- [ ] Docs, help center and changelog are indexable, on the canonical host, in the sitemap, with internal links to marketing pages.
- [ ] App routes are kept out of the index; no 200 empty shells.
- [ ] Case studies name customers and results with permission.
- [ ] Organization markup and `sameAs` links to marketplace listings and profiles are in place.
- [ ] Brand vs non-brand click share from Search Console (content-playbooks.md §Search Console audit). Non-brand growth is the goal.
- [ ] Conversion tracking ties organic landing pages to signups or demos (web-launch-checklist.md §16).

## Sources
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- https://developers.google.com/search/docs/appearance/structured-data/software-app
- https://developers.google.com/search/docs/essentials/spam-policies (scaled content abuse)
