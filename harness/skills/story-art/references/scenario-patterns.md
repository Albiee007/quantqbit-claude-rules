# Scenario patterns

A story scene shows **a person in the moment the product helps them**. Start from the feature, then find the moment: who feels the need, where, and what changes when the app is there. The scene must still be true if someone reads the feature list next to it.

## Feature → story moment, by app type

| App type | Feature pillar | Story moment |
|---|---|---|
| Travel / group trips | Shared trip expenses | Friends abroad at night on a lantern-lit street, one checking the phone, everyone relaxed |
| Travel | Foreign currency, trip money | A traveller at an airport exchange counter, the currencies floating above |
| Household / roommates | Recurring shared bills | Flatmates unpacking groceries together in a shared kitchen |
| Couples | Joint spending, fair shares | Two people planning a weekend on the sofa, a laptop between them |
| Personal finance | Budgets, spending insights | A person relaxing at home, glancing at a chart on the phone, everyday icons floating around |
| Productivity | Tasks, planning | Someone closing the laptop at a tidy desk at golden hour, the to-do list done |
| Health / habits | Streaks, tracking | A runner pausing on a morning path, checking progress on a watch |
| Marketplace / delivery | Ordering, tracking | A parcel arriving at a door while the recipient waves from the window |

Rules for the moment:
- **Show relief or delight, not the problem.** The friction can be implied (a bill on the table); the person is calm because the app handles it.
- **The app may appear as a phone in hand with an abstract screen** (shapes, a chart). Never draw a readable UI or another app's UI.
- **Objects carry the feature:** currency symbols for exchange, a donut chart for insights, grocery bags for shared bills. Name exactly which symbols.

## Shot types
- **Wide establishing:** place and group (trips, households). Good for hero backdrops and feature rows.
- **Medium:** one or two people and an object (exchange counter, sofa). Good for feature rows and cards.
- **Close-up on hands and phone:** the action. Hands are the most common defect; prefer a medium shot unless the action needs it.
- **Object still life:** no people (icons, floating symbols). Good for small placements and when casting is sensitive.

Keep one shot type dominant across a set, with at most one change for rhythm.

## Placements and aspect ratios

| Placement | Aspect ratio | Notes |
|---|---|---|
| Web feature row / art card | 4:3 landscape | The default. Export 640 and 1200 px wide |
| Hero backdrop | 16:9 or 21:9 | Keep the subject on one side, leaving calm space for the headline. Could be the LCP image: budget it hard |
| Open Graph / social | 1.91:1 (1200 × 630) | Usually built from `brand-assets` `og-image.html` with the art as a background |
| Store promo / feature graphic | 1024 × 500 (Play) | Made in the `store-mockups` kit, with the art as an `image` object (and a `license` note) |
| Onboarding screen | portrait 3:4 or 9:16 | Subject in the upper two-thirds; the lower third holds the app's copy |

Generate at the provider's closest ratio, then crop in the export step if needed. Never stretch.
