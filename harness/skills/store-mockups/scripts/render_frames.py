#!/usr/bin/env python3
"""Render store screenshots and the Play feature graphic from an HTML mockup kit.

  init   copy the kit templates into a working folder (refuses to overwrite)
  render shoot every frame x size with headless Chrome/Edge, flatten to RGB,
         and assert exact dimensions and < 8 MB per file

Kit folder after init:
  frame.html  app.css  screens.js  demo-data.js  frames.json  (assets/ for fonts, icons)
Output: <kit>/<frames.json "out">/play/{phone,tablet7,tablet10}/  ios/{6.9,6.5,ipad13}/
        play/feature_graphic_1024x500.png

Usage:
  python render_frames.py init   store-assets/mockup-kit
  python render_frames.py render store-assets/mockup-kit [--frames 01-home,03-x] [--sizes play-phone,ios-69]
                                 [--project .] [--chrome PATH]
Needs Pillow (pip install pillow) and Chrome, Chromium or Edge. Sizes follow
store-submission-precheck/references/store-specs.md.
"""

from __future__ import annotations

import argparse
import json
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

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
# key: (width, height, platform, output path relative to "out")
SIZES = {
    "play-phone": (1080, 1920, "android", "play/phone"),
    "play-tab7": (1200, 1920, "android", "play/tablet7"),
    "play-tab10": (1620, 2880, "android", "play/tablet10"),
    "ios-69": (1290, 2796, "ios", "ios/6.9"),
    "ios-69-1320": (1320, 2868, "ios", "ios/6.9"),
    "ios-65": (1242, 2688, "ios", "ios/6.5"),
    "ios-ipad13": (2064, 2752, "ios", "ios/ipad13"),
    "fg": (1024, 500, "android", "play"),
}
KIT_FILES = {
    "frame.html": "frame.html",
    "app.css": "app.css",
    "screens.example.js": "screens.js",
    "demo-data.example.js": "demo-data.js",
    "frames.example.json": "frames.json",
}
ICON_SOURCES = [
    ("node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/glyphmaps/Ionicons.json"),
    ("node_modules/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/react-native-vector-icons/glyphmaps/Ionicons.json"),
]


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


def init(kit: Path) -> int:
    kit.mkdir(parents=True, exist_ok=True)
    for src, dest in KIT_FILES.items():
        target = kit / dest
        if target.exists():
            print(f"skip {target} (exists)")
            continue
        shutil.copyfile(TEMPLATES / src, target)
        print(f"wrote {target}")
    (kit / "assets").mkdir(exist_ok=True)
    print("next: edit app.css tokens, screens.js, demo-data.js and frames.json, then run render")
    return 0


def write_icons(kit: Path, family: str, project: Path) -> None:
    out = kit / "icons.generated.js"
    if family != "ionicons":
        out.write_text("window.ION = null;\n", encoding="utf-8")
        return
    for start in [project, *project.parents]:
        for ttf, glyphs in ICON_SOURCES:
            if (start / ttf).is_file() and (start / glyphs).is_file():
                (kit / "assets").mkdir(exist_ok=True)
                shutil.copyfile(start / ttf, kit / "assets/Ionicons.ttf")
                glyph_map = json.loads((start / glyphs).read_text(encoding="utf-8"))
                out.write_text("window.ION = " + json.dumps(glyph_map) + ";\n", encoding="utf-8")
                print(f"icons: Ionicons from {start / ttf}")
                return
    raise SystemExit("frames.json asks for ionicons but no Ionicons.ttf + glyphmap was found under node_modules; "
                     "pass --project <app dir> or set \"icons\": \"material\"")


def shoot(chrome: str, url: str, size: tuple[int, int], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw = dest.with_suffix(".raw.png")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--user-data-dir={profile}", "--allow-file-access-from-files", "--no-first-run",
             f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=8000", f"--screenshot={raw}", url],
            check=True, capture_output=True,
        )
    img = Image.open(raw).convert("RGB")
    raw.unlink()
    if img.size != size:
        raise SystemExit(f"{dest.name}: got {img.size}, want {size}")
    img.save(dest, optimize=True)
    if dest.stat().st_size >= 8 * 1024 * 1024:
        raise SystemExit(f"{dest.name} is 8 MB or more")
    print(f"ok  {dest}  {size[0]}x{size[1]}")


def render(kit: Path, frames_filter: set[str], sizes_filter: list[str], project: Path, chrome_arg: str | None) -> int:
    cfg_path = kit / "frames.json"
    if not cfg_path.is_file():
        print(f"{cfg_path} not found; run: python render_frames.py init {kit}", file=sys.stderr)
        return 2
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    sizes = sizes_filter or cfg.get("sizes") or ["play-phone", "ios-69"]
    unknown = [s for s in sizes if s not in SIZES or s == "fg"]
    if unknown:
        print(f"unknown size key(s): {unknown}; choose from {[k for k in SIZES if k != 'fg']}", file=sys.stderr)
        return 2
    frames = cfg.get("frames") or []
    if not frames:
        print("frames.json has no frames", file=sys.stderr)
        return 2

    generated = dict(cfg)
    generated["sizes"] = {k: list(v[:3]) for k, v in SIZES.items()}
    (kit / "frames.generated.js").write_text("window.FRAMES = " + json.dumps(generated, ensure_ascii=False) + ";\n", encoding="utf-8")
    write_icons(kit, cfg.get("icons", "material"), project)
    chrome = find_chrome(chrome_arg)
    out = kit / cfg.get("out", "out")
    base = (kit / "frame.html").resolve().as_uri()

    for key in sizes:
        w, h, platform, folder = SIZES[key]
        for i, fr in enumerate(frames):
            if frames_filter and fr["id"] not in frames_filter:
                continue
            if platform not in fr.get("platforms", ["android", "ios"]):
                continue
            shoot(chrome, f"{base}?f={i}&s={key}", (w, h), out / folder / f"{fr['id']}.png")
    if cfg.get("featureGraphic") and not frames_filter and not sizes_filter:
        shoot(chrome, f"{base}?f=fg&s=fg", (1024, 500), out / "play" / "feature_graphic_1024x500.png")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="copy the kit templates into a folder")
    p_init.add_argument("kit", type=Path)
    p_render = sub.add_parser("render", help="render frames")
    p_render.add_argument("kit", type=Path)
    p_render.add_argument("--frames", default="", help="comma-separated frame ids (default: all)")
    p_render.add_argument("--sizes", default="", help="comma-separated size keys (default: frames.json sizes)")
    p_render.add_argument("--project", type=Path, default=Path("."), help="app folder with node_modules (for Ionicons)")
    p_render.add_argument("--chrome", help="path to Chrome/Chromium/Edge")
    args = parser.parse_args()
    if args.cmd == "init":
        return init(args.kit)
    return render(args.kit, {f for f in args.frames.split(",") if f}, [s for s in args.sizes.split(",") if s],
                  args.project.resolve(), args.chrome)


if __name__ == "__main__":
    raise SystemExit(main())
