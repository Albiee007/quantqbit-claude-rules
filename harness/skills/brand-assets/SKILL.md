---
name: brand-assets
description: Logo and brand asset production — creative brief, three logo directions, SVG masters (mark, wordmark, lockups, mono/reverse), brand colour and type tokens, and exports for splash screens, social/Open Graph images, email headers and promo banners via headless-Chrome rendering. Use when creating or refreshing a logo or visual identity, producing splash, social preview or marketing images, or when app icons and store graphics need a consistent brand source.
---

# Brand Assets

Create the brand source of truth: vector masters and tokens that the app icon, splash, store graphics, website and social images all derive from.

## Inputs
- The name, the positioning in one sentence, the audience, the markets (global or regional), the personality in 3 adjectives, and the category competitors.
- Existing assets and theme tokens (e.g. `src/theme`, the web CSS variables), plus any constraints: a colour to keep, a mark to evolve.

## Workflow
1. **Brief.** Write `brand/BRIEF.md`: name, positioning, audience, personality, competitors, the clichés to avoid, and where the brand must work (app icon, splash, store, web, social). Confirm it with the owner.
2. **Three directions.** Follow [logo-principles](references/logo-principles.md): three different ideas. Each shows the mark at 1024 and 32 px, light and dark, as an app-icon tile, with one sentence of rationale. Build them as SVG starting from [templates/logo-master.svg.template](templates/logo-master.svg.template). Show them to the owner, who chooses one; don't pick for them.
3. **Masters.** For the chosen direction, write `brand/mark.svg`, `mark-mono.svg`, `mark-reverse.svg`, `wordmark.svg`, `lockup-horizontal.svg` and `lockup-stacked.svg`. Use flat shapes and outlined text, and add no filters.
4. **Tokens.** Write `brand/tokens.json` (colours with contrast notes, fonts with their licences), and propose how the app theme and the web CSS should use them. Hand code changes to `implementor`.
5. **Export** following [asset-matrix](references/asset-matrix.md):
   - `python .claude/skills/brand-assets/scripts/export_svg.py brand/mark.svg --size 2048x2048 --size 1024x1024 --out brand/png`
   - Splash light and dark: the mark on transparency, plus background colours for the Expo splash config.
   - Social image: copy [templates/og-image.html](templates/og-image.html), fill it in, then run `export_svg.py og-image.html --size 1200x630 --flatten "#ffffff" --out public`.
6. **Hand off.** Give `icon-creator` the 2048 px mark PNG and the background colour (`app-icons` skill). Give `store-creative` the brand gradient, the accent and the icon for the feature graphic (`store-mockups`).
7. **Usage sheet.** Write `brand/README.md` covering clear space, minimum size, colours, what not to do, and font licences.

## Rules
- **The owner decides the direction.** Never replace a live logo without explicit approval.
- **Originality:** no stock icons, no traced marks, no resemblance to other brands. Say plainly that a trademark search is the owner's job before launch.
- **Font licences:** only fonts whose licence allows logo and app embedding; record each licence.
- **Contrast:** the mark reaches at least 3:1 on its backgrounds, and any text at least 4.5:1.
- **No binaries in git without asking.** SVG masters and tokens belong in the repo. Large PNG exports can go in a gitignored folder if the owner prefers.

## Output
- `brand/` containing the brief, SVG masters, tokens, PNG exports, the social image and the usage README.
- A report: the direction chosen, the files, the contrast results, the hand-offs, and the open trademark and licence checks.

## References
- [logo-principles](references/logo-principles.md): what makes a mark work, directions, clear space, don'ts.
- [asset-matrix](references/asset-matrix.md): every export, size and format.
- Templates: [logo-master.svg.template](templates/logo-master.svg.template), [og-image.html](templates/og-image.html). Script: [export_svg.py](scripts/export_svg.py).
- Related skills: `app-icons` (the icon set from the mark), `store-mockups` (the feature graphic), `ui-ux` (token rules).
