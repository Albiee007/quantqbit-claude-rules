# Art direction in the mockup kit (format 2)

A format-2 kit carries the app's screens and the words; the look comes from the owner-approved store concept. `render_frames.py` resolves the concept (token values, fonts, motif) into `.build/direction.generated.js`, and the engine (`frame.html` with the shared `artdir.js`) draws only what that says.

## frames.json
```jsonc
{
  "format": 2,
  "artDirection": { "family": "store" },      // the direction is found at or above the kit: brand/direction.json
  "style": "classic",                         // or "continuous" (references/continuous-panorama.md)
  "out": "out",
  "icons": "material",                        // "ionicons" (from node_modules) | "material" (material-symbols package or iconsFont) | "none"
  "iconsFont": "node_modules/material-symbols/material-symbols-rounded.woff2",   // optional
  "uiFonts": [                                 // the app's own UI fonts for the rebuilt screens (optional; else system fonts)
    { "family": "Roboto", "source": "local", "platform": "android",
      "files": [{ "path": "node_modules/@expo-google-fonts/roboto/Roboto_400Regular.ttf", "weight": 400 }] }
  ],
  "sizes": ["play-phone", "ios-63", "ios-69"],  // size keys, or a size of the project's own (below)
  "frames": [
    { "id": "01-home", "screen": "home", "kicker": "New", "head": "Your week, <em>planned</em>", "sub": "Lists, reminders and notes together",
      "layout": "split-left", "background": "dawn" },          // both optional: default from the concept
    { "id": "02-list", "screen": "activity", "head": "...", "sub": "...", "platforms": ["android"] }
  ],
  "featureGraphic": { "screen": "home", "title": "Fernway", "tagline": "...", "sub": "...", "icon": "assets/icon-512.png" },
  "props": ["finance"],                       // optional prop packs for continuous objects
  "objects": []                               // continuous only
}
```
- **Sizes.** The built-in keys are `play-phone`, `play-tab7`, `play-tab10`, `ios-63`, `ios-69`, `ios-69-1320`, `ios-65` and `ios-ipad13` (from `store-submission-precheck/references/store-slots.json`).
  - A size the catalog lacks goes in as an object: `{"key": "ios-61", "size": "1179x2556", "platform": "ios", "folder": "ios/6.1"}`. `platform` is `ios`, `play` or `android`. `folder` is optional (default `<play|ios>/<WxH>`) and must stay inside that store's folder. Each side is 320–7680 px.
  - Two sizes may not write the same folder at different dimensions (`ios-69` and `ios-69-1320` both use `ios/6.9/`: pick one).
  - The release gate only checks folders it knows. Declare the same folder as a slot in `store-assets.json` (`"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1179x2556"]}}`), or `render --all` fails it as `unknown-folder` when the project has a `store-assets.json`.
  - For a one-off look, `--sizes ios:1179x2556:ios/6.1` renders a size without touching frames.json. It renders only; it declares no checker slot.
  - Never write a wrapper script around `render_frames.py` for a missing size.
- Copy is data: it is escaped, and only `<em>…</em>` survives, drawn in the concept's accent style.
- Placeholder copy (`REPLACE`) is a warning in previews and an error in production.
- Paths are relative to `--project` (the app folder) and may not leave it.

## Layouts (store frames)
| Layout | What it does |
|---|---|
| `caption-top` | caption across the top, device below |
| `caption-bottom` | device from the top, caption at the foot |
| `split-left` / `split-right` | caption in a side column, device on the other side, centred vertically |
| `inset` | caption on top, device on a tinted panel (the background's `panel` colour) that crops it at the bottom |

Feature graphic (1024 × 500): `split-device-right`, `split-device-left`, `centered-type` (no device).
A frame may use any layout and background the concept lists. Anything else is refused until the owner approves the exception the error names (`direction.py approve --gate exception --scope "store:frame:<id>:layout=<x>"`).

## Backgrounds, type, device, motif
All from the concept: `solid` or `linear` (interpolated in OKLab by default) backgrounds, each with its own caption colours; caption fonts (local files from the token file's font records, or stated system fonts), weights, tracking, case and accent style (`color`, `underline`, `highlight`, `none`); device `frame` or `frameless` with a radius and shadow; an optional motif from the direction. Mesh, grain and multi-device layouts are not offered yet.

## Checks in `render --all`
- **verify:** exact size, RGB, < 8 MB; the feature graphic present at its size, RGB, < 8 MB.
- **contrast:** each caption run at the concept's `displayWidth` (default 320 CSS px). Known solid backgrounds and highlights: computed PASS/FAIL. Gradients: computed against every sample of the gradient; if that bound fails, or something is drawn behind the text, the rendered backdrop is sampled (low: FAIL; otherwise REVIEW REQUIRED).
- **text:** every caption character must be drawn by the requested family, weight and style (from the font file itself for local fonts, and by comparing browser fallbacks for system fonts), and no caption may run off the canvas or across a seam; either fails. Right-to-left copy and long translations are not checked automatically: preview them and look.
- **store:** `check_store_assets.py` on the staged set. With a `store-assets.json` (looked up in the kit, then its parent, then the project) it is the `--release` gate, so required slots, project slots and `unknown-folder` all block publishing. Without one it runs in inspect mode, and the console and run manifest say "inspect only".
A FAIL publishes nothing. REVIEW REQUIRED publishes, and the run manifest says `review-required`.

## Modes
- `render` on a format-2 kit is production: it needs the approved direction and store concept, and refuses with the reasons otherwise. `--check-only` validates and reports the gates.
- `preview` renders a draft with the selected concept or `--concept <file>`, in a temporary copy of the kit, into `<kit>/.preview/<run>/` (or `--out`), with a contact sheet. It never touches the kit, `.build/` or `out/`.
- A 1.6 kit renders with `render` exactly as in 1.6 (same engine files, same pixels), plus a warning.

## Migrating a 1.6 kit
1. `direction.py migrate` lists what predates 1.7.
2. The creative-director writes a direction and the owner approves it; a store concept round follows. Put anything of the old look the owner wants to keep in the direction's `keep`.
3. In `frames.json`: add `"format": 2` and `"artDirection": {"family": "store"}`; rename `"layout": "continuous"` to `"style": "continuous"`; remove `brand` and `background` (the concept supplies them); per frame, replace `caption.tone` with a `background` and choose a `layout`; continuous objects take role names for colours (`"accent"`, `"ink"`), and coins, chips, receipts and calendars need `"props": ["finance"]` (their colours now follow the roles).
4. Put the app's UI fonts in `uiFonts`, and give `material` icons a local font.
5. `preview`, then `render --check-only`, then `render --all`.
