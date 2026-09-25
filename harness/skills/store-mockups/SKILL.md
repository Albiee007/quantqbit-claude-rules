---
name: store-mockups
description: Creative direction and production of app-store screenshots and the Play feature graphic — storyboard, captions, internally consistent demo data, faithful HTML rebuilds of the app's real screens, then headless-Chrome renders at every Play and App Store size with dimension/alpha checks and a contact sheet. Use when creating or refreshing store screenshots, mockups, feature graphics or promo frames, when real captures contain personal or test data, or when new features need to be shown on the store page.
---

# Store Mockups

Produce store frames that **sell the app and are faithful to it**. Each frame is a real screen of the app, rebuilt with clean demo data, framed in a phone with a headline, and rendered at the exact store sizes.

## Fidelity rule (not overridable)
- **Apple 2.3.3 and Google's metadata policy:** screenshots must show the app as it ships. Rebuild real screens using their real labels, layout and tokens. **Never invent a feature, tab or state.**
- **Platform-gated features** appear only in that platform's frames. Premium-only screens appear only where Premium can be bought.
- **No real personal data**, no test artefacts, no third-party logos. See [demo-data-rules](references/demo-data-rules.md).

## Inputs
- Reference captures, e.g. from `mobile-screen-capture`. If there are none, read the screen components and the theme directly.
- The feature inventory and truth table (from `store-listing`, or build one quickly from the code).
- The theme tokens file, e.g. `src/theme/index.ts`, and the icon family the app uses (Ionicons, Material Symbols).
- The positioning, and which features to lead with. Ask the owner if they aren't given.

## Workflow
1. **Storyboard.** Plan 8 frames following [storyboard-and-captions](references/storyboard-and-captions.md): the promise, the differentiator, its payoff, the core action, the resolution, the pillars, breadth. Each frame gets a headline (at most 6 words), a sub-caption (at most 12 words) and the screen it shows. Show it to the owner if the positioning is new.
2. **Ledger.** Write the demo-data ledger first: every figure that appears twice, and how it's derived. Then write `demo-data.js` from it.
3. **Kit.** Run `python .claude/skills/store-mockups/scripts/render_frames.py init <project>/store-assets/mockup-kit`. It copies `frame.html`, `app.css`, `screens.js`, `demo-data.js` and `frames.json` into that folder. Keep the kit in a gitignored folder if the project doesn't want generated assets in git.
4. **Tokens.** Replace the `:root` variables in `app.css` with the app's light-theme tokens. The kit uses Roboto for Android and Inter for iOS, which are close to the system faces. Keep any signature UI the app has, e.g. a raised active tab (`tabBar(..., raised = true)`).
5. **Rebuild the screens** in `screens.js`, one function per screen:
   - Open the real screen component and copy its labels word for word, in its section order.
   - Read sizes off the captures. The kit's logical width of 900 px equals a 1080 px capture scaled to 83%.
   - Use the app's icon family through `I('ion-name|material_name', size, color)`. Set `"icons": "ionicons"` in `frames.json` to use the project's own Ionicons font, which is copied from `node_modules` at render time.
6. **Configure** `frames.json`: `brand` colours (the app's brand gradient and an accent for `<em>`), faint `glyphs`, `sizes`, `frames` (id, screen, head, sub, optional `platforms`) and `featureGraphic`.
7. **Render:**
   - Run `python .claude/skills/store-mockups/scripts/render_frames.py render <kit> --project <app dir>`.
   - Use `--frames 03-x --sizes play-phone` for quick checks while iterating.
   - Every PNG is flattened to RGB and checked for exact size and < 8 MB.
   - The sizes follow [store-specs](../store-submission-precheck/references/store-specs.md).
8. **Visual QA.** Open **every** rendered frame and check:
   - No clipped headline or figure. The FAB, badges and toasts don't cover the numbers the frame is about.
   - The ledger holds across frames. Currency formats are right (¥ has no decimals).
   - The iOS frames have no Android-only UI.
   - Captions are readable at thumbnail size.
   - Fix, re-render, and look again.
9. **Contact sheet.** Run `python .claude/skills/store-mockups/scripts/contact_sheet.py <out>/play/phone --feature <out>/play/feature_graphic_1024x500.png -o <out>/contact-sheet.png`. Send it to the owner for sign-off.

## Rules
- **Iterate one frame at a time;** render every size only at the end.
- **Change the kit's copy, never the harness templates.** The templates in `.claude/skills/store-mockups/templates/` are managed by the harness.
- **Hand captions to the listing.** Keep them identical to the LISTING.md caption table (`listing-copywriter`).
- **Before any upload,** run `store-precheck-auditor` (`check_store_assets.py`) on the output folder.
- **Only real app screens,** even when the owner asks for marketing-only features. If asked for a concept frame of an unreleased feature, label it as a concept and keep it out of the store folders.

## Output
- `<out>/play/{phone,tablet7,tablet10}/NN-name.png`, `<out>/ios/{6.9,6.5}/NN-name.png`, `<out>/play/feature_graphic_1024x500.png`, and `contact-sheet.png`.
- A report listing: the storyboard table, the ledger, each QA fix, the sizes rendered, and any frames left out on a platform, and why.

## References
- [storyboard-and-captions](references/storyboard-and-captions.md): frame order, caption rules, composition lessons.
- [demo-data-rules](references/demo-data-rules.md): personas, ledger, formats, what never to show.
- [worked-example-splitexpenz](references/worked-example-splitexpenz.md): a full real run, including the QA catches.
- Templates: [frame.html](templates/frame.html), [app.css](templates/app.css), [screens.example.js](templates/screens.example.js), [demo-data.example.js](templates/demo-data.example.js), [frames.example.json](templates/frames.example.json).
- Scripts: [render_frames.py](scripts/render_frames.py), [contact_sheet.py](scripts/contact_sheet.py).
