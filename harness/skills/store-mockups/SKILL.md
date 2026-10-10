---
name: store-mockups
description: Creative production of app-store screenshots and the Play feature graphic in the project's own approved look — store concepts (layouts, backgrounds, type, device style, classic frames or a continuous panorama) from the creative direction with draft previews, then storyboard, captions, internally consistent demo data, faithful HTML rebuilds of the app's real screens, and headless-Chrome renders at every Play and App Store size with dimension, contrast and font checks, staged publishing, a run manifest and a contact sheet. Use when creating or refreshing store screenshots, panoramas, mockups, feature graphics or promo frames, when real captures contain personal or test data, or when new features need to be shown on the store page.
---

# Store Mockups

Produce store frames that **sell the app, are faithful to it, and look like this project**. Each frame is a real screen of the app, rebuilt with clean demo data, laid out in the owner-approved store concept, and rendered at the exact store sizes.

## Fidelity rule (not overridable)
- **Apple 2.3.3 and Google's metadata policy:** screenshots must show the app as it ships. Rebuild real screens using their real labels, layout and tokens. **Never invent a feature, tab or state.**
- **Platform-gated features** appear only in that platform's frames. Premium-only screens appear only where Premium can be bought.
- **No real personal data**, no test artefacts, no third-party logos. See [demo-data-rules](references/demo-data-rules.md).

## Where the look comes from
Not from this skill. The project's creative direction (`brand/direction.json`, skill `creative-direction`) and the owner-approved **store concept** (`brand/concepts/store/...`) set the backgrounds, caption type and accent, device style, layouts, feature-graphic layout and motif. The kit holds the app's screens and the words. See [art-direction](references/art-direction.md).
- No direction yet: ask the parent to run the `creative-director` first. You can still build screens and `preview` drafts once a concept exists.
- **A 1.6 kit** (frames.json without `"format"`) still renders exactly as before through the frozen 1.6 engine, with a warning. Migrate it only when asked ([art-direction](references/art-direction.md#migrating-a-16-kit)).

## Inputs
- Reference captures, e.g. from `mobile-screen-capture`. If there are none, read the screen components and the theme directly.
- The feature inventory and truth table (from `store-listing`, or build one quickly from the code).
- The app's theme tokens, e.g. `src/theme/index.ts`, its UI fonts, and the icon family it uses (Ionicons, Material Symbols).
- The positioning, and which features to lead with. Ask the owner if they aren't given.
- `brand/direction.json` and the store concept (`direction.py status` tells whether they are approved).

## Workflow
0. **Concepts** (only when the store concept isn't approved, or the owner wants a new look): in concept mode, propose 2–3 store concepts per [concept-round](../creative-direction/references/concept-round.md), each previewed with `render_frames.py preview <kit> --concept <file>`. Classic or continuous is part of a concept ([continuous-panorama](references/continuous-panorama.md)); ask the owner if they already have a preference. The owner picks; the main session records it.
1. **Storyboard** with [storyboard-and-captions](references/storyboard-and-captions.md): the frames, a headline (at most 6 words) and sub-caption (at most 12 words) each, the screen it shows, and its `layout` and `background` from the concept. Show it to the owner if the positioning is new.
2. **Ledger.** Write the demo-data ledger first: every figure that appears twice, and how it's derived. Then write `demo-data.js` from it.
3. **Kit: one per project, reused on every run.**
   - Look for an existing kit first (a folder with `frames.json` next to `screens.js`) and work in it. A refresh edits that kit; it never starts a second one or copies the sources into an output folder.
   - Only when there is none, run `python .claude/skills/store-mockups/scripts/render_frames.py init <project>/store-assets/mockup-kit [--style continuous]`. It refuses when the project already has a kit.
   - The kit holds only the content files, which are yours to edit and commit: `app.css`, `screens.js`, `demo-data.js`, `frames.json`, an optional `custom-objects.js`, and your own photos in `assets/`.
   - Renders rebuild `<kit>/.build/` every time, previews go to `<kit>/.preview/`, and both are gitignored. Don't copy harness scripts or engine files into the kit, and don't write your own render, check or contrast scripts.
4. **App tokens.** Replace the grey placeholders in `app.css` with the app's light-theme tokens; these are the app's UI, not the store look. List the app's UI font files in `frames.json` `uiFonts` (local files; renders never fetch fonts) and keep signature UI the app really has (e.g. `tabBar(..., raised = true)` only if the app does it).
5. **Rebuild the screens** in `screens.js`, one function per screen:
   - Open the real screen component and copy its labels word for word, in its section order.
   - Read sizes off the captures. The kit's logical width of 900 px equals a 1080 px capture scaled to 83%.
   - Use the app's icon family through `I('ion-name|material_name', size, color)`. `"icons": "ionicons"` uses the project's Ionicons from `node_modules`; `"material"` needs the `material-symbols` package or `"iconsFont"`.
6. **Configure** `frames.json` (format 2, [art-direction](references/art-direction.md)): `sizes` (built-in keys such as `ios-63`, or a size object for any size the stores ask for), `frames` (id, screen, kicker, head, sub, optional `platforms`, `layout`, `background`, `caption.pos`, `device`) and `featureGraphic`. Continuous also sets `objects` (coloured by role names). Check it with `render_frames.py render <kit> --check-only`, which also reports the gates.
7. **Iterate** with drafts: `render_frames.py preview <kit> --frames 01-x --sizes play-phone --project <app dir>`.
8. **Render the release set:** `render_frames.py render <kit> --all --project <app dir>`. It needs the approved direction and store concept, renders every size and the feature graphic into a staging folder, writes the contact sheet (and strips with a seam report for continuous sets), re-checks every file (exact size, RGB, < 8 MB), checks caption contrast and font coverage, runs `check_store_assets.py`, and only then publishes into `<kit>/out/` and writes `brand/runs/store/<run>.json`. A failing check publishes nothing and leaves the previous renders in place.
   - Contrast is judged at the concept's `displayWidth` (default 320 CSS px wide). Captions on a known solid or gradient background get a computed PASS/FAIL; captions over photos, objects or a gradient that fails somewhere are sampled: a low sample fails, a passing one is REVIEW REQUIRED.
   - The sizes follow [store-specs](../store-submission-precheck/references/store-specs.md). With a `store-assets.json` in the kit, its parent or the project, the store check is the `--release` gate; without one it only inspects.
9. **Visual QA.** Open **every** rendered frame: no clipped headline or figure; FABs, badges and toasts don't cover the numbers the frame is about; the ledger holds across frames; currency and dates are right; iOS frames have no Android-only UI; captions read at thumbnail size; every REVIEW REQUIRED caption looked at. Fix, re-render, look again.
10. **Sign-off.** Send the owner `<out>/contact-sheet.png` (and the strips for continuous sets).

## Rules
- **Production follows the approved concept.** Frame layouts and backgrounds come from it; anything else needs the owner's exception (the error prints the command).
- **Iterate one frame at a time with `preview`;** render every size only at the end.
- **One render per kit at a time.** A second render on the same kit is refused (`.build/render.lock`). Never start a parallel agent or workflow on the same screenshots.
- **Rendered PNGs stay out of git** (the kit's `.gitignore` covers `out/`); the run manifests in `brand/runs/` are committed. If the owner wants PNGs versioned, suggest Git LFS.
- **Change the kit's copy, never the harness templates.**
- **A size the harness doesn't list is still yours to make.** Declare it in frames.json `sizes` (`{"key", "size", "platform", "folder"}`) to render it, and as a slot in `store-assets.json` `slots` so the release gate checks it. A `--sizes platform:WxH[:folder]` one-off renders only. Never write a wrapper script or edit the harness size list.
- **Hand captions to the listing.** Keep them identical to the LISTING.md caption table (`listing-copywriter`).
- **Before any upload,** run `store-precheck-auditor` (`check_store_assets.py --release`) on the output folder.
- **Only real app screens,** even when the owner asks for marketing-only features. A concept frame of an unreleased feature is labelled as a concept and kept out of the store folders.

## Output
- `<out>/<folder>/NN-name.png` for each size: `play/{phone,tablet7,tablet10}`, `ios/{6.3,6.9,6.5,ipad13}`, or the folder a project size names; `<out>/play/feature_graphic_1024x500.png`, `contact-sheet.png`, and for continuous sets `strip-android.png` and `strip-ios.png`; `brand/runs/store/<run>.json`.
- A report: the concept used, the storyboard table (with layout and background per frame), the ledger, each QA fix, the sizes rendered, the check results (PASS / FAIL / REVIEW REQUIRED), and any frames left out on a platform, and why.

## References
- [art-direction](references/art-direction.md): format-2 frames.json, layouts and backgrounds, fonts and icons, modes, migrating a 1.6 kit.
- [storyboard-and-captions](references/storyboard-and-captions.md): story structures, caption rules, composition lessons.
- [demo-data-rules](references/demo-data-rules.md): personas, ledger, formats, what never to show.
- [continuous-panorama](references/continuous-panorama.md): the continuous style: rules, strip design, objects, custom objects.
- [worked-example-splitexpenz](references/worked-example-splitexpenz.md): a full real run (1.6 era), including the QA catches.
- Templates: [frame.html](templates/frame.html), [objects.js](templates/objects.js), [props/finance.js](templates/props/finance.js), [app.css](templates/app.css), [screens.example.js](templates/screens.example.js), [demo-data.example.js](templates/demo-data.example.js), [frames.example.json](templates/frames.example.json), [frames.continuous.example.json](templates/frames.continuous.example.json); the frozen 1.6 engine in `templates/legacy-1.6/`.
- Scripts: [render_frames.py](scripts/render_frames.py), [contact_sheet.py](scripts/contact_sheet.py).
- Related skills: `creative-direction` (direction, concepts, approvals), `ui-ux`, `typography`, `color-science`, `store-listing`, `store-submission-precheck`.
