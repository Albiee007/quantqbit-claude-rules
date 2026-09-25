#!/usr/bin/env python3
"""Render store screenshots and the Play feature graphic from an HTML mockup kit.

  init   copy the kit templates into a working folder (refuses to overwrite)
         --style classic      self-contained frames (default)
         --style continuous   one strip across all frames (ribbons, coins, phones cross edges)
  render validate frames.json, then shoot every frame x size with headless Chrome/Edge,
         flatten to RGB, and assert exact dimensions and < 8 MB per file

Kit folder after init:
  content (yours to edit): app.css  screens.js  demo-data.js  frames.json  [custom-objects.js]
  engine (refreshed from the harness on every render): frame.html  objects.js
Output: <kit>/<frames.json "out">/play/{phone,tablet7,tablet10}/  ios/{6.9,6.5,ipad13}/
        play/feature_graphic_1024x500.png

Usage:
  python render_frames.py init   store-assets/mockup-kit [--style continuous]
  python render_frames.py render store-assets/mockup-kit [--frames 01-home,03-x] [--sizes play-phone,ios-69]
                                 [--project .] [--chrome PATH] [--check-only]
Needs Pillow (pip install pillow) and Chrome, Chromium or Edge. Sizes follow
store-submission-precheck/references/store-specs.md; the continuous style is documented
in references/continuous-panorama.md.
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
CONTENT_FILES = {  # template -> kit name; copied once by init, then owned by the project
    "app.css": "app.css",
    "screens.example.js": "screens.js",
    "demo-data.example.js": "demo-data.js",
}
CONFIGS = {"classic": "frames.example.json", "continuous": "frames.continuous.example.json"}
ENGINE_FILES = ("frame.html", "objects.js")  # refreshed on every render so kits get harness fixes
BUILTIN_OBJECTS = {"ribbon", "coin", "chip", "receipt", "calendar", "toast", "card", "phone", "brand", "image", "text", "html"}
TEXT_OBJECTS = {"toast", "card", "brand", "text"}  # readable text never crosses a frame edge
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


def init(kit: Path, style: str) -> int:
    kit.mkdir(parents=True, exist_ok=True)
    files = dict(CONTENT_FILES)
    files[CONFIGS[style]] = "frames.json"
    for src, dest in files.items():
        target = kit / dest
        if target.exists():
            print(f"skip {target} (exists)")
            continue
        shutil.copyfile(TEMPLATES / src, target)
        print(f"wrote {target}")
    for name in ENGINE_FILES:
        shutil.copyfile(TEMPLATES / name, kit / name)
    (kit / "assets").mkdir(exist_ok=True)
    print(f"style: {style}. Next: edit app.css tokens, screens.js, demo-data.js and frames.json, then run render")
    return 0


def validate(cfg: dict, kit: Path, project: Path) -> list[str]:
    """Guardrails for the continuous style. Returns errors; prints warnings."""
    errors: list[str] = []
    frames = cfg.get("frames") or []
    n = len(frames)
    if n > 10:
        errors.append(f"{n} frames; the App Store allows at most 10")
    elif n > 8:
        print(f"WARN  {n} frames; Google Play shows at most 8 per device type")
    if cfg.get("layout", "classic") != "continuous":
        for i, fr in enumerate(frames):
            if not fr.get("screen"):
                errors.append(f"frame {i + 1} ({fr.get('id')}): classic frames need a screen")
        return errors

    brand_only = [i for i, fr in enumerate(frames) if not fr.get("screen")]
    for i in brand_only:
        fr = frames[i]
        if "ios" in fr.get("platforms", ["android", "ios"]):
            errors.append(f"frame {i + 1} ({fr.get('id')}): a frame without app UI must be \"platforms\": [\"android\"] "
                          "(App Store 2.3.3 requires every screenshot to show the app in use)")
        if i == 0:
            errors.append("frame 1 must show the app; move the brand-only frame later (ideally last)")
    if len(brand_only) > 1:
        errors.append(f"{len(brand_only)} brand-only frames; use at most one")
    for i, fr in enumerate(frames):
        dx = (fr.get("device") or {}).get("x")
        if dx is not None and not 0.2 <= dx <= 0.8:
            errors.append(f"frame {i + 1} ({fr.get('id')}): device.x {dx} pushes the primary phone out of its frame "
                          "(keep 0.2-0.8; use a \"phone\" object for a phone that straddles frames)")

    restricted = {i for i, fr in enumerate(frames) if set(fr.get("platforms", ["android", "ios"])) != {"android", "ios"}}
    custom = (kit / "custom-objects.js").is_file()
    for k, o in enumerate(cfg.get("objects") or []):
        t = o.get("type")
        where = f"object {k + 1} ({t})"
        if t not in BUILTIN_OBJECTS:
            if custom:
                print(f"WARN  {where}: not a built-in type; expecting custom-objects.js to define it")
            else:
                errors.append(f"{where}: unknown type; built-ins are {sorted(BUILTIN_OBJECTS)} (or add custom-objects.js)")
                continue
        if t == "ribbon":
            pts = o.get("points") or []
            if len(pts) < 2:
                errors.append(f"{where}: needs at least 2 points")
            if any(not -0.5 <= p[0] <= n + 0.5 for p in pts):
                errors.append(f"{where}: a point lies far outside the strip (x must be within -0.5..{n + 0.5})")
            continue
        x, w = o.get("x"), o.get("w", 0.3)
        if x is None or not 0 <= x <= n:
            errors.append(f"{where}: x must be within 0..{n} (frame units)")
            continue
        lo, hi = x - w / 2, x + w / 2
        first, last = int(max(lo, 0)), int(min(hi, n - 1e-9))
        if t in TEXT_OBJECTS and first != last and not o.get("allowCross"):
            errors.append(f"{where}: text crosses the edge between frames {first + 1} and {last + 1} "
                          f"(spans {lo:.2f}-{hi:.2f}); keep text inside one frame or set \"allowCross\": true")
        if first != last and ({first, last} & restricted):
            print(f"WARN  {where}: crosses into a frame that is skipped on one platform; it will look cut on that platform")
        if t == "image":
            if not str(o.get("license", "")).strip():
                errors.append(f"{where}: image objects need a \"license\" note (who owns the photo, model release)")
            src = o.get("src", "")
            found = next((p for p in (kit / src, project / src) if src and p.is_file()), None)
            if not found:
                errors.append(f"{where}: image not found: {src} (relative to the kit or --project)")
            else:
                dest = kit / "assets" / found.name
                if found.resolve() != dest.resolve():
                    dest.parent.mkdir(exist_ok=True)
                    shutil.copyfile(found, dest)
                o["src"] = f"assets/{found.name}"
    return errors


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


def render(kit: Path, frames_filter: set[str], sizes_filter: list[str], project: Path, chrome_arg: str | None,
           check_only: bool) -> int:
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
    errors = validate(cfg, kit, project)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"frames.json OK ({cfg.get('layout', 'classic')}, {len(frames)} frames)")
    if check_only:
        return 0

    for name in ENGINE_FILES:
        shutil.copyfile(TEMPLATES / name, kit / name)
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
    p_init.add_argument("--style", choices=sorted(CONFIGS), default="classic")
    p_render = sub.add_parser("render", help="validate and render frames")
    p_render.add_argument("kit", type=Path)
    p_render.add_argument("--frames", default="", help="comma-separated frame ids (default: all)")
    p_render.add_argument("--sizes", default="", help="comma-separated size keys (default: frames.json sizes)")
    p_render.add_argument("--project", type=Path, default=Path("."), help="app folder with node_modules (Ionicons) and photos")
    p_render.add_argument("--chrome", help="path to Chrome/Chromium/Edge")
    p_render.add_argument("--check-only", action="store_true", help="validate frames.json without rendering")
    args = parser.parse_args()
    if args.cmd == "init":
        return init(args.kit, args.style)
    return render(args.kit, {f for f in args.frames.split(",") if f}, [s for s in args.sizes.split(",") if s],
                  args.project.resolve(), args.chrome, args.check_only)


if __name__ == "__main__":
    raise SystemExit(main())
