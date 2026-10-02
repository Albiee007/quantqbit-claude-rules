/* Screens for the store mockups. Rebuild each one from the REAL screen component: copy
   its labels word for word, its layout order and its theme tokens, then fill it with
   DEMO data. Screens render at 900 logical px wide (a 1080 px capture viewed at 83%), so
   pixel sizes can be read straight off the reference captures.

   Icons: I('ion-name|material_name', size, color). The half that matches frames.json
   "icons" is used. Rename this file to screens.js in your kit folder. */

const avatar = (initials, size = 72, bg = 'var(--brandTint)', fg = 'var(--brand)') =>
  `<div class="avatar" style="width:${size}px;height:${size}px;background:${bg};color:${fg};font-size:${Math.round(size * 0.36)}px">${initials}</div>`;

function statusBar(p) {
  if (p === 'ios') {
    return `<div class="sb"><span>9:41</span><div class="island"></div>
      <div class="icons">${I('cellular|signal_cellular_alt', 34)}${I('wifi|wifi', 34)}${I('battery-full|battery_full', 44)}</div></div>`;
  }
  return `<div class="sb"><span>9:41</span><div class="icons">${I('wifi|wifi', 30)}${I('cellular|signal_cellular_alt', 28)}${I('battery-full|battery_full', 38)}</div></div>`;
}

/* Bottom tab bar. raised=true draws the active tab as a lifted circle with the bar edge
   rising to meet it; set it only if the real app does this. */
function tabBar(active, tabs, raised = true) {
  const w = 900 / tabs.length, cx = w / 2 + active * w, a = cx - 140, b = cx + 140, top = 45;
  const edge = raised
    ? `M0 ${top} H${a} C${a + 45} ${top} ${a + 55} ${top - 22} ${cx} ${top - 22} C${b - 55} ${top - 22} ${b - 45} ${top} ${b} ${top} H900`
    : `M0 ${top} H900`;
  return `<div class="tabbar ${raised ? 'raised' : ''}">
    <svg class="bgshape" viewBox="0 0 900 300" preserveAspectRatio="none">
      <path d="${edge} V300 H0 Z" fill="#fff"/><path d="${edge}" fill="none" stroke="var(--hairline)" stroke-width="2.5"/></svg>
    ${raised ? `<div class="bubble" style="left:${cx - 75}px"><div>${I(tabs[active][2], 54)}</div></div>` : ''}
    <div class="tabs">${tabs.map(([label, icon], i) => `<div class="tab ${i === active ? 'on' : ''}">${I(icon, 46)}${label}</div>`).join('')}</div>
  </div>`;
}

const TABS = [['HOME', 'home-outline|home', 'home|home'], ['ACTIVITY', 'list-outline|list', 'list|list'], ['SETTINGS', 'settings-outline|settings', 'settings|settings']];

const appBar = (title, sub) => `<div class="appbar">${I('arrow-back|arrow_back', 48)}
  <div class="grow"><div class="t">${title}</div>${sub ? `<div class="s">${sub}</div>` : ''}</div>
  ${I('notifications-outline|notifications', 46)}${I('ellipsis-vertical|more_vert', 44)}</div>`;

const listRow = (r) => `<div class="card lrow"><div class="tile">${I(r.icon, 42)}</div><div class="body">
  <div class="l1"><span style="overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${r.title}</span><span class="amt num">${r.amount}</span></div>
  <div class="l2"><span>${r.meta}</span><span class="num">${r.secondary || ''}</span></div></div></div>`;

/* ---------- home (replace with the app's real home screen) ---------- */
function home(p) {
  const d = DEMO.home;
  return `<div class="pad" style="margin-top:18px">
    <div class="between">
      <div><div style="font-size:34px;color:var(--inkMuted)">Hello,</div><div style="font-size:52px;font-weight:700">${DEMO.me.name}</div></div>
      <div class="row" style="gap:34px">${I('notifications-outline|notifications', 50)}${avatar(DEMO.me.initials, 96)}</div>
    </div>
    <div class="grid2" style="margin-top:40px">
      ${d.stats.map((s) => `<div class="card stat"><span class="pill" style="background:var(--brandTint);color:var(--brand)">${s.badge}</span>
        <div class="ic icircle" style="background:${s.tint};color:${s.color}">${I(s.icon, 32)}</div>
        <div class="lbl">${s.label}</div><div class="val num" style="color:${s.color}">${s.value}</div><div class="note">${s.note}</div></div>`).join('')}
    </div>
    <div class="sectionTitle" style="margin-top:56px">${I('time-outline|schedule', 42, 'var(--brand)')}Recent</div>
    <div style="display:flex;flex-direction:column;gap:20px;margin-top:28px">${d.recent.map(listRow).join('')}</div>
  </div>
  <div class="fab" style="bottom:330px">${I('add|add', 62)}</div>
  ${tabBar(0, TABS)}`;
}

/* ---------- a detail list grouped by day ---------- */
function activity(p) {
  const a = DEMO.activity;
  return `${appBar(a.title, a.sub)}
  <div class="pad" style="padding-top:20px">
    ${a.days.map((day) => `<div class="dateHead"><b>${day.date}</b><span>${day.rows.length} items</span></div>
      <div style="display:flex;flex-direction:column;gap:20px">${day.rows.map(listRow).join('')}</div>`).join('')}
  </div>
  ${tabBar(1, TABS)}`;
}

const SCREENS = { home, activity };
