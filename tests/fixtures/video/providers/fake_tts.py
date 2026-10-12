"""A stand-in TTS provider for the brand-video tests: a tone as long as the line would take to say,
with 0.4 s of silence before and after. It checks for its "key" in the environment, the way a real
provider script would (the value is never written anywhere).

Usage: python fake_tts.py TEXT_FILE OUT_WAV
"""

import math
import os
import struct
import sys
import wave

if not os.environ.get("FAKE_TTS_KEY"):
    sys.exit("FAKE_TTS_KEY is not set")
text = open(sys.argv[1], encoding="utf-8").read().split()
rate, speech = 48000, max(0.6, 0.32 * len(text))
frames = []
for i in range(int(rate * (speech + 0.8))):
    t = i / rate
    v = 0.4 * math.sin(2 * math.pi * 220 * t) if 0.4 <= t < 0.4 + speech else 0.0
    frames.append(struct.pack("<h", int(v * 32767)))
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b"".join(frames))
