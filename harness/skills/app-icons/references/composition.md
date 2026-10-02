# Icon composition

The platform rules (opaque iOS tile, transparent adaptive foreground inside 66/108, white notification silhouette) are fixed. Everything else is a project choice, made in the icon concept and approved by the owner.

## Background
| Recipe | Flags | Notes |
|---|---|---|
| solid | `--bg` | the calmest; the mark carries everything |
| linear | `--bg-style linear --bg A --bg2 B [--angle 160] [--space oklab]` | interpolated in OKLab by default (no muddy midpoint); `--angle` uses the CSS convention (180 = top to bottom). The Android adaptive background becomes an image (`backgroundImage`), with `backgroundColor` set to the gradient's midpoint for launchers that ignore images |

From the direction: `--from-direction .` reads the approved icon concept (`background`, `glyphScale`, `glyphOffset`, `qualityTarget`) and refuses while it is not approved and current.

## Glyph scale and placement
- `--glyph-scale` (0.3–0.8, default 0.6): share of the tile the glyph's longest side fills. Small, dense marks read better large; open shapes need air. Favicons always use 0.9 (they are tiny).
- `--glyph-offset x,y` (−0.1..0.1): optical correction or a deliberate off-centre composition. Adaptive and maskable layers clamp the offset so the glyph stays inside their safe circles; the iOS and Play tiles take it as given.
- The adaptive foreground is capped at 95% of the safe zone automatically.

## Mark contrast
Printed for every set: the glyph's main colour against the background under it (the lowest value across a gradient). A launcher icon is branding, so this is not a WCAG requirement. A project can set a target (`--mark-contrast 3`, or `qualityTarget.markContrast` in the concept); then a lower value fails and nothing is written.

## Preview before switching
`make_icon_set.py preview --master <png> (--bg ... | --from-direction . [--concept <file>]) -o <sheet.png>` draws the icon at 16, 29, 40, 48, 64 and 180 px on light and dark wallpapers, in circle and squircle masks, plus the monochrome silhouette. Use it in concept mode and for the owner's before-and-after check.
