"""A piece with custom scenes for the 1.12 video tests (tests/video.test.sh): one scene driven by a
GSAP-style timeline, one by a Lottie-style player, both from small test libraries (libs/), and a
second piece whose scene script breaks the composition contract (a timer), and a third (1.13) whose
custom scene composes two project images from custom.assets, one of them as a CSS background.

Usage: python m4_media.py PROJECT
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    root = Path(sys.argv[1])
    vendor = root / "brand" / "vendor"
    vendor.mkdir(parents=True, exist_ok=True)
    for name in ("minitl.js", "minilottie.js"):
        shutil.copyfile(HERE / "libs" / name, vendor / name)
    scenes = root / "brand" / "video" / "motion" / "scenes"
    scenes.mkdir(parents=True, exist_ok=True)
    (scenes / "orbit.html").write_text(
        '<div class="dot" style="position:absolute;left:10%;top:62%;width:90px;height:90px;border-radius:50%;'
        'background:#2f7a4f;opacity:0"></div>\n', encoding="utf-8")
    (scenes / "orbit.js").write_text(
        "// a GSAP-style timeline: the dot slides in while the caption reads\n"
        "window.VideoScenes = window.VideoScenes || {};\n"
        "window.VideoScenes.orbit = function (el, ctx) {\n"
        "  const dot = el.querySelector('.dot');\n"
        "  return window.minitl.timeline().to(dot, { x: ctx.width * 0.5, opacity: 1 }, 0.2, 1.6);\n"
        "};\n", encoding="utf-8")
    (scenes / "badge.html").write_text('<div class="lot" style="position:absolute;inset:18% 18% 30% 18%"></div>\n',
                                       encoding="utf-8")
    (scenes / "badge.js").write_text(
        "window.VideoScenes = window.VideoScenes || {};\n"
        "window.VideoScenes.badge = function (el, ctx) {\n"
        "  return window.minilottie.loadAnimation({ container: el.querySelector('.lot'), animationData: ctx.lottie });\n"
        "};\n", encoding="utf-8")
    (scenes / "badge.json").write_text(json.dumps({"fr": 30, "op": 45, "from": [20, 50], "to": [80, 50], "r": 12,
                                                   "color": "#c2410c"}), encoding="utf-8")
    lib = [{"file": "brand/vendor/minitl.js", "name": "minitl (test helper)", "license": "MIT, written for the tests"},
           {"file": "brand/vendor/minilottie.js", "name": "minilottie (test helper)", "license": "MIT, written for the tests"}]
    piece = {
        "schemaVersion": 1, "id": "motion", "kind": "social", "title": "Custom scenes", "formats": ["social-1x1"], "fps": 30,
        "libraries": lib,
        "scenes": [
            {"id": "orbit", "template": "custom", "duration": 3,
             "custom": {"html": "brand/video/motion/scenes/orbit.html", "script": "brand/video/motion/scenes/orbit.js"},
             "copy": {"head": "Moves on its own"}},
            {"id": "badge", "template": "custom", "duration": 3, "transitionIn": {"type": "fade"},
             "custom": {"html": "brand/video/motion/scenes/badge.html", "script": "brand/video/motion/scenes/badge.js",
                        "lottie": "brand/video/motion/scenes/badge.json"}}],
    }
    (root / "brand" / "video" / "motion" / "video.json").write_text(json.dumps(piece, indent=2), encoding="utf-8")
    bad = root / "brand" / "video" / "unruly"
    (bad / "scenes").mkdir(parents=True, exist_ok=True)
    (bad / "scenes" / "tick.js").write_text(
        "window.VideoScenes = window.VideoScenes || {};\n"
        "window.VideoScenes.tick = function (el) {\n"
        "  setTimeout(() => { el.style.background = 'red'; }, 500);\n"
        "};\n", encoding="utf-8")
    (bad / "video.json").write_text(json.dumps({
        "schemaVersion": 1, "id": "unruly", "kind": "social", "formats": ["social-1x1"], "fps": 30,
        "scenes": [{"id": "tick", "template": "custom", "duration": 3,
                    "custom": {"script": "brand/video/unruly/scenes/tick.js"}, "copy": {"head": "Ticks"}}]}, indent=2),
        encoding="utf-8")
    from PIL import Image
    art = root / "brand" / "art" / "layers"
    art.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1200, 1200), (200, 40, 40)).save(art / "plate.png")
    Image.new("RGBA", (300, 300), (40, 60, 200, 255)).save(art / "figure.png")
    lay = root / "brand" / "video" / "layers"
    (lay / "scenes").mkdir(parents=True, exist_ok=True)
    (lay / "scenes" / "room.js").write_text(
        "// a layered still: the plate as a CSS background, the figure drifting in front of it\n"
        "window.VideoScenes = window.VideoScenes || {};\n"
        "window.VideoScenes.room = function (el, ctx) {\n"
        "  const plate = document.createElement('div');\n"
        "  plate.style.cssText = 'position:absolute;inset:0;background:url(' + ctx.assets.plate + ') center/cover';\n"
        "  const fig = document.createElement('img');\n"
        "  fig.src = ctx.assets.figure; fig.alt = '';\n"
        "  fig.style.cssText = 'position:absolute;left:10%;bottom:10%;width:20%';\n"
        "  el.append(plate, fig);\n"
        "  fig.animate([{ transform: 'translateX(0)' }, { transform: 'translateX(' + ctx.width * 0.3 + 'px)' }],\n"
        "              { delay: ctx.start, duration: ctx.seconds * 1000, fill: 'both', easing: 'linear' });\n"
        "};\n", encoding="utf-8")
    (lay / "video.json").write_text(json.dumps({
        "schemaVersion": 1, "id": "layers", "kind": "social", "formats": ["social-1x1"], "fps": 30,
        "scenes": [{"id": "room", "template": "custom", "duration": 3,
                    "custom": {"script": "brand/video/layers/scenes/room.js",
                               "assets": {"plate": {"file": "brand/art/layers/plate.png"},
                                          "figure": {"file": "brand/art/layers/figure.png"}}}}]}, indent=2),
        encoding="utf-8")
    print("wrote brand/video/motion, brand/video/unruly and brand/video/layers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
