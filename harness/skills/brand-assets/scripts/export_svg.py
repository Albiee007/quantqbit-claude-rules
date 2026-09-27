#!/usr/bin/env python3
"""Export SVG or HTML brand masters to PNG at exact sizes with headless Chrome/Edge.

SVG sources are centred on a transparent canvas with optional padding; HTML
sources (og-image.html, promo banners) are screenshotted at the window size.
--flatten fills transparency with a colour and saves RGB (stores reject alpha
in screenshots, feature graphics and the App Store icon).

Every file written is re-opened and checked: exact size, RGB when flattened,
and not blank. HTML sources also get a text contrast check (WCAG 2.2: 4.5:1,
3:1 for large text); --no-contrast skips it.

One-off exports:
  python export_svg.py brand/mark.svg --size 2048x2048 --out brand/png
  python export_svg.py brand/mark.svg brand/mark-mono.svg --size 1024x1024 --size 512x512 --pad 0.1 --out brand/png
  python export_svg.py og-image.html --size 1200x630 --flatten "#ffffff" --out public
The whole brand set from one plan file (paths relative to the plan's folder):
  python export_svg.py --plan brand/exports.json [--only og-image]
  {"exports": [{"src": "mark.svg", "sizes": ["2048x2048", "1024x1024"], "out": "png"},
               {"src": "html/og-image.html", "sizes": ["1200x630"], "out": "social", "flatten": "#2a1bb0"}]}
  optional per entry: "name" (output base name), "pad", "flatten", "contrast": false
Needs Pillow and Chrome, Chromium or Edge (or --chrome PATH).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

# Lists every visible text run with its colour, size, weight and boxes (appended to a copy of the page).
PROBE_JS = """<script>addEventListener('load', () => setTimeout(() => {
  const runs = [], W = innerWidth, H = innerHeight;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent.trim(), el = n.parentElement;
    if (!text || !el || el.closest('script,style,noscript')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    const rects = [...range.getClientRects()]
      .map((r) => [Math.max(0, r.left), Math.max(0, r.top), Math.min(W, r.right), Math.min(H, r.bottom)])
      .filter(([l, t, r, b]) => r - l >= 2 && b - t >= 2);
    if (rects.length) runs.push({ text: text.slice(0, 40), color: cs.color, size: parseFloat(cs.fontSize),
      weight: Number(cs.fontWeight) || 400, rects });
  }
  const pre = document.createElement('pre'); pre.id = 'probe'; pre.style.display = 'none';
  pre.textContent = JSON.stringify({ runs }); document.body.appendChild(pre);
}, 300));</script>"""
HIDE_TEXT = ("<style>body * { color: transparent !important; -webkit-text-fill-color: transparent !important; "
             "text-shadow: none !important; }</style>")


def find_chrome(explicit: str | None) -> str:
    candidates = [explicit, os.environ.get("CHROME")]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates += [str(Path(base) / "Google/Chrome/Application/chrome.exe"),
                           str(Path(base) / "Microsoft/Edge/Application/msedge.exe")]
    candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                   "/Applications/Chromium.app/Contents/MacOS/Chromium",
                   "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    candidates += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome")]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise SystemExit("Chrome/Chromium/Edge not found; pass --chrome PATH or set CHROME")


def parse_size(value: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"size must be WxH, got {value}")
    return w, h


def chrome_cmd(chrome: str, profile: str, size: tuple[int, int]) -> list[str]:
    return [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
            "--default-background-color=00000000", f"--user-data-dir={profile}", "--allow-file-access-from-files",
            f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=5000"]


def shoot(chrome: str, url: str, size: tuple[int, int], dest: Path) -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(chrome_cmd(chrome, profile, size) + [f"--screenshot={dest}", url], check=True, capture_output=True)


def page_copy(src: Path, tmp: Path, extra: str, tag: str) -> str:
    """A copy of an HTML page with `extra` appended; <base> keeps its relative URLs pointing at src's folder."""
    text = src.read_text(encoding="utf-8")
    base = f'<base href="{src.resolve().parent.as_uri()}/">'
    text = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + base, text, count=1, flags=re.I) if re.search(r"<head", text, re.I) else base + text
    text = re.sub(r"(</body>)", lambda m: extra + m.group(1), text, count=1, flags=re.I) if re.search(r"</body>", text, re.I) else text + extra
    page = tmp / f"{tag}-{src.stem}.html"
    page.write_text(text, encoding="utf-8")
    return page.as_uri()


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple) -> float:
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def parse_color(css: str) -> tuple[float, float, float, float] | None:
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)", css.strip())
    if not m:
        return None
    a = m.group(4)
    alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
    return float(m.group(1)), float(m.group(2)), float(m.group(3)), alpha


def contrast(chrome: str, src: Path, size: tuple[int, int], flatten: str | None, tmp: Path) -> int:
    """Checks every text run of an HTML page against the pixels behind it. Returns the number of failures."""
    with tempfile.TemporaryDirectory() as profile:
        r = subprocess.run(chrome_cmd(chrome, profile, size) + ["--dump-dom", page_copy(src, tmp, PROBE_JS, "probe")],
                           capture_output=True)
    m = re.search(r'<pre id="probe"[^>]*>(.*?)</pre>', r.stdout.decode("utf-8", errors="replace"), re.S)
    if not m:
        print(f"  WARN  {src.name}: contrast probe returned nothing; check the text contrast by eye")
        return 0
    runs = json.loads(html.unescape(m.group(1)))["runs"]
    shot = tmp / f"bg-{src.stem}.png"
    shoot(chrome, page_copy(src, tmp, HIDE_TEXT, "bg"), size, shot)
    bg = Image.open(shot).convert("RGBA")
    backdrop = Image.new("RGBA", bg.size, hex_rgba(flatten) if flatten else (255, 255, 255, 255))
    backdrop.alpha_composite(bg)
    px = backdrop.convert("RGB").load()
    fails = 0
    worst = 99.0
    for run in runs:
        col = parse_color(run["color"])
        if col is None:
            print(f"  WARN  {src.name}: colour {run['color']!r} of {run['text']!r} not understood; check it by eye")
            continue
        r_, g_, b_, a = col
        ratios = []
        for left, top, right, bottom in run["rects"]:
            w, h = int(right - left), int(bottom - top)
            step = max(1, int((w * h / 4000) ** 0.5))
            for y in range(int(top), int(bottom), step):
                for x in range(int(left), int(right), step):
                    p = px[min(x, size[0] - 1), min(y, size[1] - 1)]
                    t = (a * r_ + (1 - a) * p[0], a * g_ + (1 - a) * p[1], a * b_ + (1 - a) * p[2])
                    l1, l2 = luminance(t), luminance(p)
                    ratios.append((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05))
        if not ratios:
            continue
        ratios.sort()
        ratio = ratios[len(ratios) // 20]
        large = run["size"] >= 24 or (run["size"] >= 18.66 and run["weight"] >= 700)
        need = 3.0 if large else 4.5
        worst = min(worst, ratio)
        if ratio < need:
            fails += 1
            print(f"  FAIL  {src.name} @ {size[0]}x{size[1]}: {run['text']!r} ({run['color']}) {ratio:.2f}:1 < {need}:1")
    if runs:
        print(f"  contrast {src.name} @ {size[0]}x{size[1]}: {len(runs)} text runs, worst {worst:.1f}:1")
    return fails


def hex_rgba(value: str) -> tuple[int, int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        raise SystemExit(f"--flatten must be #RRGGBB, got {value}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) + (255,)  # type: ignore[return-value]


def verify(dest: Path, size: tuple[int, int], flatten: bool) -> str | None:
    with Image.open(dest) as im:
        if im.size != size:
            return f"{im.size[0]}x{im.size[1]}, want {size[0]}x{size[1]}"
        if flatten and im.mode != "RGB":
            return f"mode {im.mode}, want RGB (flattened)"
        rgba = im.convert("RGBA")
        if rgba.getchannel("A").getextrema()[1] == 0:
            return "fully transparent"
        if all(lo == hi for lo, hi in rgba.convert("RGB").getextrema()) and not flatten and rgba.getchannel("A").getextrema()[0] == 255:
            return "a single flat colour (did the source load?)"
    return None


def export(chrome: str, job: dict, tmp: Path, check_contrast: bool) -> tuple[int, int]:
    """Writes one source at each size. Returns (files written, problems)."""
    src: Path = job["src"]
    out: Path = job["out"]
    out.mkdir(parents=True, exist_ok=True)
    base = job.get("name") or src.stem
    is_svg = src.suffix.lower() == ".svg"
    written = problems = 0
    for w, h in job["sizes"]:
        if is_svg:
            pad_x, pad_y = round(w * job.get("pad", 0.0)), round(h * job.get("pad", 0.0))
            wrapper = tmp / f"wrap-{src.stem}-{w}x{h}.html"
            wrapper.write_text(
                "<!doctype html><html><body style=\"margin:0;background:transparent\">"
                f"<img src=\"{src.resolve().as_uri()}\" style=\"position:absolute;left:{pad_x}px;top:{pad_y}px;"
                f"width:{w - 2 * pad_x}px;height:{h - 2 * pad_y}px;object-fit:contain\"></body></html>",
                encoding="utf-8")
            url = wrapper.as_uri()
        else:
            url = src.resolve().as_uri()
        raw = tmp / f"raw-{src.stem}-{w}x{h}.png"
        shoot(chrome, url, (w, h), raw)
        img = Image.open(raw).convert("RGBA")
        if img.size != (w, h):
            raise SystemExit(f"{src.name}: got {img.size}, want {(w, h)}")
        if job.get("flatten"):
            bg = Image.new("RGBA", img.size, hex_rgba(job["flatten"]))
            bg.alpha_composite(img)
            img = bg.convert("RGB")
        dest = out / f"{base}-{w}x{h}.png"
        img.save(dest, optimize=True)
        written += 1
        problem = verify(dest, (w, h), bool(job.get("flatten")))
        if problem:
            problems += 1
            print(f"FAIL  {dest}: {problem}")
        else:
            print(f"wrote {dest}  {w}x{h}{'  (flattened)' if job.get('flatten') else ''}")
        if not is_svg and check_contrast and job.get("contrast", True):
            problems += contrast(chrome, src, (w, h), job.get("flatten"), tmp)
    return written, problems


def load_plan(plan: Path, only: list[str]) -> list[dict]:
    try:
        data = json.loads(plan.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SystemExit(f"cannot read plan {plan}: {e}")
    root = plan.resolve().parent
    jobs = []
    for i, e in enumerate(data.get("exports") or []):
        unknown = set(e) - {"src", "sizes", "out", "name", "pad", "flatten", "contrast"}
        if unknown or not e.get("src") or not e.get("sizes") or not e.get("out"):
            raise SystemExit(f"plan entry {i + 1}: needs src, sizes and out" + (f"; unknown keys {sorted(unknown)}" if unknown else ""))
        job = dict(e, src=root / e["src"], out=root / e["out"], sizes=[parse_size(s) for s in e["sizes"]])
        if not only or job.get("name", job["src"].stem) in only or job["src"].stem in only:
            jobs.append(job)
    if not jobs:
        raise SystemExit(f"plan {plan}: no exports" + (f" match --only {only}" if only else ""))
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", type=Path, nargs="*", help=".svg or .html masters")
    parser.add_argument("--plan", type=Path, help="JSON plan listing every export (see above)")
    parser.add_argument("--only", action="append", default=[], help="with --plan: export only this source stem or name; repeatable")
    parser.add_argument("--size", type=parse_size, action="append", help="WxH; repeatable")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--name", help="output base name (default: source stem; one source only)")
    parser.add_argument("--pad", type=float, default=0.0, help="SVG padding as a share of each side (0-0.4)")
    parser.add_argument("--flatten", help="fill transparency with #RRGGBB and save RGB")
    parser.add_argument("--no-contrast", action="store_true", help="skip the text contrast check on HTML sources")
    parser.add_argument("--chrome")
    args = parser.parse_args()
    if args.plan:
        if args.src or args.size or args.out:
            parser.error("--plan replaces SRC, --size and --out")
        jobs = load_plan(args.plan, args.only)
    else:
        if not args.src or not args.size or not args.out:
            parser.error("give SRC..., --size and --out (or --plan)")
        if args.name and len(args.src) > 1:
            parser.error("--name needs a single source")
        jobs = [{"src": s, "sizes": args.size, "out": args.out, "name": args.name, "pad": args.pad, "flatten": args.flatten}
                for s in args.src]
    for job in jobs:
        if not job["src"].is_file() or job["src"].suffix.lower() not in (".svg", ".html", ".htm"):
            print(f"{job['src']}: src must be an existing .svg or .html file", file=sys.stderr)
            return 2
    chrome = find_chrome(args.chrome)
    written = problems = 0
    with tempfile.TemporaryDirectory() as tmp:
        for job in jobs:
            w, p = export(chrome, job, Path(tmp), not args.no_contrast)
            written += w
            problems += p
    print(f"exported {written} file(s) from {len(jobs)} source(s); {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
