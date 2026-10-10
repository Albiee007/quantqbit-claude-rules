#!/usr/bin/env bash
# === store render / brand export / icon set tests ===
# render_frames.py: kit reuse, .build/, locks, legacy 1.6 kits (unchanged output, pixel parity with
# the v1.6.1 scripts), format-2 kits (approved production, drafts, layouts, fonts, contrast, staged
# publishing, run manifests, failures that keep previous renders). export_svg.py: plans,
# placeholders, HTML contrast, canvas entries. make_icon_set.py: legacy and direction-driven sets.
# Needs Python 3.9+ with Pillow; the rendering cases also need Chrome, Chromium or Edge, and the
# parity case needs the v1.6.1 tag (CI checks out full history). Missing tools are a SKIP locally
# and a failure when CI=true.
# Usage: bash tests/store-render.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="$ROOT/harness/skills"
RENDER="$SK/store-mockups/scripts/render_frames.py"
EXPORT="$SK/brand-assets/scripts/export_svg.py"
ICONS="$SK/app-icons/scripts/make_icon_set.py"
DIR="$SK/creative-direction/scripts/direction.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
LEGACY="$ROOT/tests/fixtures/legacy-1.6"
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
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 15 "$W/out" 2>/dev/null | sed 's/^/        /'
          annotate "$*"; }
annotate() { # on GitHub Actions, a failure also becomes an annotation (readable without the log)
  [[ "${GITHUB_ACTIONS:-}" == "true" ]] || return 0
  local body; body="$(tail -n 8 "$W/out" 2>/dev/null | cut -c1-300 | sed -e 's/%/%25/g' | awk '{ printf "%s%%0A", $0 }')"
  printf '::error title=store-render: %s::%s\n' "${1//::/ }" "$body"
}
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
run()   { local rc; ( cd "$W/proj" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
runin() { local dir="$1" rc; shift; ( cd "$dir" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
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
only_content() { # the kit root holds nothing but content files, .gitignore and the generated folders
  local extra
  extra="$(cd "$1" && ls -A | grep -vxE 'app\.css|screens\.js|demo-data\.js|frames\.json|custom-objects\.js|assets|\.gitignore|\.build|\.preview|out')"
  [[ -z "$extra" ]]
}
tree_hash() { (cd "$1" && find . -type f ! -path './.build/*' ! -path './.preview/*' ! -path './out/*' | LC_ALL=C sort | xargs cat | hc_py -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"); }
glyph() { hc_py -c "
import sys
from PIL import Image, ImageDraw
im = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
ImageDraw.Draw(im).ellipse((200, 200, 824, 824), fill=(255, 255, 255, 255))
im.save(sys.argv[1])" "$1"; }

mkdir -p "$W/proj"
KIT="store-assets/mockup-kit"

echo "== init: one format-2 kit per project"
run "$RENDER" init "$KIT"
check "init succeeds" rc 0
check "init writes the content files" test -f "$W/proj/$KIT/frames.json" -a -f "$W/proj/$KIT/screens.js"
check "the new kit is format 2" grep -q '"format": 2' "$W/proj/$KIT/frames.json"
check "init says the look comes from the direction" has "creative-director"
check "init writes the kit .gitignore (.build/, .preview/ and out/)" bash -c "grep -qx 'out/' '$W/proj/$KIT/.gitignore' && grep -qx '.preview/' '$W/proj/$KIT/.gitignore'"
check "init copies no engine files into the kit" only_content "$W/proj/$KIT"
check "the templates carry no 1.6 look outside legacy-1.6/" bash -c "! grep -rlE '#3525cd|#2a1bb0|#9ff3cf|#0e0f1c|Inter, sans-serif|fonts.googleapis' '$SK/store-mockups/templates' --exclude-dir=legacy-1.6"
run "$RENDER" init store-assets/second-kit
check "a second kit is refused" rc 1
check "the refusal names the existing kit" has "mockup-kit"
check "nothing was created for the refused kit" test ! -e "$W/proj/store-assets/second-kit"
run "$RENDER" init store-assets/second-kit --new
check "--new creates a second kit on purpose" rc 0
rm -rf "$W/proj/store-assets/second-kit"
run "$RENDER" render "$KIT" --check-only
check "a format-2 kit without a direction is refused (exit 1)" rc 1
check "the refusal points at the creative-director" has "creative-director"

echo "== legacy 1.6 kit: validation and arguments (no Chrome needed)"
cp -R "$LEGACY/classic" "$W/proj/legacy"
run "$RENDER" render legacy --check-only
check "--check-only accepts a 1.6 kit" rc 0
check "with a migration warning" has "legacy 1.6 kit"
run "$RENDER" render legacy --all --frames 01-home
check "--all with --frames is refused (exit 2)" rc 2
run "$RENDER" render legacy --frames nope --check-only
check "an unknown frame id is refused (exit 2)" rc 2
cp "$W/proj/legacy/frames.json" "$W/frames.json.bak"
edit "$W/proj/legacy/frames.json" 'cfg["frames"][1]["id"] = cfg["frames"][0]["id"]'
run "$RENDER" render legacy --check-only
check "duplicate frame ids are refused" rc 1
check "the duplicate id is named" has "used more than once"
cp "$W/frames.json.bak" "$W/proj/legacy/frames.json"
mkdir -p "$W/proj/legacy/.build/render.lock"
run "$RENDER" render legacy --sizes play-phone
check "a render is refused while another holds the kit lock (exit 2)" rc 2
check "the lock refusal says how to recover" has "render.lock"
rm -rf "$W/proj/legacy/.build"

echo "== sizes: any size, declared in frames.json or on the command line (no Chrome needed)"
run "$RENDER" render legacy --check-only --sizes ios-63
check "the built-in 6.3 inch key is accepted" rc 0
run "$RENDER" render legacy --check-only --sizes ios:1206x2622:ios/6.3,play:1920x1080
check "platform:WxH[:folder] one-offs are accepted" rc 0
for bad in nope fg ios:100x2622 ios:1206x9000 ios:1206x2622:ios/../x ios:1206x2622:/tmp/x ios:1206x2622:play/x \
    play:1080x1920:ios/x mac:1206x2622 ios-69,ios-69-1320; do
  run "$RENDER" render legacy --check-only --sizes "$bad"
  check "--sizes $bad is refused (exit 2)" rc 2
done
check "a folder collision names both sizes" has "'ios-69' (1290x2796) and 'ios-69-1320' (1320x2868) both write to ios/6.9/"
for obj in '{"key": "fg", "size": "1024x500", "platform": "play"}' \
    '{"key": "ios-63", "size": "1206x2622", "platform": "ios"}' \
    '{"key": "x", "size": "1206x2622", "platform": "ios", "folder": "ios/../../etc"}' \
    '{"key": "x", "size": "1206x2622", "platform": "ios", "colour": 1}' \
    '{"key": "x", "size": "12x26", "platform": "ios"}'; do
  edit "$W/proj/legacy/frames.json" "cfg['sizes'] = [json.loads(sys.argv[3])]" "$obj"
  run "$RENDER" render legacy --check-only
  check "frames.json size $obj is refused (exit 2)" rc 2
done
edit "$W/proj/legacy/frames.json" 'cfg["sizes"] = ["play-phone", {"key": "ios-61", "size": "1179x2556", "platform": "ios", "folder": "ios/6.1"}]'
run "$RENDER" render legacy --check-only
check "a frames.json size object is accepted" rc 0
run "$RENDER" render legacy --check-only --sizes ios-61
check "and can be picked with --sizes" rc 0
cp "$W/frames.json.bak" "$W/proj/legacy/frames.json"

echo "== make_icon_set.py"
# Paths go in as arguments, never inside the code string: Git Bash converts only arguments.
glyph "$W/proj/glyph.png"
run "$ICONS" generate --master glyph.png --bg "#2f6b5a" --out icons-web
check "generate succeeds" rc 0
check "the default set includes the web icons" test -f "$W/proj/icons-web/web/pwa-512.png"
check "the mark contrast is reported, without a WCAG claim" has "no WCAG threshold applies"
run "$ICONS" generate --master glyph.png --bg "#2f6b5a" --out icons-app --no-web
check "--no-web succeeds" rc 0
check "--no-web writes no web/ folder" test ! -e "$W/proj/icons-app/web"
check "--no-web leaves web out of the Expo snippet" bash -c "! grep -q '\"web\"' '$W/proj/icons-app/expo-icon-snippet.json'"
check "--no-web still writes the platform icons" test -f "$W/proj/icons-app/android/monochrome.png" -a -f "$W/proj/icons-app/play/icon-512.png"
run "$ICONS" generate --master glyph.png --bg-style linear --bg "#b5653d" --bg2 "#5a2a14" --angle 160 --out icons-grad --no-web
check "a linear background generates" rc 0
check "the snippet points at the background image" grep -q 'backgroundImage' "$W/proj/icons-grad/expo-icon-snippet.json"
check "the adaptive background is a gradient" hc_py -c "
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('RGB')
sys.exit(0 if im.getpixel((512, 20)) != im.getpixel((512, 1003)) else 1)" "$W/proj/icons-grad/android/adaptive-background.png"
run "$ICONS" generate --master glyph.png --bg "#f2f2f2" --mark-contrast 3 --out icons-low
check "a project contrast target that the mark misses fails" rc 1
check "and is not presented as WCAG" has "not a WCAG requirement"
check "nothing is written when it fails" test ! -e "$W/proj/icons-low"
run "$ICONS" generate --master glyph.png --bg "#2f6b5a" --glyph-offset 0.5,0 --out x
check "an out-of-range glyph offset is refused (exit 2)" rc 2

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
cp "$SK/brand-assets/templates/logo-master.svg.template" "$W/proj/brand/mark-template.svg"
run "$EXPORT" brand/mark-template.svg --size 64x64 --out brand/png
check "a source still holding template placeholders is refused" rc 1
check "and the placeholders are named" has "MARK_GEOMETRY"

# ---------------------------------------------------------------- with Chrome
CHROME="$(hc_py -c "import sys; sys.path.insert(0, sys.argv[1]); from harnesslib import browser
try: print(browser.find_chrome(None))
except Exception: pass" "$ROOT/harness/lib" 2>/dev/null)"
if [[ -z "$CHROME" ]]; then
  if [[ "${CI:-}" == "true" ]]; then bad "Chrome, Chromium or Edge is required in CI for the render tests"
  else echo "[SKIP] rendering cases: no Chrome, Chromium or Edge found"; fi
else
  echo "== browser smoke test ($CHROME)"
  printf '<!doctype html><body style="margin:0;background:#123456"></body>' > "$W/proj/smoke.html"
  run -c "import sys, time; sys.path.insert(0, sys.argv[1]); from pathlib import Path; from harnesslib import browser
browser.TIMEOUT_S = 90; t = time.time()
print(browser.version(sys.argv[2]))
browser.screenshot(sys.argv[2], Path(sys.argv[3]).resolve().as_uri(), (64, 64), Path(sys.argv[4]).resolve(), 1000)
print(f'screenshot in {time.time() - t:.1f} s')" "$ROOT/harness/lib" "$CHROME" smoke.html smoke.png
  cat "$W/out"
  if ! rc 0; then
    bad "headless Chrome can take one screenshot within 90 s"
    echo "store render tests: $pass passed, $fail failed (stopped: the browser does not work here)"
    exit 1
  fi
  ok "headless Chrome takes a screenshot"; rm -f "$W/proj/smoke.html" "$W/proj/smoke.png"
  echo "== legacy 1.6 kit: render --all with $CHROME"
  mkdir -p "$W/proj/legacy/out/play/phone"
  hc_py -c "import sys; from PIL import Image; Image.new('RGB', (1080, 1920)).save(sys.argv[1])" "$W/proj/legacy/out/play/phone/99-unknown.png"
  printf 'old engine copy\n' > "$W/proj/legacy/frames.generated.js"
  run "$RENDER" render legacy --all
  check "render --all succeeds" rc 0
  check "every frame is rendered at each size" test -f "$W/proj/legacy/out/play/phone/02-activity.png" -a -f "$W/proj/legacy/out/ios/6.9/01-home.png"
  check "the feature graphic is rendered" test -f "$W/proj/legacy/out/play/feature_graphic_1024x500.png"
  check "the contact sheet is written" test -f "$W/proj/legacy/out/contact-sheet.png"
  check "a PNG no render recorded is kept and reported" bash -c "[[ -f '$W/proj/legacy/out/play/phone/99-unknown.png' ]] && grep -q '99-unknown.png was not written by a recorded render' '$W/out'"
  check "the file check ran" has "verify: 5 files, 0 problem"
  check "sampled contrast is REVIEW REQUIRED, never a plain pass" has "contrast REVIEW REQUIRED"
  check "the store checker ran" has "store PASS"
  check "leftover engine files are reported" has "unused files from an older harness"
  check "the published files are recorded as owned" grep -q '01-home.png' "$W/proj/legacy/out/.render-manifest.json"
  rm -f "$W/proj/legacy/frames.generated.js"
  check "build files live in .build/" test -f "$W/proj/legacy/.build/frame.html" -a -f "$W/proj/legacy/.build/frames.generated.js"
  check ".build/ ignores itself" grep -qx '\*' "$W/proj/legacy/.build/.gitignore"
  check "the kit root still holds only content" only_content "$W/proj/legacy"
  check "the locks are released" test ! -e "$W/proj/legacy/.build/render.lock" -a ! -e "$W/proj/legacy/out/.publish.lock"
  check "no staging folder is left" bash -c "! ls -d '$W/proj/legacy/out'/.staging-* 2>/dev/null"
  edit "$W/proj/legacy/frames.json" 'cfg["frames"][1]["id"] = "02-renamed"'
  run "$RENDER" render legacy --all
  check "a recorded PNG of a renamed frame is removed" bash -c "[[ ! -e '$W/proj/legacy/out/play/phone/02-activity.png' && -f '$W/proj/legacy/out/play/phone/02-renamed.png' ]]"
  cp "$W/frames.json.bak" "$W/proj/legacy/frames.json"
  run "$RENDER" render legacy --frames 01-home --sizes play-phone --out elsewhere
  check "--out renders to another folder" test -f "$W/proj/elsewhere/play/phone/01-home.png"

  echo "== legacy contrast and failed runs"
  cp "$W/proj/legacy/out/play/phone/01-home.png" "$W/before.png"
  edit "$W/proj/legacy/frames.json" 'cfg["brand"]["sub"] = "#4a3fd0"; cfg["sizes"] = ["play-phone"]'
  run "$RENDER" contrast legacy
  check "low-contrast captions fail" rc 1
  check "the failing caption is named" has "FAIL .*01-home @ play-phone: sub"
  check "headlines still pass the 1.6 rule" bash -c "! grep -q 'FAIL .*: head' '$W/out'"
  run "$RENDER" render legacy --all
  check "a failing release set exits 1" rc 1
  check "and publishes nothing" has "NOT published"
  check "the previous renders are untouched" cmp -s "$W/before.png" "$W/proj/legacy/out/play/phone/01-home.png"
  cp "$W/frames.json.bak" "$W/proj/legacy/frames.json"

  echo "== legacy continuous kit"
  cp -R "$LEGACY/continuous" "$W/proj/pano"
  mkdir -p "$W/proj/pano/assets"
  hc_py -c "import sys; from PIL import Image; Image.new('RGB', (400, 400), (200, 120, 60)).save(sys.argv[1])" "$W/proj/pano/assets/photo.png"
  run "$RENDER" render pano --all
  check "continuous render --all succeeds" rc 0
  check "the Android strip is written" test -f "$W/proj/pano/out/strip-android.png"
  check "the iOS strip is written" test -f "$W/proj/pano/out/strip-ios.png"
  check "the seam report is printed" has "rows matching"
  check "the Android-only brand frame is skipped on iOS" test ! -e "$W/proj/pano/out/ios/6.9/05-brand.png"

  echo "== legacy pixel parity with the v1.6.1 scripts"
  OLD="$W/v161"; mkdir -p "$OLD"
  # The v1.6.1 scripts start Chrome without the macOS keychain flags, without timeouts and wait
  # for it to exit (which it may not do while Google's updater runs). A wrapper runs Chrome the
  # way the current engine does (not on Windows, where a script can't stand in for an .exe and
  # the engine's waiting isn't needed), and each render is bounded.
  OLDCHROME="$CHROME"; PYCMD="$(hc_python)"
  if [[ "$(uname -s)" != MINGW* && "$(uname -s)" != MSYS* && "$(uname -s)" != CYGWIN* ]]; then
    { printf '#!%s\n' "$(command -v python3 || echo /usr/bin/python3)"
      printf 'import sys\nsys.dont_write_bytecode = True\nsys.path.insert(0, %s)\n' "'$ROOT/harness/lib'"
      printf 'CHROME = %s\n' "'$CHROME'"
      cat <<'PY'
from harnesslib import browser
args = sys.argv[1:]
shot = next((a.split("=", 1)[1] for a in args if a.startswith("--screenshot=")), None)
done = browser._shot_done(shot) if shot else browser._dom_done if "--dump-dom" in args else None
rc, out, err = browser._run([CHROME, "--use-mock-keychain", "--password-store=basic",
                             "--no-default-browser-check"] + args, 240, done)
sys.stdout.buffer.write(out); sys.stderr.buffer.write(err)
sys.exit(rc)
PY
    } > "$W/chrome-wrapper"
    chmod +x "$W/chrome-wrapper"; OLDCHROME="$W/chrome-wrapper"
  fi
  if git -C "$ROOT" archive v1.6.1 harness/skills/store-mockups harness/skills/store-submission-precheck 2>/dev/null | tar -x -C "$OLD" 2>/dev/null; then
    check "the frozen engine is byte-identical to v1.6.1" bash -c "cmp -s '$OLD/harness/skills/store-mockups/templates/frame.html' '$SK/store-mockups/templates/legacy-1.6/frame.html' && cmp -s '$OLD/harness/skills/store-mockups/templates/objects.js' '$SK/store-mockups/templates/legacy-1.6/objects.js'"
    for k in classic continuous minimal-brand; do
      rm -rf "$W/proj/p-$k"; cp -R "$LEGACY/$k" "$W/proj/p-$k"
      if [[ "$k" == continuous ]]; then mkdir -p "$W/proj/p-$k/assets"; cp "$W/proj/pano/assets/photo.png" "$W/proj/p-$k/assets/"; fi
      edit "$W/proj/p-$k/frames.json" 'cfg["sizes"] = ["play-phone"]'
      # shellcheck disable=SC2086  # $PYCMD may be "py -3"
      ( cd "$W/proj" && CHROME="$OLDCHROME" perl -e 'alarm shift; exec @ARGV' 300 $PYCMD           "$OLD/harness/skills/store-mockups/scripts/render_frames.py" render "p-$k" --sizes play-phone --out "old-$k" )         > "$W/out" 2>&1; echo $? > "$W/rc"
      oldrc=$(cat "$W/rc")
      run "$RENDER" render "p-$k" --sizes play-phone --out "new-$k"
      check "$k: both renders succeed" bash -c "[[ $oldrc == 0 && \$(cat '$W/rc') == 0 ]]"
      check "$k: decoded pixels are identical" hc_py -c "
import sys
from pathlib import Path
from PIL import Image, ImageChops
a, b = Path(sys.argv[1]), Path(sys.argv[2])
olds = sorted(a.rglob('*.png'))
same = bool(olds) and all(ImageChops.difference(Image.open(p).convert('RGBA'), Image.open(b / p.relative_to(a)).convert('RGBA')).getbbox() is None for p in olds)
sys.exit(0 if same else 1)" "$W/proj/old-$k" "$W/proj/new-$k"
    done
  elif [[ "${CI:-}" == "true" ]]; then bad "the v1.6.1 tag is required in CI for the parity check (fetch full history)"
  else echo "[SKIP] parity: the v1.6.1 tag is not available in this clone"; fi

  echo "== format 2: approved production"
  F="$W/fern"; hc_py "$MAKE" "$F" fernway --approve > "$W/out" 2>&1
  check "the fernway fixture builds" test $? -eq 0
  K="$F/store-assets/mockup-kit"
  before="$(tree_hash "$K")"
  runin "$F" "$RENDER" render store-assets/mockup-kit --all
  check "render --all in the approved concept succeeds" rc 0
  check "contrast is computed for captions on known backgrounds" has "contrast PASS"
  check "glyphs and clipping are checked" has "text PASS"
  check "a run manifest is written" bash -c "ls '$F'/brand/runs/store/*.json >/dev/null 2>&1"
  check "the manifest records outputs, approvals and fonts" hc_py -c "
import json, sys, glob
m = json.load(open(sorted(glob.glob(sys.argv[1] + '/brand/runs/store/*.json'))[-1]))
sys.exit(0 if m['status'] == 'complete' and len(m['outputs']) >= 5 and len(m['approvals']) == 2 and m['fonts'] else 1)" "$F"
  check "production touched no kit content" test "$before" == "$(tree_hash "$K")"
  cp "$K/out/play/phone/01-home.png" "$W/fern-before.png"
  edit "$K/frames.json" 'cfg["frames"][0]["sub"] = "Every bed, every season 東"'
  runin "$F" "$RENDER" render store-assets/mockup-kit --all
  check "a glyph the caption font lacks fails the fonts check" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'text: .*has no glyph' '$W/out'"
  check "the failed run kept the previous renders" cmp -s "$W/fern-before.png" "$K/out/play/phone/01-home.png"
  check "the failed run wrote no manifest" test "$(ls "$F"/brand/runs/store/*.json | wc -l)" -eq 1
  edit "$K/frames.json" 'cfg["frames"][0]["sub"] = "Every bed, every season, one journal"'

  echo "== any size: one-offs, frames.json sizes and the store gate"
  dims() { hc_py -c "import sys; from PIL import Image; im = Image.open(sys.argv[1]); print(f'{im.size[0]}x{im.size[1]} {im.mode}')" "$1"; }
  run "$RENDER" render legacy --frames 01-home --sizes ios:1206x2622:ios/6.3,ios-63 --out x63
  check "a one-off size renders" rc 0
  check "into its folder at its size, RGB" test "$(dims "$W/proj/x63/ios/6.3/01-home.png")" == "1206x2622 RGB"
  check "the same size named twice renders once" test "$(grep -c 'ok  01-home.png  1206x2622' "$W/out")" -eq 1
  run "$RENDER" render legacy --frames 01-home --sizes android:1500x2000 --out xdefault
  check "a one-off without a folder goes to <store>/<WxH>" test "$(dims "$W/proj/xdefault/play/1500x2000/01-home.png")" == "1500x2000 RGB"
  edit "$W/proj/legacy/frames.json" 'cfg["sizes"] = [{"key": "play-chromebook", "size": "1920x1080", "platform": "play", "folder": "play/chromebook"}]'
  run "$RENDER" render legacy --frames 01-home --out xcb
  check "a frames.json size object renders (play means android)" test "$(dims "$W/proj/xcb/play/chromebook/01-home.png")" == "1920x1080 RGB"
  cp "$W/frames.json.bak" "$W/proj/legacy/frames.json"

  cp -R "$K/out" "$W/fern-out-before"
  hc_py -c "import sys; from PIL import Image; Image.new('RGBA', (512, 512), (40, 90, 60, 255)).save(sys.argv[1])" "$F/play-icon.png"
  printf '{"stores": ["play", "ios"], "ios": {"supports_tablet": false}, "play": {"icon": "../play-icon.png"}}\n' > "$F/store-assets/store-assets.json"
  runin "$F" "$RENDER" render store-assets/mockup-kit --all --no-contrast
  check "with a store-assets.json, render --all runs the release gate" has "store check: check_store_assets.py --release with .*store-assets.json"
  check "a set without the required 6.3 inch slot is not published" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'NOT published' '$W/out' && grep -q 'missing-slot.*ios/6.3' '$W/out'"
  check "the previous renders are untouched" diff -r -q "$W/fern-out-before" "$K/out"
  printf '{"stores": ["play", "ios"], "ios": {"supports_tablet": false}, "play": {"icon": "../../play-icon.png"},
 "slots": {"ios-6.3": {"need": "optional"}}}\n' > "$K/store-assets.json"
  runin "$F" "$RENDER" render store-assets/mockup-kit --all --no-contrast
  check "the kit's own store-assets.json comes first, and a need override applies" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'release with .*mockup-kit.store-assets.json' '$W/out'"
  rm "$K/store-assets.json"
  edit "$K/frames.json" 'cfg["sizes"] = ["play-phone", "ios-63", {"key": "ios-61", "size": "1179x2556", "platform": "ios", "folder": "ios/6.1"}]'
  runin "$F" "$RENDER" render store-assets/mockup-kit --all --no-contrast
  check "an undeclared project size fails the release gate" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'unknown-folder.*ios/6.1' '$W/out'"
  printf '{"stores": ["play", "ios"], "ios": {"supports_tablet": false}, "play": {"icon": "../play-icon.png"},
 "slots": {"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1179x2556"]}}}\n' > "$F/store-assets/store-assets.json"
  runin "$F" "$RENDER" render store-assets/mockup-kit --all --no-contrast
  check "declared in store-assets.json, the same set passes and is published" rc 0
  check "the 6.3 inch set is 1206x2622 RGB" test "$(dims "$K/out/ios/6.3/01-home.png")" == "1206x2622 RGB"
  check "the project size is 1179x2556 RGB" test "$(dims "$K/out/ios/6.1/01-home.png")" == "1179x2556 RGB"
  hc_py "$SK/store-submission-precheck/scripts/check_store_assets.py" "$K/out" --release --config "$F/store-assets/store-assets.json" > "$W/out" 2>&1
  check "the standalone release check agrees" test $? -eq 0
  rm -rf "$W/gate-copy"; cp -R "$K/out" "$W/gate-copy"; rm -rf "$W/gate-copy/ios/6.3"
  hc_py "$SK/store-submission-precheck/scripts/check_store_assets.py" "$W/gate-copy" --release --config "$F/store-assets/store-assets.json" --json > "$W/out" 2>&1
  check "without its 6.3 inch folder, ios-6.3 is a missing slot" grep -q '"slot": "ios-6.3"' "$W/out"
  rm "$F/store-assets/store-assets.json"
  edit "$K/frames.json" 'cfg["sizes"] = ["play-phone", "ios-69"]'

  echo "== format 2: drafts"
  G="$W/kes"; hc_py "$MAKE" "$G" kestrel > "$W/out" 2>&1
  GK="$G/store-assets/mockup-kit"
  before="$(tree_hash "$GK")"
  runin "$G" "$RENDER" render store-assets/mockup-kit --frames 01-home --sizes play-phone
  check "an unapproved production render is refused" rc 1
  runin "$G" "$RENDER" preview store-assets/mockup-kit --concept "brand/concepts/store/20261002-120000-0a0b0c/a.json" --out "$W/draft"
  check "a draft preview renders without approvals" rc 0
  check "it says DRAFT" has "DRAFT"
  check "it writes a contact sheet" test -f "$W/draft/contact-sheet.png"
  check "it wrote nothing into the kit" test "$before" == "$(tree_hash "$GK")"
  check "and nothing into the kit's out/ or .build/" test ! -e "$GK/out" -a ! -e "$GK/.build"
  check "and no run manifest" test ! -e "$G/brand/runs"
  runin "$G" "$RENDER" preview store-assets/mockup-kit --concept "brand/concepts/store/20261002-120000-0a0b0c/a.json" --out "$W/draft"
  check "a preview never overwrites a non-empty folder" rc 2

  echo "== format 2: every layout and feature-graphic preset renders"
  C="$G/brand/concepts/store/20261002-120000-0a0b0c/a.json"
  hc_py - "$C" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p, encoding="utf-8"))
c["spec"]["layouts"] = ["caption-top", "caption-bottom", "split-left", "split-right", "inset"]
json.dump(c, open(p, "w", encoding="utf-8"), indent=2)
PY
  edit "$GK/frames.json" '
L = ["caption-top", "caption-bottom", "split-left", "split-right", "inset"]
cfg["frames"] = [{"id": f"0{i + 1}-{l}", "screen": "home" if i % 2 == 0 else "activity", "head": f"Layout <em>{l}</em>", "sub": "Rendered by the test", "layout": l} for i, l in enumerate(L)]'
  for fgl in split-device-right split-device-left centered-type; do
    edit "$GK/frames.json" "cfg['featureGraphic']['layout'] = '$fgl'"
    runin "$G" "$RENDER" preview store-assets/mockup-kit --concept "brand/concepts/store/20261002-120000-0a0b0c/a.json" --sizes play-phone --out "$W/presets-$fgl"
    check "layouts + feature graphic $fgl render (draft)" bash -c "[[ \$(cat '$W/rc') == 0 && \$(ls '$W/presets-$fgl/play/phone' | wc -l) -eq 5 && -f '$W/presets-$fgl/play/feature_graphic_1024x500.png' ]]"
  done
  edit "$GK/frames.json" 'cfg["frames"][0]["head"] = "Supercalifragilisticexpialidociousnessesextraordinarilyunbreakable"'
  runin "$G" "$RENDER" preview store-assets/mockup-kit --concept "brand/concepts/store/20261002-120000-0a0b0c/a.json" --sizes play-phone --out "$W/clip"
  check "a caption that runs off the canvas is reported" has "runs off the canvas"
  edit "$GK/frames.json" 'cfg["frames"][0]["head"] = "Layout <em>caption-top</em>"'
  runin "$G" "$RENDER" preview store-assets/mockup-kit --concept "brand/concepts/store/20261002-120000-0a0b0c/a.json" --sizes play-tab10 --frames 01-caption-top --out "$W/tablet"
  check "a tablet aspect ratio renders" test -f "$W/tablet/play/tablet10/01-caption-top.png"

  echo "== export_svg.py with Chrome"
  printf '%s\n' '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024"><rect x="200" y="200" width="624" height="624" rx="120" fill="#2f6b5a"/></svg>' > "$W/proj/brand/mark.svg"
  cat > "$W/proj/brand/html/card.html" <<'HTML'
<!doctype html><html><head><style>body{margin:0;background:#173a31;font:600 40px sans-serif}
p{margin:40px}.ok{color:#ffffff}</style></head><body><p class="ok">Readable caption</p></body></html>
HTML
  sed 's/#ffffff/#24493f/' "$W/proj/brand/html/card.html" > "$W/proj/brand/html/faint.html"
  printf '%s\n' '{"exports": [' \
    '{"src": "mark.svg", "sizes": ["256x256", "128x128"], "out": "png"},' \
    '{"src": "html/card.html", "sizes": ["600x200"], "out": "social", "flatten": "#173a31"}]}' > "$W/proj/brand/exports.json"
  run "$EXPORT" --plan brand/exports.json
  check "a plan exports every entry" rc 0
  check "the plan writes each size" test -f "$W/proj/brand/png/mark-256x256.png" -a -f "$W/proj/brand/png/mark-128x128.png"
  check "flattened exports are RGB" hc_py -c "from PIL import Image; import sys; sys.exit(Image.open(sys.argv[1]).mode != 'RGB')" "$W/proj/brand/social/card-600x200.png"
  check "sampled HTML contrast is REVIEW REQUIRED" has "status REVIEW REQUIRED"
  run "$EXPORT" --plan brand/exports.json --only mark
  check "--only limits the plan" bash -c "grep -q 'from 1 source' '$W/out'"
  run "$EXPORT" brand/html/faint.html --size 600x200 --out brand/faint-out
  check "low-contrast HTML text fails" rc 1
  check "the faint text is named" has "Readable caption"
  check "a failed export writes nothing" test ! -e "$W/proj/brand/faint-out"
  run "$EXPORT" brand/html/faint.html --size 600x200 --out brand/faint-out --no-contrast
  check "--no-contrast skips the check" rc 0

  echo "== canvas entries (approved marketing concept)"
  runin "$F" "$EXPORT" --plan brand/exports.json
  check "an approved canvas exports" rc 0
  check "the Open Graph image is written where it is used" test -f "$F/web/public/og-image-1200x630.png"
  check "canvas contrast is computed" has "contrast: .* PASS, 0 FAIL"
  check "a marketing run manifest is written" bash -c "ls '$F'/brand/runs/marketing/*.json >/dev/null 2>&1"
  runin "$F" "$EXPORT" --plan brand/exports.json --preview "$W/og-draft"
  check "a canvas draft goes only to the preview folder" bash -c "[[ \$(cat '$W/rc') == 0 && -f '$W/og-draft/og-image-1200x630.png' ]]"
  MC="$F/brand/concepts/marketing/20261002-120000-0a0b0c/a.json"
  hc_py - "$MC" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p, encoding="utf-8"))
c["spec"]["backgrounds"]["soil"]["text"]["sub"] = "{color.moss.700}"
json.dump(c, open(p, "w", encoding="utf-8"), indent=2)
PY
  runin "$F" "$DIR" approve --gate concept --family marketing --concept "brand/concepts/marketing/20261002-120000-0a0b0c/a.json" --by Owner --evidence "test: approved a poor concept"
  cp "$F/web/public/og-image-1200x630.png" "$W/og-before.png"
  runin "$F" "$EXPORT" --plan brand/exports.json
  check "an approved but low-contrast canvas still fails in production" rc 1
  check "and the previous image is untouched" cmp -s "$W/og-before.png" "$F/web/public/og-image-1200x630.png"

  echo "== icons from the direction"
  glyph "$F/glyph.png"
  runin "$F" "$ICONS" generate --master glyph.png --from-direction . --out icons
  check "an approved icon concept generates" rc 0
  check "with its gradient background" grep -q 'backgroundImage' "$F/icons/expo-icon-snippet.json"
  check "and an icon run manifest" bash -c "ls '$F'/brand/runs/icon/*.json >/dev/null 2>&1"
fi

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "store render tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
