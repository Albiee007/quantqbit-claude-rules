# Product Palettes and Themes

Build on the project's existing tokens. Everything here applies only where the project has no decision yet ([context-discovery](context-discovery.md)).

## Primitive ramps
- One ramp per brand hue plus a neutral ramp (optionally a tinted neutral). Typical steps 50–950 or 0–100; match the project's existing naming.
- Author in **OKLCH** with **controlled lightness steps**: fix L per step across all hues (e.g., the same L for every `600`), so steps of the same number behave alike. Then:
  - taper chroma toward the light and dark ends (very light or very dark colors can't hold high chroma in sRGB);
  - adjust hue slightly per step if a hue drifts (yellows go muddy when dark, blues go purple in CIELAB-based tools);
  - map every step into sRGB deliberately and store the sRGB value (plus an optional P3 value).
- Equal OKLCH L does not give equal WCAG contrast. After building the ramp, compute the contrast of each step against white and against the darkest neutral and record which steps pass 4.5:1 and 3:1. Semantic tokens then pick steps from that table.
- Store primitives in the token source with the authoring space in `$description` or `$extensions` (DTCG color values carry `colorSpace`).

## Semantic roles
- **Text:** primary, secondary, disabled, inverse, link. Primary and secondary pass 4.5:1 on every surface they sit on.
- **Surface:** default, raised, sunken, overlay/scrim, inverse.
- **Border:** default (decorative, may be < 3:1), strong/input (≥ 3:1 when it identifies a control), focus (≥ 3:1 against adjacent colors).
- **Action:** primary, secondary, danger; each with default, hover, pressed, focus, selected, disabled.
- **Status:** success, warning, danger, info; each with fg, bg, border, icon.
  - Status tokens never reuse the categorical chart palette (a chart series must not read as "error").
  - Badge text ≥ 4.5:1 against the badge bg. When a border or fill is the only indicator of the badge boundary, it needs ≥ 3:1 against the adjacent surface.
  - Always icon + text label; never hue alone.
- Name by role (`color.text.danger`), never by appearance (`color.red-text`).

## Interaction states
- **State layers (Material model):** a translucent overlay of the content color on the container for hover, focus, pressed, dragged. Use the platform's documented opacities; don't invent per-component values.
- **Opacity overlays elsewhere:** define them as tokens, then compute the **composited result** over each container in each theme, and check contrast of the text/icon on that result.
- **Focus:** a focus indicator ≥ 3:1 against adjacent colors (1.4.11), visible in every theme and in forced colors (`outline` survives forced colors; `box-shadow` is removed).
- **Disabled:** exempt from contrast minimums, but must still read as disabled and never be used for enabled-but-invalid actions. Don't convey disabled by color alone; reduce emphasis and expose the state programmatically.
- **Selected:** never color-only; add a check, weight, indicator bar or icon.

## Dark theme
- **Not inversion.** Remap lightness: surfaces become dark, text light, and each semantic token gets its own dark value chosen from the ramps.
- **Reduce chroma** of accents and status colors on dark surfaces; saturated colors on dark backgrounds can vibrate and bloom. Lighter, less saturated steps usually pass contrast on dark.
- **Elevation via lighter surfaces:** higher layers get lighter surface colors (Apple's base vs elevated backgrounds; Material's tonal surfaces), since shadows are weak on dark.
- **Heuristic:** avoid pure black and pure white for large areas and long reading (halation, smearing on some OLED panels). Pure black can be right for media viewers or OLED power-saving modes. Use the project's or platform's dark surface tokens rather than a fixed hex.
- Images: dim white-background images; provide dark-safe logos and illustrations (Apple suggests slightly darkening content images with white backgrounds).
- Re-verify every pair. A light-theme pass says nothing about dark.

## High contrast
- **Web forced colors** (`@media (forced-colors: active)`): the UA replaces author colors (`color`, `background-color`, `border-color`, `outline-color`, SVG `fill`/`stroke`, …) with system colors and removes `box-shadow`, `text-shadow` and non-URL background images. Use CSS system colors (`Canvas`, `CanvasText`, `LinkText`, `ButtonFace`, `ButtonText`, `Highlight`, `HighlightText`, `GrayText`) for small fixes, add real borders where shadows defined edges, and use `forced-color-adjust: none` only for content whose colors carry meaning (e.g., color swatches), with care.
- **`prefers-contrast`:** `more`, `less`, `custom` (custom matches forced colors). Offer stronger borders, solid backgrounds instead of translucency, higher-contrast text tokens.
- **Apple Increase Contrast:** provide an increased-contrast variant for every custom color in light and dark (asset catalog "High Contrast" appearance); system colors already have them. Test with Reduce Transparency too.
- **Android:** high-contrast text is a system accessibility setting; test with it on and make sure custom text drawing, shadows or images of text don't defeat it. Material's contrast levels (standard, medium, high) map to scheme variants where the project uses Material color.

## Dynamic color (Material You)
- On Android 12+, the system derives a scheme from the wallpaper or a user-chosen color. Decide with the owner: **dynamic** (personal, brand appears in logo and key moments), **static brand scheme**, or **dynamic with harmonized brand accents** (`HarmonizedColors` shifts custom colors toward the dynamic scheme while keeping their identity).
- Status colors (error, success) and data-viz colors must stay recognizable under every dynamic scheme; harmonize them, don't replace them.
- Fall back to a static brand scheme where dynamic color isn't available.

## Color vision deficiency
- **Prevalence:** about 1 in 12 men (NEI); far fewer women. Red-green (protan, deutan) is most common; blue-yellow (tritan) is rarer; complete achromatopsia is rarest. Machado et al. cite about 200 million people worldwide.
- **Simulate** protanopia, deuteranopia, tritanopia, and anomalous trichromacy at intermediate severity:
  - Viénot et al. 1999 for protan/deutan dichromacy (single matrix), Brettel et al. 1997 for tritan;
  - Machado et al. 2009 for a unified model with severity 0–1;
  - **linearize sRGB first**; many tools skip this and over-darken.
  - Simulation is an approximation of an average dichromat, not a guarantee for any individual.
- **Design responses:** separate meaningful pairs by **lightness**, not only hue; avoid red/green-only distinctions (use blue/orange or magenta/green); add redundant cues (icons, labels, patterns, position, underline for links); direct-label charts.

## Text on images and video
- Guarantee contrast for the worst case under the text: a solid or gradient scrim, a backing plate, text shadow plus scrim, or placement on a known flat region.
- Measure against the lightest (for light text) or darkest (for dark text) pixels the text can overlap, across all crops and breakpoints. User-generated images need a scrim by default.

## Sources
- WCAG 1.4.1, 1.4.3, 1.4.11 Understanding docs: [W3C](sources.md#w3c).
- forced colors behavior and system colors (MDN), `prefers-contrast` (MDN), CSS Color Adjust 1: [W3C](sources.md#w3c), [Platforms](sources.md#platforms).
- Apple HIG Color and Dark Mode (Increase Contrast variants, base/elevated, darkening white images); Material 3 color system; Android dynamic color and `HarmonizedColors`: [Platforms](sources.md#platforms).
- CVD prevalence (NEI); Machado et al. 2009; DaltonLens on Brettel/Viénot/Machado and linearization: [Research](sources.md#research). Brettel 1997 and Viénot 1999 papers not accessed.
- Material state-layer opacities: page did not render; values not reproduced.
