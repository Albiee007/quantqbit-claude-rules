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
