# Data Visualization Color

Use the project's chart palette if one exists. Otherwise choose by data type, verify, and record it as tokens (`color.data.categorical.1…n`, `color.data.sequential.*`, `color.data.diverging.*`).

## Palette type by data
| Data | Palette | Rule |
|---|---|---|
| Categorical (nominal) | Qualitative: distinct hues, similar emphasis | No implied order. Vary lightness too, so pairs survive CVD and grayscale. |
| Sequential (ordered, one direction) | Monotonic lightness ramp, light→dark (or reverse on dark backgrounds) | Lightness carries the order; hue change is optional. |
| Diverging (signed around a meaningful midpoint: 0, mean, target) | Two sequential ramps meeting at a light (or dark) neutral midpoint | Midpoint must be the real reference value; both arms equal perceptual length. |
| Cyclic (angle, phase, time of day, direction) | Ramp whose ends match | Start and end colors identical; no false seam. |
| Multi-sequential | Two ramps for data with distinct sides that aren't a single diverging scale | Keep each side uniform. |

## Perceptually uniform ramps
- Equal data steps should look like equal color steps. Use a perceptually uniform, monotonic-lightness map:
  - the **viridis** family (viridis, magma, inferno, plasma): designed uniform in CAM02-UCS, readable in grayscale, friendlier to common CVD;
  - **scientific colour maps** (Crameri) for sequential, diverging, cyclic;
  - **OKLCH ramps** built with even L steps and gamut-mapped chroma ([perceptual-spaces](perceptual-spaces.md)).
- Check a ramp by converting to grayscale (or plotting its L): lightness must be monotonic for sequential data.
- Classed (binned) maps: use a ramp sampled evenly in lightness, not evenly in hex.

## Avoid rainbow / jet for ordered data
- Rainbow-like maps are not perceptually uniform or ordered: they create false boundaries (bright yellow and cyan bands), hide real gradients, and fail for red-green CVD. Crameri et al. report visual error that can exceed several percent of the data range. Borland & Taylor (2007) argued the same for visualization.
- If a domain convention demands rainbow (some legacy maps), document it, provide a uniform alternative, and label values directly.

## Categorical sets
- **Max categories (heuristic):** beyond about 6–8 hues, colors stop being reliably distinguishable and nameable. Group the long tail as "Other", use small multiples, or label directly instead of adding hues.
- **CVD-safe starting points:** Okabe–Ito Color Universal Design palette (built around vermilion instead of pure red, bluish green, sky blue and reddish purple; take exact values from the source), ColorBrewer qualitative sets marked colorblind-safe. Verify the chosen set by CVD simulation with your actual backgrounds.
- Avoid red-vs-green as the only distinction (e.g., profit/loss): use blue/orange, or add +/− signs, arrows, and labels.
- Assign colors consistently: the same category gets the same color across every chart in the product.

## Redundant encoding
- Never encode a series only by color (WCAG 1.4.1): add **direct labels**, marker **shapes**, line **dash styles**, **patterns/textures** for fills, or position/order.
- Prefer **direct labeling** next to lines and bars over a separate legend. If a legend is needed, keep it adjacent and in the same order as the data.
- Provide the data in text form (table, summary) for complex charts.

## Contrast for charts
- **1.4.11 Non-text contrast:** each meaningful mark (line, bar, slice, marker, focusable data point) needs ≥ 3:1 against its **adjacent background**. Series-to-series 3:1 matters only where marks touch and color is the only boundary between them; otherwise a separating border/gap (≥ 3:1) or redundant cues (labels, dashes, markers, patterns) carry the distinction.
- **1.4.3 Text:** axis labels, tick labels, data labels and legends need 4.5:1 (3:1 for large text), including labels placed on top of colored bars.
- Light categorical colors (yellows, light greens) often fail 3:1 on white: add a darker outline, or use them only with direct labels.
- Gridlines are usually decorative; keep them low contrast unless they carry values.

## Forced colors
- Forced colors replace SVG `fill` and `stroke` with system colors, so every series can collapse to one color. Keep series distinct by **dash style, marker shape, pattern** and direct labels, never by color alone.
- `forced-color-adjust: none` is acceptable only for meaningful series swatches/marks whose colors are the content; keep axes, text and chrome forced, and check those swatches still have 3:1 against `Canvas`.
- Axes, ticks and labels: `CanvasText` on `Canvas`. Focus on data points: `outline` (survives forced colors; `box-shadow` doesn't).
- Test in Windows High Contrast (contrast themes), light and dark variants.

## Dark-theme charts
- Don't reuse light-theme chart colors unchanged. Rebuild: sequential ramps run dark→light on dark backgrounds so high values stand out; reduce chroma of saturated categorical colors; re-check 3:1 against the dark surface.
- Keep category→color assignment stable between themes (same hue family), changing only lightness and chroma.

## Interaction states in charts
- Hover/selected data: emphasize by outline, size or dimming others, not by a new hue alone.
- Focus on data points (keyboard-navigable charts): visible focus ring ≥ 3:1.

## Checklist
- [ ] Palette type matches the data type.
- [ ] Ordered data: lightness monotonic; no rainbow/jet.
- [ ] Categorical: ≤ ~6–8 hues (heuristic), CVD-simulated, consistent assignment.
- [ ] Redundant encoding and direct labels.
- [ ] 3:1 for marks vs adjacent background; 4.5:1 for labels; every theme the project supports.
- [ ] Forced colors: series still distinct (dash, marker, pattern, labels).

## Sources
- Crameri, Shephard, Heron 2020, "The misuse of colour in science communication" (map classes, uniformity, CVD, rainbow errors): [Research](sources.md#research).
- Borland & Taylor 2007 (abstract metadata only, full text not accessed): [Research](sources.md#research).
- viridis design (BIDS colormap page); Okabe & Ito Color Universal Design; ColorBrewer scheme types: [Research](sources.md#research).
- WCAG 2.2 Understanding 1.4.1 and 1.4.11: [W3C](sources.md#w3c).
- Forced colors (SVG `fill`/`stroke` forced, `forced-color-adjust: none`, `CanvasText`): MDN `forced-colors` [Platforms](sources.md#platforms); CSS Color Adjust 1 [W3C](sources.md#w3c).
- The 6–8 category limit is a common practitioner heuristic, not from a verified source.
