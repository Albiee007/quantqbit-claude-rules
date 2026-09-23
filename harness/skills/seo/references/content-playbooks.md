# Content and Growth Playbooks

Vendor-neutral playbooks distilled from the Distribb SEO agent skill (90-day sprint, audit playbook, link-building playbooks), corrected where they conflict with current Google guidance. Tools named are examples; use whatever data sources the user has, and **label every number's source** (Search Console, a keyword tool, an estimate). Never invent volumes, difficulty, rankings, or traffic.

**Approval rule**: everything here ends at drafts, plans, and ready-to-send assets. Publishing, scheduling, submitting, emailing, posting, or replying publicly needs explicit user approval of the specific action and content (SKILL.md rule 1).

## Operating loop

```
Research → Cluster → Brief → Write → Link internally → Publish (approved) → Measure → Refresh
```

1. **Research**: seed topics from the business (products, customer questions, sales/support logs, competitors), expand with keyword tools, People Also Ask, related searches, and Search Console queries the site already gets impressions for.
2. **Qualify**: intent (problem / solution / brand; or informational / commercial / transactional), realistic difficulty for the site's authority, business value (does it lead to a conversion?). Prefer "winnable" terms where current top results are beatable.
3. **Cluster**: group by SERP overlap into pillar + spokes (content-eeat.md). One primary intent per URL; merge terms that share most top results.
4. **Brief**: use the brief template in content-eeat.md — intent, unique angle, outline, evidence, internal links, schema, author.
5. **Write**: people-first, expert or experienced author, original evidence, answer-first sections, sourced facts, natural language (no keyword density targets, no filler length). Human review for accuracy; SME review for YMYL.
6. **Link**: new page links to its pillar and 2–5 relevant siblings; update the pillar and older related pages to link to it (descriptive anchors).
7. **Publish** (approved), ensure it's in the sitemap, request indexing only for a few priority URLs (Search Console, user action).
8. **Measure** against a stated baseline and window (e.g. 28/90 days, Search Console clicks/impressions/position, conversions). Don't claim causation from correlation.
9. **Refresh**: see the refresh cycle below.

## 90-day sprint (new or low-authority site)

| Phase | Weeks | Goals | Key tasks |
|---|---|---|---|
| 0. Pre-launch hygiene | Day 0 | Indexable foundation | Unique titles/descriptions everywhere; Organization/WebSite (+ SoftwareApplication or Article) schema; Search Console + Bing Webmaster Tools verified; sitemap submitted; request indexing for the ~5 most important URLs; link to the site from owned properties |
| 1. Foundation | 1–4 | Clean tech, keyword map, core pages | Lighthouse/PSI on home + core templates; robots/sitemap/canonicals/CWV fixed; 20–30 winnable keywords tagged by intent and mapped to target URLs; homepage H1 states what you do; ship the highest-intent use-case page and a first honest comparison page |
| 2. Content engine | 5–8 | Consistent publishing, first referring domains | 2–3 quality pieces/week in order: comparisons/alternatives → use cases → problem-aware posts → thought leadership; one pillar + 5–7 spokes interlinked; relevant directory/profile listings (curated, not bulk); one genuinely useful guest contribution; partner/integration pages where real partnerships exist |
| 3. Authority & compounding | 9–13 | Turn early signals into growth | Refresh pages at positions ~8–20; build the next cluster; answer-first formatting and question headings for snippet/AI citation; original data asset (survey, benchmark, statistics page with sources) for link earning |
| Day-90 review | 13 | Baseline vs result | Traffic (clicks, impressions, non-brand share), technical (indexed pages, CWV), content (published, ranking), authority (referring domains) |

Correction vs source: Distribb's sprint suggests "add FAQ schema to every key page". Google FAQ rich results are discontinued (2026); add visible FAQs where useful, but don't expect a rich result from the markup.

## Search Console audit (existing sites)

Run before writing anything new. Each analysis can run in its own subagent returning only a findings table.

| # | Analysis | Method | Action |
|---|---|---|---|
| 1 | CTR gaps | Queries/pages at position < 20 with impressions > ~50; compare CTR to your own site's CTR-by-position curve (industry curves vary widely and AI features lower CTR; label benchmark source); flag where actual < ~70% of expected | Rewrite title/meta; improve snippet eligibility |
| 2 | Content decay | Period-over-period clicks and position per page | Position down → refresh content; CTR down with stable position → rewrite title/meta; both → full refresh |
| 3 | Striking distance | Queries at positions 11–20 (pages at 8–12) with meaningful impressions | Expand/refresh + add internal links from strong pages |
| 4 | Cannibalisation | Same non-brand query surfacing multiple URLs; duplicate target keywords in the content inventory | Consolidate (merge + 301) or differentiate intent |
| 5 | Dead pages | Pages that had traffic and now have ~zero | Check status/noindex/canonical; restore or redirect; check for cannibalisation |
| 6 | Brand vs non-brand | Classify queries by brand terms; non-brand click share | < ~40% non-brand → content engine is the priority |
| 7 | Topic clusters | Map existing content to pillars/spokes | Fill missing spokes; link orphans |
| 8 | Competitor gaps | Topics competitors cover that fit your business | Add to content plan (never copy; never link to competitors in money pages) |
| 9 | On-page basics | Titles, descriptions, H1, indexability, internal links | Fix templates first |

Every finding must map to an action; a finding with no next step is noise.

## Refresh cycle

- Quarterly: pull pages with declining clicks or positions 8–20; prioritise by impressions × business value.
- Refresh = update facts/statistics, add missing subtopics and first-hand evidence, improve structure and answer-first intros, fix broken links, add internal links, update `dateModified` (only for substantive changes), re-check intent against the current SERP.
- Prune: merge overlapping posts, 301 obsolete ones to the best match, remove content that has no audience and no links.

## Link earning (ethical)

Links should be a by-product of giving something genuinely useful. Google's link spam policy prohibits buying/selling links that pass signals, **excessive link exchanges** ("link to me and I'll link to you"), automated link building, low-quality directory/bookmark links, and keyword-rich anchors in guest posts/widgets. Paid or incentivised placements must use `rel="sponsored"`.

Give-first playbooks (the user sends every email from their own account; the agent drafts):

| Playbook | Idea | Guardrails |
|---|---|---|
| Customer testimonial ("invoice method") | Offer honest testimonials/case studies to tools you actually pay for; many feature customers with a link | Only real usage; no quid-pro-quo pressure |
| Source sniping | Find pages (and listicles) that AI answers and SERPs cite for your category; pitch a specific, verifiable improvement or inclusion | Verify every claim about their page; tailor each pitch |
| Tombstone | Listicles/resources still linking to discontinued products or dead sites; suggest your relevant alternative | Confirm the product is really dead (primary source) |
| Fact decay | Pages citing outdated statistics; offer the current figure with source (ideally your own research) | Never invent or exaggerate the "decay" |
| Stale screenshot | Tutorials with outdated UI screenshots of tools you know; offer updated, licensed images | Provide the asset first; credit requested, not demanded |
| Missing visual | High-ranking text-only explainers; offer a free diagram/chart they can embed with attribution | Genuinely useful, accurate asset |
| Original data | Publish surveys, benchmarks, statistics pages with methodology and sources | Transparent methodology; cite every third-party stat |
| Digital PR / expert commentary | Respond to journalist requests where the user has real expertise | Truthful credentials only |

Rules: small numbers of bespoke pitches beat mass templates; never claim something was sent that wasn't; never fabricate facts about a prospect's page; relevant sites only; no link exchanges as a scheme; no PBNs, no paid dofollow links, no automated comment/forum spam, no fake reviews or astroturfed Reddit/Quora posts.

## Local and AI-visibility add-ons

- Local: GBP hygiene, review requests to all customers (no gating/incentives), weekly review replies drafted for approval, location/service pages with real local proof (local.md).
- AI visibility: a fixed panel of real buyer prompts, checked periodically across engines; record citations as samples; mark anything unverifiable as unverified; improve the cited-source landscape via the playbooks above (geo-ai-search.md).

## Sources
- Distribb SEO agent skill (`SKILL.md`, `upstream/90-day-seo-sprint/SKILL.md`, `upstream/references/audit-playbook.md`, `upstream/references/link-building-playbooks.md`, `upstream/commands/*.md`), reviewed 2026-09-23
- https://developers.google.com/search/docs/essentials/spam-policies
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/appearance/structured-data/faqpage
- https://developers.google.com/search/docs/crawling-indexing/links-crawlable
- claude-seo v1.9.9 `seo-plan`, `seo-cluster`, `seo-content-brief` skills (AgriciDaniel and contributors, MIT)
