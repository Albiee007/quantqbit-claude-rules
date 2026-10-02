---
name: story-art
description: Story and scenario illustration for a product in its own approved style — illustration concepts from the creative direction (render style from a broad vocabulary, palette from the project's tokens, light, story world), a context pack from the code, listing and brand, one storyboarded scene per real feature pillar, a style bible locked from the approved concept with a negative list, image generation through whichever provider the session has (Canva MCP documented as the default, Figma Weave and API-key providers outlined), a contact-sheet review gate with owner approval, full-resolution retrieval, AVIF/WebP web export within byte budgets merged into the site manifest, integration guidance and recorded provenance. Use when a website, store listing, onboarding flow or campaign needs illustrations, hero or feature-row artwork, or story/scene art that shows people using the product, or when an existing illustration set needs a new or regenerated image.
---

# Story Art

Make illustrations that tell the product's story: real people (fictional, inclusive) in the moment the app helps them. Each image maps to a real feature, shares one locked style with the rest of the set, and ships only after the owner approves it.

## Inputs
- The product: the feature inventory (read it from the code), the store listing (e.g. `store-assets/*/LISTING.md`) and its claims guardrails file, and the positioning in one sentence.
- The cast: demo-data personas and names (e.g. the `store-mockups` kit's `demo-data.js`), and the markets the product serves.
- The direction: `brand/direction.json` and the approved illustration concept (`direction.py status`; `direction.py resolve illustration`). Without a direction, ask the parent to run the `creative-director`; the theme tokens alone don't settle a style.
- The placements: where each image goes (web feature row, hero backdrop, Open Graph, store promo, onboarding) and its aspect ratio. Ask the parent if no placement is named.
- The generator available in this session (see [providers](references/providers.md)).

## Workflow
0. **Context pack.** Gather the inputs above, read-only, and write them to `out/story-art/<date>/plan.md`. This one file is the set's record: context, storyboard, style bible, prompts, the per-image provenance table and the approvals. Add `out/` to the project's `.gitignore` if it isn't there.
1. **Concept** (only when the illustration concept isn't approved, or the owner wants a new style): in concept mode, 2–3 style bibles from different families in [style-vocabulary](references/style-vocabulary.md), each with one sample scene prompt, per [concept-round](../creative-direction/references/concept-round.md). The owner picks; the main session records it.
2. **Storyboard.** One scene per feature pillar, 4–8 scenes per set. Write each as:
   - **who** (fictional, a cast that reflects the markets), **where**, **the moment of need**, **the emotion**, **what the app does in that moment**;
   - the real feature it maps to, by name from the code. A scene the product can't back is cut, not softened.
   - Build scenes from the concept's story world with [scenario-patterns](references/scenario-patterns.md) (a method: register, scene generators, shot types, aspect ratios).
3. **Style bible, locked once per set.** Take it from the approved concept (`direction.py resolve illustration`): render style, palette hexes (token references, chosen with [color-science](../color-science/SKILL.md) so overlaid UI text keeps its contrast), lighting, texture, background and aspect ratio. Add the shared negative list from [prompt-template](references/prompt-template.md) plus the concept's negatives. Run `direction.py signals out/story-art/<date>/plan.md` and discuss any signal the direction doesn't keep. Never change the bible mid-set; a change means a new concept and a new set.
4. **Prompts.** Build each prompt from the template: style bible + scene. Name exact symbols and objects; a vague noun gets a guessed glyph (asking for "baht ฿" once produced a ₿-like mark).
5. **Generate** with the session's provider, following [providers](references/providers.md):
   - One image at a time. On a quota or cooldown error, wait and retry; never loop.
   - Record the provider, the media or job ID, the prompt and the date in the plan's table as each image arrives.
6. **Review gate.**
   - Save the images (preview size is fine here) and run `python .claude/skills/story-art/scripts/export_art.py sheet <dir> out/story-art/<date>/contact-sheet.png --glob '*.png'`.
   - Open **every** image and check it against [review-checklist](references/review-checklist.md): symbols and glyphs, hands and faces, stray text, brand fit, contrast with the page behind it.
   - Hand the contact sheet and your findings to the parent for **owner approval**. A sub-agent cannot ask the owner itself.
   - Regenerate rejected images with a corrected prompt. One regeneration round is included; ask before any more.
7. **Full resolution.** Previews are often thumbnails. Retrieve the approved images at native size by the provider's route in [providers](references/providers.md). For Canva: a scratch copy of a design only, never the owner's own designs; commit only that copy; export PNG at "pro" quality; download the signed URLs at once.
8. **Web export.**
   - Put the full-size PNGs in one source folder, named by scene (`trip.png`, `roommates.png`).
   - Run `python .claude/skills/story-art/scripts/export_art.py export <src> <site public folder> --prefix art --widths 640,1200 --budget 1200=120000,640=50000 --manifest <site manifest.json>`.
   - It writes `art-<scene>-<width>.{avif,webp}`, steps quality down until each file fits its budget, keeps AVIF under 80% of the WebP size (WebP only when Pillow has no AVIF), and merges the entries into the manifest without dropping other keys. It exits non-zero and writes nothing if a budget can't be met: fix the source (crop, simplify) or ask for a bigger budget, never skip the check.
   - **Integration gotcha:** if the site has its own render script that rewrites the manifest, make it keep the `art-*` entries, or the next site render drops them.
9. **Integrate (guidance; hand the code to `implementor`).**
   - `<picture>` with AVIF then WebP sources, `srcset` 640w/1200w, explicit `width` and `height` from the manifest, `loading="lazy"` below the fold. Never the LCP image unless it is the hero.
   - Decorative art gets `alt=""`. Art that carries meaning gets real alt text describing the moment.
   - Choose the layout with the direction and the page, not by habit: a full-bleed band, a rounded card, a cut-out on the page colour, art beside the copy, art masked by the direction's motif, a small spot illustration inline, or a card with a phone overlapping a corner. Art placed behind a phone mockup gets hidden: keep the subject clear of any overlap.
   - A tilted phone with negative offsets caused horizontal scroll at 640 and 1100 px: keep offsets inside the gutter and clip the section (`overflow-x: clip`). Check at 360, 640, 1100 and 1440 px.
10. **Provenance.** Close `plan.md` with one row per shipped image: file, scene, prompt, provider, media ID, date, approved by and when. Images without an approval row don't ship.

## Rules
- **Owner approval before anything ships,** and before any publish or upload outside the generator. The parent relays the approval; record it.
- **Truthful scenes.** Every scene maps to a feature that exists. The listing's claims guardrails apply to images too: no implied features, partners or results.
- **Fictional people only.** No likenesses of real or famous people, no real users' photos, no recognisable staff. Cast inclusively across age, ethnicity, gender and ability.
- **No brands or trademarks:** no logos, no other apps' UI, no real banknote designs, no crypto glyphs unless the product deals in them.
- **No text in images.** Captions and headlines stay in HTML, where they can be translated and read by screen readers.
- **Quota:** 4–8 images per set, one at a time. Ask before a second regeneration round.
- **Keys from the environment only** for API-key providers. Never write a key to a file, a log or the plan.
- **Lean output:** `out/story-art/<date>/` holds `plan.md`, the contact sheet and the source PNGs, and stays gitignored. The web files are written once, into the site's public folder. Don't write export, resize or check scripts of your own; `export_art.py` covers them.
- **Never edit the owner's designs** in a design tool. Work in a scratch copy, and tell the owner it exists so they can delete it.

## Output
- `out/story-art/<date>/plan.md` (context pack, storyboard, style bible, prompts, provenance), `contact-sheet.png` and the full-size PNGs.
- `<site public>/art-<scene>-{640,1200}.{avif,webp}` and the merged manifest.
- A report: the storyboard table (scene → feature → placement), the style bible, the per-image table (file, provider, media ID, review result, approval), the export summary from `export_art.py`, the integration notes for `implementor`, and the open items (pending approvals, scratch designs to delete).

## References
- [providers](references/providers.md): Canva MCP step by step with its gotchas, Figma Weave and API-key providers, how to detect what's available.
- [style-vocabulary](references/style-vocabulary.md): render styles by family, with prompt phrases, the moods they suit and what to watch for. No default.
- [scenario-patterns](references/scenario-patterns.md): from feature to scene in the project's story world; shot types, placements and aspect ratios.
- [prompt-template](references/prompt-template.md): the style-bible and scene templates, the negative list, two contrasting worked style bibles.
- [review-checklist](references/review-checklist.md): reject criteria, accessibility and performance budgets.
- Script: [export_art.py](scripts/export_art.py).
- Related skills: `creative-direction` (direction, concepts, approvals), `brand-assets` (tokens and palette), `store-mockups` (personas, demo data), `store-listing` (claims guardrails), `ui-ux` (contrast, alt text), `color-science` (palette lock), `seo` (LCP, image weight).
