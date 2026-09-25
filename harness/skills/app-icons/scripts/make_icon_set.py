#!/usr/bin/env python3
"""Generate and audit mobile app icon sets (iOS, Android adaptive/monochrome/notification, Play, web).

  generate  from a transparent master glyph PNG (>= 1024 px) and a background colour:
            ios/AppIcon-1024.png (opaque), android/adaptive-{foreground,background}.png,
            android/monochrome.png, android/notification-96.png, play/icon-512.png,
            web/favicon-{16,32,48}.png, web/favicon.ico, web/apple-touch-icon-180.png,
            web/pwa-{192,512}.png, web/maskable-512.png, expo-icon-snippet.json
  check     audit an Expo app.json (or explicit files) for the common icon defects

Usage:
  python make_icon_set.py generate --master brand/mark.png --bg "#6366f1" --out assets/icons
  python make_icon_set.py check --app-json app.json
Needs Pillow. Specs: references/icon-specs.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

ADAPTIVE_SAFE = 66 / 108      # safe circle diameter / adaptive canvas
MASKABLE_SAFE = 0.80          # PWA maskable safe zone diameter


def hex_rgb(value: str) -> tuple[int, int, int]:
    v = value.lstrip("#")
    if len(v) != 6:
        raise SystemExit(f"--bg must be #RRGGBB, got {value}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def glyph_on(canvas: int, glyph: Image.Image, scale: float, bg: tuple | None) -> Image.Image:
    """Place the glyph's visible content so its longest side is `scale` of the canvas."""
    box = glyph.getbbox() or (0, 0, glyph.width, glyph.height)
    content = glyph.crop(box)
    target = max(1, round(canvas * scale))
    ratio = target / max(content.size)
    content = content.resize((max(1, round(content.width * ratio)), max(1, round(content.height * ratio))), Image.LANCZOS)
    base = Image.new("RGBA", (canvas, canvas), (*bg, 255) if bg else (0, 0, 0, 0))
    base.alpha_composite(content, ((canvas - content.width) // 2, (canvas - content.height) // 2))
    return base


def silhouette(img: Image.Image) -> Image.Image:
    """White glyph keeping only the alpha channel (monochrome and notification icons)."""
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(img.getchannel("A"))
    return white


def generate(args: argparse.Namespace) -> int:
    master = Image.open(args.master).convert("RGBA")
    if min(master.size) < 1024:
        print(f"master is {master.size}; use at least 1024x1024 (export the SVG larger)", file=sys.stderr)
        return 2
    if master.getchannel("A").getextrema() == (255, 255):
        print("master has no transparency; supply the glyph on a transparent background", file=sys.stderr)
        return 2
    bg = hex_rgb(args.bg)
    out: Path = args.out
    s = args.glyph_scale

    def save(img: Image.Image, rel: str, opaque: bool = False) -> None:
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        (img.convert("RGB") if opaque else img).save(p, optimize=True)
        print(f"wrote {p}  {img.size[0]}x{img.size[1]}{'  (opaque)' if opaque else ''}")

    save(glyph_on(1024, master, s, bg), "ios/AppIcon-1024.png", opaque=True)
    save(glyph_on(1024, master, min(s, ADAPTIVE_SAFE * 0.95), None), "android/adaptive-foreground.png")
    save(Image.new("RGBA", (1024, 1024), (*bg, 255)), "android/adaptive-background.png", opaque=True)
    # Silhouettes keep only alpha, so marks drawn with inner colour contrast need a --mono master
    # whose details are cut out (transparent), or they collapse into a solid blob.
    mono = Image.open(args.mono).convert("RGBA") if args.mono else master
    save(silhouette(glyph_on(1024, mono, min(s, ADAPTIVE_SAFE * 0.95), None)), "android/monochrome.png")
    save(silhouette(glyph_on(96, mono, 0.78, None)), "android/notification-96.png")
    save(glyph_on(512, master, s, bg), "play/icon-512.png")
    for px in (16, 32, 48):
        save(glyph_on(px, master, 0.9, bg), f"web/favicon-{px}.png", opaque=True)
    ico = glyph_on(256, master, 0.9, bg).convert("RGB")
    (out / "web").mkdir(parents=True, exist_ok=True)
    ico.save(out / "web/favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"wrote {out / 'web/favicon.ico'}  16/32/48")
    save(glyph_on(180, master, s, bg), "web/apple-touch-icon-180.png", opaque=True)
    save(glyph_on(192, master, s, bg), "web/pwa-192.png", opaque=True)
    save(glyph_on(512, master, s, bg), "web/pwa-512.png", opaque=True)
    save(glyph_on(512, master, MASKABLE_SAFE * 0.7, bg), "web/maskable-512.png", opaque=True)

    snippet = {
        "expo": {
            "icon": f"./{(out / 'ios/AppIcon-1024.png').as_posix()}",
            "android": {"adaptiveIcon": {
                "foregroundImage": f"./{(out / 'android/adaptive-foreground.png').as_posix()}",
                "monochromeImage": f"./{(out / 'android/monochrome.png').as_posix()}",
                "backgroundColor": args.bg}},
            "plugins": [["expo-notifications", {"icon": f"./{(out / 'android/notification-96.png').as_posix()}", "color": args.bg}]],
            "web": {"favicon": f"./{(out / 'web/favicon-48.png').as_posix()}"},
        }
    }
    (out / "expo-icon-snippet.json").write_text(json.dumps(snippet, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out / 'expo-icon-snippet.json'} (merge into app.json; paths are relative to the project root)")
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
                visible = [p for p in rgba.getdata() if p[3] > 32]
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
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="build the platform icon set from a master glyph")
    g.add_argument("--master", type=Path, required=True, help="transparent PNG glyph, >= 1024 px")
    g.add_argument("--bg", required=True, help="background colour #RRGGBB")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--mono", type=Path, help="single-colour master with details cut out (for monochrome and notification icons)")
    g.add_argument("--glyph-scale", type=float, default=0.6, help="glyph size as a share of the full icon (default 0.6)")
    c = sub.add_parser("check", help="audit an Expo app.json")
    c.add_argument("--app-json", type=Path, required=True)
    args = parser.parse_args()
    if args.cmd == "generate":
        return generate(args)
    if not args.app_json.is_file():
        print(f"not found: {args.app_json} (app.config.js projects: run `npx expo config --json > app.json.tmp` first)", file=sys.stderr)
        return 2
    return check(args)


if __name__ == "__main__":
    raise SystemExit(main())
