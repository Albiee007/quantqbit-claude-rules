"""Caption and text contrast findings with honest result labels.

Two methods:
  computed  the text colour (composited if translucent) against a backdrop whose colour is known
            (a solid background, or every sample of a gradient, which is a conservative bound).
            PASS or FAIL is a conformance result for that pair.
  sampled   pixels rendered behind the text (images, gradients that failed the bound, objects
            overlapping the text). A sample is an estimate: a low sample is a FAIL, a passing sample
            is REVIEW REQUIRED (a person confirms it), never a normative PASS.
Sizes: WCAG large text is judged at the size the text has when the canvas is shown at its
smallest intended display width (`display_width` CSS px), which every report states.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import color as col
from .typescale import display_px

PASS, FAIL, REVIEW, SKIPPED = "PASS", "FAIL", "REVIEW REQUIRED", "SKIPPED"


@dataclass
class Finding:
    where: str
    text: str
    kind: str
    ratio: float | None
    need: float
    result: str
    method: str
    note: str = ""

    def line(self) -> str:
        shown = "n/a" if self.ratio is None else col.display_ratio(self.ratio, self.need) + ":1"
        extra = f" ({self.note})" if self.note else ""
        return f"  {self.result:<15} {self.where}: {self.kind} {self.text!r} {shown} vs {self.need:g}:1, {self.method}{extra}"


def need_for(size_px: float, weight: float, canvas_width: float, display_width: float | None) -> float:
    px = display_px(size_px, canvas_width, display_width) if display_width else size_px
    return col.text_threshold(px, weight)


def computed_solid(fg_css: str, bg_css: str) -> float:
    fg = col.parse(fg_css)
    bg = col.parse(bg_css)
    return col.contrast_ratio(col.composite(fg, bg[:3]), bg[:3])


def computed_gradient(fg_css: str, stops_css: list[str], space: str) -> float:
    """The lowest ratio of the text colour against every sample of the gradient (a bound that holds
    wherever the text sits on it)."""
    stops = [col.parse(s)[:3] for s in stops_css]
    fg = col.parse(fg_css)
    return min(col.contrast_ratio(col.composite(fg, s), s) for s in col.gradient_samples(stops, space))


def judge_computed(where: str, text: str, kind: str, ratio: float, need: float, note: str = "") -> Finding:
    return Finding(where, text, kind, ratio, need, PASS if ratio >= need else FAIL, "computed", note)


def judge_sampled(where: str, text: str, kind: str, p5: float | None, need: float, note: str = "") -> Finding:
    if p5 is None:
        return Finding(where, text, kind, None, need, REVIEW, "sampled", note or "no pixels sampled")
    return Finding(where, text, kind, p5, need, FAIL if p5 < need else REVIEW, "sampled",
                   note or "5th-percentile estimate")


def summary(findings: list[Finding]) -> dict[str, int]:
    out = {PASS: 0, FAIL: 0, REVIEW: 0, SKIPPED: 0}
    for f in findings:
        out[f.result] += 1
    return out


def overall(counts: dict[str, int]) -> str:
    if counts[FAIL]:
        return FAIL
    if counts[REVIEW]:
        return REVIEW
    if counts[PASS]:
        return PASS
    return SKIPPED
