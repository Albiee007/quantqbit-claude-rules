"""A stand-in image generator for the brand-video tests: a soft gradient at the asked size, the
prompt's length deciding its hue (so a different prompt gives different bytes).

Usage: python fake_broll.py PROMPT_FILE OUT_PNG WIDTH HEIGHT
"""

import sys

from PIL import Image, ImageDraw

prompt = open(sys.argv[1], encoding="utf-8").read()
w, h = int(sys.argv[3]), int(sys.argv[4])
im = Image.new("RGB", (w, h))
d = ImageDraw.Draw(im)
base = (len(prompt) * 7) % 60
for y in range(h):
    t = y / h
    d.line([(0, y), (w, y)], fill=(round(232 - 30 * t), round(236 - 20 * t - base / 4), round(214 - 40 * t)))
im.save(sys.argv[2])
