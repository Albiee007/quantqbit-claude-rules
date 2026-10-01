# Hierarchy and Measure

Derive the scale from evidence gathered in [context-discovery](context-discovery.md). Numbers below marked **heuristic** are starting points to test, not rules. Numbers marked **normative** come from WCAG.

## Deriving a scale
1. **Count levels needed.** List the distinct text roles on representative screens: display or hero, page title, section heading, subsection, body, secondary or meta, caption or label, and code or data if present. Most product UIs need 5–8 sizes; dense tools often fewer.
2. **Fix the body size first,** from audience and reading context. On the web, start from the user's default (`1rem`) for continuous reading and only go larger with evidence (older audience, distance viewing). WCAG sets no minimum font size. Treat the platform body default as the reading baseline (web `1rem`/16px, Android Body Large 16sp or Body Medium 14sp, iOS Body 17pt; see `ui-ux`); go smaller only for secondary or meta text (metadata, dense tables), never for essential content, and verify at 200% zoom or the largest text size.
3. **Set the range:** smallest and largest size per viewport class. Small viewports compress the top of the scale; large headings on phones waste space and wrap badly.
4. **Fill the steps** with the fewest sizes that keep adjacent levels distinguishable when combined with weight and spacing.
5. **Round** to values that render cleanly (whole px equivalents or 0.125rem steps) and express them in `rem`, `sp` or text styles.

### Modular scale (one option)
A geometric ratio between steps gives coherence but is not required. A hand-tuned scale that fits real content is equally valid. If you use a ratio, choose by context (all **heuristic**):
- **Dense data, dashboards, admin tools:** tight, about 1.067–1.2. Few levels; rely on weight and color for hierarchy.
- **General product UI:** about 1.125–1.25.
- **Editorial, marketing, landing pages:** about 1.25–1.5, wider display sizes on large screens.
- **Wide viewport range:** use different ratios per viewport (tighter on small screens), implemented with fluid type below.

### Hierarchy cues besides size
- Weight (one step heavier is often enough), color or emphasis tokens, space above vs below (more space above a heading than below ties it to its content), case and letter spacing for small labels, position and grouping.
- Test hierarchy by squinting or blurring the screenshot: levels should stay distinct.

## Measure
- **Prose: about 45–75 characters per line (heuristic,** common typographic guidance; Baymard reports long lines feel overwhelming in e-commerce testing and suggests 50–80). Implement with `max-inline-size` in `ch` or `em` on the text container, not on the page.
- **Normative AAA:** WCAG 1.4.8 Visual Presentation requires a mechanism to keep blocks of text to 80 characters or fewer, 40 for CJK. It's AAA: treat as a ceiling to design under, not an AA gate.
- UI labels, table cells and cards aren't prose; size them by content and allow wrapping.
- CJK measure is counted in characters of the full-width grid ([multilingual-and-rtl](multilingual-and-rtl.md)).

## Line height
- Unitless in CSS (`line-height: 1.5`) so it scales with the font; `em` or `sp` on native. Never a fixed px/dp line height on a fixed-height box.
- **Heuristic ranges:** body prose about 1.4–1.7; UI text about 1.25–1.5; headings about 1.05–1.3 (tighter as size grows).
- Increase it for: large x-height faces, long measures, scripts with tall marks or stacks (Devanagari, Thai, Arabic with vowel marks, Vietnamese stacked diacritics). Decrease for: short lines, large display sizes.
- Check that heading line height still clears ascenders and descenders when a heading wraps to two lines.

## Paragraph and block spacing
- Paragraph spacing at least about 0.75–1× the font size (heuristic). Use margin on one side consistently (block-end).
- Spacing tokens derive from the type scale or the 4/8 spacing scale; don't invent a third rhythm.

## Surviving WCAG 1.4.12 overrides (normative AA)
Users may set line height 1.5×, paragraph spacing 2×, letter spacing 0.12× and word spacing 0.16× the font size. Content must not be lost or overlap. Design for it:
- No fixed heights or `overflow: hidden` on text containers; use `min-block-size`.
- Buttons, chips and tabs grow with their label.
- Truncation (`text-overflow: ellipsis`, line clamp) only on non-essential text, with the full text reachable.

## Alignment and case
- Start-align body text (logical `text-align: start`). Don't justify body text on the web: rivers and uneven spacing, worse without hyphenation; WCAG 1.4.8 (AAA) also asks for unjustified text.
- Center only short blocks (2–3 lines).
- No all-caps sentences. For short caps labels, use `text-transform: uppercase` (language-aware when `lang` is set) and add slight letter spacing (about 0.05em, heuristic). Note that some screen readers may spell out short all-caps source text: keep the source in normal case.
- Never apply letter spacing to cursive scripts such as Arabic; it breaks joining.

## Fluid type (web)
- `clamp(min, preferred, max)` where `preferred` mixes `rem` and `vw`, for example `clamp(1.5rem, 1.1rem + 1.8vw, 2.5rem)`. The `rem` term keeps text responsive to zoom and user font settings.
- Never pure `vw` font sizes: WCAG lists viewport-unit text sizing as a failure of 1.4.4 (F94).
- Check that the max/min ratio between smallest and largest viewport doesn't stop 200% zoom from roughly doubling the text. Large `vw` coefficients can cap growth.
- Container queries (`@container`, `cqi` units) let a component scale type to its container instead of the viewport; keep a `rem` term there too.

## Mapping to platform systems
Map project roles to platform roles instead of inventing parallel names:

| Project role | Material 3 role | Apple text style |
|---|---|---|
| Hero / display | Display L/M/S | Large Title |
| Page title | Headline L/M | Title 1 |
| Section heading | Headline S / Title L | Title 2 / Title 3 |
| Emphasized label, list title | Title M/S | Headline |
| Body | Body L / Body M | Body |
| Secondary text | Body S | Callout / Subheadline |
| Meta, caption | Label M/S / Body S | Footnote / Caption 1 / Caption 2 |
| Button, tab, chip label | Label L | Body or Headline (system controls set their own) |

Baseline sizes: M3 in [material3](../../ui-ux/references/material3.md), Apple in [apple-hig](../../ui-ux/references/apple-hig.md). The mapping is guidance: project tokens may redefine values but should keep the roles so platform scaling applies.

## Sources
- [WCAG 2.2](sources.md#w3c): 1.4.4, 1.4.8, 1.4.10, 1.4.12, accessed 2026-10-02.
- [Understanding 1.4.4 Resize Text](sources.md#w3c) (failure F94, viewport units), accessed 2026-10-02.
- [Understanding 1.4.8 Visual Presentation](sources.md#w3c) (80/40 characters, justification), accessed 2026-10-02.
- [Understanding 1.4.12 Text Spacing](sources.md#w3c), accessed 2026-10-02.
- [CSS Text 3](sources.md#w3c) (language-sensitive `text-transform`), accessed 2026-10-02.
- [Baymard: line length](sources.md#research), accessed 2026-10-02.
- [Material Components Android typography doc](sources.md#platforms) (M3 roles and baseline sizes), accessed 2026-10-02.
- [Apple HIG Typography](sources.md#platforms) (via the developer documentation data endpoint), accessed 2026-10-02.
- Ratio ranges, line-height ranges and the screen-reader note on all-caps are heuristics from common practice, not from a fetched standard.
