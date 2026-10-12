"""An explainer piece for the provider tests (tests/video.test.sh): a b-roll still with a voice-over
line and an end card, voice from the TTS provider. Writes the piece and, with --providers, the
project's brand/video/providers.json pointing at the stand-in providers in providers/.

Usage: python m4_talk.py PROJECT [--providers]
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    root = Path(sys.argv[1])
    piece = {
        "schemaVersion": 1, "id": "talk", "kind": "explainer", "title": "Explainer", "formats": ["social-1x1"], "fps": 30,
        "scenes": [
            {"id": "intro", "template": "still", "duration": 4,
             "media": {"image": "brand/video/talk/media/broll/intro.png", "prompt": "a calm vegetable garden at dawn, soft light"},
             "copy": {"head": "Your garden, planned"}, "vo": "Plan every bed in one calm place."},
            {"id": "end", "template": "end-card", "duration": 3, "transitionIn": {"type": "fade"},
             "copy": {"head": "Try Fernway", "url": "example.com"}, "vo": "Try Fernway today."}],
        "audio": {"voice": True},
        "voice": {"language": "en"},
    }
    (root / "brand" / "video" / "talk").mkdir(parents=True, exist_ok=True)
    (root / "brand" / "video" / "talk" / "video.json").write_text(json.dumps(piece, indent=2), encoding="utf-8")
    if "--providers" in sys.argv:
        tools = root / "tools" / "providers"
        tools.mkdir(parents=True, exist_ok=True)
        for f in ("fake_tts.py", "fake_align.py", "fake_broll.py"):
            shutil.copyfile(HERE / "providers" / f, tools / f)
        cfg = {"schemaVersion": 1, "providers": {
            "tts": {"label": "fake TTS (tests)", "command": ["{python}", "tools/providers/fake_tts.py", "{text}", "{out}"],
                    "env": ["FAKE_TTS_KEY"], "terms": "test tones, no licence needed"},
            "align": {"label": "fake aligner (tests)", "command": ["{python}", "tools/providers/fake_align.py", "{audio}", "{text}", "{out}"]},
            "broll": {"label": "fake image model (tests)",
                      "command": ["{python}", "tools/providers/fake_broll.py", "{prompt}", "{out}", "{width}", "{height}"]}}}
        (root / "brand" / "video" / "providers.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("wrote brand/video/talk" + (" and brand/video/providers.json" if "--providers" in sys.argv else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
