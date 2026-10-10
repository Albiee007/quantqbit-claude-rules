#!/usr/bin/env python3
"""Render store screenshots and the Play feature graphic from an HTML mockup kit.

Modes (decided by frames.json and the command):
  legacy      a 1.6 kit (frames.json without "format"): renders exactly as 1.6 did, through the
              frozen engine in templates/legacy-1.6/, with a migration warning. Nothing else about
              the kit changes.
  preview     a draft of a format-2 kit with any store concept (--concept) or the selected one, no
              approval needed. Builds in a temporary copy of the kit and writes only to --out
              (default <kit>/.preview/<run id>/, which git ignores).
  production  `render` on a format-2 kit. Needs the owner-approved direction and store concept
              (brand/direction.json, brand/approvals.json); otherwise it refuses and names what is
              missing. Renders are staged, checked, then published into the kit's out/ folder under
              a lock; a failed run leaves the previous renders untouched. Each run writes an
              immutable manifest to brand/runs/store/<run id>.json.

Commands:
  init     copy the format-2 kit templates into a working folder (never overwrites). Refuses when
           the project already has a kit (--new to override)
  render   validate frames.json, then shoot frame x size with headless Chrome/Edge, flatten to RGB,
           and assert exact dimensions and < 8 MB per file
           --all  the release set: every size and the feature graphic, owned stale PNGs removed,
                  contact sheet (+ strips and seam report for continuous), a re-check of every
                  file, caption contrast, font coverage and check_store_assets.py
  preview  render a draft (format 2) without touching the kit or its out/
  contrast caption contrast only

Kit folder:
  content (yours, commit it): app.css  screens.js  demo-data.js  frames.json  [custom-objects.js] [assets/]
  .build/  engine + generated files, rewritten on every render and ignored by git
  out/     renders; the kit's .gitignore keeps them out of git. out/.render-manifest.json lists the
           files a render published, so only those are ever pruned

Usage:
  python render_frames.py init     store-assets/mockup-kit [--style continuous] [--project .]
  python render_frames.py render   store-assets/mockup-kit [--frames 01-home] [--sizes play-phone] [--all]
  python render_frames.py preview  store-assets/mockup-kit [--concept brand/concepts/store/<run>/<id>.json]
                                   [--frames ...] [--sizes ...] [--out DIR]
  python render_frames.py contrast store-assets/mockup-kit
  common: [--project <app dir>] [--chrome PATH] [--jobs N]; render also takes [--check-only] [--out DIR]
Needs Pillow and Chrome, Chromium or Edge. Sizes follow store-submission-precheck/references/store-specs.md.
Exit codes: 0 done (the report may say REVIEW REQUIRED), 1 a check or gate failed, 2 bad arguments,
a missing dependency or an operational failure (browser, lock).
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    import harnesslib
    from harnesslib import browser, pagecheck, schema
    from harnesslib import contrast as con
    from harnesslib import direction as dl
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import (DirLock, InputError, OperationalError, Publisher, UsageError, canonical, run_id,
                                   resolve_inside, script_json, self_ignoring_dir, sha256_file, sha256_text)
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)
try:
    from PIL import Image
    from harnesslib import imaging
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
LEGACY_ENGINE = TEMPLATES / "legacy-1.6"
MEDIA = Path(harnesslib.__file__).resolve().parent.parent / "media"
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
FG_FILE = "play/feature_graphic_1024x500.png"
MAX_BYTES = 8 * 1024 * 1024
CONTENT_FILES = {  # template -> kit name; copied once by init, then owned by the project
    "app.css": "app.css",
    "screens.example.js": "screens.js",
    "demo-data.example.js": "demo-data.js",
}
KIT_CONTENT = ("app.css", "screens.js", "demo-data.js", "frames.json", "custom-objects.js")
CONFIGS = {"classic": "frames.example.json", "continuous": "frames.continuous.example.json"}
BUILD = ".build"
LEGACY_FILES = ("frame.html", "objects.js", "frames.generated.js", "icons.generated.js", "assets/Ionicons.ttf")
SKIP_DIRS = {"node_modules", ".git", BUILD, ".preview", "android", "ios", "build", "dist", ".expo", "Pods", ".venv",
             "venv", "__pycache__"}
LEGACY_OBJECTS = {"ribbon", "coin", "chip", "receipt", "calendar", "toast", "card", "phone", "brand", "image", "text", "html"}
V2_OBJECTS = {"ribbon", "shape", "toast", "card", "phone", "brand", "image", "text", "html"}
PROP_PACKS = {"finance": {"coin", "chip", "receipt", "calendar"}}
TEXT_OBJECTS = {"toast", "card", "brand", "text"}  # readable text never crosses a frame edge
LEGACY_MIN = {"head": 3.0, "sub": 4.5}  # 1.6 rule: every headline treated as large text
FEATURE_LAYOUTS = ("split-device-right", "split-device-left", "centered-type")
ICON_SOURCES = [
    ("node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/@expo/vector-icons/build/vendor/react-native-vector-icons/glyphmaps/Ionicons.json"),
    ("node_modules/react-native-vector-icons/Fonts/Ionicons.ttf",
     "node_modules/react-native-vector-icons/glyphmaps/Ionicons.json"),
]
MATERIAL_SOURCES = ["node_modules/material-symbols/material-symbols-rounded.woff2",
                    "node_modules/@material-symbols/font-400/material-symbols-rounded.woff2"]
PLACEHOLDER = re.compile(r"\bREPLACE\b")


class RenderError(InputError):
    """A rendered file failed its check (exit 1)."""


def run_all(jobs: int, tasks: list) -> None:
    """Run callables, jobs at a time; re-raise the first failure after all finish."""
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = [pool.submit(t) for t in tasks]
    for f in futures:
        f.result()


# ------------------------------------------------------------------ kits

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
    lines = ["# render_frames.py: the build folder, previews and the renders are regenerated from this kit.",
             f"{BUILD}/", ".preview/"]
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
    root = dl.find_project(kit)
    if root is None:
        print("NOTE  no brand/direction.json above this kit yet: the look comes from the approved store concept, so "
              "run the creative-director first. `preview` renders drafts; `render` needs the owner's approvals.")
    print(f"style: {style}. Next: app.css tokens (the app's own UI), screens.js, demo-data.js and frames.json copy, "
          "then preview")
    return 0


def load_cfg(kit: Path) -> dict:
    cfg_path = kit / "frames.json"
    if not cfg_path.is_file():
        raise UsageError(f"{cfg_path} not found; run: python render_frames.py init {kit}")
    from harnesslib.fsutil import load_json
    cfg = load_json(cfg_path)
    if not isinstance(cfg, dict):
        raise InputError(f"{cfg_path}: must be a JSON object")
    if "format" in cfg and cfg["format"] != 2:
        raise InputError(f"{cfg_path}: format {cfg['format']!r} is not supported (2, or none for a 1.6 kit)")
    return cfg


def is_v2(cfg: dict) -> bool:
    return cfg.get("format") == 2


def continuous(cfg: dict) -> bool:
    return (cfg.get("style") if is_v2(cfg) else cfg.get("layout", "classic")) == "continuous"


# ------------------------------------------------------------------ validation

def validate_common(cfg: dict, kit: Path, project: Path, builtin: set[str]) -> tuple[list[str], dict[int, Path]]:
    """Frame-count, id and continuous-style guardrails shared by both formats. Prints warnings."""
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
    if not continuous(cfg):
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
        if t not in builtin:
            if custom:
                print(f"WARN  {where}: not a built-in type; expecting custom-objects.js to define it")
            else:
                errors.append(f"{where}: unknown type; built-ins are {sorted(builtin)} (or add custom-objects.js)")
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
            found = None
            for base in (kit, project):
                try:
                    cand = resolve_inside(base, src, where)
                except InputError:
                    continue
                if cand.is_file():
                    found = cand
                    break
            if not found:
                errors.append(f"{where}: image not found: {src} (relative to the kit or --project, inside them)")
            else:
                images[k] = found
    return errors, images


def validate_v2(cfg: dict, kit: Path, project: Path, ad: dict, mode: str, p: dl.Project) -> tuple[list[str], dict[int, Path]]:
    errs = schema.validate(cfg, schema.load("kit"))
    if errs:
        return [f"frames.json: {e}" for e in errs[:30]], {}
    packs = set(cfg.get("props") or [])
    used = {o.get("type") for o in cfg.get("objects") or []}
    for name, types in PROP_PACKS.items():
        if name not in packs and used & types:
            print(f"NOTE  objects {sorted(used & types)} come from the '{name}' prop pack; loading it "
                  f"(add \"props\": [\"{name}\"] to frames.json to say so)")
            packs.add(name)
    cfg["props"] = sorted(packs)
    builtin = V2_OBJECTS | set().union(*(PROP_PACKS[x] for x in packs)) if packs else set(V2_OBJECTS)
    errors, images = validate_common(cfg, kit, project, builtin)
    layouts, bgs = ad["layouts"], ad["backgrounds"]
    outside: list[str] = []  # choices outside the concept: an owner exception in production, a warning in drafts
    for fr in cfg["frames"]:
        lay = fr.get("layout")
        if lay and lay not in layouts:
            scope = f"store:frame:{fr['id']}:layout={lay}"
            if lay not in ("caption-top", "caption-bottom", "split-left", "split-right", "inset"):
                errors.append(f"frame {fr['id']}: unknown layout {lay!r}")
            elif not dl.exception_approved(p, scope):
                outside.append(f"frame {fr['id']}: layout {lay!r} is outside the approved concept ({', '.join(layouts)}); "
                               f"the owner can allow it: direction.py approve --gate exception --scope \"{scope}\"")
        if fr.get("background") and fr["background"] not in bgs:
            errors.append(f"frame {fr['id']}: background {fr['background']!r} is not in the concept ({', '.join(bgs)})")
    fg = cfg.get("featureGraphic")
    if fg:
        if fg.get("background") and fg["background"] not in bgs:
            errors.append(f"featureGraphic: background {fg['background']!r} is not in the concept ({', '.join(bgs)})")
        lay = fg.get("layout")
        if lay and lay != ad["featureGraphic"]["layout"]:
            scope = f"store:feature-graphic:layout={lay}"
            if not dl.exception_approved(p, scope):
                outside.append(f"featureGraphic: layout {lay!r} differs from the approved concept "
                               f"({ad['featureGraphic']['layout']}); the owner can allow it: direction.py approve "
                               f"--gate exception --scope \"{scope}\"")
        if fg.get("icon"):
            try:
                resolve_inside(project, fg["icon"], "featureGraphic.icon", must_exist=True)
            except InputError as e:
                errors.append(str(e))
    if mode == "production":
        errors += outside
    else:
        for msg in outside:
            print(f"WARN  {msg}")
    copy = [(fr["id"], fr.get(k, "")) for fr in cfg["frames"] for k in ("head", "sub", "kicker")]
    copy += [("featureGraphic", (fg or {}).get(k, "")) for k in ("title", "tagline", "sub")]
    copy += [(f"object {o.get('type')}", str(o.get(k, ""))) for o in cfg.get("objects") or [] for k in ("text", "title", "body", "label", "value")]
    holders = sorted({w for w, text in copy if PLACEHOLDER.search(text or "")})
    if holders:
        msg = f"placeholder copy (REPLACE) in: {', '.join(holders)}"
        if mode == "production":
            errors.append(msg)
        else:
            print(f"WARN  {msg}")
    for uf in cfg.get("uiFonts") or []:
        if uf["source"] == "local" and not uf.get("files"):
            errors.append(f"uiFonts {uf['family']}: local fonts need files")
        for f in uf.get("files") or []:
            try:
                resolve_inside(project, f["path"], f"uiFonts {uf['family']}", must_exist=True)
            except InputError as e:
                errors.append(str(e))
    return errors, images


# ------------------------------------------------------------------ build

def write_icons(build: Path, cfg: dict, project: Path, mode: str) -> list[str]:
    """icons.generated.js (+ the icon font). Returns font load specs for the page to wait on."""
    family = cfg.get("icons", "material")
    out = build / "icons.generated.js"
    if family == "none":
        out.write_text("window.ION = null; window.ICONS_NONE = true;\n", encoding="utf-8")
        return []
    if family == "ionicons":
        for start in [project, *project.parents]:
            for ttf, glyphs in ICON_SOURCES:
                if (start / ttf).is_file() and (start / glyphs).is_file():
                    shutil.copyfile(start / ttf, build / "Ionicons.ttf")
                    glyph_map = json.loads((start / glyphs).read_text(encoding="utf-8"))
                    out.write_text("window.ION = " + json.dumps(glyph_map) + ";\n"
                                   "document.head.insertAdjacentHTML('beforeend', '<style>@font-face { font-family: Ionicons; "
                                   "src: url(.build/Ionicons.ttf) format(\"truetype\"); }</style>');\n", encoding="utf-8")
                    print(f"icons: Ionicons from {start / ttf}")
                    return ["20px Ionicons"]
        raise InputError("frames.json asks for ionicons but no Ionicons.ttf + glyphmap was found under node_modules; "
                         "pass --project <app dir> or set \"icons\": \"material\"")
    out.write_text("window.ION = null;\n", encoding="utf-8")
    if not is_v2(cfg):
        return []
    font = None
    if cfg.get("iconsFont"):
        font = resolve_inside(project, cfg["iconsFont"], "iconsFont", must_exist=True)
    else:
        for start in [project, *project.parents]:
            hit = next((start / s for s in MATERIAL_SOURCES if (start / s).is_file()), None)
            if hit:
                font = hit
                break
    if font is None:
        msg = ("Material Symbols font not found locally (npm package material-symbols, or \"iconsFont\" in frames.json); "
               "format-2 renders never fetch fonts from the network")
        if mode == "production":
            raise InputError(msg)
        print(f"WARN  {msg}; icons show as text in this preview")
        return []
    shutil.copyfile(font, build / ("material-symbols" + font.suffix))
    with open(build / "fonts.generated.css", "a", encoding="utf-8") as f:
        f.write(f"@font-face {{ font-family: 'Material Symbols Rounded'; src: url(material-symbols{font.suffix}); }}\n")
    return ['24px "Material Symbols Rounded"']


def font_css(build: Path, ad: dict, cfg: dict, project: Path) -> list[str]:
    """fonts.generated.css: @font-face for every local caption face and app UI font. Returns extra load specs."""
    fonts_dir = build / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    lines = ["/* generated by render_frames.py from the approved concept and frames.json uiFonts */"]
    for face in ad["faces"]:
        if face.get("source") == "system":
            continue
        name = f"{face['sha256'][:12]}{Path(face['path']).suffix}"
        shutil.copyfile(face["abs"], fonts_dir / name)
        lines.append(f"@font-face {{ font-family: {json.dumps(face['family'])}; src: url(fonts/{name}); "
                     f"font-weight: {face['weight']}; font-style: {face['style']}; }}")
    extra = []
    roots = {}
    for uf in cfg.get("uiFonts") or []:
        fam = uf["family"]
        for f in uf.get("files") or []:
            src = resolve_inside(project, f["path"], "uiFonts", must_exist=True)
            name = f"{sha256_file(src)[:12]}{src.suffix}"
            shutil.copyfile(src, fonts_dir / name)
            style = f.get("style", "normal")
            lines.append(f"@font-face {{ font-family: {json.dumps(fam)}; src: url(fonts/{name}); "
                         f"font-weight: {f['weight']}; font-style: {style}; }}")
            extra.append(f"{'italic ' if style == 'italic' else ''}{f['weight']} 20px {json.dumps(fam)}")
        for plat in ([uf["platform"]] if uf.get("platform") else ["android", "ios"]):
            roots.setdefault(plat, json.dumps(fam))
    if roots:
        lines.append(":root { " + " ".join(f"--font-ui-{k}: {v};" for k, v in roots.items()) + " }")
    (build / "fonts.generated.css").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return extra


def prepare_build(build: Path, kit: Path, cfg: dict, images: dict[int, Path], project: Path,
                  ad: dict | None, mode: str) -> Path:
    build.mkdir(exist_ok=True)
    (build / ".gitignore").write_text("# regenerated by render_frames.py on every render\n*\n", encoding="utf-8")
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
    if ad is None:  # legacy: the frozen 1.6 engine, byte for byte
        for name in ("frame.html", "objects.js"):
            shutil.copyfile(LEGACY_ENGINE / name, build / name)
        (build / "frames.generated.js").write_text("window.FRAMES = " + json.dumps(generated, ensure_ascii=False) + ";\n",
                                                   encoding="utf-8")
        write_icons(build, cfg, project, mode)
        return build
    for name in ("frame.html", "objects.js"):
        shutil.copyfile(TEMPLATES / name, build / name)
    shutil.copyfile(MEDIA / "artdir.js", build / "artdir.js")
    packs = "".join((TEMPLATES / "props" / f"{name}.js").read_text(encoding="utf-8") for name in cfg.get("props") or [])
    (build / "props.generated.js").write_text(packs or "/* no prop packs */\n", encoding="utf-8")
    extra = font_css(build, ad, cfg, project)
    extra += write_icons(build, cfg, project, mode)
    page_ad = json.loads(json.dumps({k: v for k, v in ad.items() if k != "faces" and not k.startswith("_")}))
    page_ad["faces"] = [{k: v for k, v in f.items() if k in ("family", "weight", "style")} for f in ad["faces"]]
    if ad.get("motif"):
        (build / "assets").mkdir(exist_ok=True)
        src = resolve_inside(project_root_of(ad), ad["motif"]["asset"], "motif.asset", must_exist=True)
        shutil.copyfile(src, build / "assets" / "motif.svg")
        page_ad["motif"]["src"] = f"{BUILD}/assets/motif.svg"
    fg = generated.get("featureGraphic")
    if fg and fg.get("icon"):
        (build / "assets").mkdir(exist_ok=True)
        icon = resolve_inside(project, fg["icon"], "featureGraphic.icon", must_exist=True)
        shutil.copyfile(icon, build / "assets" / ("fg-icon" + icon.suffix))
        fg["iconSrc"] = f"{BUILD}/assets/fg-icon{icon.suffix}"
    (build / "frames.generated.js").write_text("window.FRAMES = " + script_json(generated) + ";\n", encoding="utf-8")
    (build / "direction.generated.js").write_text(
        "window.AD = " + script_json(page_ad) + ";\nwindow.EXTRA_FONTS = " + script_json(extra) + ";\n", encoding="utf-8")
    return build


def project_root_of(ad: dict) -> Path:
    return Path(ad["_root"])


def shoot(chrome: str, url: str, size: tuple[int, int], dest: Path, quiet: bool = False) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.png"
        browser.screenshot(chrome, url, size, raw)
        with Image.open(raw) as shot:
            img = shot.convert("RGB")
    if img.size != size:
        raise RenderError(f"{dest.name}: got {img.size}, want {size}")
    img.save(dest, optimize=True)
    if dest.stat().st_size >= MAX_BYTES:
        raise RenderError(f"{dest.name} is 8 MB or more")
    if not quiet:
        print(f"ok  {dest.name}  {size[0]}x{size[1]}")


def probe(chrome: str, base: str, f: str, key: str) -> dict:
    w, h = SIZES[key][:2]
    dom = browser.dump_dom(chrome, f"{base}?f={f}&s={key}&probe=1", (w, h))
    m = re.search(r'<pre id="probe"[^>]*>(.*?)</pre>', dom, re.S)
    if not m:
        raise RenderError(f"f={f} @ {key}: the caption probe returned nothing (a script error in screens.js, "
                          "custom-objects.js or the copy?)")
    return json.loads(html.unescape(m.group(1)))


def backdrop(chrome: str, base: str, f: str, key: str) -> Image.Image:
    w, h = SIZES[key][:2]
    with tempfile.TemporaryDirectory() as tmp:
        shot = Path(tmp) / "bg.png"
        shoot(chrome, f"{base}?f={f}&s={key}&nocap=1", (w, h), shot, quiet=True)
        with Image.open(shot) as im:
            return im.convert("RGB")


# ------------------------------------------------------------------ checks

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


def check_legacy_contrast(chrome: str, base: str, cfg: dict, sizes: list[str], jobs: int) -> list[con.Finding]:
    """1.6 kits: sampled backdrop, 1.6 thresholds (headline 3:1, other caption text 4.5:1)."""
    targets = contrast_targets(cfg, sizes)
    results: dict[str, list[con.Finding]] = {}

    def one(label: str, f: str, key: str) -> None:
        pr = probe(chrome, base, f, key)
        bg = backdrop(chrome, base, f, key)
        out = []
        for run in pr["runs"]:
            p5 = imaging.percentile5(imaging.sample_ratios(bg, run["rects"], run["color"]))
            out.append(con.judge_sampled(label, run["text"], run["kind"], p5, LEGACY_MIN[run["kind"]]))
        results[label] = out

    run_all(jobs, [lambda t=t: one(*t) for t in targets])
    return [f for label, *_ in targets for f in results.get(label, [])]


def check_v2(chrome: str, base: str, cfg: dict, ad: dict, sizes: list[str], jobs: int) -> tuple[list[con.Finding], list[str]]:
    """Format 2: computed contrast where the backdrop colour is known, sampled otherwise; font coverage."""
    targets = contrast_targets(cfg, sizes)
    results: dict[str, tuple[list[con.Finding], list[str]]] = {}

    def one(label: str, f: str, key: str) -> None:
        results[label] = pagecheck.evaluate(probe(chrome, base, f, key), ad, label, lambda: backdrop(chrome, base, f, key))

    run_all(jobs, [lambda t=t: one(*t) for t in targets])
    findings = [x for label, *_ in targets for x in results.get(label, ([], []))[0]]
    fonts = [x for label, *_ in targets for x in results.get(label, ([], []))[1]]
    return findings, fonts


def report_contrast(findings: list[con.Finding], header: str) -> str:
    print(header)
    for f in findings:
        if f.result != con.PASS:
            print(f.line())
    counts = con.summary(findings)
    print(f"  contrast: {counts[con.PASS]} PASS, {counts[con.FAIL]} FAIL, {counts[con.REVIEW]} REVIEW REQUIRED")
    return con.overall(counts)


def verify_outputs(out: Path, cfg: dict, sizes: list[str]) -> int:
    allowed: dict[str, set] = {}
    for key in sizes:
        allowed.setdefault(SIZES[key][3], set()).add(SIZES[key][:2])
    problems = count = 0
    for folder, dims in allowed.items():
        for p in sorted((out / folder).glob("*.png")):
            count += 1
            with Image.open(p) as im:
                if im.size not in dims or im.mode != "RGB" or p.stat().st_size >= MAX_BYTES:
                    problems += 1
                    print(f"  FAIL  {p.name}: {im.size[0]}x{im.size[1]} {im.mode} {p.stat().st_size} bytes")
    if cfg.get("featureGraphic"):
        count += 1
        if not (out / FG_FILE).is_file():
            problems += 1
            print(f"  FAIL  {FG_FILE} missing")
    print(f"verify: {count} files, {problems} problem(s)")
    return problems


def contact_sheets(out: Path, cfg: dict, sizes: list[str]) -> list[Path]:
    sheet_script = HERE / "contact_sheet.py"
    folders = list(dict.fromkeys(SIZES[k][3] for k in sizes))
    main = "play/phone" if "play/phone" in folders else folders[0]
    made = []
    cmd = [sys.executable, str(sheet_script), str(out / main), "-o", str(out / "contact-sheet.png")]
    if (out / FG_FILE).is_file():
        cmd += ["--feature", str(out / FG_FILE)]
    subprocess.run(cmd, check=True, timeout=300)
    made.append(out / "contact-sheet.png")
    if continuous(cfg):
        for platform in ("android", "ios"):
            first = next((SIZES[k][3] for k in sizes if SIZES[k][2] == platform), None)
            if first:
                dest = out / f"strip-{platform}.png"
                subprocess.run([sys.executable, str(sheet_script), str(out / first), "--strip", "--check-seams",
                                "-o", str(dest)], check=True, timeout=300)
                made.append(dest)
    return made


# ------------------------------------------------------------------ render

def plan_sizes(cfg: dict, args: argparse.Namespace) -> tuple[list[str], set[str], list[str]]:
    frames_filter = {f for f in args.frames.split(",") if f}
    sizes_filter = [s for s in args.sizes.split(",") if s]
    if getattr(args, "all", False) and (frames_filter or sizes_filter):
        raise UsageError("--all renders the whole set; drop --frames/--sizes (or drop --all for a quick look)")
    sizes = sizes_filter or cfg.get("sizes") or ["play-phone", "ios-69"]
    unknown = [s for s in sizes if s not in SIZES or s == "fg"]
    if unknown:
        raise UsageError(f"unknown size key(s): {unknown}; choose from {[k for k in SIZES if k != 'fg']}")
    frames = cfg.get("frames") or []
    if not frames:
        raise InputError("frames.json has no frames")
    missing = sorted(frames_filter - {fr.get("id") for fr in frames})
    if missing:
        raise UsageError(f"unknown frame id(s): {missing}")
    return sizes, frames_filter, sizes_filter


def shots(chrome: str, base: str, cfg: dict, sizes: list[str], frames_filter: set[str], with_fg: bool,
          dest_of) -> list:
    tasks = []
    for key in sizes:
        w, h, platform, folder = SIZES[key]
        for i, fr in enumerate(cfg["frames"]):
            if frames_filter and fr["id"] not in frames_filter:
                continue
            if platform not in fr.get("platforms", ["android", "ios"]):
                continue
            rel = f"{folder}/{fr['id']}.png"
            tasks.append(lambda i=i, key=key, rel=rel, size=(w, h): shoot(chrome, f"{base}?f={i}&s={key}", size, dest_of(rel)))
    if cfg.get("featureGraphic") and with_fg:
        tasks.append(lambda: shoot(chrome, f"{base}?f=fg&s=fg", (1024, 500), dest_of(FG_FILE)))
    return tasks


def resolve_v2(kit: Path, args: argparse.Namespace, mode: str) -> tuple[dl.Project, dict, dict]:
    """(project, resolved store family, manifest info) for a format-2 kit in the given mode."""
    root = dl.find_project(kit)
    if root is None:
        raise dl.GateError(f"no brand/direction.json found at or above {kit}. Format-2 kits take their look from the "
                           "approved creative direction: run the creative-director first (direction.py init)")
    p = dl.load_project(root)
    if mode == "production":
        prod = dl.production(p, "store")
        ad = prod.resolved
        info = {"direction": prod.gate.direction[0] if prod.gate.direction else None,  # type: ignore[index]
                "concept": prod.gate.concept[0] if prod.gate.concept else None,  # type: ignore[index]
                "approvals": prod.gate.records, "concept_rel": prod.concept_rel}
    else:
        rel, concept, ad = dl.preview(p, "store", getattr(args, "concept", None))
        g = dl.gate(p, "store")
        state = "approved" if g.ok and g.concept_rel == rel else "DRAFT, not approved for production"
        print(f"concept: {rel} ({state})")
        info = {"concept_rel": rel}
    ad["_root"] = str(p.root)
    system = sorted({f["family"] for f in ad["faces"] if f.get("source") == "system"})
    if system:
        print(f"NOTE  system fonts ({', '.join(system)}): renders depend on the fonts installed on this machine, "
              "so they are less reproducible than local font files")
    return p, ad, info


def legacy_note(kit: Path) -> None:
    old = [n for n in LEGACY_FILES if (kit / n).is_file()]
    if old:
        print(f"NOTE  unused files from an older harness in the kit (renders now run from {BUILD}/): {', '.join(old)}; "
              "delete them unless you edited them on purpose")


def render(args: argparse.Namespace) -> int:
    kit: Path = args.kit
    cfg = load_cfg(kit)
    sizes, frames_filter, sizes_filter = plan_sizes(cfg, args)
    v2 = is_v2(cfg)
    ad: dict | None = None
    info: dict = {}
    if v2:
        if args.check_only:
            try:
                p, ad, info = resolve_v2(kit, args, "production")
                print("gate: the direction and store concept are approved")
            except dl.GateError as e:
                print(f"gate: NOT MET (production renders will refuse)\n  {e}".replace("\n", "\n  "))
                try:
                    p, ad, info = resolve_v2(kit, args, "preview")
                except dl.GateError:
                    raise
                except InputError as e2:
                    print(f"concept checks SKIPPED: {e2}")
                    errs = [f"frames.json: {x}" for x in schema.validate(cfg, schema.load("kit"))]
                    if not errs:
                        errs = validate_common(cfg, kit, args.project, V2_OBJECTS | set().union(*PROP_PACKS.values()))[0]
                    if errs:
                        print("frames.json has problems:\n  " + "\n  ".join(errs), file=sys.stderr)
                        return 1
                    print(f"frames.json structure OK ({len(cfg['frames'])} frames, format 2)")
                    return 0
        else:
            p, ad, info = resolve_v2(kit, args, "production")
        errors, images = validate_v2(cfg, kit, args.project, ad, "production", p)
    else:
        print("WARN  legacy 1.6 kit (frames.json has no \"format\"): rendered unchanged with the frozen 1.6 engine. "
              "To give it the project's own look, have the creative-director set a direction and migrate the kit "
              "(store-mockups references/art-direction.md, 'Migrating a 1.6 kit')")
        errors, images = validate_common(cfg, kit, args.project, LEGACY_OBJECTS)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    print(f"frames.json OK ({'continuous' if continuous(cfg) else 'classic'}, {len(cfg['frames'])} frames"
          f"{', format 2' if v2 else ', 1.6 format'})")
    if args.check_only:
        return 0

    out = (args.out or kit / cfg.get("out", "out")).resolve()
    legacy_note(kit)
    if not (kit / ".gitignore").exists():
        (kit / ".gitignore").write_text(gitignore_text(kit, out), encoding="utf-8")
        print(f"wrote {kit / '.gitignore'} (keeps {BUILD}/, .preview/ and the renders out of git)")
    started = dl.now_utc()
    with DirLock(kit / BUILD / "render.lock", f"the kit {kit}"):
        chrome = browser.find_chrome(args.chrome)
        build = prepare_build(kit / BUILD, kit, cfg, images, args.project, ad, "production")
        base = (build / "frame.html").resolve().as_uri()
        with Publisher(out, "store renders") as pub:
            tasks = shots(chrome, base, cfg, sizes, frames_filter, not frames_filter and not sizes_filter, pub.stage_path)
            run_all(args.jobs, tasks)
            if not args.all:
                pub.publish(prune=False)
                print(f"published {len(pub.published)} file(s) -> {out}")
                if v2:
                    write_manifest(p, info, cfg, ad, out, pub, chrome, started, {"release-set": ("SKIPPED", "not --all")})
                return 0
            stage = pub.stage
            sheets = contact_sheets(stage, cfg, sizes)
            problems = verify_outputs(stage, cfg, sizes)
            checks: dict[str, tuple[str, str]] = {"verify": ("FAIL" if problems else "PASS", f"{problems} problem(s)")}
            if args.no_contrast:
                checks["contrast"] = ("SKIPPED", "--no-contrast")
                print("contrast: SKIPPED (--no-contrast)")
            elif v2:
                findings, fonts = check_v2(chrome, base, cfg, ad, sizes, args.jobs)  # type: ignore[arg-type]
                res = report_contrast(findings, f"contrast (WCAG 2.2 at the smallest intended display: canvases shown "
                                                f"{ad['displayWidth']} CSS px wide; computed where the backdrop colour is "  # type: ignore[index]
                                                "known, sampled estimates otherwise)")
                checks["contrast"] = (res, f"{len(findings)} text runs")
                for line in fonts:
                    print(f"  FAIL  text: {line}")
                checks["text"] = ("FAIL" if fonts else "PASS", f"{len(fonts)} caption run(s) with missing glyphs or cut off")
            else:
                findings = check_legacy_contrast(chrome, base, cfg, sizes, args.jobs)
                res = report_contrast(findings, "contrast (1.6 rule: headline 3:1, other caption text 4.5:1; sampled "
                                                "estimates, so a pass needs a look)")
                checks["contrast"] = (res, f"{len(findings)} text runs")
            store_rc = None
            if STORE_CHECK.is_file():
                store_rc = subprocess.run([sys.executable, str(STORE_CHECK), str(stage)], timeout=600).returncode
                checks["store"] = ("PASS" if store_rc == 0 else "FAIL", "check_store_assets.py inspect mode")
            failed = [k for k, (r, _) in checks.items() if r == "FAIL"]
            summary = "; ".join(f"{k} {r}" for k, (r, _) in checks.items())
            if failed:
                print(f"\nrender --all: NOT published ({summary}); the previous renders in {out} are unchanged",
                      file=sys.stderr)
                return 1
            pub.publish(prune=True)
            for rel in pub.removed:
                print(f"removed stale {rel}")
            stale = [p_ for d in {SIZES[k][3] for k in sizes} for p_ in sorted((out / d).glob("*.png"))]
            for rel in pub.report_unowned(stale):
                print(f"NOTE  {rel} was not written by a recorded render, so it was kept; delete it if it is obsolete")
            review = any(r == "REVIEW REQUIRED" for r, _ in checks.values())
            if v2:
                write_manifest(p, info, cfg, ad, out, pub, chrome, started, checks)
    print(f"\nrender --all: {len(tasks)} images -> {out}; sheets: {', '.join(s.name for s in sheets)}; {summary}"
          + ("; status REVIEW REQUIRED: look at every caption marked above before release" if review else ""))
    return 0


def write_manifest(p: dl.Project, info: dict, cfg: dict, ad: dict, out: Path, pub: Publisher, chrome: str,
                   started: str, checks: dict) -> None:
    outputs = []
    for rel in pub.published:
        f = out / rel
        entry = {"path": Path(os.path.relpath(f, p.root)).as_posix(), "sha256": sha256_file(f), "bytes": f.stat().st_size}
        if f.suffix == ".png":
            with Image.open(f) as im:
                entry["size"] = list(im.size)
        outputs.append(entry)
    ad_fonts = [{"family": face["family"], "source": face.get("source", "local"), "weight": face["weight"],
                 "style": face["style"], **({"sha256": face["sha256"]} if "sha256" in face else {})} for face in ad["faces"]]
    results = {k: {"result": r, "detail": d} for k, (r, d) in checks.items()}
    status = "failed" if any(r == "FAIL" for r, _ in checks.values()) else \
        "review-required" if any(r in ("REVIEW REQUIRED", "SKIPPED") for r, _ in checks.values()) else "complete"
    manifest = {"schemaVersion": 1, "runId": pub.id, "family": "store", "mode": "production", "tool": "render_frames.py",
                "startedAt": started, "finishedAt": dl.now_utc(),
                "engine": {"api": harnesslib.API_VERSION, "browser": browser.version(chrome)},
                "inputs": {"config": sha256_text(canonical(cfg)), "direction": info.get("direction"),
                           "concept": info.get("concept")},
                "approvals": info.get("approvals", []), "fonts": ad_fonts, "seed": None, "outputs": outputs,
                "checks": results, "status": status}
    path = dl.write_run_manifest(p.root, manifest)
    print(f"run manifest: {path.relative_to(p.root).as_posix()} ({status})")


def preview(args: argparse.Namespace) -> int:
    kit: Path = args.kit
    cfg = load_cfg(kit)
    if not is_v2(cfg):
        raise UsageError("preview is for format-2 kits; a 1.6 kit renders with `render` as before")
    sizes, frames_filter, sizes_filter = plan_sizes(cfg, args)
    p, ad, info = resolve_v2(kit, args, "preview")
    errors, images = validate_v2(cfg, kit, args.project, ad, "preview", p)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    rid = run_id()
    out = (args.out or self_ignoring_dir(kit / ".preview", "render_frames.py previews") / rid).resolve()
    if out.exists() and any(out.iterdir()):
        raise UsageError(f"{out} is not empty; previews never overwrite (choose another --out)")
    out.mkdir(parents=True, exist_ok=True)
    with DirLock(out.parent / f".{out.name}.lock", f"preview output {out}"), tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "kit"
        copy.mkdir()
        for name in KIT_CONTENT:
            if (kit / name).is_file():
                shutil.copyfile(kit / name, copy / name)
        if (kit / "assets").is_dir():
            shutil.copytree(kit / "assets", copy / "assets")
        rel_images = {}
        for k, path in images.items():
            try:
                rel_images[k] = copy / path.resolve().relative_to(kit.resolve())
            except ValueError:
                rel_images[k] = path
        chrome = browser.find_chrome(args.chrome)
        build = prepare_build(copy / BUILD, copy, cfg, rel_images, args.project, ad, "preview")
        base = (build / "frame.html").resolve().as_uri()
        tasks = shots(chrome, base, cfg, sizes, frames_filter, not frames_filter, lambda rel: out / rel)
        run_all(args.jobs, tasks)
        findings, fonts = check_v2(chrome, base, cfg, ad, sizes, args.jobs) if not frames_filter else ([], [])
        if findings:
            report_contrast(findings, "contrast (draft):")
        for line in fonts:
            print(f"  WARN  text: {line}")
    folders = [SIZES[k][3] for k in sizes]
    pngs = [q for d in dict.fromkeys(folders) for q in sorted((out / d).glob("*.png"))]
    if pngs:
        imaging.sheet(([out / FG_FILE] if (out / FG_FILE).is_file() else []) + pngs, out / "contact-sheet.png")
    print(f"preview: {len(tasks)} image(s) -> {out} (DRAFT; concept {info['concept_rel']}); sheet contact-sheet.png")
    return 0


def contrast_cmd(args: argparse.Namespace) -> int:
    kit = args.kit
    cfg = load_cfg(kit)
    sizes = [s for s in args.sizes.split(",") if s] or cfg.get("sizes") or ["play-phone", "ios-69"]
    if is_v2(cfg):
        p, ad, _ = resolve_v2(kit, args, "preview")
        errors, images = validate_v2(cfg, kit, args.project, ad, "preview", p)
    else:
        ad = None
        errors, images = validate_common(cfg, kit, args.project, LEGACY_OBJECTS)
    if errors:
        print("frames.json has problems:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    with DirLock(kit / BUILD / "render.lock", f"the kit {kit}"):
        chrome = browser.find_chrome(args.chrome)
        build = prepare_build(kit / BUILD, kit, cfg, images, args.project, ad, "preview")
        base = (build / "frame.html").resolve().as_uri()
        if ad is None:
            res = report_contrast(check_legacy_contrast(chrome, base, cfg, sizes, args.jobs),
                                  "contrast (1.6 rule: headline 3:1, other caption text 4.5:1; sampled estimates)")
            fonts: list[str] = []
        else:
            findings, fonts = check_v2(chrome, base, cfg, ad, sizes, args.jobs)
            res = report_contrast(findings, f"contrast (canvases shown {ad['displayWidth']} CSS px wide)")
            for line in fonts:
                print(f"  FAIL  text: {line}")
    return 1 if res == con.FAIL or fonts else 0


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
    for name, text in (("render", "validate and render frames"), ("preview", "render a draft (format 2)"),
                       ("contrast", "caption contrast check only")):
        p = sub.add_parser(name, help=text)
        p.add_argument("kit", type=Path)
        p.add_argument("--sizes", default="", help="comma-separated size keys (default: frames.json sizes)")
        p.add_argument("--project", type=Path, default=Path("."), help="app folder with node_modules (icons, fonts) and photos")
        p.add_argument("--chrome", help="path to Chrome/Chromium/Edge")
        p.add_argument("--jobs", type=int, default=jobs, help=f"parallel Chrome runs (default {jobs}, at most 8)")
        if name in ("render", "preview"):
            p.add_argument("--frames", default="", help="comma-separated frame ids (default: all)")
            p.add_argument("--out", type=Path, help="output folder")
        if name in ("preview", "contrast"):
            p.add_argument("--concept", help="a store concept file (relative to the project root); default: the selected one")
        if name == "render":
            p.add_argument("--all", action="store_true", help="release set: every size, sheets, verify, contrast, store check")
            p.add_argument("--no-contrast", action="store_true", help="with --all: skip the contrast check")
            p.add_argument("--check-only", action="store_true", help="validate frames.json (and report the gates) without rendering")
    args = parser.parse_args()
    if getattr(args, "jobs", None) is not None:
        args.jobs = max(1, min(8, args.jobs))
    try:
        if args.cmd == "init":
            return init(args.kit, args.style, args.project.resolve(), args.new)
        args.project = args.project.resolve()
        return {"render": render, "preview": preview, "contrast": contrast_cmd}[args.cmd](args)
    except (UsageError, OperationalError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
