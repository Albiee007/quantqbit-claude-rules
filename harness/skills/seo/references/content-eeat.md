# Content Quality and E-E-A-T

Google's ranking systems aim to surface helpful, reliable, **people-first** content. The helpful-content signals are part of core ranking (no longer a separate classifier), so quality is assessed continuously and re-weighted at core updates. There is no word-count target and E-E-A-T is not a single ranking factor — it is the lens for judging whether a page deserves trust.

## People-first self-assessment

Ask of every page (condensed from Google's questions):
- Does it provide **original** information, reporting, research, or analysis — not just a rewrite of other sources?
- Is it a substantial, complete description of the topic, with insight beyond the obvious?
- Would a reader bookmark it, share it, or cite it? Would they leave satisfied, or need to search again?
- Is it written or reviewed by someone who demonstrably knows the topic (expert or experienced enthusiast)?
- Is it free of factual errors, spelling issues, and sloppy production?
- Is the headline accurate (no exaggeration or clickbait)?

Search-engine-first red flags:
- Producing lots of content on many unrelated topics hoping some ranks.
- Extensive automation to churn pages on many topics.
- Summarising others without adding value; writing to a word count; chasing trends outside the site's expertise.
- Changing publish dates to seem fresh without substantive changes.
- Promising answers to questions that have none (e.g. unconfirmed release dates).

## Who / How / Why

- **Who** created it: visible byline where readers expect one, linking to an author page with background and credentials.
- **How** it was created: disclose methods where readers would want to know — testing process for reviews, data sources, and how automation/AI was used.
- **Why** it exists: to help people. If the primary reason is attracting search visits, rethink it.

## E-E-A-T signals

**Trust is the most important** member; experience, expertise, and authoritativeness support it. Weight scrutiny by stakes: **YMYL** topics (health, finance, safety, legal, civic information, groups of people) need the strongest evidence.

| Dimension | On-page evidence to look for / add |
|---|---|
| Experience | First-hand use, original photos/screenshots, test data, specific details only a practitioner would know, case studies with numbers |
| Expertise | Author credentials relevant to the topic, accurate terminology, correct and current facts, expert review for YMYL ("Reviewed by …") |
| Authoritativeness | Recognition by others: citations, mentions, awards, being the primary source (the manufacturer, the official body) |
| Trust | Accurate claims with cited sources, clear ownership (About, contact, address), policies (privacy, returns, editorial/corrections), HTTPS, honest ads/affiliate disclosure, secure checkout |

### Author pages
- One page per author: name, photo, role, relevant qualifications/experience, links to profiles (`sameAs`), list of their articles.
- Mark up with `ProfilePage` + `Person` JSON-LD; reference the author from Article `author` (with `url`).
- Don't invent authors or credentials. Use organisation authorship when content is genuinely institutional.

### Freshness
- Show "Published" and "Updated" dates when time matters; update `dateModified` only for meaningful changes.
- Review cadence by type: news (hours/days), fast-moving topics like pricing/tools/regulations (quarterly), evergreen guides (at least annually), product/spec pages (whenever specs change).
- Freshness is query-dependent: evergreen topics don't need constant churn.

## AI-assisted content

Allowed when it adds value and is accurate. Generating many pages without adding value is **scaled content abuse** regardless of whether humans, AI, or both produce it. Requirements for AI-assisted pages here:
- Human expert review of facts, especially YMYL; cite sources.
- Add something not available elsewhere: original data, experience, examples, tools.
- Titles, meta descriptions, alt text, and structured data held to the same quality bar.
- Disclose automation where readers would reasonably expect it.
- AI-generated product images in e-commerce must carry IPTC `DigitalSourceType` = `TrainedAlgorithmicMedia`.

## Spam policies that touch content

- **Scaled content abuse** — "many pages are generated for the primary purpose of manipulating search rankings and not helping users" (any method).
- **Doorway abuse** — many near-identical pages targeting variants (cities, keywords) that funnel to one destination.
- **Site reputation abuse** — third-party content hosted on an established site to exploit its ranking signals.
- **Thin affiliation** — affiliate pages with copied merchant descriptions and no added value.
- **Scraping** — republishing others' content without adding value.
- **Keyword stuffing** and **hidden text**.
- **Expired domain abuse** — buying expired domains to host low-value content.
See programmatic.md for safe at-scale patterns.

## Thin and duplicate content

Thin = little unique value: boilerplate-heavy templates, stub pages, auto-generated tag pages, near-duplicate variants. Remedies in order of preference: **improve** (add unique substance), **consolidate** (merge + 301), **noindex** (keep for users, not search), **remove** (404/410).

Duplicate content is not penalised by itself (outside spam); it wastes crawl and splits signals. Fix with canonicalisation (technical.md).

Coverage floors from claude-seo (heuristics, not Google rules — use to flag *possible* thinness, then judge by intent): home ~500 words, service/feature ~800, blog post ~1,500, product ~300–400, category intro ~150–400 above/below the grid, location ~500–600 with majority unique content. A short page that fully answers a narrow query is fine.

## Search intent

Classify the dominant intent from the current SERP before writing:

| Intent | Signals | Page type that wins |
|---|---|---|
| Informational | how, what, why, guide | Guide, explainer, tutorial |
| Commercial investigation | best, vs, review, alternatives | Comparison, review, listicle with real testing |
| Transactional | buy, price, coupon, sign up | Product, pricing, landing page |
| Navigational | brand + product/page | The brand's own page |
| Local | near me, city + service | Location page + Business Profile |

Match format too (list vs long guide vs tool vs video). A page-type mismatch (e.g. a product page for an informational query) is a common reason good pages don't rank.

## Topic clusters

- **Pillar/hub**: broad page covering the topic, linking to every supporting page.
- **Spokes**: focused pages on subtopics/questions, each linking back to the pillar and to closely related siblings.
- Group keywords by **SERP overlap** (if two queries share many of the same top-10 URLs, one page can target both; little overlap → separate pages). Heuristic from claude-seo: 7–10 shared → same page; 4–6 → same cluster; 2–3 → adjacent clusters, interlink; 0–1 → separate.
- Only cover topics the site can credibly serve (products, expertise, audience).

## Keyword cannibalisation

Two or more URLs competing for the same query and intent, splitting signals and swapping positions.
- Detect: Search Console query → multiple pages with impressions; site search `site:example.com "topic"`; duplicate titles/H1s.
- Fix: keep the strongest page (links, conversions, relevance); merge the others' useful content into it and 301 them; or differentiate intents clearly (e.g. "X pricing" vs "what is X") and interlink. Don't `noindex` a page just to dodge cannibalisation if it has links — merge instead.

## Content brief template

```markdown
# Brief: <working title>
Target query + intent: <query> — <intent>; SERP format: <guide|comparison|…>
Audience & job-to-be-done: <who, what they need to do>
Primary term / related terms & entities: <…>
Unique angle (why ours is better): <original data, experience, tool, expert>
Outline: H1 …; H2 … (key points, evidence needed per section)
Must-answer questions: <from PAA / sales / support>
Evidence & sources: <primary sources, internal data, SME to interview>
Internal links: to <hub>, <siblings>; from <pages to update>
Schema: <Article + BreadcrumbList …>
Author / reviewer: <name, credentials>
Title (~55 chars) / meta description draft / slug
Success metric & review date
```

Rules (adapted from claude-seo's content-brief): suggest only sections the site can credibly deliver; hub briefs must cover every real child category and none that don't exist; when improving an existing page, keep what works and target gaps rather than rewriting.

## Content audit scoring

Score each E-E-A-T dimension 0–25 (Trust weighted most in judgment), plus checks for intent match, originality, freshness, structure, and internal links; roll up to the Content category score (0–100) in SKILL.md.

## Sources
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/fundamentals/seo-starter-guide
- https://developers.google.com/search/updates
- claude-seo v1.9.9 `seo-content`, `seo-content-brief`, `seo-cluster`, `eeat-framework.md`, `quality-gates.md` (AgriciDaniel and contributors, MIT)
- Distribb SEO agent skill `references/audit-playbook.md` (cannibalisation and decay analyses)
