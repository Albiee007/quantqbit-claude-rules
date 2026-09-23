# Navigation and Information Architecture

## Information architecture
- Organize by **user tasks and mental models**, not by org chart, database, or API structure. Validate with card sorting (grouping) and tree testing (findability) when restructuring.
- Name sections in user vocabulary. Each label is distinct and predictable: users should be able to guess what is behind it (information scent).
- Prefer broad and shallow over deep hierarchies. Every level adds a decision (Hick's Law), and every hidden level adds recall.
- One canonical location per item. Cross-link from other contexts instead of duplicating pages.
- Order by importance and frequency (Pareto). Put the most important items first and last (serial position).

## Choosing navigation patterns
| Pattern | Use when | Rules |
|---|---|---|
| **Top nav bar (web)** | 3-7 top-level sections, desktop | Visible labels. Current section indicated (`aria-current="page"`). Collapses to a menu button on narrow screens |
| **Sidebar / navigation drawer** | Many sections or apps with deep tools | Collapsible groups. Persistent on wide screens, modal on narrow. Current item highlighted with more than color |
| **Bottom navigation / tab bar (mobile)** | 3-5 top-level peer destinations | Icon plus label, always. Navigation only, never actions. Tabs keep their own state. Never hide or disable tabs |
| **Navigation rail (Android medium+)** | Tablet or foldable widths | See [material3](material3.md) |
| **Tabs (in-page)** | 2-6 peer views of the same object | Short labels. Do not use for sequential steps. ARIA tabs pattern (arrow keys move between tabs) |
| **Hierarchical push / back** | Drill-down (list to detail) | Back returns to the previous level with scroll position and filters preserved |
| **Stepper / wizard** | Linear multi-step task | Show steps and position. Back without data loss. Review step before commit |
| **Breadcrumbs** | Sites with 3+ hierarchy levels | See below |
| **Search** | Large content sets or known-item seeking | See below |
| **Hamburger / overflow menu** | Secondary items only on small screens | Never hide the primary destinations behind it when a tab bar fits |

Platform: Android uses the system Back (predictive back). Never trap it, and it closes sheets and dialogs first. iOS uses the edge-swipe back gesture; keep it working. Web: every view has a URL. Browser Back and Forward, deep links, refresh, and open-in-new-tab work. Real links (`<a href>`) for navigation, `<button>` for actions.

## Breadcrumbs
- Supplement primary navigation; never replace it.
- Show the **hierarchy, not the history**. One canonical path when a page has several parents.
- Start with Home (or the root). The last item is the current page: not a link, `aria-current="page"`, and visually distinct.
- Include only real pages that users can navigate to.
- Skip breadcrumbs for flat sites (1-2 levels).
- Mobile: do not wrap onto several lines. Consider showing only the parent ("< Parent"). Keep touch targets adequate.
- Markup: `<nav aria-label="Breadcrumb"><ol>...</ol></nav>`.

## Search
- A visible search field (not just an icon) when search is a primary task. Magnifier icon plus a label or accessible name. `role="search"` landmark / `<search>`.
- Tolerate typos, synonyms, plurals, and case (Postel's Law). Offer autosuggest with keyboard support (combobox pattern).
- Results page: repeat the query in an editable field, show the result count (announced via a status message), highlight matched terms, and offer sorting and filters with visible applied-filter chips that can be removed individually.
- No results: suggest corrections and alternatives. Never a dead end ([forms-and-states](forms-and-states.md)).
- Preserve search, filter, sort, and pagination in the URL (web) or navigation state (native).

## Wayfinding
- Users can always answer: Where am I? Where can I go? How do I get back?
- Page and screen titles are unique and descriptive (WCAG 2.4.2). Headings form a logical outline (one `h1`, no skipped levels).
- Mark the current location in every navigation component. Visited links differ from unvisited links where it helps.
- Repeated navigation keeps the same order and position (3.2.3). Same function, same label and icon (3.2.4). Help lives in a consistent place (3.2.6).
- Provide at least two ways to reach content in a site (nav plus search or sitemap, 2.4.5).
- Skip link to main content and landmarks (`header`, `nav`, `main`, `footer`, `aside`) with labels when repeated (2.4.1).
- After navigation in a SPA: move focus to the new page's `h1` or main region and update the `<title>`. Announce route changes.
- Overlays (dialogs, sheets, menus): focus moves in, Esc and Back close them, focus returns to the trigger. The background is inert (`inert`, `aria-modal="true"`).
- Links opening a new window or tab, or a download, say so ("(opens in new tab)", "PDF, 2 MB").

## Sources
- https://www.nngroup.com/articles/breadcrumbs/
- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://developer.apple.com/design/human-interface-guidelines/tab-bars
- https://developer.android.com/develop/ui/compose/layouts/adaptive/build-adaptive-navigation
- https://www.w3.org/TR/WCAG22/
- https://lawsofux.com/
