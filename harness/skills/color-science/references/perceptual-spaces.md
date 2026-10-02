# Perceptual Spaces and Color Difference

Pick the space for the job, state it, and know its limits. None of these replaces WCAG contrast math ([accessibility-standards](accessibility-standards.md)).

## CIELAB and LCh
- L* (lightness 0–100), a* (green–red), b* (blue–yellow); LCh is its polar form (C* chroma, h hue angle).
- Defined relative to a reference white. **Conventions differ:** ICC and CSS `lab()`/`lch()` use **D50**; some tools compute Lab from D65 directly. Lab values from different whites are not comparable; state the white and the CAT used to get there.
- L* is a reasonable lightness predictor for surface colors and is the "tone" axis of Material's HCT.
- **Known non-uniformity:** hue is not constant along lines of constant CIELAB hue angle, worst in blues (blue shifts toward purple as chroma drops). Chroma steps are uneven across hues. Gradients and ramps built in LCh can drift in hue.

## Oklab and OKLCH
- Björn Ottosson's 2020 space: L (0–1), a, b; OKLCH is its polar form. **D65** white. Fit to CAM16-derived lightness and chroma data and to IPT hue data, with a simple, stable transform (linear sRGB → LMS-like → cube root → Lab-like). Matrices: see the Oklab article or CSS Color 4 sample code; don't retype them.
- Better hue linearity than CIELAB in blues; good for ramps, mixing and gradients. CSS Color 4 uses it as the default interpolation space and for gamut mapping.
- **Use for:** primitive ramps with controlled lightness steps, hue-stable tints and shades, gradients, `color-mix()`.
- **Limitations:**
  - Not a color appearance model: assumes ordinary, well-lit viewing; no surround, adaptation-luminance or background parameters, no absolute luminance (not built for HDR).
  - **OKLCH L is not WCAG relative luminance.** Two colors with equal L can have different contrast ratios against the same background. Always compute WCAG contrast separately.
  - Equal L across hues is only approximately equal perceived lightness; check saturated yellows and blues.
  - Constant OKLCH chroma is often out of sRGB gamut at some hues/lightnesses; map deliberately ([rgb-and-compositing](rgb-and-compositing.md)).

## Color difference (ΔE)
Always name the formula; "ΔE 2" without a formula is meaningless.
- **ΔE\*ab (CIE 1976):** Euclidean distance in CIELAB, `√(ΔL*² + Δa*² + Δb*²)`. Simple; overstates differences in saturated colors and understates some near-neutral ones.
- **ΔE94 (CIE 1994):** weights chroma and hue differences by chroma; has application-specific constants (graphic arts vs textiles). State which set you used.
- **CIEDE2000 (ΔE00):** adds hue-dependent and chroma-dependent weights, a blue-region rotation term and an a* rescale for neutrals. Current choice for small differences in surface colors.
  - **Implementation pitfalls** (Sharma, Wu, Dalal 2005): hue-angle computation (use `atan2`, handle a′ = b′ = 0), choosing the mean hue when the hue difference exceeds 180°, and discontinuities in the formula. Validate any implementation against their published test data before trusting it.
- **ΔEOK:** Euclidean distance in Oklab (CSS Color 4). Used for gamut mapping; scale is 0–1-based, so a value of 0.02 there is not comparable to ΔE00 2.
- **JND heuristics (with caveats):** CSS Color 4 treats ΔEOK 0.02 and ΔE00 2 as about one just-noticeable difference for its gamut-mapping purposes. Real visibility depends on sample size, separation, surround, observer and medium. Treat any JND number as a heuristic, never as a tolerance; print tolerances come from the job's spec ([color-management](color-management.md)).
- ΔE is not contrast. Two colors can be ΔE00 30 apart and still fail 4.5:1.

## Color appearance models
- **CIECAM02** (CIE 159:2004) and **CAM16** (Li et al. 2017) predict appearance correlates: lightness J, chroma C, colorfulness M, saturation s, hue h, brightness Q.
- They need **viewing conditions**: the adopted white, adapting luminance, background relative luminance and surround (average, dim, dark). Without these stated, a CAM result is not meaningful.
- **CAM16-UCS** is a uniform color space derived from CAM16 for color differences.
- Use a CAM when viewing conditions differ (dim-room display vs bright office vs print booth), for cross-media appearance matching, or when predicting how a color looks rather than whether two match.
- CAM16 paper not accessed: specifics (equations, parameter tables) are not reproduced here; use a validated library (e.g., colour-science, colorjs.io) and cite its version.

## HCT (Material)
- Material 3's color system uses **HCT**: hue and chroma from **CAM16**, tone from **CIELAB L\***. Tonal palettes vary tone at fixed hue and chroma; dynamic color derives schemes from a source color.
- Because tone is L*, a tone difference correlates with, but does not equal, WCAG contrast. Verify ratios.
- Default CAM16 viewing conditions are baked into Material's libraries; if you compute HCT yourself, state the conditions.

## Which space when
| Task | Space |
|---|---|
| WCAG contrast | sRGB → linear → relative luminance (only) |
| Physical light mixing, compositing, resizing | linear-light RGB |
| UI ramps, tints, gradients, `color-mix()` | OKLCH / Oklab (check gamut) |
| Android theming consistent with Material | HCT via Material libraries |
| Small color differences, QA tolerances | CIEDE2000 (stated white, observer) |
| Print / ICC transforms | CIELAB D50 (PCS) |
| Different viewing conditions, appearance | CAM16 / CAM16-UCS with stated conditions |

## Sources
- Oklab (design, D65, fit data, limits, CIELAB blue issue): Ottosson 2020 [Research](sources.md#research).
- Lab D50 vs Oklab D65, ΔEOK, JND notes: CSS Color 4 [W3C](sources.md#w3c).
- CIEDE2000 implementation notes: Sharma, Wu, Dalal 2005 [Research](sources.md#research).
- HCT built on CAM16 and L*: Material 3 "How the system works" [Platforms](sources.md#platforms).
- CAM16: Li et al. 2017 [Research](sources.md#research), not accessed. CIECAM02 (CIE 159:2004), ΔE94 (CIE 116-1995): [Inaccessible standards](sources.md#inaccessible-standards).
