/* A tiny Lottie-style player for the brand-video tests. It is not lottie-web: it reads a two-key
   "animation" ({fr, op, from: [x, y], to: [x, y], r, color}) and draws one SVG circle, with the
   surface the seek runtime uses (goToAndStop(ms, false), getDuration, pause). MIT, written for these
   tests. */
(function () {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  function loadAnimation(opts) {
    const d = opts.animationData;
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', '100%');
    svg.setAttribute('viewBox', '0 0 100 100');
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('r', String(d.r));
    c.setAttribute('fill', d.color);
    svg.appendChild(c);
    opts.container.appendChild(svg);
    const anim = {
      goToAndStop(value, isFrame) {
        const frame = isFrame ? value : (value / 1000) * d.fr;
        const k = Math.min(1, Math.max(0, frame / d.op));
        c.setAttribute('cx', String(d.from[0] + (d.to[0] - d.from[0]) * k));
        c.setAttribute('cy', String(d.from[1] + (d.to[1] - d.from[1]) * k));
      },
      getDuration(inFrames) { return inFrames ? d.op : d.op / d.fr; },
      pause() {},
    };
    anim.goToAndStop(0, true);
    return anim;
  }
  window.minilottie = { loadAnimation };
})();
