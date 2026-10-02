"""Signals that an asset repeats the harness's own 1.6 defaults.

These are critique signals, never a pass/fail rule: a project may keep any of these on purpose
(direction.json "keep"), and consistency with an approved earlier campaign is often right. Each
signal names the matched feature so a person can judge it.
"""

from __future__ import annotations

import re
from typing import Any

from . import color as col

HARNESS_16_COLORS = {
    "#2a1bb0": "1.6 default gradient start (indigo)",
    "#3525cd": "1.6 default brand (indigo)",
    "#5b4ff0": "1.6 default gradient end (violet)",
    "#9ff3cf": "1.6 default accent (mint)",
    "#dcd9ff": "1.6 default sub-caption (lavender)",
    "#464555": "1.6 default dark sub-caption",
    "#0e0f1c": "1.6 default device bezel",
    "#1d0f8a": "1.6 story-art example indigo",
    "#c3c0ff": "1.6 story-art example lavender",
}
NEAR = 0.03  # ΔEOK; a little above one just-noticeable difference


def _near_default(css: str) -> tuple[str, str] | None:
    try:
        lab = col.srgb_to_oklab(col.parse(css)[:3])
    except col.ColorError:
        return None
    for hexv, label in HARNESS_16_COLORS.items():
        if col.delta_e_ok(lab, col.srgb_to_oklab(col.parse(hexv)[:3])) < NEAR:
            return hexv, label
    return None


def _colors_in(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += _colors_in(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _colors_in(v)
    elif isinstance(obj, str):
        out += re.findall(r"#[0-9a-fA-F]{6}\b|rgb\([^)]*\)", obj)
    return out


def palette_signals(obj: Any) -> list[dict]:
    seen, out = set(), []
    for c in _colors_in(obj):
        hit = _near_default(c)
        if hit and hit[0] not in seen:
            seen.add(hit[0])
            out.append({"id": "harness:color", "label": hit[1], "detail": f"{c} is within ΔEOK {NEAR} of {hit[0]}"})
    return out


def resolved_signals(r: dict) -> list[dict]:
    """Signals in a resolved store/marketing family (direction.resolve_family output)."""
    out = palette_signals(r)
    cap = r.get("caption", {})
    head = cap.get("head") or {}
    if head.get("family", "").lower() == "inter" and head.get("weight", 0) >= 800 and head.get("tracking", 0) <= -0.02:
        out.append({"id": "harness:inter-800-tight", "label": "1.6 caption type", "detail": "Inter 800 with tight tracking"})
    dev = r.get("device") or {}
    if (cap.get("align") == "center" and r.get("defaultLayout") == "caption-top" and dev.get("style") == "frame"
            and r.get("layouts") == ["caption-top"]):
        out.append({"id": "harness:centred-phone", "label": "1.6 classic layout",
                    "detail": "every frame: centred caption on top, framed phone below"})
    for name, b in (r.get("backgrounds") or {}).items():
        if b.get("recipe") == "linear" and 145 <= float(b.get("angle", 180)) <= 170 and len(b.get("stops", [])) >= 3:
            out.append({"id": "harness:diagonal-3-stop", "label": "1.6 gradient shape",
                        "detail": f"background {name!r}: a {b.get('angle')}° three-stop diagonal gradient"})
    return out


def legacy_kit_signals(cfg: dict) -> list[dict]:
    """Signals in a 1.6-format frames.json."""
    out = palette_signals(cfg.get("brand") or {})
    if (cfg.get("brand") or {}).get("glyphs"):
        out.append({"id": "harness:watermark-glyphs", "label": "1.6 watermark glyphs",
                    "detail": f"glyphs {cfg['brand']['glyphs']} at the engine's fixed spots"})
    if cfg.get("layout", "classic") == "classic":
        out.append({"id": "harness:centred-phone", "label": "1.6 classic layout", "detail": "the only 1.6 classic layout"})
    if any(o.get("type") in ("coin", "chip", "receipt", "calendar") for o in cfg.get("objects") or []):
        out.append({"id": "harness:finance-props", "label": "1.6 finance props", "detail": "coins, chips, receipts or calendar"})
    return out


TEXT_SIGNALS = [
    (r"soft clay", "harness:soft-clay-3d", "1.6 story-art example render style"),
    (r"(dark )?indigo(/navy)? backdrop", "harness:dark-indigo-backdrop", "1.6 story-art example backdrop"),
    (r"\{\{ONE_LINE_BENEFIT\}\}|--bg1:\s*#2a1bb0", "harness:og-1.6-template", "the 1.6 Open Graph template"),
    (r'r="400"[^>]*fill="\{\{PRIMARY\}\}"', "harness:circle-check-logo", "the 1.6 logo placeholder"),
]


def text_signals(text: str) -> list[dict]:
    out = palette_signals(text)
    for pattern, sid, label in TEXT_SIGNALS:
        if re.search(pattern, text, re.I):
            out.append({"id": sid, "label": label, "detail": f"matched /{pattern}/"})
    return out


def icon_signals(spec: dict) -> list[dict]:
    out = palette_signals(spec)
    bg = spec.get("background", {})
    if bg.get("recipe") == "solid" and abs(spec.get("glyphScale", 0) - 0.6) < 0.02 and spec.get("glyphOffset", [0, 0]) == [0, 0]:
        out.append({"id": "harness:flat-icon-0.6", "label": "1.6 icon composition",
                    "detail": "glyph centred at 0.6 on a flat colour"})
    return out
