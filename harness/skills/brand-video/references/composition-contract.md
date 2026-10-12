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

## Recordings

- A `recording` scene's video is turned into numbered JPEG frames with ffmpeg before the render, at the piece's fps: frame `n` of the scene is file `n` (a phone's variable-rate recording becomes one picture per video frame). Past the recording's end the last frame holds.
- The page shows them with `img[data-seq-src]`. On each seek the runtime sets the frame's file and waits for it to decode before the frame is drawn, so the browser never plays video and seeking stays history-independent.

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
## Custom scenes and libraries

- A `custom` scene is the project's own: `custom.html` (a fragment placed in the scene), `custom.script`, and optionally `custom.lottie` (animation data). The script registers a builder: `window.VideoScenes["<scene id>"] = (el, ctx) => player`.
- `ctx` gives `width`, `height`, `fps`, `frames`, `seconds`, `safe`, `AD` (the resolved concept), `lottie`, `headPx`, `ms(frames)`, `start` (the scene's start in composition milliseconds, for Web Animation delays) and `rand(key)`.
- The builder may create Web Animations (`el.animate(...)`, with delays from `ctx.start`), which the runtime seeks like ours. It may also return a library player, which the runtime registers (`__hf.register(el, player)`) and positions on every seek at the time relative to the scene. Accepted players:
  - a paused GSAP-style timeline (`totalTime(seconds, true)`);
  - a Lottie animation with `autoplay: false` (`goToAndStop(ms, false)`);
  - anything with `seek(seconds)`.

  A promise can be returned too; readiness waits for it.
- **Libraries** (GSAP, lottie-web...) are the project's: `libraries: [{file, name, license}]`, local files loaded before the scenes. The harness never fetches or vendors one.
- **Lint** refuses the scene's own HTML and script (not the libraries) when they use timers or frame loops, clock reads, `Math.random`, CSS transitions, the network, or `play()`/`autoplay`/`loop: true`. Their bytes and the libraries' bytes are part of the storyboard approval.

## Engines

- `render --engine ours` (default) draws every frame in our browser, as above.
- `render --engine hyperframes` asks the pinned HyperFrames CLI (0.8.119) for the frames:
  - The composition is exported as a HyperFrames project: `index.html` plus fonts, assets and scripts, without our runtime, since HyperFrames brings its own `window.__hf`.
  - The CLI renders a PNG sequence. Our encoder, profiles, sound, checks, manifest and approvals then work as with our engine.
  - A parity signal (`engine-parity:<format>`) compares HyperFrames' frame with ours at every scene's still frame. Fonts and anti-aliasing differ between browser builds, so it is a signal.
  - It needs Node.js 22+ and the CLI (`HYPERFRAMES_BIN`, `--hyperframes`, or `npx`, which downloads it), and turns HyperFrames' render telemetry off.
  - Recording and custom scenes need our runtime, so they are refused there.
- The manifest records `engine.renderer` and `engine.hyperframes`.
