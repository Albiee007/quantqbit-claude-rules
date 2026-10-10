/* Seek runtime for video compositions (render_video.py injects it before any page script).

   window.__hf = { fps, frames, duration, ready(timeoutMs), seek(seconds, {raf}), waitFor(promise, label), rand(key) }
   is the HyperFrames engine protocol (window.__hf.seek(t)); our renderer calls seek(n / fps) for
   whole frames n and the runtime turns the time back into a frame: n = floor(t * fps + 1e-6).

   Contract (brand-video references/composition-contract.md):
   - seek(n) gives the same pixels whatever was seeked before. Only declarative animation is
     allowed: Web Animations (el.animate) and CSS @keyframes, created at load, paused, positioned by
     absolute time. WAAPI times are composition time; CSS @keyframes times are relative to the
     nearest [data-start] clip (the time base HyperFrames 0.8.119 uses, checked in the M0 spike).
   - A clip ([data-start][data-duration]) is visible for frames [start, end).
   - Stray clock reads are frozen (Date, performance.now): a safety net, not the guarantee.
   - The runtime keeps the browser's own requestAnimationFrame / setTimeout in this closure; after
     each seek it waits for one real frame (macOS returned stale frames without it), bounded.
*/
(function () {
  'use strict';
  if (window.__hf) return; // injected before the page's own copy, or another engine's runtime
  const nativeRAF = window.requestAnimationFrame.bind(window);
  const nativeSetTimeout = window.setTimeout.bind(window);
  const nativeClearTimeout = window.clearTimeout.bind(window);
  const NativePromise = window.Promise;

  const EPOCH = Date.UTC(2026, 0, 1);
  const NativeDate = Date;
  // Date() without new returns a string, with new an object; both see the fixed epoch.
  function FrozenDate(...a) {
    if (!new.target) return new NativeDate(EPOCH).toString();
    return Reflect.construct(NativeDate, a.length ? a : [EPOCH], new.target);
  }
  FrozenDate.prototype = NativeDate.prototype;
  FrozenDate.UTC = NativeDate.UTC;
  FrozenDate.parse = NativeDate.parse;
  FrozenDate.now = () => EPOCH;
  window.Date = FrozenDate;
  try { Object.defineProperty(performance, 'now', { value: () => 0, configurable: true }); } catch (e) { /* read-only */ }

  function withTimeout(p, ms, what) {
    return new NativePromise((resolve, reject) => {
      const t = nativeSetTimeout(() => reject(new Error(`timed out after ${ms} ms waiting for ${what()}`)), ms);
      p.then((v) => { nativeClearTimeout(t); resolve(v); }, (e) => { nativeClearTimeout(t); reject(e); });
    });
  }
  const oneFrame = () => new NativePromise((resolve) => nativeRAF(() => resolve()));
  const toFrames = (s, fps) => Math.floor(Number(s) * fps + 0.5);

  let root = null, fps = 30, frames = 0, clips = [], current = -1;
  // Every animation seen so far: a finished animation with fill 'none' leaves
  // document.getAnimations(), but a backward seek must still reach it.
  const known = new Set();
  const animations = () => { document.getAnimations().forEach((a) => known.add(a)); return [...known]; };
  const waits = [];

  function scan() {
    root = document.querySelector('[data-composition-id]');
    if (!root) throw new Error('no [data-composition-id] root element');
    fps = Number(root.dataset.fps || 30);
    frames = toFrames(root.dataset.duration, fps);
    clips = [...root.querySelectorAll('[data-start][data-duration]')].map((el) => {
      const start = toFrames(el.dataset.start, fps);
      return { el, start, end: start + toFrames(el.dataset.duration, fps) };
    });
  }

  function clipStartMs(el) {
    const host = el && el.closest('[data-start]');
    return host ? (toFrames(host.dataset.start, fps) * 1000) / fps : 0;
  }

  function hash32(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  window.__hf = {
    get fps() { return fps; },
    get frames() { return frames; },
    get duration() { return frames / fps; },
    get frame() { return current; },
    /* Something the page loads asynchronously (a font, a Lottie file): ready() waits for it. */
    waitFor(promise, label) { waits.push([NativePromise.resolve(promise), String(label)]); },
    /* Deterministic "randomness": a pure function of the composition id and a key. */
    rand(key) {
      const r = root || document.querySelector('[data-composition-id]');
      return hash32(String(r ? r.dataset.compositionId : '') + '\u0000' + key) / 4294967296;
    },
    ready(timeoutMs = 20000) {
      const pending = new Set(['fonts']);
      const work = (async () => {
        await document.fonts.ready;
        pending.delete('fonts');
        waits.forEach(([, label]) => pending.add(label));
        await NativePromise.all(waits.map(([p, label]) => p.then(() => pending.delete(label))));
        const imgs = [...document.images];
        imgs.forEach((i) => pending.add('image ' + (i.getAttribute('src') || '')));
        await NativePromise.all(imgs.map((i) => i.decode().catch(() => { throw new Error('image failed to decode: ' + i.getAttribute('src')); })
          .then(() => pending.delete('image ' + (i.getAttribute('src') || '')))));
        scan();
        const anims = animations();
        anims.forEach((a) => a.pause());
        let endMs = 0, infinite = 0;
        for (const a of anims) {
          const t = a.effect && a.effect.getComputedTiming();
          if (!t) continue;
          if (!Number.isFinite(t.endTime)) { infinite += 1; continue; }
          endMs = Math.max(endMs, t.endTime + (typeof CSSAnimation !== 'undefined' && a instanceof CSSAnimation ? clipStartMs(a.effect.target) : 0));
        }
        return { fps, frames, clips: clips.length, animations: anims.length, animationEndMs: endMs, infinite };
      })();
      return withTimeout(work, timeoutMs, () => [...pending].join(', ') || 'the page');
    },
    seek(t, opts) {
      const n = Math.floor(Number(t) * fps + 1e-6);
      for (const c of clips) c.el.style.visibility = n >= c.start && n < c.end ? 'visible' : 'hidden';
      const ms = (n * 1000) / fps;
      for (const a of animations()) {
        a.pause();
        const css = typeof CSSAnimation !== 'undefined' && a instanceof CSSAnimation;
        a.currentTime = Math.max(0, ms - (css && a.effect ? clipStartMs(a.effect.target) : 0));
      }
      void document.body.getBoundingClientRect(); // style and layout now, not at the next frame
      current = n;
      if (opts && opts.raf === false) return n;
      return withTimeout(oneFrame().then(() => n), 2000, () => 'a rendered frame');
    },
  };
})();
