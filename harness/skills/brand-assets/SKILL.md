---
name: brand-assets
description: Logo and brand asset production in the project's own approved look — the brief (only when no strategy document exists), three genuinely different logo directions, SVG masters (mark, wordmark, lockups, mono/reverse), brand colour and type tokens extended with the color-science and typography tools, and exports for splash screens plus social/Open Graph, email-header and banner canvases drawn in the owner-approved marketing concept, via headless-Chrome rendering with size, contrast and font checks. Use when creating or refreshing a logo or visual identity, producing splash, social preview or marketing images, or when app icons and store graphics need a consistent brand source.
---

# Brand Assets

Create the brand source of truth: vector masters, tokens and marketing images that the app icon, splash, store graphics, website and social images all derive from, in **this project's** look.

## Inputs
- The project's strategy: an existing brand or positioning document, or `brand/BRIEF.md` (written only when none exists, from creative-direction's [brief-template](../creative-direction/references/brief-template.md)).
- The creative direction: `brand/direction.json` and its approvals (`direction.py status`). Marketing images need an approved marketing concept.
- Existing assets and theme tokens (`src/theme`, web CSS variables), plus any constraints: a colour to keep, a mark to evolve.

## Workflow
1. **Brief.** Reuse the project's strategy document. Only when none exists, write `brand/BRIEF.md` and have the owner confirm it.
2. **Three logo directions** (when a logo is in scope). Follow [logo-principles](references/logo-principles.md): three different ideas, each shown at 1024 and 32 px, light and dark, as an app-icon tile, with one sentence of rationale. Start each from the construction guide in [templates/logo-master.svg.template](templates/logo-master.svg.template), which holds no shape on purpose. Show them to the owner, who chooses one; don't pick for them.
3. **Masters.** For the chosen direction, write `brand/mark.svg`, `mark-mono.svg`, `mark-reverse.svg`, `wordmark.svg`, `lockup-horizontal.svg` and `lockup-stacked.svg`. Flat shapes and outlined text, no filters.
   - These six are the set. Add another variant only when the owner asks or a named surface needs it.
   - One-off helpers (outlining a font, extracting a glyph) run from a temp folder; don't leave scripts in `brand/`.
4. **Tokens.** Extend the project's existing token file, never a second one:
   - colours with `python .claude/skills/color-science/scripts/palette.py ramp ... --out <tokens file>` (OKLCH ramps mapped to sRGB, contrast table; it never overwrites, `--replace` names a change);
   - fonts with `python .claude/skills/typography/scripts/type_scale.py font ... --out <tokens file>` (local files with hashes and licence evidence, or a stated system font).
   Follow [typography](../typography/SKILL.md) (script coverage, licence, loading) and [color-science](../color-science/SKILL.md) (semantic roles, every theme, CVD, stated colour space). Propose how the app theme and the web CSS use them; hand code changes to `implementor`.
5. **Marketing concepts** (social, Open Graph, email header, banners), when the marketing concept isn't approved: in concept mode, 2–3 concepts per [concept-round](../creative-direction/references/concept-round.md), previewed with `export_svg.py --plan brand/exports.json --preview <dir> --concept <file>`. The owner picks.
6. **Export** the **core set** from [asset-matrix](references/asset-matrix.md), and the on-request rows only when the owner names a use:
   - List every export in `brand/exports.json` and run `python .claude/skills/brand-assets/scripts/export_svg.py --plan brand/exports.json`. The plan is the re-runnable record; don't write export or verify scripts of your own.
   - **Marketing images are canvas entries:** describe each in `brand/canvas.json` (`id`, `size` og / square / story / email-header / WxH, `copy`, optional `layout`, `background`, `slots.image` with `imageLicense`, `slots.logo`) and list it in the plan as `{"canvas": "<id>", "out": "...", "name": "...", "flatten": true}`. Canvas exports need the approved direction and marketing concept and write `brand/runs/marketing/<run>.json`.
   - Each file is written **once, where it's used**: the 2048 mark for `app-icons` in `brand/png/`, the splash image in the app's assets folder, the Open Graph image in the site's `public/`. No second copies, no copies of retired artwork.
   - The script renders into a temporary folder, re-checks every file (size, RGB when flattened, not blank, no `{{...}}` placeholder left), checks text contrast and fonts, and moves files into place only when everything passes. Fix a failure; don't skip it.
7. **Hand off.** Give `icon-creator` the 2048 px mark PNG. Give `store-creative` and `illustrator` the direction and approved concepts (not hex lists).
8. **Usage sheet.** Write `brand/README.md` covering clear space, minimum size, colours, what not to do, and font licences.

## Rules
- **The owner decides** the logo direction and every concept. Never replace a live logo without explicit approval, and never record an approval yourself.
- **Originality:** no stock icons, no traced marks, no resemblance to other brands. Say plainly that a trademark search is the owner's job before launch.
- **Font licences:** only fonts whose licence allows logo and app embedding; record each licence (the font record holds the evidence).
- **Contrast:** text in marketing images meets WCAG at the concept's display width (the export reports PASS / FAIL / REVIEW REQUIRED). Logos and logotypes are branding: WCAG's contrast criteria don't apply to them unless they act as UI, but report the mark's ratio on each background it uses, and meet any target the project set.
- **No binaries in git without asking.** SVG masters, tokens, `canvas.json`, `exports.json`, the run manifests and your HTML sources belong in the repo. PNGs the app or site ships are committed where they're used; `brand/png/` and `brand/.build/` can be gitignored, since the plan regenerates them.
- **Lean by default:** the core set, not every variant at every size. Each extra export needs a named use.
- **`templates/og-image.html` is deprecated** (kept so existing copies keep working). New social, email and banner images are canvas entries; `direction.py migrate` lists copies to move.

## Output
- `brand/` containing the masters, tokens, `canvas.json`, `exports.json`, any HTML sources and the usage README, plus the exports the plan wrote and `brand/runs/marketing/` manifests.
- A report: the direction and concepts chosen (by whom), the files, the check results, the hand-offs, and the open trademark and licence checks.

## References
- [logo-principles](references/logo-principles.md): what makes a mark work, directions, clear space, don'ts.
- [asset-matrix](references/asset-matrix.md): every export, size and format; canvas entries.
- Templates: [logo-master.svg.template](templates/logo-master.svg.template) (construction guide), [og-image.html](templates/og-image.html) (deprecated). Script: [export_svg.py](scripts/export_svg.py).
- Related skills: `creative-direction` (direction, concepts, approvals), `app-icons`, `store-mockups`, `story-art`, `ui-ux`, `typography`, `color-science`.
