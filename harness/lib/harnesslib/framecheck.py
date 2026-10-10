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


def _mad(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / (len(a) or 1)


def seam_signal(frames: list[bytes]) -> tuple[float, float]:
    """(jump at the loop point, threshold) on small grey frames: the change from the last frame back
    to the first, against the piece's own larger frame-to-frame changes. A jump above the threshold
    is a visible seam when the loop repeats (a signal: a deliberate cut can be fine)."""
    if len(frames) < 3:
        return 0.0, 0.0
    steps = sorted(_mad(frames[i - 1], frames[i]) for i in range(1, len(frames)))
    p95 = steps[min(len(steps) - 1, int(len(steps) * 0.95))]
    return _mad(frames[-1], frames[0]), max(3.0, 2 * p95)


def anim_problems(path, profile: str, frames: int, size: tuple[int, int], duration_s: float) -> tuple[list[str], dict]:
    """Problems with an animated GIF or WebP, or a poster PNG, against what was asked for (empty =
    PASS), and what was found {frames, size, loop, durationS}."""
    from PIL import Image
    want = {"gif": "GIF", "webp-anim": "WEBP", "poster": "PNG"}[profile]
    try:
        with Image.open(path) as im:
            fmt, got_size = im.format, im.size
            n = getattr(im, "n_frames", 1)
            loop = im.info.get("loop")
            total = 0
            if profile != "poster":
                for i in range(n):
                    im.seek(i)
                    im.load()  # WebP sets a frame's duration only once it is decoded
                    total += im.info.get("duration", 0)
    except (OSError, ValueError) as e:
        return [f"unreadable: {e}"], {}
    found = {"frames": n, "size": list(got_size), "loop": loop, "durationS": round(total / 1000, 3)}
    out = []
    if fmt != want:
        out.append(f"format {fmt}, want {want}")
    if tuple(got_size) != tuple(size):
        out.append(f"{got_size[0]}x{got_size[1]}, want {size[0]}x{size[1]}")
    if profile == "poster":
        return out, found
    if not 0 < n <= frames:  # encoders may merge identical frames into one longer frame
        out.append(f"{n} frames, want at most {frames}")
    if loop != 0:
        out.append(f"loop count {loop}, want 0 (forever)")
    if abs(total / 1000 - duration_s) > max(0.1, duration_s * 0.02):
        out.append(f"plays {total / 1000:.2f} s, want {duration_s:.2f} s")
    return out, found
