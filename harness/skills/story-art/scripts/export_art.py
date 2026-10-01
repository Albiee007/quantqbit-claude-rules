#!/usr/bin/env python3
"""Export approved story art for the web, and build a contact sheet for review.

  export  every PNG/JPG in SRC_DIR (file stem = scene name, e.g. trip.png) becomes
          <prefix>-<scene>-<width>.webp and .avif at each width. WebP steps its
          quality down from 82 until the file fits the width's budget; AVIF steps
          down until it is under the budget and under 80% of the WebP size. Without
          AVIF support in Pillow only WebP is written (a note goes to stderr).
          Two sources with one stem (trip.png, trip.jpg) are refused. With
          --manifest the entries are merged into {"files": {name: {"width",
          "height"}}}; other keys in that file are kept. The manifest is checked
          before encoding; nothing is written unless every file meets its budget,
          and then the images and manifest are staged and moved into place together.
  sheet   one review image from the files in DIR matching --glob, labelled with
          their names.

Usage:
  python export_art.py export art-src public/marketing --prefix art --widths 640,1200 \\
      --budget 1200=120000,640=50000 --manifest public/marketing/manifest.json
  python export_art.py sheet public/marketing out/story-art/contact-sheet.png --glob 'art-*-1200.webp'
Exit codes: 0 ok, 1 the art can't be exported as asked (a budget, the AVIF ratio, or a width
wider than the source), 2 bad input.
Needs Pillow (AVIF needs Pillow 11.3+ or a build with libavif).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, features
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

SOURCE_SUFFIXES = {".png", ".jpg", ".jpeg"}
SCENE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
WEBP_QUALITIES = range(82, 39, -4)   # 82, 78, … 42
AVIF_QUALITIES = range(70, 24, -5)   # 70, 65, … 25
AVIF_MAX_RATIO = 0.8                 # AVIF must be under 80% of the WebP size


class ExportError(Exception):
    """The art can't be exported as asked; nothing has been written."""


def parse_widths(text: str) -> list[int]:
    try:
        widths = sorted({int(w) for w in text.split(",") if w.strip()})
    except ValueError:
        raise argparse.ArgumentTypeError(f"widths must be integers, e.g. 640,1200 (got {text!r})")
    if not widths or widths[0] <= 0:
        raise argparse.ArgumentTypeError("widths must be positive")
    return widths


def parse_budget(text: str) -> dict[int, int]:
    budget: dict[int, int] = {}
    for part in filter(None, (p.strip() for p in text.split(","))):
        width, _, size = part.partition("=")
        if not (width.isdigit() and size.isdigit()):
            raise argparse.ArgumentTypeError(f"budget entries are WIDTH=BYTES, e.g. 1200=120000 (got {part!r})")
        budget[int(width)] = int(size)
    return budget


def encode(img: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, quality=quality)
    return buf.getvalue()


def smallest_fit(img: Image.Image, fmt: str, qualities: range, limit: int) -> tuple[bytes, int]:
    """Highest quality whose encoding is under limit bytes."""
    for q in qualities:
        data = encode(img, fmt, q)
        if len(data) <= limit:
            return data, q
    raise ExportError(f"{fmt} cannot get under {limit:,} bytes even at quality {qualities[-1]}")


def export_scene(src: Path, widths: list[int], budget: dict[int, int], prefix: str,
                 avif: bool) -> list[tuple[str, bytes, int, int, int]]:
    """Encode one source; returns (name, data, width, height, quality) per file."""
    with Image.open(src) as opened:
        opened.load()
        img = opened.convert("RGBA" if "A" in opened.getbands() else "RGB")
    out = []
    for w in widths:
        if w > img.width:
            raise ExportError(f"{src.name} is {img.width} px wide; {w} px would upscale it")
        h = round(img.height * w / img.width)
        frame = img.resize((w, h), Image.LANCZOS)
        limit = budget.get(w, sys.maxsize)
        base = f"{prefix}-{src.stem}-{w}"
        try:
            webp, wq = smallest_fit(frame, "WEBP", WEBP_QUALITIES, limit)
            out.append((f"{base}.webp", webp, w, h, wq))
            if avif:
                cap = min(limit, int(len(webp) * AVIF_MAX_RATIO))
                data, aq = smallest_fit(frame, "AVIF", AVIF_QUALITIES, cap)
                out.append((f"{base}.avif", data, w, h, aq))
        except ExportError as exc:
            raise ExportError(f"{base}: {exc}") from None
    return out


def load_manifest(path: Path) -> dict:
    """The existing manifest ({} if absent); ExportError if it can't be merged into."""
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExportError(f"{path}: {exc}") from None
    if not isinstance(doc, dict) or not isinstance(doc.get("files", {}), dict):
        raise ExportError(f"{path}: expected {{\"files\": {{...}}}}")
    return doc


def write_staged(targets: list[tuple[Path, bytes]]) -> None:
    """Write every file to a hidden sibling first, then move them all into place."""
    staged: list[tuple[Path, Path]] = []
    try:
        for path, data in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".{path.name}.tmp")
            tmp.write_bytes(data)
            staged.append((tmp, path))
    except OSError:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)
        raise
    for tmp, path in staged:
        os.replace(tmp, path)


def cmd_export(args: argparse.Namespace) -> int:
    if not SCENE_NAME.match(args.prefix):
        print(f"--prefix must be lowercase letters, digits and hyphens (got {args.prefix!r})", file=sys.stderr)
        return 2
    sources = sorted(p for p in args.src_dir.glob("*") if p.suffix.lower() in SOURCE_SUFFIXES)
    if not sources:
        print(f"no PNG or JPG sources in {args.src_dir}", file=sys.stderr)
        return 2
    bad = [p.name for p in sources if not SCENE_NAME.match(p.stem)]
    if bad:
        print(f"rename these to lowercase-hyphen scene names (the stem becomes the file name): {', '.join(bad)}",
              file=sys.stderr)
        return 2
    stems: dict[str, list[str]] = {}
    for p in sources:
        stems.setdefault(p.stem, []).append(p.name)
    dupes = [" and ".join(names) for names in stems.values() if len(names) > 1]
    if dupes:
        print(f"one source per scene name (they would write the same files): {'; '.join(dupes)}", file=sys.stderr)
        return 2
    manifest: dict = {}
    if args.manifest:
        try:
            manifest = load_manifest(args.manifest)
        except ExportError as exc:
            print(f"manifest can't be merged into, nothing written: {exc}", file=sys.stderr)
            return 2
    avif = features.check("avif")
    if not avif:
        print("note: this Pillow has no AVIF support; writing WebP only (pip install -U pillow)", file=sys.stderr)

    try:
        files = [f for src in sources for f in export_scene(src, args.widths, args.budget, args.prefix, avif)]
    except ExportError as exc:
        print(f"export failed, nothing written: {exc}", file=sys.stderr)
        return 1

    targets = [(args.out_dir / name, data) for name, data, *_ in files]
    if args.manifest:
        manifest.setdefault("files", {}).update({n: {"width": w, "height": h} for n, _, w, h, _ in files})
        targets.append((args.manifest, (json.dumps(manifest, indent=2) + "\n").encode("utf-8")))
    try:
        write_staged(targets)
    except OSError as exc:
        print(f"export failed, nothing written: {exc}", file=sys.stderr)
        return 1

    print(f"{'file':<34} {'size':>9} {'quality':>7} {'budget':>9}")
    for name, data, w, _, q in files:
        limit = args.budget.get(w)
        print(f"{name:<34} {len(data):>9,} {q:>7} {f'{limit:,}' if limit else '-':>9}")
    if args.manifest:
        print(f"manifest: {len(files)} entries merged into {args.manifest}")
    print(f"{len(files)} files written to {args.out_dir}")
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    files = sorted(args.dir.glob(args.glob))
    if not files:
        print(f"no files matching {args.glob!r} in {args.dir}", file=sys.stderr)
        return 2
    w, gap, label = args.width, 20, 24
    thumbs = []
    for f in files:
        with Image.open(f) as img:
            thumbs.append(img.convert("RGB").resize((w, round(img.height * w / img.width)), Image.LANCZOS))
    cols = min(args.cols, len(thumbs))
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(t.height for t in thumbs) + label
    sheet = Image.new("RGB", (cols * w + (cols + 1) * gap, rows * cell_h + (rows + 1) * gap), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for i, (f, thumb) in enumerate(zip(files, thumbs)):
        x, y = gap + (i % cols) * (w + gap), gap + (i // cols) * (cell_h + gap)
        sheet.paste(thumb, (x, y))
        draw.text((x, y + thumb.height + 6), f.name, fill=(230, 230, 235))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"wrote {args.out} ({sheet.width}x{sheet.height}, {len(files)} images)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="AVIF + WebP at each width, within budgets")
    ex.add_argument("src_dir", type=Path)
    ex.add_argument("out_dir", type=Path)
    ex.add_argument("--prefix", default="art")
    ex.add_argument("--widths", type=parse_widths, default=parse_widths("640,1200"))
    ex.add_argument("--budget", type=parse_budget, default=parse_budget("1200=120000,640=50000"),
                    help="max bytes per width, e.g. 1200=120000,640=50000")
    ex.add_argument("--manifest", type=Path, help="JSON manifest to merge the entries into")
    sh = sub.add_parser("sheet", help="contact sheet for review")
    sh.add_argument("dir", type=Path)
    sh.add_argument("out", type=Path)
    sh.add_argument("--glob", default="art-*-1200.webp")
    sh.add_argument("--cols", type=int, default=2)
    sh.add_argument("--width", type=int, default=560, help="thumbnail width in px")
    args = parser.parse_args()
    return cmd_export(args) if args.cmd == "export" else cmd_sheet(args)


if __name__ == "__main__":
    raise SystemExit(main())
