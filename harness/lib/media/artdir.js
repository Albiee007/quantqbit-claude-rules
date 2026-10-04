/* Art-direction runtime shared by the store frame (store-mockups) and the marketing canvas
   (brand-assets). Everything it draws comes from window.AD, which the Python side resolves from
   the approved concept: colours are CSS strings and fonts are stacks. It never resolves tokens,
   so Python and the browser can't disagree about a value.

   AD = { roles, type, backgrounds: {name: {recipe, color|stops, angle, space, panel, text:{head,sub,accent,onAccent}}},
          caption: {head, sub, kicker?: {stack, weight, italic, tracking, lineHeight, case}, align, accent, headScale, subRatio},
          device?: {style, bezel, radius, shadow}, motif?: {src, opacity, placement, scale}, faces: [...] }
   Copy is data: copy() escapes it and keeps only balanced <em>…</em> as the accent. */
(function () {
  'use strict';

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function copy(s) {
    let open = 0;
    const out = esc(s).replace(/&lt;(\/?)em&gt;/g, (m, slash) => {
      if (!slash) { open += 1; return '<em>'; }
      if (open > 0) { open -= 1; return '</em>'; }
      return '';
    });
    return out + '</em>'.repeat(open);
  }

  function bg(name) {
    const b = window.AD.backgrounds[name];
    if (!b) throw new Error(`ArtDir: no background named "${name}" in the concept`);
    return b;
  }

  function background(spec) {
    if (spec.recipe === 'solid') return spec.color;
    if (spec.recipe === 'linear') {
      const space = spec.space === 'srgb' ? 'srgb' : 'oklab';
      return `linear-gradient(${Number(spec.angle ?? 180)}deg in ${space}, ${spec.stops.join(', ')})`;
    }
    throw new Error('ArtDir: unknown background recipe ' + spec.recipe);
  }

  function textCSS(ts, px) {
    return `font-family:${ts.stack};font-weight:${ts.weight};font-style:${ts.italic ? 'italic' : 'normal'};` +
      `font-size:${px}px;line-height:${ts.lineHeight};letter-spacing:${ts.tracking}em;` +
      (ts.case === 'upper' ? 'text-transform:uppercase;' : '');
  }

  function accent(em, b) {
    em.style.fontStyle = 'inherit';
    switch (window.AD.caption.accent) {
      case 'color':
        em.style.color = b.text.accent;
        break;
      case 'underline':
        Object.assign(em.style, { textDecorationLine: 'underline', textDecorationColor: b.text.accent,
          textDecorationThickness: '0.09em', textUnderlineOffset: '0.14em' });
        break;
      case 'highlight':
        Object.assign(em.style, { backgroundColor: b.text.accent, color: b.text.onAccent, padding: '0 0.12em',
          borderRadius: '0.1em', boxDecorationBreak: 'clone', webkitBoxDecorationBreak: 'clone' });
        break;
      default:
        break;
    }
  }

  /* A caption block. box: {left, width, top | bottom, headPx, align?, bgName}. Returns the element. */
  function caption(parent, c, box) {
    const cap = window.AD.caption;
    const b = bg(box.bgName);
    const head = box.headPx;
    const sub = head * cap.subRatio;
    const align = box.align || cap.align;
    const el = document.createElement('div');
    el.className = 'cap';
    el.dataset.bg = box.bgName;
    el.style.cssText = `position:absolute;left:${box.left}px;width:${box.width}px;text-align:${align === 'center' ? 'center' : 'start'};`;
    let html = '';
    if (c.kicker && cap.kicker) html += `<div class="kicker" style="${textCSS(cap.kicker, sub * 0.86)}color:${b.text.accent};margin:0 0 ${sub * 0.55}px">${copy(c.kicker)}</div>`;
    if (c.head) html += `<h1 style="margin:0;${textCSS(cap.head, head)}color:${b.text.head}">${copy(c.head)}</h1>`;
    if (c.sub) html += `<p style="margin:${c.head ? head * 0.34 : 0}px 0 0;${textCSS(cap.sub, sub)}color:${b.text.sub}">${copy(c.sub)}</p>`;
    el.innerHTML = html;
    el.querySelectorAll('em').forEach((em) => accent(em, b));
    parent.appendChild(el);
    el.style.top = (box.bottom !== undefined ? box.bottom - el.offsetHeight : box.top) + 'px';
    return el;
  }

  const SHADOWS = {
    none: () => 'none',
    soft: (w) => `0 ${0.045 * w}px ${0.09 * w}px rgba(0,0,0,.24)`,
    long: (w) => `${0.06 * w}px ${0.09 * w}px ${0.05 * w}px rgba(0,0,0,.18)`,
    crisp: (w) => `0 ${0.014 * w}px 0 rgba(0,0,0,.28)`,
  };

  /* A device showing `inner` (a screen of SW x SH logical px) at scale s. Returns {el, w, h}. */
  function device(inner, SW, SH, s) {
    const d = window.AD.device;
    const framed = d.style === 'frame';
    const bz = framed ? 26 * s : 0;
    const w = SW * s + 2 * bz;
    const h = SH * s + 2 * bz;
    const r = d.radius * w;
    const el = document.createElement('div');
    el.className = 'device';
    el.style.cssText = `position:absolute;width:${w}px;height:${h}px;border-radius:${r}px;` +
      `background:${framed ? d.bezel : 'transparent'};box-shadow:${(SHADOWS[d.shadow] || SHADOWS.soft)(w)};`;
    el.innerHTML = `<div class="glass" style="position:absolute;left:${bz}px;top:${bz}px;width:${SW * s}px;height:${SH * s}px;` +
      `border-radius:${Math.max(0, r - bz)}px;overflow:hidden;background:var(--bg)">` +
      `<div style="transform:scale(${s});transform-origin:0 0;width:${SW}px;height:${SH}px;position:relative">${inner}</div></div>`;
    return { el, w, h };
  }

  function motif(parent, W, H, anchor) {
    const m = window.AD.motif;
    if (!m) return null;
    const img = document.createElement('img');
    img.className = 'motif';
    img.alt = '';
    img.src = m.src;
    const size = Math.max(W, H) * m.scale;
    let css = `position:absolute;width:${size}px;height:${size}px;object-fit:contain;opacity:${m.opacity};pointer-events:none;`;
    if (m.placement === 'edge') css += `left:${-size * 0.45}px;top:${H * 0.5 - size / 2}px;`;
    else if (m.placement === 'behind-device' && anchor) css += `left:${anchor.x - size / 2}px;top:${anchor.y - size / 2}px;`;
    else css += `left:${W - size * 0.62}px;top:${H - size * 0.62}px;`;
    img.style.cssText = css;
    parent.appendChild(img);
    return img;
  }

  /* ---------------- store frame layouts: ctx = {W, H, parent, left, frame, bgName, fit(maxW, maxH) -> device} */
  function headPx(W, H, k = 1) { return Math.min(W * window.AD.caption.headScale * k, H * 0.05); }

  function place(ctx, dev, x, y) {
    Object.assign(dev.el.style, { left: ctx.left + x + 'px', top: y + 'px' });
    ctx.parent.appendChild(dev.el);
    return dev;
  }

  const store = {
    'caption-top'(ctx) {
      const { W, H } = ctx, pad = W * 0.07;
      const cap = caption(ctx.parent, ctx.frame, { left: ctx.left + pad, width: W - 2 * pad, top: H * 0.05, headPx: headPx(W, H), bgName: ctx.bgName });
      const top = cap.offsetTop + cap.offsetHeight + H * 0.035;
      const dev = ctx.fit(W * (ctx.wide ? 0.6 : 0.78), H - top - H * 0.03);
      return place(ctx, dev, (W - dev.w) / 2, top);
    },
    'caption-bottom'(ctx) {
      const { W, H } = ctx, pad = W * 0.07;
      const cap = caption(ctx.parent, ctx.frame, { left: ctx.left + pad, width: W - 2 * pad, bottom: H * 0.95, headPx: headPx(W, H), bgName: ctx.bgName });
      const dev = ctx.fit(W * (ctx.wide ? 0.6 : 0.78), cap.offsetTop - H * 0.035 - H * 0.04);
      return place(ctx, dev, (W - dev.w) / 2, H * 0.04);
    },
    'split-left'(ctx) { return split(ctx, 'left'); },
    'split-right'(ctx) { return split(ctx, 'right'); },
    inset(ctx) {
      const { W, H } = ctx, pad = W * 0.06;
      const b = bg(ctx.bgName);
      const cap = caption(ctx.parent, ctx.frame, { left: ctx.left + pad, width: W - 2 * pad, top: H * 0.05, headPx: headPx(W, H), bgName: ctx.bgName });
      const top = cap.offsetTop + cap.offsetHeight + H * 0.03;
      const panel = document.createElement('div');
      panel.className = 'panel';
      panel.style.cssText = `position:absolute;left:${ctx.left + pad}px;top:${top}px;width:${W - 2 * pad}px;height:${H - top - pad}px;` +
        `border-radius:${W * 0.05}px;background:${b.panel};overflow:hidden;`;
      ctx.parent.appendChild(panel);
      const dev = ctx.fit((W - 2 * pad) * (ctx.wide ? 0.6 : 0.8), Infinity);
      Object.assign(dev.el.style, { left: (W - 2 * pad - dev.w) / 2 + 'px', top: W * 0.06 + 'px' });
      panel.appendChild(dev.el);
      return dev;
    },
  };

  function split(ctx, side) {
    const { W, H } = ctx, pad = W * 0.07;
    const devW = W * (ctx.wide ? 0.42 : 0.54);
    const dev = ctx.fit(devW, H * 0.86);
    const colW = W - dev.w - pad * 2.2;
    const capLeft = side === 'left' ? pad : W - pad - colW;
    const devX = side === 'left' ? W - dev.w - pad * 0.6 : pad * 0.6;
    const devY = (H - dev.h) / 2;
    place(ctx, dev, devX, devY);
    const cap = caption(ctx.parent, ctx.frame, { left: ctx.left + capLeft, width: colW, top: 0, headPx: headPx(W, H, 0.82),
      align: 'start', bgName: ctx.bgName });
    cap.style.top = Math.max(H * 0.05, devY + dev.h * 0.32 - cap.offsetHeight / 2) + 'px';
    return dev;
  }

  /* ---------------- feature graphic layouts (1024 x 500): ctx = {W, H, parent, fg, bgName, fit(maxW, maxH)} */
  function fgText(ctx, left, width, align) {
    const b = bg(ctx.bgName);
    const T = window.AD.caption;
    const el = document.createElement('div');
    el.className = 'cap';
    el.dataset.bg = ctx.bgName;
    el.style.cssText = `position:absolute;left:${left}px;width:${width}px;top:0;bottom:0;display:flex;flex-direction:column;` +
      `justify-content:center;align-items:${align === 'center' ? 'center' : 'flex-start'};text-align:${align === 'center' ? 'center' : 'start'};`;
    const fg = ctx.fg;
    el.innerHTML =
      `<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px">` +
      (fg.iconSrc ? `<img src="${esc(fg.iconSrc)}" alt="" style="width:60px;height:60px;border-radius:14px">` : '') +
      (fg.title ? `<span style="${textCSS(T.sub, 28)}color:${b.text.head}">${copy(fg.title)}</span>` : '') +
      `</div>` +
      (fg.tagline ? `<h1 style="margin:0;${textCSS(T.head, 46)}color:${b.text.head}">${copy(fg.tagline)}</h1>` : '') +
      (fg.sub ? `<p style="margin:16px 0 0;max-width:${width - 20}px;${textCSS(T.sub, 20)}color:${b.text.sub}">${copy(fg.sub)}</p>` : '');
    el.querySelectorAll('h1 em, p em').forEach((em) => accent(em, b));
    ctx.parent.appendChild(el);
    return el;
  }

  const feature = {
    'split-device-right'(ctx) {
      fgText(ctx, 64, 560, 'start');
      if (ctx.fg.screen) { const d = ctx.fit(280, Infinity); place(ctx, d, 700, 40); }
    },
    'split-device-left'(ctx) {
      if (ctx.fg.screen) { const d = ctx.fit(280, Infinity); place(ctx, d, 44, 40); }
      fgText(ctx, 400, 560, 'start');
    },
    'centered-type'(ctx) { fgText(ctx, 112, 800, 'center'); },
  };

  /* ---------------- marketing canvas layouts: ctx = {W, H, parent, asset, bgName, slots: {image, logo}} */
  function logoEl(ctx, h, x, y) {
    if (!ctx.slots.logo) return null;
    const img = document.createElement('img');
    img.className = 'logo';
    img.alt = '';
    img.src = ctx.slots.logo;
    img.style.cssText = `position:absolute;left:${x}px;top:${y}px;height:${h}px;width:auto;`;
    ctx.parent.appendChild(img);
    return img;
  }

  const canvasLayouts = {
    'type-start'(ctx) {
      const { W, H } = ctx, pad = Math.min(W, H) * 0.1;
      logoEl(ctx, H * 0.08, pad, pad);
      const cap = caption(ctx.parent, ctx.asset.copy, { left: pad, width: W * 0.68, top: 0, headPx: W * window.AD.caption.headScale, align: 'start', bgName: ctx.bgName });
      cap.style.top = Math.max(pad + H * 0.12, (H - cap.offsetHeight) / 2) + 'px';
    },
    'type-center'(ctx) {
      const { W, H } = ctx, pad = Math.min(W, H) * 0.1;
      const logo = logoEl(ctx, H * 0.08, 0, pad);
      if (logo) logo.style.left = `calc(50% - ${logo.getBoundingClientRect().width / 2}px)`;
      const cap = caption(ctx.parent, ctx.asset.copy, { left: W * 0.1, width: W * 0.8, top: 0, headPx: W * window.AD.caption.headScale, align: 'center', bgName: ctx.bgName });
      cap.style.top = Math.max(pad + H * 0.12, (H - cap.offsetHeight) / 2) + 'px';
    },
    'split-image'(ctx) {
      const { W, H } = ctx, pad = Math.min(W, H) * 0.08;
      if (ctx.slots.image) {
        const img = document.createElement('img');
        img.className = 'art';
        img.alt = '';
        img.src = ctx.slots.image;
        img.style.cssText = `position:absolute;right:${pad}px;top:${pad}px;width:${W * 0.42}px;height:${H - 2 * pad}px;object-fit:cover;border-radius:${Math.min(W, H) * 0.04}px;`;
        ctx.parent.appendChild(img);
      }
      logoEl(ctx, H * 0.08, pad, pad);
      const cap = caption(ctx.parent, ctx.asset.copy, { left: pad, width: W * 0.46, top: 0, headPx: W * window.AD.caption.headScale * 0.9, align: 'start', bgName: ctx.bgName });
      cap.style.top = Math.max(pad + H * 0.12, (H - cap.offsetHeight) / 2) + 'px';
    },
    'logo-band'(ctx) {
      const { W, H } = ctx;
      const logo = logoEl(ctx, H * 0.4, 0, H * 0.3);
      if (logo) logo.style.left = `calc(50% - ${logo.getBoundingClientRect().width / 2}px)`;
      if (ctx.asset.copy && (ctx.asset.copy.head || ctx.asset.copy.sub)) {
        if (logo) logo.style.top = H * 0.16 + 'px';
        caption(ctx.parent, ctx.asset.copy, { left: W * 0.1, width: W * 0.8, top: H * 0.62, headPx: H * 0.11, align: 'center', bgName: ctx.bgName });
      }
    },
  };

  /* ---------------- fonts: wait for every face (bounded), then verify glyph coverage per caption run */
  function loadFaces(faces, extra, timeoutMs) {
    const specs = faces.map((f) => `${f.style === 'italic' ? 'italic ' : ''}${f.weight} 40px "${f.family}"`).concat(extra || []);
    const all = Promise.all(specs.map((s) => document.fonts.load(s).catch(() => null)));
    return Promise.race([all, new Promise((resolve) => setTimeout(resolve, timeoutMs || 8000))]);
  }

  function firstFamily(stack) { return String(stack).split(',')[0].trim().replace(/^["']|["']$/g, ''); }

  const measurer = document.createElement('canvas').getContext('2d');
  /* Characters of `text` that the first family does not draw (they fall back to another font). */
  function missingGlyphs(text, family, weight, italic) {
    const style = `${italic ? 'italic ' : ''}${weight} 40px "${family}"`;
    const miss = new Set();
    for (const ch of new Set(Array.from(text))) {
      if (!ch.trim()) continue;
      measurer.font = `${style}, monospace`;
      const a = measurer.measureText(ch).width;
      measurer.font = `${style}, serif`;
      const b = measurer.measureText(ch).width;
      if (Math.abs(a - b) > 0.01) miss.add(ch);
    }
    return [...miss].join('');
  }

  /* Is el drawn at all? (A video frame keeps hidden scenes in the page.) */
  function shown(el) {
    if (getComputedStyle(el).visibility === 'hidden') return false;
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      if (Number(getComputedStyle(e).opacity) === 0) return false;
    }
    return true;
  }

  /* Caption runs for the contrast and font checks: colour, size, weight, boxes, own backdrop,
     overlap with drawn objects, and missing glyphs. Text that is not drawn is skipped. */
  function probeData(W, H) {
    const runs = [];
    const blockers = [...document.querySelectorAll('.device, .obj, .motif, .art, .logo')].filter(shown).map((e) => e.getBoundingClientRect());
    document.querySelectorAll('.cap').forEach((cap) => {
      if (!shown(cap)) return;
      const walker = document.createTreeWalker(cap, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        const text = n.textContent.trim();
        if (!text) continue;
        const range = document.createRange();
        range.selectNodeContents(n);
        const raw = [...range.getClientRects()].filter((r) => r.right > 0 && r.left < W && r.bottom > 0 && r.top < H);
        const clipped = raw.some((r) => r.left < -1 || r.top < -1 || r.right > W + 1 || r.bottom > H + 1);
        const rects = raw
          .map((r) => [Math.max(0, r.left), Math.max(0, r.top), Math.min(W, r.right), Math.min(H, r.bottom)])
          .filter(([l, t, r, b]) => r - l >= 2 && b - t >= 2);
        if (!rects.length) continue;
        const el = n.parentElement;
        const cs = getComputedStyle(el);
        let own = null;
        for (let e = el; e && e !== cap.parentElement; e = e.parentElement) {
          const c = getComputedStyle(e).backgroundColor;
          if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') { own = c; break; }
          if (e === cap) break;
        }
        const overlap = rects.some(([l, t, r, b]) => blockers.some((x) => x.left < r && x.right > l && x.top < b && x.bottom > t));
        const family = firstFamily(cs.fontFamily);
        const weight = Number(cs.fontWeight) || 400;
        const italic = cs.fontStyle === 'italic';
        runs.push({ text: text.slice(0, 40), chars: [...new Set(Array.from(text))].join(''), kind: el.closest('h1') ? 'head' : el.closest('.kicker') ? 'kicker' : 'sub',
          bg: cap.dataset.bg || null, color: cs.color, own, overlap, clipped, size: parseFloat(cs.fontSize), weight, italic,
          family, missing: missingGlyphs(text, family, weight, italic), rects });
      }
    });
    return { W, H, runs };
  }

  function probe(W, H) {
    const pre = document.createElement('pre');
    pre.id = 'probe';
    pre.style.display = 'none';
    pre.textContent = JSON.stringify(probeData(W, H));
    document.body.appendChild(pre);
  }

  window.ArtDir = { esc, copy, bg, background, textCSS, caption, device, motif, loadFaces, probe, probeData,
    layouts: { store, feature, canvas: canvasLayouts } };
})();
