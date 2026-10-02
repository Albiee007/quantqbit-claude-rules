# Continuous (panorama) style

An optional style for the whole screenshot set. The gallery is designed as **one strip**, and each screenshot is a window onto it. A band, shapes or the project's motif run from frame to frame, objects are cut by a frame edge and continue in the next one, a tilted phone straddles two frames, and backgrounds change while staying linked. In a store gallery that you swipe through, the set reads as one piece.

It is chosen as part of a store concept (creative-direction concept round), or by the owner up front. In a format-2 kit it is `"style": "continuous"` in `frames.json`; start one with `render_frames.py init <kit> --style continuous`. Colours, type, backgrounds and the motif come from the approved concept, so two projects' panoramas don't share a look. (A 1.6 kit uses `"layout": "continuous"` and the 1.6 engine; see [art-direction](art-direction.md) to migrate it.)

## When to choose it
- Choose continuous for brands with a strong visual motif (the direction's motif, a band, a shape, props from the product's own domain) and a set of 5–8 frames that people swipe through.
- Choose classic when frames will be seen alone most of the time, e.g. localised sets swapped per market, or when the team needs to swap single frames often. In continuous mode, changing one frame can break its neighbours.

## Rules (not overridable)
1. **Every frame must read on its own.** The stores show frames individually: search results show the first 3, and review tools show one at a time. Seams carry **decoration only**. Captions, toasts, cards and any text stay inside one frame; the renderer rejects text objects that cross a seam unless `"allowCross": true`.
2. **Frame 1 is self-contained** and carries the promise. It's often the only frame people see.
3. **Each frame's primary phone stays inside its frame** (`device.x` 0.2–0.8). A phone that crosses a seam is an extra `phone` object.
4. **Every iOS frame shows the app** (App Store 2.3.3). A brand-only or photo-only frame (`"screen": null`) must be `"platforms": ["android"]`. Use at most one, never as frame 1, and put it **last**, because on iOS it's skipped and the seam next to it breaks.
5. **Photos are licensed:** every `image` object carries a `"license"` note ("own photo, model releases on file", "licensed from X, ID 123"). No real users' photos without written consent, and no stock faces used as if they were customers.
6. **The fidelity rule from the skill still applies:** props must fit the app (receipts only if the app handles receipts), and nothing implies a feature the app lacks.
7. **Captions follow the concept:** each frame's `background` (from the concept) brings its own caption colours, so a caption never sits on a background whose text colours weren't chosen for it.

## Designing the strip
- **One hero motif.** The direction's motif, a single band, or one prop family runs through the whole strip. Two competing motifs look busy.
- **Seam budget:** at most 1–2 crossing objects per seam. Let some seams be clean.
- **Rhythm:** alternate the concept's backgrounds per frame (`"background": "<name>"`), or keep one throughout for a calmer strip. The band and the crossing objects make the jump between them feel continuous.
- **Caption placement:** mix `caption.pos` top and bottom so the eye moves along the strip.
- **Depth:** `"z": "back"` objects sit behind the phones and captions (ribbons default to back); everything else sits in front. Put props that touch a phone in front of it, and background shapes behind.
- **Gutters:** stores draw a gap between frames, so a crossing object reads as "continuing behind the gap". Leave `gutter` at 0 unless you want to align precisely with one store's gap (px at 1080 wide).
- **Preview the strip the way stores show it:** `contact_sheet.py <out>/play/phone --strip --check-seams`. A crossing object shows up as matching rows at that seam. A low match is normal where the background changes.

## frames.json reference (continuous, format 2)
```jsonc
{
  "format": 2,
  "artDirection": { "family": "store" },
  "style": "continuous",
  "gutter": 0,
  "props": ["finance"],                                                       // optional prop packs
  "frames": [
    { "id": "01-home", "screen": "home", "head": "Headline with <em>accent</em>", "sub": "Sub-caption",
      "background": "dawn",                                                   // a background from the concept
      "caption": { "pos": "top" },                                            // top | bottom
      "device":  { "x": 0.5, "y": 0.62, "scale": 1, "rotate": 0, "bleed": "none" } },   // all optional
    { "id": "08-brand", "screen": null, "platforms": ["android"] }
  ],
  "objects": [ /* see below; drawn in order, z: "back" | "front" */ ]
}
```

### Units
- `x`: **frame units** along the strip. `0` is the left edge of frame 1, `0.5` its centre, `1.0` the seam between frames 1 and 2, and `N` the right end.
- `y`: a fraction of the height. `w` and `h`: fractions of the frame width.
- One config therefore renders correctly at every store size.

### Built-in objects
Common properties on every object: `x`, `y`, `w`, `rotate` (degrees), `opacity`, `z`, `shadow` (default true), and `allowCross` (text objects only). Colours are **role names** from the direction (`"accent"`, `"ink"`, `"surface"`) or CSS colours; type comes from the direction's font roles.

| type | Extra props | Crosses seams? |
|---|---|---|
| `ribbon` | `points` [[x,y]…] (strip units), `w` (thickness), `colors` [roles], `texture` "none", "dots" or "lines", `cap` | Yes, it's the connector |
| `shape` | `shape` "circle", "blob", "arc" or "pill", `color`, `outline` | Yes |
| `phone` | `screen` (a screens.js name), `w` | Yes (the secondary phone) |
| `image` | `src`, `h`, `mask` "none", "rounded" or "circle", `fit`, `position`, **`license`** | Yes, if the photo tolerates cropping |
| `toast` | `title`, `body`, `icon` ("ion-name/material_name" joined by a bar) | **No** |
| `card` | `label`, `value`, `sub`, `tone` (a role name) | **No** |
| `brand` | `text`, `src` (logo), `size`, `color` | **No** |
| `text` | `text` (escaped; `<em>` marks the accent), `size`, `font` (a font role), `color`, `align` | **No** |
| `html` | `html` (raw markup you write, sized in em; 1em = w/10) | Your call |
| `coin`, `chip`, `receipt`, `calendar` | with `"props": ["finance"]`: as in 1.6, coloured from the roles; `calendar` needs its `month` | Yes |

### Custom objects (per app)
Create `custom-objects.js` in the kit folder. `frame.html` loads it after the built-ins:
```js
// Every renderer returns HTML; 1em = one tenth of the object's width, so size in em.
OBJECTS.ticket = (o, u) => `<div style="width:10em;height:4.5em;border-radius:.8em;background:${u.R.surface};display:grid;place-items:center">
  <span style="font-family:${u.T.display.stack};font-size:1.4em;color:${u.R.accent}">${u.esc(o.label)}</span></div>`;
```
Helpers available as `u`:
- `X(x)`, `Y(y)`, `S(w)` convert units to px.
- `W`, `H`, `stripW` are the canvas and strip sizes.
- `R` holds the direction's colour roles and `T` its font roles (`T.display.stack`).
- `I(name, px, color)` draws an icon; `device(screen, widthPx)` returns a phone.
- `esc()` escapes text; `copy()` escapes it and keeps `<em>`.

The renderer warns (instead of failing) about unknown types when this file exists.

## Workflow additions (continuous)
1. **Pick the motif** from the direction (its `motif`, roles and `keep` list): which band, shapes or props suit this product.
2. **Seam plan:** a table with one row per seam, listing what crosses it and what each frame keeps to itself.

   ```
   | seam | crossing object | notes |
   |------|-----------------|-------|
   | 1|2  | blob (accent)   | caption of 2 stays clear |
   ```
3. **Place the objects in frames.json,** then check with `render_frames.py render <kit> --check-only`.
4. **Preview one size:** `render_frames.py preview <kit> --sizes play-phone`, then `contact_sheet.py <preview>/play/phone --strip --check-seams`. Iterate, then run `render --all` (with the approved concept), which renders every size and writes the strips with their seam reports.
5. **QA each frame alone** as well as the strip: every frame must still make sense cropped out of the strip.
