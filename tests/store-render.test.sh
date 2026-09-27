#!/usr/bin/env bash
# === store render / brand export / icon set tests ===
# render_frames.py (kit reuse, .build/, lock, --all, contrast), export_svg.py
# (plans, verification, HTML contrast) and make_icon_set.py (--no-web).
# Needs Python 3.9+ with Pillow; the rendering cases also need Chrome, Chromium
# or Edge. Missing tools are a SKIP locally and a failure when CI=true.
# Usage: bash tests/store-render.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="$ROOT/harness/skills"
RENDER="$SK/store-mockups/scripts/render_frames.py"
EXPORT="$SK/brand-assets/scripts/export_svg.py"
ICONS="$SK/app-icons/scripts/make_icon_set.py"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1  # importing the scripts must not leave __pycache__ in harness/
if ! hc_py -c 'import PIL' 2>/dev/null; then
  if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] Pillow is required in CI (pip install pillow)"; exit 1; fi
  echo "[SKIP] store render tests: Pillow not installed (pip install pillow)"; exit 0
fi
W="$(mktemp -d "${TMPDIR:-/tmp}/store-render-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0

ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 15 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
run()   { local rc; ( cd "$W/proj" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
rc()    { [[ "$(cat "$W/rc")" == "$1" ]]; }
has()   { grep -q -- "$1" "$W/out"; }
edit()  { hc_py - "$@" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
cfg = json.load(open(path, encoding="utf-8"))
exec(expr)
json.dump(cfg, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PY
}
only_content() { # the kit root holds nothing but content files, .gitignore and the two build folders
  local extra
  extra="$(cd "$1" && ls -A | grep -vxE 'app\.css|screens\.js|demo-data\.js|frames\.json|custom-objects\.js|assets|\.gitignore|\.build|out')"
  [[ -z "$extra" ]]
}

mkdir -p "$W/proj"
KIT="store-assets/mockup-kit"

echo "== init: one kit per project"
run "$RENDER" init "$KIT"
check "init succeeds" rc 0
check "init writes the content files" test -f "$W/proj/$KIT/frames.json" -a -f "$W/proj/$KIT/screens.js"
check "init writes the kit .gitignore (.build/ and out/)" grep -qx 'out/' "$W/proj/$KIT/.gitignore"
check "init copies no engine files into the kit" only_content "$W/proj/$KIT"
check "the template app.css no longer points at a kit copy of Ionicons" bash -c "! grep -q 'assets/Ionicons.ttf' '$W/proj/$KIT/app.css'"
run "$RENDER" init store-assets/second-kit
check "a second kit is refused" rc 1
check "the refusal names the existing kit" has "mockup-kit"
check "nothing was created for the refused kit" test ! -e "$W/proj/store-assets/second-kit"
run "$RENDER" init store-assets/second-kit --new
check "--new creates a second kit on purpose" rc 0
rm -rf "$W/proj/store-assets/second-kit"
run "$RENDER" init "$KIT"
check "re-running init on the same kit is fine (skips existing files)" rc 0

echo "== render: validation and argument checks (no Chrome needed)"
run "$RENDER" render "$KIT" --check-only
check "--check-only accepts the example kit" rc 0
run "$RENDER" render "$KIT" --all --frames 01-home
check "--all with --frames is refused" rc 2
run "$RENDER" render "$KIT" --frames nope --check-only
check "an unknown frame id is refused" rc 2
cp "$W/proj/$KIT/frames.json" "$W/frames.json.bak"
edit "$W/proj/$KIT/frames.json" 'cfg["frames"][1]["id"] = cfg["frames"][0]["id"]'
run "$RENDER" render "$KIT" --check-only
check "duplicate frame ids are refused" rc 1
check "the duplicate id is named" has "used more than once"
cp "$W/frames.json.bak" "$W/proj/$KIT/frames.json"
mkdir -p "$W/proj/$KIT/.build/render.lock"
run "$RENDER" render "$KIT" --sizes play-phone
check "a render is refused while another holds the kit lock" rc 1
check "the lock refusal says how to recover" has "render.lock"
rm -rf "$W/proj/$KIT/.build"

echo "== make_icon_set.py"
# Paths go in as arguments, never inside the code string: Git Bash converts only arguments.
hc_py -c "
import sys
from PIL import Image, ImageDraw
im = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
ImageDraw.Draw(im).ellipse((200, 200, 824, 824), fill=(255, 255, 255, 255))
im.save(sys.argv[1])" "$W/proj/glyph.png"
run "$ICONS" generate --master glyph.png --bg "#3525cd" --out icons-web
check "generate succeeds" rc 0
check "the default set includes the web icons" test -f "$W/proj/icons-web/web/pwa-512.png"
run "$ICONS" generate --master glyph.png --bg "#3525cd" --out icons-app --no-web
check "--no-web succeeds" rc 0
check "--no-web writes no web/ folder" test ! -e "$W/proj/icons-app/web"
check "--no-web leaves web out of the Expo snippet" bash -c "! grep -q '\"web\"' '$W/proj/icons-app/expo-icon-snippet.json'"
check "--no-web still writes the platform icons" test -f "$W/proj/icons-app/android/monochrome.png" -a -f "$W/proj/icons-app/play/icon-512.png"

echo "== export_svg.py: argument and plan checks (no Chrome needed)"
mkdir -p "$W/proj/brand/html"
printf '{"exports": [{"src": "mark.svg", "sizes": ["64x64"]}]}\n' > "$W/proj/brand/bad.json"
run "$EXPORT" --plan brand/bad.json
check "a plan entry without out is refused" rc 1
check "the plan error names the entry" has "plan entry 1"
run "$EXPORT" --plan brand/bad.json --size 10x10
check "--plan with --size is refused" rc 2
run "$EXPORT" brand/a.svg brand/b.svg --size 10x10 --out x --name one
check "--name with two sources is refused" rc 2

# ---------------------------------------------------------------- with Chrome
CHROME="$(hc_py -c "import sys; sys.path.insert(0, sys.argv[1]); import render_frames as r
try: print(r.find_chrome(None))
except SystemExit: pass" "$SK/store-mockups/scripts" 2>/dev/null)"
if [[ -z "$CHROME" ]]; then
  if [[ "${CI:-}" == "true" ]]; then bad "Chrome, Chromium or Edge is required in CI for the render tests"
  else echo "[SKIP] rendering cases: no Chrome, Chromium or Edge found"; fi
else
  echo "== render --all (classic) with $CHROME"
  edit "$W/proj/$KIT/frames.json" 'cfg["sizes"] = ["play-phone", "ios-69"]'
  mkdir -p "$W/proj/$KIT/out/play/phone"
  hc_py -c "import sys; from PIL import Image; Image.new('RGB', (1080, 1920)).save(sys.argv[1])" "$W/proj/$KIT/out/play/phone/99-renamed.png"
  printf 'old engine copy\n' > "$W/proj/$KIT/frames.generated.js"
  run "$RENDER" render "$KIT" --all
  check "render --all succeeds" rc 0
  check "every frame is rendered at each size" test -f "$W/proj/$KIT/out/play/phone/02-activity.png" -a -f "$W/proj/$KIT/out/ios/6.9/01-home.png"
  check "the feature graphic is rendered" test -f "$W/proj/$KIT/out/play/feature_graphic_1024x500.png"
  check "the contact sheet is written" test -f "$W/proj/$KIT/out/contact-sheet.png"
  check "a PNG of a renamed frame is removed" test ! -e "$W/proj/$KIT/out/play/phone/99-renamed.png"
  check "the file check ran" has "verify: 5 files, 0 problem"
  check "the contrast check ran and passed" has "contrast OK"
  check "the store checker ran" has "store check OK"
  check "leftover engine files are reported" has "unused files from an older harness"
  rm -f "$W/proj/$KIT/frames.generated.js"
  check "build files live in .build/" test -f "$W/proj/$KIT/.build/frame.html" -a -f "$W/proj/$KIT/.build/frames.generated.js"
  check ".build/ ignores itself" grep -qx '\*' "$W/proj/$KIT/.build/.gitignore"
  check "the kit root still holds only content" only_content "$W/proj/$KIT"
  check "the lock is released" test ! -e "$W/proj/$KIT/.build/render.lock"
  if command -v git >/dev/null 2>&1; then
    git -C "$W/proj" init -q 2>/dev/null
    git -C "$W/proj" status --porcelain -uall -- "$KIT" > "$W/out"
    check "git sees only the kit's content files" bash -c "! grep -qE '\\.build/|/out/' '$W/out' && [[ \$(wc -l < '$W/out') -eq 5 ]]"
  fi
  run "$RENDER" render "$KIT" --frames 01-home --sizes play-phone --out elsewhere
  check "--out renders to another folder" test -f "$W/proj/elsewhere/play/phone/01-home.png"

  echo "== contrast check"
  edit "$W/proj/$KIT/frames.json" 'cfg["brand"]["sub"] = "#4a3fd0"; cfg["sizes"] = ["play-phone"]'
  run "$RENDER" contrast "$KIT"
  check "low-contrast captions fail" rc 1
  check "the failing caption is named" has "FAIL  01-home @ play-phone: sub"
  check "headlines still pass" bash -c "! grep -q 'FAIL .*: head' '$W/out'"
  cp "$W/frames.json.bak" "$W/proj/$KIT/frames.json"

  echo "== render --all (continuous)"
  run "$RENDER" init "$W/proj/pano" --style continuous --new
  edit "$W/proj/pano/frames.json" 'cfg["sizes"] = ["play-phone", "ios-69"]'
  run "$RENDER" render pano --all
  check "continuous render --all succeeds" rc 0
  check "the Android strip is written" test -f "$W/proj/pano/out/strip-android.png"
  check "the iOS strip is written" test -f "$W/proj/pano/out/strip-ios.png"
  check "the seam report is printed" has "rows matching"
  check "the Android-only brand frame is skipped on iOS" test ! -e "$W/proj/pano/out/ios/6.9/05-brand.png"

  echo "== export_svg.py with Chrome"
  cp "$SK/brand-assets/templates/logo-master.svg.template" "$W/proj/brand/mark.svg"
  cat > "$W/proj/brand/html/card.html" <<'HTML'
<!doctype html><html><head><style>body{margin:0;background:#2a1bb0;font:600 40px sans-serif}
p{margin:40px}.ok{color:#ffffff}</style></head><body><p class="ok">Readable caption</p></body></html>
HTML
  sed 's/#ffffff/#3a2bc0/' "$W/proj/brand/html/card.html" > "$W/proj/brand/html/faint.html"
  printf '%s\n' '{"exports": [' \
    '{"src": "mark.svg", "sizes": ["256x256", "128x128"], "out": "png"},' \
    '{"src": "html/card.html", "sizes": ["600x200"], "out": "social", "flatten": "#2a1bb0"}]}' > "$W/proj/brand/exports.json"
  run "$EXPORT" --plan brand/exports.json
  check "a plan exports every entry" rc 0
  check "the plan writes each size" test -f "$W/proj/brand/png/mark-256x256.png" -a -f "$W/proj/brand/png/mark-128x128.png"
  check "flattened exports are RGB" hc_py -c "from PIL import Image; import sys; sys.exit(Image.open(sys.argv[1]).mode != 'RGB')" "$W/proj/brand/social/card-600x200.png"
  check "the HTML contrast check ran" has "contrast card.html"
  run "$EXPORT" --plan brand/exports.json --only mark
  check "--only limits the plan" bash -c "grep -q 'from 1 source' '$W/out'"
  run "$EXPORT" brand/html/faint.html --size 600x200 --out brand/social
  check "low-contrast HTML text fails" rc 1
  check "the faint text is named" has "Readable caption"
  run "$EXPORT" brand/html/faint.html --size 600x200 --out brand/social --no-contrast
  check "--no-contrast skips the check" rc 0
fi

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "store render tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
