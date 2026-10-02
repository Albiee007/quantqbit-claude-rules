# Foundations

Enough colorimetry to state assumptions correctly and explain mismatches. Load before conversions, white-point choices or observer choices.

## Light and spectra
- Light is described by its **spectral power distribution (SPD)**: power per wavelength, roughly 380–780 nm for vision.
- A surface's color depends on its **spectral reflectance** × the illuminant SPD. Change the light and the stimulus changes.
- Emissive displays produce color from a few primaries; their SPDs are narrow-band or broad depending on technology (LCD+filters, OLED, quantum dot).

## Cones and trichromacy
- Normal human color vision uses three cone types, L, M and S (long, medium, short wavelength). Their spectral sensitivities are the **cone fundamentals** (CIE 2006 LMS fundamentals are a free CIE dataset).
- Three signals mean any stimulus can be matched by a mix of three primaries: **trichromacy**. This is why three numbers (RGB, XYZ) suffice to specify a color match, but not its appearance.
- Color vision deficiency (CVD) is a missing or shifted cone class: see [product-palettes](product-palettes.md).

## Standard observers and color matching functions
- **Color matching functions (CMFs)** x̄(λ), ȳ(λ), z̄(λ) turn an SPD into XYZ tristimulus values by integration.
- **CIE 1931 2° observer:** derived from matching experiments on a small foveal field (Wright and Guild data). Use for small fields, and it is the default of sRGB, CSS, ICC and most software.
- **CIE 1964 10° observer:** derived for larger fields. Recommended when the stimulus subtends more than about 4°; common for paint, textiles and product/surface color with larger fields.
- **Graphic-arts print measurement uses the 2° observer** (ISO 13655; standard not accessed, not verified). Don't switch a print job to 10° because the sheet is large.
- Never compare XYZ, Lab or ΔE values computed with different observers. State the observer for every measured or computed value.

## Illuminants vs light sources
- An **illuminant** is a defined SPD table; a **light source** is a physical lamp. A lamp can approximate an illuminant, never be one.
- **D65:** average daylight, ~6500 K CCT. White point of sRGB, Display P3, Rec. 709, Rec. 2020, Oklab.
- **D50:** horizon daylight, ~5000 K. White point of the ICC profile connection space (PCS), CIELAB in CSS, and graphic-arts viewing (ISO 3664).
- **A:** incandescent (tungsten), ~2856 K.
- **F-series:** fluorescent lamp SPDs (e.g., F2 cool white, F11 narrow-band). Spiky SPDs make metamerism worse.
- Free tables for A, D50, D65 and lamp SPDs: CIE data tables.

## XYZ, luminance and chromaticity
- **XYZ** is device-independent tristimulus space. **Y is luminance** (scaled relative: white = 1 or 100; absolute: cd/m²). WCAG relative luminance is Y of the sRGB color with white = 1.
- **xy chromaticity:** x = X/(X+Y+Z), y = Y/(X+Y+Z). Drops luminance. Use it to plot gamuts and white points.
- **Limits:** xy is **not perceptually uniform** (MacAdam ellipses vary greatly in size). Never use xy distance as a color difference. A gamut triangle's area on xy overstates or understates perceived gamut differences; compare gamut volumes in a perceptual space instead.
- u′v′ (CIE 1976 UCS) is more uniform than xy for chromaticity, still not a difference metric.

## Correlated color temperature (CCT)
- CCT is the temperature of the black-body radiator whose chromaticity is nearest the source's. It is one number for a 2D chromaticity: two sources with the same CCT can look different (green vs magenta tint, measured as Duv).
- CCT says nothing about color rendering. Two "5000 K" lamps can render colors very differently.

## Chromatic adaptation
- The visual system adapts to the prevailing white. A **chromatic adaptation transform (CAT)** predicts the corresponding color under a different white.
- **Von Kries:** scale cone-like responses by the ratio of the two whites. All common CATs are von Kries-type in a chosen cone-like space.
- **Bradford:** a sharpened cone space; used by CSS Color 4 for D65↔D50 and widely in ICC workflows.
- **CAT02** (CIECAM02) and **CAT16** (CAM16): later CATs with a degree-of-adaptation factor that depends on viewing conditions.
- **Why D50↔D65 matters:** the ICC PCS is D50; web RGB spaces are D65; CSS `lab()` is D50 while `oklab()` is D65. Converting without adaptation gives a visible cast. Converting with different CATs gives small but real differences, so state the CAT.
- Adaptation is not a gamut operation; apply it to XYZ before mapping into the destination space.

## Metamerism
- **Metamers:** different spectra that match for a given observer and illuminant.
- **Illuminant metamerism:** a match under one light fails under another (print matches screen proof under D50, not under store LEDs).
- **Observer metamerism:** a match for one observer fails for another person, or for 2° vs 10°. Narrow-band displays (laser, some OLED/QD) increase observer metamerism; two calibrated displays can still disagree visually.
- Practical: when a physical product must match, evaluate under the real lighting and the relevant observer; when two displays must match, expect residual differences that measurement may not show.

## Practical implications
- Every conversion: name the source space, destination space, both whites and the CAT.
- Web work: D65, 2° observer, sRGB unless stated. Print and ICC: D50 PCS, 2° observer unless the workflow says otherwise.
- Paint, textiles, product/surface color with large fields: consider the 10° observer and the real illuminant. Graphic-arts print: 2° (above).
- Never claim a match without saying under which light, for which observer, and how it was checked.

## Sources
- CIE free datasets (CMFs, illuminants A/D50/D65, CIE 2006 cone fundamentals, lamp SPDs): [CIE](sources.md#cie).
- CIE 015:2018 Colorimetry: [CIE](sources.md#cie), paywalled, contents not verified.
- 2° vs 10° use, Y as luminance, xy non-uniformity: Wikipedia "CIE 1931 color space" [Research](sources.md#research) (secondary).
- Bradford in CSS, Lab D50 vs Oklab D65: CSS Color 4 [W3C](sources.md#w3c).
- ICC PCS illuminant D50: ICC.1:2022 [ICC and ISO](sources.md#icc-and-iso).
- 2° observer for graphic-arts measurement: ISO 13655 [Inaccessible standards](sources.md#inaccessible-standards), not verified.
- CAT16: Li et al. 2017 [Research](sources.md#research), not accessed.
