# Local SEO

For businesses that serve customers at a physical location or within a service area. Local results (map pack, Maps, local finder) are driven mostly by the **Google Business Profile (GBP)**, with the website supporting relevance and prominence.

Google's stated local ranking factors: **relevance** (how well the profile matches the query), **distance** (from the searcher), and **prominence** (how well known the business is — links, reviews and ratings, web presence). "There's no way to request or pay for a better local ranking."

## Business type

| Type | Signals | Implications |
|---|---|---|
| Storefront | Customers visit an address | Show address publicly; map embed; full NAP everywhere |
| Service-area business (SAB) | Travels to customers, no public storefront | Hide address in GBP; one service-area profile; `areaServed` on site; no fake offices |
| Hybrid | Storefront + service area | Show address and service areas |

## Google Business Profile guidelines (must follow)

- **Eligible** only with in-person contact during stated hours at a real location or service area. No virtual offices, P.O. boxes, or mailboxes-as-offices.
- **Name** exactly as on real-world signage/branding. No keywords, locations, taglines, or phone numbers in the name — the most common cause of suspensions.
- **One profile per location** (per business); no duplicate profiles. Departments/practitioners only where rules allow.
- **Categories**: the fewest that describe the core business; primary category is the most specific accurate one. Don't use categories as keywords.
- **Hours**: accurate regular and special hours.
- **Description**: accurate; no links, no promotional ALL CAPS, no irrelevant content.
- Keep phone, website link, attributes, services/products, and photos current.

**Safety:** creating, editing, posting to, or replying from a Business Profile is an external action — draft changes and get explicit approval (SKILL.md rule 1). Never create profiles for addresses the business doesn't operate from.

## Reviews

Google prohibits:
- Fake engagement or reviews not based on a real experience.
- **Incentives** (payment, discounts, freebies) for reviews or for changing/removing reviews.
- **Review gating**: discouraging negative reviews or selectively soliciting positive ones (e.g. "Happy? Review us on Google; unhappy? tell us privately" flows).
- Conflict-of-interest reviews (owners, employees, competitors), and staff quotas for reviews.

Do:
- Ask every customer, the same way, with a direct review link (from GBP "Ask for reviews").
- Respond to reviews professionally; for negatives, acknowledge, take it offline, don't disclose private details (healthcare/legal confidentiality applies).
- Review velocity and recency matter to users; aim for a steady flow, not bursts.
- Public replies are external posts → approval required before posting.
- Site review stars: `aggregateRating` in LocalBusiness/Organization markup about **your own** business is not eligible for review rich results; only show genuine, attributable testimonials.

## NAP consistency and citations

NAP = Name, Address, Phone. Keep identical across: website (footer/contact page), LocalBusiness JSON-LD, GBP, Apple Business Connect, Bing Places, major directories and data aggregators, industry directories (e.g. medical, legal, trades), and social profiles.
- Use one canonical phone number (tracking numbers: put the main number as primary where platforms allow).
- Same address formatting (suite numbers, abbreviations) where possible.
- After a move or rebrand, update everywhere and mark old listings closed/merged rather than leaving duplicates.
Citations mostly support prominence and data accuracy; don't buy bulk low-quality directory packages.

## Website signals

- **Location pages** (one per real location): unique content — address, map embed (lazy-loaded), hours, parking/transit directions, local team, photos of that location, services offered there, local testimonials, FAQs specific to that location. Include NAP in HTML text (not an image).
- **Service pages**: one page per core service; for SABs, service pages can mention served areas where you genuinely operate, with real local proof (projects, reviews).
- **Title/H1** combining service and place where natural: `Emergency Plumber in Austin, TX | Acme Plumbing`.
- **Click-to-call** (`<a href="tel:+15125550100">`) and clear contact CTA.
- **Doorway risk**: "city-swap" pages (same text with only the city name changed) are doorway abuse. Swap test: if you can swap the city name and the page still reads correctly, it's not unique enough. claude-seo quality gate: warn at 30+ location pages, require explicit justification at 50+, each with majority-unique content and real local presence.
- Store locator: every location has a crawlable, indexable URL linked via `<a href>` (not only a JS map widget).

## LocalBusiness schema

- Most specific subtype (`Dentist`, `Plumber`, `Restaurant`, `LegalService`, `AutoRepair` …); one block per location page with a unique `@id`.
- Required by Google: `name`, `address`. Recommended: `geo` (≥5 decimal places), `telephone`, `openingHoursSpecification`, `url`, `priceRange` (<100 chars), `image`, `menu`/`servesCuisine` for restaurants.
- SABs: `areaServed` (named cities/regions), omit `streetAddress` if hidden publicly (Google's feature expects an address; weigh accuracy over eligibility).
- Multi-location: link to the brand `Organization` via `parentOrganization` (or `branchOf`), `sameAs` to the location's Maps URL.
- Values must match GBP and the visible page. Template: `LocalBusiness` in [schema-templates.json](schema-templates.json).

## Local audit checklist

| Area | Checks | Weight (local score) |
|---|---|---|
| GBP | Claimed/verified, name compliant, primary category correct, hours, photos, services, no duplicates | 25 |
| Reviews | Volume, rating, recency, response rate, no gating/incentives | 20 |
| On-site | Location/service pages unique, NAP in HTML, local title/H1, crawlable locator, CWV | 25 |
| NAP & citations | Consistency across site, schema, GBP, top directories | 15 |
| Schema | Correct subtype, required props, matches GBP | 15 |

Weights adapted from claude-seo's local dimensions. Can't verify GBP data without access? Say so; infer only from public signals and never guess ratings or counts.

## Sources
- https://support.google.com/business/answer/3038177
- https://support.google.com/business/answer/7091
- https://support.google.com/contributionpolicy/answer/7400114
- https://developers.google.com/search/docs/appearance/structured-data/local-business
- https://developers.google.com/search/docs/essentials/spam-policies
- claude-seo v1.9.9 `seo-local` skill, `local-seo-signals.md`, `quality-gates.md` (AgriciDaniel, MIT)
- Distribb SEO agent skill `commands/gbp.md` (review replies are public — approval before posting)
