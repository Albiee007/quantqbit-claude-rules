#!/usr/bin/env python3
"""Render store screenshots and the Play feature graphic from an HTML mockup kit.

  init     copy the kit templates into a working folder (never overwrites). Refuses when the
           project already has a kit, so every run reuses one kit (--new to override)
           --style classic      self-contained frames (default)
           --style continuous   one strip across all frames (ribbons, coins, phones cross edges)
  render   validate frames.json, then shoot frame x size with headless Chrome/Edge, flatten to
           RGB, and assert exact dimensions and < 8 MB per file
           --all  the release set in one run: every size and the feature graphic, stale PNGs
                  removed, contact sheet (+ strips and seam report for continuous), a re-check
                  of every file, the caption contrast check and check_store_assets.py
  contrast caption contrast only: headline text needs 3:1 (large text), every other caption 4.5:1

Kit folder:
  content (yours, commit it): app.css  screens.js  demo-data.js  frames.json  [custom-objects.js]
                              [assets/ for your own photos]
  .build/  engine + generated files, rewritten on every render and ignored by git (render.lock
           in it stops two renders sharing a kit)
  out/     renders (frames.json "out", or --out); the kit's .gitignore keeps them out of git
Output: <out>/play/{phone,tablet7,tablet10}/  ios/{6.9,6.5,ipad13}/  play/feature_graphic_1024x500.png
        --all adds contact-sheet.png and, for continuous sets, strip-android.png / strip-ios.png

Usage:
  python render_frames.py init     store-assets/mockup-kit [--style continuous] [--project .]
  python render_frames.py render   store-assets/mockup-kit [--frames 01-home,03-x] [--sizes play-phone,ios-69]
  python render_frames.py render   store-assets/mockup-kit --all [--out DIR] [--no-contrast]
  python render_frames.py contrast store-assets/mockup-kit
  common: [--project .] [--chrome PATH] [--jobs N]; render also takes [--check-only]
Needs Pillow (pip install pillow) and Chrome, Chromium or Edge. Sizes follow
store-submission-precheck/references/store-specs.md; the continuous style is documented
in references/continuous-panorama.md.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
STORE_CHECK = HERE.parent.parent / "store-submission-precheck" / "scripts" / "check_store_assets.py"
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
MAX_BYTES = 8 * 1024 * 1024
CONTENT_FILES = {  # template -> kit name; copied once by init, then owned by the project
    "app.css": "app.css",
    "screens.example.js": "screens.js",
    "demo-data.example.js": "demo-data.js",
}
CONFIGS = {"classic": "frames.example.json", "continuous": "frames.continuous.example.json"}
BUILD = ".build"
ENGINE_FILES = ("frame.html", "objects.js")  # copied into .build/ on every render so kits get harness fixes
LEGACY_FILES = ("frame.html", "objects.js", "frames.generated.js", "icons.generated.js", "assets/Ionicons.ttf")
LOCK_STALE_S = 2 * 3600
SKIP_DIRS = {"node_modules", ".git", BUILD, "android", "ios", "build", "dist", ".expo", "Pods", ".venv", "venv", "__pycache__"}
BUILTIN_OBJECTS = {"ribbon", "coin", "chip", "receipt", "calendar", "toast", "card", "phone", "brand", "image", "text", "html"}
TEXT_OBJECTS = {"toast", "card", "brand", "text"}  # readable text never crosses a frame edge
MIN_CONTRAST = {"head": 3.0, "sub": 4.5}  # WCAG 2.2: headlines are large text
ICON_SOURCES = [
    ("node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/glyphmaps/Ionicons.json"),
    ("node_modules/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/react-native-vector-icons/glyphmaps/Ionicons.json"),
]


class RenderError(Exception):
    pass


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


def find_kits(root: Path, max_depth: int = 6) -> list[Path]:
    """Folders under root that hold a kit (frames.json next to screens.js)."""
    kits = []
    root = root.resolve()
    for d, dirs, files in os.walk(root):
        depth = len(Path(d).relative_to(root).parts)
        dirs[:] = [] if depth >= max_depth else sorted(x for x in dirs if x not in SKIP_DIRS)
        if "frames.json" in files and "screens.js" in files:
            kits.append(Path(d))
    return kits


def gitignore_text(kit: Path, out: Path) -> str:
    lines = ["# render_frames.py: the build folder and the renders are regenerated from this kit.", f"{BUILD}/"]
    try:
        lines.append(out.resolve().relative_to(kit.resolve()).as_posix() + "/")
    except ValueError:
        pass
    return "\n".join(lines) + "\n"


def init(kit: Path, style: str, project: Path, new: bool) -> int:
    others = [k for k in find_kits(project) if k.resolve() != kit.resolve()]
    if others and not new:
        print("this project already has a mockup kit; reuse it instead of starting a second one:", file=sys.stderr)
        for k in others:
            print(f"  python render_frames.py render {k}", file=sys.stderr)
        print("(pass --new only when the owner wants a separate kit)", file=sys.stderr)
        return 1
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
    ignore = kit / ".gitignore"
    if not ignore.exists():
        ignore.write_text(gitignore_text(kit, kit / "out"), encoding="utf-8")
        print(f"wrote {ignore}")
    print(f"style: {style}. Next: edit app.css tokens, screens.js, demo-data.js and frames.json, then run render")
    return 0


def validate(cfg: dict, kit: Path, project: Path) -> tuple[list[str], dict[int, Path]]:
    """Guardrails for the continuous style. Returns errors and the resolved photo paths; prints warnings."""
    errors: list[str] = []
    images: dict[int, Path] = {}
    frames = cfg.get("frames") or []
    n = len(frames)
    if n > 10:
        errors.append(f"{n} frames; the App Store allows at most 10")
    elif n > 8:
        print(f"WARN  {n} frames; Google Play shows at most 8 per device type")
    ids = [fr.get("id") for fr in frames]
    for dup in sorted({i for i in ids if ids.count(i) > 1}, key=str):
        errors.append(f"frame id {dup!r} is used more than once")
    if cfg.get("layout", "classic") != "continuous":
        for i, fr in enumerate(frames):
            if not fr.get("screen"):
                errors.append(f"frame {i + 1} ({fr.get('id')}): classic frames need a screen")
        return errors, images

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
                images[k] = found
    return errors, images


class KitLock:
    """One render per kit at a time: two agents rendering into one kit overwrite each other's files."""

    def __init__(self, kit: Path) -> None:
        self.path = kit / BUILD / "render.lock"

    def __enter__(self) -> "KitLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir()
        except FileExistsError:
            age = time.time() - self.path.stat().st_mtime
            if age < LOCK_STALE_S:
                owner = self.path / "owner"
                who = owner.read_text(encoding="utf-8").strip() if owner.is_file() else "unknown"
                raise SystemExit(f"another render is using this kit ({who}, started {int(age // 60)} min ago); wait for it. "
                                 f"If none is running, delete {self.path}")
            shutil.rmtree(self.path, ignore_errors=True)
            self.path.mkdir()
        (self.path / "owner").write_text(f"pid {os.getpid()} on {socket.gethostname()}\n", encoding="utf-8")
        return self

    def __exit__(self, *exc: object) -> None:
        shutil.rmtree(self.path, ignore_errors=True)


def write_icons(build: Path, family: str, project: Path) -> None:
    out = build / "icons.generated.js"
    if family != "ionicons":
        out.write_text("window.ION = null;\n", encoding="utf-8")
        return
    for start in [project, *project.parents]:
        for ttf, glyphs in ICON_SOURCES:
            if (start / ttf).is_file() and (start / glyphs).is_file():
                shutil.copyfile(start / ttf, build / "Ionicons.ttf")
                glyph_map = json.loads((start / glyphs).read_text(encoding="utf-8"))
                out.write_text("window.ION = " + json.dumps(glyph_map) + ";\n"
                               "document.head.insertAdjacentHTML('beforeend', '<style>@font-face { font-family: Ionicons; "
                               "src: url(.build/Ionicons.ttf) format(\"truetype\"); }</style>');\n", encoding="utf-8")
                print(f"icons: Ionicons from {start / ttf}")
                return
    raise SystemExit("frames.json asks for ionicons but no Ionicons.ttf + glyphmap was found under node_modules; "
                     "pass --project <app dir> or set \"icons\": \"material\"")


def prepare_build(kit: Path, cfg: dict, images: dict[int, Path], project: Path) -> Path:
    build = kit / BUILD
    build.mkdir(exist_ok=True)
    (build / ".gitignore").write_text("# regenerated by render_frames.py on every render\n*\n", encoding="utf-8")
    for name in ENGINE_FILES:
        shutil.copyfile(TEMPLATES / name, build / name)
    generated = json.loads(json.dumps(cfg))
    generated["sizes"] = {k: list(v[:3]) for k, v in SIZES.items()}
    for k, found in images.items():
        try:
            src = found.resolve().relative_to(kit.resolve()).as_posix()
        except ValueError:  # a project photo outside the kit: copy it into the build, not the kit
            (build / "assets").mkdir(exist_ok=True)
            shutil.copyfile(found, build / "assets" / found.name)
            src = f"{BUILD}/assets/{found.name}"
        generated["objects"][k]["src"] = src
    (build / "frames.generated.js").write_text("window.FRAMES = " + json.dumps(generated, ensure_ascii=False) + ";\n", encoding="utf-8")
    write_icons(build, cfg.get("icons", "material"), project)
    return build


def chrome_cmd(chrome: str, profile: str, size: tuple[int, int]) -> list[str]:
    return [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--user-data-dir={profile}", "--allow-file-access-from-files", "--no-first-run",
            f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=8000"]


def shoot(chrome: str, url: str, size: tuple[int, int], dest: Path, quiet: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.png"
        r = subprocess.run(chrome_cmd(chrome, str(Path(tmp) / "profile"), size) + [f"--screenshot={raw}", url],
                           capture_output=True)
        if r.returncode != 0 or not raw.is_file():
            raise RenderError(f"{dest.name}: Chrome failed ({r.returncode}): {r.stderr.decode(errors='replace')[-300:]}")
        with Image.open(raw) as shot:
            img = shot.convert("RGB")
    if img.size != size:
        raise RenderError(f"{dest.name}: got {img.size}, want {size}")
    img.save(dest, optimize=True)
    if dest.stat().st_size >= MAX_BYTES:
        raise RenderError(f"{dest.name} is 8 MB or more")
    if not quiet:
        print(f"ok  {dest}  {size[0]}x{size[1]}")


def dump_dom(chrome: str, url: str, size: tuple[int, int]) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(chrome_cmd(chrome, str(Path(tmp) / "profile"), size) + ["--dump-dom", url], capture_output=True)
    if r.returncode != 0:
        raise RenderError(f"Chrome --dump-dom failed ({r.returncode}): {r.stderr.decode(errors='replace')[-300:]}")
    return r.stdout.decode("utf-8", errors="replace")


def run_all(jobs: int, tasks: list) -> None:
    """Run callables, jobs at a time; re-raise the first failure after all finish."""
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(t) for t in tasks]
    for f in futures:
        f.result()


# ------------------------------------------------------------------ contrast

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


def run_contrast(bg: Image.Image, run: dict) -> float | None:
    """The 5th-percentile contrast between a text run's colour and the pixels behind it."""
    col = parse_color(run["color"])
    if col is None:
        return None
    r, g, b, a = col
    ratios = []
    for left, top, right, bottom in run["rects"]:
        box = bg.crop((int(left), int(top), int(right + 0.999), int(bottom + 0.999)))
        step = max(1, int((box.width * box.height / 4000) ** 0.5))
        px = box.load()
        for y in range(0, box.height, step):
            for x in range(0, box.width, step):
                p = px[x, y]
                text = (a * r + (1 - a) * p[0], a * g + (1 - a) * p[1], a * b + (1 - a) * p[2])
                l1, l2 = luminance(text), luminance(p)
                ratios.append((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05))
    if not ratios:
        return None
    ratios.sort()
    return ratios[len(ratios) // 20]


def contrast_targets(cfg: dict, sizes: list[str]) -> list[tuple[str, str, str]]:
    """(label, f param, size key): every frame at the first size per platform, plus the feature graphic."""
    targets = []
    seen = set()
    for key in sizes:
        platform = SIZES[key][2]
        if platform in seen:
            continue
        seen.add(platform)
        for i, fr in enumerate(cfg.get("frames") or []):
            if platform in fr.get("platforms", ["android", "ios"]):
                targets.append((f"{fr['id']} @ {key}", str(i), key))
    if cfg.get("featureGraphic"):
        targets.append(("feature graphic", "fg", "fg"))
    return targets


def check_contrast(chrome: str, base: str, cfg: dict, sizes: list[str], jobs: int) -> int:
    targets = contrast_targets(cfg, sizes)
    results: dict[str, list] = {}

    def one(label: str, f: str, key: str) -> None:
        w, h = SIZES[key][:2]
        dom = dump_dom(chrome, f"{base}?f={f}&s={key}&probe=1", (w, h))
        m = re.search(r'<pre id="probe"[^>]*>(.*?)</pre>', dom, re.S)
        if not m:
            raise RenderError(f"{label}: the contrast probe returned nothing (is .build/frame.html current?)")
        probe = json.loads(html.unescape(m.group(1)))
        with tempfile.TemporaryDirectory() as tmp:
            shot = Path(tmp) / "bg.png"
            shoot(chrome, f"{base}?f={f}&s={key}&nocap=1", (w, h), shot, quiet=True)
            with Image.open(shot) as im:
                bg = im.convert("RGB")
        results[label] = [(run, run_contrast(bg, run)) for run in probe["runs"]]

    run_all(jobs, [lambda t=t: one(*t) for t in targets])
    fails = 0
    print("contrast (5th-percentile ratio of caption text against its background; headline >= 3:1, other text >= 4.5:1)")
    for label, *_ in targets:
        worst: dict[str, float] = {}
        for run, ratio in results.get(label, []):
            if ratio is None:
                print(f"  WARN  {label}: colour {run['color']!r} of {run['text']!r} not understood; check it by eye")
                continue
            worst[run["kind"]] = min(worst.get(run["kind"], 99.0), ratio)
            if ratio < MIN_CONTRAST[run["kind"]]:
                fails += 1
                print(f"  FAIL  {label}: {run['kind']} {run['text']!r} ({run['color']}) {ratio:.2f}:1 "
                      f"< {MIN_CONTRAST[run['kind']]}:1")
        summary = "  ".join(f"{k} {v:.1f}:1" for k, v in sorted(worst.items())) or "no caption text"
        print(f"  {'ok' if all(v >= MIN_CONTRAST[k] for k, v in worst.items()) else '--'}    {label}: {summary}")
    return fails


# ------------------------------------------------------------------ render

def legacy_note(kit: Path) -> None:
    old = [n for n in LEGACY_FILES if (kit / n).is_file()]
    if old:
        print(f"NOTE  unused files from an older harness in the kit (renders now run from {BUILD}/): {', '.join(old)}; "
              "delete them unless you edited them on purpose")


def prune_stale(out: Path, cfg: dict, sizes: list[str]) -> None:
    """--all: drop PNGs in the rendered slots whose frame id is gone (a renamed or removed frame)."""
    expected: dict[str, set[str]] = {}
    for key in sizes:
        platform, folder = SIZES[key][2], SIZES[key][3]
        ids = {f"{fr['id']}.png" for fr in cfg["frames"] if platform in fr.get("platforms", ["android", "ios"])}
        expected.setdefault(folder, set()).update(ids)
    for folder, keep in expected.items():
        for p in sorted((out / folder).glob("*.png")):
            if p.name not in keep:
                p.unlink()
                print(f"removed stale {p}")


def verify_outputs(out: Path, cfg: dict, sizes: list[str]) -> int:
    allowed: dict[str, set] = {}
    for key in sizes:
        allowed.setdefault(SIZES[key][3], set()).add(SIZES[key][:2])
    problems = 0
    count = 0
    for folder, dims in allowed.items():
        for p in sorted((out / folder).glob("*.png")):
            count += 1
            with Image.open(p) as im:
                if im.size not in dims or im.mode != "RGB" or p.stat().st_size >= MAX_BYTES:
                    problems += 1
                    print(f"  FAIL  {p}: {im.size[0]}x{im.size[1]} {im.mode} {p.stat().st_size} bytes")
    fg = out / "play" / "feature_graphic_1024x500.png"
    if cfg.get("featureGraphic"):
        count += 1
        if not fg.is_file():
            problems += 1
            print(f"  FAIL  {fg} missing")
    print(f"verify: {count} files, {problems} problem(s)")
    return problems


def contact_sheets(out: Path, cfg: dict, sizes: list[str]) -> list[Path]:
    sheet_script = HERE / "contact_sheet.py"
    folders = list(dict.fromkeys(SIZES[k][3] for k in sizes))
    main = "play/phone" if "play/phone" in folders else folders[0]
    made = []
    cmd = [sys.executable, str(sheet_script), str(out / main), "-o", str(out / "contact-sheet.png")]
    fg = out / "play" / "feature_graphic_1024x500.png"
    if fg.is_file():
        cmd += ["--feature", str(fg)]
    subprocess.run(cmd, check=True)
    made.append(out / "contact-sheet.png")
    if cfg.get("layout") == "continuous":
        for platform in ("android", "ios"):
            first = next((SIZES[k][3] for k in sizes if SIZES[k][2] == platform), None)
            if first:
                dest = out / f"strip-{platform}.png"
                subprocess.run([sys.executable, str(sheet_script), str(out / first), "--strip", "--check-seams",
                                "-o", str(dest)], check=True)
                made.append(dest)
    return made


def load_cfg(kit: Path) -> dict | None:
    cfg_path = kit / "frames.json"
    if not cfg_path.is_file():
        print(f"{cfg_path} not found; run: python render_frames.py init {kit}", file=sys.stderr)
        return None
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def render(args: argparse.Namespace) -> int:
    kit: Path = args.kit
    cfg = load_cfg(kit)
    if cfg is None:
        return 2
    frames_filter = {f for f in args.frames.split(",") if f}
    sizes_filter = [s for s in args.sizes.split(",") if s]
    if args.all and (frames_filter or sizes_filter):
        print("--all renders the whole set; drop --frames/--sizes (or drop --all for a quick look)", file=sys.stderr)
        return 2
    sizes = sizes_filter or cfg.get("sizes") or ["play-phone", "ios-69"]
    unknown = [s for s in sizes if s not in SIZES or s == "fg"]
    if unknown:
        print(f"unknown size key(s): {unknown}; choose from {[k for k in SIZES if k != 'fg']}", file=sys.stderr)
        return 2
    frames = cfg.get("frames") or []
    if not frames:
        print("frames.json has no frames", file=sys.stderr)
        return 2
    missing = sorted(frames_filter - {fr.get("id") for fr in frames})
    if missing:
        print(f"unknown frame id(s): {missing}", file=sys.stderr)
        return 2
    errors, images = validate(cfg, kit, args.project)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"frames.json OK ({cfg.get('layout', 'classic')}, {len(frames)} frames)")
    if args.check_only:
        return 0

    out = args.out or kit / cfg.get("out", "out")
    legacy_note(kit)
    if not (kit / ".gitignore").exists():
        (kit / ".gitignore").write_text(gitignore_text(kit, out), encoding="utf-8")
        print(f"wrote {kit / '.gitignore'} (keeps {BUILD}/ and the renders out of git)")
    with KitLock(kit):
        chrome = find_chrome(args.chrome)
        build = prepare_build(kit, cfg, images, args.project)
        base = (build / "frame.html").resolve().as_uri()
        tasks = []
        for key in sizes:
            w, h, platform, folder = SIZES[key]
            for i, fr in enumerate(frames):
                if frames_filter and fr["id"] not in frames_filter:
                    continue
                if platform not in fr.get("platforms", ["android", "ios"]):
                    continue
                tasks.append(lambda i=i, key=key, dest=out / folder / f"{fr['id']}.png", size=(w, h):
                             shoot(chrome, f"{base}?f={i}&s={key}", size, dest))
        if cfg.get("featureGraphic") and not frames_filter and not sizes_filter:
            tasks.append(lambda: shoot(chrome, f"{base}?f=fg&s=fg", (1024, 500), out / "play" / "feature_graphic_1024x500.png"))
        try:
            run_all(args.jobs, tasks)
            if not args.all:
                return 0
            prune_stale(out, cfg, sizes)
            sheets = contact_sheets(out, cfg, sizes)
            problems = verify_outputs(out, cfg, sizes)
            low = 0 if args.no_contrast else check_contrast(chrome, base, cfg, sizes, args.jobs)
        except RenderError as e:
            print(f"render failed: {e}", file=sys.stderr)
            return 1
    store_rc = 0
    if STORE_CHECK.is_file():
        store_rc = subprocess.run([sys.executable, str(STORE_CHECK), str(out)]).returncode
    print(f"\nrender --all: {len(tasks)} images -> {out}; sheets: {', '.join(p.name for p in sheets)}; "
          f"verify {'OK' if not problems else 'FAIL'}; contrast "
          f"{'skipped' if args.no_contrast else 'OK' if not low else f'{low} FAIL'}; "
          f"store check {'OK' if store_rc == 0 else 'FAIL' if STORE_CHECK.is_file() else 'not installed'}")
    return 1 if problems or low or store_rc else 0


def contrast_cmd(args: argparse.Namespace) -> int:
    cfg = load_cfg(args.kit)
    if cfg is None:
        return 2
    sizes = [s for s in args.sizes.split(",") if s] or cfg.get("sizes") or ["play-phone", "ios-69"]
    errors, images = validate(cfg, args.kit, args.project)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    with KitLock(args.kit):
        chrome = find_chrome(args.chrome)
        build = prepare_build(args.kit, cfg, images, args.project)
        try:
            low = check_contrast(chrome, (build / "frame.html").resolve().as_uri(), cfg, sizes, args.jobs)
        except RenderError as e:
            print(f"contrast check failed: {e}", file=sys.stderr)
            return 1
    return 1 if low else 0


def main() -> int:
    # Line-buffered so our lines stay in order with the child scripts' output; caption text may not
    # fit a Windows console code page.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(line_buffering=True, errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="copy the kit templates into a folder")
    p_init.add_argument("kit", type=Path)
    p_init.add_argument("--style", choices=sorted(CONFIGS), default="classic")
    p_init.add_argument("--project", type=Path, default=Path("."), help="project folder searched for an existing kit")
    p_init.add_argument("--new", action="store_true", help="create a kit even though the project already has one")
    jobs = min(4, os.cpu_count() or 2)
    for name, text in (("render", "validate and render frames"), ("contrast", "caption contrast check only")):
        p = sub.add_parser(name, help=text)
        p.add_argument("kit", type=Path)
        p.add_argument("--sizes", default="", help="comma-separated size keys (default: frames.json sizes)")
        p.add_argument("--project", type=Path, default=Path("."), help="app folder with node_modules (Ionicons) and photos")
        p.add_argument("--chrome", help="path to Chrome/Chromium/Edge")
        p.add_argument("--jobs", type=int, default=jobs, help=f"parallel Chrome runs (default {jobs})")
        if name == "render":
            p.add_argument("--frames", default="", help="comma-separated frame ids (default: all)")
            p.add_argument("--out", type=Path, help="output folder (default: the kit's frames.json \"out\")")
            p.add_argument("--all", action="store_true", help="release set: every size, sheets, verify, contrast, store check")
            p.add_argument("--no-contrast", action="store_true", help="with --all: skip the contrast check")
            p.add_argument("--check-only", action="store_true", help="validate frames.json without rendering")
    args = parser.parse_args()
    if args.cmd == "init":
        return init(args.kit, args.style, args.project.resolve(), args.new)
    args.project = args.project.resolve()
    return render(args) if args.cmd == "render" else contrast_cmd(args)


if __name__ == "__main__":
    raise SystemExit(main())
