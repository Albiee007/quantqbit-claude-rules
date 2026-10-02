"""Pillow-based helpers: backdrop sampling for contrast, similarity diagnostics, simple sheets.

Needs Pillow; callers report a missing dependency (exit 2) when the import fails.
Similarity numbers are diagnostics only: they cannot tell quality or originality, and a match with
an approved earlier campaign is often the intent. Images are normalised (alpha composited on mid
grey, sRGB, 64x64) before comparison, and each report says so.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image  # noqa: E402  (a hard dependency of this module only)

from . import color as col

MAX_PIXELS = 80_000_000  # refuse absurd images (decompression bombs)
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


def open_rgb(path: Path, backdrop: tuple[int, int, int] = (128, 128, 128)) -> Image.Image:
    with Image.open(path) as im:
        im.load()
        rgba = im.convert("RGBA")
    base = Image.new("RGBA", rgba.size, (*backdrop, 255))
    base.alpha_composite(rgba)
    return base.convert("RGB")


def sample_ratios(bg: Image.Image, rects: list[list[float]], fg_css: str) -> list[float]:
    """Contrast of the text colour against the rendered pixels inside each rect (canvas px)."""
    fg = col.parse(fg_css)
    ratios: list[float] = []
    for left, top, right, bottom in rects:
        box = bg.crop((int(left), int(top), int(right + 0.999), int(bottom + 0.999)))
        step = max(1, int((box.width * box.height / 4000) ** 0.5))
        px = box.load()
        for y in range(0, box.height, step):
            for x in range(0, box.width, step):
                p = tuple(c / 255 for c in px[x, y][:3])
                ratios.append(col.contrast_ratio(col.composite(fg, p), p))
    return ratios


def percentile5(values: list[float]) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return values[len(values) // 20]


def missing_glyphs(font_path: str, text: str) -> str:
    """Characters of text that the font file has no glyph for: each is drawn and compared with the
    font's .notdef rendering (a private-use code point no font maps). Whitespace is skipped."""
    from PIL import ImageDraw, ImageFont
    font = ImageFont.truetype(str(font_path), 48)

    def draw(ch: str) -> bytes:
        im = Image.new("L", (96, 96), 0)
        ImageDraw.Draw(im).text((16, 16), ch, font=font, fill=255)
        return im.tobytes()

    notdef = draw("\U0010FFFD")
    blank = bytes(96 * 96)
    out = []
    for ch in dict.fromkeys(text):
        if ch.isspace():
            continue
        img = draw(ch)
        if img == notdef or img == blank:
            out.append(ch)
    return "".join(out)


def _ahash(im: Image.Image, n: int = 16) -> int:
    small = im.convert("L").resize((n, n), Image.LANCZOS)
    data = list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    avg = sum(data) / len(data)
    bits = 0
    for v in data:
        bits = (bits << 1) | (1 if v >= avg else 0)
    return bits


def dominant_oklab(im: Image.Image, k: int = 5) -> list[tuple[tuple[float, float, float], float]]:
    small = im.resize((64, 64), Image.LANCZOS).quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = small.getpalette() or []
    counts = sorted(small.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1
    out = []
    for c, idx in counts:
        rgb = tuple(v / 255 for v in pal[idx * 3: idx * 3 + 3])
        out.append((col.srgb_to_oklab(rgb), c / total))  # type: ignore[arg-type]
    return out


def compare(a: Path, b: Path) -> dict:
    """Diagnostics for two images: average-hash distance (0 = same structure, 256 = opposite) and the
    weighted OKLab distance between their dominant palettes. Never a verdict."""
    ia, ib = open_rgb(a), open_rgb(b)
    ha, hb = _ahash(ia), _ahash(ib)
    pa, pb = dominant_oklab(ia), dominant_oklab(ib)
    pal = sum(w * min(col.delta_e_ok(c, d) for d, _ in pb) for c, w in pa)
    return {"ahash_distance": bin(ha ^ hb).count("1"), "ahash_bits": 256, "palette_delta_e_ok": round(pal, 4),
            "normalised": "alpha on mid grey, sRGB, 16x16 hash and 64x64 palette"}


def sheet(paths: list[Path], dest: Path, cols: int = 4, width: int = 300, gutter: int = 16,
          bg: tuple[int, int, int] = (24, 24, 28)) -> Path:
    thumbs = []
    for p in paths:
        im = open_rgb(p, bg)
        h = round(im.height * width / im.width)
        thumbs.append(im.resize((width, max(1, h)), Image.LANCZOS))
    if not thumbs:
        raise ValueError("no images for the sheet")
    rows = [thumbs[i:i + cols] for i in range(0, len(thumbs), cols)]
    row_h = [max(t.height for t in r) for r in rows]
    W = gutter + cols * (width + gutter)
    H = gutter + sum(h + gutter for h in row_h)
    out = Image.new("RGB", (W, H), bg)
    y = gutter
    for r, h in zip(rows, row_h):
        x = gutter
        for t in r:
            out.paste(t, (x, y))
            x += width + gutter
        y += h + gutter
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, optimize=True)
    return Path(dest)
