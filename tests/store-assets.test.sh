#!/usr/bin/env bash
# === store asset checker tests ===
# Builds image fixtures with Pillow at run time (no binaries in the repo) and
# runs check_store_assets.py in inspect and --release modes.
# Portable: Linux, macOS, Windows Git Bash. Needs Python 3.9+ with Pillow;
# skipped locally without it, but a failure when CI=true.
# Usage: bash tests/store-assets.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/harness/skills/store-submission-precheck"
CHECK="$SKILL/scripts/check_store_assets.py"
source "$ROOT/harness/bin/harness-lib.sh"
if ! hc_py -c 'import PIL' 2>/dev/null; then
  if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] Pillow is required in CI (pip install pillow)"; exit 1; fi
  echo "[SKIP] store asset tests: Pillow not installed (pip install pillow)"; exit 0
fi
W="$(mktemp -d "${TMPDIR:-/tmp}/store-assets-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0

ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }

# mk <root> <spec>... — spec is path:WxH[:MODE[:FORMAT]], path:truncated or
# path:random. One Python process per call.
cat > "$W/mk.py" <<'PY'
import os, sys
from pathlib import Path
from PIL import Image
root = Path(sys.argv[1])
for spec in sys.argv[2:]:
    rel, *rest = spec.split(":")
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if rest == ["random"]:
        p.write_bytes(os.urandom(4096)); continue
    if rest == ["truncated"]:
        Image.new("RGB", (1080, 1920), (40, 90, 160)).save(p, "PNG")
        p.write_bytes(p.read_bytes()[:400]); continue
    w, h = map(int, rest[0].split("x"))
    mode = rest[1] if len(rest) > 1 else "RGB"
    fmt = rest[2] if len(rest) > 2 else ("JPEG" if p.suffix.lower() in (".jpg", ".jpeg") else "PNG")
    if mode == "RGB16":  # 16 bits per channel: write the PNG by hand (Pillow cannot)
        import struct, zlib
        raw = b"".join(b"\0" + b"\x12\x34" * 3 * w for _ in range(h))
        chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 16, 2, 0, 0, 0))
                      + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        continue
    color = {"RGB": (40, 90, 160), "RGBA": (40, 90, 160, 128), "CMYK": (0, 50, 90, 10), "L": 128, "P": 3}[mode]
    Image.new(mode, (w, h), color).save(p, fmt)
PY
mk() { hc_py "$W/mk.py" "$@"; }
run() { hc_py "$CHECK" "$@" > "$W/out" 2> "$W/err"; }
has() { grep -q -- "$1" "$W/out"; }
code() { hc_py -c 'import json,sys; d=json.load(open(sys.argv[1])); print(" ".join(sorted({f["code"] for f in d["findings"] if f["level"]==sys.argv[2]})))' "$W/out" "$1"; }

# A complete, valid submission for both stores.
valid_set() {
  mk "$1" play/phone/1.png:1080x1920 play/phone/2.png:1080x1920 play/phone/3.png:1080x1920 \
    play/phone/4.png:1080x1920 play/feature_graphic_1024x500.png:1024x500 play/tablet10/1.png:1620x2880 \
    ios/6.3/1.png:1206x2622 ios/6.3/2.png:1179x2556 ios/6.9/1.png:1290x2796 ios/6.9/2.png:1320x2868 \
    ios/ipad13/1.png:2064x2752 \
    icons/ios-1024.png:1024x1024 icons/play-512.png:512x512:RGBA
  printf '{"version": 1, "stores": ["play", "ios"],
  "ios": {"supports_tablet": true, "icon": "icons/ios-1024.png"},
  "play": {"icon": "icons/play-512.png", "tablet_slots": ["tablet10"]},
  "min_counts": {"play-phone": 4}}\n' > "$1/store-assets.json"
}

echo "1. empty root"
mkdir -p "$W/empty"
run "$W/empty"; check "inspect mode: exit 0" test $? -eq 0
check "inspect mode: empty slots are INFO" has 'INFO   \[empty-slot\]'
run "$W/empty" --release; check "--release without stores: exit 2" test $? -eq 2
check "names the missing setting" grep -q -- '--stores' "$W/err"
run "$W/empty" --release --stores play,ios --no-supports-tablet --json; check "--release: exit 1" test $? -eq 1
check "--release: required slots missing" test "$(code ERROR)" = "missing-slot"
check "--release: phone, feature graphic, play icon, 6.3 reported" \
  test "$(hc_py -c 'import json,sys; print(sorted(f["slot"] for f in json.load(open(sys.argv[1]))["findings"] if f["code"]=="missing-slot"))' "$W/out")" \
  = "['ios-6.3', 'play-feature-graphic', 'play-icon', 'play-phone']"
run "$W/empty" --release --stores ios; check "--release ios without iPad answer: exit 2" test $? -eq 2

echo "2. a complete submission passes the release gate"
valid_set "$W/valid"
run "$W/valid" --release --json; rc=$?
check "exit 0" test $rc -eq 0 || cat "$W/out"
check "JSON reports 0 errors" test "$(hc_py -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["errors"], d["mode"], d["supports_tablet"], d["counts"]["play-phone"])' "$W/out")" = "0 release True 4"
run "$W/valid" --release; check "text report ends with the totals" grep -q '^0 error(s)' "$W/out"

echo "3. release gaps"
valid_set "$W/gaps"; rm -f "$W/gaps"/ios/6.3/*.png "$W/gaps"/ios/ipad13/*.png
run "$W/gaps" --release --json; check "exit 1" test $? -eq 1
check "empty 6.3 folder is missing-slot" grep -q '"slot": "ios-6.3"' "$W/out"
check "iPad required when supports_tablet" grep -q '"slot": "ios-ipad13"' "$W/out"
run "$W/gaps" --json; check "same tree in inspect mode: exit 0" test $? -eq 0
valid_set "$W/min"; rm -f "$W/min/play/phone/4.png"
run "$W/min" --release --json; check "min_counts raises the phone minimum" test "$(code ERROR)" = "count"

echo "4. broken files are findings, never tracebacks"
mk "$W/broken" play/phone/a.png:truncated play/phone/b.png:random play/phone/c.png:1080x1920:RGB:GIF \
  play/phone/d.jpg:1080x1920:CMYK play/phone/e.png:1080x1920:RGBA play/phone/f.png:1080x1920:RGB16 \
  play/phone/g.png:1080x1920:RGB:JPEG
run "$W/broken" --json; check "exit 1" test $? -eq 1
check "no traceback" test ! -s "$W/err"
check "corrupt, format, mode and alpha errors" test "$(code ERROR)" = "alpha corrupt format mode"
check "JPEG named .png is a warning" grep -q 'is a JPEG file with a .png name' "$W/out"
check "16-bit PNG is caught" grep -q 'more than 8 bits per channel' "$W/out"
check "CMYK is caught" grep -q 'is CMYK' "$W/out"

echo "5. leftovers, duplicates and counts"
mk "$W/misc" play/phone/1.png:1080x1920 play/phone/2.png:1080x1920 play/phone/1.raw.png:1080x1920 \
  play/phone/.DS_Store:random play/feature_graphic.png:1024x500 play/feature_graphic_old.jpg:1024x500 \
  play/feature_graphic.raw.png:1024x500
run "$W/misc" --json; check "exit 1" test $? -eq 1
check "intermediate and hidden files ignored, with warnings" test "$(grep -c '"code": "leftover"' "$W/out")" -eq 3
check ".raw.png not counted" grep -q '"play-phone": 2' "$W/out"
check "two feature graphics is an error" test "$(code ERROR)" = "duplicate-feature-graphic"
mk "$W/nine" play/phone/{1,2,3,4,5,6,7,8,9}.png:1080x1920
run "$W/nine" --json; check "9 phone screenshots: count error" test "$(code ERROR)" = "count"

echo "6. Play size rules (phone 3840 px, tablets 7680 px)"
mk "$W/sizes" play/phone/1.png:2160x3840 play/phone/2.png:2200x4000 play/tablet10/1.png:3000x6000 \
  play/tablet7/1.png:1000x1600
run "$W/sizes" --json; check "exit 1" test $? -eq 1
check "phone over 3840 px is an error" grep -q '2200x4000: each side must be 320-3840' "$W/out"
check "tablet up to 7680 px is accepted" test "$(grep -c '3000x6000' "$W/out")" -eq 0
check "tablet short side under 1080 warns" grep -q '"code": "large-screen"' "$W/out"

echo "7. config"
valid_set "$W/cfg"
printf '{"stores": ["play"], "colour": 1}\n' > "$W/cfg/store-assets.json"
run "$W/cfg"; check "unknown key: exit 2" test $? -eq 2
printf '{"stores": ["play"],\n' > "$W/cfg/store-assets.json"
run "$W/cfg"; check "malformed JSON: exit 2" test $? -eq 2
printf '{"stores": ["play"], "min_counts": {"play-phone": 9}}\n' > "$W/cfg/store-assets.json"
run "$W/cfg"; check "min_counts above the store maximum: exit 2" test $? -eq 2
printf '{"expo": {"ios": {"supportsTablet": false}}}\n' > "$W/cfg/app.json"
printf '{"stores": ["ios"], "ios": {"supports_tablet": true, "app_json": "app.json", "icon": "icons/ios-1024.png"}}\n' \
  > "$W/cfg/store-assets.json"
run "$W/cfg" --release --json; check "supports_tablet contradicting app.json is an error" test "$(code ERROR)" = "config"
printf '{"stores": ["ios"], "ios": {"app_json": "app.json"}}\n' > "$W/cfg/store-assets.json"
run "$W/cfg" --release --json; check "iPad requirement read from app.json" test $? -eq 0
check "undeclared store's folders are INFO" grep -q '"code": "undeclared-store"' "$W/out"
run "$W/cfg" --stores play --json; check "--stores overrides the config" grep -q '"play-phone": 4' "$W/out"

echo "8. the slot catalog matches references/store-specs.md"
hc_py - "$SKILL/references/store-slots.json" "$SKILL/references/store-specs.md" > "$W/spec.txt" <<'PY'
import json, sys
cat = json.load(open(sys.argv[1], encoding="utf-8"))
doc = open(sys.argv[2], encoding="utf-8").read()
sizes = {tuple(map(int, v.split("x"))) for s in cat["slots"].values() for v in s.get("sizes", [])}
sizes |= {tuple(map(int, cat["featureGraphic"]["size"].split("x"))), (512, 512), (1024, 1024)}
missing = [f"{a} × {b}" for a, b in sorted(sizes) if f"{a} × {b}" not in doc and f"{b} × {a}" not in doc]
limits = [str(s["rule"]["maxSide"]) for s in cat["slots"].values() if "rule" in s and str(s["rule"]["maxSide"]) not in doc]
slots = [n for n, s in cat["slots"].items() if s["store"] == "ios" and f"`{n}`" not in doc]
print(" ".join(missing + limits + slots), end="")
PY
check "every size, side limit and iOS slot appears in store-specs.md" test ! -s "$W/spec.txt"
[[ -s "$W/spec.txt" ]] && echo "    missing: $(cat "$W/spec.txt")"

echo "9. iPhone defaults: 6.3 required, 6.9 and 6.5 optional"
mk "$W/ios63" ios/6.3/1.png:1206x2622 ios/6.3/2.png:2556x1179
run "$W/ios63" --release --stores ios --no-supports-tablet --json; rc=$?
check "a 6.3 set alone (one landscape) passes release" test $rc -eq 0 || cat "$W/out"
mk "$W/ios69" ios/6.9/1.png:1290x2796
run "$W/ios69" --release --stores ios --no-supports-tablet --json
check "a 6.9 set alone is missing a required slot" test "$(code ERROR)" = "missing-slot"
check "the missing slot is ios-6.3" grep -q '"slot": "ios-6.3"' "$W/out"
mk "$W/ios63bad" ios/6.3/1.png:1290x2796
run "$W/ios63bad" --stores ios --json; check "a 6.9 size in the 6.3 folder is bad-size" test "$(code ERROR)" = "bad-size"
check "bad-size names the accepted sizes" grep -q '1179x2556, 1206x2622 (or landscape)' "$W/out"

echo "10. project slots in store-assets.json"
mk "$W/proj" ios/6.3/1.png:1206x2622 ios/6.1/1.png:1170x2532 play/phone/1.png:1080x1920 play/phone/2.png:1080x1920 \
  play/chromebook/1.png:1920x1080 play/feature_graphic.png:1024x500 icons/play-512.png:512x512:RGBA
cfg() { printf '%s\n' "$1" > "$W/proj/store-assets.json"; }
cfg '{"stores": ["ios"], "ios": {"supports_tablet": false},
 "slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "need": "always"}}}'
run "$W/proj" --release --json; rc=$?
check "a project slot is checked and passes" test $rc -eq 0 || cat "$W/out"
check "its count is reported" grep -q '"ios-6.1": 1' "$W/out"
rm "$W/proj/ios/6.1/1.png"
run "$W/proj" --release --json; check "a required project slot gates release" grep -q '"slot": "ios-6.1"' "$W/out"
mk "$W/proj" ios/6.1/1.png:1170x2532
cfg '{"stores": ["ios"], "ios": {"supports_tablet": false}, "slots": {"ios-6.9": {"need": "always"}}}'
run "$W/proj" --release --json; check "a need override makes ios-6.9 required" grep -q '"slot": "ios-6.9"' "$W/out"
check "an undeclared folder is an error in release" grep -q '"code": "unknown-folder"' "$W/out"
cfg '{"stores": ["ios"], "ios": {"supports_tablet": false}, "slots": {"ios-6.3": {"count": [2, 10]}}}'
run "$W/proj" --json
check "a count override keeps the slot's sizes" test "$(code ERROR)" = "count"
cfg '{"stores": ["ios"], "ios": {"supports_tablet": false}, "slots": {"ios-6.3": {"sizes": ["1206x2622"]}},
 "min_counts": {"ios-6.3": 1}}'
mk "$W/proj" ios/6.3/2.png:1179x2556
run "$W/proj" --json; check "a sizes override replaces the accepted sizes" grep -q '1179x2556 is not an accepted ios-6.3 size' "$W/out"
rm "$W/proj/ios/6.3/2.png"
mk "$W/rule" play/phone/1.png:1080x1920 play/phone/2.png:1440x2560
printf '{"slots": {"play-phone": {"sizes": ["1080x1920"]}}}\n' > "$W/rule/store-assets.json"
run "$W/rule" --stores play --json
check "a sizes override replaces a slot's size rule" grep -q '1440x2560 is not an accepted play-phone size' "$W/out"
cfg '{"stores": ["play"], "play": {"icon": "icons/play-512.png", "tablet_slots": ["play-chromebook"]},
 "slots": {"play-chromebook": {"store": "play", "folder": "play/chromebook", "sizes": ["1080x1920"], "need": "declared"}},
 "min_counts": {"play-chromebook": 1}}'
run "$W/proj" --release --json; rc=$?
check "an exact-size Play slot takes exactly those sizes (landscape too)" test $rc -eq 0 || cat "$W/out"
check "an exact-size Play slot gets no size-rule or large-screen findings" test "$(grep -c '"slot": "play-chromebook"' "$W/out")" -eq 0
rm "$W/proj/play/chromebook/1.png"
run "$W/proj" --release --json; check "a declared project tablet slot is required" grep -q '"slot": "play-chromebook"' "$W/out"
cfg '{"stores": ["play"], "play": {"icon": "icons/play-512.png", "tablet_slots": ["tablet7"]}}'
run "$W/proj" --release --json; check "tablet7 still names play-tablet7" grep -q '"slot": "play-tablet7"' "$W/out"
for bad in \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1"}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "rule": {"maxSide": 3000}}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "../ios/6.1", "sizes": ["1170x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/../x", "sizes": ["1170x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "/tmp/x", "sizes": ["1170x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "play/x", "sizes": ["1170x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.3", "sizes": ["1170x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170 x 2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["100x2532"]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "count": [true, 3]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "count": [5, 2]}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "need": "sometimes"}}}' \
  '{"slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"], "colour": 1}}}' \
  '{"slots": {"ios-6.9": {"folder": "ios/big"}}}' \
  '{"slots": {"Bad Name": {"store": "ios", "folder": "ios/6.1", "sizes": ["1170x2532"]}}}' \
  '{"slots": ["ios-6.1"]}' \
  '{"play": {"tablet_slots": ["tablet13"]}}' \
  '{"min_counts": {"ios-6.1": 1}}'; do
  cfg "$bad"; run "$W/proj"; rc=$?
  check "rejected (exit 2, no traceback): $bad" test $rc -eq 2 -a "$(grep -c Traceback "$W/err")" -eq 0
done

echo "11. images in folders no slot reads"
mk "$W/stray" ios/6.3/1.png:1206x2622 ios/6.3/old/1.png:1206x2622 ios/1.png:1206x2622 ios/foo/1.png:1206x2622 \
  play/phone/1.png:1080x1920 play/phone/2.png:1080x1920 play/feature_graphic.png:1024x500 play/misc/1.png:1080x1920 \
  play/tablet7/.hidden.png:1200x1920
run "$W/stray" --json; check "inspect mode: warnings only" test $? -eq 0
check "every stray folder is reported, nested ones included" test "$(hc_py -c 'import json,sys; print(sorted(f["path"] for f in json.load(open(sys.argv[1]))["findings"] if f["code"]=="unknown-folder"))' "$W/out")" \
  = "['ios/', 'ios/6.3/old/', 'ios/foo/', 'play/misc/']"
check "they are WARN in inspect mode" test "$(code WARN | tr ' ' '\n' | grep -c unknown-folder)" -eq 1
run "$W/stray" --release --stores play,ios --no-supports-tablet --json
check "they are ERROR in release" test "$(code ERROR | tr ' ' '\n' | grep -c unknown-folder)" -eq 1

echo "12. the catalog is validated"
cp "$SKILL/references/store-slots.json" "$W/cat.json"
run "$W/empty" --catalog "$W/cat.json"; check "a copy of the catalog loads" test $? -eq 0
hc_py - "$W/cat.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["slots"]["ios-6.5"]["folder"] = "ios/6.9"; json.dump(d, open(sys.argv[1], "w"))
PY
run "$W/empty" --catalog "$W/cat.json"; check "two catalog slots sharing a folder: exit 2" test $? -eq 2
cp "$SKILL/references/store-slots.json" "$W/cat.json"
hc_py - "$W/cat.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["slots"]["ios-6.3"]["render"]["ios-63"] = "1290x2796"; json.dump(d, open(sys.argv[1], "w"))
PY
run "$W/empty" --catalog "$W/cat.json"; check "a render size its own slot rejects: exit 2" test $? -eq 2
printf '{"version": 2, "slots": {}}' > "$W/cat.json"
run "$W/empty" --catalog "$W/cat.json"; check "a wrong catalog version: exit 2" test $? -eq 2
run "$W/empty" --catalog "$W/nope.json"; check "a missing catalog: exit 2 with a hint" grep -q 'harness sync' "$W/err"

printf '\nstore asset tests: %d passed, %d failed\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
