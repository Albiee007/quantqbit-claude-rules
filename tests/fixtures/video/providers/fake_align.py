"""A stand-in word aligner for the brand-video tests: finds where the take is not silent and spreads
the line's words evenly over it.

Usage: python fake_align.py TAKE_WAV TEXT_FILE OUT_JSON
"""

import json
import struct
import sys
import wave

with wave.open(sys.argv[1], "rb") as w:
    rate, n = w.getframerate(), w.getnframes()
    data = struct.unpack(f"<{n * w.getnchannels()}h", w.readframes(n))
loud = [i for i, v in enumerate(data) if abs(v) > 300]
start, end = loud[0] / rate, loud[-1] / rate
words = open(sys.argv[2], encoding="utf-8").read().split()
step = (end - start) / len(words)
out = [{"word": w, "start": round(start + i * step, 3), "end": round(start + (i + 1) * step - 0.02, 3)}
       for i, w in enumerate(words)]
json.dump({"words": out}, open(sys.argv[3], "w", encoding="utf-8"))
