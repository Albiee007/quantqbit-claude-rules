"""Evaluate a rendered art-direction page's caption probe (artdir.js ArtDir.probe output).

For each caption text run: contrast (computed against the known backdrop colour when nothing is
drawn under the text, otherwise sampled from the rendered backdrop) and text problems: characters
the requested family does not draw (from the font file itself for local fonts, Pillow/FreeType,
and from the browser's fallback comparison otherwise), and text cut off by the canvas edge.
Pillow is imported only when needed.
"""

from __future__ import annotations

from typing import Callable

from . import contrast as con


def evaluate(pr: dict, ad: dict, label: str, backdrop: Callable[[], object]) -> tuple[list[con.Finding], list[str]]:
    """pr: the probe JSON; ad: the resolved family; backdrop(): the page rendered without captions
    (a PIL image), called at most once. Returns (contrast findings, text problems)."""
    found: list[con.Finding] = []
    fonts: list[str] = []
    dw = ad["displayWidth"]
    bg_img = None
    files = {(f["family"], f["weight"], f["style"]): f["abs"] for f in ad.get("faces", []) if f.get("abs")}
    for run in pr["runs"]:
        need = con.need_for(run["size"], run["weight"], pr["W"], dw)
        face = files.get((run["family"], run["weight"], "italic" if run["italic"] else "normal"))
        if face:
            from . import imaging
            text = run.get("chars", run["text"])
            text += text.upper()
            run["missing"] = "".join(sorted(set(run["missing"]) | set(imaging.missing_glyphs(face, text))))
        if run["missing"]:
            fonts.append(f"{label}: {run['family']} {run['weight']}{' italic' if run['italic'] else ''} has no glyph for "
                         f"{run['missing']!r} in {run['text']!r}")
        if run.get("clipped"):
            fonts.append(f"{label}: {run['text']!r} runs off the canvas (shorten the copy or choose another layout)")
        b = ad["backgrounds"].get(run.get("bg") or "")
        if run["own"] and not run["overlap"]:
            found.append(con.judge_computed(label, run["text"], run["kind"], con.computed_solid(run["color"], run["own"]),
                                            need, "on its highlight"))
            continue
        if b and not run["overlap"] and b["recipe"] == "solid":
            found.append(con.judge_computed(label, run["text"], run["kind"], con.computed_solid(run["color"], b["color"]), need))
            continue
        if b and not run["overlap"] and b["recipe"] == "linear":
            ratio = con.computed_gradient(run["color"], b["stops"], b["space"])
            if ratio >= need:
                found.append(con.judge_computed(label, run["text"], run["kind"], ratio, need, "whole-gradient bound"))
                continue
        from . import imaging  # Pillow, only when a sample is needed
        if bg_img is None:
            bg_img = backdrop()
        p5 = imaging.percentile5(imaging.sample_ratios(bg_img, run["rects"], run["color"]))  # type: ignore[arg-type]
        why = "overlaps a drawn object" if run["overlap"] else "gradient behind the text"
        found.append(con.judge_sampled(label, run["text"], run["kind"], p5, need, f"5th-percentile estimate; {why}"))
    return found, fonts
