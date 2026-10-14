# Measuring AI Search Visibility

[geo-ai-search.md](geo-ai-search.md) says how to be citable. This file says how to **measure** whether AI assistants reach, use and cite the site, with data the project owns. No measurement here involves scraping chat interfaces or automating accounts: prompts are run by a person (or through an official API the user has approved and pays for), and every tool reads local exports.

Four layers, each a precondition for the next:

| Layer | Question | Data | Tool |
|---|---|---|---|
| 1. Access | Can AI and search bots fetch the pages? | Server/CDN logs, Clarity Bot Activity | [`bot_log_audit.py`](../scripts/bot_log_audit.py) |
| 2. Eligibility | Is the page indexed and allowed in snippets? | Search Console, Bing Webmaster Tools, `check-url.sh` | technical.md |
| 3. Citation | Do answers cite us, for which queries, against whom? | Bing AI Performance, prompt library | [`ai_citations.py`](../scripts/ai_citations.py) |
| 4. Outcome | Does AI visibility bring visits and conversions? | Analytics referrals (chatgpt.com, perplexity.ai, copilot.microsoft.com, gemini.google.com, claude.ai), Search Console (AI features are counted under "Web") | analytics |

## 1. Bot access

- **Server or CDN logs** are the ground truth. Run `bot_log_audit.py access.log --robots robots.txt` for a status per bot (healthy, blocked, throttled, erroring, robots violations, over-scraping) and one fix each. Verify identity with the operators' published IP ranges (`--ranges TOKEN=FILE`); a user-agent string alone proves nothing.
- **Microsoft Clarity Bot Activity** (AI Visibility → Bot Activity) reads server-side logs from a connected CDN (Cloudflare, Fastly, Amazon CloudFront, Azure Front Door, Akamai; the Clarity WordPress plugin enables it automatically). It reports AI bot requests, share of traffic, pages crawled, response status and robots.txt violations, split by operator and by crawler vs assistant. Save its per-bot table as CSV (a user-agent or bot column, plus requests, path and status where shown) and pass it to `bot_log_audit.py`; confirm the column names against your export. Clarity notes that a bot request does not prove the content was used for training, grounding or a citation.
- Blocking a **search** bot (OAI-SearchBot, Claude-SearchBot, PerplexityBot, Bingbot, Googlebot) removes the site from that engine's answers. Blocking **training** bots does not. That is a business decision (see geo-ai-search.md). The bot list both files use is [ai-bots.json](ai-bots.json).

## 2. Citation data from Bing

Bing Webmaster Tools **AI Performance** (public preview since February 2026) reports how often the site is cited in Microsoft Copilot, Bing's AI summaries and some partner integrations:
- total citations, average cited pages, page-level citation counts and trends;
- **grounding queries**: the phrases the AI used to retrieve the content it cited. They are machine-written, summary-level and sampled, not users' prompts.
- June 2026 preview additions: **Intents** (informational, commercial, navigational), **Topics** (query clusters), **Citation Share** (your share of all citations for a grounding query) and **Compare**.

It does not measure rankings or authority, and the data is sampled, so read trends rather than single numbers. Export the grounding-query and page reports and run:

```
python ai_citations.py --bing-queries grounding.csv --bing-pages pages.csv --search gsc_queries.csv
```

Queries you rank for in the top 10 but that rarely ground a citation are **under-represented**: the page ranks but its passage isn't being picked. Make it citable (answer-first, defined terms, sourced numbers) and confirm Bingbot can fetch it. Google offers no citation report; AI Overviews and AI Mode traffic is included in Search Console's Web search type.

## 3. Prompt library (all assistants)

The only way to see answers in ChatGPT, Claude, Gemini, Perplexity and Google AI Mode is to ask them. Keep it disciplined:

1. **Write 8–30 prompts per topic** the way customers ask: problem ("how do I…"), comparison ("X vs Y for…"), recommendation ("best … for …"), brand ("is <brand> good for…"), local ("… near <city>"). Draw them from Search Console queries, sales and support questions, and Bing grounding queries. Don't write prompts that name the brand unless you are testing brand perception.
2. **Run each prompt in each assistant you care about**, in a clean session (logged out or a fresh profile, no memory or personalisation), at the same cadence (monthly). Record the location and date. Answers vary by run, so run important prompts 2–3 times.
3. **Record the result** in a CSV, one row per run:

   ```csv
   Prompt,Engine,Date,Cited,Our URL,Competitors,Notes
   best crm for startups,ChatGPT,2026-10-01,yes,https://ex.com/blog/best-crm,HubSpot;Pipedrive,listed third
   crm for law firms,Claude,2026-10-01,no,,Clio,recommends Clio and MyCase
   ```

   "Cited" means a link or named source pointing at the site; a brand mention without a link goes in Notes.
4. **Bucket it**: `ai_citations.py --prompts prompt_results.csv` sorts prompts into owned / contested / absent with one move each. Add `--bing-queries` and `--search` to combine with Bing data.

Report it as "cited in N of M prompt runs" per engine and topic, with the dates. Never present it as a market share or a ranking: it is a sample.

## 4. Entity clarity audit

Assistants and Google connect facts to **entities**. Score each layer 0–2 (missing / partial / done) and fix the lowest first:

| Layer | Done looks like |
|---|---|
| Entity home | One canonical page (usually About or home) that states who the organisation or person is, what it does, where, and since when, in plain text |
| Structured data | Organization (or Person) JSON-LD on the entity home with `name`, `url`, `logo`, `description`, `foundingDate`, `address` and contact where true, and `sameAs` links to the profiles below; consistent `@id` across pages (schema.md) |
| Consistent profiles | Same name, description and URL on LinkedIn, Crunchbase, GitHub, app stores, Google Business Profile, industry directories and social accounts; each links back to the site |
| Independent references | Coverage, reviews, awards, partner pages and directories that name the entity without being written by it; this is what assistants cite |
| Knowledge bases | A Wikidata item or Wikipedia article **only when** the entity meets their notability rules through independent, reliable sources. Creating items about your own organisation is discouraged as self-promotion, gets extra scrutiny and is deleted when notability is missing. Never create or edit them on the user's behalf without explicit approval (safety rule 1) |
| Knowledge panel | If Google shows one, claim it through the Google verification flow and keep facts current |

## Scorecard

Feed the results into the GEO readiness score in geo-ai-search.md:
- **Access**: every search bot healthy (or deliberately blocked, and recorded).
- **Eligibility**: key pages indexed, no `nosnippet` on content meant to be cited.
- **Citation**: trend in Bing citations, citation share, and prompt-library hit rate per topic.
- **Entity**: layer scores above.
- **Outcome**: AI-referral sessions and conversions per month.

## Sources
- https://developers.google.com/search/docs/appearance/ai-features
- https://blogs.bing.com/webmaster/February-2026/Introducing-AI-Performance-in-Bing-Webmaster-Tools-Public-Preview
- https://www.bing.com/webmasters/help/ai-performance-9f8e7d6c
- https://blogs.bing.com/search/June-2026/New-AI-Visibility-Insights-in-Bing-Webmaster-Tools-Intents-Topics-Citation-Share-Compare
- https://learn.microsoft.com/en-us/clarity/ai-visibility/bot-activity-overview
- https://clarity.microsoft.com/blog/robots-txt-violations-in-bot-analytics/
- https://www.wikidata.org/wiki/Wikidata:Notability
- https://www.wikidata.org/wiki/Wikidata:Self-promotion
