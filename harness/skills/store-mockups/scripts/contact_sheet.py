#!/usr/bin/env python3
"""Make one review image from a folder of store frames (plus an optional feature graphic).

  grid (default)  thumbnails in rows, feature graphic on top
  --strip         one row with a store-like gutter and rounded corners, the way a store
                  gallery shows a continuous set
  --check-seams   for continuous sets: compare the touching edge columns of neighbouring
                  frames; reports the mean difference and the share of matching rows
                  (objects that cross a seam match; a background change between frames does not)

Usage:
  python contact_sheet.py out/play/phone --feature out/play/feature_graphic_1024x500.png -o contact-sheet.png
  python contact_sheet.py out/play/phone --strip --check-seams -o strip.png
Needs Pillow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageStat
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)


def rounded(img: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def check_seams(files: list[Path]) -> None:
    print("seam                          mean diff   rows matching (objects crossing the seam match; background changes do not)")
    for a, b in zip(files, files[1:]):
        left, right = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        if left.height != right.height:
            print(f"  {a.stem} | {b.stem}: different heights, skipped")
            continue
        edge_a = left.crop((left.width - 1, 0, left.width, left.height))
        edge_b = right.crop((0, 0, 1, right.height))
        delta = ImageChops.difference(edge_a, edge_b)
        diff = sum(ImageStat.Stat(delta).mean) / 3
        raw = delta.tobytes()
        rows = [max(raw[i:i + 3]) for i in range(0, len(raw), 3)]
        match = sum(1 for r in rows if r <= 24) / len(rows)
        print(f"  {a.stem} | {b.stem}: {diff:6.1f}   {match:6.0%}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--feature", type=Path, help="feature graphic shown full width on top (grid mode)")
    parser.add_argument("--cols", type=int, default=4)
    parser.add_argument("--width", type=int, default=300, help="thumbnail width in px")
    parser.add_argument("--strip", action="store_true", help="one row, store-gallery style")
    parser.add_argument("--gutter", type=int, default=16, help="gap between frames in --strip mode (px)")
    parser.add_argument("--check-seams", action="store_true", help="report edge continuity between neighbours")
    parser.add_argument("-o", "--out", type=Path, required=True)
    args = parser.parse_args()

    files = sorted(args.folder.glob("*.png"))
    if not files:
        print(f"no PNGs in {args.folder}", file=sys.stderr)
        return 2
    if args.check_seams:
        check_seams(files)

    gap, w = 20, args.width
    first = Image.open(files[0])
    h = round(first.height * w / first.width)

    if args.strip:
        g = args.gutter
        sheet = Image.new("RGB", (len(files) * w + (len(files) - 1) * g + 2 * gap, h + 2 * gap), (24, 24, 28))
        for i, f in enumerate(files):
            thumb = rounded(Image.open(f).convert("RGB").resize((w, h), Image.LANCZOS), max(6, w // 24))
            sheet.paste(thumb, (gap + i * (w + g), gap), thumb)
    else:
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
