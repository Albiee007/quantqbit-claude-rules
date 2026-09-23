# Typography and Color

## Typography

### Type scale
- Use the project's type tokens. If none exist, define one scale and use nothing outside it. Web: a modular scale from a 16 px (1rem) base with ratio 1.2 (minor third) or 1.25 (major third), rounded to whole px, for example 12, 14, 16, 20, 24, 30, 36, 48. Android: the M3 scale ([material3](material3.md)). iOS: system text styles ([apple-hig](apple-hig.md)).
- Keep 5-8 sizes in active use. Express hierarchy with size, weight, and spacing together, not size alone.
- Body text at least **16 px** on web (1rem), 17 pt iOS (Body), 14-16 sp Android (Body Medium/Large). Never below 12 px/sp except legal microcopy, and never for essential information.
- Web: font sizes in `rem`, never `px` on text, so user font settings apply. Never disable zoom (`user-scalable=no`, `maximum-scale=1`).

### Measure, line height, and spacing
- **Line length (measure):** 50-75 characters for body text (about 45-75 is common guidance). Hard ceiling 80 characters (40 for CJK, WCAG 1.4.8 AAA). Web: `max-inline-size: 65ch` (or 60-75ch) on prose.
- **Line height:** body 1.4-1.6 (use 1.5 by default). Headings 1.1-1.3. UI labels about 1.2-1.4. Unitless in CSS (`line-height: 1.5`).
- **Paragraph spacing:** at least 0.75-1x the font size. Must survive WCAG 1.4.12 overrides (1.5 line height, 2x paragraph, 0.12em letter, 0.16em word spacing). No fixed heights on text boxes. Allow wrapping.
- Left-align (start-align) body text. Do not justify body text on the web. Do not center-align blocks longer than 2-3 lines.
- No all-caps for sentences. For short labels, use `text-transform` so screen readers read normal case. Add letter spacing of about 0.05em for caps labels.
- At most 2 font families (plus monospace for code). Limit weights to about 3 (regular, medium or semibold, bold). Avoid thin weights for UI text.
- Use tabular numerals (`font-variant-numeric: tabular-nums`) in tables, prices, and timers.
- Web fonts: `font-display: swap` (or `optional`), a size-matched fallback stack, and preload only critical faces.

### Fluid type (web)
Use `clamp(min, preferred, max)` with a rem component so zoom still works:
```css
--font-size-h1: clamp(1.75rem, 1.2rem + 2.5vw, 3rem);
```
Never use pure `vw` font sizes (they break 1.4.4 text resize). Verify at 200% zoom.

## Color

### Contrast math (WCAG 2.x, normative)
1. Convert each sRGB channel (0-255) to 0-1: `c = C/255`.
2. Linearize: `c <= 0.04045 ? c/12.92 : ((c + 0.055)/1.055)^2.4`.
3. Relative luminance: `L = 0.2126*R + 0.7152*G + 0.0722*B`.
4. Contrast ratio: `(L1 + 0.05) / (L2 + 0.05)`, where L1 is the lighter color. The range is 1:1 to 21:1.

Requirements: text **4.5:1**. Large text (at least 24 px, or at least 18.5 px bold) **3:1**. UI component boundaries, states, focus indicators, and meaningful graphics **3:1** against adjacent colors. AAA (good practice): 7:1 and 4.5:1. Do not round up: 4.49:1 fails. Measure semi-transparent colors after compositing on their actual background. Text on images needs a scrim or overlay that guarantees the ratio.

**APCA** (Lc values; for example Lc 75 minimum for body text, Lc 90 preferred) is **informational only**. It is not part of WCAG 2.x and does not replace the ratios above. It may help tune dark-theme pairs that pass WCAG but read poorly.

### Palette structure
- **Primitives:** hue ramps (for example 50-950) per brand hue plus neutrals, with perceptually even steps (OKLCH is a good authoring space).
- **Semantic roles:** text (primary, secondary, disabled, inverse, link), surface or background (default, raised, sunken, overlay), border (default, strong, focus), action (primary, secondary, danger; each with hover, pressed, and disabled states), status (success, warning, danger, info; each with fg, bg, and border). See [design-tokens-dtcg](design-tokens-dtcg.md).
- Accent color is scarce: roughly 60/30/10 (neutral surfaces / secondary / accent).
- Status colors always come with an icon or text (1.4.1). Red and green pairs must also differ in lightness for color-vision deficiency. Check with a CVD simulator (protanopia, deuteranopia, tritanopia).
- Links in body text are underlined, or differ by at least 3:1 from surrounding text **and** show a non-color cue on hover and focus.
- Disabled elements are exempt from contrast rules but must still look disabled. Never use disabled styling for enabled-but-invalid actions.

### Dark mode
- Implement dark mode as a **semantic token theme**, not per-component overrides.
- Backgrounds: dark gray (for example around `#121212`), not pure black, for large surfaces. Near-white text (not pure `#fff` on pure black for long reading). Express elevation with lighter surfaces instead of shadows.
- Desaturate and lighten accent colors (lower chroma) so they do not vibrate on dark backgrounds. Re-verify every pair: a pass in light does not imply a pass in dark.
- Follow the system preference by default (`prefers-color-scheme`, `isSystemInDarkTheme()`, `colorScheme`). An in-app override is optional on web and Android (discouraged by Apple HIG on iOS). Set CSS `color-scheme: light dark` so native controls match.
- Images and illustrations: provide dark variants or reduce the brightness of white-background images. Logos need dark-safe versions.
- Support high-contrast modes: `forced-colors: active` (Windows) using system colors and visible borders, and Increase Contrast (iOS).

## Sources
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- https://www.w3.org/TR/WCAG22/
- https://baymard.com/blog/line-length-readability
- https://git.apcacontrast.com/documentation/APCA_in_a_Nutshell.html
- https://developer.apple.com/design/human-interface-guidelines/typography
- https://developer.apple.com/design/human-interface-guidelines/dark-mode
- https://developer.android.com/guide/topics/ui/accessibility/apps
