# Brand asset matrix

Export everything from the SVG or HTML masters, never by resizing PNGs. Store sizes come from the `store-submission-precheck` skill's `references/store-specs.md` (mobile projects), and app icons from the `app-icons` skill.

**Core** rows are made on every brand job. **On request** rows are made only when the owner names the use: a campaign, an email, a site header, a dark-mode surface. List every export in `brand/exports.json` and run `export_svg.py --plan brand/exports.json`, so the set is one re-runnable command. Write each file once, where it is used.

| Asset | Size | Format | Source | When | Notes |
|---|---|---|---|---|---|
| Mark (master) | vector, 1024 viewBox | SVG | `brand/mark.svg` | Core | Plus `mark-mono.svg` and `mark-reverse.svg` |
| Wordmark | vector | SVG | `brand/wordmark.svg` | Core | Text converted to outlines. Licence check on the font |
| Horizontal lockup | vector | SVG | `brand/lockup-horizontal.svg` | Core | Mark + wordmark, clear space = the height of the mark's inner shape |
| Stacked lockup | vector | SVG | `brand/lockup-stacked.svg` | Core | For square spaces |
| Mark PNG | 2048 px | PNG with alpha | `mark.svg` | Core | Feeds `app-icons` (`brand/png/`) |
| Splash image (light) | 1024 × 1024 mark on transparency | PNG | `mark.svg` | Core (apps) | Export straight into the app's assets folder; Expo `expo-splash-screen` `image` + `backgroundColor` |
| Splash image (dark) | 1024 × 1024 | PNG | `mark-reverse.svg` | Core if the app has a dark splash | `dark: { image, backgroundColor }` |
| Social / Open Graph | 1200 × 630 (`og`) | PNG, flattened | canvas entry (`brand/canvas.json`) | Core (sites) | Export into the site's `public/`. Also the Twitter/X `summary_large_image`. Keep text inside the central 1080 × 540 |
| Play feature graphic | 1024 × 500 | PNG, no alpha | `store-mockups` kit | Store releases | Made by `store-mockups` (`render --all`), not here |
| Favicon / PWA | 16–512 | PNG / ICO | `app-icons` | Sites and PWAs | Made by `make_icon_set.py` |
| Mark PNGs at other sizes | 1024, 512, 256 px | PNG with alpha | `mark.svg` | On request | For a named surface (docs site, press kit) |
| Variant PNGs | per use | PNG | mono / reverse / lockups / wordmark | On request | Only the variant and size the surface needs, not every variant at every size |
| Email header | 1200 × 300 (`email-header`) | PNG, flattened | canvas entry, often `logo-band` | On request | Keep text large enough for mobile mail |
| Promo banner | as the campaign needs (`WxH`, `square`, `story`) | PNG, flattened | canvas entry | On request | Web and ads, never inside store screenshots |

## Colour and type tokens
Write the brand tokens once, e.g. `brand/tokens.json` (DTCG format: primary, on-primary, accent, neutral scale, and fonts with their licences). Link the app theme and the web CSS to it, and have the ui-ux skill's token rules consume it. Derive the palette with [color-science](../../color-science/SKILL.md) and the fonts with [typography](../../typography/SKILL.md). Every asset above uses only these tokens.

## Canvases (`brand/canvas.json`)
Social, Open Graph, email-header and banner images are drawn by the shared canvas page in the approved marketing concept's look: its backgrounds, caption type and accent, layouts (`type-start`, `type-center`, `split-image`, `logo-band`), logo and motif. The file holds only what changes per image:
```json
{"schemaVersion": 1, "assets": [
  {"id": "og", "size": "og", "copy": {"kicker": "Fernway", "head": "Notes that <em>grow</em>", "sub": "Every bed, every season"}},
  {"id": "launch", "size": "1600x900", "layout": "split-image", "background": "soil",
   "copy": {"head": "Spring is here"}, "slots": {"image": "public/art-spring-1200.webp"}, "imageLicense": "own illustration, story-art run 2026-10"},
  {"id": "email", "size": "email-header", "layout": "logo-band", "copy": {}, "slots": {"logo": "brand/lockup-horizontal.svg"}}
]}
```
A layout or background outside the concept is refused until the owner approves the exception the error names.

## A minimal plan
```json
{"exports": [
  {"src": "mark.svg", "sizes": ["2048x2048"], "out": "png"},
  {"src": "mark.svg", "sizes": ["1024x1024"], "out": "../mobile/assets/splash", "name": "splash-icon"},
  {"canvas": "og", "out": "../web/public", "name": "og-image", "flatten": true}
]}
```
Paths are relative to the plan's folder. `export_svg.py` renders into a temporary folder and re-checks every file before moving it into place. Canvas text is checked at the concept's display width (computed PASS/FAIL where the background colour is known, sampled REVIEW REQUIRED or FAIL elsewhere) along with font coverage; HTML pages of your own are sampled at their own size. Drafts: `export_svg.py --plan brand/exports.json --preview <dir> [--concept <file>]`.
