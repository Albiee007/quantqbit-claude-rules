// M0 prototype of clock.js + timeline.js (init script; runs before any page script).
// CSS animations seek relative to their clip's data-start and WAAPI animations to the composition
// clock: the same time base HyperFrames 0.8.119 uses (checked in the M0 spike).
(function () {
  "use strict";
  // Native scheduling, captured before page code can replace it, kept in this closure only.
  const nativeRAF = window.requestAnimationFrame.bind(window);
  const nativeSetTimeout = window.setTimeout.bind(window);
  const nativeClearTimeout = window.clearTimeout.bind(window);
  const NativePromise = window.Promise;

  // Safety net: stray clock reads are frozen (not advanced). History independence comes from
  // declarative animation + lint, not from this.
  const EPOCH = Date.UTC(2026, 0, 1);
  const NativeDate = Date;
  class FrozenDate extends NativeDate {
    constructor(...a) { if (a.length) super(...a); else super(EPOCH); }
    static now() { return EPOCH; }
  }
  window.Date = FrozenDate;
  const perfNow = () => 0;
  try { Object.defineProperty(performance, "now", { value: perfNow, configurable: true }); } catch (e) {}

  function withTimeout(p, ms, what) {
    return new NativePromise((res, rej) => {
      const t = nativeSetTimeout(() => rej(new Error(`timed out after ${ms} ms waiting for ${what()}`)), ms);
      p.then((v) => { nativeClearTimeout(t); res(v); }, (e) => { nativeClearTimeout(t); rej(e); });
    });
  }
  const frameRAF = () => new NativePromise((r) => nativeRAF(() => r()));

  let root = null, fps = 30, frames = 0, clips = [];
  const waits = [];
  function scan() {
    root = document.querySelector("[data-composition-id]");
    if (!root) throw new Error("no [data-composition-id] root");
    fps = Number(root.dataset.fps || 30);
    frames = Math.floor(Number(root.dataset.duration) * fps + 0.5);
    clips = [...root.querySelectorAll(".clip[data-start]")].map((el) => {
      const s = Math.floor(Number(el.dataset.start) * fps + 0.5);
      const d = Math.floor(Number(el.dataset.duration) * fps + 0.5);
      return { el, start: s, end: s + d };
    });
  }

  function hash32(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }

  window.__hf = {
    get fps() { return fps; },
    get frames() { return frames; },
    get duration() { return frames / fps; },
    waitFor(promise, label) { waits.push([NativePromise.resolve(promise), String(label)]); },
    rand(key) { return hash32(String(root && root.dataset.compositionId) + "\u0000" + key) / 4294967296; },
    ready(timeoutMs = 20000) {
      const pending = new Set(["fonts"]);
      const work = (async () => {
        scan();
        await document.fonts.ready; pending.delete("fonts");
        const imgs = [...document.images];
        imgs.forEach((i) => pending.add("img " + (i.getAttribute("src") || "")));
        await NativePromise.all(imgs.map((i) => i.decode().then(() => pending.delete("img " + (i.getAttribute("src") || "")))));
        waits.forEach(([, l]) => pending.add(l));
        await NativePromise.all(waits.map(([p, l]) => p.then(() => pending.delete(l))));
        document.getAnimations().forEach((a) => a.pause());
        return { fps, frames, clips: clips.length, animations: document.getAnimations().length };
      })();
      return withTimeout(work, timeoutMs, () => [...pending].join(", ") || "nothing");
    },
    // seek(t): t in seconds; converted back to an integer frame. Pure function of the frame.
    seek(t, opts) {
      const n = Math.floor(t * fps + 1e-6);
      for (const c of clips) c.el.style.visibility = n >= c.start && n < c.end ? "visible" : "hidden";
      const ms = (n * 1000) / fps;
      for (const a of document.getAnimations()) {
        a.pause();
        let off = 0;
        if (typeof CSSAnimation !== "undefined" && a instanceof CSSAnimation && a.effect && a.effect.target) {
          const host = a.effect.target.closest("[data-start]");
          if (host) off = Math.floor(Number(host.dataset.start) * fps + 0.5) * 1000 / fps;
        }
        a.currentTime = Math.max(0, ms - off);
      }
      void document.body.getBoundingClientRect(); // style + layout flush
      if (opts && opts.raf === false) return n;
      return withTimeout(frameRAF().then(() => n), 2000, () => "a frame");
    },
  };
})();
