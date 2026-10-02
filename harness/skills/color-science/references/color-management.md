# Color Management, Print, HDR and Measurement

Load for print, measured color, image pipelines, wide gamut assets or HDR. Many relevant standards are paywalled: say so in the report rather than implying conformance ([sources](sources.md#inaccessible-standards)).

## ICC architecture
- A **CMM** (color management module) converts device values → **PCS** → device values using two profiles (source, destination) and a rendering intent.
- **PCS:** CIEXYZ or CIELAB relative to **D50** (PCS illuminant XYZ ≈ 0.9642, 1.0, 0.8249). Display profiles for D65 spaces carry adaptation to D50 (chromatic adaptation tag).
- **Profile classes:** input (camera, scanner), display, output (printer/press), device link, color space (e.g., sRGB, Lab), abstract, named color.
- **ICC v4 vs v2:** ICC.1:2022 defines profile version 4.4 (technically aligned with ISO 15076-1). v4 tightened the perceptual intent with a reference medium and black point. v2 profiles are still widespread; some older software handles only v2. Ship the version the target workflow supports, and test.
- **iccMAX (ICC.2, "v5"):** spectral data, selectable illuminants and observers, alternative PCS processing. An extension for needs v4 can't meet, not a replacement; v4 CMMs can't read iccMAX profiles.

## Calibration vs characterization
- **Calibration:** adjust the device to a known, repeatable state (white point, luminance, tone response, ink limits, press linearization).
- **Characterization / profiling:** measure the calibrated device and build a profile describing it.
- They are distinct steps. A profile is valid only while the device stays in the calibrated state; recalibrate and re-verify on a schedule.
- **Monitor targets are context-dependent:** e.g., a D65-ish white and moderate luminance for web/video work; D50-ish white and luminance matched to a viewing booth for print soft proofing. State the target white, luminance (cd/m²), tone response (sRGB, gamma 2.2, BT.1886) and ambient conditions. There is no single correct target.

## Rendering intents
| Intent | What it does | Use for |
|---|---|---|
| Perceptual | Compresses the whole source gamut into the destination, preserving relationships; out-of-gamut and in-gamut colors both change | Photos and images with many out-of-gamut colors |
| Relative (media-relative) colorimetric | Maps source white to destination white; in-gamut colors match colorimetrically relative to the media white; out-of-gamut colors clip | Logos, brand and spot colors, proofs where paper white should be the destination paper; most graphics |
| + Black point compensation (BPC) | Scales the source black to the destination black to keep shadow detail with relative colorimetric | Use when shadow detail matters and source black is deeper than destination black; state on/off |
| Saturation | Preserves vividness over accuracy (vendor-dependent) | Business graphics and charts where hue accuracy matters less |
| ICC-absolute colorimetric | Matches including the source media white (simulates paper color) | Proofing: simulating one device or paper on another |
State the intent and BPC setting for every transform. BPC is standardized separately (ISO 18619, not accessed).

## Soft proofing and print proofing
- **Soft proof:** display simulates the output (press profile, intent, paper white, ink black) on a calibrated display. Valid only with a profiled display and appropriate viewing conditions.
- **Hard proof:** a contract proof printed to a characterization target and verified by measurement (control strip).
- **Viewing:** graphic arts compares prints and proofs under D50 viewing conditions (ISO 3664: D50 source, defined illuminance levels for critical comparison vs practical appraisal, neutral surround). Print process targets come from ISO 12647 parts. These standards were not accessed; the summary comes from an ICC-hosted presentation (Cheydleur). If the project needs conformance, obtain the standard; otherwise report "not verified".

## Brand colors to print
- sRGB brand colors (bright blues, greens, oranges) may lie outside a coated-paper gamut. Convert with the printer's characterization or press profile (stated intent and BPC); don't hand-pick CMYK from the sRGB value.
- **Acceptance target** is the profile-predicted Lab (or the agreed proof), not the source sRGB Lab.
- Critical brand colors that can't be reached in CMYK: specify a spot color (e.g., a Pantone ink) as fallback, agreed with the brand owner.
- **Characterization data:** confirm with the printer. Examples only: FOGRA51 (PSO Coated v3, premium coated), GRACoL2013 (CRPC6), Japan Color 2011 (coated).
- **Measurement condition:** state it. M1 for substrates with optical brighteners and current graphic-arts practice; M0 only for legacy data (per the ICC-hosted ISO 13655 summary; standard not verified).
- **Substrate white:** measure the paper white; state whether Lab values are media-relative or absolute.
- **Tolerance:** use the job spec's. If it has none, propose a labelled, provisional tolerance (e.g., ΔE00 per patch and as an average over patches) for sign-off. ISO 12647-2 tolerances may be cited only as not verified.

## Embedding profiles in images
- Tag every image with its profile (sRGB, Display P3, a press profile) or know the convention. **Untagged images and CSS colors are treated as sRGB** on the web.
- Converting vs assigning: **convert** changes numbers to keep appearance; **assign** keeps numbers and changes appearance. Never assign to "fix" a mismatch.
- Strip large profiles from tiny web images only if they are sRGB; keep P3 tags.

## Wide gamut workflows
- Master in a space at least as wide as the widest output (Display P3 or Rec. 2020 for screens; the press profile or a wide RGB for print).
- Export Display P3 assets with an embedded profile (16-bit PNG for gradients, per Apple guidance) plus sRGB variants or rely on CMS conversion; check that distinct P3 colors stay distinct on sRGB and gradients don't band or clip.
- Web: gate wide values with `@media (color-gamut: p3)` and always define sRGB fallbacks ([rgb-and-compositing](rgb-and-compositing.md)).

## HDR
- **PQ (SMPTE ST 2084, in BT.2100):** absolute luminance encoding up to 10,000 cd/m². Content mastered at a stated peak (e.g., 1000 cd/m²) and mastering display.
- **HLG (BT.2100):** relative, display-adapted; diffuse white at 75% signal in CSS Color HDR's description.
- **Reference white:** HDR reference/graphics white of **203 cd/m²** (from ITU-R BT.2408, as adopted by CSS Color HDR). Place SDR UI and graphics at reference white; reserve **headroom** above it for highlights only.
- **CSS:** `rec2100-pq`, `rec2100-hlg`, `rec2100-linear` and `dynamic-range-limit` are in a Working Draft (CSS Color HDR, Sep 2026). `@media (dynamic-range: high)` detects capable displays. Treat as experimental; never put UI text in HDR headroom.
- Tone mapping HDR → SDR is display/OS-dependent; preview on SDR too.

## Measurement
- **Spectrophotometer:** measures spectral reflectance/transmittance (or emission); compute XYZ for any illuminant/observer. Needed for print, paint, spectral data, fluorescence questions.
- **Colorimeter:** filter-based, measures display output in XYZ-like terms; fast for display calibration, needs a correction matrix or spectral sample for each display technology.
- **Geometry:** 45°/0° (or 0°/45°) excludes specular gloss, matches visual print assessment, standard for graphic arts; d/8° (sphere) with specular included or excluded is common for paint, plastics, textiles. Only compare readings taken with the same geometry.
- **Measurement conditions (ISO 13655, per the ICC-hosted summary):** M0 illuminant A-like, UV undefined (legacy); M1 D50-matched including UV, so optical brighteners fluoresce as under D50; M2 UV-cut; M3 polarized + UV-cut (reduces gloss; for press density work). Readings under different M conditions are not comparable, especially on papers with optical brighteners.
- **Backing:** white or black backing changes readings on thin substrates; state it.
- **Repeatability vs inter-instrument agreement:** repeatability is the same instrument re-measuring; inter-instrument agreement is between units/models and is usually worse. Report both if available, and stay within one instrument for tight tolerances.
- **Report:** instrument model, geometry, M condition, backing, illuminant/observer for computed values, white reference, number of readings and their spread, ΔE formula (ΔE00 or ΔE\*ab) with its parametric factors, and the tolerance from the job spec. State uncertainty; a ΔE smaller than the measurement uncertainty is not a meaningful pass or fail.

## Sources
- ICC.1:2022 (v4.4, PCS D50 values, intents, ISO 15076-1 relation) and iccMAX overview: [ICC and ISO](sources.md#icc-and-iso).
- Characterization data names (FOGRA51, CRPC6/GRACoL2013, Japan Color 2011): ICC profile registry [ICC and ISO](sources.md#icc-and-iso). "PSO Coated v3" as FOGRA51's profile name: general practice, not verified there.
- ISO 3664, ISO 12647, ISO 13655, ISO 18619: [Inaccessible standards](sources.md#inaccessible-standards); summaries from Cheydleur, "ISO 13655 measurement conditions" (ICC presentation) [ICC and ISO](sources.md#icc-and-iso).
- CSS Color HDR (203 cd/m², PQ/HLG spaces, `dynamic-range-limit`), Media Queries 5: [W3C](sources.md#w3c).
- BT.2100, BT.2408 (reference pages; full texts not accessed): [ITU and SMPTE](sources.md#itu-and-smpte).
- Apple HIG Color (P3, 16-bit PNG, variations), Android wide color gamut: [Platforms](sources.md#platforms).
- Instrument types, geometries, repeatability: general colorimetry practice; CIE 015:2018 not accessed.
