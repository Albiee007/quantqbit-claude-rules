# Modes and migration

## Three modes
| Mode | What it is | Gates | Where it writes |
|---|---|---|---|
| legacy | a 1.6 asset that predates the direction (a frames.json without `"format"`, an HTML or SVG export of your own, `--bg` icons) | none, as in 1.6 | where it always did, now staged and checked first |
| draft preview | any concept, approved or not, for the owner to look at | none | only its own preview folder (gitignored) or temporary space |
| approved production | a format-2 kit, a canvas entry, `--from-direction` icons | Gate 1 and the family's Gate 2, current | the production destination, published only after every check passes; a run manifest in `brand/runs/` |

## Commands by mode
| Command | Mode |
|---|---|
| `render_frames.py init` | creates a format-2 kit (content files only) |
| `render_frames.py render` on a 1.6 kit | legacy (frozen 1.6 engine, pixel-identical output, migration warning) |
| `render_frames.py render` on a format-2 kit (any `--frames`/`--sizes`) | production; `--check-only` reports the gates without rendering |
| `render_frames.py preview` | draft preview (format 2 only) |
| `render_frames.py contrast` | a check; 1.6 kits use the 1.6 thresholds, format-2 kits the selected or given concept |
| `export_svg.py SRC ...` and plan entries with `src` | legacy (your own SVG or HTML) |
| `export_svg.py --plan` canvas entries | production |
| `export_svg.py --plan ... --preview DIR` | draft preview of the canvas entries |
| `make_icon_set.py generate --bg ...` | legacy (your own colours) |
| `make_icon_set.py generate --from-direction .` | production |
| `make_icon_set.py preview` | draft preview |
| story art | the style bible comes from `direction.py resolve illustration`; every image still needs the owner's approval (story-art) |

Exit codes everywhere: 0 completed (the report may still say REVIEW REQUIRED or SKIPPED), 1 a check failed or a gate is not met, 2 bad arguments, a missing dependency or an operational failure.

## Precedence of values
canonical tokens → direction → selected concept → declared per-asset choices (frame `layout`/`background`, canvas `layout`/`background`). A per-asset choice must stay inside the concept's vocabulary; anything else needs the owner's exception (`direction.py approve --gate exception --scope "<scope from the error>"`).

## Migrating a 1.6 mockup kit
Nothing forces it: the kit keeps rendering exactly as before. To give it the project's look:
1. Run `direction.py migrate` for a list of what predates 1.7.
2. Creative-director: a direction (Gate 1), then a store concept round (Gate 2). Use `keep` for anything of the 1.6 look the owner wants to keep.
3. In the kit's `frames.json`: add `"format": 2`, `"artDirection": {"family": "store"}`; rename `"layout": "continuous"` to `"style": "continuous"`; remove `brand` (colours now come from the concept); per frame, replace `caption.tone` with a `background` from the concept and pick a `layout`; for continuous objects, colours become role names (`"accent"`) and coins, chips, receipts and calendars need `"props": ["finance"]`.
4. Fonts: the app's own UI fonts go in `"uiFonts"` (local files); icons need a local icon font (`material-symbols` npm package, or `"iconsFont"`).
5. `render_frames.py preview`, then `render --check-only`, then `render --all`.

## Migrating the 1.6 Open Graph template
The managed `og-image.html` is deprecated and kept until a later major release; your copies under `brand/html/` keep exporting. To move one: add the asset to `brand/canvas.json` (`id`, `size`, `copy`, optional `slots`), then replace its plan entry with `{"canvas": "<id>", "out": "...", "name": "...", "flatten": true}`.
