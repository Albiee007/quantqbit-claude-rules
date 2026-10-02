---
name: color-science
description: Mandatory, context-aware color companion to ui-ux for every UI change. Discovers brand, semantic needs, themes, content, data-viz needs and output media before deciding anything. Covers palettes and interaction states, dark and high-contrast themes, color-vision-deficiency (CVD) accessibility, color spaces, perceptual models, gamut mapping, alpha compositing, ICC and print, wide gamut and HDR. Use when creating or changing any UI, choosing or editing colors, palettes, themes or color tokens, building charts, converting color spaces, or preparing print or measured color.
---

# Color Science

**Mandatory** alongside `ui-ux` for every change that touches a user interface. Non-UI color work (print, standalone charts, measurement, image pipelines) loads this skill on its own, without `ui-ux`. Decide from the project's context, not from generic defaults. State every assumption behind a number.

## Precedence
1. **WCAG 2.2 AA minimums are never overridable** (1.4.1, 1.4.3, 1.4.11, 2.4.7, 2.4.11). No brand, token or design file lowers them. If a design fails, implement the accessible version and flag the difference.
2. **Project color tokens and existing design docs** are the source of truth for every value and name.
3. **Platform system:** Material 3 color roles and dynamic color (Android), Apple semantic and system colors (Apple platforms), CSS system colors in forced-colors mode (web).
4. This skill and its references.

**Extend existing tokens; never create a parallel palette.** Add a token only for a real, repeated need, named by role ([design-tokens-dtcg](../ui-ux/references/design-tokens-dtcg.md)).

## Workflow
1. **Discover context** with [context-discovery](references/context-discovery.md) when colors, tokens, themes or palettes change: brand, semantic needs, themes, content types, data-viz, output media. Type-only changes skip discovery and re-verify text contrast via [accessibility-standards](references/accessibility-standards.md).
2. **Inventory** the existing tokens, themes, brand palette and color docs. List what exists before proposing anything. **Greenfield** (no tokens exist): create a minimal semantic set (text, surface, border, action, status, focus) via [design-tokens-dtcg](../ui-ux/references/design-tokens-dtcg.md) and record it as the initial decision.
3. **Decide only what's missing.** Reuse first. A new color needs a role, a value per theme and a rationale.
4. **Implement semantic tokens for every theme the project supports** (light, plus dark, high-contrast and dynamic only where in scope). Components consume semantic tokens only ([product-palettes](references/product-palettes.md)).
5. **Verify** with the checklist below, in every theme the project supports and every state, after compositing.
6. **Record** each decision and its rationale in the project's existing design docs or token `$description`, using the decision-record format in [context-discovery](references/context-discovery.md). Never start a second color doc.

## Rules
- **State assumptions.** Any calculation (conversion, ΔE, contrast, gamut check, print transform) states:
  - color space and encoding (e.g., sRGB gamma-encoded vs linear, Display P3, CIELAB D50);
  - units and range (0–1 vs 0–255, % vs 0–100, cd/m²);
  - white point and chromatic adaptation method (e.g., D65→D50 via Bradford);
  - observer (CIE 1931 2° or CIE 1964 10°);
  - viewing conditions and surround where the model needs them (CAM16, HCT);
  - output medium and profile (sRGB web, P3 device, named ICC print profile).
- **Standards vs supplementary.** Report WCAG 2.2 conformance (normative) in its own section. APCA, ΔE, CVD-simulation scores and perceptual-uniformity checks are supplementary. They never substitute for, "override" or excuse a WCAG result ([accessibility-standards](references/accessibility-standards.md)).
- **Heuristics are labeled.** Color psychology, cultural meaning and 60/30/10 proportions are contextual heuristics. Label them as such, and defer to the project's brand and user research ([heuristics](references/heuristics.md)).
- **Linear light for math.** Blend, composite, scale, resize and compute luminance on linear-light values ([rgb-and-compositing](references/rgb-and-compositing.md)).
- **Interpolate in a stated space.** Gradients and mixes name their interpolation space (e.g., OKLab) and hue method, and are checked for gamut.
- **Never use color alone** to convey meaning, state or action (WCAG 1.4.1). Add text, icon, shape, pattern or position.
- **Measure what the user sees.** Contrast is computed on the final composited color against its actual backdrop, never on a token with alpha.
- **Map out-of-gamut colors deliberately.** Never rely on silent clipping. Provide an sRGB fallback for every wide-gamut value.
- **No raw color values in components.** Hex, rgb(), oklch() and Color(0x…) live only in the token source.

## Required checks
Every item is true, or is reported as not verified with a reason.

- [ ] **Text contrast** ≥ 4.5:1 (≥ 3:1 for large text) for every text/background token pair, in every theme the project supports and every state (default, hover, pressed, focus, selected, error), computed after alpha compositing. Ratios truncated, never rounded up.
- [ ] **Non-text contrast** ≥ 3:1 against adjacent colors for component boundaries, state indicators, meaningful icons, focus indicators and chart marks.
- [ ] **Color is never the only signal** (status, errors, links in text, selected state, chart series).
- [ ] **CVD simulation** run on every meaningful color pair (status colors, chart series, success/error): protan, deutan, tritan. Pairs that collapse get a lightness difference or a redundant cue.

Theme items apply in every theme the project supports; dark and high-contrast only when in scope ([context-discovery](references/context-discovery.md)).

- [ ] **Dark theme parity** (when dark is in scope): every semantic token has a dark value, built by lightness remapping, not inversion. Re-verified, not assumed from light.
- [ ] **High-contrast parity** (when supported): web `forced-colors: active` uses CSS system colors with visible borders and focus; `prefers-contrast: more` handled where the project supports it; Apple Increase Contrast variants; Android high-contrast text not broken.
- [ ] **Gamut:** every wide-gamut (P3, Rec. 2020) value is mapped deliberately and has an sRGB fallback; gradients checked for clipping on sRGB displays.
- [ ] **Charts:** palette type matches the data type (categorical, sequential, diverging, cyclic); redundant encoding (labels, shapes, patterns); no rainbow/jet for ordered data ([data-visualization](references/data-visualization.md)).
- [ ] **Print or measured color:** named output profile, rendering intent (and BPC choice), soft proof done, measurement condition and instrument stated, ΔE formula and tolerance stated, observer and adaptation stated, uncertainty reported ([color-management](references/color-management.md), [perceptual-spaces](references/perceptual-spaces.md) for the ΔE formula, [foundations](references/foundations.md) for observer and adaptation).
- [ ] **Decisions recorded** in the project's existing docs with rationale and assumptions.

## Tools
`python .claude/skills/color-science/scripts/palette.py` (stdlib; sRGB IEC 61966-2-1, D65, WCAG 2.x luminance; ratios compared at full precision, printed truncated):
- `ramp --name brand --seed "#hex"` (or `--hue --chroma`) `[--lightness L1,..]`: an OKLCH tonal ramp with stated lightness steps and tapered chroma, gamut-mapped to sRGB (CSS Color 4), with each step's contrast against white and black.
- `contrast FG BG [--size px --weight w | --large | --non-text] [--tokens f]`: one pair, composited first; exits 1 below the threshold.
- `check --tokens f --pairs pairs.json`: the pairs you actually use, in the report format below.
- `convert COLOR`: sRGB, OKLab, OKLCH and gamut status.
With `--out <tokens file>`, `ramp` merges into the existing DTCG file without overwriting (`--replace` names a change; the old file is kept as `.bak`). CVD simulation, ΔE2000 and harmony generators are not part of the tool yet: run CVD checks with a simulator and report them as supplementary.

## Reporting
- Section 1, **WCAG 2.2 conformance:** each pair or element, measured ratio (truncated to 2 decimals, never rounded up), threshold, pass/fail, theme and state.
- Section 2, **Supplementary:** APCA, ΔE, CVD simulation, gamut notes. Labeled informative.
- Section 3, **Assumptions:** spaces, encodings, white points, observer, media, profiles.
- Section 4, **Not verified:** list each check not done and why, e.g. no measurement device, no target display (P3, HDR), no physical proof or viewing booth, standard not accessible (paywalled), no user research for a heuristic claim, platform setting not testable here.

## References
- [context-discovery](references/context-discovery.md): what to discover (brand, semantics, themes, content, data-viz, media), where tokens live per platform, decision-record format. Load when colors, tokens, themes or palettes change; for type-only changes just re-verify text contrast via accessibility-standards.
- [foundations](references/foundations.md): spectra, cones, CIE observers, CMFs, illuminants, XYZ, chromaticity, CCT, chromatic adaptation, metamerism. Load when converting between spaces, picking an observer or white point, or explaining a mismatch.
- [rgb-and-compositing](references/rgb-and-compositing.md): RGB space definitions, transfer functions, linear-light math, alpha compositing, interpolation, gamut mapping, CSS and native wide gamut. Load when blending, compositing, building gradients, or using P3/Rec. 2020.
- [perceptual-spaces](references/perceptual-spaces.md): CIELAB/LCh, Oklab/OKLCH, ΔE formulas, CAM16, HCT and their limits. Load when building ramps, measuring color differences, or choosing a working space.
- [product-palettes](references/product-palettes.md): primitive ramps, semantic roles, interaction states, dark, high-contrast, dynamic color, CVD, text on images. Load when creating or changing palettes, themes or tokens, or making any component work in dark, forced-colors or high-contrast modes.
- [accessibility-standards](references/accessibility-standards.md): normative WCAG 2.2 color criteria and contrast math, then supplementary methods, plus a reporting template. Load for every contrast check or report.
- [data-visualization](references/data-visualization.md): palette type by data, uniform ramps, CVD-safe categorical sets, redundant encoding, chart contrast, dark charts. Load when building any chart, map or legend.
- [color-management](references/color-management.md): ICC architecture, calibration vs profiling, rendering intents, proofing, embedding, wide gamut and HDR workflows, measurement. Load for print, measured color, image pipelines or HDR.
- [heuristics](references/heuristics.md): color psychology, cultural meaning, 60/30/10, accent scarcity, how to validate. Load when a choice rests on emotion, culture or proportion.
- [sources](references/sources.md): dated source index with access status and inaccessible standards. Load when citing or checking a claim.
