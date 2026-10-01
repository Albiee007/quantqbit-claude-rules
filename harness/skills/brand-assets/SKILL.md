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
   - These six are the set. Add another variant (e.g. a dark-mode mark) only when the owner asks or a named surface needs it.
   - If a one-off helper (outlining a font, extracting an icon glyph) is needed, run it from a temp folder; don't leave scripts in `brand/`.
4. **Tokens.** Write `brand/tokens.json` (colours with contrast notes, fonts with their licences), and propose how the app theme and the web CSS should use them. Hand code changes to `implementor`.
5. **Export** the **core set** from [asset-matrix](references/asset-matrix.md), and the on-request rows only when the owner names a use (a campaign, an email, a site header):
   - List every export in `brand/exports.json` and run `python .claude/skills/brand-assets/scripts/export_svg.py --plan brand/exports.json`. The plan is the re-runnable record; don't write export or verify scripts of your own.
   - Each file is written **once, where it's used**: the 2048 mark for `app-icons` in `brand/png/`, the splash image in the app's assets folder, the OG image in the site's `public/`. No second copies (`brand/splash/` duplicating `png/`), no copies of retired artwork.
   - Social image: copy [templates/og-image.html](templates/og-image.html) into `brand/html/`, fill it in, and add it to the plan with `"flatten"`.
   - The script re-checks every file (size, RGB when flattened, not blank) and checks text contrast on HTML sources. It exits non-zero on any problem: fix it, don't skip it.
6. **Hand off.** Give `icon-creator` the 2048 px mark PNG and the background colour (`app-icons` skill). Give `store-creative` the brand gradient, the accent and the icon for the feature graphic (`store-mockups`). Give `illustrator` the palette hexes for the story-art style bible (`story-art`).
7. **Usage sheet.** Write `brand/README.md` covering clear space, minimum size, colours, what not to do, and font licences.

## Rules
- **The owner decides the direction.** Never replace a live logo without explicit approval.
- **Originality:** no stock icons, no traced marks, no resemblance to other brands. Say plainly that a trademark search is the owner's job before launch.
- **Font licences:** only fonts whose licence allows logo and app embedding; record each licence.
- **Contrast:** the mark reaches at least 3:1 on its backgrounds, and any text at least 4.5:1.
- **No binaries in git without asking.** SVG masters, tokens, the HTML sources and `exports.json` belong in the repo. PNGs the app or site ships are committed where they're used; `brand/png/` can be gitignored, since the plan regenerates it.
- **Lean by default:** make the core set, not every variant at every size. Each extra export needs a named use.

## Output
- `brand/` containing the brief, the six SVG masters, tokens, `exports.json`, the HTML sources and the usage README, plus the exports the plan wrote.
- A report: the direction chosen, the files, the contrast results, the hand-offs, and the open trademark and licence checks.

## References
- [logo-principles](references/logo-principles.md): what makes a mark work, directions, clear space, don'ts.
- [asset-matrix](references/asset-matrix.md): every export, size and format.
- Templates: [logo-master.svg.template](templates/logo-master.svg.template), [og-image.html](templates/og-image.html). Script: [export_svg.py](scripts/export_svg.py).
- Related skills: `app-icons` (the icon set from the mark), `store-mockups` (the feature graphic), `story-art` (illustrations in the brand palette), `ui-ux` (token rules).
