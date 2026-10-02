/* A kit-defined object type, as 1.6 kits may have (uses the 1.6 helpers u.B and u.esc). */
OBJECTS.stamp = (o, u) => `<div style="width:10em;height:10em;border-radius:50%;border:.8em solid ${u.B.accent};display:grid;place-items:center;
  color:${u.B.accent};font:800 3.6em/1 Inter, sans-serif">${u.esc(o.label || 'OK')}</div>`;
