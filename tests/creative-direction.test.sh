#!/usr/bin/env bash
# === creative direction tests: direction, concepts, approvals and production gates ===
# direction.py (validate, status, approve, concept, signals, migrate) on fixture projects built by
# tests/fixtures/media/make_project.py, and the production gates of render_frames.py,
# export_svg.py and make_icon_set.py (refusals need no browser). Approvals must bind to the content
# and the resolved inputs: a change invalidates exactly the affected scope, an unchanged rerun
# passes, and nothing approves without owner evidence.
# Needs Python 3.9+ with Pillow (fixture and icon cases). Missing Pillow is a SKIP locally and a
# failure when CI=true.
# Usage: bash tests/creative-direction.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
SK="$ROOT/harness/skills"
DIR="$SK/creative-direction/scripts/direction.py"
RENDER="$SK/store-mockups/scripts/render_frames.py"
EXPORT="$SK/brand-assets/scripts/export_svg.py"
ICONS="$SK/app-icons/scripts/make_icon_set.py"
MAKE="$ROOT/tests/fixtures/media/make_project.py"
RUNID="20261002-120000-0a0b0c"
if ! hc_py -c 'import PIL' 2>/dev/null; then
  if [[ "${CI:-}" == "true" ]]; then echo "[FAIL] Pillow is required in CI (pip install pillow)"; exit 1; fi
  echo "[SKIP] creative direction tests: Pillow not installed (pip install pillow)"; exit 0
fi
W="$(mktemp -d "${TMPDIR:-/tmp}/creative-direction-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 12 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
run()   { local dir="$1" rc; shift; ( cd "$dir" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
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

echo "== fixtures"
hc_py "$MAKE" "$W/fern" fernway > "$W/out" 2>&1; check "fernway fixture builds (not approved)" test $? -eq 0
hc_py "$MAKE" "$W/kes" kestrel --approve > "$W/out" 2>&1; check "kestrel fixture builds (approved)" test $? -eq 0
hc_py "$MAKE" "$W/same" samebrand --approve > "$W/out" 2>&1; check "same-brand fixture builds (approved)" test $? -eq 0
F="$W/fern"; STORE="brand/concepts/store/$RUNID/a.json"; MKT="brand/concepts/marketing/$RUNID/a.json"; ICON="brand/concepts/icon/$RUNID/a.json"

echo "== validate"
run "$F" "$DIR" validate
check "a sound direction validates" rc 0
check "every concept is checked" has "store: Fernway store"
cp "$F/brand/direction.json" "$W/direction.bak"
jset "$F/brand/direction.json" 'd["surprise"] = 1'
run "$F" "$DIR" validate; check "an unknown key is refused" rc 1
cp "$W/direction.bak" "$F/brand/direction.json"
jset "$F/brand/direction.json" 'd["schemaVersion"] = 2'
run "$F" "$DIR" validate; check "an unknown schema version is refused" rc 1
cp "$W/direction.bak" "$F/brand/direction.json"
jset "$F/brand/direction.json" 'd["tokens"]["source"] = "../outside.json"'
run "$F" "$DIR" validate; check "a token source outside the project is refused" rc 1
cp "$W/direction.bak" "$F/brand/direction.json"
sed 's/"revision": 1/"revision": NaN/' "$W/direction.bak" > "$F/brand/direction.json"
run "$F" "$DIR" validate; check "a non-finite number is refused" rc 1
cp "$W/direction.bak" "$F/brand/direction.json"
jset "$F/brand/direction.json" 'd["tokens"]["roles"]["ink"] = "{color.nope.1}"'
run "$F" "$DIR" validate; check "an unresolved token reference is refused" rc 1
check "and named" has "color.nope.1"
cp "$W/direction.bak" "$F/brand/direction.json"

echo "== concepts"
cp "$F/$STORE" "$W/store.bak"
jset "$F/$STORE" 'd["spec"]["backgrounds"]["dawn"]["text"]["head"] = "#123456"'
run "$F" "$DIR" concept check "$STORE"; check "a literal hex in a concept is refused (token references only)" rc 1
cp "$W/store.bak" "$F/$STORE"
jset "$F/$STORE" 'd["spec"]["backgrounds"]["soil"]["text"]["head"] = "{color.moss.800}"'
run "$F" "$DIR" concept check "$STORE"; check "a low-contrast declared pair fails" rc 1
check "the failing pair is computed, not sampled" has "FAIL.*computed"
cp "$W/store.bak" "$F/$STORE"
mkdir -p "$F/brand/concepts/store/other"; cp "$F/$STORE" "$F/brand/concepts/store/other/a.json"
run "$F" "$DIR" concept check "brand/concepts/store/other/a.json"; check "a concept outside its run folder is refused" rc 1
check "and says where it must live" has "must live at"
rm -rf "$F/brand/concepts/store/other"
run "$F" "$DIR" concept new --family store --id b --name "Second" --run "$RUNID"
check "concept new writes a valid skeleton" rc 0
run "$F" "$DIR" concept new --family store --id b --name "Again" --run "$RUNID"
check "concepts are never overwritten" rc 2
rm -f "$F/brand/concepts/store/$RUNID/b.json"

echo "== gates and approvals"
run "$F" "$DIR" status; check "nothing is approved yet" rc 1
check "Gate 1 is reported" has "Gate 1 direction: NOT MET"
run "$F" "$DIR" approve --gate concept --family store --concept "$STORE" --by Owner --evidence "picked a"
check "a concept can't be approved before the direction" rc 1
run "$F" "$DIR" approve --gate direction --by Owner --evidence "  "
check "an approval without evidence is refused" rc 1
run "$F" "$DIR" approve --gate direction --by "Owner" --evidence "chat 2026-10-02: approved"
check "the owner approves the direction" rc 0
run "$F" "$DIR" approve --gate concept --family store --concept "$STORE" --by Owner --evidence "picked a"
run "$F" "$DIR" approve --gate concept --family marketing --concept "$MKT" --by Owner --evidence "picked a"
run "$F" "$DIR" approve --gate concept --family icon --concept "$ICON" --by Owner --evidence "picked a"
run "$F" "$DIR" status; check "all gates met" rc 0
check "the selection is recorded in the direction" grep -q "\"selected\": \"$STORE\"" "$F/brand/direction.json"
check "DIRECTION.md is regenerated with the approvals" grep -q "picked a" "$F/brand/DIRECTION.md"
jset "$F/$STORE" 'd["idea"] = "A changed idea for the store concept, after approval."'
run "$F" "$DIR" status
check "editing the store concept makes only its approval stale" bash -c "grep -q 'Gate 2 store: NOT MET.*stale: the concept file' '$W/out' && grep -q 'Gate 2 marketing: approved' '$W/out' && grep -q 'Gate 2 icon: approved' '$W/out'"
cp "$W/store.bak" "$F/$STORE"
run "$F" "$DIR" status; check "restoring it makes the approval current again (unchanged rerun)" rc 0
cp "$F/brand/direction.json" "$W/direction.approved"
jset "$F/brand/direction.json" 'd["summary"] = "A different summary."'
run "$F" "$DIR" status
check "editing the direction makes it and every concept chosen under it stale" bash -c "grep -q 'Gate 1 direction: NOT MET.*its content' '$W/out' && grep -q 'Gate 2 icon: NOT MET' '$W/out'"
cp "$W/direction.approved" "$F/brand/direction.json"
cp "$F/brand/tokens.json" "$W/tokens.bak"
jset "$F/brand/tokens.json" 'd["color"]["unused"] = {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0, 0, 0], "hex": "#000000"}}'
run "$F" "$DIR" status; check "adding an unrelated token changes nothing" rc 0
jset "$F/brand/tokens.json" 'd["color"]["moss"]["950"]["$value"]["components"][0] = 0.11; d["color"]["moss"]["950"]["$value"]["hex"] = "#1c1c1c"'
run "$F" "$DIR" status
check "changing a token the direction resolves makes it stale" has "a token, font or motif it resolves changed"
cp "$W/tokens.bak" "$F/brand/tokens.json"
FONT="$(ls "$F"/brand/fonts/* | head -1)"; cp "$FONT" "$W/font.bak"
printf 'x' >> "$FONT"
run "$F" "$DIR" status; check "a changed font file blocks the gates" rc 1
check "and names the file" has "changed since it was recorded"
cp "$W/font.bak" "$FONT"
run "$F" "$DIR" status; check "everything is current again" rc 0
cp "$F/brand/approvals.json" "$W/approvals.bak"
jset "$F/brand/approvals.json" 'd["records"].append(dict(d["records"][0]))'
run "$F" "$DIR" status; check "a hand-edited approvals file with a duplicate id is refused" rc 1
cp "$W/approvals.bak" "$F/brand/approvals.json"

echo "== production gates (no browser needed)"
G="$W/kes-draft"; hc_py "$MAKE" "$G" kestrel > "$W/out" 2>&1
run "$G" "$RENDER" render store-assets/mockup-kit --frames 01-home --sizes play-phone
check "a single-frame production render is refused without approvals" rc 1
check "the refusal names the missing approval" has "no owner approval"
run "$G" "$RENDER" render store-assets/mockup-kit --check-only
check "--check-only validates and reports the gate" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'gate: NOT MET' '$W/out'"
run "$G" "$EXPORT" --plan brand/exports.json
check "a canvas export is refused without approvals" rc 1
hc_py -c "
import sys
from PIL import Image, ImageDraw
im = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))
ImageDraw.Draw(im).ellipse((200, 200, 824, 824), fill=(255, 255, 255, 255))
im.save(sys.argv[1])" "$G/glyph.png"
run "$G" "$ICONS" generate --master glyph.png --from-direction . --out icons
check "icons from the direction are refused without approvals" rc 1
check "and nothing was written" test ! -e "$G/icons"
run "$G" "$ICONS" preview --master glyph.png --from-direction . --concept "$ICON" -o out/icon-preview.png
check "a draft icon preview works without approvals" rc 0
check "the preview writes only its sheet" bash -c "[[ -f '$G/out/icon-preview.png' && \$(ls '$G/out' | wc -l) -eq 1 ]]"
K="$W/kes"
jset "$K/store-assets/mockup-kit/frames.json" 'd["frames"][0]["layout"] = "split-left"'
run "$K" "$RENDER" render store-assets/mockup-kit --check-only
check "a frame layout outside the approved concept is refused" rc 1
check "the refusal prints the exception command" has 'approve --gate exception --scope "store:frame:01-home:layout=split-left"'
run "$K" "$DIR" approve --gate exception --scope "store:frame:01-home:layout=split-left" --by Owner --evidence "ok for frame 1"
run "$K" "$RENDER" render store-assets/mockup-kit --check-only
check "the owner's exception allows it" rc 0
jset "$K/store-assets/mockup-kit/frames.json" 'd["frames"][0]["head"] = "REPLACE: the promise"'
run "$K" "$RENDER" render store-assets/mockup-kit --check-only
check "placeholder copy fails a production check" bash -c "[[ \$(cat '$W/rc') == 1 ]] && grep -q 'placeholder copy' '$W/out'"

echo "== scoped approvals and the video family (1.8)"
V="$W/vid"; hc_py "$MAKE" "$V" kestrel --video --approve > "$W/out" 2>&1
check "a fixture with an approved video concept and storyboard builds" test $? -eq 0
run "$V" "$DIR" status; check "every gate is met, including Gate 3" bash -c "[[ \$(cat '$W/rc') == 0 ]] && grep -q 'Gate 3 storyboard launch: approved' '$W/out'"
check "new records carry hashVersion 2" grep -q '"hashVersion": 2' "$V/brand/approvals.json"
VD="$V/brand/direction.json"; cp "$VD" "$W/vdir.bak"; cp "$V/brand/tokens.json" "$W/vtok.bak"
gates() { grep -q "Gate 1 direction: approved" "$W/out" && for g in "$@"; do grep -q -- "$g" "$W/out" || return 1; done; }
jset "$VD" 'd["families"]["illustration"] = {"requested": True, "brief": "spot art for onboarding"}'
run "$V" "$DIR" status
check "requesting and briefing another family leaves every approval current" gates "Gate 2 store: approved" "Gate 2 video: approved" "Gate 3 storyboard launch: approved"
cp "$W/vdir.bak" "$VD"
jset "$VD" 'd["families"]["video"]["brief"] = "a 20-second teaser for the autumn release"'
run "$V" "$DIR" status
check "briefing the video family makes the video concept and storyboard stale, nothing else" bash -c "grep -q 'Gate 1 direction: approved' '$W/out' && grep -q 'Gate 2 store: approved' '$W/out' && grep -q 'Gate 2 icon: approved' '$W/out' && grep -q 'Gate 2 video: NOT MET.*stale' '$W/out' && grep -q 'Gate 3 storyboard launch: NOT MET' '$W/out'"
cp "$W/vdir.bak" "$VD"
jset "$VD" 'd["families"]["store"]["brief"] = "lead with the live map"'
run "$V" "$DIR" status
check "briefing the store family makes only the store concept stale" gates "Gate 2 store: NOT MET.*stale" "Gate 2 marketing: approved" "Gate 2 video: approved" "Gate 3 storyboard launch: approved"
cp "$W/vdir.bak" "$VD"
jset "$V/brand/tokens.json" 'd["motion"]["duration"]["base"]["$value"]["value"] = 333'
run "$V" "$DIR" status
check "a motion token change makes the video concept and storyboard stale, not the stills" gates "Gate 2 store: approved" "Gate 2 icon: approved" "Gate 2 video: NOT MET.*value it resolves" "Gate 3 storyboard launch: NOT MET"
cp "$W/vtok.bak" "$V/brand/tokens.json"
jset "$V/brand/tokens.json" 'd["color"]["signal"]["400"]["$value"]["components"][0] = 0.5; d["color"]["signal"]["400"]["$value"]["hex"] = "#80590c"'
run "$V" "$DIR" status
check "a role colour change makes the direction stale and the concepts that use it" bash -c "grep -q 'Gate 1 direction: NOT MET.*token, font or motif' '$W/out' && grep -q 'store concept approval.*stale' '$W/out' && grep -q 'video concept approval.*stale' '$W/out' && ! grep -q 'icon concept approval.*stale' '$W/out'"
cp "$W/vtok.bak" "$V/brand/tokens.json"
mkdir -p "$V/brand/video/promo"; sed 's/"id": "launch"/"id": "promo"/' "$V/brand/video/launch/video.json" > "$V/brand/video/promo/video.json"
run "$V" "$DIR" approve --gate storyboard --piece promo --by Owner --evidence "promo approved"
jset "$V/brand/video/promo/video.json" 'd["scenes"][0]["copy"]["head"] = "A different promise"'
run "$V" "$DIR" status
check "editing one piece leaves another piece's storyboard current" bash -c "grep -q 'Gate 3 storyboard launch: approved' '$W/out' && grep -q 'Gate 3 storyboard promo: NOT MET.*on-screen content' '$W/out'"
rm -rf "$V/brand/video/promo"
run "$V" "$DIR" status; check "the unchanged rerun is current again" rc 0
run "$V" "$DIR" approve --gate review --run 20261002-120000-0a0b0c --items all --by Owner --evidence "ok"
check "a review acknowledgement needs an existing run" rc 1
hc_py -c "
import sys; sys.path.insert(0, sys.argv[1])
from harnesslib import schema
old = {'schemaVersion': 1, 'runId': '20261002-120000-0a0b0c', 'family': 'store', 'mode': 'production', 'tool': 'render_frames.py',
       'startedAt': 'x', 'finishedAt': 'y', 'engine': {'api': 1}, 'inputs': {'config': '0' * 64}, 'approvals': [], 'fonts': [],
       'seed': None, 'outputs': [{'path': 'a.png', 'sha256': '0' * 64, 'bytes': 1, 'size': [1, 1]}], 'checks': {}, 'status': 'complete'}
schema.check(old, 'run-manifest', '1.7 manifest')
" "$ROOT/harness/lib" > "$W/out" 2>&1
check "a 1.7 run manifest still validates" test $? -eq 0

LEGACY_REF="${LEGACY_REF:-cd14423}"  # 1.7.0 on main
if git -C "$ROOT" cat-file -e "$LEGACY_REF^{commit}" 2>/dev/null; then
  mkdir -p "$W/h17" && git -C "$ROOT" archive "$LEGACY_REF" harness tests/fixtures/media | tar -x -C "$W/h17"
  O="$W/old17"; hc_py "$W/h17/tests/fixtures/media/make_project.py" "$O" kestrel --approve > "$W/out" 2>&1
  check "a project approved by the 1.7 harness builds" test $? -eq 0
  check "its records have no hashVersion" bash -c "! grep -q hashVersion '$O/brand/approvals.json'"
  run "$O" "$DIR" status
  check "1.7 approvals stay current under 1.8" rc 0
  check "status notes the 1.7 hashing" has "1.7 hashing"
  cp "$O/brand/direction.json" "$W/odir.bak"
  jset "$O/brand/direction.json" 'd["families"]["video"] = {"requested": True, "brief": "a launch teaser"}'
  run "$O" "$DIR" status
  check "requesting video keeps every 1.7 approval current (the adapter)" gates "Gate 2 store: approved" "Gate 2 marketing: approved" "Gate 2 icon: approved" "Gate 2 video: NOT MET"
  cp "$W/odir.bak" "$O/brand/direction.json"
  jset "$O/brand/direction.json" 'd["families"]["store"]["brief"] = "lead with the live map"'
  run "$O" "$DIR" status
  check "the 1.7 coupling stays for 1.7 records: a store brief makes the direction stale" has "Gate 1 direction: NOT MET"
  run "$O" "$DIR" approve --gate direction --by Owner --evidence "re-approved under 1.8"
  for f in store marketing icon; do run "$O" "$DIR" approve --gate concept --family "$f" --concept "brand/concepts/$f/$RUNID/a.json" --by Owner --evidence "re-approved"; done
  jset "$O/brand/direction.json" 'd["families"]["store"]["brief"] = "lead with the live map, at night"'
  run "$O" "$DIR" status
  check "after re-approval the hashes are scoped: only the store concept goes stale" gates "Gate 2 store: NOT MET.*stale" "Gate 2 marketing: approved" "Gate 2 icon: approved"
elif [[ "${CI:-}" == "true" ]]; then
  bad "the 1.7 reference commit $LEGACY_REF is missing (CI checks out full history)"
else
  echo "  [SKIP] 1.7 adapter cases: commit $LEGACY_REF not in this clone"
fi

echo "== signals, migrate, same brand"
run "$W/same" "$DIR" concept check "$STORE"
check "a kept 1.6-like look still passes its checks" rc 0
check "and its signals are shown for discussion" has "harness:inter-800-tight"
run "$W/same" "$DIR" status; check "the same-brand project is approved and current" rc 0
mkdir -p "$W/legacy"; cp -R "$ROOT/tests/fixtures/legacy-1.6/classic" "$W/legacy/kit"
printf '<html><style>:root { --bg1: #2a1bb0; }</style><p>{{ONE_LINE_BENEFIT}}</p></html>\n' > "$W/legacy/og-image.html"
run "$W/legacy" "$DIR" migrate
check "migrate lists the 1.6 kit" has "kit/frames.json: a 1.6 mockup kit"
check "migrate lists the copied 1.6 template" has "og-image.html: a copy of the 1.6 Open Graph template"
check "migrate changes nothing" bash -c "grep -q 'nothing was changed' '$W/out' && cmp -s '$W/legacy/kit/frames.json' '$ROOT/tests/fixtures/legacy-1.6/classic/frames.json'"

check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "creative direction tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
