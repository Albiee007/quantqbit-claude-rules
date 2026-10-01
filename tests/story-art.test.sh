#!/usr/bin/env bash
# === story art export tests ===
# Builds synthetic art with Pillow at run time (no binaries in the repo) and
# runs export_art.py export and sheet.
# Portable: Linux, macOS, Windows Git Bash. Needs Python 3.9+ with Pillow;
# skipped locally without it, but a failure when CI=true. The AVIF checks run
# only when Pillow has AVIF support (Pillow 11.3+ wheels).
# Usage: bash tests/story-art.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ART="$ROOT/harness/skills/story-art/scripts/export_art.py"
source "$ROOT/harness/bin/harness-lib.sh"
if ! hc_py -c 'import PIL' 2>/dev/null; then
  if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] Pillow is required in CI (pip install pillow)"; exit 1; fi
  echo "[SKIP] story art tests: Pillow not installed (pip install pillow)"; exit 0
fi
W="$(mktemp -d "${TMPDIR:-/tmp}/story-art-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0

ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }

# mk <dir> <spec>... — spec is name.png:WxH[:noise]. Smooth art compresses
# like an illustration; noise cannot meet any realistic budget.
cat > "$W/mk.py" <<'PY'
import os, sys
from pathlib import Path
from PIL import Image, ImageDraw
root = Path(sys.argv[1]); root.mkdir(parents=True, exist_ok=True)
for spec in sys.argv[2:]:
    name, size, *kind = spec.split(":")
    w, h = map(int, size.split("x"))
    if kind == ["noise"]:
        Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)).save(root / name); continue
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line((0, y, w, y), fill=(29 + y * 60 // h, 15 + y * 40 // h, 138))
    d.ellipse((w // 5, h // 4, w // 2, h * 3 // 4), fill=(159, 243, 207))
    d.rounded_rectangle((w // 2, h // 3, w * 4 // 5, h * 5 // 6), 40, fill=(195, 192, 255))
    img.save(root / name)
PY
mk()  { hc_py "$W/mk.py" "$@"; }
run() { hc_py "$ART" "$@" > "$W/out" 2> "$W/err"; }
# info <file> -> "WxH bytes"
info() { hc_py -c 'import os,sys; from PIL import Image; i=Image.open(sys.argv[1]); print(f"{i.width}x{i.height} {os.path.getsize(sys.argv[1])}")' "$1"; }
size() { wc -c < "$1" | tr -d ' '; }
avif=0; hc_py -c 'from PIL import features; raise SystemExit(0 if features.check("avif") else 1)' && avif=1

echo "1. export writes every width within budget"
mk "$W/src" trip.png:1456x1088 roommates.png:1456x1088
printf '{\n  "files": {\n    "shot-home-1080.webp": {"width": 1080, "height": 1920}\n  },\n  "note": "site"\n}\n' > "$W/manifest.json"
run export "$W/src" "$W/pub" --prefix art --widths 640,1200 --budget 1200=120000,640=50000 --manifest "$W/manifest.json"
check "exit 0" test $? -eq 0 || cat "$W/err"
check "summary table printed" grep -q 'art-trip-1200.webp' "$W/out"
for s in trip roommates; do
  check "$s 1200 webp is 1200x897" test "$(info "$W/pub/art-$s-1200.webp" | cut -d' ' -f1)" = "1200x897"
  check "$s 640 webp is 640x478" test "$(info "$W/pub/art-$s-640.webp" | cut -d' ' -f1)" = "640x478"
  check "$s 1200 webp within 120000 bytes" test "$(size "$W/pub/art-$s-1200.webp")" -le 120000
  check "$s 640 webp within 50000 bytes" test "$(size "$W/pub/art-$s-640.webp")" -le 50000
  if [[ $avif -eq 1 ]]; then
    for w in 640 1200; do
      check "$s $w avif under 80% of webp" \
        test $(( $(size "$W/pub/art-$s-$w.avif") * 10 )) -lt $(( $(size "$W/pub/art-$s-$w.webp") * 8 ))
    done
  fi
done
if [[ $avif -eq 1 ]]; then
  check "8 files written" test "$(find "$W/pub" -type f | wc -l | tr -d ' ')" -eq 8
else
  echo "  [note] Pillow has no AVIF support: WebP-only path tested"
  check "WebP only: 4 files written" test "$(find "$W/pub" -type f | wc -l | tr -d ' ')" -eq 4
  check "WebP only: says so on stderr" grep -q 'no AVIF support' "$W/err"
fi

echo "2. manifest merge keeps other entries"
manifest() { hc_py -c 'import json,sys; d=json.load(open(sys.argv[1])); exec(sys.argv[2])' "$W/manifest.json" "$1"; }
check "pre-existing file entry kept" test "$(manifest 'print(d["files"]["shot-home-1080.webp"]["height"])')" = "1920"
check "other top-level key kept" test "$(manifest 'print(d["note"])')" = "site"
check "new entry has width and height" test "$(manifest 'e=d["files"]["art-trip-1200.webp"]; print(e["width"], e["height"])')" = "1200 897"
check "one entry per file written" \
  test "$(manifest 'print(sum(k.startswith("art-") for k in d["files"]))')" -eq "$(find "$W/pub" -type f | wc -l | tr -d ' ')"
run export "$W/src" "$W/pub" --manifest "$W/new/manifest.json"
check "absent manifest is created" test -f "$W/new/manifest.json"

echo "3. a budget that cannot be met fails and writes nothing"
mk "$W/noisy" busy.png:1300x900:noise
run export "$W/noisy" "$W/nopub" --widths 1200 --budget 1200=20000
check "exit 1" test $? -eq 1
check "names the file and the budget" grep -q 'art-busy-1200: WEBP cannot get under 20,000 bytes' "$W/err"
check "nothing written" test ! -e "$W/nopub"

echo "4. bad input is refused"
mk "$W/small" tiny.png:500x400
run export "$W/small" "$W/x" --widths 640; check "upscaling: exit 1" test $? -eq 1
check "upscaling is named" grep -q 'would upscale' "$W/err"
mk "$W/badname" "Hero Shot.png:1300x900"
run export "$W/badname" "$W/x"; check "non-slug scene name: exit 2" test $? -eq 2
mkdir -p "$W/empty"
run export "$W/empty" "$W/x"; check "no sources: exit 2" test $? -eq 2
run export "$W/src" "$W/x" --budget 1200; check "malformed budget: exit 2" test $? -eq 2

echo "5. contact sheet"
run sheet "$W/pub" "$W/review/sheet.png"
check "exit 0" test $? -eq 0
check "sheet written" test -f "$W/review/sheet.png"
check "sheet holds both 1200 images" grep -q '2 images' "$W/out"
run sheet "$W/pub" "$W/review/none.png" --glob 'nothing-*'; check "no matches: exit 2" test $? -eq 2

check "no __pycache__ left in the skill" test ! -e "$ROOT/harness/skills/story-art/scripts/__pycache__"

printf '\nstory art tests: %d passed, %d failed\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
