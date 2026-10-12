# Verification

Screenshots and a passing build can't prove animation fidelity. A run checks precise states on a controlled clock, behaviour in real time, and pacing in a real-time recording, then puts the build next to the reference for a person to judge.

## Commands

| Command | Lane | Approval | Output |
|---|---|---|---|
| `capture <id> [--viewport V] [--at MS,MS] [--reduced] [--determinism K]` | visual | none (draft) | `.preview/<run>/captures/`, `sheets/` |
| `check <id> [--viewport V]` | behaviour | none (draft) | the check table |
| `record <id> [--seconds S] [--adb] [--file F]` | real time | none (draft) | `.preview/<run>/recording/` |
| `compare <id> --run R` | – | none (draft) | `.preview/<run>/compare/` |
| `verify <id>` | all | Gate 3 and every planned asset | `out/` (complete runs), `brand/runs/motion/<run>.json` |

`motion.py` never starts a dev server. Give it a base URL (`--base-url`, `$MOTION_BASE_URL` or `dev_url=` in `.claude/harness.config`), or point `capture.page` at a project HTML file. Prefer a production preview build for `verify`: dev servers add error overlays, hot reload and cold compiles. Stop the server yourself when you are done. Every browser, ffmpeg or adb process a command starts is stopped when it ends, fails, is interrupted or reaches `--timeout`.

## Checks

| Check | Lane | Result |
|---|---|---|
| visual | visual | PASS when every viewport and time was captured |
| scenes | visual | `state().sceneId` against the spec's scene: FAIL on a mismatch; SKIPPED without `state()` |
| essential | visual | `capture.essential` visible where each scene has settled: FAIL if not |
| overflow | visual | horizontal overflow on mobile viewports: FAIL |
| hidden-focus | visual | focusable but invisible elements: REVIEW REQUIRED |
| loop-seam | visual | time loops: the frame at `lengthMs` against 0 ms: REVIEW REQUIRED if different |
| determinism | visual | K times in a fresh browser: FAIL if different, PASS if identical or near-identical |
| clock-sources, network | visual | uncontrolled time sources, blocked requests: REVIEW REQUIRED |
| reduced-motion | visual | `prefers-reduced-motion: reduce`, frames 2.5 s apart: static-complete must be identical (FAIL); other strategies are REVIEW REQUIRED |
| control | behaviour | press the app's control; the picture (and `state().ms`) must stop changing: FAIL if not; pause must resume on a second press |
| hidden-tab | behaviour | another tab in front for 2.5 s: with `state().ms`, a jump over 800 ms FAILs; from pixels alone, a large change is REVIEW REQUIRED; SKIPPED (manual review item) if the browser can't hide the tab |
| context-loss | behaviour | `loseContext()` on every WebGL context: a blank page is REVIEW REQUIRED |
| page-errors | both | uncaught exceptions: FAIL; console errors: REVIEW REQUIRED |
| flashing | recording | over 3 flashes in a second: REVIEW REQUIRED, labelled WCAG 2.3.1 (approximation) or the stricter harness rule (flashes below the WCAG threshold) |
| compare | – | always REVIEW REQUIRED: the owner looks |

Results: PASS and FAIL are measured; SKIPPED says why it didn't run; REVIEW REQUIRED means a person must look. Signals (cut times, loop candidates, structure and palette distances) are never verdicts.

## Equivalent comparisons

- Compare at the designed viewport (`reference.designedViewport`) and equivalent times (`reference.offsetMs` lines them up). A phone recording of a desktop site is not a mobile reference.
- Look at motion boundaries and midpoints: opening motion, holds, transition boundaries, title flight, scene arrival, loop reset.
- Compare landmark position and scale, near-to-far displacement, layer geometry, title anchor, sharpness and departure, panel reveals, fixed navigation, framing and grade. Palette differences are expected where the brand replaces the reference's look.
- For a dolly zoom, check the invariant f(d) / (D − d) = f0 / D through the travel, and that nearer layers still change scale. Tests that mirror intermediate implementation values add little.
- Measure performance on representative hardware or with throttling: canvas resolution, per-frame allocations, component re-renders, activity while paused. Don't impose one quality cap on every project.

## Symptoms and causes

| Symptom | Investigate |
|---|---|
| Looks like a slideshow | depth separation, camera and lens compensation, the medium |
| Bent edges or aperture rim | shared displacement across depths, mask geometry |
| A landmark jumps at a cut | landmark alignment, framing or camera discontinuity at the boundary |
| Wrong title flight | its own depth track, pivot, scale, easing, opacity |
| Wrong colours | token mapping, media grade, overlays |
| Striped borders | UV coverage, clamped texture edges, overscan |
| Wrong timing | the shared clock, measured intervals, buffering, visibility handling |
| Captures differ between runs | uncontrolled time sources (clock-sources), random values without a seed, media without app-seek |

Go back to the reference interval, find the failed track, and fix that cause; don't add decorative motion to hide a structural mismatch.

## Hand-off

Report: the gates; the run's completeness, missing and omitted items; the check table; open review items with what to look at; the fidelity claim and its limits. Matching durations alone does not establish fidelity. Publishing, deploying and messaging need the user's authorisation.
