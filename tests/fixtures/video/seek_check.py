"""The seek contract, checked in a real browser (used by tests/video.test.sh).

seek.html holds two overlapping clips, Web Animations with absolute delays, a CSS @keyframes
animation (clip-relative time) and dots placed with __hf.rand. The harness runtime
(harness/lib/media/timeline.js) is injected the way render_video.py injects it. Checks:
frames are identical however they are reached (forward, backward, random with repeats, a second
browser starting mid-way, fresh browsers starting at single frames); a linear black-to-white box is
128 at frame 15 of 30; clip windows are [start, end); remote requests are blocked; readiness times
out naming what is pending. Prints one line per check; exit 1 when any fails.

    python tests/fixtures/video/seek_check.py [--chrome PATH] [--trials N]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "harness" / "lib"))
sys.dont_write_bytecode = True
from harnesslib import browser, cdp  # noqa: E402
from PIL import Image  # noqa: E402

SIZE = (1080, 1920)
RUNTIME = (REPO / "harness" / "lib" / "media" / "timeline.js").read_text(encoding="utf-8")
URL = (HERE / "seek.html").as_uri()
failed = 0


def check(ok: bool, what: str) -> None:
    global failed
    print(("ok    " if ok else "FAIL  ") + what)
    failed += not ok


def open_page(b: cdp.Browser, url: str = URL):
    p = b.new_page(SIZE)
    p.block_network()
    p.add_init_script(RUNTIME)
    p.navigate(url)
    return p, p.evaluate("window.__hf.ready()")


def frame(p, n: int) -> Image.Image:
    p.evaluate(f"window.__hf.seek({n}/window.__hf.fps)")
    return Image.open(io.BytesIO(p.screenshot("png"))).convert("RGB")


def digest(im: Image.Image) -> str:
    return hashlib.sha256(im.tobytes()).hexdigest()[:16]


def render(chrome: str, order: list[int]) -> dict[int, list[str]]:
    with cdp.Browser.launch(chrome, SIZE) as b:
        p, _ = open_page(b)
        out: dict[int, list[str]] = {}
        for n in order:
            out.setdefault(n, []).append(digest(frame(p, n)))
        return out


def differ(ref: dict, other: dict) -> list[int]:
    return sorted(n for n in other if any(h != ref[n][0] for h in other[n]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome")
    ap.add_argument("--trials", type=int, default=12)
    a = ap.parse_args()
    chrome = browser.find_chrome(a.chrome)
    frames = list(range(90))
    with cdp.Browser.launch(chrome, SIZE) as b:
        p, info = open_page(b)
        check(info["frames"] == 90 and info["clips"] == 2 and not p.errors, f"the fixture loads: {info}, errors {p.errors}")
        fwd: dict[int, list[str]] = {n: [digest(frame(p, n))] for n in frames}
        box = frame(p, 15).getpixel((100, 100))
        check(all(abs(c - 128) <= 3 for c in box), f"a linear black-to-white fade is 128 at frame 15 of 30 (got {box})")
        vis = "[...document.querySelectorAll('.clip')].map(e=>e.id+':'+getComputedStyle(e).visibility).join(' ')"
        want = {35: "a:visible b:hidden", 36: "a:visible b:visible", 44: "a:visible b:visible", 45: "a:hidden b:visible"}
        got = {}
        for n in want:
            p.evaluate(f"window.__hf.seek({n}/30)")
            got[n] = p.evaluate(vis)
        check(got == want, f"clip windows are [start, end): {got}")
        p.evaluate("fetch('https://example.com/x').then(()=>'ok',()=>'failed')")
        check(any(u.startswith("https://example.com") for u in p.blocked), "a remote request is blocked")
        check(p.evaluate("Date.now() === new Date().getTime() && performance.now() === 0"), "clock reads are frozen")
        check(p.evaluate("typeof Date() === 'string' && new Date(0).getTime() === 0 && new Date() instanceof Date"),
              "Date() without new still works (and dates with arguments are untouched)")
    check(len({h[0] for h in fwd.values()}) > 40, "the fixture really animates (many distinct frames)")
    check(not differ(fwd, render(chrome, frames[::-1])), "backward seeks give the same frames")
    rng = random.Random(7)
    rep = render(chrome, [rng.choice(frames) for _ in range(120)] + [15, 15, 44, 45, 45])
    check(not differ(fwd, rep), "random seeks with repeats give the same frames")
    check(not differ(fwd, render(chrome, frames[45:])), "a second browser starting at frame 45 matches")
    fresh: dict[int, list[str]] = {}
    for i in range(a.trials):
        n = (15, 36, 44, 45, 60, 89)[i % 6]
        fresh.setdefault(n, []).extend(render(chrome, [n])[n])
    check(not differ(fwd, fresh), f"{a.trials} fresh browsers seeking straight to one frame match")
    with tempfile.TemporaryDirectory() as tmp:
        hang = Path(tmp) / "hang.html"
        hang.write_text((HERE / "seek.html").read_text(encoding="utf-8").replace(
            "<script>", "<script>__hf.waitFor(new Promise(()=>{}), 'lottie: logo.json');", 1), encoding="utf-8")
        with cdp.Browser.launch(chrome, SIZE) as b:
            p = b.new_page(SIZE)
            p.add_init_script(RUNTIME)
            p.navigate(hang.as_uri())
            try:
                p.evaluate("window.__hf.ready(1500)")
                msg = "resolved"
            except Exception as e:  # noqa: BLE001
                msg = str(e)
        check("lottie: logo.json" in msg, f"readiness times out and names what is pending ({msg[:90]})")
    print(f"seek contract: {failed} failure(s)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
