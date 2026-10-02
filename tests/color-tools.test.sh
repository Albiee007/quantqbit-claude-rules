#!/usr/bin/env bash
# === colour, token, type and schema tool tests (stdlib Python only) ===
# harness/lib/harnesslib (color, dtcg, typescale, schema, fsutil) and the CLIs palette.py and
# type_scale.py: reference vectors, precision boundaries (ratios compared unrounded, printed
# truncated), gamut mapping, DTCG aliases and diagnostics, non-destructive merges, platform output,
# strict JSON and safe paths, and the import bootstrap in the installed layout.
# Usage: bash tests/color-tools.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/harness/bin/harness-lib.sh"
export PYTHONDONTWRITEBYTECODE=1
PALETTE="$ROOT/harness/skills/color-science/scripts/palette.py"
TYPE="$ROOT/harness/skills/typography/scripts/type_scale.py"
W="$(mktemp -d "${TMPDIR:-/tmp}/color-tools-test.XXXXXX")"
trap 'rm -rf "$W"' EXIT
pass=0; fail=0
ok()    { pass=$((pass + 1)); printf '  [OK] %s\n' "$*"; }
bad()   { fail=$((fail + 1)); printf '  [FAIL] %s\n' "$*"; tail -n 12 "$W/out" 2>/dev/null | sed 's/^/        /'; }
check() { local d="$1"; shift; if "$@"; then ok "$d"; else bad "$d"; fi; }
run()   { local rc; ( cd "$W" && hc_py "$@" ) > "$W/out" 2>&1; rc=$?; echo "$rc" > "$W/rc"; return 0; }
rc()    { [[ "$(cat "$W/rc")" == "$1" ]]; }
has()   { grep -q -- "$1" "$W/out"; }

echo "== library unit checks"
hc_py - "$ROOT/harness/lib" > "$W/out" 2>&1 <<'PY'
import math, sys
sys.path.insert(0, sys.argv[1])
from harnesslib import color as c, dtcg, typescale as ts, schema
from harnesslib.fsutil import InputError, loads_json, safe_rel, canonical, script_json
fails = []
def expect(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)
W = c.parse("#ffffff")
# WCAG vectors: full precision against the threshold, truncated for display only
r = c.contrast_ratio(c.parse("#767676"), W)
expect("#767676 on white is 4.54 and passes 4.5", c.display_ratio(r) == "4.54" and r >= 4.5)
r = c.contrast_ratio(c.parse("#777777"), W)
expect("#777777 on white is 4.47 and fails 4.5", c.display_ratio(r) == "4.47" and r < 4.5)
expect("truncation never rounds up (4.4999 -> 4.49)", c.display_ratio(4.4999) == "4.49")
expect("a failing ratio never prints as the threshold", c.display_ratio(4.5 - 1e-15, 4.5) == "4.49" and c.display_ratio(4.49999, 4.5) == "4.49")
expect("black on white is 21", abs(c.contrast_ratio(c.parse("#000"), W) - 21.0) < 1e-12)
expect("contrast is symmetric", c.contrast_ratio(W, c.parse("#3366cc")) == c.contrast_ratio(c.parse("#3366cc"), W))
# 3:1 boundary for large text and non-text
expect("large text = 24px, or 18.67px bold", c.is_large_text(24, 400) and c.is_large_text(18.67, 700) and not c.is_large_text(18.67, 600) and not c.is_large_text(23.9, 400))
# alpha compositing (gamma space, as browsers do)
comp = c.composite((0, 0, 0, 0.5), (1, 1, 1))
expect("50% black over white composites to mid grey", all(abs(v - 0.5) < 1e-12 for v in comp))
# OKLab reference vectors (Ottosson)
L, a, b = c.srgb_to_oklab((1, 0, 0))
expect("sRGB red in OKLab", abs(L - 0.627955) < 1e-4 and abs(a - 0.224863) < 1e-4 and abs(b - 0.125846) < 1e-4)
L, a, b = c.srgb_to_oklab((1, 1, 1))
expect("white has L 1 and no chroma", abs(L - 1) < 1e-4 and math.hypot(a, b) < 1e-4)
expect("grey is achromatic (hue none)", c.oklab_to_oklch(c.srgb_to_oklab((0.5, 0.5, 0.5)))[2] is None)
expect("hue wraps into [0, 360)", 0 <= c.oklab_to_oklch((0.5, 0.1, -0.0001))[2] < 360)
rt = c.oklab_to_srgb(c.srgb_to_oklab((0.2, 0.4, 0.6)))
expect("sRGB -> OKLab -> sRGB round trip", all(abs(x - y) < 1e-6 for x, y in zip(rt, (0.2, 0.4, 0.6))))
# gamut mapping
raw = c.oklab_to_srgb(c.oklch_to_oklab((0.7, 0.35, 150)))
mapped = c.gamut_map_oklch((0.7, 0.35, 150))
expect("an out-of-gamut OKLCH colour is detected", not c.in_gamut(raw))
expect("gamut mapping lands in sRGB and keeps lightness", c.in_gamut(mapped) and abs(c.srgb_to_oklab(mapped)[0] - 0.7) < 0.02)
expect("L >= 1 maps to white, L <= 0 to black", c.gamut_map_oklch((1.2, 0.1, 30)) == (1, 1, 1) and c.gamut_map_oklch((-0.1, 0.1, 30)) == (0, 0, 0))
# parsing
expect("rgb() with alpha parses", c.parse("rgb(255 0 0 / 50%)")[3] == 0.5 and c.parse("rgba(0, 0, 255, 0.25)")[3] == 0.25)
try:
    c.parse("rgb(1 2 3 / 2)"); expect("alpha above 1 is rejected", False)
except c.ColorError:
    expect("alpha above 1 is rejected", True)
# gradients: interpolation space is stated
mid_ok = c.interpolate([c.parse("#0000ff"), c.parse("#ffff00")], 0.5, "oklab")
mid_rgb = c.interpolate([c.parse("#0000ff"), c.parse("#ffff00")], 0.5, "srgb")
expect("OKLab and sRGB gradients differ at the midpoint", c.delta_e_ok(c.srgb_to_oklab(mid_ok), c.srgb_to_oklab(mid_rgb)) > 0.02)

# DTCG
doc = {"color": {"$type": "color",
        "base": {"$value": {"colorSpace": "srgb", "components": [0.2, 0.4, 0.6], "hex": "#336699"}},
        "alias": {"$value": "{color.base}"},
        "legacy": {"$value": "#ff0000"},
        "$extensions": {"vendor.x": {"keep": True}}},
       "size": {"body": {"$type": "dimension", "$value": {"value": 16, "unit": "px"}}},
       "font": {"display": {"$type": "fontFamily", "$value": ["Fraunces", "serif"]}},
       "type": {"h1": {"$type": "typography", "$value": {"fontFamily": "{font.display}", "fontSize": "{size.body}", "fontWeight": "bold"}}},
       "other": {"shadow": {"$type": "shadow", "$value": {"x": 1}}}}
t = dtcg.Tokens(doc)
expect("aliases resolve through groups with inherited $type", t.resolve("{color.alias}").value["hex"] == "#336699")
expect("typography composites resolve their aliases", t.resolve("type.h1").value["fontWeight"] == 700)
expect("a legacy string colour resolves with a warning", t.resolve("color.legacy").warnings != [])
expect("foreign types are kept and not checked", t.check_all() == [])
for name, bad in [("cycle", {"a": {"$type": "color", "$value": "{b}"}, "b": {"$type": "color", "$value": "{a}"}}),
                  ("missing", {"a": {"$type": "color", "$value": "{nope}"}}),
                  ("type mismatch", {"a": {"$type": "color", "$value": "{d}"}, "d": {"$type": "dimension", "$value": {"value": 1, "unit": "px"}}}),
                  ("bad unit", {"d": {"$type": "dimension", "$value": {"value": 1, "unit": "em"}}}),
                  ("out of gamut without hex", {"x": {"$type": "color", "$value": {"colorSpace": "oklch", "components": [0.7, 0.35, 150]}}})]:
    errs = dtcg.Tokens(bad).check_all()
    expect(f"diagnoses {name}", bool(errs) and (name != "cycle" or all("cycle" in e for e in errs)))
for name, bad in [("$ref", {"a": {"$ref": "#/b"}}), ("$extends", {"g": {"$extends": "{x}", "a": {"$type": "number", "$value": 1}}})]:
    try:
        dtcg.Tokens(bad); expect(f"rejects {name} explicitly", False)
    except dtcg.TokenError:
        expect(f"rejects {name} explicitly", True)
deep = {f"t{i}": {"$type": "number", "$value": f"{{t{i + 1}}}"} for i in range(40)}
deep["t40"] = {"$type": "number", "$value": 1}
expect("alias depth is bounded", any("deeper" in e for e in dtcg.Tokens(deep).check_all()))
# merge: non-destructive, keeps metadata, conflicts need --replace
add = {"color": {"base": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [1, 0, 0], "hex": "#ff0000"}},
                 "new": {"$type": "color", "$value": {"colorSpace": "srgb", "components": [0, 1, 0], "hex": "#00ff00"}}}}
merged, changes = dtcg.merge(doc, add)
kinds = {ch.path: ch.kind for ch in changes}
expect("merge adds new tokens and reports a conflict", kinds == {"color.base": "conflict", "color.new": "add"})
expect("a conflict leaves the old value", merged["color"]["base"]["$value"]["hex"] == "#336699")
expect("merge keeps foreign extensions", merged["color"]["$extensions"] == {"vendor.x": {"keep": True}})
merged, changes = dtcg.merge(doc, add, {"color.base"})
expect("--replace changes only the named token", merged["color"]["base"]["$value"]["hex"] == "#ff0000")

# type scale and platform output
s = ts.modular(16, 1.25, ["caption", "body", "h2", "h1"], "body")
expect("modular scale around the body step", abs(s["h1"] - 25) < 1e-9 and abs(s["caption"] - 12.8) < 1e-9)
cl = ts.fluid_clamp(16, 20, 360, 1440)
expect("fluid clamp keeps a rem term", cl.startswith("clamp(1rem, ") and "rem + " in cl and cl.endswith("1.25rem)"))
expect("platform adapters", ts.platform_value(20, "android") == "20sp" and ts.platform_value(20, "ios") == 20.0 and ts.platform_value(20, "web") == "1.25rem")
expect("media px for a 320 px display of a 1080 canvas", abs(ts.media_px(24, 1080, 320) - 81) < 1e-9)

# strict JSON and paths
for name, text in [("duplicate keys", '{"a": 1, "a": 2}'), ("NaN", '{"a": NaN}'), ("Infinity", '{"a": Infinity}')]:
    try:
        loads_json(text); expect(f"strict JSON rejects {name}", False)
    except InputError:
        expect(f"strict JSON rejects {name}", True)
for p in ["/etc/x", "C:/x", "../x", "a/../../x", "a\\b", "~/x"]:
    try:
        safe_rel(p); expect(f"unsafe path {p!r} rejected", False)
    except InputError:
        expect(f"unsafe path {p!r} rejected", True)
expect("script JSON cannot close its <script>", "</script" not in script_json({"x": "</script><b>"}))
expect("canonical JSON is stable", canonical({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}')
# schema subset
d = schema.load("direction")
errs = schema.validate({"schemaVersion": 2}, d)
expect("unknown schemaVersion rejected", any("schemaVersion" in e for e in errs))
errs = schema.validate({"schemaVersion": 1, "records": [{"id": "x"}, {"id": "x"}]}, schema.load("approvals"))
expect("duplicate ids rejected", any("more than once" in e for e in errs))
try:
    schema._check_schema({"type": "object", "minProperties": 1}, "t"); expect("unsupported schema keywords are errors", False)
except schema.SchemaError:
    expect("unsupported schema keywords are errors", True)
sys.exit(1 if fails else 0)
PY
r=$?; grep -c '^ok' "$W/out" | xargs -I{} echo "  {} unit checks passed"; grep '^FAIL' "$W/out" | sed 's/^/  /'
if [[ $r -eq 0 ]]; then ok "library unit checks"; else bad "library unit checks"; fi

echo "== palette.py"
run "$PALETTE" contrast "#777777" "#ffffff"
check "a failing pair exits 1" rc 1
check "the ratio is truncated, not rounded" has "4.47:1"
run "$PALETTE" contrast "#767676" "#ffffff"
check "a passing pair exits 0" rc 0
run "$PALETTE" contrast "#777777" "#ffffff" --large
check "large text needs 3:1" rc 0
run "$PALETTE" contrast "#77" "#ffffff"
check "a bad colour argument exits 2" rc 2
run "$PALETTE" ramp --name brand --seed "#2f7d6d" --out tokens.json
check "ramp writes tokens" rc 0
check "ramp prints contrast against white and black" has "vs white"
check "the ramp is valid DTCG with an OKLCH record" hc_py -c "
import json, sys
t = json.load(open(sys.argv[1]))['color']['brand']
ls = [t[k]['\$extensions']['org.quantqbit.oklch']['l'] for k in sorted(t, key=int)]
sys.exit(0 if ls == sorted(ls, reverse=True) and all('hex' in t[k]['\$value'] for k in t) else 1)" "$W/tokens.json"
cp "$W/tokens.json" "$W/tokens.before"
run "$PALETTE" ramp --name brand --seed "#7d2f6d" --out tokens.json
check "a different ramp under the same name conflicts (exit 1)" rc 1
check "nothing was written on conflict" cmp -s "$W/tokens.json" "$W/tokens.before"
run "$PALETTE" ramp --name brand --seed "#2f7d6d" --steps 50,100 --lightness 0.5,0.9,0.2 --out tokens.json
check "mismatched --lightness is a usage error (exit 2)" rc 2
run "$PALETTE" ramp --name brand --seed "#2f7d6d" --steps 50,100,200 --lightness 0.9,0.95,0.2
check "non-monotonic lightness is refused" rc 2
printf '[{"fg": "{color.brand.950}", "bg": "{color.brand.50}", "where": "body"}, {"fg": "{color.brand.400}", "bg": "{color.brand.500}", "where": "bad"}]\n' > "$W/pairs.json"
run "$PALETTE" check --tokens tokens.json --pairs pairs.json
check "check fails on a bad pair" rc 1
check "check uses the report sections" has "Section 1, WCAG 2.2 conformance"
check "check names the failing pair" has "FAIL  bad"

echo "== type_scale.py"
run "$TYPE" scale --base 16 --ratio 1.2 --steps caption,body,h2,h1 --body body --platform web,android,ios,rn --fluid 360:1440 --max-ratio 1.25 --out tokens.json
check "scale merges into the token file" rc 0
check "the web value is a clamp() with a rem term" hc_py -c "
import json, sys
t = json.load(open(sys.argv[1]))['typography']['scale']['h1']
w = t['\$extensions']['org.quantqbit.platform']['web']
sys.exit(0 if w.startswith('clamp(') and 'rem +' in w and t['\$value']['unit'] == 'px' else 1)" "$W/tokens.json"
check "the old token file is kept as .bak" test -f "$W/tokens.json.bak"
hc_py -c "open(__import__('sys').argv[1], 'wb').write(b'not really a font')" "$W/face.ttf"
run "$TYPE" font --name display --family "Test Face" --source local --file face.ttf:700 --out tokens.json
check "a local font without licence evidence is refused" rc 2
run "$TYPE" font --name display --family "Test Face" --source local --file face.ttf:700 --license OFL-1.1 --license-evidence fonts/OFL.txt --out tokens.json
check "a local font record is written" rc 0
run "$TYPE" check --tokens tokens.json
check "check passes on an intact record" rc 0
printf 'changed' >> "$W/face.ttf"
run "$TYPE" check --tokens tokens.json
check "check fails when a font file changed" rc 1
check "and says which" has "changed since it was recorded"
run "$TYPE" font --name text --family "Segoe UI" --source system --out tokens.json
check "a system font needs an availability note" rc 2
run "$TYPE" media --canvas-width 1080 --display-width 320 --min headline=24
check "media sizes print canvas px" has "81.0 canvas px"

echo "== bootstrap: one import path, source and installed layouts"
for f in $(grep -rl "harness lib bootstrap" "$ROOT/harness/skills" --include='*.py'); do
  grep -q 'sys.path\[:0\] = \[str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()\]\[:1\]' "$f" \
    || bad "$(basename "$f") uses a different bootstrap"
done
n=$(grep -rl "from harnesslib\|import harnesslib" "$ROOT/harness/skills" --include='*.py' | wc -l | tr -d ' ')
m=$(grep -rl "harness lib bootstrap" "$ROOT/harness/skills" --include='*.py' | wc -l | tr -d ' ')
check "every script that imports harnesslib uses the documented bootstrap ($m of $n)" test "$n" -eq "$m"
mkdir -p "$W/inst/.claude/harness" "$W/inst/.claude/skills/color-science"
cp -R "$ROOT/harness/lib" "$W/inst/.claude/harness/lib"
cp -R "$ROOT/harness/skills/color-science/scripts" "$W/inst/.claude/skills/color-science/scripts"
run "$W/inst/.claude/skills/color-science/scripts/palette.py" convert "#336699"
check "the installed layout (.claude/harness/lib) imports" rc 0
rm -rf "$W/inst/.claude/harness/lib"
run "$W/inst/.claude/skills/color-science/scripts/palette.py" convert "#336699"
check "a missing library exits 2 and says to sync" bash -c "[[ \$(cat '$W/rc') == 2 ]] && grep -q 'harness sync' '$W/out'"

check "the library ships wherever a script that imports it ships" hc_py - "$ROOT/harness/manifest.tsv" "$ROOT/harness" <<'PY'
import sys
from pathlib import Path
rows = [l.rstrip("\r\n").split("\t") for l in open(sys.argv[1], encoding="utf-8") if not l.startswith("#")]
lib = set.intersection(*[set(r[4].split(",")) for r in rows if r[0].startswith("lib/")])
need = set()
for r in rows:
    if r[0].endswith(".py") and r[0].startswith("skills/") and "harness lib bootstrap" in (Path(sys.argv[2]) / r[0]).read_text(encoding="utf-8"):
        need |= set(r[4].split(","))
sys.exit(0 if "all" not in need and need <= lib else 1)
PY
check "no __pycache__ was left in harness/" test -z "$(find "$ROOT/harness" -name __pycache__ -print -quit)"
echo "color tools tests: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
