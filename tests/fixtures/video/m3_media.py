"""Media and pieces for the 1.11 video tests (tests/video.test.sh, part 5): an App Store preview of a
screen recording with recorded voice-over and music, and a transparent overlay. Everything is
generated here with ffmpeg (test patterns and tones), so no third-party media is in the repo.

Usage: python m3_media.py PROJECT FFMPEG
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def ff(ffmpeg: str, *args: str) -> None:
    subprocess.run([ffmpeg, "-hide_banner", "-v", "error", "-y", *args], check=True, timeout=300)


def take(ffmpeg: str, dest: Path, freq: int, speech: float) -> None:
    """A stand-in voice take: half a second of room tone, a tone for the speech, half a second after."""
    ff(ffmpeg, "-f", "lavfi", "-i", f"sine=f={freq}:d={speech}", "-af", "adelay=500|500,apad=pad_dur=0.5,volume=0.5",
       "-ac", "1", "-ar", "48000", str(dest))


def main() -> int:
    root, ffmpeg = Path(sys.argv[1]), sys.argv[2]
    media = root / "brand" / "video" / "preview" / "media"
    (media / "vo").mkdir(parents=True, exist_ok=True)
    # a 443x960 "screen recording": half the preview's size, so the recording scene scales it to cover
    ff(ffmpeg, "-f", "lavfi", "-i", "testsrc2=s=443x960:r=30:d=14", "-c:v", "libx264", "-pix_fmt", "yuv420p",
       "-preset", "veryfast", str(media / "flow.mp4"))
    take(ffmpeg, media / "vo" / "flow.wav", 330, 2.0)
    take(ffmpeg, media / "vo" / "end.wav", 440, 1.0)
    ff(ffmpeg, "-f", "lavfi", "-i", "sine=f=110:d=6", "-ac", "2", "-ar", "48000", "-af", "volume=0.3", str(media / "music.wav"))
    preview = {
        "schemaVersion": 1, "id": "preview", "kind": "app-preview", "title": "App Store preview",
        "formats": ["app-preview-iphone"], "fps": 30,
        "scenes": [
            {"id": "flow", "template": "recording", "duration": 13, "media": {"video": "brand/video/preview/media/flow.mp4"},
             "copy": {"head": "Plan in a minute"}, "vo": "Plan your beds in a minute."},
            {"id": "end", "template": "end-card", "duration": 3, "copy": {"head": "Try Fernway", "url": "example.com"},
             "vo": "Try Fernway today."}],
        "audio": {"voice": True, "music": {"file": "brand/video/preview/media/music.wav", "license": "a test tone made by the test"}},
        "voice": {"language": "en"},
    }
    (root / "brand" / "video" / "preview" / "video.json").write_text(json.dumps(preview, indent=2), encoding="utf-8")
    lower = {
        "schemaVersion": 1, "id": "lower", "kind": "social", "title": "Lower third", "formats": ["overlay"],
        "customFormats": {"overlay": {"like": "wide-16x9", "size": "960x540"}}, "fps": 30, "transparent": True,
        "scenes": [{"id": "name", "template": "title", "duration": 3, "layout": "type-lower",
                    "copy": {"head": "Fernway", "sub": "A garden journal"}}],
    }
    (root / "brand" / "video" / "lower").mkdir(parents=True, exist_ok=True)
    (root / "brand" / "video" / "lower" / "video.json").write_text(json.dumps(lower, indent=2), encoding="utf-8")
    print("wrote brand/video/preview and brand/video/lower")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
