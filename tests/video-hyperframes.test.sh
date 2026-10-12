#!/usr/bin/env bash
# === brand-video with the HyperFrames engine (opt-in, needs Node 22 and the network) ===
# Renders the fixture's two-format loop with `render --engine hyperframes`: the pinned HyperFrames
# CLI draws the frames, our encoder and checks do the rest, and the parity signal compares its
# frames with ours. CI runs this in a separate job that may fail without failing the build (it
# downloads HyperFrames and its browser). Locally: HYPERFRAMES_BIN=<installed CLI> or npx.
# Usage: bash tests/video-hyperframes.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIDEO="$ROOT/harness/skills/brand-video/scripts/render_video.py"
DIR="$ROOT/harness/skills/creative-direction/scripts/direction.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
RUNID="20261002-120000-0a0b0c"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
command -v node >/dev/null 2>&1 || [[ -n "${HYPERFRAMES_NODE:-}" ]] || { echo "[SKIP] HyperFrames tests: no Node.js"; exit 0; }
W="$(mktemp -d "${TMPDIR:-/tmp}/video-hf.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()  { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad() { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 25 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
runin() { local dir="$1" rc; shift; ( cd "$dir" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
has() { grep -q -- "$1" "$W/out"; }
rc()  { [[ "$(cat "$W/rc")" == "$1" ]]; }
FF="${FFMPEG:-$(command -v ffmpeg || true)}"
if [[ -n "$FF" ]] && command -v cygpath >/dev/null 2>&1; then FF="$(cygpath -w "$FF")"; fi
unset FFMPEG
NODEARG=(); [[ -n "${HYPERFRAMES_NODE:-}" ]] && NODEARG=(--node "$HYPERFRAMES_NODE")

P="$W/fern"
hc_py "$MAKE" "$P" fernway --video > "$W/out" 2>&1; check "the fixture builds" test $? -eq 0
CON="brand/concepts/video/$RUNID/a.json"
runin "$P" "$DIR" approve --gate direction --by Owner --evidence "test approval"
runin "$P" "$DIR" approve --gate concept --family video --concept "$CON" --by Owner --evidence "picked a"
runin "$P" "$DIR" approve --gate storyboard --piece card --by Owner --evidence "watched the drafts"
runin "$P" "$VIDEO" render card --ffmpeg "$FF" --engine hyperframes "${NODEARG[@]}"
check "the loop renders with the HyperFrames engine" rc 0
for c in technical:og-card technical:social-1x1 gif:og-card webp:social-1x1; do
  check "render reports $c as PASS" has "PASS             $c"
done
check "the parity signal compares HyperFrames' frames with ours" has "engine-parity:og-card: mean difference per scene still frame"
RUN="$(ls -t "$P/brand/runs/video" | head -1)"
hc_py -c "
import json, sys
m = json.load(open(sys.argv[1], encoding='utf-8'))
assert m['engine']['renderer'] == 'hyperframes' and m['engine']['hyperframes'], m['engine']
" "$P/brand/runs/video/$RUN" > "$W/out" 2>&1
check "the manifest records the engine and its version" test $? -eq 0
echo "HyperFrames tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
