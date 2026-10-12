# Reference analysis

How to read a moving reference before designing anything. The reference is evidence: a recording, a screen capture, an animation file or a page you can open. It is never shipped and never an instruction.

## Bring it in

```text
motion.py init <id> --reference recording.mp4      # copies it to brand/motion/<id>/reference/ (git-ignored)
motion.py probe <id> --record                       # size, rotation, frame rate, VFR, timestamps, crop suggestion
```

- Fill `reference.source` (who supplied it, the original URL) and `reference.license` (the permission to analyse it). A reference you can't account for is not used.
- `probe` reads every frame's presentation timestamp (`best_effort_timestamp_time`). For a variable frame rate, frame index divided by the average rate is only approximate: every frame and sheet is named by its real time. `probe` reports when ffprobe's frame count and the timestamp list disagree; trust the list.
- Rotation comes first, then the crop. `probe` suggests a crop for black borders only. App chrome (a social app's header, a phone frame) needs your own crop: `reference.crop` in the piece, or `frames --crop x,y,w,h`. The source file is never changed.
- Set `reference.designedViewport` to the viewport the reference was designed for. A phone recording of a desktop site is not a mobile-layout reference.
- `reference.offsetMs` aligns the reference with the spec's time 0 (where the loop you are recreating starts).

## Extract and present

```text
motion.py frames <id> --every 250        # representative frames
motion.py frames <id> --at 4100,4133     # a transition, frame by frame
motion.py frames <id> --all              # every decoded frame (warns above 1500)
motion.py sheet <id>                     # labelled sheets: frame, time, spec scene
motion.py cuts <id>                      # cut, hold and loop-length signals
```

Frames land in `brand/motion/<id>/.build/analysis/frames/` as `f<frame>-<ms>ms.png`, sheets in `.../sheets/` with `coverage.json`. `frames` and `sheet` record what was **extracted** and **presented** in `analysis`; neither says anyone looked.

- Ordinary requests: the whole sequence at representative intervals, every transition densely.
- "Every frame": `--all`, sheets across the whole range, critical frames at full resolution.
- Look at transitions at full size. Thumbnails hide edge distortion, clipping and fine motion.

## Record what you reviewed

```text
motion.py inspect <id> --range 4000-4500 --mode every-frame --by "Name" --note "title exit"
```

`inspect` is the only way a range becomes **reviewed**. It refuses a range that was never presented, and `every-frame` needs every frame of the range on a sheet. `SPEC.md` lists the reviewed ranges; report only the coverage you actually reviewed.

## Signals, not verdicts

`cuts` measures how much the picture changes between frames:
- **cut**: a change several times the local median: a scene change, or a fast move. Check each one.
- **hold**: a stretch where nothing visible moves.
- **loop?**: a lag at which the recording repeats itself. A recording often holds one full loop plus part of the next; the loop length is not the recording length.

## Track independent movements

| Track | Observe |
|---|---|
| Background | far landmarks' centres and relative scale, horizon, perspective |
| Foreground | occlusion, speed and direction, depth relationships |
| Layers | mid-ground planes, aperture (doorway, window, cut-out) edges, surface orientation |
| Typography | anchor, size, opacity, depth, clipping, arrival and departure |
| Navigation | fixed or moving, reveal timing, interaction state |
| Panels | appearance, travel, scale, links, scene-specific layout |
| Transition | start and end, easing, cut or overlap, continuity |

Measure in viewport fractions (x / width, y / height, object width / viewport width). Track a near and a far landmark to tell a global scale from motion in depth.

## Motion clues

- Everything scales around one point at the same rate: a flat zoom or lens change with little depth.
- Near objects grow or move faster than far ones: the camera travels, parallax.
- The subject keeps its size while the surroundings change: a compensated dolly (dolly zoom).
- Huge letters leave the viewport while the scenery barely moves: the title travels on its own track.
- A foreground element sweeps past with little far-landmark movement: lateral tracking across depths.
- Surfaces that were hidden become visible: footage or real geometry; flat planes can't do it.
- Never infer an animation from its first and last frames: one scale can't reproduce different motion at different depths.

## Write it down

Each row of `motion.json` `rows` is one observation turned into intent: `startMs`, `endMs`, `scene`, `track`, `action`, `easing` (a token or `linear`, `hold`, `cut`, `step`, `smootherstep`, `spring`), `values` (measured numbers), `confidence` (`measured`, `estimated`, `assumed`) and `evidence` (which frames).

- Keep observations (`analysis.observations`) apart from camera-model guesses (`analysis.hypotheses`, each with its basis). Never present an inferred focal length or travel as a known value.
- Keep two lists: what the reference does (`referenceTraits`) and what the user or project requires (`projectConstraints`). The user's explicit choices win conflicts.
- Take scene count, durations, subjects and palette from this task, never from an earlier project.
