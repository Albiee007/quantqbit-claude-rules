# Accessibility Standards for Color

Two parts, never mixed: **normative WCAG 2.2** (conformance) and **supplementary** methods (informative). Report them in separate sections.

## Part 1. Normative: WCAG 2.2 (W3C Recommendation, 12 Dec 2024)

### Success criteria
- **1.4.1 Use of Color (A):** color is never the only visual means of conveying information, indicating an action, prompting a response or distinguishing an element. Add text, icon, pattern or shape. Inline links distinguished from body text only by color: sufficient technique G183 (updated 27 Jul 2026) checks ≥ 3:1 between link color and surrounding text color; the link text still needs 4.5:1 against its background. G183 no longer tests a hover/focus cue; an underline remains the simplest and most robust cue.
- **1.4.3 Contrast (Minimum) (AA):** text and images of text ≥ **4.5:1**; large-scale text ≥ **3:1**. Exempt: inactive (disabled) components, pure decoration, text not visible to anyone, incidental text in pictures, logotypes.
- **1.4.6 Contrast (Enhanced) (AAA):** ≥ **7:1**, large text ≥ **4.5:1**. Good practice, out of AA scope.
- **1.4.11 Non-text Contrast (AA):** ≥ **3:1** against adjacent color(s) for visual information needed to identify UI components and their states, and for parts of graphics needed to understand the content. Inactive components exempt. For gradients, test the least-contrasting part.
- **2.4.7 Focus Visible (AA):** keyboard focus indicator is visible.
- **2.4.11 Focus Not Obscured (Minimum) (AA):** the focused component isn't entirely hidden by author content.
- **2.4.13 Focus Appearance (AAA):** indicator area at least a 2 CSS px thick perimeter, and ≥ 3:1 contrast between the same pixels focused vs unfocused. Good practice; its contrast-of-change idea is a useful target.

### Large-scale text
At least 18 point, or 14 point bold (CJK equivalent). In CSS px (1pt = 1.333px): about **24 px** regular, **18.66 px** bold. Use the computed size from the user agent.

### Relative luminance and contrast ratio
For sRGB, with channels as 0–1 (`c = C8bit / 255`):
1. Linearize each channel: `c ≤ 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055)^2.4`.
2. `L = 0.2126·R + 0.7152·G + 0.0722·B` (linear values).
3. Contrast ratio `= (L1 + 0.05) / (L2 + 0.05)`, L1 the lighter. Range 1–21.

Notes:
- **Threshold:** the current WCAG 2.2 text uses **0.04045**. Before May 2021 the definition used 0.03928 (from an older sRGB draft); W3C notes the change has no practical effect for these guidelines. Use 0.04045, and don't flag tools that use 0.03928 as wrong.
- **No rounding:** compare the unrounded ratio. 4.499:1 fails 4.5:1; 2.999:1 fails 3:1. Report two decimals, truncated, never rounded up.
- **After compositing:** translucent colors are measured after compositing on their actual backdrop the way the renderer does it (see [rgb-and-compositing](rgb-and-compositing.md)). Test each backdrop.
- **Measure colors, not screenshots:** use the specified foreground/background values from styles, not anti-aliased pixels. Thin or unusual fonts read lighter: exceed the minimum for them.
- **Wide-gamut colors:** WCAG's formula is defined for sRGB. For P3 or other values, convert to sRGB for the check (state the mapping) and also check the sRGB fallback.
- **Themes and states:** every pair, in every theme the project supports (light, plus dark and high-contrast when in scope), every state.

### Testing
- Token-pair matrix: compute every text/surface and boundary/adjacent pair from the token source.
- Automated: axe-core / Lighthouse catch many text-contrast failures but miss composited, image and state cases.
- Manual: hover, focus, pressed, selected, error, disabled; forced colors; zoomed text.

## Part 2. Supplementary (not conformance)
Informative only. Never report these as pass/fail against WCAG, never use them to excuse a WCAG failure, never present them as a requirement unless the project has adopted them in addition to WCAG.

- **APCA (Accessible Perceptual Contrast Algorithm):** polarity-aware lightness-contrast model with Lc values and font size/weight lookups. Its own docs describe it as a candidate for WCAG 3. The **WCAG 3.0 Working Draft (10 Sep 2026)** states its contrast algorithm is yet to be determined and does not name APCA. Use APCA to tune pairs that pass WCAG but read poorly (often dark themes, thin type); quote Lc values only from the APCA docs, labeled informative.
- **Adopting APCA in addition:** if a team adopts APCA, record the adopted Lc targets in a decision record that names the APCA version, report Lc side by side with WCAG ratios, and keep WCAG as the conformance result. APCA never replaces WCAG 2.2.
- **ΔE for distinguishability:** useful for checking that categorical or status colors are distinct from each other (state the formula; [perceptual-spaces](perceptual-spaces.md)). It is not contrast and says nothing about legibility.
- **CVD simulation:** checks whether meaningful pairs survive protan/deutan/tritan vision. A "passes simulation" result doesn't satisfy 1.4.1; redundant cues do.
- **Platform guidance beyond WCAG:** Apple HIG suggests striving for 7:1 for custom colors in small text and providing increased-contrast variants. Record as platform guidance, separate from WCAG results.

## Reporting template
```markdown
## WCAG 2.2 conformance (normative)
| Element / pair | Theme | State | Fg (composited) | Bg | Ratio | Required | Result |
|---|---|---|---|---|---|---|---|
| Body text on surface.default | dark | default | #e6e6e6 | #1c1c1e | 13.63 | 4.5 | Pass |
| Input border vs surface.default | light | default | #949494 | #ffffff | 3.03 | 3.0 | Pass |
1.4.1: <where color carries meaning, and the non-color cue used>
Focus (2.4.7 / 2.4.11): <indicator, ratio vs adjacent, obscured?>

## Supplementary (informative, not conformance)
- APCA Lc: <values, labeled informative>
- ΔE00 between status colors: <values, white, observer>
- CVD simulation (method, linearized?): <pairs that collapse and the fix>

## Assumptions
sRGB, 8-bit hex, composited source-over in gamma-encoded sRGB over <backdrop>; threshold 0.04045.

## Not verified
<e.g., on-device P3 rendering, forced colors on Windows, Increase Contrast on iOS>
```
Example rows are computed with the formula above (sRGB, 8-bit, opaque colors) and truncated to two decimals; they illustrate the format, not project values.

## Sources
- WCAG 2.2 Recommendation (SC text, relative luminance with 0.04045 and the May 2021 note, large-scale text): [W3C](sources.md#w3c).
- Technique G183 (link vs surrounding text 3:1): [W3C](sources.md#w3c).
- Understanding 1.4.3 (no rounding, measuring from styles, anti-aliasing, logotypes), 1.4.11 (adjacent colors, gradients, 2.999 fails), 1.4.1 (links, charts), 2.4.13: [W3C](sources.md#w3c).
- WCAG 3.0 Working Draft status: [W3C](sources.md#w3c).
- APCA in a Nutshell: [Research](sources.md#research).
- Apple HIG Dark Mode (4.5:1 minimum, strive for 7:1): [Platforms](sources.md#platforms).
