/* Virtual clock for capturing a live app's motion (motion.py injects it before any page script).

   window.__motionClock = { stepMs, now(), step(ms), info(), release() }
   (window.__motionClockConfig = { stepMs, settle, seed } set before it is injected configures it)

   From the first line of the page, time stands still: performance.now, Date, requestAnimationFrame
   and setTimeout/setInterval with a delay above 0 run on a virtual clock that only moves when the
   capture calls step(ms). Work that does not depend on time keeps running natively: fetches, image
   decoding, zero-delay timers, MessageChannel (React's scheduler), promises. So an app boots and
   hydrates while its clock reads 0, and every run reaches the same state at the same virtual time.

   step(ms) advances in fixed increments of stepMs (apps clamp large frame deltas, so one jump would
   not reach the same state): each increment runs the due timers in order, then one animation frame
   with the virtual timestamp, then positions every Web Animation (CSS animations and transitions
   included) at its virtual age, then lets native tasks settle. After the last increment it waits
   for two real frames, so the screenshot shows the result.

   Not controlled (info() lists what it saw): <video>/<audio> playback, Workers and OffscreenCanvas,
   cross-origin iframes, scroll-driven timelines, document.timeline.currentTime reads, and GPU
   differences between machines. motion-ui references/capture-contract.md has the full contract.
*/
(function () {
  'use strict';
  if (window.__motionClock) return;
  const W = window;
  const native = {
    raf: W.requestAnimationFrame.bind(W),
    caf: W.cancelAnimationFrame.bind(W),
    setTimeout: W.setTimeout.bind(W),
    clearTimeout: W.clearTimeout.bind(W),
    setInterval: W.setInterval.bind(W),
    clearInterval: W.clearInterval.bind(W),
    perfNow: performance.now.bind(performance),
    Date: W.Date,
    Promise: W.Promise,
    pause: Animation.prototype.pause,
    play: Animation.prototype.play,
  };
  const EPOCH = Date.UTC(2026, 0, 1);
  const cfg = W.__motionClockConfig || {};
  const STEP = Number(cfg.stepMs) > 0 ? Number(cfg.stepMs) : 1000 / 60;
  const SETTLE = Number.isInteger(cfg.settle) ? cfg.settle : 2;

  let vnow = 0;
  let released = false;
  let nextId = 1e9; // far from the browser's own timer ids, so clearTimeout never cancels the wrong one
  const moved = new Map(); // virtual timer id -> native id after release()
  const frames = new Map(); // id -> callback
  const timers = new Map(); // id -> {due, cb, args, every}
  const seen = { video: 0, worker: 0, offscreen: 0, iframe: 0, scrollTimeline: 0, timelineReads: 0 };

  // ---- time sources
  try { Object.defineProperty(performance, 'now', { value: () => (released ? native.perfNow() : vnow), configurable: true }); } catch (e) { /* read-only */ }
  function VDate(...a) {
    const t = released ? native.Date.now() : EPOCH + Math.floor(vnow);
    if (!new.target) return new native.Date(t).toString();
    return Reflect.construct(native.Date, a.length ? a : [t], new.target);
  }
  VDate.prototype = native.Date.prototype;
  VDate.UTC = native.Date.UTC;
  VDate.parse = native.Date.parse;
  VDate.now = () => (released ? native.Date.now() : EPOCH + Math.floor(vnow));
  W.Date = VDate;

  // ---- seeded randomness (opt-in: the capture sets __motionClockConfig.seed)
  if (Number.isInteger(cfg.seed)) {
    let s = cfg.seed >>> 0 || 1;
    Math.random = () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
  }

  // ---- frames and timers
  W.requestAnimationFrame = (cb) => { const id = nextId++; frames.set(id, cb); return id; };
  W.cancelAnimationFrame = (id) => { if (!frames.delete(id)) native.caf(id); };
  function addTimer(cb, delay, args, every) {
    const d = Math.max(0, Number(delay) || 0);
    if (d === 0 && !every) return native.setTimeout(cb, 0, ...args); // ordering work, not time
    const id = nextId++;
    timers.set(id, { due: vnow + Math.max(d, every ? 1 : 0), cb, args, every: every ? Math.max(1, d) : 0, seq: id });
    return id;
  }
  W.setTimeout = (cb, delay, ...args) => addTimer(cb, delay, args, false);
  W.setInterval = (cb, delay, ...args) => addTimer(cb, delay, args, true);
  W.clearTimeout = (id) => { if (!timers.delete(id)) native.clearTimeout(moved.has(id) ? moved.get(id) : id); };
  W.clearInterval = (id) => { if (!timers.delete(id)) native.clearInterval(moved.has(id) ? moved.get(id) : id); };

  // ---- Web Animations: the app's own pause/play is remembered; the clock positions the rest
  const known = new Map(); // animation -> virtual birth time
  let internal = false;
  Animation.prototype.pause = function () { if (!internal) this.__appPaused = true; return native.pause.call(this); };
  Animation.prototype.play = function () { if (!internal) this.__appPaused = false; return native.play.call(this); };
  function position() {
    internal = true;
    try {
      for (const a of document.getAnimations()) {
        if (!known.has(a)) known.set(a, vnow);
        if (a.__appPaused) continue;
        if (a.playState !== 'paused') native.pause.call(a);
        a.currentTime = (vnow - known.get(a)) * (a.playbackRate || 1);
      }
    } finally { internal = false; }
  }

  // ---- what the clock cannot reach (reported, never hidden)
  function census() {
    seen.video = document.querySelectorAll('video, audio').length;
    seen.iframe = [...document.querySelectorAll('iframe')].filter((f) => { try { return !f.contentDocument; } catch (e) { return true; } }).length;
  }
  if (W.Worker) { const NW = W.Worker; W.Worker = function (...a) { seen.worker++; return new NW(...a); }; W.Worker.prototype = NW.prototype; }
  if (W.HTMLCanvasElement && HTMLCanvasElement.prototype.transferControlToOffscreen) {
    const t = HTMLCanvasElement.prototype.transferControlToOffscreen;
    HTMLCanvasElement.prototype.transferControlToOffscreen = function () { seen.offscreen++; return t.call(this); };
  }
  if (W.ScrollTimeline) { const S = W.ScrollTimeline; W.ScrollTimeline = function (...a) { seen.scrollTimeline++; return new S(...a); }; }

  const macrotask = () => new native.Promise((r) => { const c = new MessageChannel(); c.port1.onmessage = () => r(); c.port2.postMessage(0); });
  // A real frame that has been painted: rAF callbacks run before the frame's rendering steps, so
  // resolve from a task queued inside the callback (it runs after the frame is committed).
  const realFrame = () => new native.Promise((r) => native.raf(() => { macrotask().then(r); }));

  function runTimers(until) {
    for (;;) {
      let next = null;
      for (const [id, t] of timers) if (t.due <= until && (!next || t.due < next[1].due || (t.due === next[1].due && t.seq < next[1].seq))) next = [id, t];
      if (!next) return;
      const [id, t] = next;
      vnow = Math.max(vnow, t.due);
      if (t.every) { t.due += t.every; t.seq = nextId++; } else timers.delete(id);
      try { t.cb(...t.args); } catch (e) { native.setTimeout(() => { throw e; }, 0); }
    }
  }

  async function increment(ms) {
    const until = vnow + ms;
    runTimers(until);
    vnow = until;
    const due = [...frames.values()];
    frames.clear();
    for (const cb of due) {
      try { cb(vnow); } catch (e) { native.setTimeout(() => { throw e; }, 0); }
    }
    position();
    for (let i = 0; i < SETTLE; i++) await macrotask();
    // Every increment is rendered once: a layer is rasterised the first time a frame shows it, so
    // skipped frames would change later pixels (measured: 1-px edge differences in the M0 spike).
    await realFrame();
  }

  W.__motionClock = {
    get stepMs() { return STEP; },
    now: () => vnow,
    async step(ms) {
      if (released) throw new Error('the clock was released');
      let left = Number(ms);
      while (left > 1e-6) {
        const d = Math.min(STEP, left);
        await increment(d);
        left -= d;
      }
      position();
      await realFrame();
      await realFrame();
      return vnow;
    },
    /* Real time from here on (behaviour checks run on the browser's own clock). */
    release() {
      if (released) return;
      released = true;
      for (const [id, t] of timers) {
        const wait = Math.max(0, t.due - vnow);
        if (t.every) {
          const first = native.setTimeout(() => {
            try { t.cb(...t.args); } finally { moved.set(id, native.setInterval(t.cb, t.every, ...t.args)); }
          }, wait);
          moved.set(id, first);
        } else {
          moved.set(id, native.setTimeout(t.cb, wait, ...t.args));
        }
      }
      timers.clear();
      W.requestAnimationFrame = native.raf;
      W.cancelAnimationFrame = native.caf;
      W.setTimeout = native.setTimeout;
      W.setInterval = native.setInterval;
      for (const [, cb] of frames) native.raf(cb);
      frames.clear();
      internal = true;
      try { for (const a of known.keys()) if (!a.__appPaused) native.play.call(a); } finally { internal = false; }
    },
    info() {
      census();
      return { now: vnow, stepMs: STEP, pendingFrames: frames.size, pendingTimers: timers.size,
               animations: known.size, uncontrolled: Object.fromEntries(Object.entries(seen).filter(([, n]) => n > 0)) };
    },
  };
})();
