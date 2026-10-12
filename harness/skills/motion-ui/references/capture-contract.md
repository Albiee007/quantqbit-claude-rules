# Capture contract

How `motion.py` makes repeatable pictures of a live app, and what it can't control. The M0 spike (1.10) measured both modes on a synthetic page and on a production React + WebGL hero.

## Two lanes

| Lane | Clock | Proves | Never used for |
|---|---|---|---|
| **Visual** (deterministic) | app-seek or the virtual clock | composition and pose at spec times; the reduced-motion frame; determinism (same pixels in a fresh browser) | pause, visibility, pacing, input behaviour |
| **Behaviour** (real time) | the browser's own | the app's pause/stop/hide control, a really hidden tab, input replay, WebGL loss, errors, pacing (recording) | exact pixel claims |

A seek holds the scene whatever the play state, and a frozen clock makes everything look paused, so the visual lane can never judge a pause button. The behaviour lane presses the app's real control and watches real time; a button that changes its label while the loop keeps running fails there.

## Seek modes (visual lane)

Every visual page is opened with `media/clock.js` injected before any page script: time stands still from the first line. After the boot (below):
- **app-seek** (preferred; used when the page has a hook and `seekMode` is `auto` or `app-seek`): the clock is released to real time and the capture calls the app's `window.__motion.seek(ms)`.
- **virtual-clock** (`seekMode` `virtual-clock`, or `auto` without a hook): the capture steps the injected clock to each time.

`seekMode: app-seek` without a hook is an error, not a silent fallback.

### The seek hook (app-seek)

Expose it in development or behind a query flag, never in production builds:

```ts
window.__motion = {
  version: 1,
  ready(): Promise<unknown>,            // fonts, textures and first frame ready
  seek(ms: number): Promise<unknown>,   // hold the scene at ms; resolve after the change is committed
  state(): { sceneId: string; ms: number; paused: boolean; reducedMotion: boolean },
};
```

`seek(ms)` must:
- set the scene index and its content (DOM text, layout variant), the camera and every track value, overlays and panels, media `currentTime` (and pause any `<video>`), and transition progress;
- cancel pending work: timers, in-flight transitions, queued scene changes;
- position CSS and Web Animations it owns (`el.getAnimations()`: pause, set `currentTime`; cancel stray CSS transitions);
- **hold** the scene at ms until the next seek or a reload (the app's own loop must not move it);
- resolve only after the framework has committed (React: `flushSync`, or await a commit effect);
- ignore the play state: the visual lane never uses seek to judge pausing.

`state().sceneId` is compared with the spec's scene at each capture time (a mismatch FAILs); `state().ms` must equal the requested time (one retry, then a problem). In the behaviour lane (no seek) `state().ms` is the motion's own elapsed time; the hidden-tab check uses it when present.

### The virtual clock (no hook)

`clock.js` virtualises `performance.now`, `Date` (epoch 2026-01-01), `requestAnimationFrame`, and `setTimeout`/`setInterval` with a delay above 0. Zero-delay timers, `MessageChannel` (React's scheduler), fetches, image decoding and promises stay native, so the app boots and hydrates while its clock reads 0.

`step(ms)` advances in increments of `capture.stepMs` (default 1000/60): each increment runs the due timers, then one animation frame with the virtual timestamp, then positions every Web Animation (CSS animations and transitions included) at its virtual age, then lets native tasks settle and **waits for one real painted frame**. Apps clamp large frame deltas, so one jump would not reach the same state; and a layer is rasterised the first time a frame shows it, so skipped frames change later pixels (the spike measured 1-px edge differences until every increment was painted).

`Math.random` is seeded when `capture.seed` is set. `release()` hands everything back to real time (pending virtual timers move to native ones, nothing fires twice).

## Boot

Network is blocked except `file:`, `data:`, `blob:`, the target's own origin and `capture.allowOrigins` (blocked requests are a review item). The capture waits for the network to go quiet, then checks the ready condition (`document.readyState === 'complete'` plus `capture.ready.selector` and `.expression`); while it is false it steps the virtual clock one increment and tries again, until `ready.timeoutMs`. Apps that wait on a timer or an animation frame to reveal themselves (the spike's hero needed three increments) boot the same way every run. Time 0 is the moment the page became ready; set `reference.offsetMs` to line the reference up with it.

## Settle (app-seek)

Before each screenshot: await `seek`; await `document.fonts.ready` and the decoding of non-lazy images; two animation frames; one `MessageChannel` round trip; read `state()`.

## What is not controlled

`clock.js` reports what it saw; the run lists it as a review item (`clock-sources`):
- `<video>` and `<audio>` playback (use app-seek, which sets `currentTime`);
- Workers and OffscreenCanvas (their own clocks);
- cross-origin iframes;
- scroll-driven timelines (scroll pieces set the scroll position instead);
- reads of `document.timeline.currentTime`;
- GPU and rasterisation differences between machines and browser versions: determinism holds on one machine and browser.

Two captures count as identical when every pixel matches, and as near-identical (rasterisation noise, PASS with a note) when no channel differs by more than 2 levels on at most 0.05 % of pixels. Anything else in the determinism check FAILs.

## WebGL

`capture.webgl: true` launches the browser with SwiftShader (`--use-angle=swiftshader --enable-unsafe-swiftshader`), because headless Chrome runs with `--disable-gpu`. The behaviour lane records every WebGL context the page creates and checks the page after `loseContext()`.

## M0 findings (1.10)

- CDP `Emulation.setVirtualTimePolicy`: rejected. Animation frames don't advance with it in headless Chrome, so a rAF-driven hero never changed scene.
- App-seek on the fixture: identical pixels at 10 of 10 times in two fresh browsers.
- Virtual clock on the fixture: 10 of 10. On a production React + WebGL hero (rAF loop with clamped deltas, scene changes through React state): scene changes landed on the right frames; 8 of 10 times identical and 2 near-identical (at most 9 pixels, 1 level).
- Visibility: putting another tab in front (`Target.activateTarget`) makes the page `hidden` in headless Chrome; switching back makes it `visible`. Screencast: about 57 fps, longest gap 133 ms in 3 s.
