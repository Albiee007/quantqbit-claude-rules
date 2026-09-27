# Continuous (panorama) style

An optional style for the whole screenshot set. The gallery is designed as **one strip**, and each screenshot is a window onto it. A ribbon swoops from frame to frame, coins and receipts are cut by a frame edge and continue in the next one, a tilted phone straddles two frames, and backgrounds alternate while staying linked. In a store gallery that you swipe through, the set reads as one piece.

Pick it in `frames.json` with `"layout": "continuous"`, or start from `render_frames.py init <kit> --style continuous`. **Ask the user which style they want (classic or continuous) before storyboarding.** Classic is the default.

## When to choose it
- Choose continuous for brands with a strong visual motif (a ribbon, a shape, props from the domain like coins, tickets or leaves) and a set of 5–8 frames that people swipe through.
- Choose classic when frames will be seen alone most of the time, e.g. localised sets swapped per market, or when the team needs to swap single frames often. In continuous mode, changing one frame can break its neighbours.

## Rules (not overridable)
1. **Every frame must read on its own.** The stores show frames individually: search results show the first 3, and review tools show one at a time. Seams carry **decoration only**. Captions, toasts, cards and any text stay inside one frame; the renderer rejects text objects that cross a seam unless `"allowCross": true`.
2. **Frame 1 is self-contained** and carries the promise. It's often the only frame people see.
3. **Each frame's primary phone stays inside its frame** (`device.x` 0.2–0.8). A phone that crosses a seam is an extra `phone` object.
4. **Every iOS frame shows the app** (App Store 2.3.3). A brand-only or photo-only frame (`"screen": null`) must be `"platforms": ["android"]`. Use at most one, never as frame 1, and put it **last**, because on iOS it's skipped and the seam next to it breaks.
5. **Photos are licensed:** every `image` object carries a `"license"` note ("own photo, model releases on file", "licensed from X, ID 123"). No real users' photos without written consent, and no stock faces used as if they were customers.
6. **The fidelity rule from the skill still applies:** props must fit the app (receipts only if the app handles receipts), and nothing implies a feature the app lacks.

## Designing the strip
- **One hero motif.** A single ribbon, or one prop family, runs through the whole strip. Two competing motifs look busy.
- **Seam budget:** at most 1–2 crossing objects per seam. Let some seams be clean.
- **Rhythm:** alternate background treatments (gradient, then light, then gradient) using `"background": {"mode": "per-frame"}`. The ribbon and the crossing props make the jump between them feel continuous. One gradient running the whole strip (`"mode": "continuous"`) is the calmer option.
- **Caption placement:** mix `caption.pos` top and bottom so the eye moves along the strip. Use `"tone": "dark"` on light backgrounds.
- **Depth:** `"z": "back"` objects sit behind the phones and captions (ribbons default to back); everything else sits in front. Put props that touch a phone in front of it, and background shapes behind.
- **Gutters:** stores draw a gap between frames, so a crossing object reads as "continuing behind the gap". Leave `gutter` at 0 unless you want to align precisely with one store's gap (px at 1080 wide).
- **Preview the strip the way stores show it:** `contact_sheet.py <out>/play/phone --strip --check-seams`. A crossing object shows up as matching rows at that seam. A low match is normal where the background changes.

## frames.json reference (continuous)
```jsonc
{
  "layout": "continuous",
  "gutter": 0,
  "brand": { "bg1": "#2a1bb0", "bg2": "#3525cd", "bg3": "#5b4ff0", "accent": "#9ff3cf", "sub": "#dcd9ff",
             "ink": "#131b2e", "ribbon1": "#7c6cf6", "ribbon2": "#3525cd", "headFont": "Inter", "glyphs": ["$", "€"] },
  "background": { "mode": "continuous", "stops": ["#2a1bb0", "#5b4ff0"] },
  //  or        { "mode": "per-frame", "glyphs": false, "frames": [ { "type": "gradient" }, { "type": "solid", "color": "#f6f5ff" },
  //                                                                  { "type": "image", "src": "assets/bg.jpg" }, { "css": "…any CSS background…" } ] }
  "frames": [
    { "id": "01-home", "screen": "home", "head": "Headline with <em>accent</em>", "sub": "Sub-caption",
      "caption": { "pos": "top", "tone": "light" },                        // pos: top | bottom; tone: light | dark
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
Common properties on every object: `x`, `y`, `w`, `rotate` (degrees), `opacity`, `z`, `shadow` (default true), `style` (extra CSS), and `allowCross` (text objects only).

| type | Extra props | Crosses seams? |
|---|---|---|
| `ribbon` | `points` [[x,y]…] (strip units), `w` (thickness), `colors` [..], `texture` "dots" or "none", `cap` | Yes, it's the connector |
| `coin` | `glyph`, `metal` "silver", "gold" or "brand", `tilt` (3D squash, degrees) | Yes |
| `chip` | `glyph`, `color`, `bg` | Yes |
| `receipt` | `title`, `sub`, `lines` [[label, value]], `total` [label, value], `footer` | Yes (it's a prop) |
| `calendar` | `day`, `weekday`, `month`, `color` | Yes |
| `phone` | `screen` (a screens.js name), `w` | Yes (the secondary phone) |
| `image` | `src`, `h`, `mask` "none", "rounded" or "circle", `fit`, `position`, **`license`** | Yes, if the photo tolerates cropping |
| `toast` | `title`, `body`, `icon` ("ion|material"), `iconBg` | **No** |
| `card` | `label`, `value`, `sub`, `tone` "positive", "negative" or "brand", `avatars` | **No** |
| `brand` | `text`, `src` (logo), `size`, `color`, `gradient` [c1, c2], `glow` | **No** |
| `text` | `text` (HTML allowed), `size`, `weight`, `color`, `align`, `font` | **No** |
| `html` | `html` (raw markup, sized in em; 1em = w/10) | Your call |

### Custom objects (per app)
Create `custom-objects.js` in the kit folder. `frame.html` loads it after the built-ins:
```js
// Every renderer returns HTML; 1em = one tenth of the object's width, so size in em.
OBJECTS.ticket = (o, u) => `<div style="width:10em;height:4.5em;border-radius:.8em;background:#fff;display:grid;place-items:center">
  <span style="font:800 1.4em Inter;color:${u.B.bg2}">${u.esc(o.label || 'BOARDING PASS')}</span></div>`;
```
Helpers available as `u`:
- `X(x)`, `Y(y)`, `S(w)` convert units to px.
- `W`, `H`, `stripW` are the canvas and strip sizes.
- `B` is the brand.
- `I(name, px, color)` draws an icon.
- `device(screen, widthPx)` returns a phone.
- `esc()` escapes text.

The renderer warns (instead of failing) about unknown types when this file exists.

## Workflow additions (continuous)
1. **Pick the motif:** the ribbon colours and which props suit the app's domain and brand.
2. **Seam plan:** a table with one row per seam, listing what crosses it and what each frame keeps to itself.

   ```
   | seam | crossing object | notes |
   |------|-----------------|-------|
   | 1|2  | coin €          | caption of 2 stays clear |
   ```
3. **Place the objects in frames.json,** then check with `render_frames.py render <kit> --check-only`.
4. **Render one size, then preview:** `contact_sheet.py … --strip --check-seams`. Iterate, then run `render --all`, which renders every size and writes the strips with their seam reports.
5. **QA each frame alone** as well as the strip: every frame must still make sense cropped out of the strip.
