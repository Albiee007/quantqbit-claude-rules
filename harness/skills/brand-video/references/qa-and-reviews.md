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
| A still's picture the format has to enlarge: its fit (`cover` fills, `contain` fits inside), plus the 108 % zoom when it moves. EXIF orientation is applied; SVG is exempt | REVIEW REQUIRED (`resolution:<scene>:<format>`, naming the size needed) |
| A still's picture whose size can't be read, or no Pillow | warning (resolution not checked) |
| A custom scene asset that is missing, outside the project or not an image; a bad asset name; more than 16 | FAIL |
| A custom scene asset outside `brand/` with no `license` | REVIEW REQUIRED (`provenance:<scene>:<asset>`) |
| A recording scene with no recording, or a recording that is missing or not a video | FAIL |
| A recording shorter than its scene | warning (its last frame holds) |
| An App Store preview not at 30 fps, outside 15–30 s, or transparent | FAIL |
| An App Store preview with scenes that are not recordings | REVIEW REQUIRED (`suitability:app-store:<format>`) |
| Audio: a missing voice take for a `vo` line, two takes for one scene, a music file that is missing or not audio | FAIL (a warning in drafts) |
| A recorded take running past the end of the video | FAIL |
| A transparent piece with loops or audio | FAIL |
| A custom scene without a script; its HTML or script using timers, clock reads, `Math.random`, CSS transitions, the network or playback | FAIL (a warning in `preview`) |
| Generated voice or media in the piece (provenance.json) | REVIEW REQUIRED (`disclosure:ai-voice`, `disclosure:ai-media:<scene>`) |
| `--engine hyperframes` with recording or custom scenes | refused (they need our runtime) |
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
| `audio:<format>`: integrated loudness within 1 LU of the target, true peak at most −1 dBTP; or the silent track of an App Store preview | PASS / FAIL |
| `contrast:<format>` of a transparent overlay | REVIEW REQUIRED (`contrast:overlay`) |
| `engine-parity:<format>` (`--engine hyperframes`): HyperFrames' frames against ours at each scene's still frame | PASS or REVIEW REQUIRED (`engine-parity`) |
| `contrast`: computed against solid backgrounds and caption plates; whole-gradient bound | PASS / FAIL |
| `contrast` sampled from pixels (text over a drawn object, a failing gradient) | REVIEW REQUIRED (`contrast:<scene>:<n>`) or FAIL |
| `text`: glyph coverage from the font file; text cut off by the frame | PASS / FAIL |
| `safe-area`: text inside the platforms' UI zones | REVIEW REQUIRED (`safe-area:<scene>`) |
| `flashing`: WCAG 2.3.1 heuristic on decoded frames | PASS or REVIEW REQUIRED (`flash:<t>`) |
| `determinism` (`--determinism K`): K frames re-rendered in a fresh browser, in reverse order | PASS / FAIL (same machine) |
| `audio` (a piece without an `audio` section) | SKIPPED (silent by default) |

Contrast is checked on each scene's still frame, at the concept's display width.

## Run integrity

1. **Lock.** `render` takes the piece's lock before it reads any input.
2. **Snapshot.** Fonts, the logo, the motif, the scenes' pictures and recordings, and the voice takes and music are copied into the build and checked against the hashes the storyboard and mix approvals used. The frames and the mix come only from those copies.
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
