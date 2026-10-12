/* A tiny GSAP-style timeline for the brand-video tests. It is not GSAP: it has just the surface the
   seek runtime uses (totalTime, totalDuration, pause), so a custom scene can be tested without
   shipping a third-party library. MIT, written for these tests. */
(function () {
  'use strict';
  function Timeline() { this.tweens = []; this.time = 0; }
  Timeline.prototype.to = function (el, props, at, dur) {
    this.tweens.push({ el, props, at, dur });
    return this;
  };
  Timeline.prototype.totalTime = function (t) {
    this.time = t;
    for (const w of this.tweens) {
      const k = Math.min(1, Math.max(0, (t - w.at) / w.dur));
      const x = (w.props.x || 0) * k;
      const y = (w.props.y || 0) * k;
      w.el.style.transform = `translate(${x}px, ${y}px)`;
      if ('opacity' in w.props) w.el.style.opacity = String(k * w.props.opacity);
    }
    return this;
  };
  Timeline.prototype.totalDuration = function () {
    return this.tweens.reduce((m, w) => Math.max(m, w.at + w.dur), 0);
  };
  Timeline.prototype.pause = function () { return this; };
  window.minitl = { timeline: () => new Timeline() };
})();
