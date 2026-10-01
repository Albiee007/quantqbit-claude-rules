# RGB Spaces, Compositing and Gamut

## An RGB space is three things
1. **Primaries:** the chromaticities of R, G, B.
2. **White point:** usually D65 for display spaces.
3. **Transfer function:** how encoded values relate to linear light.
An "RGB value" without its space is ambiguous. `#ff0000` in sRGB and `color(display-p3 1 0 0)` are different colors.

## Common spaces
| Space | Primaries | White | Transfer | Use |
|---|---|---|---|---|
| sRGB (IEC 61966-2-1) | Rec. 709 primaries | D65 | sRGB piecewise | Web default, untagged content |
| Display P3 | DCI-P3 primaries | D65 | sRGB piecewise | Apple devices, modern phones and laptops |
| Rec. 709 (ITU-R BT.709) | same as sRGB | D65 | camera OETF; display EOTF per BT.1886 | HD video |
| Rec. 2020 (ITU-R BT.2020) | very wide (spectral-locus primaries) | D65 | SDR: BT.709-style; HDR: PQ or HLG (BT.2100) | UHD/HDR video, future-proof masters |
| Adobe RGB (1998) (`a98-rgb` in CSS) | wider greens than sRGB | D65 | pure power ≈ 2.2 | Photography, print-oriented editing |
| ProPhoto RGB | very wide, some imaginary | D50 | power 1.8 | Raw photo editing only |

## Transfer functions
- **sRGB EOTF (decode, 0–1):** `c ≤ 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055)^2.4`.
- **sRGB inverse (encode):** `l ≤ 0.0031308 ? 12.92 · l : 1.055 · l^(1/2.4) − 0.055`.
- **Gamma 2.2 vs piecewise:** a pure 2.2 power curve and the sRGB piecewise curve agree in midtones and differ most in the darkest values. Pick one per pipeline and state it; mixing them shifts shadows.
- **BT.1886:** reference display EOTF for HD (power 2.4 with black-level terms). Video graded on BT.1886 looks different on an sRGB-decoding monitor.
- **PQ (SMPTE ST 2084, BT.2100):** absolute; encoded value maps to cd/m² up to 10,000. Content is mastered for a specific peak.
- **HLG (BT.2100):** relative, scene-referred; adapts to display peak; designed for broadcast compatibility.

## Linear-light operations
Do these on linear values (decode, operate, re-encode):
- Blending and mixing physical light (crossfades, glows, lighting).
- Scaling intensity, exposure, multiplying by opacity for physically correct results.
- Luminance (WCAG relative luminance is computed from linearized sRGB).
- Resizing and filtering images (gamma-space downscaling darkens fine detail and high-contrast edges).
- CVD simulation (linearize first, or results are too dark).
Do perceptual operations (ramps, uniform steps, hue rotation) in a perceptual space instead ([perceptual-spaces](perceptual-spaces.md)).

## Alpha compositing
- **Porter–Duff** defines the operators (source-over is the default). Simple source-over with straight alpha: `co = Cs·αs + Cb·αb·(1 − αs)`, `αo = αs + αb·(1 − αs)`, result color `Co = co / αo`.
- **Premultiplied alpha** stores `C·α`. Filtering, resizing and interpolation must happen on premultiplied values, or transparent pixels bleed their (often black) color into edges.
- **Browsers composite in gamma-encoded sRGB in practice.** The Compositing spec does not mandate linear light, and CSS legacy colors interpolate in gamma-encoded sRGB. So `rgba(0,0,0,0.5)` over white yields encoded ~#808080, not linear 50% light.
- **For contrast measurement:** compute the composited color the way the renderer does (gamma-encoded source-over for web), then compute contrast on that result. Never test a translucent token in isolation. Test over every backdrop it can appear on (surface, raised surface, image, dark theme).
- Native platforms may composite differently (e.g., linear or extended-range on wide-color surfaces). Measure on-device when it matters.

## Interpolation (CSS Color 4 and 5)
- Gradients and `color-mix()` take an interpolation space: `linear-gradient(in oklab, …)`, `color-mix(in oklch, a 40%, b)`.
- Default when the host syntax doesn't specify one is **Oklab**. Gradients between only legacy sRGB colors keep sRGB (gamma-encoded) interpolation for compatibility unless a space is named.
- Polar spaces (OKLCH, LCH, HSL) take a hue method: `shorter` (default), `longer`, `increasing`, `decreasing`.
- Interpolation is **premultiplied** (alpha applied before, undone after), so fading to transparent doesn't go gray.
- Choice: OKLab for smooth, even mixes; OKLCH for hue-preserving ramps (watch gamut); linear sRGB for physically correct light mixing; gamma sRGB only for legacy matching.

## Gamut mapping
- **Clipping** (clamping each channel) is fast but shifts hue and lightness and flattens gradients.
- **Chroma reduction** keeps lightness and hue, lowers chroma until in gamut. CSS Color 4's algorithm for RGB destinations works in **OKLCh**: binary-search chroma, and stop when the clipped color is within **ΔEOK 0.02** (one JND) of the candidate; then clip.
- Ottosson's gamut-clipping article compares lightness-preserving chroma compression, projection toward a fixed lightness, and adaptive blends.
- **Deliberate mapping:** for tokens, choose the sRGB fallback by hand (or with the CSS algorithm) and check its contrast. Don't let each browser or OS pick.

## Wide gamut on the web
- `color(display-p3 r g b)`, `color(rec2020 …)`, `oklch()`, `lab()` can express out-of-sRGB colors.
- `@media (color-gamut: p3)` (also `srgb`, `rec2020`) gates wide values (values below are illustrative, not a computed match):
  ```css
  :root { --accent: #2f6fd6; }
  @media (color-gamut: p3) { :root { --accent: color(display-p3 0.16 0.42 0.88); } }
  ```
- Contrast must pass with **both** the fallback and the wide value.
- **HDR:** `dynamic-range-limit: standard | constrained | no-limit` and `rec2100-pq`, `rec2100-hlg`, `rec2100-linear` are in the CSS Color HDR Working Draft. Treat as experimental; check support before shipping.

## Native wide gamut
- **Android:** `android:colorMode="wideColorGamut"` per activity (API 26+). Costs memory and GPU composition; enable only where it pays (full-screen photo viewers). Check `Configuration.isScreenWideColorGamut()`; use `ColorSpace` and `Bitmap.getColorSpace()`.
- **Apple:** color sets in asset catalogs can specify Display P3 components; export wide-color images as 16-bit Display P3 PNG; provide sRGB variants when two P3 colors become indistinguishable or gradients clip on sRGB displays.

## Sources
- CSS Color 4 (predefined spaces, sRGB transfer code, interpolation default Oklab, hue methods, premultiplied interpolation, OKLCh gamut mapping with ΔEOK JND 0.02): [W3C](sources.md#w3c).
- CSS Color 5 (`color-mix()` default Oklab): [W3C](sources.md#w3c).
- Compositing and Blending 1 (Porter–Duff, simple alpha compositing): [W3C](sources.md#w3c).
- CSS Color HDR, Media Queries 5: [W3C](sources.md#w3c).
- Ottosson, sRGB gamut clipping: [Research](sources.md#research).
- BT.709, BT.1886, BT.2020, BT.2100: [ITU and SMPTE](sources.md#itu-and-smpte) (reference pages only).
- IEC 61966-2-1, SMPTE ST 2084: [Inaccessible standards](sources.md#inaccessible-standards).
- Android wide color gamut, Apple HIG Color: [Platforms](sources.md#platforms).
