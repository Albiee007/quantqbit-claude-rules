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
| Social / Open Graph | 1200 × 630 | PNG or JPEG, flattened | `templates/og-image.html` | Core (sites) | Export into the site's `public/`. Also the Twitter/X `summary_large_image` |
| Play feature graphic | 1024 × 500 | PNG, no alpha | `store-mockups` kit | Store releases | Made by `store-mockups` (`render --all`), not here |
| Favicon / PWA | 16–512 | PNG / ICO | `app-icons` | Sites and PWAs | Made by `make_icon_set.py` |
| Mark PNGs at other sizes | 1024, 512, 256 px | PNG with alpha | `mark.svg` | On request | For a named surface (docs site, press kit) |
| Variant PNGs | per use | PNG | mono / reverse / lockups / wordmark | On request | Only the variant and size the surface needs, not every variant at every size |
| Email header | 1200 × 300 | PNG, flattened | HTML like og-image | On request | Keep text large enough for mobile mail |
| Promo banner | as the campaign needs | PNG, flattened | HTML like og-image | On request | Web and ads, never inside store screenshots |

## Colour and type tokens
Write the brand tokens once, e.g. `brand/tokens.json` (DTCG format: primary, on-primary, accent, neutral scale, and fonts with their licences). Link the app theme and the web CSS to it, and have the ui-ux skill's token rules consume it. Every asset above uses only these tokens.

## A minimal plan
```json
{"exports": [
  {"src": "mark.svg", "sizes": ["2048x2048"], "out": "png"},
  {"src": "mark.svg", "sizes": ["1024x1024"], "out": "../mobile/assets/splash", "name": "splash-icon"},
  {"src": "html/og-image.html", "sizes": ["1200x630"], "out": "../web/public", "flatten": "#2a1bb0"}
]}
```
Paths are relative to the plan's folder. `export_svg.py` re-checks every file, and checks text contrast on HTML sources (4.5:1, or 3:1 for large text).
