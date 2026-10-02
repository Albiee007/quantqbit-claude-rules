"""Type-scale maths and platform adapters (DTCG stays the interchange; platforms are adapters).

A scale is a list of named steps. Sizes are computed in a base unit that is CSS px on the web and
dp/sp/pt on native platforms (1 CSS px ≈ 1 dp ≈ 1 pt at default settings); adapters format them:
  web   rem (root 16 px) and, when a viewport range is given, clamp() with a rem term so the text
        still responds to the user's font size (WCAG 1.4.4)
  android sp, ios pt, rn unitless numbers (React Native scales them with the OS font size)
Media sizes (store frames, social images) are raster pixels: media_px() converts a minimum size
the text must keep at its smallest intended display into canvas pixels.
Ratios, line heights and tracking defaults are heuristics; callers label them as such.
"""

from __future__ import annotations

import math

PLATFORMS = ("web", "android", "ios", "rn")
ROOT_PX = 16.0


class ScaleError(ValueError):
    pass


def modular(base: float, ratio: float, names: list[str], body: str) -> dict[str, float]:
    """Sizes for names (smallest first) with `body` at `base` and each step `ratio` apart."""
    if not (math.isfinite(base) and base > 0):
        raise ScaleError("base must be a positive number")
    if not (math.isfinite(ratio) and 1.0 < ratio <= 2.0):
        raise ScaleError("ratio must be between 1 (exclusive) and 2")
    if body not in names:
        raise ScaleError(f"body step {body!r} is not one of {names}")
    if len(set(names)) != len(names):
        raise ScaleError("step names must be unique")
    i0 = names.index(body)
    return {n: base * ratio ** (i - i0) for i, n in enumerate(names)}


def rem(px: float, root: float = ROOT_PX) -> str:
    return f"{px / root:.4g}rem"


def fluid_clamp(min_px: float, max_px: float, vw_min: float, vw_max: float, root: float = ROOT_PX) -> str:
    """CSS clamp() between min_px at vw_min and max_px at vw_max (viewport widths in px).
    The preferred value keeps a rem term, so browser zoom and the user's font size still apply."""
    if not (0 < vw_min < vw_max):
        raise ScaleError("viewport range must be 0 < min < max")
    if min_px > max_px:
        min_px, max_px = max_px, min_px
    slope = (max_px - min_px) / (vw_max - vw_min)
    intercept = min_px - slope * vw_min
    if slope == 0:
        return rem(min_px, root)
    return f"clamp({rem(min_px, root)}, {intercept / root:.4g}rem + {slope * 100:.4g}vw, {rem(max_px, root)})"


def platform_value(px: float, platform: str) -> str | float:
    if platform == "web":
        return rem(px)
    if platform == "android":
        return f"{round(px, 1):g}sp"
    if platform == "ios":
        return round(px, 1)
    if platform == "rn":
        return round(px, 1)
    raise ScaleError(f"unknown platform {platform!r} ({', '.join(PLATFORMS)})")


def media_px(min_display_px: float, canvas_width: float, display_width: float) -> float:
    """Canvas pixels needed so text is at least min_display_px when the canvas is shown
    display_width CSS px wide (its smallest intended display)."""
    if min(min_display_px, canvas_width, display_width) <= 0:
        raise ScaleError("sizes must be positive")
    return min_display_px * canvas_width / display_width


def display_px(canvas_px: float, canvas_width: float, display_width: float) -> float:
    """Inverse of media_px: the CSS px size of canvas text at the given display width."""
    return canvas_px * display_width / canvas_width
