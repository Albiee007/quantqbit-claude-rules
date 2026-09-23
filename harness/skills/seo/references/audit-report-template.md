# SEO Audit Report Template

Copy, fill, and delete guidance lines (in *italics*). Every finding needs evidence (URL + observed value) and a concrete fix. State data gaps instead of guessing. Keep the executive summary to one screen.

---

```markdown
# SEO Audit: <site> — <YYYY-MM-DD>

**Prepared for:** <team/owner>  **Auditor:** <name / agent>  **Scope:** <domains, sections, templates>
**Method:** <pages sampled (N), crawl limits, tools/data: check-url.sh, Search Console (Y/N), CrUX/PSI (Y/N), logs (Y/N)>
**Business type:** <SaaS | e-commerce | local | publisher | agency | other>  **Markets/languages:** <…>

## 1. Executive summary

**SEO health score: NN/100 (<excellent | good | needs work | poor>)**

| Category | Weight | Score | Status |
|---|---|---|---|
| Technical SEO | 22 | NN | pass / warn / fail |
| Content quality (E-E-A-T) | 23 | NN | |
| On-page SEO | 20 | NN | |
| Schema / structured data | 10 | NN | |
| Core Web Vitals | 10 | NN | |
| AI-search readiness (GEO) | 10 | NN | |
| Images | 5 | NN | |

*If a category was not assessable, mark "n/a", renormalise weights, and say why.*

**Top 5 issues**
1. <Critical/High issue — one line, impact, fix>
2. …

**Top 5 quick wins** (high impact, effort S)
1. …

**Bottom line:** <the single most important thing to do first>

## 2. Prioritised action plan

| # | Severity | Category | Finding | Evidence | Fix | Effort | Owner |
|---|---|---|---|---|---|---|---|
| 1 | Critical | Technical | Production robots.txt disallows `/` | `https://…/robots.txt` line 2 | Remove rule; add Sitemap line | S | Dev |
| 2 | High | Content | … | … | … | M | Content |

*Severity: Critical = blocks crawl/index or risks manual action; High = materially limits ranking/eligibility; Medium = optimisation; Low = polish. Effort: S ≤ 1 h, M ≤ 1 day, L > 1 day.*

## 3. Technical SEO — NN/100
- Crawlability (robots.txt, internal links, orphans): …
- Indexability (meta robots, canonicals, duplicates, Search Console coverage): …
- Status codes & redirects (chains, soft 404s): …
- Rendering (raw vs rendered HTML, SSR status per template): …
- URL structure, pagination, faceted navigation: …
- HTTPS / mobile-first / security issues: …
- Sitemaps (validity, coverage vs crawl): …
- International (hreflang), if applicable: …

## 4. Content quality — NN/100
| Template/page | Intent match | E | E | A | T | Originality | Freshness | Notes |
|---|---|---|---|---|---|---|---|---|
- Thin / duplicate / cannibalised pages: …
- Author & trust signals (bylines, author pages, About, policies): …

## 5. On-page SEO — NN/100
| URL | Title (len) | Description (len) | H1 count | Canonical | Issues |
|---|---|---|---|---|---|
- Internal linking gaps and anchor quality: …
- Social tags (OG/Twitter): …

## 6. Structured data — NN/100
| Page type | Types found | Valid? | Eligible features | Issues | Recommended |
|---|---|---|---|---|---|
*Include ready-to-paste JSON-LD for top recommendations; no placeholders left unexplained.*

## 7. Core Web Vitals — NN/100
| Template | Source (CrUX/RUM/lab) | LCP p75 | INP p75 | CLS p75 | Main cause |
|---|---|---|---|---|---|

## 8. AI-search readiness — NN/100
- Access (indexable, snippet-eligible, SSR, AI search bots allowed in robots.txt/WAF): …
- Answerability & structure: …
- Evidence, originality, entity clarity: …
- AI crawler policy summary (search vs training): …

## 9. Images — NN/100
| Metric | Count |
|---|---|
| Images sampled | N |
| Missing alt | N |
| No dimensions | N |
| Lazy-loaded LCP | N |
| Oversized (> 200 KB) | N |
| Legacy format only | N |

## 10. Conditional sections (delete if n/a)
- Local SEO (GBP, NAP, reviews, location pages): …
- E-commerce (product/category templates, facets, availability): …
- Programmatic (gates, uniqueness, index bloat): …

## 11. Data gaps & assumptions
- <e.g. No Search Console access — indexing inferred from site: and crawl only>
- <e.g. CrUX has no URL-level data — origin-level used>

## 12. Next steps
1. <Immediate action> — owner, due date
2. Re-audit date: <YYYY-MM-DD> with the same sample for comparison

*External actions (Search Console submissions, IndexNow, GBP edits, outreach, publishing) are listed as recommendations for the user to approve; none were performed.*

---
Methodology: category weights adapted from claude-seo (AgriciDaniel, MIT). Facts verified against Google Search Central and web.dev as of <date>.
```

## Short form (single page review)

```markdown
# Page review: <URL> — <date>
Score: NN/100 (On-page NN · Content NN · Technical NN · Schema NN · Images NN · CWV n/a)
| Severity | Finding | Evidence | Fix | Effort |
|---|---|---|---|---|
Suggested title: … (NN chars) | Suggested description: … | JSON-LD: <block>
```

## Sources
- claude-seo v1.9.9 `seo-audit` skill report structure and priority definitions (AgriciDaniel, MIT)
- Distribb SEO agent skill `upstream/references/audit-playbook.md` (report format; "tie every finding to an action")
