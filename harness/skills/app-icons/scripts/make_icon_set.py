#!/usr/bin/env python3
"""Generate, preview and audit mobile app icon sets (iOS, Android adaptive/monochrome/notification, Play, web).

  generate  from a transparent master glyph PNG (>= 1024 px) and a background:
            ios/AppIcon-1024.png (opaque), android/adaptive-{foreground,background}.png,
            android/monochrome.png, android/notification-96.png, play/icon-512.png,
            web/favicon-{16,32,48}.png, web/favicon.ico, web/apple-touch-icon-180.png,
            web/pwa-{192,512}.png, web/maskable-512.png, expo-icon-snippet.json
            Background: --bg (solid) or --bg-style linear --bg --bg2 [--angle] (interpolated in OKLab),
            or --from-direction <project>: the owner-approved icon concept supplies the background,
            glyph scale and offset (and refuses when the concept is not approved).
            --glyph-offset x,y moves the glyph (fractions of the tile); adaptive and maskable layers
            keep it inside their safe zones. --no-web skips the web/ set.
            Files are generated into a temporary folder, checked, then moved into --out.
  preview   one review sheet for a master and background: 16-180 px on light and dark wallpapers,
            circle and squircle masks, and the monochrome silhouette. Writes only the sheet.
  check     audit an Expo app.json (or explicit files) for the common icon defects

Mark contrast: the glyph's main colour against the background under it is always measured and
printed. A launcher icon is branding, so this is not a WCAG requirement; a project can still set a
target (--mark-contrast, or "qualityTarget" in the icon concept), and then a lower value fails.

Usage:
  python make_icon_set.py generate --master brand/png/mark-2048.png --bg "#2f6b5a" --out assets/icons [--no-web]
  python make_icon_set.py generate --master brand/png/mark-2048.png --bg-style linear --bg "#2f6b5a" --bg2 "#173a31" --angle 160 --out assets/icons
  python make_icon_set.py generate --master brand/png/mark-2048.png --from-direction . --out assets/icons
  python make_icon_set.py preview  --master brand/png/mark-2048.png (--bg ... | --from-direction . [--concept F]) -o out/icon-preview.png
  python make_icon_set.py check --app-json app.json
Needs Pillow. Specs: references/icon-specs.md; composition choices: references/composition.md.
Exit codes: 0 done, 1 a check or gate failed, 2 bad arguments or a missing file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    import harnesslib
    from harnesslib import color as col
    from harnesslib import direction as dl
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import InputError, UsageError, canonical, run_id, sha256_file, sha256_text
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)
try:
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

ADAPTIVE_SAFE = 66 / 108      # safe circle diameter / adaptive canvas
MASKABLE_SAFE = 0.80          # PWA maskable safe zone diameter


def hex_rgb(value: str, flag: str = "--bg") -> tuple[int, int, int]:
    try:
        rgba = col.parse(value)
    except col.ColorError:
        raise UsageError(f"{flag} must be a colour such as #RRGGBB, got {value}") from None
    return tuple(round(c * 255) for c in col.clip(rgba))  # type: ignore[return-value]


class Background:
    """A solid colour or a linear gradient (OKLab or sRGB interpolation, CSS angle convention)."""

    def __init__(self, recipe: str, stops: list[str], angle: float = 180, space: str = "oklab") -> None:
        if recipe not in ("solid", "linear"):
            raise UsageError(f"background recipe must be solid or linear, got {recipe}")
        if recipe == "linear" and len(stops) < 2:
            raise UsageError("a linear background needs two colours (--bg and --bg2)")
        self.recipe, self.stops, self.angle, self.space = recipe, stops, angle, space
        self.rgb = [hex_rgb(s) for s in stops]

    def image(self, size: int) -> Image.Image:
        if self.recipe == "solid":
            return Image.new("RGBA", (size, size), (*self.rgb[0], 255))
        stops = [tuple(c / 255 for c in s) for s in self.rgb]
        lut = Image.new("RGB", (256, 1))
        lut.putdata([tuple(round(c * 255) for c in col.interpolate(stops, i / 255, self.space)) for i in range(256)])
        d = int(size * 1.5) + 2
        strip = lut.resize((d, d), Image.BILINEAR)
        rot = strip.rotate(90 - self.angle, resample=Image.BICUBIC, expand=False)
        off = (d - size) // 2
        return rot.crop((off, off, off + size, off + size)).convert("RGBA")

    def mean(self) -> str:
        if self.recipe == "solid":
            return self.stops[0]
        stops = [tuple(c / 255 for c in s) for s in self.rgb]
        return col.to_hex(col.interpolate(stops, 0.5, self.space))

    def describe(self) -> str:
        return self.stops[0] if self.recipe == "solid" else f"linear {self.angle:g}deg {', '.join(self.stops)} in {self.space}"


def glyph_on(canvas: int, glyph: Image.Image, scale: float, bg: Background | None, offset: tuple[float, float] = (0, 0),
             safe: float | None = None) -> Image.Image:
    """Place the glyph's visible content so its longest side is `scale` of the canvas, moved by offset
    (fractions of the canvas). With `safe`, the content stays inside the central circle of that diameter."""
    box = glyph.getbbox() or (0, 0, glyph.width, glyph.height)
    content = glyph.crop(box)
    target = max(1, round(canvas * scale))
    ratio = target / max(content.size)
    content = content.resize((max(1, round(content.width * ratio)), max(1, round(content.height * ratio))), Image.LANCZOS)
    base = bg.image(canvas) if bg else Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    ox, oy = offset
    if safe is not None:
        half_diag = (content.width ** 2 + content.height ** 2) ** 0.5 / 2 / canvas
        room = max(0.0, safe / 2 - half_diag)
        dist = (ox * ox + oy * oy) ** 0.5
        if dist > room and dist > 0:
            ox, oy = ox * room / dist, oy * room / dist
    x = round((canvas - content.width) / 2 + ox * canvas)
    y = round((canvas - content.height) / 2 + oy * canvas)
    base.alpha_composite(content, (x, y))
    return base


def pixels(img: Image.Image):
    """Pixel values in order (Pillow 12 renamed getdata to get_flattened_data)."""
    return img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()


def silhouette(img: Image.Image) -> Image.Image:
    """White glyph keeping only the alpha channel (monochrome and notification icons)."""
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(img.getchannel("A"))
    return white


def mark_contrast(master: Image.Image, scale: float, bg: Background, offset: tuple[float, float]) -> float:
    """Lowest contrast between the glyph's main colour and the background under the glyph."""
    size = 256
    glyph = glyph_on(size, master, scale, None, offset)
    alpha = glyph.getchannel("A")
    box = alpha.getbbox()
    if not box:
        raise InputError("the master glyph is empty")
    opaque = [p[:3] for p in pixels(glyph) if p[3] > 200]
    if not opaque:
        raise InputError("the master glyph has no opaque pixels")
    q = Image.new("RGB", (len(opaque), 1))
    q.putdata(opaque)
    pal = q.quantize(colors=4)
    counts = sorted(pal.getcolors() or [], reverse=True)
    palette = pal.getpalette() or []
    main = tuple(palette[counts[0][1] * 3: counts[0][1] * 3 + 3])
    fg = tuple(c / 255 for c in main)
    bgimg = bg.image(size).crop(box).convert("RGB")
    step = max(1, bgimg.width // 16)
    ratios = [col.contrast_ratio(fg, tuple(c / 255 for c in bgimg.getpixel((x, y))))
              for y in range(0, bgimg.height, step) for x in range(0, bgimg.width, step)]
    return min(ratios)


def from_direction(project: str, concept: str | None, production: bool) -> tuple[dict, dict, dl.Project]:
    root = Path(project).resolve()
    if not (root / dl.DIRECTION).is_file():
        raise UsageError(f"--from-direction {project}: no {dl.DIRECTION} there")
    p = dl.load_project(root)
    if production:
        prod = dl.production(p, "icon")
        info = {"direction": prod.gate.direction[0] if prod.gate.direction else None,
                "concept": prod.gate.concept[0] if prod.gate.concept else None, "approvals": prod.gate.records,
                "concept_rel": prod.concept_rel}
        return prod.resolved, info, p
    rel, _, r = dl.preview(p, "icon", concept)
    g = dl.gate(p, "icon")
    print(f"concept: {rel} ({'approved' if g.ok and g.concept_rel == rel else 'DRAFT, not approved for production'})")
    return r, {"concept_rel": rel}, p


def parse_offset(text: str | None) -> tuple[float, float]:
    if not text:
        return (0.0, 0.0)
    try:
        x, y = (float(v) for v in text.split(","))
    except ValueError:
        raise UsageError("--glyph-offset must be x,y (fractions of the tile, e.g. 0,0.03)") from None
    if not (-0.1 <= x <= 0.1 and -0.1 <= y <= 0.1):
        raise UsageError("--glyph-offset values must be within -0.1..0.1")
    return x, y


def setup(args: argparse.Namespace, production: bool) -> tuple[Image.Image, Background, float, tuple[float, float], float | None, dict, dl.Project | None]:
    if not Path(args.master).is_file():
        raise UsageError(f"--master {args.master}: file not found")
    master = Image.open(args.master).convert("RGBA")
    if min(master.size) < 1024:
        raise UsageError(f"master is {master.size}; use at least 1024x1024 (export the SVG larger)")
    if master.getchannel("A").getextrema() == (255, 255):
        raise UsageError("master has no transparency; supply the glyph on a transparent background")
    if args.from_direction:
        if args.bg or args.bg2 or args.bg_style != "solid":
            raise UsageError("--from-direction supplies the background; drop --bg/--bg2/--bg-style")
        r, info, p = from_direction(args.from_direction, getattr(args, "concept", None), production)
        b = r["background"]
        bg = Background(b["recipe"], [b["color"]] if b["recipe"] == "solid" else b["stops"], b.get("angle", 180), b.get("space", "oklab"))
        target = (r.get("qualityTarget") or {}).get("markContrast")
        return master, bg, r["glyphScale"], tuple(r["glyphOffset"]), target, info, p  # type: ignore[return-value]
    if not args.bg:
        raise UsageError("give --bg (and --bg2 for a linear background), or --from-direction")
    stops = [args.bg] + ([args.bg2] if args.bg2 else [])
    bg = Background(args.bg_style, stops, args.angle, args.space)
    if not 0.3 <= args.glyph_scale <= 0.8:
        raise UsageError("--glyph-scale must be 0.3-0.8")
    return master, bg, args.glyph_scale, parse_offset(args.glyph_offset), args.mark_contrast, {}, None


def report_mark(master: Image.Image, scale: float, bg: Background, offset: tuple[float, float], target: float | None) -> bool:
    ratio = mark_contrast(master, scale, bg, offset)
    if target is None:
        print(f"mark contrast: {col.display_ratio(ratio)}:1 (glyph's main colour on the background under it; "
              "branding, so no WCAG threshold applies unless the project sets one)")
        return True
    ok = ratio >= target
    print(f"mark contrast: {'PASS' if ok else 'FAIL'} {col.display_ratio(ratio, target)}:1 vs the project's target "
          f"{target:g}:1 (a project quality target, not a WCAG requirement)")
    return ok


def generate(args: argparse.Namespace) -> int:
    production = bool(args.from_direction)
    master, bg, s, offset, target, info, project = setup(args, production)
    out: Path = args.out
    started = dl.now_utc()
    if not report_mark(master, s, bg, offset, target):
        print("nothing written: the mark misses the project's contrast target", file=sys.stderr)
        return 1
    mono = Image.open(args.mono).convert("RGBA") if args.mono else master
    files: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)

        def save(img: Image.Image, rel: str, opaque: bool = False) -> None:
            p = stage / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            (img.convert("RGB") if opaque else img).save(p, optimize=True)
            files.append(rel)
            print(f"ok    {rel}  {img.size[0]}x{img.size[1]}{'  (opaque)' if opaque else ''}")

        fg_scale = min(s, ADAPTIVE_SAFE * 0.95)
        save(glyph_on(1024, master, s, bg, offset), "ios/AppIcon-1024.png", opaque=True)
        save(glyph_on(1024, master, fg_scale, None, offset, safe=ADAPTIVE_SAFE), "android/adaptive-foreground.png")
        save(bg.image(1024), "android/adaptive-background.png", opaque=True)
        # Silhouettes keep only alpha, so marks drawn with inner colour contrast need a --mono master
        # whose details are cut out (transparent), or they collapse into a solid blob.
        save(silhouette(glyph_on(1024, mono, fg_scale, None, offset, safe=ADAPTIVE_SAFE)), "android/monochrome.png")
        save(silhouette(glyph_on(96, mono, 0.78, None)), "android/notification-96.png")
        save(glyph_on(512, master, s, bg, offset), "play/icon-512.png")
        if not args.no_web:
            for px in (16, 32, 48):
                save(glyph_on(px, master, 0.9, bg), f"web/favicon-{px}.png", opaque=True)
            ico = glyph_on(256, master, 0.9, bg).convert("RGB")
            ico.save(stage / "web/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
            files.append("web/favicon.ico")
            print("ok    web/favicon.ico  16/32/48")
            save(glyph_on(180, master, s, bg, offset), "web/apple-touch-icon-180.png", opaque=True)
            save(glyph_on(192, master, s, bg, offset), "web/pwa-192.png", opaque=True)
            save(glyph_on(512, master, s, bg, offset), "web/pwa-512.png", opaque=True)
            save(glyph_on(512, master, MASKABLE_SAFE * 0.7, bg, offset, safe=MASKABLE_SAFE), "web/maskable-512.png", opaque=True)
        tint = bg.mean()
        adaptive = {"foregroundImage": f"./{(out / 'android/adaptive-foreground.png').as_posix()}",
                    "monochromeImage": f"./{(out / 'android/monochrome.png').as_posix()}",
                    "backgroundColor": tint}
        if bg.recipe != "solid":
            adaptive["backgroundImage"] = f"./{(out / 'android/adaptive-background.png').as_posix()}"
        snippet = {"expo": {
            "icon": f"./{(out / 'ios/AppIcon-1024.png').as_posix()}",
            "android": {"adaptiveIcon": adaptive},
            "plugins": [["expo-notifications", {"icon": f"./{(out / 'android/notification-96.png').as_posix()}", "color": tint}]],
        }}
        if not args.no_web:
            snippet["expo"]["web"] = {"favicon": f"./{(out / 'web/favicon-48.png').as_posix()}"}
        (stage / "expo-icon-snippet.json").write_text(json.dumps(snippet, indent=2) + "\n", encoding="utf-8")
        files.append("expo-icon-snippet.json")
        for rel in files:
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stage / rel), str(dest))
    print(f"wrote {len(files)} file(s) to {out} (background {bg.describe()}; merge expo-icon-snippet.json into app.json; "
          "paths are relative to the project root)")
    if production and project is not None:
        write_manifest(project, info, out, files, started, bg, s, offset, target)
    return 0


def write_manifest(p: dl.Project, info: dict, out: Path, files: list[str], started: str, bg: Background, s: float,
                   offset: tuple[float, float], target: float | None) -> None:
    outputs = []
    for rel in files:
        f = out / rel
        entry = {"path": Path(os.path.relpath(f, p.root)).as_posix(), "sha256": sha256_file(f), "bytes": f.stat().st_size}
        if f.suffix == ".png":
            with Image.open(f) as im:
                entry["size"] = list(im.size)
        outputs.append(entry)
    checks = {"mark-contrast": {"result": "PASS" if target is not None else "SKIPPED",
                                "detail": f"project target {target}" if target is not None else "no project target set"},
              "on-device": {"result": "SKIPPED", "detail": "launcher masks, themed icons and notifications need a device"}}
    manifest = {"schemaVersion": 1, "runId": run_id(), "family": "icon", "mode": "production", "tool": "make_icon_set.py",
                "startedAt": started, "finishedAt": dl.now_utc(), "engine": {"api": harnesslib.API_VERSION},
                "inputs": {"config": sha256_text(canonical({"bg": bg.describe(), "scale": s, "offset": list(offset)})),
                           "direction": info.get("direction"), "concept": info.get("concept")},
                "approvals": info.get("approvals", []), "fonts": [], "seed": None, "outputs": outputs, "checks": checks,
                "status": "review-required"}
    path = dl.write_run_manifest(p.root, manifest)
    print(f"run manifest: {path.relative_to(p.root).as_posix()} (review-required: on-device checks remain)")


def squircle_mask(size: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.23), fill=255)
    return m


def preview(args: argparse.Namespace) -> int:
    master, bg, s, offset, target, _, _ = setup(args, production=False)
    report_mark(master, s, bg, offset, target)
    sizes = [16, 29, 40, 48, 64, 180]
    walls = [(242, 242, 242), (28, 28, 30)]
    pad = 24
    W = pad + sum(x + pad for x in sizes) + 180 * 3 + pad * 3
    H = pad + (180 + pad) * 2
    sheet = Image.new("RGB", (W, H), (128, 128, 128))
    tile = glyph_on(1024, master, s, bg, offset)
    fg = glyph_on(1024, master, min(s, ADAPTIVE_SAFE * 0.95), None, offset, safe=ADAPTIVE_SAFE)
    for row, wall in enumerate(walls):
        y0 = pad + row * (180 + pad)
        ImageDraw.Draw(sheet).rectangle((0, y0 - pad // 2, W, y0 + 180 + pad // 2), fill=wall)
        x = pad
        for px in sizes:
            sheet.paste(tile.resize((px, px), Image.LANCZOS).convert("RGB"), (x, y0 + 180 - px))
            x += px + pad
        adaptive = bg.image(1024)
        adaptive.alpha_composite(fg)
        circle = Image.new("L", (180, 180), 0)
        ImageDraw.Draw(circle).ellipse((0, 0, 179, 179), fill=255)
        for mask in (circle, squircle_mask(180)):
            sheet.paste(adaptive.resize((180, 180), Image.LANCZOS).convert("RGB"), (x, y0), mask)
            x += 180 + pad
        mono = silhouette(glyph_on(180, Image.open(args.mono).convert("RGBA") if args.mono else master, min(s, ADAPTIVE_SAFE * 0.95), None))
        tinted = Image.new("RGBA", (180, 180), (*((60, 60, 60) if row == 0 else (230, 230, 230)), 0))
        tinted.putalpha(mono.getchannel("A"))
        sheet.paste(tinted.convert("RGB"), (x, y0), tinted.getchannel("A"))
    args.o.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.o, optimize=True)
    print(f"wrote {args.o}: sizes {', '.join(map(str, sizes))} px, circle and squircle masks, monochrome; light and dark "
          f"wallpapers (background {bg.describe()})")
    return 0


class Audit:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str]] = []

    def add(self, sev: str, msg: str) -> None:
        self.rows.append((sev, msg))
        print(f"  {sev:<7} {msg}")


def opaque_everywhere(img: Image.Image) -> bool:
    return img.mode not in ("RGBA", "LA", "PA") or img.getchannel("A").getextrema()[0] == 255


def plugin_config(plugins: list, name: str) -> dict | None:
    for p in plugins or []:
        if p == name:
            return {}
        if isinstance(p, list) and p and p[0] == name:
            return p[1] if len(p) > 1 and isinstance(p[1], dict) else {}
    return None


def check(args: argparse.Namespace) -> int:
    audit = Audit()
    root = args.app_json.parent
    cfg = json.loads(args.app_json.read_text(encoding="utf-8")).get("expo", {})

    def img_at(rel: str | None, what: str) -> Image.Image | None:
        if not rel:
            return None
        p = (root / rel).resolve()
        if not p.is_file():
            audit.add("HIGH", f"{what}: {rel} not found")
            return None
        return Image.open(p)

    icon = img_at(cfg.get("ios", {}).get("icon") if isinstance(cfg.get("ios", {}).get("icon"), str) else cfg.get("icon"), "icon")
    if icon is None and not cfg.get("icon"):
        audit.add("BLOCKER", "no icon configured (expo.icon)")
    elif icon is not None:
        if icon.size != (1024, 1024):
            audit.add("HIGH", f"icon is {icon.size[0]}x{icon.size[1]}; use 1024x1024")
        if not opaque_everywhere(icon):
            audit.add("BLOCKER", "icon has transparent pixels; the App Store icon must be opaque (flatten it)")
        else:
            audit.add("OK", "icon: 1024x1024, opaque")
    if not isinstance(cfg.get("ios", {}).get("icon"), dict):
        audit.add("INFO", "no iOS 18 dark/tinted variants (expo.ios.icon {light, dark, tinted}); optional")

    adaptive = cfg.get("android", {}).get("adaptiveIcon", {})
    fg = img_at(adaptive.get("foregroundImage"), "adaptive foreground")
    if not adaptive:
        audit.add("MEDIUM", "no android.adaptiveIcon; launchers will shrink the legacy icon into a white shape")
    elif fg is not None:
        if opaque_everywhere(fg):
            audit.add("MEDIUM", "adaptive foreground is fully opaque; the launcher mask crops it and backgroundColor never shows. "
                                "Use the glyph on transparency, within the central 66/108 safe zone")
        else:
            box = fg.getchannel("A").getbbox()
            if box:
                extent = max(box[2] - box[0], box[3] - box[1]) / max(fg.size)
                if extent > ADAPTIVE_SAFE + 0.02:
                    audit.add("MEDIUM", f"adaptive foreground content spans {extent:.0%} of the canvas; keep it within ~61% (66/108 dp) or masks clip it")
                else:
                    audit.add("OK", f"adaptive foreground: transparent, content {extent:.0%} of canvas")
    if adaptive and not adaptive.get("backgroundColor") and not adaptive.get("backgroundImage"):
        audit.add("LOW", "adaptiveIcon has no backgroundColor/backgroundImage")
    if adaptive and adaptive.get("backgroundImage"):
        img_at(adaptive.get("backgroundImage"), "adaptive background image")
    if adaptive and not adaptive.get("monochromeImage"):
        audit.add("MEDIUM", "no adaptiveIcon.monochromeImage; Android 13+ themed icons fall back to the full-colour icon")

    notif = plugin_config(cfg.get("plugins", []), "expo-notifications")
    notif_icon = (notif or {}).get("icon") or cfg.get("notification", {}).get("icon")
    if notif is not None or cfg.get("notification"):
        n = img_at(notif_icon, "notification icon") if notif_icon else None
        if not notif_icon:
            audit.add("MEDIUM", "expo-notifications has no icon; Android shows the app icon as a grey/white square in the status bar. "
                                "Add a 96x96 white-on-transparent silhouette")
        elif n is not None:
            rgba = n.convert("RGBA")
            if opaque_everywhere(rgba):
                audit.add("HIGH", "notification icon has no transparency; Android renders it as a solid square")
            else:
                visible = [p for p in pixels(rgba) if p[3] > 32]
                non_white = sum(1 for r, g, b, _ in visible if min(r, g, b) < 200)
                if visible and non_white / len(visible) > 0.05:
                    audit.add("LOW", "notification icon is not white; Android ignores the colour and uses only the alpha")
                else:
                    audit.add("OK", "notification icon: white on transparent")

    splash = plugin_config(cfg.get("plugins", []), "expo-splash-screen")
    if splash is None and not cfg.get("splash"):
        audit.add("LOW", "no splash configuration")
    elif splash is not None and not splash.get("dark"):
        audit.add("INFO", "splash has no dark variant")

    fav = img_at(cfg.get("web", {}).get("favicon"), "web favicon")
    if fav is not None and max(fav.size) < 48:
        audit.add("LOW", f"web favicon is {fav.size[0]}x{fav.size[1]}; ship 48+ (and 180 apple-touch, 192/512 PWA)")

    worst = {"BLOCKER": 3, "HIGH": 2, "MEDIUM": 1}
    score = max((worst.get(s, 0) for s, _ in audit.rows), default=0)
    print(f"\n{sum(1 for s, _ in audit.rows if s in worst)} finding(s) at MEDIUM or above")
    return 1 if score >= 2 else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("generate", "preview"):
        g = sub.add_parser(name, help="build the platform icon set from a master glyph" if name == "generate"
                           else "a review sheet for a master and background")
        g.add_argument("--master", type=Path, required=True, help="transparent PNG glyph, >= 1024 px")
        g.add_argument("--bg", help="background colour (#RRGGBB); the first stop of a linear background")
        g.add_argument("--bg2", help="second colour of a linear background")
        g.add_argument("--bg-style", choices=["solid", "linear"], default="solid")
        g.add_argument("--angle", type=float, default=180, help="linear background direction, CSS degrees (180 = top to bottom)")
        g.add_argument("--space", choices=["oklab", "srgb"], default="oklab", help="gradient interpolation space")
        g.add_argument("--glyph-scale", type=float, default=0.6, help="glyph size as a share of the full icon (default 0.6)")
        g.add_argument("--glyph-offset", help="x,y glyph offset as fractions of the tile (-0.1..0.1)")
        g.add_argument("--mono", type=Path, help="single-colour master with details cut out (for monochrome and notification icons)")
        g.add_argument("--mark-contrast", type=float, help="a project target for the mark's contrast (not a WCAG requirement)")
        g.add_argument("--from-direction", metavar="PROJECT", help="take background, scale and offset from the approved icon concept")
        if name == "generate":
            g.add_argument("--out", type=Path, required=True)
            g.add_argument("--no-web", action="store_true", help="skip favicon/PWA icons (no web target)")
        else:
            g.add_argument("--concept", help="with --from-direction: a draft icon concept file (default: the selected one)")
            g.add_argument("-o", type=Path, required=True, help="the sheet to write")
    c = sub.add_parser("check", help="audit an Expo app.json")
    c.add_argument("--app-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.cmd == "generate":
            return generate(args)
        if args.cmd == "preview":
            return preview(args)
        if not args.app_json.is_file():
            raise UsageError(f"not found: {args.app_json} (app.config.js projects: run `npx expo config --json > app.json.tmp` first)")
        return check(args)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
