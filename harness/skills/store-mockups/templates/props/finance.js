/* Optional prop pack "finance" for format-2 continuous kits (frames.json "props": ["finance"]).
   The same object names and props as 1.6 (coin, chip, receipt, calendar), coloured from the
   project's roles instead of fixed hues, so a finance app can keep them without the 1.6 look.
   1.6 kits load the original versions through templates/legacy-1.6/objects.js. */

Object.assign(OBJECTS, {
  /* Coin. Props: glyph, metal ("brand" | "silver" | "gold"), tilt (0-70 deg of 3D squash). */
  coin(o, u) {
    const metals = { brand: [u.R.canvas, u.R.accent, u.R.ink], silver: ['#ffffff', '#d7dbe3', '#8f97a6'], gold: ['#fff4c2', '#f3c64d', '#b07d12'] };
    const [a, b, c] = metals[o.metal || 'brand'] || metals.brand;
    const squash = Math.cos(((o.tilt ?? 0) * Math.PI) / 180);
    return `<div style="width:10em;height:10em;border-radius:50%;transform:scaleX(${squash});${shadow(o)}
        background:radial-gradient(circle at 32% 28%, ${a} 0 18%, ${b} 45%, ${c} 100%);
        box-shadow:inset 0 0 0 0.7em ${b}, inset 0 0 0 0.95em ${c};display:grid;place-items:center;color:${c}">
        <span style="font-family:${fontOf(u, 'display')};font-size:5.2em;line-height:1">${esc(o.glyph ?? '¤')}</span></div>`;
  },

  /* Flat chip with a glyph. Props: glyph, color (role or CSS), bg (role or CSS). */
  chip(o, u) {
    return `<div style="width:10em;height:10em;border-radius:50%;background:${role(u, o.bg, u.R.surface || u.R.canvas)};display:grid;place-items:center;
      color:${role(u, o.color, u.R.accent)};${shadow(o)}"><span style="font-family:${fontOf(u, 'display')};font-size:5em;line-height:1">${esc(o.glyph ?? '¤')}</span></div>`;
  },

  /* Paper receipt with a zig-zag bottom. Props: title, sub, lines [[label, value]], total [label, value], footer. */
  receipt(o, u) {
    const teeth = 14, zig = Array.from({ length: teeth * 2 + 1 }, (_, i) => `${(i / (teeth * 2)) * 100}% ${i % 2 ? 100 : 96.5}%`).join(',');
    const rows = (o.lines || []).map(([l, v]) => `<div style="display:flex;justify-content:space-between"><span>${esc(l)}</span><span>${esc(v)}</span></div>`).join('');
    return `<div style="${shadow(o)}"><div style="width:10em;background:${u.R.surface || u.R.canvas};color:${u.R.ink};padding:0.8em 0.8em 1.4em;
        clip-path:polygon(0 0,100% 0,${zig},0 96.5%)"><div style="font-size:0.52em;line-height:1.55;font-family:ui-monospace, monospace">
      ${o.title ? `<div style="font-family:${fontOf(u, 'display')};font-size:1.5em;line-height:1.2;text-align:center">${esc(o.title)}</div>` : ''}
      ${o.sub ? `<div style="text-align:center;color:${u.R.inkMuted};margin-bottom:.6em">${esc(o.sub)}</div>` : ''}
      <div style="border-top:1px dashed ${u.R.inkMuted};margin:.5em 0;padding-top:.5em">${rows}</div>
      ${o.total ? `<div style="display:flex;justify-content:space-between;font-weight:700;border-top:1px dashed ${u.R.inkMuted};padding-top:.5em"><span>${esc(o.total[0])}</span><span>${esc(o.total[1])}</span></div>` : ''}
      ${o.footer ? `<div style="text-align:center;color:${u.R.inkMuted};margin-top:.8em">${esc(o.footer)}</div>` : ''}
    </div></div></div>`;
  },

  /* Calendar tile. Props: day, weekday, month (required: no default month), color (role or CSS). */
  calendar(o, u) {
    return `<div style="width:10em;border-radius:1.4em;background:${u.R.surface || u.R.canvas};overflow:hidden;${shadow(o)};text-align:center;font-family:${fontOf(u, 'text')}">
      <div style="background:${role(u, o.color, u.R.accent)};color:${u.R.onAccent || u.R.canvas};font-size:1.4em;line-height:2.2;letter-spacing:.08em">${esc(o.month)}</div>
      <div style="font-family:${fontOf(u, 'display')};font-size:5em;line-height:1.1;color:${u.R.ink}">${esc(o.day)}</div>
      <div style="font-size:1.2em;line-height:2;color:${u.R.inkMuted}">${esc(o.weekday)}</div></div>`;
  },
});
