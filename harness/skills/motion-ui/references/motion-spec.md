# The motion spec

`brand/motion/<id>/motion.json` (schema `harnesslib/schemas/motion.schema.json`) says what a piece of motion shows and when, and how to capture it. Its look comes from the selected motion concept, so it never sets a colour, a font or CSS. `motion.py spec <id>` turns it into `SPEC.md` for the owner. Starter: `motion.py init <id>`; a filled example: [motion.example.json](../templates/motion.example.json).

## Fields

| Field | What it holds |
|---|---|
| `platform` | `web`, `react-native`, `android-compose`, `ios` |
| `target` | `route`, `files` (the components that implement the motion) |
| `fingerprint.globs` | the files a review binds to (default: the folders of `target.files` and `capture.page`, plus package manifests) |
| `reference` | `path` (in the ignored `reference/` folder), `source`, `license`, `sha256` (by `probe --record`), `crop`, `designedViewport`, `offsetMs` |
| `fidelity` | `targets` (composition, motion, interaction, pacing), `medium`, `claim` (original-footage, generated-footage, reconstructed-layers, code-only), `limits` |
| `viewports` | built-ins `desktop` (1440×900), `tablet` (820×1180 @2x), `mobile` (390×844 @3x), or names from `customViewports` |
| `customViewports` | `{"kiosk": {"size": "1080x1920", "like": "tablet", "dpr": 1}}`: any size 240–3840 px, the rest from the built-in it is like |
| `loop` | `mode` (time-loop, once, scroll, interaction), `lengthMs`, `repeat` (infinite or N), `autoplay` |
| `scenes` | `id`, `label`, `durationMs`, `holdMs`, `layout` per viewport, `media` (asset ids), `transitionIn` (kind, durationMs) |
| `rows` | timed observations turned into intent (see [reference-analysis](reference-analysis.md)) |
| `tracks` | optional numeric keyframes (hashed with timing) |
| `assets` | `id`, `role`, `origin` (project, generated, licensed, footage), `plan` (brief, prompt, licence, source, continuity), later `path`, `license`, `provenance` |
| `reducedMotion` | `strategy` (static-complete, crossfade-only, reduced-travel), `staticAt` (scene, ms) |
| `motionControl` | `kind` (pause, stop, hide, none), `selector`, `essentialJustification` |
| `resilience` | `hiddenTab` (pause or continue), `fallback` (an asset id), `contextLoss` |
| `input` | scroll pieces: `scroll` (container, axis, fromPx, toPx, `progressMap` [[px, ms], …]); interaction pieces: `sequence` [{action, target, value, atMs}] |
| `capture` | `driver` (web, expo-web, adb, frames, file), `path` (with a base URL) or `page` (a project HTML file), `ready` (selector, expression, timeoutMs), `seekMode` (auto, app-seek, virtual-clock), `stepMs`, `times`, `allowOrigins`, `essential` (selectors that must be visible), `webgl`, `colorScheme`, `seed`, `settleMs`, `recordViewport` |
| `analysis` | `extracted`, `presented` (written by the tools), `reviewed` (only by `inspect`), `observations`, `hypotheses`, `referenceTraits`, `projectConstraints` |

## Lint (`motion.py lint`)

Beyond the schema:
- **Timing:** scene durations add up to `loop.lengthMs` (time-loop, once); rows stay inside it, in time order; holds and transitions fit their scenes.
- **Medium:** one the concept allows, or an owner exception `motion:<id>:medium=<medium>`.
- **Automatic motion (WCAG 2.2.2):** motion that starts by itself and runs more than 5 s needs `motionControl` (pause, stop or hide, with a selector) or an `essentialJustification`, which becomes a review item. Total time is what counts: a 4 s loop that repeats without end needs a control, and so does a 10 s one-shot.
- **Input:** scroll and interaction pieces need `input`; time-based pieces take none.
- **Assets:** a generated asset needs a brief or prompt in its plan; licensed and footage assets need a licence. With `--stage verify` every planned asset must exist, and generated ones need provenance.
- **Easing:** a cubicBezier token or one of linear, hold, cut, step, smootherstep, spring.
- **Placeholders:** no `REPLACE` text outside `analysis`.

## Approved, verified, reviewed

Three words, three fingerprints, each with its own test:

| Word | Means | Bound to | Goes stale when |
|---|---|---|---|
| **approved** (Gate 3) | the owner accepts the intent | the parts `visual` (platform, fidelity, viewports, scene structure, reduced motion, control, resilience), `timing` (loop, scene timing, rows, tracks, input), `assetPlan` (ids, roles, origins, plans; no bytes), `reference` (hash, crop, source, licence), plus the motion concept's approval | an intent part changes. Code, asset bytes, capture settings and analysis notes don't touch it |
| **verified** | a `verify` run that is complete for its driver | the run manifest: approved hashes, build fingerprint, resolved target, effective capture settings (driver, viewports with DPR, times, seek mode, step, flags, browser and ffmpeg versions), asset bytes, output hashes | a record; `status` says verified only while the spec, the code, the assets and the published files still match it |
| **reviewed** | the owner acknowledged one run's review items | the run's review hash: approved hashes + build + target + capture settings + asset bytes + deterministic outputs + the items listed | any of these changes, even when motion.json didn't |

- **Assets** are approved as a plan before they exist. Adding or replacing a file never re-opens Gate 3; it makes the last review stale.
- **Build fingerprint:** the content (LF line endings) of every file `fingerprint.globs` matches, listed through git when there is one. Content, not commits: committing the verified work keeps it. With nothing naming the motion's code, the run says the fingerprint is partial (a review item).
- **Evidence outputs** (the real-time recording) are never byte-identical between runs, so the review hash leaves them out; the build fingerprint still ties the acknowledgement to the code that was recorded. Their signals (effective fps, longest gap, cut times, loop length) are in the manifest's `evidence`, for display.
- An identical re-verify (same code, settings and captures) keeps the acknowledgement. Rasterisation noise between machines or browser versions changes capture bytes, which needs a new look.

## Completeness

Execution status (PASS, FAIL, SKIPPED, REVIEW REQUIRED per check) and completeness are separate.
- Each driver requires certain evidence ([platform-mobile](platform-mobile.md) has the table). Web: the visual lane, the behaviour lane, the reduced-motion frames, the recording, and the comparison when there is a reference.
- A required item that could not run (no ffmpeg, the reference file not on this machine, no frames) makes the run **incomplete**: its manifest is written with `missing` and reasons, its outputs stay in `.preview/<run>/`, it is not published, and `approve --gate review` refuses it. Under `CI=true` an incomplete run exits 1.
- An optional item that does not apply goes in `omitted` with its reason (for example `compare` without a reference) and does not block.
- Any FAIL publishes nothing.
