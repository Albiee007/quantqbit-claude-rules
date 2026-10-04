"""Signals from decoded video frames. They are heuristics for a person to look at, never a pass.

flash_signal approximates the WCAG 2.3.1 general flash rule on small grey frames: a transition is
a frame where at least `area` of the picture changes relative luminance by 10 % or more (with the
darker state below 0.80); a flash is a pair of opposing transitions; more than three flashes in
any one-second window is reported. Luma is treated as sRGB-encoded luminance, which is close but
not exact, so a hit means REVIEW REQUIRED, and no hit is not a conformance claim.
"""

from __future__ import annotations

import hashlib

_LIN = [((v / 255) / 12.92) if v / 255 <= 0.04045 else (((v / 255) + 0.055) / 1.055) ** 2.4 for v in range(256)]


def _transition(a: bytes, b: bytes, area: float) -> int:
    """+1 (brighter), -1 (darker) or 0 for the change from frame a to frame b."""
    up = down = 0
    for x, y in zip(a, b):
        la, lb = _LIN[x], _LIN[y]
        if abs(lb - la) >= 0.10 and min(la, lb) < 0.80:
            if lb > la:
                up += 1
            else:
                down += 1
    n = len(a) or 1
    if up / n >= area and up >= down:
        return 1
    if down / n >= area:
        return -1
    return 0


def flash_signal(frames: list[bytes], fps: int, area: float = 0.25) -> list[float]:
    """Start times (seconds) of one-second windows holding more than three flashes."""
    events: list[tuple[int, int]] = []
    for i in range(1, len(frames)):
        t = _transition(frames[i - 1], frames[i], area)
        if t:
            events.append((i, t))
    # count opposing pairs inside sliding one-second windows
    hits: list[float] = []
    for start in range(len(events)):
        window = [e for e in events[start:] if e[0] - events[start][0] < fps]
        flashes, last = 0, None
        for _, sign in window:
            if last is not None and sign != last:
                flashes += 1
            last = sign
        flashes = (flashes + 1) // 2
        if flashes > 3:
            t0 = round(events[start][0] / fps, 2)
            if not hits or t0 - hits[-1] >= 1:
                hits.append(t0)
    return hits


def pixel_hash(png_bytes: bytes) -> str:
    """A hash of the decoded pixels (not the file bytes, which depend on the encoder)."""
    import io

    from PIL import Image
    with Image.open(io.BytesIO(png_bytes)) as im:
        return hashlib.sha256(im.convert("RGB").tobytes()).hexdigest()
