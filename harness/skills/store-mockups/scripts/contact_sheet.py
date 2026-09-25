#!/usr/bin/env python3
"""Make one review image from a folder of store frames (plus an optional feature graphic).

Usage:
  python contact_sheet.py out/play/phone --feature out/play/feature_graphic_1024x500.png -o contact-sheet.png
  python contact_sheet.py out/ios/6.9 --cols 4 --width 320 -o ios-sheet.png
Needs Pillow.
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--feature", type=Path, help="feature graphic shown full width on top")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--width", type=int, default=300, help="thumbnail width in px")
    parser.add_argument("-o", "--out", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(args.folder.glob("*.png"))
    if not files:
        print(f"no PNGs in {args.folder}", file=sys.stderr)
        return 2
    gap, w = 20, args.width
    first = Image.open(files[0])
    h = round(first.height * w / first.width)
    cols = min(args.cols, len(files))
    rows = (len(files) + cols - 1) // cols
    sheet_w = cols * w + (cols + 1) * gap
    top = gap
    fg = None
    if args.feature and args.feature.is_file():
        fg = Image.open(args.feature).convert("RGB")
        fg_w = sheet_w - 2 * gap
        fg = fg.resize((fg_w, round(fg.height * fg_w / fg.width)), Image.LANCZOS)
        top += fg.height + gap
    sheet = Image.new("RGB", (sheet_w, top + rows * (h + gap)), "white")
    if fg:
        sheet.paste(fg, (gap, gap))
    for i, f in enumerate(files):
        thumb = Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS)
        sheet.paste(thumb, (gap + (i % cols) * (w + gap), top + (i // cols) * (h + gap)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"wrote {args.out} ({sheet.width}x{sheet.height}, {len(files)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
