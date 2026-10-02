# Accessibility Checks for Text

Run these on the representative screens from [context-discovery](context-discovery.md). Record each as passed, failed (with the fix) or not verified (with the reason).

## Pass criteria for every scaling test
- No essential text is clipped, overlapped, truncated or hidden. Controls stay operable and labels stay readable.
- Containers grow; content reflows or scrolls in one direction.
- Hierarchy is still recognizable.
- Non-essential truncation shows an affordance to reach the full text.

## Web
1. **Browser zoom 200% (1.4.4):** zoom to 200% at a desktop viewport. Then also test **text-only zoom** (Firefox: View > Zoom > Zoom Text Only) and a **larger default font size** in browser settings: these catch `px` text and fixed-height boxes that full-page zoom hides.
2. **Reflow 320 CSS px (1.4.10):** set the viewport to 320 px wide (or 1280 px at 400% zoom). No horizontal scrolling except content that needs two dimensions (data tables, maps, code); headings and controls around such content still reflow.
3. **Text spacing (1.4.12):** apply the overrides with a user stylesheet, browser extension or a text-spacing bookmarklet:
   ```css
   * { line-height: 1.5 !important; letter-spacing: 0.12em !important;
       word-spacing: 0.16em !important; }
   p { margin-block-end: 2em !important; }
   ```
   Nothing may be cut off or overlap. Languages that don't use a given property only need to support the ones they use.
4. **Code scan:** grep for `px` in `font-size`, `line-height` with px on fixed-height elements, `vw`-only font sizes, `user-scalable`, `maximum-scale`, `text-size-adjust: none`, `overflow: hidden` plus fixed `height` on text containers.
5. **Automated:** axe or Lighthouse catch meta-viewport zoom blocking and some contrast; they don't verify scaling or spacing. Manual steps above are required.

## Android
1. Settings > Accessibility > Display size and text: **font size to maximum** (200% on Android 14+), and **display size to largest** together.
2. Check every representative screen, dialogs, bottom sheets, tab bars and buttons. Compose previews: `@Preview(fontScale = 2f)` for quick checks; still confirm on a device or emulator.
3. Accessibility Scanner flags clipped text and small targets; it doesn't replace manual review.

## Apple
1. Settings > Accessibility > Display & Text Size > Larger Text: enable **Larger Accessibility Sizes** and set the **maximum**. Also test the **smallest** size.
2. Xcode: Environment Overrides (Dynamic Type) at run time; SwiftUI previews with `.environment(\.dynamicTypeSize, .accessibility5)`.
3. Enable **Bold Text** and check custom fonts respond.
4. Accessibility Inspector audit catches some clipping and Dynamic Type issues.

## React Native
- Test both platforms with the steps above: scaling paths differ. Search for `allowFontScaling={false}`, small `maxFontSizeMultiplier`, `adjustsFontSizeToFit` and fixed `height` on text containers.
- Android 14+ nonlinear scaling: current React Native source converts `fontSize` and `lineHeight` with `TypedValue.applyDimension(COMPLEX_UNIT_SP)`, which applies the nonlinear curve. Older RN versions not verified: test at 200% on an Android 14+ device or emulator.

## Screen readers and transformed text
- Visual transforms (`text-transform: uppercase`, letter spacing, small caps) leave the underlying text intact, which is what screen readers get. Keep source strings in normal case; some screen readers may spell out short all-caps source strings as abbreviations.
- Don't split words into per-letter spans for animation: screen readers can read letters one at a time. If needed, put the full word in an accessible label and hide the spans.
- Text in images or canvas isn't scalable or readable by assistive tech: avoid it for content.
- Set `lang` so screen readers switch pronunciation; mark inline language changes.

## Body defaults are the baseline, not a floor to design down to
- WCAG defines no minimum font size, and `ui-ux` lists platform body defaults (web 16px/`1rem`, Android Body Large 16sp / Body Medium 14sp, iOS Body 17pt), not floors. Treat the platform body default as the reading baseline: essential content stays at or above it; only secondary or meta text goes smaller. Apple's per-platform minimum sizes and M3's smallest label roles are the lowest sizes for any text, not targets.
- Whatever the size, verify at 200% zoom (web) or the largest text size (native).
- Thin or light weights at small sizes read as smaller and lower contrast: raise size or weight.

## Truncation policy
- **Essential information is never truncated:** prices, amounts, dates, errors, instructions, legal text, names in confirmations, form labels.
- Non-essential previews may truncate (list snippets, long titles in cards) only when the full text is one tap or hover away and available to screen readers.
- Prefer wrapping, then layout change (stacking), then truncation, in that order. Never shrink-to-fit essential text below the user's chosen size.

## Contrast
- Text contrast is owned by [color-science](../../color-science/references/accessibility-standards.md) and `ui-ux`. Re-verify contrast after any change in weight or size, since large-text thresholds depend on both, and check every theme.

## Dyslexia and "readable" font claims
- Specialty dyslexia fonts lack strong evidence. Wery & Diliberto (Annals of Dyslexia, 2017; online 2016) found no improvement in reading rate or accuracy with OpenDyslexic vs Arial and Times New Roman for elementary students with dyslexia, and no participant preferred it. Rello & Baeza-Yates (ASSETS 2013, "Good fonts for dyslexia") studied font effects for readers with dyslexia; its findings weren't verified this pass.
- **Heuristic:** what plausibly helps is user control (size, spacing, line length, font choice through the OS or browser), clear sans or serif faces with distinct letterforms, generous spacing and short measure, not a special font imposed on everyone. Don't claim a font "is accessible for dyslexia" in copy or docs.

## Reporting unverifiable checks
State each gap explicitly, for example:
- "Android 200% font scale: not verified, no emulator in this environment."
- "Arabic rendering: not verified, no RTL locale configured yet."
- "Licence for web embedding: not verified, licence text not in repo."
- "CJK line breaking: verified in Chrome only; Safari and Firefox not tested."

## Sources
- [Understanding 1.4.4 Resize Text](sources.md#w3c), [Understanding 1.4.10 Reflow](sources.md#w3c), [Understanding 1.4.12 Text Spacing](sources.md#w3c), accessed 2026-10-02.
- [WCAG 2.2](sources.md#w3c), accessed 2026-10-02.
- [Android 14 nonlinear font scaling](sources.md#platforms) (200% test setting), accessed 2026-10-02.
- [Apple HIG Typography](sources.md#platforms) (Dynamic Type testing, minimum sizes), accessed 2026-10-02.
- [Wery & Diliberto](sources.md#research) (abstract via Semantic Scholar, metadata via Crossref), accessed 2026-10-02.
- [Rello & Baeza-Yates](sources.md#research) (metadata only), accessed 2026-10-02; findings not verified.
- Device menu paths, Compose `@Preview(fontScale)`, Xcode overrides and the screen-reader all-caps behaviour are platform knowledge, not verified against a fetched page in this pass.
