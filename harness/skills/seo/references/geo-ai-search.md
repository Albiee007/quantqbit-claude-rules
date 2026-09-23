# AI Search and Generative Engine Optimisation (GEO)

"GEO" here means making pages easy for AI-driven search experiences — Google AI Overviews and AI Mode, ChatGPT search, Perplexity, Copilot, Claude — to **find, understand, trust, and cite**. It is an extension of SEO, not a replacement, and much of the industry advice is unproven. Stick to what operators document and what also helps human readers.

## What Google says (primary source)

- "There are no additional requirements to appear in AI Overviews or AI Mode, nor other special optimizations necessary." Standard SEO fundamentals apply.
- To be shown as a supporting link, a page must be **indexed and eligible to be shown with a snippet** — i.e. meet the normal Search technical requirements.
- Controls: `nosnippet`, `data-nosnippet`, `max-snippet`, and `noindex` apply to AI features too. Googlebot robots.txt rules control crawling for Search including AI features. **Google-Extended** only controls use for Gemini model training/grounding outside Search and does **not** affect Search inclusion or ranking.
- Traffic from AI Overviews/AI Mode is reported inside Search Console's Performance report (Web search type); there is no separate filter.

Implication: a page that is not indexable, is client-rendered only, or blocks snippets will not be cited by Google's AI features.

## How answer engines select sources (practical model)

Most answer engines run retrieval over a search index (their own or a partner's), then have a model synthesise an answer citing a few passages. Pages get cited when they:
1. Are **retrievable**: crawlable by that engine's search bot, indexable, and fast to fetch. Many AI fetchers do not execute JavaScript — server-render content.
2. Contain a **passage that directly answers** a sub-question, understandable without surrounding context.
3. Look **trustworthy**: clear authorship, sources, dates, consistent facts across the web.
4. Offer **something unique** — original data, first-hand testing, definitive specs — rather than a restatement of common knowledge.

## Citation-friendly content structure

- Lead each section with the answer (1–2 sentences), then detail. Use question-style H2/H3 when the section answers that question.
- Self-contained passages: name the subject explicitly instead of "it"/"this" at the start of a section; define terms ("X is …").
- Specific, verifiable facts: numbers with units, dates, versions, prices with currency, each with a cited source.
- Tables for comparisons and specs; ordered lists for procedures; short paragraphs.
- Visible "Updated on" dates and a changelog for fast-moving topics; keep facts current (stale numbers get dropped or contradicted).
- Summaries/TL;DR at the top of long pages.
- Visible FAQ sections are fine for users and answer engines (don't expect a Google FAQ rich result — discontinued in 2026).
- Original assets: benchmarks, surveys, calculators, datasets, and diagrams with text explanations are the most cite-worthy.
- Avoid: fluff intros, walls of text, burying the answer, contradictory numbers across pages, AI-generated filler.

claude-seo suggests self-contained answer blocks of roughly 130–170 words; treat as a heuristic, not a rule.

## Entity clarity

AI systems reason about **entities** (organisations, people, products, places). Make yours unambiguous:
- Consistent name, description, logo, and facts across the site, Business Profile, social profiles, directories, and knowledge bases (Wikidata/Wikipedia only where notability genuinely exists — never create promotional entries).
- Organization JSON-LD with stable `@id`, `sameAs` links to official profiles; Person markup for authors; Product/SoftwareApplication with clear names and versions.
- A clear About page, a product/pricing page with current facts, and docs/specs pages that answer "what is X / how much / does it do Y".
- Third-party mentions (reviews, press, community discussions, comparisons) influence what answer engines say about a brand. Earn them honestly; never fabricate reviews or astroturf communities.

## AI crawler controls (robots.txt)

Decide per business goal: **search/answer visibility** vs **training use**. Tokens verified from operator docs (Sept 2026):

| Operator | Token | Purpose | Honours robots.txt |
|---|---|---|---|
| Google | `Googlebot` | Search, including AI Overviews/AI Mode | Yes |
| Google | `Google-Extended` | Gemini training/grounding outside Search (control token, not a separate crawler) | Yes |
| OpenAI | `OAI-SearchBot` | ChatGPT search results; blocking removes you from ChatGPT search answers | Yes |
| OpenAI | `GPTBot` | Model training | Yes |
| OpenAI | `ChatGPT-User` | User-initiated fetches in ChatGPT/GPTs | May not apply (user-initiated) |
| Anthropic | `Claude-SearchBot` | Search indexing for Claude | Yes |
| Anthropic | `ClaudeBot` | Model training | Yes |
| Anthropic | `Claude-User` | User-initiated fetches | Yes (per Anthropic) |
| Perplexity | `PerplexityBot` | Perplexity search index (not training) | Yes |
| Perplexity | `Perplexity-User` | User-initiated fetches | Generally no |
| Microsoft | `Bingbot` | Bing index (also used by Copilot) | Yes |
| Common Crawl | `CCBot` | Open crawl dataset widely used for training | Yes |
| Apple | `Applebot` / `Applebot-Extended` | Spotlight/Siri/Safari search / control token for Apple model training | Yes |

Example — visible in AI search, opted out of training:

```
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: *
Allow: /
Disallow: /admin/

Sitemap: https://example.com/sitemap.xml
```

Notes:
- Blocking a search bot (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Bingbot`) removes you from that engine's answers. Blocking training bots does not.
- robots.txt is advisory; enforce with WAF/bot management if needed. Verify bots by published IP ranges, not UA strings.
- Don't block these bots at the CDN/WAF by accident (common with default "block AI bots" toggles) if visibility is the goal.
- Changing robots.txt policy for AI bots is a business decision — surface it to the user; don't change it unilaterally.

## llms.txt stance

`/llms.txt` is a community proposal (a Markdown index of key pages for LLMs). Status as of Sept 2026:
- Google has said it does not use it (compared it to the keywords meta tag); no major AI provider has committed to using it for search/answers.
- Public log studies show AI crawlers rarely request it.
- Genuine use: developer documentation consumed by coding assistants and agents.

Policy here: **optional, low priority.** Don't score its absence as a defect or claim ranking/citation benefits. Reasonable to add for developer-docs sites (keep it accurate and auto-generated from the docs nav). Similarly treat emerging licensing standards (e.g. RSL) as optional business decisions.

## Measurement

- Search Console (AI features are included in Web performance data); watch impressions vs clicks on informational queries.
- Analytics referrals from `chatgpt.com`, `perplexity.ai`, `copilot.microsoft.com`, `gemini.google.com`, `claude.ai` (referrers are often stripped; treat as a lower bound).
- Manual/prompt panel checks: a fixed list of priority questions run periodically in each engine, recording whether and how the brand is cited. Label results as samples (answers vary by user, location, and time). Do not automate queries against Google Search (machine-generated traffic policy).
- Server logs: hits from search-oriented AI bots on key pages.

## GEO readiness score (AI-search category, 0–100)

| Dimension | Weight | Checks |
|---|---|---|
| Access | 30 | Indexable, snippet-eligible, SSR content, AI search bots not blocked (robots + WAF) |
| Answerability | 25 | Answer-first sections, self-contained passages, question headings, tables/lists |
| Evidence & originality | 20 | Cited facts, original data/experience, dates current |
| Entity clarity | 15 | Organization/Person/Product schema with `@id`/`sameAs`, consistent facts, About page |
| Measurement | 10 | Referral tracking, periodic citation checks |

Dimensions adapted from claude-seo's GEO scoring, reweighted toward documented factors.

## Sources
- https://developers.google.com/search/docs/appearance/ai-features
- https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers
- https://developers.google.com/search/docs/appearance/snippet
- https://developers.openai.com/api/docs/bots
- https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler
- https://docs.perplexity.ai/guides/bots
- https://support.apple.com/en-us/119829
- https://ahrefs.com/blog/llmstxt-study/
- https://www.webyes.com/blogs/does-llms-txt-improve-rankings/
- claude-seo v1.9.9 `seo-geo` skill and agent (AgriciDaniel, MIT)
- Distribb SEO agent skill `commands/ai-visibility.md` (prompt-panel visibility checks, never fabricate citations)
