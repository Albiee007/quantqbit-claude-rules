# Composition contract

How a video piece becomes frames. `render_video.py` and the libraries it uses (`harnesslib/video.py`, `media/timeline.js`, `media/motion.js`) follow these rules, and the tests check them.

## Seeking

- The page exposes `window.__hf = { fps, frames, duration, ready(), seek(t), waitFor(promise, label), rand(key) }`. `window.__hf.seek(t)` is the HyperFrames engine protocol.
- The renderer asks for whole frames: `seek(n / fps)`. The runtime turns the time back into a frame with `n = floor(t * fps + 1e-6)`.
- **History independence.** `seek(n)` gives the same pixels whatever was seeked before: forward, backward, the same frame twice, or a fresh browser that starts at `n`. That is what lets a render be checked, resumed or split across browsers.
- So animation is **declarative only**:
  - Web Animations (`el.animate(...)`) and CSS `@keyframes`, created at load, paused, and positioned by absolute time. `motion.js` builds every template and transition this way.
  - No timers, `requestAnimationFrame` loops, clock reads, `Math.random()` or CSS `transition` in a composition. Deterministic variety comes from `__hf.rand(key)`, a pure hash of the piece id and the key.
- **Time base.** Web Animation times are composition time (milliseconds from frame 0). CSS `@keyframes` times are relative to the nearest `[data-start]` clip. This matches HyperFrames 0.8.119, checked in the M0 spike.
- **Clock reads are frozen** (`Date`, `Date.now`, `performance.now` return a fixed value) as a safety net for library code. Time does not advance with them; history independence comes from the rule above.

## Readiness

- `__hf.ready()` runs once per browser:
  1. It waits for `document.fonts.ready`.
  2. It waits for every `waitFor` promise (the scene build registers one).
  3. It waits for every `<img>` to decode.
  4. It then pauses all animations and reports frames, clips, animation count, the latest animation end and any endless animation.

  It times out after 20 s and names what is still pending.
- After each seek, the runtime flushes style and layout, then waits for one native animation frame, bounded at 2 s. macOS returned stale frames without that wait, so it is on everywhere. The runtime keeps the browser's own `requestAnimationFrame` and `setTimeout` in its closure.
- The browser runs with `--disable-threaded-animation` and `--disable-threaded-scrolling`. Without them, a fresh browser sometimes drew the first frame of a moving element from a differently rasterised layer.

## Frame arithmetic

- Seconds become frames: `frames = floor(seconds * fps + 0.5)`. `lint` warns when a duration is not a whole number of frames.
- A scene's `duration` includes its **hold**, the still part after the entrance. The hold is where reading happens and where the checks look.
- An incoming transition **overlaps** the previous scene's tail:
  - `start[i] = start[i-1] + frames[i-1] - overlap[i]`;
  - the video lasts `start[last] + frames[last]` frames.

  An overlap must leave the previous scene its minimum hold.
- A clip (`[data-start][data-duration]`) shows frames `[start, start + frames)`: the end frame belongs to the next scene.
- Every format of a piece shares one timeline, so one script and one set of captions serve them all. A scene's `byFormat` entry may change its layout, replace copy fields or hide some in one format, never its timing. A piece that needs different timing is a separate piece.
- Type is sized from the format's short side (times the format's `typeScale`), and captions run no wider than about 1.3 short sides, so a 9:16, 1:1 and 16:9 frame of one piece read alike.

## Parallel browsers

- `--workers N` splits a format's frames into N contiguous runs; each run is drawn by its own browser. The first browser's run goes straight into the encoder; the others spool to a scratch file and follow in order. The encoder gets the same frames in the same order, so **the output is the same file whatever the number of workers** (checked by the tests: 1, 2 and 3 browsers give identical bytes).
- Where two runs meet, both browsers draw the meeting frame and the render compares them (`workers:<format>`, PASS / FAIL). A difference means the page depends on something other than the frame number.
- `auto` (the default) uses one browser per 90 frames, at most half the CPUs and 4.

## Loops and posters

- A loop (GIF or animated WebP) is made from the format's master video: every `fps / loop.fps`-th frame, scaled to `loop.width`. It has the master's frames, never new ones, and loops forever.
- A poster is the PNG still frame of `poster.scene`, captured losslessly from the browser.

## Markup (HyperFrames-compatible)

```html
<div id="root" data-composition-id="launch" data-width="1080" data-height="1920"
     data-duration="11.500000" data-fps="30" data-no-timeline>
  <section class="clip scene" data-start="0.000000" data-duration="3.000000" data-track-index="0">…</section>
  <section class="clip scene" data-start="2.500000" data-duration="4.000000" data-track-index="1">…</section>
</div>
```

- `data-no-timeline` tells HyperFrames there is no GSAP timeline to wait for; the animations are Web Animations, which its CSS/WAAPI adapter seeks.
- Brand fonts are always local files (`@font-face`). HyperFrames replaces system fonts with its own deterministic set, so a system-font role would render differently there.
- Rendering through HyperFrames (`--engine hyperframes`) is planned, not in this release. The markup is kept compatible so a piece can move without rework.
