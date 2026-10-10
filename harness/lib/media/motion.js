/* Video scenes for brand-video, built from the approved video concept (window.AD, resolved by
   Python) and the piece's frame plan (window.VIDEO). Everything is drawn with artdir.js, so a video
   frame carries the same backgrounds, type and accents as the project's stills.

   Every animation is a paused Web Animation with an absolute delay on the composition clock
   (timeline.js seeks them); nothing reads a clock or schedules a timer. Times arrive from Python
   in whole frames and are turned into milliseconds here: ms(n) = n * 1000 / fps.

   VIDEO = { id, width, height, fps, frames, safe: {top, right, bottom, left}, typeScale, draft, assets: {logo?},
             scenes: [{ id, template, start, frames, overlap, enter, transition, layout, background, copy,
                        media?: {src, fit, motion, focus} }] }
   Type is sized from the format's short side (times typeScale), so a 9:16, 1:1 or 16:9 frame of
   the same piece reads alike; captions never run wider than about 1.3 short sides. */
(function () {
  'use strict';
  const V = window.VIDEO;
  const AD = window.AD;
  const M = AD.motion;
  const ms = (n) => (n * 1000) / V.fps;
  const animations = [];

  function anim(el, keyframes, delayMs, durationMs, easing, fill) {
    if (!el || durationMs <= 0) return null;
    const a = el.animate(keyframes, { delay: delayMs, duration: durationMs, easing: easing || M.easing.standard, fill: fill || 'both' });
    a.pause();
    animations.push(a);
    return a;
  }

  /* ---------------- text entrances and exits */
  const TEXT_IN = {
    'fade-up': (px) => [{ opacity: 0, transform: `translateY(${px * 0.45}px)` }, { opacity: 1, transform: 'none' }],
    'mask-up': (px) => [{ clipPath: 'inset(100% 0 0 0)', transform: `translateY(${px * 0.3}px)` }, { clipPath: 'inset(0 0 0 0)', transform: 'none' }],
    'scale-in': () => [{ opacity: 0, transform: 'scale(0.94)' }, { opacity: 1, transform: 'none' }],
    fade: () => [{ opacity: 0 }, { opacity: 1 }],
    'word-stagger': (px) => [{ opacity: 0, transform: `translateY(${px * 0.35}px)` }, { opacity: 1, transform: 'none' }],
  };

  function splitWords(el) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let n = walker.nextNode(); n; n = walker.nextNode()) nodes.push(n);
    const spans = [];
    for (const n of nodes) {
      const frag = document.createDocumentFragment();
      for (const part of n.textContent.split(/(\s+)/)) {
        if (!part) continue;
        if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); continue; }
        const s = document.createElement('span');
        s.className = 'w';
        s.style.display = 'inline-block';
        s.textContent = part;
        frag.appendChild(s);
        spans.push(s);
      }
      n.parentNode.replaceChild(frag, n);
    }
    return spans;
  }

  /* Animate the parts of a scene's text in order (kicker, head, sub, points...), starting at startMs. */
  function textIn(parts, startMs, px) {
    const style = M.textIn;
    if (style === 'none' || !TEXT_IN[style]) return 0;
    const step = M.stagger.perItemMs, max = M.stagger.maxItems, dur = M.durations.base;
    let items = [];
    for (const p of parts) {
      if (!p) continue;
      if (style === 'word-stagger' && p.tagName === 'H1') items = items.concat(splitWords(p));
      else items.push(p);
    }
    items.forEach((el, i) => anim(el, TEXT_IN[style](px), startMs + Math.min(i, max - 1) * step, dur, M.easing.enter));
    return items.length ? Math.min(items.length - 1, max - 1) * step + dur : 0;
  }

  function textOut(parts, endMs, px) {
    const style = M.textOut;
    if (style === 'none' || !TEXT_IN[style]) return;
    const dur = M.durations.fast;
    const kf = TEXT_IN[style](px).slice().reverse();
    parts.filter(Boolean).forEach((el) => anim(el, kf, endMs - dur, dur, M.easing.exit, 'forwards'));
  }

  /* ---------------- transitions: the incoming scene (and, for some, the outgoing one) */
  function transition(prev, next, startMs, overlapMs, type) {
    if (!overlapMs || type === 'cut') return;
    const E = M.easing;
    switch (type) {
      case 'fade':
        anim(next, [{ opacity: 0 }, { opacity: 1 }], startMs, overlapMs, E.standard);
        break;
      case 'dip':
        anim(prev, [{ opacity: 1 }, { opacity: 0 }], startMs, overlapMs / 2, E.exit, 'forwards');
        anim(next, [{ opacity: 0 }, { opacity: 1 }], startMs + overlapMs / 2, overlapMs / 2, E.enter);
        break;
      case 'slide':
        anim(next, [{ transform: 'translateX(100%)' }, { transform: 'none' }], startMs, overlapMs, E.enter);
        break;
      case 'push':
        anim(next, [{ transform: 'translateX(100%)' }, { transform: 'none' }], startMs, overlapMs, E.standard);
        anim(prev, [{ transform: 'none' }, { transform: 'translateX(-100%)' }], startMs, overlapMs, E.standard, 'forwards');
        break;
      case 'scale':
        anim(next, [{ opacity: 0, transform: 'scale(1.06)' }, { opacity: 1, transform: 'none' }], startMs, overlapMs, E.enter);
        break;
      case 'wipe':
        anim(next, [{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0 0 0)' }], startMs, overlapMs, E.standard);
        break;
      default:
        break;
    }
  }

  /* ---------------- templates: each returns the text parts to animate, in reading order */
  const W = V.width, H = V.height, S = V.safe;
  const innerW = W - S.left - S.right;
  const short = Math.min(W, H) * (V.typeScale || 1);
  const capW = Math.min(innerW, short * 1.3);
  const headPx = () => short * AD.caption.headScale;

  function placeCaption(parent, copy, bgName, layout, px) {
    const align = layout === 'type-center' ? 'center' : AD.caption.align;
    const left = align === 'center' ? S.left + (innerW - capW) / 2 : S.left;
    const box = { left, width: capW, top: 0, headPx: px, align, bgName };
    const cap = ArtDir.caption(parent, copy, box);
    const room = H - S.top - S.bottom;
    let top;
    if (layout === 'type-lower') top = S.top + room * 0.62 - cap.offsetHeight / 2;
    else if (layout === 'type-center') top = S.top + (room - cap.offsetHeight) / 2;
    else top = S.top + room * 0.38 - cap.offsetHeight / 2;
    top = Math.max(S.top, Math.min(top, H - S.bottom - cap.offsetHeight));
    cap.style.top = top + 'px';
    return cap;
  }

  function capParts(cap) {
    return [cap.querySelector('.kicker'), cap.querySelector('h1'), cap.querySelector('p')];
  }

  function textBlock(parent, bgName, lines, px, align, top) {
    const b = ArtDir.bg(bgName);
    const el = document.createElement('div');
    el.className = 'cap';
    el.dataset.bg = bgName;
    const left = align === 'center' ? S.left + (innerW - capW) / 2 : S.left;
    el.style.cssText = `position:absolute;left:${left}px;width:${capW}px;top:${top}px;text-align:${align === 'center' ? 'center' : 'start'};`;
    for (const line of lines) {
      const p = document.createElement('p');
      p.style.cssText = `margin:0 0 ${px * 0.5}px;${ArtDir.textCSS(AD.caption.sub, px)}color:${b.text.sub}`;
      p.innerHTML = ArtDir.copy(line);
      el.appendChild(p);
    }
    parent.appendChild(el);
    return el;
  }

  const TEMPLATES = {
    title(el, sc) {
      return capParts(placeCaption(el, sc.copy, sc.background, sc.layout, headPx()));
    },
    feature(el, sc) {
      const px = headPx();
      const cap = placeCaption(el, { kicker: sc.copy.kicker, head: sc.copy.head, sub: sc.copy.sub }, sc.background, sc.layout, px);
      const points = sc.copy.points || [];
      if (!points.length) return capParts(cap);
      const subPx = px * AD.caption.subRatio * 1.05;
      const block = textBlock(el, sc.background, points.map((p) => '— ' + p), subPx,
        sc.layout === 'type-center' ? 'center' : AD.caption.align, 0);
      const below = cap.offsetTop + cap.offsetHeight + px * 0.7;
      const top = Math.min(below, H - S.bottom - block.offsetHeight);
      if (top < below) cap.style.top = Math.max(S.top, top - px * 0.7 - cap.offsetHeight) + 'px';
      block.style.top = Math.max(top, cap.offsetTop + cap.offsetHeight + px * 0.4) + 'px';
      return capParts(cap).concat([...block.querySelectorAll('p')]);
    },
    stat(el, sc) {
      const px = headPx();
      const b = ArtDir.bg(sc.background);
      const cap = document.createElement('div');
      cap.className = 'cap';
      cap.dataset.bg = sc.background;
      const align = sc.layout === 'type-center' ? 'center' : AD.caption.align;
      const left = align === 'center' ? S.left + (innerW - capW) / 2 : S.left;
      cap.style.cssText = `position:absolute;left:${left}px;width:${capW}px;top:0;text-align:${align === 'center' ? 'center' : 'start'};`;
      const sub = px * AD.caption.subRatio;
      cap.innerHTML =
        (sc.copy.kicker && AD.caption.kicker ? `<div class="kicker" style="${ArtDir.textCSS(AD.caption.kicker, sub * 0.86)}color:${b.text.accent};margin:0 0 ${sub * 0.6}px">${ArtDir.copy(sc.copy.kicker)}</div>` : '') +
        `<h1 style="margin:0;${ArtDir.textCSS(AD.caption.head, px * 2.6)}color:${b.text.accent}">${ArtDir.copy(sc.copy.value || '')}</h1>` +
        (sc.copy.label ? `<p style="margin:${px * 0.2}px 0 0;${ArtDir.textCSS(AD.caption.head, px * 0.8)}color:${b.text.head}">${ArtDir.copy(sc.copy.label)}</p>` : '') +
        (sc.copy.sub ? `<p class="sub" style="margin:${px * 0.4}px 0 0;${ArtDir.textCSS(AD.caption.sub, sub)}color:${b.text.sub}">${ArtDir.copy(sc.copy.sub)}</p>` : '');
      el.appendChild(cap);
      const room = H - S.top - S.bottom;
      cap.style.top = Math.max(S.top, S.top + (room - cap.offsetHeight) * (sc.layout === 'type-lower' ? 0.7 : 0.45)) + 'px';
      return [cap.querySelector('.kicker'), cap.querySelector('h1'), ...cap.querySelectorAll('p')];
    },
    'end-card'(el, sc) {
      const px = headPx();
      const parts = [];
      let logoBottom = S.top;
      if (V.assets.logo && AD.endCard.logo) {
        const img = document.createElement('img');
        img.className = 'logo';
        img.alt = '';
        img.src = V.assets.logo;
        const h = px * 1.6;
        const top = S.top + (H - S.top - S.bottom) * 0.3;
        // centred by CSS, not by measuring: the image may not have loaded yet at build time
        img.style.cssText = `position:absolute;height:${h}px;width:auto;max-width:${innerW}px;left:0;right:0;` +
          `margin:0 auto;top:${top}px;display:block;`;
        el.appendChild(img);
        logoBottom = top + h;
        parts.push(img);
      }
      const copy = { kicker: sc.copy.kicker, head: sc.copy.head, sub: sc.copy.url || sc.copy.sub };
      const cap = ArtDir.caption(el, copy, { left: S.left + (innerW - capW) / 2, width: capW, top: 0, headPx: px * 0.9, align: 'center', bgName: sc.background });
      cap.style.top = Math.min(H - S.bottom - cap.offsetHeight, Math.max(logoBottom + px * 0.8, S.top + (H - S.top - S.bottom - cap.offsetHeight) / 2)) + 'px';
      return parts.concat(capParts(cap));
    },
    /* A picture filling the frame (cover) or framed on the scene background (contain), with an
       optional slow linear move over the whole scene, and an optional caption on top. */
    still(el, sc) {
      const m = sc.media;
      const [fy0, fx0] = [(m.focus || [0.5, 0.5])[1], (m.focus || [0.5, 0.5])[0]];
      // a pan needs picture beyond both edges: keep its zoom origin near the middle
      const fx = m.motion && m.motion.startsWith('pan-') ? Math.min(0.625, Math.max(0.375, fx0)) : fx0;
      const fy = fy0;
      const img = document.createElement('img');
      img.className = 'still-image';
      img.alt = '';
      img.src = m.src;
      img.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;object-fit:${m.fit};` +
        `object-position:${fx * 100}% ${fy * 100}%;transform-origin:${fx * 100}% ${fy * 100}%;`;
      el.appendChild(img);
      const z = 1.08, dx = W * 0.03;
      const MOVES = {
        'push-in': [{ transform: 'scale(1)' }, { transform: `scale(${z})` }],
        'pull-out': [{ transform: `scale(${z})` }, { transform: 'scale(1)' }],
        'pan-left': [{ transform: `translateX(${dx}px) scale(${z})` }, { transform: `translateX(${-dx}px) scale(${z})` }],
        'pan-right': [{ transform: `translateX(${-dx}px) scale(${z})` }, { transform: `translateX(${dx}px) scale(${z})` }],
      };
      if (MOVES[m.motion]) anim(img, MOVES[m.motion], ms(sc.start), ms(sc.frames), 'linear');
      const c = sc.copy || {};
      if (!c.head && !c.sub && !c.kicker) return [];
      return capParts(placeCaption(el, c, sc.background, sc.layout, headPx()));
    },
  };

  /* ---------------- build */
  function build() {
    const root = document.getElementById('root');
    Object.assign(root.style, { width: W + 'px', height: H + 'px', background: AD.roles.canvas });
    const els = [];
    V.scenes.forEach((sc, i) => {
      const el = document.createElement('section');
      el.className = 'clip scene';
      el.id = 'scene-' + sc.id;
      el.dataset.start = (sc.start / V.fps).toFixed(6);
      el.dataset.duration = (sc.frames / V.fps).toFixed(6);
      el.dataset.trackIndex = String(i % 2);
      el.dataset.template = sc.template;
      el.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px;overflow:hidden;z-index:${i + 1};` +
        `background:${ArtDir.background(ArtDir.bg(sc.background))};`;
      root.appendChild(el);
      if (AD.motif) {
        const m = ArtDir.motif(el, W, H);
        if (m && M.motifMotion === 'drift') anim(m, [{ transform: 'translate(0, 0)' }, { transform: `translate(${-W * 0.04}px, ${-H * 0.02}px)` }], ms(sc.start), ms(sc.frames), 'linear');
        if (m && M.motifMotion === 'pulse') anim(m, [{ opacity: AD.motif.opacity }, { opacity: AD.motif.opacity * 1.6 }, { opacity: AD.motif.opacity }], ms(sc.start), ms(sc.frames), M.easing.standard);
      }
      const parts = TEMPLATES[sc.template](el, sc);
      const start = ms(sc.start);
      transition(els[i - 1], el, start, ms(sc.overlap), sc.transition);
      textIn(parts, start + ms(sc.overlap), headPx());
      const next = V.scenes[i + 1];
      if (next) textOut(parts, ms(next.start), headPx());
      els.push(el);
    });
    if (V.draft) {
      const tag = document.createElement('div');
      tag.className = 'draft-tag';
      tag.textContent = 'DRAFT · not approved';
      tag.style.cssText = 'position:absolute;right:24px;bottom:24px;z-index:9999;font:600 28px/1 sans-serif;' +
        'padding:10px 14px;background:rgba(0,0,0,.72);color:#fff;border-radius:8px;';
      root.appendChild(tag);
    }
    return animations.length;
  }

  window.__composition = ArtDir.loadFaces(AD.faces, [], 15000).then(build);
  if (window.__hf) window.__hf.waitFor(window.__composition, 'scene build');
})();
