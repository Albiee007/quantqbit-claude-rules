"""Colour maths: sRGB transfer, OKLab/OKLCH, gamut mapping, WCAG luminance and contrast, compositing.

Conventions (stated once, used everywhere):
- sRGB values are floats, gamma-encoded per IEC 61966-2-1, D65 white, nominal range 0..1.
  Conversions may return values outside 0..1 for out-of-gamut colours; in_gamut() tells.
- OKLab/OKLCH use Ottosson's matrices as published in CSS Color 4 (D65). L is 0..1, hue is in
  degrees [0, 360). A chroma below ACHROMATIC_C has no meaningful hue: oklch() reports hue None.
- WCAG 2.x relative luminance uses the 0.04045 threshold. contrast_ratio() returns full precision;
  compare that value with a threshold. display_ratio() is for printing only and truncates.
- Alpha compositing is source-over on gamma-encoded sRGB, which is what browsers do by default.
"""

from __future__ import annotations

import math
import re

ACHROMATIC_C = 1e-4      # OKLCH chroma below this is treated as grey (hue powerless)
JND_OK = 0.02            # CSS Color 4 gamut-mapping just-noticeable difference in OKLab
GAMUT_EPS = 1e-6         # tolerance for in_gamut() on float noise
LARGE_TEXT_PX = 24.0     # WCAG large text: 18pt
LARGE_BOLD_PX = 56 / 3   # 14pt = 18.67 px, with weight >= 700
TEXT_NORMAL = 4.5
TEXT_LARGE = 3.0
NON_TEXT = 3.0


class ColorError(ValueError):
    pass


# ------------------------------------------------------------------ transfer functions

def srgb_to_linear(c: float) -> float:
    """sRGB EOTF (sign-preserving, so out-of-gamut values stay continuous)."""
    a = abs(c)
    lin = a / 12.92 if a <= 0.04045 else ((a + 0.055) / 1.055) ** 2.4
    return math.copysign(lin, c)


def linear_to_srgb(c: float) -> float:
    a = abs(c)
    enc = a * 12.92 if a <= 0.0031308 else 1.055 * a ** (1 / 2.4) - 0.055
    return math.copysign(enc, c)


# ------------------------------------------------------------------ OKLab / OKLCH

def linear_srgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklab_to_linear_srgb(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    L, a, b = lab
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def srgb_to_oklab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    return linear_srgb_to_oklab(tuple(srgb_to_linear(c) for c in rgb[:3]))  # type: ignore[arg-type]


def oklab_to_srgb(lab: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(linear_to_srgb(c) for c in oklab_to_linear_srgb(lab))  # type: ignore[return-value]


def oklab_to_oklch(lab: tuple[float, float, float]) -> tuple[float, float, float | None]:
    L, a, b = lab
    C = math.hypot(a, b)
    if C < ACHROMATIC_C:
        return L, C, None
    return L, C, math.degrees(math.atan2(b, a)) % 360.0


def oklch_to_oklab(lch: tuple[float, float, float | None]) -> tuple[float, float, float]:
    L, C, H = lch
    if H is None or C <= 0:
        return L, 0.0, 0.0
    h = math.radians(H % 360.0)
    return L, C * math.cos(h), C * math.sin(h)


def delta_e_ok(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """Euclidean distance in OKLab (ΔEOK, CSS Color 4). 0.02 is about one just-noticeable difference."""
    return math.dist(lab1, lab2)


# ------------------------------------------------------------------ gamut

def in_gamut(rgb: tuple[float, ...], eps: float = GAMUT_EPS) -> bool:
    return all(-eps <= c <= 1 + eps for c in rgb[:3])


def clip(rgb: tuple[float, ...]) -> tuple[float, float, float]:
    return tuple(min(1.0, max(0.0, c)) for c in rgb[:3])  # type: ignore[return-value]


def gamut_map_oklch(lch: tuple[float, float, float | None]) -> tuple[float, float, float]:
    """CSS Color 4 gamut mapping to sRGB: reduce OKLCH chroma (binary search with a local
    ΔEOK < JND clip test), keeping lightness and hue. Returns in-gamut gamma-encoded sRGB."""
    L, C, H = lch
    if L >= 1:
        return 1.0, 1.0, 1.0
    if L <= 0:
        return 0.0, 0.0, 0.0
    rgb = oklab_to_srgb(oklch_to_oklab((L, C, H)))
    if in_gamut(rgb):
        return clip(rgb)
    clipped = clip(rgb)
    if delta_e_ok(srgb_to_oklab(clipped), oklch_to_oklab((L, C, H))) < JND_OK:
        return clipped
    lo, hi, lo_in = 0.0, C, True
    eps = 1e-4
    while hi - lo > eps:
        mid = (lo + hi) / 2
        current = oklch_to_oklab((L, mid, H))
        cand = oklab_to_srgb(current)
        if lo_in and in_gamut(cand):
            lo = mid
            continue
        clipped = clip(cand)
        e = delta_e_ok(srgb_to_oklab(clipped), current)
        if e < JND_OK:
            if JND_OK - e < eps:
                return clipped
            lo_in = False
            lo = mid
        else:
            hi = mid
    return clip(oklab_to_srgb(oklch_to_oklab((L, lo, H))))


# ------------------------------------------------------------------ parsing and formatting

_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?"
NAMED = {"white": (1.0, 1.0, 1.0, 1.0), "black": (0.0, 0.0, 0.0, 1.0), "transparent": (0.0, 0.0, 0.0, 0.0)}


def _num(tok: str, pct_scale: float = 1.0) -> float:
    tok = tok.strip()
    if tok == "none":
        return 0.0
    v = float(tok[:-1]) / 100 * pct_scale if tok.endswith("%") else float(tok)
    if not math.isfinite(v):
        raise ColorError(f"non-finite number {tok!r}")
    return v


def _split(body: str) -> tuple[list[str], str | None]:
    body = body.strip()
    alpha = None
    if "/" in body:
        body, alpha = body.split("/", 1)
    parts = [p for p in re.split(r"[\s,]+", body.strip()) if p]
    if alpha is None and len(parts) == 4:  # legacy rgba(r, g, b, a)
        alpha = parts.pop()
    return parts, alpha


def _alpha(tok: str | None) -> float:
    if tok is None:
        return 1.0
    a = _num(tok)
    if not 0 <= a <= 1:
        raise ColorError(f"alpha {tok!r} outside 0..1")
    return a


def parse(css: str) -> tuple[float, float, float, float]:
    """CSS colour -> (r, g, b, alpha), gamma-encoded sRGB floats (r, g, b may be out of gamut).
    Accepts #rgb #rgba #rrggbb #rrggbbaa, rgb()/rgba() (numbers or %), oklch(), oklab(),
    color(srgb ...), color(srgb-linear ...), white, black and transparent."""
    s = str(css).strip().lower()
    if s in NAMED:
        return NAMED[s]
    if s.startswith("#"):
        h = s[1:]
        if not re.fullmatch(r"[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8}", h):
            raise ColorError(f"bad hex colour {css!r}")
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return (vals[0], vals[1], vals[2], vals[3] if len(vals) == 4 else 1.0)
    m = re.fullmatch(r"(rgba?|oklch|oklab|color)\((.*)\)", s)
    if not m:
        raise ColorError(f"unsupported colour {css!r}")
    fn, body = m.groups()
    if fn == "color":
        space, _, rest = body.strip().partition(" ")
        parts, alpha = _split(rest)
        if len(parts) != 3:
            raise ColorError(f"color() needs 3 components: {css!r}")
        vals = [_num(p) for p in parts]
        if space == "srgb":
            return (vals[0], vals[1], vals[2], _alpha(alpha))
        if space == "srgb-linear":
            return (*(linear_to_srgb(v) for v in vals), _alpha(alpha))  # type: ignore[return-value]
        raise ColorError(f"color({space} ...) is not supported (srgb, srgb-linear only)")
    parts, alpha = _split(body)
    if len(parts) != 3:
        raise ColorError(f"{fn}() needs 3 components: {css!r}")
    if fn in ("rgb", "rgba"):
        vals = [_num(p, 255) for p in parts]
        return (vals[0] / 255, vals[1] / 255, vals[2] / 255, _alpha(alpha))
    if fn == "oklch":
        L = _num(parts[0])
        C = _num(parts[1], 0.4)
        H = None if parts[2] == "none" else _num(parts[2].removesuffix("deg"))
        r, g, b = oklab_to_srgb(oklch_to_oklab((L, C, H)))
        return (r, g, b, _alpha(alpha))
    L, a, b = _num(parts[0]), _num(parts[1], 0.4), _num(parts[2], 0.4)
    r, g, b_ = oklab_to_srgb((L, a, b))
    return (r, g, b_, _alpha(alpha))


def to_hex(rgb: tuple[float, ...], alpha: bool = False) -> str:
    r, g, b = (round(c * 255) for c in clip(rgb))
    out = f"#{r:02x}{g:02x}{b:02x}"
    if alpha and len(rgb) > 3 and rgb[3] < 1:
        out += f"{round(rgb[3] * 255):02x}"
    return out


def css_rgb(rgba: tuple[float, ...]) -> str:
    r, g, b = (round(c * 255) for c in clip(rgba))
    a = rgba[3] if len(rgba) > 3 else 1.0
    return f"rgb({r} {g} {b})" if a >= 1 else f"rgb({r} {g} {b} / {a:.4g})"


# ------------------------------------------------------------------ WCAG

def relative_luminance(rgb: tuple[float, ...]) -> float:
    """WCAG 2.x relative luminance of an opaque, in-gamut sRGB colour (clipped first)."""
    r, g, b = (srgb_to_linear(c) for c in clip(rgb))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[float, ...], bg: tuple[float, ...]) -> float:
    """Full-precision WCAG contrast ratio of two opaque colours. Composite alpha first."""
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def composite(fg: tuple[float, ...], bg: tuple[float, ...]) -> tuple[float, float, float]:
    """Source-over of fg (r, g, b, a) on an opaque bg, in gamma-encoded sRGB (browser default)."""
    a = fg[3] if len(fg) > 3 else 1.0
    if len(bg) > 3 and bg[3] < 1:
        raise ColorError("composite() needs an opaque backdrop; composite the backdrop first")
    return tuple(a * f + (1 - a) * b for f, b in zip(clip(fg), clip(bg)))  # type: ignore[return-value]


def is_large_text(px: float, weight: float) -> bool:
    """WCAG large text: at least 18pt (24 CSS px), or 14pt (18.67 px) at weight 700 or more."""
    return px >= LARGE_TEXT_PX - 1e-9 or (px >= LARGE_BOLD_PX - 1e-9 and weight >= 700)


def text_threshold(px: float, weight: float) -> float:
    return TEXT_LARGE if is_large_text(px, weight) else TEXT_NORMAL


def truncate(value: float, places: int = 2) -> float:
    f = 10 ** places
    return math.floor(value * f + 1e-12) / f


def display_ratio(ratio: float, need: float | None = None) -> str:
    """A ratio for printing: truncated to 2 decimals, never rounded up. A failing ratio never prints at
    or above its threshold."""
    shown = truncate(ratio, 2)
    if need is not None and ratio < need <= shown:
        shown = round(need - 0.01, 2)  # float noise at the boundary: still show it below the threshold
    return f"{shown:.2f}"


# ------------------------------------------------------------------ gradients

def interpolate(stops: list[tuple[float, ...]], t: float, space: str = "oklab") -> tuple[float, float, float]:
    """Colour at t (0..1) along evenly spaced opaque stops, interpolated in 'oklab' or 'srgb'."""
    if not stops:
        raise ColorError("no stops")
    if len(stops) == 1:
        return clip(stops[0])
    t = min(1.0, max(0.0, t))
    seg = t * (len(stops) - 1)
    i = min(int(seg), len(stops) - 2)
    u = seg - i
    a, b = stops[i], stops[i + 1]
    if space == "srgb":
        return clip(tuple(x + (y - x) * u for x, y in zip(a[:3], b[:3])))
    if space == "oklab":
        la, lb = srgb_to_oklab(a[:3]), srgb_to_oklab(b[:3])
        return clip(oklab_to_srgb(tuple(x + (y - x) * u for x, y in zip(la, lb))))  # type: ignore[arg-type]
    raise ColorError(f"unsupported interpolation space {space!r} (oklab, srgb)")


def gradient_samples(stops: list[tuple[float, ...]], space: str = "oklab", n: int = 33) -> list[tuple[float, float, float]]:
    return [interpolate(stops, i / (n - 1), space) for i in range(n)]
