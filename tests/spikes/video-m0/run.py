"""M0 spike for video rendering (not a release test).

Checks the seek contract on this OS: frames are identical however they are reached, clip windows
are [start, end), readiness times out with a reason, no network, and (when ffmpeg is present) an
H.264 encode and a two-segment concat give the exact frame count. Prints JSON; exit 1 on a failure.

    python tests/spikes/video-m0/run.py [--chrome PATH] [--ffmpeg PATH] [--trials N]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "harness" / "lib"))
from harnesslib import browser, cdp  # noqa: E402

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

SIZE = (1080, 1920)
RUNTIME = (HERE / "runtime.js").read_text(encoding="utf-8")
URL = (HERE / "fixture.html").as_uri()
failures: list[str] = []
res: dict = {}


def check(ok: bool, what: str) -> None:
    if not ok:
        failures.append(what)


def open_page(b, url=URL):
    p = b.new_page(SIZE)
    p.block_network()
    p.add_init_script(RUNTIME)
    p.navigate(url)
    return p, p.evaluate("window.__hf.ready()")


def shot(p, n, fmt="png", raf=False):
    p.evaluate(f"window.__hf.seek({n}/window.__hf.fps, {{raf: {str(raf).lower()}}})")
    return p.screenshot(fmt, 92 if fmt == "jpeg" else None)


def pix(png):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    return hashlib.sha256(im.tobytes()).hexdigest()[:16], im


def render(chrome, order):
    with cdp.Browser.launch(chrome, SIZE) as b:
        p, info = open_page(b)
        out: dict[int, list[str]] = {}
        for n in order:
            out.setdefault(n, []).append(pix(shot(p, n))[0])
        return out, info, p.errors


def mismatches(ref, other):
    return [n for n in other if any(h != ref[n][0] for h in other[n])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chrome")
    ap.add_argument("--ffmpeg")
    ap.add_argument("--trials", type=int, default=20)
    a = ap.parse_args()
    if Image is None:
        print("Pillow is required", file=sys.stderr)
        return 2
    chrome = browser.find_chrome(a.chrome)
    res["chrome"] = browser.version(chrome)
    res["platform"] = sys.platform

    frames = list(range(90))
    t = time.monotonic()
    fwd, info, errs = render(chrome, frames)
    res["ready"], res["page_errors"] = info, errs
    res["forward_s"] = round(time.monotonic() - t, 2)
    check(info.get("frames") == 90 and not errs, "fixture loads cleanly with 90 frames")
    rng = random.Random(7)
    res["backward_mismatch"] = mismatches(fwd, render(chrome, frames[::-1])[0])
    rep = render(chrome, [rng.choice(frames) for _ in range(120)] + [15, 15, 44, 45, 45])[0]
    res["random_mismatch"] = mismatches(fwd, rep)
    res["repeat_internal_mismatch"] = [n for n, hs in rep.items() if len(set(hs)) > 1]
    res["worker2_mismatch"] = mismatches(fwd, render(chrome, frames[45:])[0])
    fresh: dict[int, list[str]] = {}
    for i in range(a.trials):
        n = (15, 36, 44, 45, 60, 89)[i % 6]
        fresh.setdefault(n, []).extend(render(chrome, [n])[0][n])
    res["fresh_trials"] = a.trials
    res["fresh_mismatch"] = mismatches(fwd, fresh)
    for k in ("backward_mismatch", "random_mismatch", "repeat_internal_mismatch", "worker2_mismatch", "fresh_mismatch"):
        check(not res[k], f"seek history independence: {k} = {res[k]}")

    with cdp.Browser.launch(chrome, SIZE) as b:
        p, _ = open_page(b)
        px = pix(shot(p, 15))[1].getpixel((100, 100))
        res["box_px_f15"] = px
        check(all(abs(c - 128) <= 3 for c in px), "linear black→white at frame 15 of 30 is 128±3")
        vis = "[...document.querySelectorAll('.clip')].map(e=>e.id+':'+getComputedStyle(e).visibility).join(' ')"
        want = {35: "a:visible b:hidden", 36: "a:visible b:visible", 44: "a:visible b:visible", 45: "a:hidden b:visible"}
        for n, w in want.items():
            p.evaluate(f"window.__hf.seek({n}/30, {{raf: false}})")
            got = p.evaluate(vis)
            check(got == w, f"clip window at frame {n}: {got} (want {w})")
        p.evaluate("fetch('https://example.com/x').then(()=>'ok',()=>'failed')")
        res["blocked"] = p.blocked
        check(any(u.startswith("https://example.com") for u in p.blocked), "remote request is blocked")
        res["raf_vs_noraf_mismatch"] = [n for n in (15, 40, 50, 70) if pix(shot(p, n, raf=True))[0] != fwd[n][0]]
        check(not res["raf_vs_noraf_mismatch"], "frames identical with and without the rAF wait")

    with tempfile.TemporaryDirectory() as tmp:
        hang = Path(tmp) / "hang.html"
        hang.write_text((HERE / "fixture.html").read_text(encoding="utf-8").replace(
            "<script>", "<script>__hf.waitFor(new Promise(()=>{}), 'lottie: logo.json');", 1), encoding="utf-8")
        with cdp.Browser.launch(chrome, SIZE) as b:
            p = b.new_page(SIZE)
            p.add_init_script(RUNTIME)
            p.navigate(hang.as_uri())
            try:
                p.evaluate("window.__hf.ready(2000)")
                res["ready_timeout"] = "resolved"
            except Exception as e:  # noqa: BLE001
                res["ready_timeout"] = str(e)
        check("lottie: logo.json" in res["ready_timeout"], "readiness timeout names what is pending")

    def bench(fmt, n=60):
        with cdp.Browser.launch(chrome, SIZE) as b:
            p, _ = open_page(b)
            shot(p, 0, fmt)
            t0 = time.monotonic()
            for i in range(n):
                shot(p, i % 90, fmt)
            return round((time.monotonic() - t0) / n * 1000, 1)
    res["ms_per_frame_png"] = bench("png")
    res["ms_per_frame_jpeg92"] = bench("jpeg")

    ff = a.ffmpeg or shutil.which("ffmpeg")
    if not ff:
        res["encode"] = "SKIPPED (ffmpeg not found)"
    else:
        fp = str(Path(ff).with_name(Path(ff).name.replace("ffmpeg", "ffprobe")))
        vf = ("scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
              "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv")
        enc = ["-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
               "-pix_fmt", "yuv420p", "-r", "30"]

        def encode(rng_, dest, faststart=True):
            argv = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-vcodec", "mjpeg",
                    "-framerate", "30", "-i", "-", *enc] + (["-movflags", "+faststart"] if faststart else []) + [str(dest)]
            proc = subprocess.Popen(argv, stdin=subprocess.PIPE)
            with cdp.Browser.launch(chrome, SIZE) as b:
                p, _ = open_page(b)
                for n in rng_:
                    proc.stdin.write(shot(p, n, "jpeg"))
            proc.stdin.close()
            return proc.wait(300)

        def probe(path):
            r = subprocess.run([fp, "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path)],
                               capture_output=True, text=True, timeout=120)
            st = json.loads(r.stdout)["streams"][0]
            return {k: st.get(k) for k in ("codec_name", "profile", "pix_fmt", "width", "height", "r_frame_rate",
                                           "nb_read_frames", "color_space", "color_primaries", "color_transfer")}

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            check(encode(range(90), d / "single.mp4") == 0, "ffmpeg encode")
            check(encode(range(45), d / "s0.mp4", False) == 0 and encode(range(45, 90), d / "s1.mp4", False) == 0,
                  "ffmpeg segment encode")
            (d / "list.txt").write_text("file 's0.mp4'\nfile 's1.mp4'\n")
            subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                            str(d / "list.txt"), "-c", "copy", "-movflags", "+faststart", str(d / "joined.mp4")],
                           check=True, timeout=120)
            for name in ("single", "joined"):
                pr = probe(d / f"{name}.mp4")
                res[f"probe_{name}"] = pr
                head = (d / f"{name}.mp4").read_bytes()[:1 << 20]
                check(pr["codec_name"] == "h264" and pr["profile"] == "High" and pr["pix_fmt"] == "yuv420p"
                      and pr["r_frame_rate"] == "30/1" and pr["nb_read_frames"] == "90"
                      and (pr["width"], pr["height"]) == SIZE, f"{name}: h264-web profile and 90 frames")
                check(pr["color_space"] == pr["color_primaries"] == pr["color_transfer"] == "bt709", f"{name}: BT.709 tags")
                moov, mdat = head.find(b"moov"), head.find(b"mdat")
                check(moov != -1 and (mdat == -1 or moov < mdat), f"{name}: moov before mdat (faststart)")
        res["ffmpeg"] = subprocess.run([ff, "-version"], capture_output=True, text=True).stdout.split("\n")[0]

    res["failures"] = failures
    print(json.dumps(res, indent=1, default=str))
    if os.environ.get("GITHUB_ACTIONS"):  # annotations are readable without a login; job logs aren't
        for f in failures:
            print(f"::error title=video M0 ({sys.platform})::{f}")
        keys = ("chrome", "forward_s", "fresh_trials", "box_px_f15", "ms_per_frame_png", "ms_per_frame_jpeg92",
                "ready_timeout", "encode", "ffmpeg")
        print(f"::notice title=video M0 ({sys.platform})::" + json.dumps({k: res.get(k) for k in keys}, default=str))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        if os.environ.get("GITHUB_ACTIONS"):
            msg = f"{type(e).__name__}: {e}".replace("\n", " ")[:900]
            print(f"::error title=video M0 ({sys.platform}) crashed::{msg}")
        raise
