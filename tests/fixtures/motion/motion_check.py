"""motion-ui capture lanes in a real browser (used by tests/motion-ui.test.sh).

On tests/fixtures/motion/hero.html (a rAF loop with clamped deltas, a CSS transition started from
setTimeout, @keyframes, a Web Animation, setInterval and Date text):
- the virtual clock and the app seek hook each give identical pixels in two fresh browsers;
- the virtual clock holds performance.now and Date still between steps and releases to real time;
- the seek hook's state() names the spec's scene;
- reduced motion is static; a remote request is blocked and reported;
- the behaviour lane passes the real pause button and fails one that only changes its label;
- the hidden-tab check sees a real hidden tab.
Prints one line per check; exit 1 when any fails.

    python tests/fixtures/motion/motion_check.py [--chrome PATH]
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "harness" / "lib"))
sys.dont_write_bytecode = True
from harnesslib import browser  # noqa: E402
from harnesslib import motion as mo  # noqa: E402
from harnesslib import motioncap as mc  # noqa: E402

failed = 0
TIMES = [0.0, 250.0, 1000.0, 1300.0, 2400.0]


def check(ok: bool, what: str) -> None:
    global failed
    print(("ok    " if ok else "FAIL  ") + what)
    failed += not ok


def spec(query: str = "") -> dict:
    return {
        "schemaVersion": 1, "id": "hero", "platform": "web",
        "fidelity": {"targets": ["motion"], "medium": "css", "claim": "code-only"},
        "viewports": ["desktop"], "customViewports": {"small": {"size": "640x400", "like": "desktop"}},
        "loop": {"mode": "time-loop", "lengthMs": 2400, "repeat": "infinite"},
        "scenes": [{"id": "s1", "durationMs": 1200}, {"id": "s2", "durationMs": 1200}],
        "rows": [{"startMs": 0, "endMs": 2400, "track": "camera", "action": "push", "confidence": "measured"}],
        "reducedMotion": {"strategy": "static-complete", "staticAt": {"scene": "s1", "ms": 900}},
        "motionControl": {"kind": "pause", "selector": "#pause"},
        "resilience": {"hiddenTab": "pause"},
        "capture": {"driver": "web", "page": "hero.html", "path": query, "ready": {"selector": "#hero", "timeoutMs": 20000},
                    "essential": ["h1"]},
    }


def shots(chrome: str, piece: dict, scope: mo.ProcessScope, force_virtual: bool = False, reduced: bool = False):
    target = mc.resolve_target(HERE, piece, None)
    vp = mo.viewport_spec(piece, "small")
    v = mc.open_visual(chrome, piece, vp, target, scope, reduced=reduced, force_virtual=force_virtual)
    out, states = {}, {}
    for t in TIMES:
        png, st = mc.capture_at(v, piece, t)
        out[t], states[t] = png, st
    extra = {"mode": v.mode, "blocked": v.page.blocked,
             "frozen": v.page.evaluate("(() => { const a = performance.now(), b = Date.now(); "
                                       "for (let i = 0; i < 1e6; i++); return [a, b, performance.now(), Date.now()]; })()")}
    v.close()
    return out, states, extra


def repeat(a: dict, b: dict, what: str) -> tuple[bool, str]:
    """Two fresh browsers agree at every time: identical, or near-identical (rasterisation noise,
    which the capture contract counts as a pass). The detail names each time's verdict."""
    verdicts = {t: mc.same(a[t], b[t]) for t in TIMES}
    diffs = {t: mc.pixel_diff(a[t], b[t]) for t in TIMES if verdicts[t] != "identical"}
    ok = all(v != "different" for v in verdicts.values())
    return ok, f"{what}: the same pixels in two fresh browsers ({verdicts}; differences {diffs})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome")
    a = ap.parse_args()
    chrome = browser.find_chrome(a.chrome)
    with mo.ProcessScope(600) as scope:
        # virtual clock (no hook), twice in fresh browsers
        p = spec("?no-seek")
        s1, _, x1 = shots(chrome, p, scope)
        s2, _, _ = shots(chrome, p, scope)
        check(x1["mode"] == "virtual-clock", "without a hook the capture steps the virtual clock")
        check(*repeat(s1, s2, "virtual clock"))
        check(len({mc.same(s1[t], s1[TIMES[0]]) for t in TIMES[1:]} - {"identical"}) > 0, "the captures differ over time (the clock moves)")
        f = x1["frozen"]
        check(f[0] == f[2] and f[1] == f[3], "performance.now and Date stand still between steps")
        # app seek hook, twice
        p = spec()
        h1, st1, x2 = shots(chrome, p, scope)
        h2, _, _ = shots(chrome, p, scope)
        check(x2["mode"] == "app-seek", "with window.__motion the capture uses the app's seek")
        check(*repeat(h1, h2, "app seek"))
        check(all((st1[t] or {}).get("sceneId") == mo.expected_scene(p, t) for t in TIMES),
              "state().sceneId matches the spec's scene at every time")
        # forced virtual clock on a page with a hook
        p2 = copy.deepcopy(p)
        p2["capture"]["seekMode"] = "virtual-clock"
        _, _, x3 = shots(chrome, p2, scope)
        check(x3["mode"] == "virtual-clock", "seekMode virtual-clock ignores the hook")
        # reduced motion
        r, _, _ = shots(chrome, spec("?no-seek"), scope, reduced=True)
        rv = {t: mc.same(r[t], r[0.0]) for t in TIMES}
        check(all(v != "different" for v in rv.values()), f"reduced motion: the page stands still ({rv})")
        # blocked network
        _, _, x4 = shots(chrome, spec("?no-seek&remote"), scope)
        check(any("example.com" in u for u in x4["blocked"]), "a remote request is blocked and reported")
        # release to real time
        target = mc.resolve_target(HERE, spec("?no-seek"), None)
        v = mc.open_visual(chrome, spec("?no-seek"), mo.viewport_spec(spec(), "small"), target, scope)
        a0 = v.page.evaluate("performance.now()")
        v.page.evaluate("window.__motionClock.release()")
        v.page.pump(0.3)
        check(v.page.evaluate("performance.now()") > a0 + 100, "release() hands the page back to real time")
        v.close()
        # behaviour lane
        vp = mo.viewport_spec(spec(), "small")
        live = mc.open_live(chrome, spec(), vp, mc.resolve_target(HERE, spec(), None), scope)
        c = mc.check_control(live, spec())
        check(c["result"] == "PASS", f"a working pause button passes ({c['detail']})")
        hid = mc.check_hidden_tab(live, spec())
        check(hid["result"] == "PASS", f"a really hidden tab is seen and the motion does not jump ({hid['detail']})")
        live.browser.close()
        p = spec("?broken-pause")
        live = mc.open_live(chrome, p, vp, mc.resolve_target(HERE, p, None), scope)
        c = mc.check_control(live, p)
        check(c["result"] == "FAIL", f"a pause button that only changes its label fails ({c['detail']})")
        live.browser.close()
        pids = [pr.pid for pr, _ in scope.procs]
    alive = []
    for pid in pids:
        try:
            if sys.platform == "win32":
                import subprocess
                out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=30).stdout
                if str(pid) in out:
                    alive.append(pid)
            else:
                import os
                os.kill(pid, 0)
                alive.append(pid)
        except (ProcessLookupError, PermissionError):
            pass
    check(not alive, f"every browser the checks started is stopped ({len(pids)} started)")
    print(json.dumps({"failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
