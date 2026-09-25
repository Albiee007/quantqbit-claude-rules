#!/usr/bin/env python3
"""Check store images against the Play and App Store specs (references/store-specs.md).

Point it at an assets root laid out like the store-mockups output:
  <root>/play/phone/*.png  play/tablet7/  play/tablet10/  play/feature_graphic*.png
  <root>/ios/6.9/*.png     ios/6.5/       ios/ipad13/
Missing folders are skipped (reported as INFO). Icons are checked with
--ios-icon / --play-icon. Needs Pillow (pip install pillow).

Usage:
  python check_store_assets.py <root> [--ios-icon assets/icon.png] [--play-icon icon-512.png] [--supports-tablet]
Exit: 0 no errors, 1 errors found, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

MB = 1024 * 1024
IOS_69 = {(1290, 2796), (1320, 2868), (1260, 2736)}
IOS_65 = {(1242, 2688), (1284, 2778)}
IPAD_13 = {(2064, 2752), (2048, 2732)}


def both(sizes: set) -> set:
    return sizes | {(h, w) for (w, h) in sizes}


# slot: (relative folder, allowed sizes or None for rule-based, min, max, store)
SLOTS = {
    "play-phone": ("play/phone", None, 2, 8, "play"),
    "play-tablet7": ("play/tablet7", None, 0, 8, "play"),
    "play-tablet10": ("play/tablet10", None, 0, 8, "play"),
    "ios-6.9": ("ios/6.9", both(IOS_69), 1, 10, "ios"),
    "ios-6.5": ("ios/6.5", both(IOS_65), 1, 10, "ios"),
    "ios-ipad13": ("ios/ipad13", both(IPAD_13), 1, 10, "ios"),
}

errors = warnings = 0


def err(msg: str) -> None:
    global errors
    errors += 1
    print(f"  ERROR  {msg}")


def warn(msg: str) -> None:
    global warnings
    warnings += 1
    print(f"  WARN   {msg}")


def has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or (im.mode == "P" and "transparency" in im.info)


def play_rule(w: int, h: int) -> str | None:
    short, long_ = min(w, h), max(w, h)
    if short < 320 or long_ > 3840:
        return f"{w}x{h}: each side must be 320-3840 px"
    if long_ > 2 * short:
        return f"{w}x{h}: long side is more than twice the short side"
    return None


def check_slot(root: Path, name: str) -> None:
    rel, allowed, lo, hi, store = SLOTS[name]
    folder = root / rel
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg")) if folder.is_dir() else []
    if not files:
        print(f"  INFO   {name}: no images at {rel}/ (skipped)")
        return
    print(f"{name}: {len(files)} image(s) in {rel}/")
    if not lo <= len(files) <= hi:
        err(f"{name}: {len(files)} images; the store allows {lo}-{hi}")
    big = 0
    for f in files:
        im = Image.open(f)
        w, h = im.size
        if allowed is not None and (w, h) not in allowed:
            err(f"{f.name}: {w}x{h} is not an accepted {name} size ({', '.join(f'{a}x{b}' for a, b in sorted(allowed)[:3])} …)")
        if store == "play":
            problem = play_rule(w, h)
            if problem:
                err(f"{f.name}: {problem}")
            elif name == "play-phone" and min(w, h) >= 1080 and max(w, h) * 9 == min(w, h) * 16:
                big += 1
        if has_alpha(im):
            err(f"{f.name}: has an alpha channel ({im.mode}); flatten to RGB")
        if f.stat().st_size > 8 * MB:
            err(f"{f.name}: {f.stat().st_size / MB:.1f} MB (max 8 MB)")
    if name == "play-phone" and big < 4:
        warn(f"play-phone: only {big} screenshot(s) at 9:16 with a short side of 1080+ px; 4 are needed for recommendation eligibility")


def check_feature_graphic(root: Path) -> None:
    hits = sorted((root / "play").glob("feature_graphic*.*")) if (root / "play").is_dir() else []
    if not hits:
        print("  INFO   play feature graphic: none found at play/feature_graphic*.png (required for Play)")
        return
    for f in hits:
        im = Image.open(f)
        print(f"play feature graphic: {f.name}")
        if im.size != (1024, 500):
            err(f"{f.name}: {im.size[0]}x{im.size[1]}; must be 1024x500")
        if has_alpha(im):
            err(f"{f.name}: has alpha; must be JPEG or 24-bit PNG")


def check_icon(path: Path, store: str) -> None:
    if not path.is_file():
        err(f"{store} icon: {path} not found")
        return
    im = Image.open(path)
    print(f"{store} icon: {path}")
    want = (1024, 1024) if store == "ios" else (512, 512)
    if im.size != want:
        err(f"{path.name}: {im.size[0]}x{im.size[1]}; must be {want[0]}x{want[1]}")
    if store == "ios" and has_alpha(im):
        err(f"{path.name}: has alpha; the App Store icon must be opaque")
    if store == "play" and path.stat().st_size > 1024 * 1024:
        err(f"{path.name}: over 1024 KB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="assets root containing play/ and/or ios/")
    parser.add_argument("--ios-icon", type=Path, help="1024x1024 App Store icon to check")
    parser.add_argument("--play-icon", type=Path, help="512x512 Play icon to check")
    parser.add_argument("--supports-tablet", action="store_true", help="the iOS app supports iPad (iPad 13\" required)")
    args = parser.parse_args()
    if not args.root.is_dir():
        print(f"not a folder: {args.root}", file=sys.stderr)
        return 2

    for slot in SLOTS:
        check_slot(args.root, slot)
    check_feature_graphic(args.root)
    if (args.root / "ios").is_dir() and not any((args.root / "ios" / s).is_dir() for s in ("6.9",)):
        err("ios/: no 6.9\" screenshots (required for iPhone apps)")
    if args.supports_tablet and not (args.root / "ios" / "ipad13").is_dir():
        err("ios/ipad13/: missing, but the app supports iPad")
    if args.ios_icon:
        check_icon(args.ios_icon, "ios")
    if args.play_icon:
        check_icon(args.play_icon, "play")

    print(f"\n{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
