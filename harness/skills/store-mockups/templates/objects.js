/* Decorative objects for the CONTINUOUS store-screenshot style (frames.json "layout": "continuous").
   Objects are placed on one strip that spans every frame, so anything crossing a frame edge
   continues in the next frame.

   Units (see references/continuous-panorama.md):
     x    frame units along the strip: 0 = left edge of frame 1, 1.5 = middle of frame 2
     y    fraction of the canvas height (0 top, 1 bottom)
     w, h fraction of the canvas width (h defaults per type)
   Common props: rotate (deg), opacity, z ("back" | "front"), shadow (bool), style (extra CSS),
   colors (array or "brand"), allowCross (text objects only; see the guardrails).

   Every renderer is (o, u) => HTML, where u has X(), Y(), S(), W, H, B (brand), I() (icons),
   device(screenName, widthPx) and esc(). Inside an anchored object, 1em = w/10 of its width,
   so renderers size everything in em and scale with the object.

   Add app-specific types in the kit's custom-objects.js:
     OBJECTS.plane = (o, u) => `<div style="font-size:6em">✈</div>`;                           */

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const palette = (o, B, fallback) => (Array.isArray(o.colors) ? o.colors : fallback || [B.bg2, B.bg3]);
const shadow = (o) => (o.shadow === false ? '' : 'filter:drop-shadow(0 1.2em 1.6em rgba(10,8,60,.28));');

/* Smooth path through points (Catmull-Rom converted to cubic Bézier). */
function smoothPath(pts) {
  if (pts.length < 2) return '';
  let d = `M${pts[0][0]} ${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0]} ${c1[1]} ${c2[0]} ${c2[1]} ${p2[0]} ${p2[1]}`;
  }
  return d;
}

const OBJECTS = {
  /* Hero ribbon across the strip. Not anchored: points are [x, y] in strip units.
     Props: points, w (thickness), colors, texture ("dots" | "none"), cap ("round" | "butt"). */
  ribbon(o, u) {
    const id = 'rb' + Math.random().toString(36).slice(2, 8);
    const pts = (o.points || []).map(([x, y]) => [u.X(x), u.Y(y)]);
    const d = smoothPath(pts);
    const c = palette(o, u.B, [u.B.ribbon1 || u.B.bg3, u.B.ribbon2 || u.B.bg2]);
    const sw = u.S(o.w ?? 0.16);
    const tex = o.texture === 'none' ? '' : `
      <pattern id="${id}p" width="${sw / 9}" height="${sw / 9}" patternUnits="userSpaceOnUse">
        <circle cx="${sw / 18}" cy="${sw / 18}" r="${sw / 60}" fill="#fff" fill-opacity=".35"/></pattern>`;
    return `<svg style="position:absolute;left:0;top:0;overflow:visible;opacity:${o.opacity ?? 1}" width="${u.stripW}" height="${u.H}">
      <defs><linearGradient id="${id}" x1="0" x2="1" y1="0" y2="0">${c.map((col, i) => `<stop offset="${i / Math.max(1, c.length - 1)}" stop-color="${col}"/>`).join('')}</linearGradient>${tex}</defs>
      <path d="${d}" fill="none" stroke="url(#${id})" stroke-width="${sw}" stroke-linecap="${o.cap || 'round'}"/>
      ${tex ? `<path d="${d}" fill="none" stroke="url(#${id}p)" stroke-width="${sw * 0.98}" stroke-linecap="${o.cap || 'round'}"/>` : ''}
    </svg>`;
  },

  /* Metallic coin. Props: glyph, metal ("silver" | "gold" | "brand"), tilt (0-70 deg of 3D squash). */
  coin(o, u) {
    const metals = { silver: ['#ffffff', '#d7dbe3', '#8f97a6'], gold: ['#fff4c2', '#f3c64d', '#b07d12'], brand: ['#ffffff', u.B.bg3, u.B.bg1] };
    const [a, b, c] = metals[o.metal || 'silver'] || metals.silver;
    const squash = Math.cos(((o.tilt ?? 0) * Math.PI) / 180);
    return `<div style="width:10em;height:10em;border-radius:50%;transform:scaleX(${squash});${shadow(o)}
        background:radial-gradient(circle at 32% 28%, ${a} 0 18%, ${b} 45%, ${c} 100%);
        box-shadow:inset 0 0 0 0.7em ${b}, inset 0 0 0 0.95em ${c}, inset 0 -0.6em 1.2em rgba(0,0,0,.25);
        display:grid;place-items:center;color:${c}"><span style="font:800 5.2em/1 ${u.B.headFont || 'Inter'}, sans-serif;
        text-shadow:0 0.03em 0 #fff, 0 -0.03em 0 rgba(0,0,0,.25)">${esc(o.glyph ?? '$')}</span></div>`;
  },

  /* Flat currency chip (white disc with a brand glyph). Props: glyph, color, bg. */
  chip(o, u) {
    return `<div style="width:10em;height:10em;border-radius:50%;background:${o.bg || '#fff'};display:grid;place-items:center;
      color:${o.color || u.B.bg2};${shadow(o)}"><span style="font:800 5em/1 ${u.B.headFont || 'Inter'}, sans-serif">${esc(o.glyph ?? '$')}</span></div>`;
  },

  /* Paper receipt with a zig-zag bottom. Props: title, sub, lines [[label, value]], total [label, value], footer. */
  receipt(o) {
    const teeth = 14, zig = Array.from({ length: teeth * 2 + 1 }, (_, i) => `${(i / (teeth * 2)) * 100}% ${i % 2 ? 100 : 96.5}%`).join(',');
    const rows = (o.lines || []).map(([l, v]) => `<div style="display:flex;justify-content:space-between"><span>${esc(l)}</span><span>${esc(v)}</span></div>`).join('');
    return `<div style="${shadow(o)}"><div style="width:10em;background:#fff;color:#1f2430;padding:0.8em 0.8em 1.4em;
        clip-path:polygon(0 0,100% 0,${zig},0 96.5%)"><div style="font:500 0.52em/1.55 'Courier New', monospace">
      ${o.title ? `<div style="font:800 1.5em/1.2 Inter, sans-serif;text-align:center;letter-spacing:.04em">${esc(o.title)}</div>` : ''}
      ${o.sub ? `<div style="text-align:center;opacity:.7;margin-bottom:.6em">${esc(o.sub)}</div>` : ''}
      <div style="border-top:1px dashed #9aa0ab;margin:.5em 0;padding-top:.5em">${rows}</div>
      ${o.total ? `<div style="display:flex;justify-content:space-between;font-weight:800;border-top:1px dashed #9aa0ab;padding-top:.5em"><span>${esc(o.total[0])}</span><span>${esc(o.total[1])}</span></div>` : ''}
      ${o.footer ? `<div style="text-align:center;opacity:.7;margin-top:.8em">${esc(o.footer)}</div>` : ''}
    </div></div></div>`;
  },

  /* Tear-off calendar tile. Props: day, weekday, month, color. */
  calendar(o, u) {
    return `<div style="width:10em;border-radius:1.4em;background:#fff;overflow:hidden;${shadow(o)};text-align:center;font-family:Inter, sans-serif">
      <div style="background:${o.color || '#ef4444'};color:#fff;font:700 1.4em/2.2 Inter;letter-spacing:.08em">${esc(o.month || 'SEPT')}</div>
      <div style="font:800 5em/1.1 Inter;color:#1f2430">${esc(o.day ?? '16')}</div>
      <div style="font:500 1.2em/2 Inter;color:#6b7280">${esc(o.weekday || 'Wednesday')}</div></div>`;
  },

  /* Notification toast. Props: title, body, icon (I() name), iconBg. Text object: may not cross a seam. */
  toast(o, u) {
    return `<div style="width:10em;display:flex;gap:.6em;align-items:center;background:#fff;border-radius:1.1em;padding:.7em .8em;${shadow(o)};font-family:Inter, sans-serif">
      <div style="flex:none;width:2.4em;height:2.4em;border-radius:.7em;background:${o.iconBg || u.B.bg2};color:#fff;display:grid;place-items:center">${u.I(o.icon || 'flash|bolt', u.S(o.w ?? 0.5) * 0.12, '#fff')}</div>
      <div style="min-width:0"><div style="font:700 .62em/1.3 Inter;color:#131b2e">${esc(o.title || '')}</div>
      <div style="font:500 .55em/1.35 Inter;color:#464555">${esc(o.body || '')}</div></div></div>`;
  },

  /* Floating stat card. Props: label, value, sub, tone ("positive" | "negative" | "brand"), avatars ["MC","LE"]. Text object. */
  card(o, u) {
    const tones = { positive: '#16a34a', negative: '#dc2626', brand: u.B.bg2 };
    return `<div style="width:10em;background:#fff;border-radius:1.2em;padding:.9em 1em;${shadow(o)};font-family:Inter, sans-serif">
      <div style="font:600 .75em/1.3 Inter;color:#464555">${esc(o.label || '')}</div>
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:.3em">
        <span style="font:800 1.7em/1.1 Inter;color:${tones[o.tone] || tones.brand}">${esc(o.value || '')}</span>
        <span style="display:flex">${(o.avatars || []).map((a, i) => `<span style="width:1.9em;height:1.9em;border-radius:50%;border:.15em solid #fff;margin-left:${i ? -0.6 : 0}em;background:#e2dfff;color:${u.B.bg2};display:grid;place-items:center"><span style="font:700 .7em/1 Inter">${esc(a)}</span></span>`).join('')}</span></div>
      ${o.sub ? `<div style="font:500 .7em/1.3 Inter;color:#777587;margin-top:.3em">${esc(o.sub)}</div>` : ''}</div>`;
  },

  /* Extra (secondary) phone showing any screen. Props: screen, w, rotate. May straddle a seam. */
  phone(o, u) {
    return u.device(o.screen, u.S(o.w ?? 0.7));
  },

  /* Brand mark: wordmark text and/or a logo image. Props: text, src, color, gradient [c1, c2], glow. Text object. */
  brand(o, u) {
    const grad = o.gradient ? `background:linear-gradient(135deg, ${o.gradient.join(',')});-webkit-background-clip:text;color:transparent;` : `color:${o.color || '#fff'};`;
    return `<div style="width:10em;text-align:center;${o.glow ? `filter:drop-shadow(0 0 1.4em ${o.glow});` : ''}">
      ${o.src ? `<img src="${esc(o.src)}" style="width:${o.imgW ?? 6}em;height:auto;display:block;margin:0 auto .5em">` : ''}
      ${o.text ? `<div style="font:800 ${o.size ?? 2.4}em/1 ${u.B.headFont || 'Inter'}, sans-serif;letter-spacing:-.02em;${grad}">${esc(o.text)}</div>` : ''}</div>`;
  },

  /* Project photo. Props: src (copied into assets/ by render_frames.py), h, mask ("none" | "rounded" | "circle"),
     fit ("cover" | "contain"), position (CSS object-position). license is REQUIRED (validated). */
  image(o, u) {
    const r = { rounded: '1.6em', circle: '50%' }[o.mask] || '0';
    const h = o.h ? `${(o.h / (o.w ?? 1)) * 10}em` : 'auto';
    return `<img src="${esc(o.src)}" alt="" style="display:block;width:10em;height:${h};object-fit:${o.fit || 'cover'};object-position:${o.position || 'center'};border-radius:${r}">`;
  },

  /* Free text. Props: text (HTML allowed), size (em of the object width/10), weight, color, align. Text object. */
  text(o) {
    return `<div style="width:10em;text-align:${o.align || 'center'}"><div style="font:${o.weight || 800} ${o.size ?? 1.2}em/1.1 ${o.font || 'Inter'}, sans-serif;color:${o.color || '#fff'}">${o.text || ''}</div></div>`;
  },

  /* Raw markup for anything else. Props: html. */
  html(o) {
    return `<div style="width:10em">${o.html || ''}</div>`;
  },
};

/* Types that carry readable text: the renderer validation keeps them inside one frame. */
const TEXT_OBJECTS = ['toast', 'card', 'brand', 'text'];
