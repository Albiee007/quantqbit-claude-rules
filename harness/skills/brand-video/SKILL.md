---
name: brand-video
description: Branded video in the project's own approved look — a video concept (motion, pace, transitions, voice direction) chosen in a concept round, a storyboard per piece (brand/video/<id>/video.json) the owner approves, deterministic HTML scenes rendered frame by frame in headless Chrome and encoded with ffmpeg (H.264, BT.709), with contrast, safe-area, flashing, frame-count and determinism checks and a run manifest. The default output is a silent video plus a voice-over script, a voice prompt and planned captions, so the voice can be made in any tool. Use when the project needs a social promo, reel, short or vertical teaser, a voice-over script for one, or a re-render of an existing piece.
---

# Brand Video

Make short videos that look and move like **this project**: the backgrounds, type, accents and motif of the approved direction, animated with the project's own motion tokens. Every frame is an HTML page seeked to an exact time, so a render is repeatable and reviewable frame by frame.

## Inputs
- The creative direction and its approvals (`direction.py status`). Video needs Gate 1 (direction), Gate 2 (a video concept) and, per piece, Gate 3 (the storyboard).
- Motion tokens in the project's token file (`$type` duration and cubicBezier). `render_video.py motion-tokens` suggests them from the mood; `--write` adds them without overwriting.
- What the video is for: platform, length, message, call to action, and whether a voice-over is wanted.

## Workflow
1. **Direction.** No video family requested, or no motion tokens: the creative-director adds `families.video` (with a brief) and runs `render_video.py motion-tokens`. Requesting a family no longer makes other approvals stale.
2. **Concept round.** `video-creative` (concept mode) writes 2–3 video concepts (`direction.py concept new --family video`) per [concept-round](../creative-direction/references/concept-round.md): genuinely different motion and pace, all in the approved look. Each gets a preview (`render_video.py preview <piece> --concept <file>`): a sheet of each scene's still frame and a half-size draft. The creative-director critiques; the owner picks; the main session records it (`direction.py approve --gate concept --family video ...`).
3. **Storyboard.** `render_video.py init <id>` writes a starter `brand/video/<id>/video.json`. Fill the scenes (template, duration, copy, `vo` line) from the brief and the project's real claims. Run `render_video.py lint <id>` until it reports no problems, then `preview <id>`.
4. **Owner approves the storyboard** after watching the draft and reading `voice/script.md`: `direction.py approve --gate storyboard --piece <id> --by ... --evidence ...` (main session only).
5. **Render.** `render_video.py render <id>` checks the gates, lints, renders every frame, encodes, checks, writes `brand/runs/video/<run>.json` and then publishes to `brand/video/<id>/out/`. A FAIL publishes nothing.
6. **Reviews.** REVIEW REQUIRED items (sampled contrast, safe areas, flashing, reading time, voice-over fit) are listed in the run manifest. The output is published but not cleared for use until the owner looks and the main session records it: `direction.py approve --gate review --run <run> --items <ids|all> ...`. `render_video.py status` shows what is open. A byte-identical re-render keeps the acknowledgement.
7. **Voice.** Hand `out/voice/voice-prompt.md` and `script.md` to whoever makes the voice (a voice actor or any TTS tool). Mixing a supplied recording into the video arrives in a later release; until then the video ships silent or is finished in an editor.

## Templates and vocabulary
- Scene templates: `title`, `feature` (head plus up to five points), `stat` (a number and its label), `end-card` (logo, call to action, URL). The concept lists which a project uses.
- Layouts `type-start`, `type-center`, `type-lower`; transitions `cut`, `fade`, `dip`, `slide`, `push`, `scale`, `wipe`; text entrances `fade-up`, `mask-up`, `word-stagger`, `scale-in`, `fade`. A scene may use only what its concept allows; anything else needs an owner exception (`--scope "video:<piece>:scene:<scene>:<kind>=<value>"`).
- Formats: `social-9x16` (1080×1920; Reels, Shorts, TikTok). More formats, app previews, explainers with mixed audio and animated loops arrive in later releases. See [formats-and-profiles](references/formats-and-profiles.md).

## Rules
- **The look comes from the concept,** never from the piece: no colours, fonts or CSS in `video.json`. Change the look through the concept and its approval.
- **The owner decides** concepts, storyboards and review items; agents never record approvals and never call a paid or external voice or video service.
- **Truthful copy.** On-screen claims and voice-over lines follow the same claims guardrails as the store listing; no invented numbers (a `stat` scene needs a real figure).
- **Reading time and pace are signals.** `lint` reports scenes too short to read or lines too long for their scene; the owner decides. The concept's minimum hold is enforced.
- **Accessibility:** no more than three flashes a second (the render's flashing heuristic is a signal; look at anything it flags), keep text inside the safe insets, ship the caption sidecar with the video where the platform takes one.
- **Use the scripts.** Don't write your own render, encode or check scripts; don't hand-edit `out/`, `.build/` or run manifests.
- **ffmpeg** must be installed (`render_video.py` names the install command per OS); Chrome, Chromium or Edge renders. Media files never go into `.claude/`.

## Output
- `brand/video/<id>/video.json` (project-owned), `brand/video/<id>/out/`: `<format>/<id>.mp4`, `<id>-sheet.png` (each scene's still frame), `voice/script.md`, `voice/voice-prompt.md`, `voice/cues.json`, `voice/captions.planned.srt|vtt`; `brand/runs/video/<run>.json`.
- A report: concept and storyboard approvals, the check table, open review items, and the voice hand-off.

## References
- [composition-contract](references/composition-contract.md): the seek contract, frame arithmetic, HyperFrames-compatible markup.
- [motion-vocabulary](references/motion-vocabulary.md): mood to motion, transitions, text entrances, pace and reading time.
- [formats-and-profiles](references/formats-and-profiles.md): formats, safe areas, output profiles and their checks.
- [audio-and-voice](references/audio-and-voice.md): the script, the voice prompt, planned captions, recording specs.
- [qa-and-reviews](references/qa-and-reviews.md): every check, its label, and how review items are cleared.
- Template: [video.example.json](templates/video.example.json). Script: [render_video.py](scripts/render_video.py).
- Related skills: `creative-direction`, `ui-ux` (motion, reduced motion, flashing), `typography`, `color-science`, `brand-assets` (logo), `story-art` (stills), `store-listing` (claims).
