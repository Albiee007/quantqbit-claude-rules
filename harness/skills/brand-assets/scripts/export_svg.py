#!/usr/bin/env python3
"""Export SVG or HTML brand masters to PNG at exact sizes with headless Chrome/Edge.

SVG sources are centred on a transparent canvas with optional padding; HTML
sources (og-image.html, promo banners) are screenshotted at the window size.
--flatten fills transparency with a colour and saves RGB (stores reject alpha
in screenshots, feature graphics and the App Store icon).

Usage:
  python export_svg.py brand/mark.svg --size 2048x2048 --out brand/png
  python export_svg.py brand/mark.svg --size 1024x1024 --size 512x512 --pad 0.1 --out brand/png
  python export_svg.py og-image.html --size 1200x630 --flatten "#ffffff" --out public
Needs Pillow and Chrome, Chromium or Edge (or --chrome PATH).
"""

from __future__ import annotations

import argparse
import os
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


def shoot(chrome: str, url: str, size: tuple[int, int], dest: Path) -> None:
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             "--default-background-color=00000000", f"--user-data-dir={profile}", "--allow-file-access-from-files",
             f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=5000", f"--screenshot={dest}", url],
            check=True, capture_output=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", type=Path, help=".svg or .html master")
    parser.add_argument("--size", type=parse_size, action="append", required=True, help="WxH; repeatable")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--name", help="output base name (default: source stem)")
    parser.add_argument("--pad", type=float, default=0.0, help="SVG padding as a share of each side (0-0.4)")
    parser.add_argument("--flatten", help="fill transparency with #RRGGBB and save RGB")
    parser.add_argument("--chrome")
    args = parser.parse_args()
    if not args.src.is_file() or args.src.suffix.lower() not in (".svg", ".html", ".htm"):
        print("src must be an existing .svg or .html file", file=sys.stderr)
        return 2
    chrome = find_chrome(args.chrome)
    args.out.mkdir(parents=True, exist_ok=True)
    base = args.name or args.src.stem

    with tempfile.TemporaryDirectory() as tmp:
        for w, h in args.size:
            if args.src.suffix.lower() == ".svg":
                pad_x, pad_y = round(w * args.pad), round(h * args.pad)
                wrapper = Path(tmp) / f"wrap-{w}x{h}.html"
                wrapper.write_text(
                    "<!doctype html><html><body style=\"margin:0;background:transparent\">"
                    f"<img src=\"{args.src.resolve().as_uri()}\" style=\"position:absolute;left:{pad_x}px;top:{pad_y}px;"
                    f"width:{w - 2 * pad_x}px;height:{h - 2 * pad_y}px;object-fit:contain\"></body></html>",
                    encoding="utf-8")
                url = wrapper.as_uri()
            else:
                url = args.src.resolve().as_uri()
            raw = Path(tmp) / f"raw-{w}x{h}.png"
            shoot(chrome, url, (w, h), raw)
            img = Image.open(raw).convert("RGBA")
            if img.size != (w, h):
                raise SystemExit(f"got {img.size}, want {(w, h)}")
            if args.flatten:
                v = args.flatten.lstrip("#")
                bg = Image.new("RGBA", img.size, tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) + (255,))
                bg.alpha_composite(img)
                img = bg.convert("RGB")
            dest = args.out / f"{base}-{w}x{h}.png"
            img.save(dest, optimize=True)
            print(f"wrote {dest}  {w}x{h}{'  (flattened)' if args.flatten else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
