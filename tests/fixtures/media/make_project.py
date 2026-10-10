#!/usr/bin/env python3
"""Build a fictional project with a creative direction, concepts and a format-2 mockup kit.

Used by tests/creative-direction.test.sh and tests/media-variety.test.sh. Everything is made with
the harness's own CLIs (palette.py, type_scale.py, direction.py, render_frames.py init), so the
fixture exercises them. Fonts: a font file found on this machine is copied into brand/fonts/ and
recorded as a local font (test use only; nothing is committed).

Usage: python make_project.py DIR VARIANT [--approve] [--video] [--font PATH]
--video also writes motion tokens (render_video.py motion-tokens), a video concept and a piece
brand/video/launch/video.json (and, when the concept allows still scenes, a two-format loop
brand/video/card/video.json over brand/art/garden.png); with --approve the video concept and the
launch storyboard are approved too.
Variants: fernway (garden journal: warm, serif display, gradient, frameless, split layouts)
          kestrel (logistics: slate + orange, mono display, solid, framed, inset/caption-bottom)
          samebrand (keeps 1.6-like Inter + indigo on purpose, listed in direction "keep")
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SK = REPO / "harness" / "skills"
PALETTE = SK / "color-science" / "scripts" / "palette.py"
TYPE = SK / "typography" / "scripts" / "type_scale.py"
DIRECTION = SK / "creative-direction" / "scripts" / "direction.py"
RENDER = SK / "store-mockups" / "scripts" / "render_frames.py"
VIDEO = SK / "brand-video" / "scripts" / "render_video.py"
RUN = "20261002-120000-0a0b0c"

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/georgia.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf", "/System/Library/Fonts/Supplemental/Georgia.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
]


def find_font() -> Path:
    for c in FONT_CANDIDATES:
        if Path(c).is_file():
            return Path(c)
    try:
        out = subprocess.run(["fc-list", "--format", "%{file}\n", ":lang=en:fontformat=TrueType"], capture_output=True,
                             text=True, timeout=30).stdout
        for line in out.splitlines():
            if line.strip().lower().endswith(".ttf") and Path(line.strip()).is_file():
                return Path(line.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    raise SystemExit("no TrueType font found on this machine (pass --font)")


def run(*args: object, cwd: Path) -> str:
    r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True,
                       env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(map(str, args))} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r.stdout


VARIANTS = {
    "fernway": {
        "name": "Fernway",
        "ramps": [("moss", ["--seed", "#3d6b4f"]), ("clay", ["--seed", "#b5653d"]), ("sand", ["--hue", "80", "--chroma", "0.03"])],
        "fonts": {"display": ("Fernway Serif", "Georgia,serif", 700), "text": ("Fernway Sans", "sans-serif", 400)},
        "roles": {"canvas": "{color.sand.50}", "ink": "{color.moss.950}", "inkMuted": "{color.moss.800}",
                  "accent": "{color.clay.700}", "onAccent": "{color.sand.50}", "surface": "{color.sand.100}"},
        "facts": [{"text": "A journal for home gardeners", "source": "README.md"}],
        "mood": {"keywords": ["field notebook", "sun-bleached"], "axes": {"calm-energetic": -0.6, "warm-cool": -0.7, "organic-geometric": -0.6}},
        "store": {
            "backgrounds": {
                "dawn": {"recipe": "linear", "stops": ["{color.sand.50}", "{color.sand.200}"], "angle": 180, "space": "oklab",
                         "text": {"head": "{color.moss.950}", "sub": "{color.moss.800}", "accent": "{color.clay.800}"}},
                "soil": {"recipe": "solid", "color": "{color.moss.900}",
                         "text": {"head": "{color.sand.50}", "sub": "{color.sand.200}", "accent": "{color.clay.200}"}},
            },
            "caption": {"head": {"font": "display", "weight": 700, "lineHeight": 1.05}, "sub": {"font": "text", "weight": 400},
                        "align": "start", "accent": "underline", "headScale": 0.08},
            "device": {"style": "frameless", "radius": 0.08, "shadow": "long"},
            "layouts": ["split-left", "caption-bottom"], "defaultLayout": "split-left", "defaultBackground": "dawn",
            "featureGraphic": {"layout": "centered-type", "background": "soil"},
        },
        "marketing": {
            "backgrounds": {"soil": {"recipe": "solid", "color": "{color.moss.900}",
                                     "text": {"head": "{color.sand.50}", "sub": "{color.sand.200}", "accent": "{color.clay.200}"}}},
            "caption": {"head": {"font": "display", "weight": 700}, "sub": {"font": "text", "weight": 400},
                        "kicker": {"font": "text", "weight": 400, "case": "upper", "tracking": 0.08}, "align": "start",
                        "accent": "underline"},
            "layouts": ["type-start", "split-image"], "defaultLayout": "type-start", "defaultBackground": "soil",
        },
        "icon": {"background": {"recipe": "linear", "stops": ["{color.clay.500}", "{color.clay.700}"], "angle": 160},
                 "glyphScale": 0.52, "glyphOffset": [0, 0.02]},
        "video": {
            "backgrounds": {
                "dawn": {"recipe": "linear", "stops": ["{color.sand.50}", "{color.sand.200}"], "angle": 180, "space": "oklab",
                         "text": {"head": "{color.moss.950}", "sub": "{color.moss.800}", "accent": "{color.clay.800}"}},
                "soil": {"recipe": "solid", "color": "{color.moss.900}",
                         "text": {"head": "{color.sand.50}", "sub": "{color.sand.200}", "accent": "{color.clay.200}"}},
            },
            "caption": {"head": {"font": "display", "weight": 700, "lineHeight": 1.05}, "sub": {"font": "text", "weight": 400},
                        "align": "start", "accent": "underline"},
            "layouts": ["type-start", "type-lower"], "defaultLayout": "type-start", "defaultBackground": "dawn",
            "sceneTemplates": ["title", "feature", "stat", "end-card", "still"],
            "motion": {"transitions": ["cut", "fade", "dip"], "defaultTransition": "fade", "textIn": "fade-up"},
            "pace": {"readingWpm": 200, "minHold": 1.0, "voWpm": 145},
            "endCard": {"background": "soil", "logo": False},
            "voice": {"casting": "a warm, unhurried gardener in their fifties", "pace": "measured"},
            "music": {"mood": "acoustic, morning light", "bpm": [80, 96], "energy": "arc"},
        },
        "frames": [("01-home", "home", "Notes that <em>grow</em> with your garden", "Every bed, every season, one journal", "split-left", "dawn"),
                   ("02-activity", "activity", "See what <em>thrived</em>", "Your week at a glance", "caption-bottom", "soil")],
    },
    "kestrel": {
        "name": "Kestrel Ops",
        "ramps": [("slate", ["--hue", "250", "--chroma", "0.03"]), ("signal", ["--seed", "#e8590c"])],
        "fonts": {"display": ("Kestrel Mono", "ui-monospace,monospace", 700), "text": ("Kestrel Sans", "sans-serif", 400)},
        "roles": {"canvas": "{color.slate.900}", "ink": "{color.slate.50}", "inkMuted": "{color.slate.200}",
                  "accent": "{color.signal.400}", "onAccent": "{color.slate.950}", "surface": "{color.slate.800}"},
        "facts": [{"text": "Dispatch tool for small delivery fleets", "source": "app.json description"}],
        "mood": {"keywords": ["control room", "precise"], "axes": {"calm-energetic": 0.4, "warm-cool": 0.6, "organic-geometric": 0.8}},
        "store": {
            "backgrounds": {
                "night": {"recipe": "solid", "color": "{color.slate.950}",
                          "panel": "{color.slate.800}",
                          "text": {"head": "{color.slate.50}", "sub": "{color.slate.200}", "accent": "{color.signal.400}",
                                   "onAccent": "{color.slate.950}"}},
            },
            "caption": {"head": {"font": "display", "weight": 700, "tracking": -0.01, "case": "upper"},
                        "sub": {"font": "text", "weight": 400}, "align": "center", "accent": "highlight", "headScale": 0.062},
            "device": {"style": "frame", "bezel": "{color.slate.700}", "radius": 0.06, "shadow": "crisp"},
            "layouts": ["inset", "caption-top"], "defaultLayout": "inset", "defaultBackground": "night",
            "featureGraphic": {"layout": "split-device-left", "background": "night"},
        },
        "marketing": {
            "backgrounds": {"night": {"recipe": "solid", "color": "{color.slate.950}",
                                      "text": {"head": "{color.slate.50}", "sub": "{color.slate.200}", "accent": "{color.signal.400}",
                                               "onAccent": "{color.slate.950}"}}},
            "caption": {"head": {"font": "display", "weight": 700, "case": "upper"}, "sub": {"font": "text", "weight": 400},
                        "align": "center", "accent": "highlight"},
            "layouts": ["type-center"], "defaultLayout": "type-center", "defaultBackground": "night",
        },
        "icon": {"background": {"recipe": "solid", "color": "{color.slate.900}"}, "glyphScale": 0.64,
                 "qualityTarget": {"markContrast": 3}},
        "video": {
            "backgrounds": {"night": {"recipe": "solid", "color": "{color.slate.950}",
                                      "text": {"head": "{color.slate.50}", "sub": "{color.slate.200}", "accent": "{color.signal.400}",
                                               "onAccent": "{color.slate.950}"}}},
            "caption": {"head": {"font": "display", "weight": 700, "case": "upper"}, "sub": {"font": "text", "weight": 400},
                        "align": "center", "accent": "highlight"},
            "layouts": ["type-center"], "defaultLayout": "type-center", "defaultBackground": "night",
            "motion": {"transitions": ["cut", "push", "wipe"], "defaultTransition": "push", "textIn": "mask-up",
                       "stagger": {"perItemMs": 60, "maxItems": 4}},
            "pace": {"readingWpm": 220, "minHold": 0.8, "voWpm": 160},
            "voice": {"casting": "a crisp, confident dispatcher", "pace": "brisk"},
        },
        "frames": [("01-home", "home", "Every route, <em>live</em>", "Dispatch from one screen", "inset", "night"),
                   ("02-activity", "activity", "Know what <em>shipped</em>", "A clear log for every driver", "caption-top", "night")],
    },
    "samebrand": {
        "name": "Ledgerly",
        "ramps": [],
        "fonts": {"display": ("Inter", "sans-serif", 800), "text": ("Inter", "sans-serif", 400)},
        "roles": {"canvas": "{color.brand.ground}", "ink": "{color.brand.ink}", "inkMuted": "{color.brand.sub}",
                  "accent": "{color.brand.mint}"},
        "facts": [{"text": "Existing brand: Inter and an indigo gradient", "source": "src/theme/index.ts"}],
        "keep": ["Inter typeface (existing brand)", "indigo gradient and mint accent (existing brand)"],
        "mood": {"keywords": ["confident"], "axes": {}},
        "store": {
            "backgrounds": {"brand": {"recipe": "linear", "stops": ["{color.brand.ground}", "{color.brand.violet}"], "angle": 165,
                                      "text": {"head": "{color.brand.white}", "sub": "{color.brand.sub}", "accent": "{color.brand.mint}"}}},
            "caption": {"head": {"font": "display", "weight": 800, "tracking": -0.025}, "sub": {"font": "text", "weight": 400},
                        "align": "center", "accent": "color"},
            "device": {"style": "frame"}, "layouts": ["caption-top"], "defaultLayout": "caption-top", "defaultBackground": "brand",
        },
        "frames": [("01-home", "home", "Your money, <em>clearly</em>", "Personal and shared costs together", None, None),
                   ("02-activity", "activity", "Every cost, <em>by day</em>", "Search and filter your history", None, None)],
    },
}

SAMEBRAND_TOKENS = {"color": {"brand": {
    "ground": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0.1647, 0.1059, 0.6902], "hex": "#2a1bb0"}},
    "violet": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0.3569, 0.3098, 0.9412], "hex": "#5b4ff0"}},
    "mint": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0.6235, 0.9529, 0.8118], "hex": "#9ff3cf"}},
    "sub": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0.8627, 0.851, 1.0], "hex": "#dcd9ff"}},
    "ink": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0.0745, 0.1059, 0.1804], "hex": "#131b2e"}},
    "white": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [1, 1, 1], "hex": "#ffffff"}},
}}}


MOTION_REFS = {"durations": {"fast": "{motion.duration.fast}", "base": "{motion.duration.base}", "slow": "{motion.duration.slow}"},
               "easing": {"standard": "{motion.easing.standard}", "enter": "{motion.easing.enter}",
                          "exit": "{motion.easing.exit}", "emphasis": "{motion.easing.emphasis}"}}


def piece(v: dict) -> dict:
    name, head, sub = v["name"], v["frames"][0][2], v["frames"][0][3]
    return {"schemaVersion": 1, "id": "launch", "kind": "social", "title": "Launch teaser", "formats": ["social-9x16"], "fps": 30,
            "scenes": [
                {"id": "hook", "template": "title", "duration": 4.5, "copy": {"kicker": name, "head": head, "sub": sub},
                 "vo": f"Meet {name}. {sub}."},
                {"id": "how", "template": "feature", "duration": 5,
                 "copy": {"head": "Built for the <em>week</em>", "points": ["Plan in a minute", "See what changed"]},
                 "vo": "Plan in a minute, and see what changed since yesterday."},
                {"id": "proof", "template": "stat", "duration": 3.5, "copy": {"value": "3x", "label": "faster each morning"},
                 "vo": "Three times faster, every morning."},
                {"id": "end", "template": "end-card", "duration": 3, "copy": {"head": f"Try {name} today", "url": "example.com"},
                 "vo": f"Try {name} today."}],
            "voice": {"language": "en", "pronunciations": [{"text": name, "say": name}]},
            "captions": {"sidecar": ["srt", "vtt"]}}


def loop_piece(v: dict) -> dict:
    """A short loop in two formats: a still scene over a picture, then the name; GIF, WebP, poster."""
    return {"schemaVersion": 1, "id": "card", "kind": "loop", "title": "Link card loop", "formats": ["og-card", "social-1x1"],
            "fps": 30,
            "scenes": [
                {"id": "art", "template": "still", "duration": 2.5,
                 "media": {"image": "brand/art/garden.png", "motion": "push-in", "focus": [0.5, 0.4]},
                 "copy": {"head": "Notes that <em>grow</em>"}},
                {"id": "name", "template": "title", "duration": 2.4, "copy": {"head": v["name"], "sub": "Your garden journal"},
                 "byFormat": {"social-1x1": {"layout": "type-lower"}}}],
            "loop": {"outputs": ["gif", "webp"], "width": 480, "fps": 15},
            "poster": {"scene": "art"}}


def garden_png(path: Path) -> None:
    """A soft, light picture for the still scene (made here: no third-party image in the fixture)."""
    from PIL import Image, ImageDraw
    w, h = 1600, 1000
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(round(246 - 18 * t), round(239 - 22 * t), round(222 - 30 * t)))
    for i, (cx, cy, r) in enumerate([(300, 700, 220), (820, 760, 300), (1350, 690, 240)]):
        d.ellipse([cx - r, cy - r // 2, cx + r, cy + r // 2], fill=(214 - 6 * i, 222 - 4 * i, 196 - 8 * i))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=False)


def build(root: Path, variant: str, approve: bool, font: Path, video: bool = False) -> None:
    v = VARIANTS[variant]
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)  # a project boundary for find_project()
    (root / "README.md").write_text(f"# {v['name']}\n", encoding="utf-8")
    brand = root / "brand"
    (brand / "fonts").mkdir(parents=True, exist_ok=True)
    tokens = "brand/tokens.json"
    if variant == "samebrand":
        (brand / "tokens.json").write_text(json.dumps(SAMEBRAND_TOKENS, indent=2), encoding="utf-8")
    for name, args in v["ramps"]:
        run(PALETTE, "ramp", "--name", name, *args, "--out", tokens, cwd=root)
    done = {}
    for role, (family, fallback, weight) in v["fonts"].items():
        if family in done:
            continue
        rel = f"brand/fonts/{family.replace(' ', '-').lower()}-{weight}{font.suffix}"
        shutil.copyfile(font, root / rel)
        files = ["--file", f"{rel}:{weight}"]
        if variant == "samebrand" and family == "Inter":
            rel2 = f"brand/fonts/inter-400{font.suffix}"
            shutil.copyfile(font, root / rel2)
            files += ["--file", f"{rel2}:400"]
        run(TYPE, "font", "--name", role, "--family", family, "--fallback", fallback, "--source", "local", *files,
            "--license", "test fixture only", "--license-evidence", "copied from a system font for tests; never shipped",
            "--out", tokens, cwd=root)
        done[family] = role
    run(DIRECTION, "init", "--name", v["name"], cwd=root)
    d = json.loads((brand / "direction.json").read_text(encoding="utf-8"))
    d["summary"] = f"Fixture direction for {v['name']}."
    d["tokens"]["roles"] = v["roles"]
    d["tokens"]["fonts"] = {role: "{font." + done[fam] + "}" for role, (fam, _, _) in v["fonts"].items()}
    d["context"]["facts"] = v["facts"]
    d["context"]["openQuestions"] = []
    d["mood"] = v["mood"]
    d["keep"] = v.get("keep", [])
    fams = ("store", "marketing", "icon") + (("video",) if video else ())
    for fam in fams:
        d["families"][fam] = {"requested": fam in v}
    if video:
        d["families"]["video"]["brief"] = "a 15-second vertical launch teaser"
    (brand / "direction.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
    if video:
        run(VIDEO, "motion-tokens", "--write", cwd=root)
    for fam in fams:
        if fam not in v:
            continue
        run(DIRECTION, "concept", "new", "--family", fam, "--id", "a", "--name", f"{v['name']} {fam}", "--run", RUN, cwd=root)
        cpath = brand / "concepts" / fam / RUN / "a.json"
        c = json.loads(cpath.read_text(encoding="utf-8"))
        c["idea"] = f"The {fam} look for {v['name']}, from its direction."
        c["spec"] = json.loads(json.dumps(v[fam]))
        if fam == "video":
            c["spec"]["motion"] = {**MOTION_REFS, **c["spec"]["motion"]}
        cpath.write_text(json.dumps(c, indent=2), encoding="utf-8")
    if "marketing" in v:
        canvas = {"schemaVersion": 1, "assets": [{"id": "og", "size": "og", "copy": {
            "kicker": v["name"], "head": v["frames"][0][2], "sub": v["frames"][0][3]}}]}
        (brand / "canvas.json").write_text(json.dumps(canvas, indent=2), encoding="utf-8")
        (brand / "exports.json").write_text(json.dumps({"exports": [
            {"canvas": "og", "out": "../web/public", "name": "og-image", "flatten": True}]}, indent=2), encoding="utf-8")
    run(RENDER, "init", "store-assets/mockup-kit", "--project", ".", cwd=root)
    kit = root / "store-assets" / "mockup-kit"
    cfg = json.loads((kit / "frames.json").read_text(encoding="utf-8"))
    cfg["icons"] = "none"
    cfg["sizes"] = ["play-phone", "ios-69"]
    cfg["frames"] = []
    for fid, screen, head, sub, layout, bg in v["frames"]:
        fr = {"id": fid, "screen": screen, "head": head, "sub": sub}
        if layout:
            fr["layout"] = layout
        if bg:
            fr["background"] = bg
        cfg["frames"].append(fr)
    cfg["featureGraphic"] = {"screen": "home", "title": v["name"], "tagline": v["frames"][0][2], "sub": v["frames"][0][3]}
    (kit / "frames.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    if video and "video" in v:
        (brand / "video" / "launch").mkdir(parents=True, exist_ok=True)
        (brand / "video" / "launch" / "video.json").write_text(json.dumps(piece(v), indent=2), encoding="utf-8")
        if "still" in v["video"].get("sceneTemplates", []):
            garden_png(brand / "art" / "garden.png")
            (brand / "video" / "card").mkdir(parents=True, exist_ok=True)
            (brand / "video" / "card" / "video.json").write_text(json.dumps(loop_piece(v), indent=2), encoding="utf-8")
    if approve:
        run(DIRECTION, "approve", "--gate", "direction", "--by", "Fixture Owner", "--evidence", "test fixture approval", cwd=root)
        for fam in fams:
            if fam in v:
                run(DIRECTION, "approve", "--gate", "concept", "--family", fam, "--concept",
                    f"brand/concepts/{fam}/{RUN}/a.json", "--by", "Fixture Owner", "--evidence", "test fixture approval", cwd=root)
        if video and "video" in v:
            run(DIRECTION, "approve", "--gate", "storyboard", "--piece", "launch", "--by", "Fixture Owner",
                "--evidence", "test fixture approval", cwd=root)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("variant", choices=sorted(VARIANTS))
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--font", type=Path)
    a = ap.parse_args()
    build(a.dir, a.variant, a.approve, a.font or find_font(), a.video)
    print(f"built {a.variant} in {a.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
