#!/usr/bin/env python3
"""Build a fictional project with a creative direction, concepts and a format-2 mockup kit.

Used by tests/creative-direction.test.sh and tests/media-variety.test.sh. Everything is made with
the harness's own CLIs (palette.py, type_scale.py, direction.py, render_frames.py init), so the
fixture exercises them. Fonts: a font file found on this machine is copied into brand/fonts/ and
recorded as a local font (test use only; nothing is committed).

Usage: python make_project.py DIR VARIANT [--approve] [--font PATH]
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


def build(root: Path, variant: str, approve: bool, font: Path) -> None:
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
    for fam in ("store", "marketing", "icon"):
        d["families"][fam] = {"requested": fam in v}
    (brand / "direction.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
    for fam in ("store", "marketing", "icon"):
        if fam not in v:
            continue
        run(DIRECTION, "concept", "new", "--family", fam, "--id", "a", "--name", f"{v['name']} {fam}", "--run", RUN, cwd=root)
        cpath = brand / "concepts" / fam / RUN / "a.json"
        c = json.loads(cpath.read_text(encoding="utf-8"))
        c["idea"] = f"The {fam} look for {v['name']}, from its direction."
        c["spec"] = v[fam]
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
    if approve:
        run(DIRECTION, "approve", "--gate", "direction", "--by", "Fixture Owner", "--evidence", "test fixture approval", cwd=root)
        for fam in ("store", "marketing", "icon"):
            if fam in v:
                run(DIRECTION, "approve", "--gate", "concept", "--family", fam, "--concept",
                    f"brand/concepts/{fam}/{RUN}/a.json", "--by", "Fixture Owner", "--evidence", "test fixture approval", cwd=root)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", type=Path)
    ap.add_argument("variant", choices=sorted(VARIANTS))
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--font", type=Path)
    a = ap.parse_args()
    build(a.dir, a.variant, a.approve, a.font or find_font())
    print(f"built {a.variant} in {a.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
