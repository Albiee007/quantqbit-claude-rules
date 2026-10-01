# Typography and Color (overview)

This file used to hold all type and color guidance. That guidance now lives in two specialist skills, and both are mandatory for every UI change, together with `ui-ux`:
- [typography](../../typography/SKILL.md): context discovery, hierarchy and measure, font metrics and pairing, variable fonts, multilingual and RTL text, loading and licensing, and platform text scaling.
- [color-science](../../color-science/SKILL.md): context discovery, palettes and states, dark and high-contrast themes, color-vision deficiency (CVD), color spaces and gamut mapping, perceptual models, data visualization, and ICC, print and HDR work.

When this overview and a specialist skill disagree, follow the specialist skill. Project tokens and design docs override both.

## Floors that never change (WCAG 2.2 AA)
- **Text contrast:** at least **4.5:1**. Large text (at least 24 px, or at least 18.66 px (14 pt) bold) needs at least **3:1**.
- **Non-text contrast:** UI boundaries, states, focus indicators and meaningful graphics need at least **3:1** against adjacent colors.
- **Measure correctly:** don't round up, so 4.49:1 fails. Measure semi-transparent colors after compositing them on their real background. Check every theme.
- **Never use color alone** to convey meaning (1.4.1).
- **Text resizing:** text resizes to 200% (1.4.4), and content survives the 1.4.12 spacing overrides.
- **Web:** set text sizes in `rem`, and never disable zoom.

[color-science/references/accessibility-standards.md](../../color-science/references/accessibility-standards.md) has the contrast formula and its supplementary metrics. It reports APCA separately and never treats it as conformance.

## Fallback defaults, used only when the project gives no evidence
These are starting points, not rules. The specialist skills explain how to replace them with values derived from the project's content, audience and platforms.
- **Type:** use the platform scale (Material 3 type roles, Apple text styles). On the web, start with a modular scale from a 1rem base, with its ratio chosen by content density.
- **Families:** use the fewest that cover the project's scripts and roles, and record why each one is there.
- **Palette:** semantic roles on top of primitive ramps. Accent proportions such as 60/30/10 are a heuristic ([color-science heuristics](../../color-science/references/heuristics.md)).
- **Dark mode:** a semantic token theme with lightness remapped, not inverted. Choose a specific surface value by verifying it, rather than taking a fixed hex.

## Sources
- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- The specialist skills' `references/sources.md` files hold the dated source indexes.
