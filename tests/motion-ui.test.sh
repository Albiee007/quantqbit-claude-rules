#!/usr/bin/env bash
# === motion-ui tests: library, capture lanes, reference analysis, gates, verify, reviews ===
# 1. Library checks with no browser and no ffmpeg (tests/fixtures/motion/unit_check.py): schema and
#    viewports, which edits touch Gate 3, WCAG 2.2.2 automatic-motion rules, lint, review hashes,
#    build fingerprints, cut/hold/loop signals, flash labels, harness.config.
# 2. Capture lanes in a real browser (tests/fixtures/motion/motion_check.py): virtual clock and
#    app seek deterministic in fresh browsers, reduced motion, blocked network, a real pause button
#    passes and a label-only one fails, a really hidden tab, every browser stopped.
# 3. Reference analysis (ffmpeg): a synthetic reference made here (A, B, A again; and a variable
#    frame rate copy): probe, frames named by time, sheets, cuts, loop length, review records.
# 4. motion.py on a fixture project: lint and SPEC.md, verify refused before Gate 3, drafts,
#    approval, a complete verify run published with its manifest, review acknowledgement kept by
#    an identical re-verify, which edits make which word stale (approved, verified, reviewed), an
#    incomplete run (no ffmpeg) not published and not reviewable, --timeout stopping every process.
# Needs Python 3.9+ with Pillow; parts 2-4 need Chrome, Chromium or Edge, parts 3-4 ffmpeg.
# Missing tools are a SKIP locally and a failure when CI=true.
# Usage: bash tests/motion-ui.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SK="$ROOT/harness/skills"
MOTION="$SK/motion-ui/scripts/motion.py"
DIR="$SK/creative-direction/scripts/direction.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
FIX="$ROOT/tests/fixtures/motion"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
unset MOTION_BASE_URL
skip_or_fail() { if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] $1 (required in CI)"; exit 1; fi; echo "[SKIP] motion-ui tests: $1"; exit 0; }
hc_py -c 'import PIL' 2>/dev/null || skip_or_fail "Pillow not installed (pip install pillow)"
PYX="$(hc_python)"  # for the bash -c checks below
W="$(mktemp -d "${TMPDIR:-/tmp}/motion-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 15 "$W/out" 2>/dev/null | sed 's/^/        /'; annotate "$*"; }
annotate() {
  [[ "${GITHUB_ACTIONS:-}" == "true" ]] || return 0
  local body; body="$(tail -n 8 "$W/out" 2>/dev/null | cut -c1-300 | sed -e 's/%/%25/g' | awk '{ printf "%s%%0A", $0 }')"
  printf '::error title=motion-ui: %s::%s\n' "${1//::/ }" "$body"
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
jget()  { hc_py -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); print(eval(sys.argv[2]))" "$@"; }
lines_ok() {
  local f="$1" line
  while IFS= read -r line; do
    case "$line" in ok*) ok "${line#ok    }" ;; FAIL*) fail=$((fail + 1)); printf '  [FAIL] %s\n' "${line#FAIL  }"
      [[ "${GITHUB_ACTIONS:-}" == "true" ]] && printf '::error title=motion-ui check failed::%s\n' "${line#FAIL  }" ;; esac  # a message, not only a title: GitHub drops empty ones
  done < "$f"
}
finish() { echo "motion-ui tests: $pass passed, $fail failed"; [[ $fail -eq 0 ]] || exit 1; }

echo "== 1. library (no browser, no ffmpeg)"
hc_py "$FIX/unit_check.py" > "$W/unit" 2>&1; urc=$?
lines_ok "$W/unit"
[[ $urc -eq 0 ]] || { cp "$W/unit" "$W/out"; bad "unit_check.py exited $urc"; }

if ! hc_py -c "import sys; sys.path.insert(0, sys.argv[1]); from harnesslib import browser; browser.find_chrome(None)" "$ROOT/harness/lib" >/dev/null 2>&1; then
  finish; skip_or_fail "Chrome/Chromium/Edge not found (parts 2-4)"
fi

echo "== 2. capture lanes (browser)"
hc_py "$FIX/motion_check.py" > "$W/lanes" 2>&1; lrc=$?
lines_ok "$W/lanes"
[[ $lrc -eq 0 ]] || { cp "$W/lanes" "$W/out"; bad "motion_check.py exited $lrc"; }

FF="${FFMPEG:-$(command -v ffmpeg || true)}"
if [[ -n "$FF" ]] && command -v cygpath >/dev/null 2>&1; then FF="$(cygpath -w "$FF")"; fi
unset FFMPEG
if [[ -z "$FF" ]]; then finish; skip_or_fail "ffmpeg not found (parts 3-4; install it or set FFMPEG)"; fi

echo "== 3. reference analysis"
P="$W/proj"
hc_py "$MAKE" "$P" fernway --approve --motion > "$W/out" 2>&1; check "a fixture with a motion concept and piece builds" test $? -eq 0
mkdir -p "$W/media"
# A (testsrc2) 1 s, B (smptebars) 1 s, A again 1 s: two cuts, and the picture repeats after 2 s.
"$FF" -v error -y -f lavfi -i "testsrc2=s=320x180:r=30:d=1" -f lavfi -i "smptebars=s=320x180:r=30:d=1" \
  -filter_complex "[0]split[a][c];[a][1][c]concat=n=3:v=1:a=0,format=yuv420p" -c:v libx264 -preset veryfast "$W/media/ref.mp4" > "$W/out" 2>&1
check "a synthetic reference is made with ffmpeg" test -s "$W/media/ref.mp4"
# The same with frames 40-44 dropped and their timestamps kept: a variable frame rate.
"$FF" -v error -y -i "$W/media/ref.mp4" -vf "select='not(between(n,40,44))'" -fps_mode vfr -c:v libx264 -preset veryfast "$W/media/vfr.mp4" > "$W/out" 2>&1
runin "$P" "$MOTION" init ref --reference "$W/media/ref.mp4"
check "init copies the reference into the piece's ignored reference/ folder" bash -c "rc() { [[ \$(cat '$W/rc') == 0 ]]; }; rc && [[ -f '$P/brand/motion/ref/reference/ref.mp4' && -f '$P/brand/motion/ref/reference/.gitignore' ]]"
runin "$P" "$MOTION" probe ref --record --ffmpeg "$FF"
check "probe reads 90 frames at 30/1, constant rate" bash -c "grep -q '90 frames' '$W/out' && grep -q '30/1 (constant)' '$W/out'"
check "probe --record writes the reference hash into the piece" bash -c "[[ \$(cd '$P' && $PYX -c \"import json;print(len(json.load(open('brand/motion/ref/motion.json'))['reference']['sha256']))\") == 64 ]]"
runin "$P" "$MOTION" cuts ref --ffmpeg "$FF"
check "cuts finds the cut at 1000 ms" has "cut   at    1000.0 ms"
check "cuts finds the cut at 2000 ms" has "cut   at    2000.0 ms"
check "no cut inside the moving test pattern" bash -c "[[ \$(grep -c 'cut   at' '$W/out') -eq 2 ]]"
check "the loop candidate is 2000 ms" bash -c "grep -m1 'loop?' '$W/out' | grep -q 'after 2000 ms'"
runin "$P" "$MOTION" frames ref --every 500 --ffmpeg "$FF"
check "frames --every 500 writes 6 frames named by time" bash -c "[[ \$(ls '$P/brand/motion/ref/.build/analysis/frames' | wc -l) -eq 6 ]] && ls '$P/brand/motion/ref/.build/analysis/frames' | grep -q 'f000015-0000500.0ms.png'"
runin "$P" "$MOTION" sheet ref --ffmpeg "$FF"
check "sheet writes labelled sheets and coverage" bash -c "[[ -f '$P/brand/motion/ref/.build/analysis/sheets/sheet-01.png' && -f '$P/brand/motion/ref/.build/analysis/sheets/coverage.json' ]]"
check "the sheet says it is not a review" has "record what you actually reviewed"
runin "$P" "$MOTION" inspect ref --range 0-1000 --mode every-frame --by Tester
check "inspect refuses every-frame over sampled frames" rc 1
runin "$P" "$MOTION" inspect ref --range 0-1000 --mode sampled --by Tester --note "first scene"
check "inspect records a sampled review of presented frames" rc 0
runin "$P" "$MOTION" inspect ref --range 0-9000 --mode sampled --by Tester
check "inspect refuses a range that was never presented" rc 1
runin "$P" "$MOTION" frames ref --all --ffmpeg "$FF"
check "frames --all writes every decoded frame" bash -c "[[ \$(ls '$P/brand/motion/ref/.build/analysis/frames' | wc -l) -eq 90 ]]"
runin "$P" "$MOTION" sheet ref --ffmpeg "$FF"
runin "$P" "$MOTION" inspect ref --range 900-1100 --mode every-frame --by Tester --note "the cut"
check "inspect records an every-frame review once every frame was presented" rc 0
check "the piece holds extracted, presented and reviewed separately" bash -c "cd '$P' && $PYX -c \"
import json; a=json.load(open('brand/motion/ref/motion.json'))['analysis']
assert len(a['extracted'])==2 and len(a['presented'])==2 and len(a['reviewed'])==2, a
assert a['reviewed'][1]['mode']=='every-frame' and a['presented'][1]['mode']=='all'\""
runin "$P" "$MOTION" probe ref --file "$W/media/vfr.mp4" --ffmpeg "$FF"
check "a variable frame rate is flagged" has "VFR"
check "the VFR copy has 85 frames" has "85 frames"
runin "$P" "$MOTION" cuts ref --file "$W/media/vfr.mp4" --ffmpeg "$FF"
check "VFR: cuts still land at 1000 and 2000 ms (timestamps, not index / fps)" bash -c "grep -q 'cut   at    1000.0 ms' '$W/out' && grep -q 'cut   at    2000.0 ms' '$W/out'"

echo "== 4. motion.py on the fixture project"
runin "$P" "$MOTION" lint hero
check "lint passes the fixture piece" rc 0
check "lint names the driver's ceiling" has "capture: web (complete)"
runin "$P" "$MOTION" lint ref
check "lint fails a starter piece that still says REPLACE" bash -c "rc() { [[ \$(cat '$W/rc') == 1 ]]; }; rc && grep -q 'still says REPLACE' '$W/out'"
runin "$P" "$MOTION" spec hero
check "spec writes SPEC.md for the owner" bash -c "grep -q 'Motion spec: Home hero' '$P/brand/motion/hero/SPEC.md' && grep -q 'approve --gate storyboard --family motion --piece hero' '$P/brand/motion/hero/SPEC.md'"
runin "$P" "$MOTION" verify hero --ffmpeg "$FF"
check "verify is refused before Gate 3" rc 1
check "the refusal names the missing approval" has "no owner approval"
runin "$P" "$MOTION" capture hero --draft --ffmpeg "$FF"
check "a draft capture runs without approval" rc 0
check "the draft has captures and sheets per viewport" bash -c "ls '$P'/brand/motion/hero/.preview/*/captures/desktop/t0.png '$P'/brand/motion/hero/.preview/*/sheets/mobile.png >/dev/null 2>&1"
check "nothing was published by the draft" test ! -e "$P/brand/motion/hero/out"
runin "$P" "$DIR" approve --gate storyboard --piece hero --by "Fixture Owner" --evidence "test approval"
check "approve without --family points at the motion piece" bash -c "rc() { [[ \$(cat '$W/rc') == 2 ]]; }; rc && grep -q 'add --family motion' '$W/out'"
runin "$P" "$DIR" approve --gate concept,storyboard --family motion --concept "brand/concepts/motion/20261002-120000-0a0b0c/a.json" --piece hero --by "Fixture Owner" --evidence "test approval"
check "the owner's spec approval is recorded (chained with the concept at one checkpoint)" rc 0
runin "$P" "$DIR" status
check "direction.py status shows Gate 3 for the motion spec" has "Gate 3 motion spec hero: approved"
export MOTION_PID_LOG="$W/pids.log"
runin "$P" "$MOTION" verify hero --ffmpeg "$FF"
check "verify runs once the spec is approved" rc 0
check "the run is complete and published" has "published to brand/motion/hero/out"
check "the pause control passes in real time" has "PASS             control"
check "reduced motion is static" has "PASS             reduced-motion"
check "the invisible focusable link is a review item" has "hidden-focus"
RUN1="$(ls "$P/brand/runs/motion" | head -n1)"; RUN1="${RUN1%.json}"
M1="$P/brand/runs/motion/$RUN1.json"
check "the manifest records completeness, build, target and capture settings" bash -c "[[ \$(cd '$P' && $PYX -c \"
import json; m=json.load(open('brand/runs/motion/$RUN1.json'))
print(m['completeness'], m['build']['kind'], m['target']['kind'], m['captureConfig']['driver'], m['family'])\") == 'complete content file web motion' ]]"
check "the recording is marked as evidence" bash -c "grep -q '\"kind\": \"evidence\"' '$M1'"
check "compare is omitted without a reference" bash -c "grep -q 'no reference: nothing to compare with' '$M1'"
check "published captures exist" test -f "$P/brand/motion/hero/out/captures/desktop/t0.png"
check "every process verify started was stopped" bash -c "$PYX - '$W/pids.log' <<'PY'
import subprocess, sys
starts = [l.split()[1] for l in open(sys.argv[1]) if l.startswith('start')]
stops = {l.split()[1] for l in open(sys.argv[1]) if l.startswith('stop')}
assert starts and set(starts) <= stops, (starts, stops)
for pid in starts:
    if sys.platform == 'win32':
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
        assert pid not in out, pid
    else:
        import os
        try:
            os.kill(int(pid), 0)
            raise SystemExit(f'{pid} alive')
        except ProcessLookupError:
            pass
PY"
runin "$P" "$MOTION" status hero
check "status: approved and verified, not yet reviewed" bash -c "grep -q 'approved (Gate 3): yes' '$W/out' && grep -q 'verified: yes' '$W/out' && grep -q 'reviewed: NO: 1 review item' '$W/out'"
runin "$P" "$DIR" approve --gate review --run "$RUN1" --items all --by "Fixture Owner" --evidence "looked at the captures"
check "the owner's review is recorded" rc 0
runin "$P" "$MOTION" status hero
check "status: reviewed" has "reviewed: yes"
runin "$P" "$MOTION" verify hero --ffmpeg "$FF"
check "an identical re-verify keeps the acknowledgement" has "the owner already acknowledged"
# capture settings and analysis notes are not the approved intent
jset "$P/brand/motion/hero/motion.json" "d['capture']['ready']['timeoutMs'] = 25000; d['analysis']['observations'].append({'ms': 0, 'text': 'a note'})"
runin "$P" "$MOTION" status hero
check "editing capture.ready and analysis keeps Gate 3" has "approved (Gate 3): yes"
jset "$P/brand/motion/hero/motion.json" "d['capture']['ready']['timeoutMs'] = 30000; d['analysis']['observations'].pop()"
cp "$P/brand/motion/hero/motion.json" "$W/hero.json"
jset "$P/brand/motion/hero/motion.json" "d['rows'][0]['action'] = 'a faster push in'"
runin "$P" "$MOTION" status hero
check "a row edit makes Gate 3 stale, naming timing" has "stale: timing changed"
cp "$W/hero.json" "$P/brand/motion/hero/motion.json"
# the app's code changes between captured times: motion.json is untouched, the review is not
cp "$P/web/hero.html" "$W/hero.html"
sed -e 's/q.has(.moved.) \&\& i === 1 ? 160 : 60/i === 1 ? 160 : 60/' "$W/hero.html" > "$P/web/hero.html"
check "the fixture's motion code was changed" bash -c "! cmp -s '$W/hero.html' '$P/web/hero.html'"
runin "$P" "$MOTION" status hero
check "changed code: Gate 3 still approved" has "approved (Gate 3): yes"
check "changed code: no longer verified (build fingerprint)" has "build fingerprint differs"
check "changed code: no longer reviewed" has "reviewed: NO"
runin "$P" "$MOTION" verify hero --ffmpeg "$FF"
check "a re-verify of the changed code needs a new look" has "not reviewed yet"
cp "$W/hero.html" "$P/web/hero.html"
# an asset's bytes bind at review, not at Gate 3
mkdir -p "$P/web/img"; printf 'one' > "$P/web/img/poster.txt"
jset "$P/brand/motion/hero/motion.json" "d['assets'] = [{'id': 'poster', 'role': 'poster', 'origin': 'project', 'path': 'web/img/poster.txt'}]; d['resilience']['fallback'] = 'poster'"
runin "$P" "$MOTION" status hero
check "adding an asset to the plan makes Gate 3 stale (the asset plan)" has "the asset plan"
cp "$W/hero.json" "$P/brand/motion/hero/motion.json"
# incomplete: no ffmpeg means no recording
export CI=false
runin "$P" "$MOTION" verify hero --ffmpeg "$W/no/ffmpeg"
check "without ffmpeg the run is incomplete, not published" bash -c "grep -q 'NOT published (incomplete)' '$W/out' && grep -q 'MISSING  recording' '$W/out'"
check "an incomplete run exits 0 locally" rc 0
RUN3="$(ls -t "$P/brand/runs/motion" | head -n1)"; RUN3="${RUN3%.json}"
check "the incomplete run keeps its outputs in .preview" test -d "$P/brand/motion/hero/.preview/$RUN3/captures"
runin "$P" "$DIR" approve --gate review --run "$RUN3" --items all --by "Fixture Owner" --evidence "tried"
check "an incomplete run can't be reviewed" bash -c "rc() { [[ \$(cat '$W/rc') == 1 ]]; }; rc && grep -q 'incomplete' '$W/out'"
export CI=true
runin "$P" "$MOTION" verify hero --ffmpeg "$W/no/ffmpeg"
check "an incomplete run fails under CI=true" rc 1
unset CI
runin "$P" "$MOTION" status hero
check "status reports the incomplete last run" has "the last run is incomplete"
# --timeout stops everything it started
: > "$W/pids.log"
runin "$P" "$MOTION" verify hero --ffmpeg "$FF" --timeout 4
check "--timeout stops the run (exit 2)" bash -c "rc() { [[ \$(cat '$W/rc') == 2 ]]; }; rc && grep -q 'stopped' '$W/out'"
check "after a timeout every started browser is stopped" bash -c "$PYX - '$W/pids.log' <<'PY'
import subprocess, sys
starts = [l.split()[1] for l in open(sys.argv[1]) if l.startswith('start')]
stops = {l.split()[1] for l in open(sys.argv[1]) if l.startswith('stop')}
assert set(starts) <= stops, (starts, stops)
for pid in starts:
    if sys.platform == 'win32':
        assert pid not in subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True, text=True).stdout
PY"
check "a timed-out run leaves no staging folder" bash -c "! ls -d '$P'/brand/motion/hero/.build/motion-verify-* >/dev/null 2>&1"
unset MOTION_PID_LOG
runin "$P" "$MOTION" clean hero
check "clean removes .build and .preview, keeps out/" bash -c "[[ ! -e '$P/brand/motion/hero/.build' && ! -e '$P/brand/motion/hero/.preview' && -d '$P/brand/motion/hero/out' ]]"
runin "$P" "$DIR" status
check "every earlier approval is still current with the motion family requested" bash -c "! grep -q 'stale' '$W/out' && grep -q 'Gate 2 store: approved' '$W/out' && grep -q 'Gate 2 motion: approved' '$W/out'"

finish
