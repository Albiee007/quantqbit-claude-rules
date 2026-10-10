# Checks and reviews

## Labels

- **PASS / FAIL:** a check that ran and has a numerical result. Any FAIL publishes nothing.
- **SKIPPED:** the check did not run; the detail says why.
- **REVIEW REQUIRED:** only an estimate or a heuristic exists, and a person decides.

## Before rendering (`lint`, and again in `render`)

| Check | Label |
|---|---|
| Schema, ids, and templates, layouts and transitions within the concept (or owner exceptions) | FAIL (a warning in `preview`, so other concepts can be tried) |
| Backgrounds in the concept; required copy per template; placeholder copy (`REPLACE`, `TODO`, `{{…}}`) | FAIL (placeholders are a warning in `preview`) |
| Durations that are not whole frames | warning |
| A transition as long as its scene; a still part under the concept's `minHold` | FAIL |
| Length outside the format's range; a loop over 15 s; a loop rate that does not divide the fps; an unknown poster scene | FAIL |
| A still scene with no picture, or a picture that is missing or not an image | FAIL |
| A picture outside `brand/` with no `media.license` | REVIEW REQUIRED (`provenance:<scene>`) |
| Reading time longer than the still part | REVIEW REQUIRED (`reading:<scene>`, or `reading:<scene>:<format>` when a format changes the copy) |
| Planned voice-over longer than its scene | REVIEW REQUIRED (`vo-fit:<scene>`) |
| Planned voice-over ending after the video | FAIL |
| Page: script errors, network requests, frame count, endless animations, animations past the end | FAIL |
| Page: a frame that changes when reached a second time (`lint` checks one; `render` checks the first scene's still frame again after the whole video) | FAIL |

## After rendering

Checks that look at a format's output are named `<check>:<format>` (for example `technical:social-1x1`); review item ids carry `:<format>` when a piece has more than one format.

| Check | Label |
|---|---|
| `technical`: the output profile (see formats-and-profiles) | PASS / FAIL |
| `gif`, `webp`, `poster`: format, size, loop forever, play length, at most the master's frames | PASS / FAIL |
| `gif`, `webp` over the piece's `loop.maxBytes` (default 5 MB) | REVIEW REQUIRED (`size:<kind>`) |
| `loop-seam` (`kind: "loop"`): the jump from the last frame back to the first, against the piece's own frame-to-frame changes | PASS or REVIEW REQUIRED (`loop-seam`) |
| `workers` (more than one browser): the frames where their runs meet are drawn identically | PASS / FAIL |
| `contrast`: computed against solid backgrounds and caption plates; whole-gradient bound | PASS / FAIL |
| `contrast` sampled from pixels (text over a drawn object, a failing gradient) | REVIEW REQUIRED (`contrast:<scene>:<n>`) or FAIL |
| `text`: glyph coverage from the font file; text cut off by the frame | PASS / FAIL |
| `safe-area`: text inside the platforms' UI zones | REVIEW REQUIRED (`safe-area:<scene>`) |
| `flashing`: WCAG 2.3.1 heuristic on decoded frames | PASS or REVIEW REQUIRED (`flash:<t>`) |
| `determinism` (`--determinism K`): K frames re-rendered in a fresh browser, in reverse order | PASS / FAIL (same machine) |
| `audio` | SKIPPED (silent by default) |

Contrast is checked on each scene's still frame, at the concept's display width.

## Run integrity

1. **Lock.** `render` takes the piece's lock before it reads any input.
2. **Snapshot.** Fonts, the logo, the motif and the scenes' pictures are copied into the build and checked against the hashes the gates used. The frames come only from those copies.
3. **Manifest first.** The run manifest (`brand/runs/video/<run>.json`) is written before the outputs move into `out/`.
4. **Ownership.** `out/.render-manifest.json` records which files the run owns.

`render_video.py status` compares `out/` with the latest manifest, so an interrupted publish or a hand-edited output shows up as NOT PUBLISHED.

## Clearing review items

- A run with review items is **published but not cleared for use**.
- The owner looks at the items: the sheet, the video, the notes.
- The main session then records an acknowledgement:

  ```
  python .claude/skills/creative-direction/scripts/direction.py approve --gate review --run <run> --items all --by "<owner>" --evidence "<where they said so>"
  ```

- The record binds to the run's output hashes and the item ids. A byte-identical re-render keeps it; any change to the outputs needs a new look.
- Agents never record it. The creative-director's review mode treats open items as "not ready to use".
