#!/usr/bin/env bash
# === media variety demonstration ===
# Three fictional projects share the same app screens and demo data but have their own creative
# directions: Fernway (garden journal), Kestrel Ops (fleet dispatch) and Ledgerly, which keeps a
# 1.6-like look (Inter, indigo) on purpose. Each renders its approved store set and Open Graph
# canvas in production. Asserted: every render passes its checks, the configured layouts, type and
# backgrounds differ, and the kept look is not penalised. Image distances are printed as
# diagnostics only (no thresholds). A side-by-side sheet is written for a person to review:
# $VARIETY_SHEET if set (CI uploads it), otherwise inside the temporary folder.
# Needs Pillow and Chrome, Chromium or Edge (a SKIP locally, a failure when CI=true).
# Usage: bash tests/media-variety.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
SK="$ROOT/harness/skills"
RENDER="$SK/store-mockups/scripts/render_frames.py"
EXPORT="$SK/brand-assets/scripts/export_svg.py"
DIR="$SK/creative-direction/scripts/direction.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
skip_or_fail() { if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] $1 (required in CI)"; exit 1; fi; echo "[SKIP] media variety: $1"; exit 0; }
hc_py -c 'import PIL' 2>/dev/null || skip_or_fail "Pillow not installed"
hc_py -c "import sys; sys.path.insert(0, sys.argv[1]); from harnesslib import browser; browser.find_chrome(None)" "$ROOT/harness/lib" >/dev/null 2>&1 \
  || skip_or_fail "no Chrome, Chromium or Edge found"
W="$(mktemp -d "${TMPDIR:-/tmp}/media-variety-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 12 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
runin() { local dir="$1" rc; shift; ( cd "$dir" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
rc()    { [[ "$(cat "$W/rc")" == "$1" ]]; }

for v in fernway kestrel samebrand; do
  echo "== $v"
  hc_py "$MAKE" "$W/$v" "$v" --approve > "$W/out" 2>&1
  check "$v: the project builds with approved concepts" test $? -eq 0
  runin "$W/$v" "$RENDER" render store-assets/mockup-kit --all
  check "$v: the store set renders in production and passes its checks" rc 0
  cp "$W/rc" "$W/$v.render.rc"
  if [[ -f "$W/$v/brand/exports.json" ]]; then
    runin "$W/$v" "$EXPORT" --plan brand/exports.json
    check "$v: the Open Graph canvas exports" rc 0
  fi
done

echo "== the directions differ where they were configured to"
hc_py - "$W" > "$W/out" 2>&1 <<'PY'
import glob, json, sys
from pathlib import Path
root = Path(sys.argv[1])
def concept(v):
    return json.load(open(root / v / "brand/concepts/store/20261002-120000-0a0b0c/a.json"))["spec"]
def fonts(v):
    m = json.load(open(sorted(glob.glob(str(root / v / "brand/runs/store/*.json")))[-1]))
    return sorted({f["family"] for f in m["fonts"]})
a, b = concept("fernway"), concept("kestrel")
checks = {
    "layout sets differ": set(a["layouts"]) != set(b["layouts"]),
    "device styles differ": a["device"]["style"] != b["device"]["style"],
    "accent treatments differ": a["caption"]["accent"] != b["caption"]["accent"],
    "background recipes differ": {x["recipe"] for x in a["backgrounds"].values()} != {x["recipe"] for x in b["backgrounds"].values()},
    "caption font families differ": fonts("fernway") != fonts("kestrel"),
    "feature-graphic layouts differ": a["featureGraphic"]["layout"] != b["featureGraphic"]["layout"],
}
for k, v in checks.items():
    print(("ok   " if v else "FAIL ") + k)
sys.exit(0 if all(checks.values()) else 1)
PY
r=$?; sed 's/^/  /' "$W/out"
check "fernway and kestrel differ in every configured lever" test $r -eq 0
runin "$W/samebrand" "$DIR" concept check "brand/concepts/store/20261002-120000-0a0b0c/a.json"
check "the kept 1.6-like look shows its signals" grep -q "harness:inter-800-tight" "$W/out"
check "and its production render was not penalised" test "$(cat "$W/samebrand.render.rc")" == 0

echo "== diagnostics (printed, never asserted)"
for pair in "fernway kestrel" "fernway samebrand" "kestrel samebrand"; do
  set -- $pair
  runin "$W" "$DIR" compare "$W/$1/store-assets/mockup-kit/out/play/phone/01-home.png" "$W/$2/store-assets/mockup-kit/out/play/phone/01-home.png"
  echo "  $1 vs $2: $(tr '\n' ' ' < "$W/out")"
done

SHEET="${VARIETY_SHEET:-$W/variety-sheet.png}"
hc_py - "$W" "$SHEET" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent))
root, dest = Path(sys.argv[1]), Path(sys.argv[2])
from PIL import Image
cols = []
for v in ("fernway", "kestrel", "samebrand"):
    out = root / v / "store-assets/mockup-kit/out"
    tiles = [out / "play/phone/01-home.png", out / "play/phone/02-activity.png"]
    cols.append([Image.open(p).convert("RGB").resize((270, 480)) for p in tiles if p.is_file()])
W = 16 + len(cols) * (270 * 2 + 32)
sheet = Image.new("RGB", (W, 512), (24, 24, 28))
x = 16
for col in cols:
    for im in col:
        sheet.paste(im, (x, 16)); x += 286
    x += 16
dest.parent.mkdir(parents=True, exist_ok=True)
sheet.save(dest)
print(f"variety sheet: {dest}")
PY
check "the side-by-side sheet is written" test -f "$SHEET"

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "media variety tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
