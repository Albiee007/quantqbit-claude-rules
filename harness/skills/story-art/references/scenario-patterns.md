# Scenario patterns

A story scene shows **the moment the product matters** to the people it serves. Start from the feature, then find the moment in the project's own story world. The scene must still be true if someone reads the feature list next to it.

## From feature to scene (a method, not a table)
1. **Feature inventory.** List the pillars from the code and the listing, by their real names.
2. **Story world** (from the illustration concept's `storyWorld`): the setting (where the product's people are), the era and texture of that world, the cast (who, cast to reflect the markets), and the emotional register.
3. **Register.** Choose it from the direction, not by habit: calm, pride, focus, play, belonging, competence, relief, delight, curiosity, anticipation. One register for the set, with room for a quieter or louder frame.
4. **Scene generators.** For each pillar, try two or three and keep the truest:
   - **Moment of need:** the person just before or as the product helps.
   - **Before and after:** the change the feature makes, in one image or a pair.
   - **Metaphor or still life:** objects that carry the idea, no people (useful when casting is sensitive).
   - **Environment only:** the place where the job happens, calm and specific.
   - **Abstract concept:** shapes in the palette that express the feature's effect.
   - **Mascot:** only if the brand already has one.
5. **Check it:** could this image sell a competitor just as well? If so, make it more specific to this product's people and place.

## Rules for the moment
- **The app may appear as a device in hand with an abstract screen** (shapes, a chart). Never a readable UI, never another app's UI.
- **Objects carry the feature:** name exactly which ones and which symbols ("a paper map with three pins", not "travel items").
- **Show the register, not a stock smile.** Calm can be a quiet room; pride can be a finished thing on a table.

## Two contrasting examples (fictional, to show range; not defaults)
| Product | Story world | Pillar | Scene |
|---|---|---|---|
| A garden journal | home gardens, early morning, hands and soil; register: calm pride | seasonal notes | a still life of a notebook, seed packets and a trowel on a sun-bleached bench |
| A dispatch tool for small fleets | depots and vans at night, sodium light; register: competence | live routes | an empty loading bay at dusk, three van tail-lights leaving in a fan |

## Shot types
- **Wide establishing:** place and group. Good for hero backdrops and feature rows.
- **Medium:** one or two people and an object. Good for feature rows and cards.
- **Close-up on hands and an object:** the action. Hands are the most common defect; use it when the action needs it.
- **Object still life:** no people. Good for small placements and when casting is sensitive.

Keep one shot type dominant across a set, with at most one change for rhythm.

## Placements and aspect ratios

| Placement | Aspect ratio | Notes |
|---|---|---|
| Web feature row / art card | 4:3 or 3:2 landscape | Export 640 and 1200 px wide |
| Hero backdrop | 16:9 or 21:9 | Keep the subject on one side, leaving calm space for the headline. Could be the LCP image: budget it hard |
| Open Graph / social | 1.91:1 (1200 × 630) | Usually a `brand-assets` canvas with the art in its `image` slot (`split-image` layout) |
| Store promo / feature graphic | 1024 × 500 (Play) | Made in the `store-mockups` kit, with the art as an `image` object (and a `license` note) |
| Onboarding screen | portrait 3:4 or 9:16 | Subject in the upper two-thirds; the lower third holds the app's copy |

Generate at the provider's closest ratio, then crop in the export step if needed. Never stretch.
