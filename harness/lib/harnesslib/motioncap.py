"""Capture lanes for motion pieces (motion-ui references/capture-contract.md).

Visual lane (deterministic): the page is loaded with media/clock.js injected, so its time stands
still until the capture moves it. After boot the lane either
  app-seek       calls the app's window.__motion.seek(ms) (the seek contract), or
  virtual-clock  steps the injected clock to each time,
and takes a screenshot per time and viewport. It proves composition and pose at spec times, the
reduced-motion frame and determinism. It never judges pause, visibility or pacing: a seek holds
the scene whatever the play state, and a frozen clock makes everything look paused.

Behaviour lane (real time): no clock is injected. It presses the app's own pause, stop or hide
control, hides the tab for real (another tab in front), replays scroll and interaction input,
loses the WebGL context, and records the loop in real time (evidence, never byte-identical).
"""

from __future__ import annotations

import io
import json
import math
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from . import cdp
from . import motion as mo
from .fsutil import InputError, OperationalError, UsageError, harness_config, resolve_inside

MEDIA = Path(__file__).resolve().parent.parent / "media"
SWIFTSHADER = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
STILL = 0.5  # mean luma change (0-255, 64-px frames) below which two real-time frames count as still
NEAR = (2, 0.0005)  # two captures are near-identical: max channel delta <= 2 on <= 0.05 % of pixels

GL_PROBE = """(() => { if (window.__motionGL) return; window.__motionGL = [];
  const g = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (type, ...a) {
    const c = g.call(this, type, ...a);
    if (c && /webgl/.test(String(type)) && !window.__motionGL.includes(c)) window.__motionGL.push(c);
    return c; }; })();"""

SETTLE_JS = """(async () => {
  await document.fonts.ready;
  await Promise.all([...document.images].filter((i) => i.loading !== 'lazy' || i.complete)
    .map((i) => i.decode().catch(() => 0)));
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  await new Promise((r) => { const c = new MessageChannel(); c.port1.onmessage = () => r(); c.port2.postMessage(0); });
})()"""

PAGE_FACTS = """((essential, mobile) => {
  const vw = innerWidth, vh = innerHeight;
  const shown = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || r.right <= 0 || r.bottom <= 0 || r.left >= vw || r.top >= vh) return false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
    }
    return true;
  };
  const missing = essential.filter((s) => { const el = document.querySelector(s); return !el || !shown(el); });
  const focusable = [...document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]')]
    .filter((el) => !el.disabled && el.tabIndex >= 0 && !el.closest('[inert], [aria-hidden="true"]'));
  const hiddenFocus = focusable.filter((el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.visibility === 'hidden' || Number(cs.opacity) === 0) return true;
    }
    return false;
  }).map((el) => (el.getAttribute('aria-label') || el.textContent || el.tagName).trim().slice(0, 60));
  const overflow = mobile && document.documentElement.scrollWidth > vw + 1 ? document.documentElement.scrollWidth : 0;
  return JSON.stringify({ missing, hiddenFocus, overflow });
})"""


# ------------------------------------------------------------------ target

@dataclass
class Target:
    url: str
    kind: str  # url | file
    origin: str
    path: str

    def record(self) -> dict:
        return {"kind": self.kind, "origin": self.origin, "path": self.path}


def base_url(given: str | None, root: Path) -> str | None:
    import os
    return given or os.environ.get("MOTION_BASE_URL") or harness_config(root).get("dev_url") or None


def resolve_target(root: Path, piece: dict, base: str | None) -> Target:
    """The URL a capture opens: base URL + capture.path, or capture.page as a file. motion.py never
    starts a server; an unreachable URL is an operational error (exit 2)."""
    cap = piece["capture"]
    path = cap.get("path") or ""
    if base:
        u = urlsplit(base)
        if u.scheme not in ("http", "https") or not u.netloc:
            raise UsageError(f"base URL {base!r}: give http(s)://host[:port]")
        url = base.rstrip("/") + ("/" + path.lstrip("/") if path and not path.startswith("?") else path or "/")
        clean = urlsplit(url)
        return Target(url, "url", f"{u.scheme}://{u.netloc}", clean.path[:300] or "/")
    if cap.get("page"):
        f = resolve_inside(root, cap["page"], "capture.page", must_exist=True)
        query = path if path.startswith("?") else ""
        return Target(f.as_uri() + query, "file", "file://", cap["page"])
    raise UsageError("no base URL: pass --base-url, set $MOTION_BASE_URL or dev_url= in .agents/harness.config "
                     "(motion.py never starts a dev server), or set capture.page to a project HTML file")


def check_reachable(t: Target, timeout: float = 15) -> None:
    if t.kind != "url":
        return
    try:
        with urllib.request.urlopen(urllib.request.Request(t.url, method="GET"), timeout=timeout) as r:  # noqa: S310
            r.read(1)
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            raise OperationalError(f"{t.url} answered {e.code}; is the dev server healthy?") from None
    except (urllib.error.URLError, OSError) as e:
        raise OperationalError(f"{t.url} is not reachable ({getattr(e, 'reason', e)}); start the app yourself "
                               "(motion.py never starts servers) or pass --base-url") from None


# ------------------------------------------------------------------ pixels

def pixel_diff(a: bytes, b: bytes) -> tuple[int, float]:
    """(max channel delta, fraction of pixels that differ) between two PNG screenshots."""
    from PIL import Image, ImageChops
    ia = Image.open(io.BytesIO(a)).convert("RGB")
    ib = Image.open(io.BytesIO(b)).convert("RGB")
    if ia.size != ib.size:
        return 255, 1.0
    d = ImageChops.difference(ia, ib)
    ext = max(hi for _, hi in d.getextrema())
    if ext == 0:
        return 0, 0.0
    gray = d.convert("L")
    hist = gray.histogram()
    changed = sum(hist[1:])
    return ext, changed / (ia.width * ia.height)


def same(a: bytes, b: bytes) -> str:
    """'identical', 'near-identical' (rasterisation noise) or 'different'."""
    ext, frac = pixel_diff(a, b)
    if ext == 0:
        return "identical"
    return "near-identical" if ext <= NEAR[0] and frac <= NEAR[1] else "different"


def small_gray(png: bytes, width: int = 64) -> bytes:
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("L")
    h = max(1, round(im.height * width / im.width))
    return im.resize((width, h), Image.BILINEAR).tobytes()


def gray_stdev(png: bytes) -> float:
    data = small_gray(png)
    m = sum(data) / len(data)
    return math.sqrt(sum((x - m) ** 2 for x in data) / len(data))


# ------------------------------------------------------------------ visual lane

@dataclass
class Visual:
    browser: cdp.Browser
    page: cdp.Page
    viewport: dict
    mode: str  # app-seek | virtual-clock
    boot_steps: int
    now: float = 0.0
    problems: list[str] = field(default_factory=list)

    def close(self) -> None:
        self.browser.close()


def launch(chrome: str, piece: dict, vp: dict, scope: mo.ProcessScope, webgl_probe: bool = False) -> tuple[cdp.Browser, cdp.Page]:
    extra = SWIFTSHADER if piece["capture"].get("webgl") else []
    b = cdp.Browser.launch(chrome, vp["size"], extra_args=extra)
    scope.adopt(b.proc, f"chrome {vp['name']}")
    scope.on_close(b.close)
    page = b.new_page()
    page.set_viewport(vp["size"], vp["dpr"], vp["mobile"])
    if webgl_probe:
        page.add_init_script(GL_PROBE)
    return b, page


def _media(piece: dict, reduced: bool) -> dict:
    feats = {"prefers-reduced-motion": "reduce" if reduced else "no-preference"}
    if piece["capture"].get("colorScheme"):
        feats["prefers-color-scheme"] = piece["capture"]["colorScheme"]
    return feats


def _ready_expr(piece: dict) -> str:
    r = piece["capture"].get("ready") or {}
    parts = ["document.readyState === 'complete'"]
    if r.get("selector"):
        parts.append(f"!!document.querySelector({json.dumps(r['selector'])})")
    if r.get("expression"):
        parts.append(f"!!({r['expression']})")
    return " && ".join(parts)


def open_visual(chrome: str, piece: dict, vp: dict, target: Target, scope: mo.ProcessScope,
                reduced: bool = False, force_virtual: bool = False) -> Visual:
    cap = piece["capture"]
    b, page = launch(chrome, piece, vp, scope)
    page.emulate_media(_media(piece, reduced))
    page.track_network()
    page.block_network(([target.origin] if target.kind == "url" else []) + list(cap.get("allowOrigins") or []))
    cfg = {"stepMs": cap.get("stepMs", 1000 / 60), "settle": 2}
    if cap.get("seed"):
        cfg["seed"] = cap["seed"]
    page.add_init_script(f"window.__motionClockConfig = {json.dumps(cfg)};")
    page.add_init_script((MEDIA / "clock.js").read_text(encoding="utf-8"))
    timeout_s = (cap.get("ready") or {}).get("timeoutMs", 60000) / 1000
    page.navigate(target.url, timeout=max(30.0, timeout_s))
    expr = _ready_expr(piece)
    step = cfg["stepMs"]
    boot = 0
    deadline = time.monotonic() + timeout_s
    time.sleep((cap.get("settleMs") or 0) / 1000)
    while True:
        page.network_idle(0.3, max(1.0, deadline - time.monotonic()))
        if page.evaluate(f"!!({expr})"):
            break
        if time.monotonic() > deadline:
            raise InputError(f"{vp['name']}: the page was not ready within {timeout_s:g} s (capture.ready: {expr})")
        page.evaluate(f"window.__motionClock.step({step})", timeout=60)
        boot += 1
    hook = page.evaluate("!!(window.__motion && typeof window.__motion.seek === 'function')")
    want = cap.get("seekMode", "auto")
    if want == "app-seek" and not hook:
        raise InputError("capture.seekMode is app-seek but the page has no window.__motion.seek (references/capture-contract.md "
                         "says what to add, dev-only), or use seekMode auto / virtual-clock")
    mode = "app-seek" if hook and want != "virtual-clock" and not force_virtual else "virtual-clock"
    v = Visual(b, page, vp, mode, boot)
    if mode == "app-seek":
        page.evaluate("window.__motionClock.release()")
        page.evaluate("Promise.resolve(window.__motion.ready ? window.__motion.ready() : true)", timeout=max(30.0, timeout_s))
        if (page.evaluate("JSON.stringify(window.__motion.version || 1)") or "1") not in ("1",):
            v.problems.append("window.__motion.version is not 1")
    return v


def _scroll_px(piece: dict, ms: float) -> float:
    pm = sorted(piece["input"]["scroll"]["progressMap"], key=lambda x: x[1])
    if ms <= pm[0][1]:
        return pm[0][0]
    for (p0, t0), (p1, t1) in zip(pm, pm[1:]):
        if t0 <= ms <= t1:
            return p0 + (p1 - p0) * ((ms - t0) / (t1 - t0) if t1 > t0 else 0)
    return pm[-1][0]


def _do_input(page: cdp.Page, act: dict) -> None:
    sel = json.dumps(act.get("target") or "body")
    a = act["action"]
    if a in ("click", "hover"):
        r = page.evaluate(f"(() => {{ const el = document.querySelector({sel}); if (!el) return null; el.scrollIntoView({{block: 'nearest'}}); "
                          "const b = el.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; })()")
        if not r:
            raise InputError(f"input target {act.get('target')!r} not found")
        page.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": r[0], "y": r[1]})
        if a == "click":
            for t in ("mousePressed", "mouseReleased"):
                page.send("Input.dispatchMouseEvent", {"type": t, "x": r[0], "y": r[1], "button": "left", "clickCount": 1})
    elif a == "focus":
        page.evaluate(f"document.querySelector({sel})?.focus()")
    elif a == "key":
        key = act.get("value") or "Enter"
        for t in ("keyDown", "keyUp"):
            page.send("Input.dispatchKeyEvent", {"type": t, "key": key})
    elif a == "scroll":
        page.evaluate(f"window.scrollBy(0, {float(act.get('value') or 400)})")


def capture_at(v: Visual, piece: dict, t: float, sequence: list[dict] | None = None) -> tuple[bytes, dict | None]:
    """Screenshot at spec time t (ms after ready). Scroll pieces set the mapped scroll position first;
    interaction pieces replay the input that falls before t."""
    page = v.page
    if piece["loop"]["mode"] == "scroll":
        px = _scroll_px(piece, t)
        sc = piece["input"]["scroll"]
        axis = "top" if sc.get("axis", "y") == "y" else "left"
        cont = json.dumps(sc.get("container") or "")
        page.evaluate(f"(() => {{ const c = {cont} ? document.querySelector({cont}) : null; "
                      f"(c || window).scrollTo({{{axis}: {px}, behavior: 'instant'}}); }})()")
    if v.mode == "app-seek":
        st = None
        for _ in range(2):
            page.evaluate(f"window.__motion.seek({t})", timeout=60)
            page.evaluate(SETTLE_JS, timeout=60)
            st = page.evaluate("window.__motion.state ? JSON.stringify(window.__motion.state()) : null")
            st = json.loads(st) if st else None
            if not st or st.get("ms") is None or abs(float(st["ms"]) - t) < 1:
                break
        else:
            v.problems.append(f"t={t:g} ms: window.__motion.state().ms says {st.get('ms') if st else '?'} after seek({t:g})")
        return page.screenshot(), st
    # virtual clock: replay input in time order, then step to t
    for act in sequence or []:
        if v.now <= act["atMs"] <= t:
            page.evaluate(f"window.__motionClock.step({act['atMs'] - v.now})", timeout=120)
            v.now = act["atMs"]
            _do_input(page, act)
    page.evaluate(f"window.__motionClock.step({max(0.0, t - v.now)})", timeout=300)
    v.now = max(v.now, t)
    st = page.evaluate("window.__motion && window.__motion.state ? JSON.stringify(window.__motion.state()) : null")
    return page.screenshot(), (json.loads(st) if st else None)


def page_facts(page: cdp.Page, piece: dict, vp: dict) -> dict:
    return json.loads(page.evaluate(f"{PAGE_FACTS}({json.dumps(piece['capture'].get('essential') or [])}, "
                                    f"{json.dumps(bool(vp['mobile']))})"))


# ------------------------------------------------------------------ behaviour lane

@dataclass
class Live:
    browser: cdp.Browser
    page: cdp.Page
    viewport: dict


def open_live(chrome: str, piece: dict, vp: dict, target: Target, scope: mo.ProcessScope, reduced: bool = False) -> Live:
    cap = piece["capture"]
    b, page = launch(chrome, piece, vp, scope, webgl_probe=bool(cap.get("webgl")))
    page.emulate_media(_media(piece, reduced))
    page.track_network()
    page.block_network(([target.origin] if target.kind == "url" else []) + list(cap.get("allowOrigins") or []))
    timeout_s = (cap.get("ready") or {}).get("timeoutMs", 60000) / 1000
    page.navigate(target.url, timeout=max(30.0, timeout_s))
    deadline = time.monotonic() + timeout_s
    expr = _ready_expr(piece)
    while not page.evaluate(f"!!({expr})"):
        if time.monotonic() > deadline:
            raise InputError(f"{vp['name']}: the page was not ready within {timeout_s:g} s (capture.ready: {expr})")
        page.pump(0.1)
    page.network_idle(0.3, 15)
    time.sleep((cap.get("settleMs") or 0) / 1000)
    return Live(b, page, vp)


def _state(page: cdp.Page) -> dict | None:
    st = page.evaluate("window.__motion && window.__motion.state ? JSON.stringify(window.__motion.state()) : null")
    return json.loads(st) if st else None


def _moving(page: cdp.Page, span: float = 0.5, tries: int = 4) -> tuple[bool, float]:
    """Does the picture change in real time right now? (mean luma change over span seconds)"""
    best = 0.0
    for _ in range(tries):
        a = small_gray(page.screenshot())
        page.pump(span)
        b = small_gray(page.screenshot())
        best = max(best, mo.mad(a, b))
        if best > STILL:
            return True, best
    return False, best


def check_control(live: Live, piece: dict) -> dict:
    """Press the app's own pause/stop/hide control and watch real time: the picture must stop
    changing (and, for pause, start again on the second press)."""
    ctl = piece["motionControl"]
    page = live.page
    moving, before = _moving(page)
    if not moving:
        return {"result": "REVIEW REQUIRED", "detail": f"no motion seen in real time before pressing the control (change {before:.2f}); "
                                                      "check the control by hand"}
    sel = ctl["selector"]
    if not page.evaluate(f"!!document.querySelector({json.dumps(sel)})"):
        return {"result": "FAIL", "detail": f"motionControl.selector {sel!r} matches nothing"}
    _do_input(page, {"action": "click", "target": sel})
    page.pump(0.4)
    s0 = _state(page)
    a = small_gray(page.screenshot())
    page.pump(1.5)
    b = small_gray(page.screenshot())
    s1 = _state(page)
    change = mo.mad(a, b)
    ms_moved = None
    if s0 and s1 and s0.get("ms") is not None and s1.get("ms") is not None:
        ms_moved = float(s1["ms"]) - float(s0["ms"])
    stopped = change <= STILL and (ms_moved is None or abs(ms_moved) < 50)
    if not stopped:
        why = f"the picture kept changing ({change:.2f})" + (f" and window.__motion.state().ms moved {ms_moved:.0f} ms" if ms_moved else "")
        return {"result": "FAIL", "detail": f"after pressing {sel!r} the motion did not stop: {why}"}
    detail = f"{ctl['kind']} via {sel!r}: no change over 1.5 s ({change:.2f})"
    if ctl["kind"] == "pause":
        _do_input(page, {"action": "click", "target": sel})
        moving2, after = _moving(page)
        if not moving2:
            return {"result": "REVIEW REQUIRED", "detail": detail + f"; pressing it again did not start the motion ({after:.2f})"}
        detail += f"; pressing it again resumed it ({after:.2f})"
    return {"result": "PASS", "detail": detail}


def check_hidden_tab(live: Live, piece: dict) -> dict:
    """Put another tab in front for real (visibilityState hidden), come back, and see whether the
    motion jumped (policy pause) or carried on (policy continue: not judged)."""
    policy = piece["resilience"]["hiddenTab"]
    page, b = live.page, live.browser
    if policy == "continue":
        return {"result": "PASS", "detail": "policy continue: running while hidden is intended (not judged)"}
    s0 = _state(page)
    short_a = small_gray(page.screenshot())
    page.pump(0.2)
    short_b = small_gray(page.screenshot())
    short = mo.mad(short_a, short_b)
    long_a = short_b
    page.pump(2.5)
    long_b = small_gray(page.screenshot())
    long_ = mo.mad(long_a, long_b)
    before = long_b
    s0 = _state(page) or s0
    other = b.new_page()
    other.activate()
    page.pump(0.2)
    vis = page.evaluate("document.visibilityState")
    if vis != "hidden":
        return {"result": "SKIPPED", "detail": f"the browser kept the tab {vis} with another tab in front; check by hand"}
    page.pump(2.5)
    page.activate()
    page.pump(0.05)
    after = small_gray(page.screenshot())
    s1 = _state(page)
    if s0 and s1 and s0.get("ms") is not None and s1.get("ms") is not None:
        jump = float(s1["ms"]) - float(s0["ms"])
        if jump > 800:
            return {"result": "FAIL", "detail": f"window.__motion.state().ms moved {jump:.0f} ms while the tab was hidden 2.5 s (policy pause)"}
        return {"result": "PASS", "detail": f"window.__motion.state().ms moved {jump:.0f} ms over a 2.5 s hidden tab"}
    jump = mo.mad(before, after)
    if long_ <= STILL:
        return {"result": "REVIEW REQUIRED", "detail": "the motion was still during the check, so a jump can't be seen; check by hand"}
    if jump <= max(2 * short, STILL):
        return {"result": "PASS", "detail": f"picture change across the hidden tab {jump:.2f} (0.2 s of motion: {short:.2f}, 2.5 s: {long_:.2f})"}
    return {"result": "REVIEW REQUIRED", "detail": f"the picture changed {jump:.2f} across a 2.5 s hidden tab (0.2 s of motion: "
                                                    f"{short:.2f}, 2.5 s: {long_:.2f}); it may have jumped"}


def check_context_loss(live: Live) -> dict:
    page = live.page
    n = page.evaluate("(window.__motionGL || []).filter((g) => g.getExtension('WEBGL_lose_context')).length")
    if not n:
        return {"result": "SKIPPED", "detail": "no WebGL context on the page"}
    page.evaluate("(window.__motionGL || []).forEach((g) => { const x = g.getExtension('WEBGL_lose_context'); if (x) x.loseContext(); })")
    page.pump(0.8)
    sd = gray_stdev(page.screenshot())
    page.evaluate("(window.__motionGL || []).forEach((g) => { const x = g.getExtension('WEBGL_lose_context'); try { x && x.restoreContext(); } catch (e) {} })")
    if sd < 2:
        return {"result": "REVIEW REQUIRED", "detail": f"the page looks blank after losing the WebGL context (stdev {sd:.1f}); "
                                                      "show the fallback or recover"}
    return {"result": "PASS", "detail": f"{n} context(s) lost; the page still shows a picture (stdev {sd:.1f})"}


def record(live: Live, seconds: float, ff: str, dest: Path, fps: int = 30) -> dict:
    """A real-time recording: screencast frames resampled to fps (each tick shows the newest frame
    at or before it), encoded as an H.264 draft. Evidence of pacing, never frame-exact."""
    from . import ffmpeg as ffm
    page = live.page
    size = live.viewport["size"]
    page.start_screencast(max_size=(min(size[0], 1280), min(size[1], 1280)))
    page.pump(seconds)
    frames = page.stop_screencast()
    if len(frames) < 2:
        raise OperationalError(f"the screencast produced {len(frames)} frame(s) in {seconds:g} s")
    t0 = frames[0][0]
    stamps = [f[0] - t0 for f in frames]
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    n = max(1, int(stamps[-1] * fps))
    j = 0
    with ffm.Encoder(ff, "h264-draft", dest, fps=fps) as enc:
        for k in range(n):
            t = k / fps
            while j + 1 < len(frames) and stamps[j + 1] <= t:
                j += 1
            enc.write(frames[j][1])
    return {"frames": len(frames), "seconds": round(stamps[-1], 2), "effectiveFps": round(len(frames) / max(stamps[-1], 1e-6), 1),
            "longestGapMs": round(max(gaps) * 1000), "encodedFrames": n, "fps": fps}
