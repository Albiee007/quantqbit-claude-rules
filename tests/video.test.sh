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
#    Then an App Store preview of a screen recording with recorded voice and music (the mix gate,
#    loudness, segment-aligned captions) and a transparent overlay (VP9 alpha).
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
check "a picture the 1:1 push-in has to enlarge is a resolution review item" has "REVIEW REQUIRED  scene art (social-1x1): brand/art/garden.png is 1600x1000"
check "and the og-card, which it covers at full size, is not" bash -c "! grep -q 'scene art (og-card)' '$W/out'"
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
assert any(r['id'] == 'resolution:art:social-1x1' for r in m['reviews'])
assert not any(r['id'] == 'resolution:art:og-card' for r in m['reviews'])
" "$P/brand/runs/video/$CRUN" > "$W/out" 2>&1
check "the manifest records each format's outputs, the workers and the picture it used" test $? -eq 0
runin "$P" "$VIDEO" check card --ffmpeg "$FF"
check "check re-verifies every published video, loop and poster" bash -c "[[ \$(cat '$W/rc') == 0 ]] && [[ \$(grep -c '^PASS  technical' '$W/out') == 8 ]]"
cp "$P/brand/art/garden.png" "$W/garden.bak"; printf 'x' >> "$P/brand/art/garden.png"
runin "$P" "$DIR" status
check "changing the picture's bytes makes the loop's storyboard stale, naming it" has "Gate 3 storyboard card: NOT MET.*a picture or recording it shows"
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

echo "== 6. an App Store preview with recorded voice and music, and a transparent overlay"
hc_py "$FIX/m3_media.py" "$P" "$FF" > "$W/out" 2>&1; check "the recording, takes and music are generated" test $? -eq 0
runin "$P" "$VIDEO" lint preview
check "the preview lints, a graphics scene being a suitability item" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'REVIEW REQUIRED  app-preview-iphone: App Store previews should show footage' '$W/out'"
runin "$P" "$VIDEO" preview preview --ffmpeg "$FF" --out "$W/apdraft"
check "the draft has the draft mix and segment-aligned captions" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'with the draft mix' '$W/out' && grep -q 'NOTE segment-aligned' '$W/apdraft/voice/captions.vtt'"
runin "$P" "$DIR" approve --gate mix --piece preview --by Owner --evidence "listened"
check "a mix can't be approved before its storyboard" rc 1
runin "$P" "$DIR" approve --gate storyboard --piece preview --by Owner --evidence "watched the draft"
runin "$P" "$VIDEO" render preview --ffmpeg "$FF"
check "production with audio needs the mix approval" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'approve --gate mix --piece preview' '$W/out'"
runin "$P" "$DIR" approve --gate mix --piece preview --by Owner --evidence "listened to the draft"
check "the owner approves the mix" rc 0
runin "$P" "$DIR" status
check "status shows the mix gate" has "Gate 3 mix preview: approved"
runin "$P" "$VIDEO" render preview --ffmpeg "$FF" --workers 2
check "the App Store preview renders" rc 0
for c in technical:app-preview-iphone audio:app-preview-iphone workers:app-preview-iphone voice-over; do
  check "render reports $c as PASS" has "PASS             $c"
done
AO="$P/brand/video/preview/out"
check "segment-aligned captions are published as captions.srt/vtt" bash -c "[[ -f '$AO/voice/captions.srt' && -f '$AO/voice/captions.vtt' && ! -f '$AO/voice/captions.planned.srt' ]]"
ARUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py -c "
import json, sys
m = json.load(open(sys.argv[1], encoding='utf-8'))
mp4 = [o for o in m['outputs'] if o['path'].endswith('.mp4')][0]
assert mp4['audio'] is True and mp4['profile'] == 'app-preview', mp4
assert m['piece']['captions'] == 'segment-aligned'
paths = {a['path'] for a in m['inputs']['assets']}
assert {'brand/video/preview/media/flow.mp4', 'brand/video/preview/media/music.wav', 'brand/video/preview/media/vo/flow.wav'} <= paths, paths
assert any(r['id'] == 'suitability:app-store:app-preview-iphone' for r in m['reviews'])
" "$P/brand/runs/video/$ARUN" > "$W/out" 2>&1
check "the manifest records the sound, the recording, the takes and the suitability item" test $? -eq 0
runin "$P" "$VIDEO" check preview --ffmpeg "$FF"
check "check re-verifies the preview with its sound track" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'PASS  technical (app-preview)' '$W/out'"
MU="$P/brand/video/preview/media/music.wav"; cp "$MU" "$W/music.bak"; printf 'x' >> "$MU"
runin "$P" "$DIR" status
check "changing the music makes only the mix stale" bash -c "grep -q 'Gate 3 mix preview: NOT MET.*the audio' '$W/out' && grep -q 'Gate 3 storyboard preview: approved' '$W/out'"
cp "$W/music.bak" "$MU"
PV="$P/brand/video/preview/video.json"; cp "$PV" "$W/preview.bak"
jset "$PV" 'd["scenes"][1]["vo"] = "Try Fernway this week."'
runin "$P" "$DIR" status
check "editing a voice-over line makes the storyboard and the mix stale" bash -c "grep -q 'Gate 3 storyboard preview: NOT MET.*voice-over script' '$W/out' && grep -q 'Gate 3 mix preview: NOT MET' '$W/out'"
cp "$W/preview.bak" "$PV"
runin "$P" "$DIR" status; check "restoring both restores both approvals" bash -c "grep -q 'Gate 3 storyboard preview: approved' '$W/out' && grep -q 'Gate 3 mix preview: approved' '$W/out'"

runin "$P" "$DIR" approve --gate storyboard --piece lower --by Owner --evidence "watched the overlay"
runin "$P" "$VIDEO" render lower --ffmpeg "$FF"
check "the transparent overlay renders" rc 0
check "it is VP9 with alpha in WebM" bash -c "grep -q 'PASS             technical:overlay: VP9 with alpha' '$W/out' && [[ -f '$P/brand/video/lower/out/overlay/lower.webm' ]]"
check "its contrast is a review item (the footage under it is unknown)" has "REVIEW REQUIRED  contrast:overlay"

echo "== 7. custom scenes: a GSAP-style timeline and a Lottie-style player, seeked frame by frame"
hc_py "$FIX/m4_media.py" "$P" > "$W/out" 2>&1; check "the custom scenes and test libraries are written" test $? -eq 0
runin "$P" "$VIDEO" lint unruly --static
check "a scene script with a timer is refused" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q \"tick.js:3: 'setTimeout' is a timer\" '$W/out'"
runin "$P" "$VIDEO" lint motion
check "the custom scenes lint, their players counted" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'page (social-1x1): 4 animations' '$W/out'"
runin "$P" "$DIR" approve --gate storyboard --piece motion --by Owner --evidence "watched the draft"
runin "$P" "$VIDEO" render motion --ffmpeg "$FF" --workers 2 --determinism 4
check "the custom scenes render" rc 0
for c in technical:social-1x1 determinism:social-1x1 workers:social-1x1; do
  check "render reports $c as PASS" has "PASS             $c"
done
hc_py - "$P/brand/video/motion/out/social-1x1/motion.mp4" "$FF" > "$W/out" 2>&1 <<'PY'
import subprocess, sys
f, ff = sys.argv[1], sys.argv[2]
def frame(n):
    return subprocess.run([ff, "-v", "error", "-i", f, "-vf", f"select=eq(n\\,{n}),scale=64:64,format=gray", "-frames:v", "1",
                           "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
def diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)
assert diff(frame(8), frame(50)) > 0.3, "the timeline did not move the dot"
assert diff(frame(95), frame(130)) > 0.3, "the Lottie-style player did not move"
assert diff(frame(150), frame(160)) < 0.05, "the end of the badge scene should hold still"
PY
check "the timeline and the player move the frames they own, and hold after" test $? -eq 0
cp "$P/brand/video/motion/scenes/orbit.js" "$W/orbit.bak"; echo "// a comment" >> "$P/brand/video/motion/scenes/orbit.js"
runin "$P" "$DIR" status
check "editing a scene script makes the storyboard stale" has "Gate 3 storyboard motion: NOT MET.*a picture or recording it shows"
cp "$W/orbit.bak" "$P/brand/video/motion/scenes/orbit.js"

echo "== 7b. custom.assets: a layered scene composing project images, one as a CSS background"
runin "$P" "$VIDEO" lint layers
check "a custom scene with assets lints" rc 0
runin "$P" "$DIR" approve --gate storyboard --piece layers --by Owner --evidence "watched the draft"
runin "$P" "$VIDEO" render layers --ffmpeg "$FF"
check "the layered scene renders" rc 0
LRUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py - "$P/brand/runs/video/$LRUN" "$P/brand/video/layers/out/social-1x1/layers.mp4" "$FF" > "$W/out" 2>&1 <<'PY'
import json, subprocess, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
paths = {a["path"] for a in m["inputs"]["assets"]}
assert {"brand/art/layers/plate.png", "brand/art/layers/figure.png"} <= paths, paths
px = subprocess.run([sys.argv[3], "-v", "error", "-i", sys.argv[2], "-vf", "select=eq(n\\,0),scale=1:1", "-frames:v", "1",
                     "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
assert px[0] > 150 and px[1] < 90 and px[2] < 90, f"the CSS-background plate is not in the first frame: {tuple(px)}"
PY
check "the manifest lists both assets, and the background plate is drawn from the first frame" test $? -eq 0
cp "$P/brand/art/layers/plate.png" "$W/plate.bak"
hc_py -c "from PIL import Image; import sys; Image.new('RGB', (1200, 1200), (40, 160, 60)).save(sys.argv[1])" "$P/brand/art/layers/plate.png"
runin "$P" "$DIR" status
check "repainting an asset makes the storyboard stale" has "Gate 3 storyboard layers: NOT MET.*a picture or recording it shows"
cp "$W/plate.bak" "$P/brand/art/layers/plate.png"
runin "$P" "$DIR" status; check "restoring the asset restores the approval" has "Gate 3 storyboard layers: approved"

echo "== 8. providers: voice, alignment and b-roll from the project's own commands"
hc_py "$FIX/m4_talk.py" "$P" > "$W/out" 2>&1
runin "$P" "$VIDEO" generate talk --what tts
check "without providers.json, generate says where to declare them" bash -c "[[ \$(cat '$W/rc') == 2 ]] && grep -q 'providers.json not found' '$W/out'"
hc_py "$FIX/m4_talk.py" "$P" --providers > "$W/out" 2>&1
( unset FAKE_TTS_KEY; runin "$P" "$VIDEO" generate talk --what tts )
check "a provider without its key in the environment is refused" bash -c "[[ \$(cat '$W/rc') == 2 ]] && grep -q 'needs FAKE_TTS_KEY in the environment' '$W/out'"
export FAKE_TTS_KEY=test-only
runin "$P" "$VIDEO" generate talk --what tts
check "the TTS provider writes a take per line" bash -c "[[ \$(cat '$W/rc') == 0 && -f '$P/brand/video/talk/media/vo/intro.wav' && -f '$P/brand/video/talk/media/vo/end.wav' ]]"
runin "$P" "$VIDEO" generate talk --what tts
check "takes that exist are kept without --force" has "kept intro"
runin "$P" "$VIDEO" generate talk --what align
check "the aligner writes word timings" test -f "$P/brand/video/talk/media/vo/intro.words.json"
runin "$P" "$VIDEO" generate talk --what broll
check "the b-roll provider writes the scene's picture" test -f "$P/brand/video/talk/media/broll/intro.png"
check "provenance records every generated file, never the key" bash -c "grep -q 'fake image model' '$P/brand/video/talk/media/provenance.json' && ! grep -rq 'test-only' '$P/brand'"
unset FAKE_TTS_KEY
runin "$P" "$DIR" approve --gate storyboard --piece talk --by Owner --evidence "watched the draft"
runin "$P" "$DIR" approve --gate mix --piece talk --by Owner --evidence "listened"
runin "$P" "$VIDEO" render talk --ffmpeg "$FF"
check "the explainer renders with generated voice and b-roll" rc 0
check "generated voice is an AI-disclosure review item" has "REVIEW REQUIRED  2 voice take(s) were generated (fake TTS (tests))"
check "generated b-roll is one too" has "REVIEW REQUIRED  scene intro shows brand/video/talk/media/broll/intro.png, generated by"
check "captions follow the aligned words" grep -q "NOTE word-aligned" "$P/brand/video/talk/out/voice/captions.vtt"
TRUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py -c "
import json, sys
m = json.load(open(sys.argv[1], encoding='utf-8'))
assert m['piece']['captions'] == 'word-aligned', m['piece']
kinds = sorted(g['kind'] for g in m['generated'])
assert kinds == ['broll', 'tts', 'tts'], kinds
assert {'disclosure:ai-voice', 'disclosure:ai-media:intro'} <= {r['id'] for r in m['reviews']}
" "$P/brand/runs/video/$TRUN" > "$W/out" 2>&1
check "the manifest lists the generated files and the disclosure items" test $? -eq 0

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "video tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
