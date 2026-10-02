/* Decorative objects for the CONTINUOUS store-screenshot style (frames.json "style": "continuous"),
   format 2. Objects sit on one strip that spans every frame, so anything crossing a frame edge
   continues in the next frame. Colours and type come from the approved concept: u.R holds the
   direction's colour roles (canvas, ink, inkMuted, accent, surface, ...) and u.T its font roles
   (display, text, ...), so an object looks like the project, not like the harness.

   Units (see references/continuous-panorama.md):
     x    frame units along the strip: 0 = left edge of frame 1, 1.5 = middle of frame 2
     y    fraction of the canvas height (0 top, 1 bottom)
     w, h fraction of the canvas width (h defaults per type)
   Common props: rotate (deg), opacity, z ("back" | "front"), shadow (bool), colors (role names or
   CSS colours), allowCross (text objects only; see the guardrails).

   Every renderer is (o, u) => HTML, where u has X(), Y(), S(), W, H, R (colour roles), T (font
   roles), I() (icons), device(screenName, widthPx), esc() and copy() (escaped text, <em> kept).
   Inside an anchored object, 1em = w/10 of its width, so renderers size everything in em.
   Text is data: renderers escape it. The html type is the one exception, for kit-authored markup.

   Optional prop packs (frames.json "props"): "finance" adds coin, chip, receipt and calendar.
   Add app-specific types in the kit's custom-objects.js:
     OBJECTS.plane = (o, u) => `<div style="font-size:6em;color:${u.R.accent}">✈</div>`;              */

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
/* A colour prop: a role name ("accent") or a CSS colour. */
const role = (u, v, fallback) => (v && u.R[v]) || v || fallback;
const fontOf = (u, r) => (u.T[r] || u.T.text || u.T.display).stack;
const shadow = (o) => (o.shadow === false ? '' : 'filter:drop-shadow(0 1.2em 1.6em rgba(0,0,0,.22));');

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

let uid = 0;
const OBJECTS = {
  /* A band across the strip. Not anchored: points are [x, y] in strip units.
     Props: points, w (thickness), colors (roles or CSS), texture ("none" | "dots" | "lines"), cap ("round" | "butt"). */
  ribbon(o, u) {
    uid += 1;
    const id = 'rb' + uid;
    const pts = (o.points || []).map(([x, y]) => [u.X(x), u.Y(y)]);
    const d = smoothPath(pts);
    const c = (Array.isArray(o.colors) ? o.colors : ['accent', 'ink']).map((v) => role(u, v, v));
    const sw = u.S(o.w ?? 0.16);
    const tex = o.texture === 'dots'
      ? `<pattern id="${id}p" width="${sw / 9}" height="${sw / 9}" patternUnits="userSpaceOnUse"><circle cx="${sw / 18}" cy="${sw / 18}" r="${sw / 60}" fill="${u.R.canvas}" fill-opacity=".35"/></pattern>`
      : o.texture === 'lines'
        ? `<pattern id="${id}p" width="${sw / 7}" height="${sw / 7}" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="${sw / 28}" height="${sw / 7}" fill="${u.R.canvas}" fill-opacity=".3"/></pattern>`
        : '';
    return `<svg style="position:absolute;left:0;top:0;overflow:visible;opacity:${o.opacity ?? 1}" width="${u.stripW}" height="${u.H}">
      <defs><linearGradient id="${id}" x1="0" x2="1" y1="0" y2="0">${c.map((col, i) => `<stop offset="${i / Math.max(1, c.length - 1)}" stop-color="${esc(col)}"/>`).join('')}</linearGradient>${tex}</defs>
      <path d="${d}" fill="none" stroke="url(#${id})" stroke-width="${sw}" stroke-linecap="${o.cap === 'butt' ? 'butt' : 'round'}"/>
      ${tex ? `<path d="${d}" fill="none" stroke="url(#${id}p)" stroke-width="${sw * 0.98}" stroke-linecap="${o.cap === 'butt' ? 'butt' : 'round'}"/>` : ''}
    </svg>`;
  },

  /* A plain shape. Props: shape ("circle" | "blob" | "arc" | "pill"), color (role or CSS), outline (bool). */
  shape(o, u) {
    const col = role(u, o.color, u.R.accent);
    const fill = o.outline ? 'none' : esc(col);
    const stroke = o.outline ? `stroke="${esc(col)}" stroke-width="5"` : '';
    const paths = {
      circle: `<circle cx="50" cy="50" r="47" fill="${fill}" ${stroke}/>`,
      blob: `<path d="M50 4C74 4 96 22 96 48S78 96 50 96 4 78 6 50 26 4 50 4Z" fill="${fill}" ${stroke}/>`,
      arc: `<path d="M6 94A88 88 0 0 1 94 6" fill="none" stroke="${esc(col)}" stroke-width="10" stroke-linecap="round"/>`,
      pill: `<rect x="3" y="30" width="94" height="40" rx="20" fill="${fill}" ${stroke}/>`,
    };
    return `<svg viewBox="0 0 100 100" style="display:block;width:10em;height:10em">${paths[o.shape] || paths.circle}</svg>`;
  },

  /* Notification toast. Props: title, body, icon (I() name). Text object: may not cross a seam. */
  toast(o, u) {
    return `<div style="width:10em;display:flex;gap:.6em;align-items:center;background:${u.R.surface || u.R.canvas};border-radius:1.1em;padding:.7em .8em;${shadow(o)};font-family:${fontOf(u, 'text')}">
      <div style="flex:none;width:2.4em;height:2.4em;border-radius:.7em;background:${u.R.accent};color:${u.R.onAccent || u.R.canvas};display:grid;place-items:center">${u.I(o.icon || 'notifications|notifications', u.S(o.w ?? 0.5) * 0.12)}</div>
      <div style="min-width:0"><div style="font-size:.62em;line-height:1.3;font-weight:700;color:${u.R.ink}">${esc(o.title)}</div>
      <div style="font-size:.55em;line-height:1.35;color:${u.R.inkMuted}">${esc(o.body)}</div></div></div>`;
  },

  /* Floating stat card. Props: label, value, sub, tone (a role name, default "accent"). Text object. */
  card(o, u) {
    return `<div style="width:10em;background:${u.R.surface || u.R.canvas};border-radius:1.2em;padding:.9em 1em;${shadow(o)};font-family:${fontOf(u, 'text')}">
      <div style="font-size:.75em;line-height:1.3;color:${u.R.inkMuted}">${esc(o.label)}</div>
      <div style="font-size:1.7em;line-height:1.1;font-family:${fontOf(u, 'display')};color:${role(u, o.tone, u.R.accent)};margin-top:.2em">${esc(o.value)}</div>
      ${o.sub ? `<div style="font-size:.7em;line-height:1.3;color:${u.R.inkMuted};margin-top:.3em">${esc(o.sub)}</div>` : ''}</div>`;
  },

  /* Extra (secondary) phone showing any screen. Props: screen, w, rotate. May straddle a seam. */
  phone(o, u) {
    return u.device(o.screen, u.S(o.w ?? 0.7));
  },

  /* Brand mark: wordmark text and/or a logo image. Props: text, src, color (role or CSS), size. Text object. */
  brand(o, u) {
    return `<div style="width:10em;text-align:center">
      ${o.src ? `<img src="${esc(o.src)}" alt="" style="width:${o.imgW ?? 6}em;height:auto;display:block;margin:0 auto .5em">` : ''}
      ${o.text ? `<div style="font-family:${fontOf(u, 'display')};font-size:${o.size ?? 2.4}em;line-height:1;color:${role(u, o.color, u.R.ink)}">${esc(o.text)}</div>` : ''}</div>`;
  },

  /* Project photo. Props: src (copied into the build by render_frames.py), h, mask ("none" | "rounded" | "circle"),
     fit ("cover" | "contain"), position (CSS object-position). license is REQUIRED (validated). */
  image(o) {
    const r = { rounded: '1.6em', circle: '50%' }[o.mask] || '0';
    const h = o.h ? `${(o.h / (o.w ?? 1)) * 10}em` : 'auto';
    return `<img src="${esc(o.src)}" alt="" style="display:block;width:10em;height:${h};object-fit:${o.fit === 'contain' ? 'contain' : 'cover'};object-position:${esc(o.position || 'center')};border-radius:${r}">`;
  },

  /* Free text. Props: text (escaped; <em> marks the accent), size (em), font (a font role), color (role or CSS), align. Text object. */
  text(o, u) {
    return `<div style="width:10em;text-align:${o.align === 'start' ? 'start' : 'center'}"><div style="font-family:${fontOf(u, o.font || 'display')};font-size:${o.size ?? 1.2}em;line-height:1.1;color:${role(u, o.color, u.R.ink)}">${u.copy(o.text).replace(/<em>/g, `<em style="font-style:inherit;color:${u.R.accent}">`)}</div></div>`;
  },

  /* Raw markup for anything else, written by the kit's owner. Props: html. */
  html(o) {
    return `<div style="width:10em">${o.html || ''}</div>`;
  },
};

/* Types that carry readable text: the renderer validation keeps them inside one frame. */
const TEXT_OBJECTS = ['toast', 'card', 'brand', 'text'];
