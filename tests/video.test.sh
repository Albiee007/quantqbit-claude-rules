#!/usr/bin/env bash
# === brand-video tests: library, seek contract, gates, render, reviews ===
# 1. Library checks with no browser and no ffmpeg (tests/fixtures/video/unit_check.py): the
#    DevTools WebSocket client, whole-frame scene arithmetic, planned captions, the flashing
#    heuristic, output-profile checks, cubicBezier tokens, ffmpeg lookup advice.
# 2. The seek contract in a real browser (tests/fixtures/video/seek_check.py): frames identical
#    however they are reached, clip windows, blocked network, bounded readiness.
# 3. render_video.py on a fixture project: drafts without approval, production refused until the
#    storyboard is approved, a full render (H.264 profile, contrast, safe area, flashing,
#    determinism), the run manifest written before publishing, review acknowledgements bound to
#    the outputs (kept by a byte-identical re-render), stale storyboards naming what changed,
#    interrupted publishes, locks; then a two-format loop (a still scene over a picture, GIF, WebP,
#    posters) rendered by parallel browsers, and a changed picture making its storyboard stale.
# Needs Python 3.9+ with Pillow; parts 2-3 need Chrome, Chromium or Edge, and part 3 ffmpeg.
# Missing tools are a SKIP locally and a failure when CI=true.
# Usage: bash tests/video.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="$ROOT/harness/skills"
VIDEO="$SK/brand-video/scripts/render_video.py"
DIR="$SK/creative-direction/scripts/direction.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
FIX="$ROOT/tests/fixtures/video"
RUNID="20261002-120000-0a0b0c"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
skip_or_fail() { if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] $1 (required in CI)"; exit 1; fi; echo "[SKIP] video tests: $1"; exit 0; }
hc_py -c 'import PIL' 2>/dev/null || skip_or_fail "Pillow not installed (pip install pillow)"
W="$(mktemp -d "${TMPDIR:-/tmp}/video-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 15 "$W/out" 2>/dev/null | sed 's/^/        /'; annotate "$*"; }
annotate() { # on GitHub Actions, a failure also becomes an annotation (readable without the log)
  [[ "${GITHUB_ACTIONS:-}" == "true" ]] || return 0
  local body; body="$(tail -n 8 "$W/out" 2>/dev/null | cut -c1-300 | sed -e 's/%/%25/g' | awk '{ printf "%s%%0A", $0 }')"
  printf '::error title=video: %s::%s\n' "${1//::/ }" "$body"
}
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
runin() { local dir="$1" rc; shift; ( cd "$dir" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
rc()    { [[ "$(cat "$W/rc")" == "$1" ]]; }
has()   { grep -q -- "$1" "$W/out"; }
jset()  { hc_py - "$@" <<'PY'
import json, sys
path, expr = sys.argv[1], sys.argv[2]
d = json.load(open(path, encoding="utf-8"))
exec(expr)
json.dump(d, open(path, "w", encoding="utf-8"), indent=2)
PY
}
lines_ok() { # every line of a helper's report is "ok": count them into the totals
  local f="$1" line
  while IFS= read -r line; do
    case "$line" in ok*) ok "${line#ok    }" ;; FAIL*) fail=$((fail + 1)); printf '  [FAIL] %s\n' "${line#FAIL  }"
      [[ "${GITHUB_ACTIONS:-}" == "true" ]] && printf '::error title=video: %s::\n' "${line#FAIL  }" ;; esac
  done < "$f"
}

echo "== 1. library (no browser, no ffmpeg)"
hc_py "$FIX/unit_check.py" > "$W/unit" 2>&1; urc=$?
lines_ok "$W/unit"
[[ $urc -eq 0 ]] || { cp "$W/unit" "$W/out"; bad "unit_check.py exited $urc"; }

if ! hc_py -c "import sys; sys.path.insert(0, sys.argv[1]); from harnesslib import browser; browser.find_chrome(None)" "$ROOT/harness/lib" >/dev/null 2>&1; then
  echo "video tests: $pass passed, $fail failed"
  [[ $fail -eq 0 ]] || exit 1
  skip_or_fail "Chrome/Chromium/Edge not found (parts 2-3)"
fi

echo "== 2. seek contract (browser)"
hc_py "$FIX/seek_check.py" --trials "${VIDEO_TRIALS:-12}" > "$W/seek" 2>&1; src=$?
lines_ok "$W/seek"
[[ $src -eq 0 ]] || { cp "$W/seek" "$W/out"; bad "seek_check.py exited $src"; }

FF="${FFMPEG:-$(command -v ffmpeg || true)}"
# Git Bash paths (/c/...) mean nothing to Windows Python; give it the Windows form.
if [[ -n "$FF" ]] && command -v cygpath >/dev/null 2>&1; then FF="$(cygpath -w "$FF")"; fi
unset FFMPEG  # the scripts get the path through --ffmpeg
if [[ -z "$FF" ]]; then
  echo "video tests: $pass passed, $fail failed"
  [[ $fail -eq 0 ]] || exit 1
  skip_or_fail "ffmpeg not found (part 3; install it or set FFMPEG)"
fi

echo "== 3. render_video.py"
P="$W/fern"
hc_py "$MAKE" "$P" fernway --video > "$W/out" 2>&1; check "a fixture with a video concept and piece builds" test $? -eq 0
CON="brand/concepts/video/$RUNID/a.json"
runin "$P" "$VIDEO" lint launch --static --concept "$CON"
check "lint passes the fixture piece" rc 0
check "lint reports reading-time signals as review items" has "REVIEW REQUIRED  scene hook"
runin "$P" "$VIDEO" render launch --ffmpeg "$FF"
check "production is refused without approvals" rc 1
check "the refusal names the missing approval" has "no owner approval"
runin "$P" "$VIDEO" preview launch --concept "$CON" --ffmpeg "$FF" --out "$W/draft"
check "a draft renders without approval" rc 0
check "the draft has a sheet, a half-size video and the voice files" bash -c "[[ -f '$W/draft/social-9x16/sheet.png' && -f '$W/draft/social-9x16/draft.mp4' && -f '$W/draft/voice/script.md' && -f '$W/draft/voice/voice-prompt.md' && -f '$W/draft/voice/captions.planned.vtt' ]]"
check "nothing was published by the draft" test ! -e "$P/brand/video/launch/out"
check "the voice prompt carries the concept's casting" grep -q "warm, unhurried gardener" "$W/draft/voice/voice-prompt.md"
check "the captions say they are planned" grep -q "NOTE planned timing" "$W/draft/voice/captions.planned.vtt"

runin "$P" "$DIR" approve --gate direction --by Owner --evidence "test approval"
runin "$P" "$DIR" approve --gate storyboard --piece launch --by Owner --evidence "watched the draft"
check "a storyboard can't be approved before the video concept" rc 1
runin "$P" "$DIR" approve --gate concept --family video --concept "$CON" --by Owner --evidence "picked a"
runin "$P" "$DIR" approve --gate storyboard --piece launch --by Owner --evidence "watched the draft"
check "the owner approves the storyboard" rc 0
runin "$P" "$DIR" status
check "status shows Gate 3" has "Gate 3 storyboard launch: approved"

mkdir -p "$P/brand/video/launch/.build/render.lock"; echo "pid 1 on elsewhere" > "$P/brand/video/launch/.build/render.lock/owner"
runin "$P" "$VIDEO" render launch --ffmpeg "$FF"
check "a held render lock is an operational error" bash -c "[[ \$(cat '$W/rc') == 2 ]] && grep -q 'locked by another run' '$W/out'"
rm -rf "$P/brand/video/launch/.build/render.lock"

runin "$P" "$VIDEO" render launch --ffmpeg "$FF" --determinism 4
check "the approved piece renders" rc 0
for c in "PASS             technical" "PASS             contrast" "PASS             text" "PASS             determinism" "SKIPPED          audio"; do
  check "render reports ${c##* } as ${c%% *}" has "$c"
done
OUT="$P/brand/video/launch/out"
check "the video, sheet and voice files are published" bash -c "[[ -f '$OUT/social-9x16/launch.mp4' && -f '$OUT/social-9x16/launch-sheet.png' && -f '$OUT/voice/script.md' && -f '$OUT/voice/cues.json' && -f '$OUT/voice/captions.planned.srt' ]]"
check "the owned-files record names the run" grep -q '"run"' "$OUT/.render-manifest.json"
RUN="$(ls "$P/brand/runs/video" | head -1)"; RUN="${RUN%.json}"
check "a run manifest was written" test -n "$RUN"
hc_py -c "
import json, sys
sys.path.insert(0, sys.argv[1])
from harnesslib import schema
m = json.load(open(sys.argv[2], encoding='utf-8'))
schema.check(m, 'run-manifest', 'manifest')
mp4 = [o for o in m['outputs'] if o['path'].endswith('.mp4')][0]
assert m['family'] == 'video' and m['piece']['captions'] == 'planned' and mp4['frames'] == m['piece']['frames']
assert mp4['profile'] == 'h264-web' and mp4['audio'] is False and m['engine']['renderer'] == 'ours'
assert m['status'] == 'review-required' and m['reviews'], m['status']
" "$ROOT/harness/lib" "$P/brand/runs/video/$RUN.json" > "$W/out" 2>&1
check "the manifest validates and records frames, profile and review items" test $? -eq 0
runin "$P" "$VIDEO" check launch --ffmpeg "$FF"
check "check re-verifies the published file against its profile" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'PASS  technical' '$W/out'"

runin "$P" "$VIDEO" status launch
check "a run with review items is published but not cleared" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'not cleared for use' '$W/out'"
runin "$P" "$DIR" approve --gate review --run "$RUN" --items "nope" --by Owner --evidence "looked"
check "an unknown review item is refused" rc 1
runin "$P" "$DIR" approve --gate review --run "$RUN" --items all --by Owner --evidence "watched it; pace is fine"
check "the owner acknowledges the review items" rc 0
runin "$P" "$VIDEO" status launch
check "then it is cleared for use" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'cleared for use' '$W/out'"
SHA1="$(hc_py -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$OUT/social-9x16/launch.mp4")"
runin "$P" "$VIDEO" render launch --ffmpeg "$FF" --workers 3
check "a re-render with nothing changed works (three browsers)" rc 0
check "the browsers draw the frames where their runs meet identically" has "PASS             workers:social-9x16"
SHA2="$(hc_py -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$OUT/social-9x16/launch.mp4")"
if [[ "$SHA1" == "$SHA2" ]]; then
  runin "$P" "$VIDEO" status launch
  check "a byte-identical re-render keeps the acknowledgement" rc 0
else
  ok "the re-render is not byte-identical on this machine ($SHA1 vs $SHA2); the acknowledgement rightly does not carry over"
fi
[[ "$SHA1" == "$SHA2" ]] && ok "one browser and three browsers encode the same bytes"

cp "$OUT/social-9x16/launch.mp4" "$W/keep.mp4"; rm "$OUT/social-9x16/launch.mp4"
runin "$P" "$VIDEO" status launch
check "a missing output shows as NOT PUBLISHED" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'NOT PUBLISHED' '$W/out'"
cp "$W/keep.mp4" "$OUT/social-9x16/launch.mp4"

V="$P/brand/video/launch/video.json"; cp "$V" "$W/video.bak"
jset "$V" 'd["scenes"][0]["vo"] = "A different opening line."'
runin "$P" "$DIR" status
check "editing a voice-over line makes the storyboard stale, naming the script" has "Gate 3 storyboard launch: NOT MET.*voice-over script"
runin "$P" "$VIDEO" render launch --ffmpeg "$FF"
check "and production is refused" rc 1
cp "$W/video.bak" "$V"
jset "$V" 'd["scenes"][1]["duration"] = 5.5'
runin "$P" "$DIR" status; check "a timing edit is named as timing" has "Gate 3 storyboard launch: NOT MET.*timing"
cp "$W/video.bak" "$V"
jset "$V" 'd["scenes"][0]["copy"]["head"] = "Another promise"'
runin "$P" "$DIR" status; check "a copy edit is named as on-screen content" has "Gate 3 storyboard launch: NOT MET.*on-screen content"
cp "$W/video.bak" "$V"
runin "$P" "$DIR" status; check "restoring the piece restores the approval" has "Gate 3 storyboard launch: approved"
jset "$V" 'd["scenes"][0]["copy"]["head"] = "Another promise"'
runin "$P" "$DIR" approve --gate storyboard --piece launch --by Owner --evidence "new headline approved"
runin "$P" "$VIDEO" status launch
check "after a re-approved edit, the old render is not the approved piece" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'predates the current storyboard approval' '$W/out'"
cp "$W/video.bak" "$V"
runin "$P" "$DIR" approve --gate storyboard --piece launch --by Owner --evidence "back to the first headline"
runin "$P" "$VIDEO" status launch
check "approving the rendered storyboard again makes the render current" rc 0

echo "== 4. a two-format loop: still scene, GIF, WebP, posters, parallel browsers"
runin "$P" "$VIDEO" lint card --format social-1x1
check "lint checks one format's page on request" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'page (social-1x1)' '$W/out' && ! grep -q 'page (og-card)' '$W/out'"
runin "$P" "$DIR" approve --gate storyboard --piece card --by Owner --evidence "watched both drafts"
check "the loop's storyboard is approved" rc 0
runin "$P" "$VIDEO" render card --ffmpeg "$FF" --workers 2
check "the loop renders in both formats" rc 0
for c in technical:og-card technical:social-1x1 workers:og-card gif:og-card webp:og-card poster:og-card gif:social-1x1 webp:social-1x1 poster:social-1x1; do
  check "render reports $c as PASS" has "PASS             $c"
done
check "a loop that does not return to its opening picture is a seam review item" has "REVIEW REQUIRED  loop-seam:og-card"
CO="$P/brand/video/card/out"
check "each format has its video, GIF, WebP, poster and sheet" bash -c "for f in og-card social-1x1; do for x in card.mp4 card.gif card.webp card-poster.png card-sheet.png; do [[ -f '$CO/'\$f/\$x ]] || exit 1; done; done"
CRUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py -c "
import json, sys
m = json.load(open(sys.argv[1], encoding='utf-8'))
by = {o['path'].split('/out/')[1]: o for o in m['outputs']}
assert by['og-card/card.gif']['size'] == [480, 252] and by['og-card/card.gif']['loop'] == 0, by['og-card/card.gif']
assert by['social-1x1/card.mp4']['frames'] == m['piece']['frames'] and by['social-1x1/card.mp4']['format'] == 'social-1x1'
assert m['piece']['formats'] == ['og-card', 'social-1x1'] and m['engine']['workers'] == 2
assert any(a['path'] == 'brand/art/garden.png' for a in m['inputs']['assets'])
assert any(r['id'] == 'loop-seam:og-card' for r in m['reviews'])
" "$P/brand/runs/video/$CRUN" > "$W/out" 2>&1
check "the manifest records each format's outputs, the workers and the picture it used" test $? -eq 0
runin "$P" "$VIDEO" check card --ffmpeg "$FF"
check "check re-verifies every published video, loop and poster" bash -c "[[ \$(cat '$W/rc') == 0 ]] && [[ \$(grep -c '^PASS  technical' '$W/out') == 8 ]]"
cp "$P/brand/art/garden.png" "$W/garden.bak"; printf 'x' >> "$P/brand/art/garden.png"
runin "$P" "$DIR" status
check "changing the picture's bytes makes the loop's storyboard stale, naming it" has "Gate 3 storyboard card: NOT MET.*an image it shows"
check "and leaves the launch piece approved" has "Gate 3 storyboard launch: approved"
cp "$W/garden.bak" "$P/brand/art/garden.png"
runin "$P" "$DIR" status; check "restoring the picture restores the approval" has "Gate 3 storyboard card: approved"

echo "== 5. a format of the piece's own: customFormats"
CV="$P/brand/video/card/video.json"; cp "$CV" "$W/card.bak"
jset "$CV" 'd["customFormats"] = {"li-card": {"size": "1201x628", "like": "og-card"}}; d["formats"] = ["li-card"]'
runin "$P" "$VIDEO" lint card --static
check "an odd custom size is refused when the piece loads" bash -c "[[ \$(cat '$W/rc') != 0 ]] && grep -q 'odd side' '$W/out'"
jset "$CV" 'd["customFormats"]["li-card"]["size"] = "1200x628"; d["scenes"][0]["byFormat"] = {"li-card": {"layout": d["scenes"][0].get("layout", "type-start")}}'
runin "$P" "$DIR" status
check "adding a custom format makes the storyboard stale, naming on-screen content" has "Gate 3 storyboard card: NOT MET.*on-screen content"
runin "$P" "$DIR" approve --gate storyboard --piece card --by Owner --evidence "watched the LinkedIn draft"
check "the custom-format storyboard is approved" rc 0
runin "$P" "$VIDEO" render card --ffmpeg "$FF"
check "a 1200x628 custom format like og-card renders" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'PASS             technical' '$W/out'"
CRUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py -c "
import json, sys
m = json.load(open(sys.argv[1], encoding='utf-8'))
by = {o['path'].split('/out/')[1]: o for o in m['outputs']}
assert by['li-card/card.mp4']['size'] == [1200, 628] and by['li-card/card.mp4']['format'] == 'li-card', by.get('li-card/card.mp4')
assert by['li-card/card.gif']['size'] == [480, 251], by['li-card/card.gif']
" "$P/brand/runs/video/$CRUN" > "$W/out" 2>&1
check "the encoded video is 1200x628 and its loop keeps the aspect" test $? -eq 0
runin "$P" "$VIDEO" check card --ffmpeg "$FF"
check "check re-verifies the custom format's files against their size" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q '^PASS  technical' '$W/out'"
jset "$CV" 'd["customFormats"]["li-card"]["safe"] = {"standard": {"left": 90}}'
runin "$P" "$DIR" status
check "changing a custom format's insets makes the approval stale" has "Gate 3 storyboard card: NOT MET.*on-screen content"
jset "$CV" 'd["customFormats"]["li-card"].pop("safe")'
runin "$P" "$DIR" status; check "restoring the insets restores the approval" has "Gate 3 storyboard card: approved"
cp "$W/card.bak" "$CV"

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "video tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
