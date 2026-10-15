"""motion-ui library checks with no browser and no ffmpeg (used by tests/motion-ui.test.sh).

Schema and viewports, the approval parts (what changes Gate 3 and what doesn't), automatic-motion
rules (WCAG 2.2.2), lint, review hashes (evidence outputs excluded, the build included), cut, hold
and loop signals on synthetic frames, the flash labels, path globs and harness.config parsing.
Prints one line per check; exit 1 when any fails.
"""

from __future__ import annotations

import copy
import json
import math
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "harness" / "lib"))
sys.dont_write_bytecode = True
from harnesslib import framecheck, schema  # noqa: E402
from harnesslib import motion as mo  # noqa: E402
from harnesslib.fsutil import InputError, harness_config  # noqa: E402

failed = 0


def check(ok: bool, what: str) -> None:
    global failed
    print(("ok    " if ok else "FAIL  ") + what)
    failed += not ok


def raises(fn, *a) -> bool:
    try:
        fn(*a)
    except (InputError, ValueError):
        return True
    return False


EXAMPLE = json.loads((REPO / "harness/skills/motion-ui/templates/motion.example.json").read_text(encoding="utf-8"))


def piece(**over) -> dict:
    d = copy.deepcopy(EXAMPLE)
    d.update(over)
    return d


# ---------------------------------------------------------------- schema and viewports
schema.check(EXAMPLE, "motion", "example")
check(True, "the template example matches the motion schema")
bad = piece()
bad["capture"]["speed"] = 2
check(raises(schema.check, bad, "motion", "x"), "an unknown capture key is refused")
check(mo.viewport_spec(EXAMPLE, "kiosk")["size"] == (1080, 1920) and mo.viewport_spec(EXAMPLE, "kiosk")["dpr"] == 1
      and mo.viewport_spec(EXAMPLE, "kiosk")["mobile"] is True, "a custom viewport resolves size and dpr, the rest from its like")
check(mo.viewport_spec(EXAMPLE, "mobile")["size"] == (390, 844), "built-in viewports resolve")
v = piece(customViewports={"wall": {"size": "100x5000", "like": "desktop"}})
check(raises(mo.viewport_spec, v, "wall"), "a custom viewport outside 240-3840 px is refused")
v = piece(customViewports={"wall": {"size": "1920x1080", "like": "tv"}})
check(raises(mo.viewport_spec, v, "wall"), "a custom viewport like an unknown built-in is refused")
check(raises(mo.viewport_spec, EXAMPLE, "watch"), "an undeclared viewport is refused")

# ---------------------------------------------------------------- approval parts
base = mo._parts(EXAMPLE)
p2 = piece()
p2["capture"]["ready"] = {"selector": "#other", "timeoutMs": 9000}
p2["analysis"]["observations"].append({"ms": 1, "text": "a new note"})
p2["target"]["files"].append("src/x.ts")
p2["title"] = "renamed"
check(mo._parts(p2) == base, "capture, analysis, target and title edits leave the approved parts unchanged")
p3 = piece()
p3["rows"][0]["endMs"] = 1200
check({k for k in base if mo._parts(p3)[k] != base[k]} == {"timing"}, "a row edit changes only the timing part")
p4 = piece()
p4["assets"][0]["path"] = "public/hero/interior.webp"
p4["assets"][0]["provenance"] = "out/story-art/2026-10-12/plan.md"
check(mo._parts(p4) == base, "adding an asset's file does not touch Gate 3 (the plan is approved, the bytes bind at review)")
p5 = piece()
p5["assets"][0]["plan"]["brief"] = "a different wall"
check({k for k in base if mo._parts(p5)[k] != base[k]} == {"assetPlan"}, "changing an asset's plan changes the assetPlan part")
p6 = piece()
p6["reference"]["crop"] = {"x": 0, "y": 0, "w": 1080, "h": 1920}
check({k for k in base if mo._parts(p6)[k] != base[k]} == {"reference"}, "a new crop changes the reference part")
p7 = piece()
p7["motionControl"]["selector"] = "#pause"
check({k for k in base if mo._parts(p7)[k] != base[k]} == {"visual"}, "the control is part of the approved visual intent")

# ---------------------------------------------------------------- automatic motion (WCAG 2.2.2)
def auto(mode, length, repeat=None, autoplay=None):
    d = piece()
    d["loop"] = {"mode": mode, "lengthMs": length}
    if repeat is not None:
        d["loop"]["repeat"] = repeat
    if autoplay is not None:
        d["loop"]["autoplay"] = autoplay
    return mo.automatic_motion(d)


a = auto("time-loop", 4000, "infinite")
check(a["needsControl"] and math.isinf(a["totalMs"]), "a 4 s loop that repeats forever needs a control")
check(auto("once", 10000)["needsControl"], "a 10 s one-shot needs a control")
check(not auto("time-loop", 4000, 1)["needsControl"], "a 4 s loop played once needs none")
check(not auto("time-loop", 2000, 2)["needsControl"], "2 x 2 s (4 s in total) needs none")
check(auto("time-loop", 2000, 3)["needsControl"], "3 x 2 s (6 s in total) needs a control")
check(not auto("scroll", 20000)["needsControl"], "scroll motion moves only on input")
check(auto("scroll", 20000, autoplay=True)["needsControl"], "scroll motion that plays by itself counts")


def scenes_for(length):
    return [{"id": "s1", "durationMs": length}]


def lint_of(d):
    return mo.lint(None, "x", d, None, "spec")


d = piece(loop={"mode": "time-loop", "lengthMs": 4000, "repeat": "infinite"}, scenes=scenes_for(4000),
          rows=[{"startMs": 0, "endMs": 4000, "track": "camera", "action": "drift", "confidence": "assumed"}],
          motionControl={"kind": "none"}, reducedMotion={"strategy": "static-complete"})
d["resilience"].pop("fallback", None)
lt = lint_of(d)
check(any("WCAG 2.2.2" in e for e in lt.errors), "lint: endless 4 s loop without a control is an error")
d["motionControl"] = {"kind": "none", "essentialJustification": "a live data visual that must keep moving"}
lt = lint_of(d)
check(not any("2.2.2" in e for e in lt.errors) and any(r["id"] == "motion-control:essential" for r in lt.reviews),
      "lint: an essential justification turns it into a review item")
d["motionControl"] = {"kind": "pause"}
check(any("needs a selector" in e for e in lint_of(d).errors), "lint: a control without a selector is an error (web)")
d["motionControl"] = {"kind": "stop", "selector": "#stop"}
check(not lint_of(d).errors, "lint: a stop control satisfies WCAG 2.2.2")

# ---------------------------------------------------------------- lint
lt = lint_of(EXAMPLE)
check(not lt.errors, "lint: the template example is clean before Gate 3 (assets may be plans)")
lt = mo.lint(None, "x", EXAMPLE, None, "verify")
check(any("planned but not added yet" in e for e in lt.errors), "lint --stage verify: planned assets must exist")
d = piece()
d["scenes"][0]["durationMs"] = 6000
check(any("must match" in e for e in lint_of(d).errors), "lint: scene durations must add up to the loop")
d = piece()
d["rows"][2]["startMs"] = 500
check(any("time order" in e for e in lint_of(d).errors), "lint: rows out of time order are an error")
d = piece()
d["rows"][0]["easing"] = "bouncy"
check(not lint_of(d).errors, "lint without a project does not resolve easing tokens (no false errors)")
d = piece(loop={"mode": "scroll", "lengthMs": 14500})
check(any("needs input" in e for e in lint_of(d).errors), "lint: a scroll piece needs input")
d = piece(input={"sequence": [{"action": "click", "target": "#a", "atMs": 0}]})
check(any("takes no input" in e for e in lint_of(d).errors), "lint: a time loop takes no input")
d = piece()
d["assets"].append({"id": "stock", "role": "footage", "origin": "licensed"})
check(any("needs a licence" in e for e in lint_of(d).errors), "lint: licensed footage needs a licence")
d = piece(platform="android-compose")
check(any("does not fit platform" in e for e in lint_of(d).errors), "lint: a browser driver does not fit a Compose piece")
d = piece(platform="ios")
d["capture"] = {"driver": "file"}
lt = lint_of(d)
check(any("evidence-only" in w for w in lt.warnings), "lint: native drivers are reported as evidence-only")

# ---------------------------------------------------------------- times and scenes
t = mo.capture_times(EXAMPLE)
check(t[0] == 0 and t[-1] == EXAMPLE["loop"]["lengthMs"] and t == sorted(t), "default capture times start at 0 and end at the loop seam")
check(mo.expected_scene(EXAMPLE, 6600) == "ridge" and mo.expected_scene(EXAMPLE, 14500 + 100) == "arrive",
      "the expected scene follows the spec and wraps for loops")

# ---------------------------------------------------------------- review hash
m = {"piece": {"hash": "a" * 64, "inputs": "b" * 64}, "build": {"kind": "content", "sha256": "c" * 64, "files": 3},
     "target": {"kind": "url", "origin": "http://localhost:3000", "path": "/"}, "captureConfig": {"driver": "web"},
     "inputs": {"config": "d" * 64, "assets": [{"path": "public/a.webp", "sha256": "e" * 64}]},
     "outputs": [{"path": "o/captures/desktop/t0.png", "sha256": "f" * 64, "bytes": 1},
                 {"path": "o/recording/desktop.mp4", "sha256": "1" * 64, "bytes": 1, "kind": "evidence"}],
     "reviews": [{"id": "x", "note": "look"}]}
h = mo.review_hash(m)
m2 = copy.deepcopy(m)
m2["outputs"][1]["sha256"] = "2" * 64
check(mo.review_hash(m2) == h, "the review hash ignores evidence bytes (the recording)")
for what, change in (("the build", lambda x: x["build"].update(sha256="9" * 64)),
                     ("the target", lambda x: x["target"].update(path="/other")),
                     ("the capture settings", lambda x: x["captureConfig"].update(browser="Chrome 999")),
                     ("an asset's bytes", lambda x: x["inputs"]["assets"][0].update(sha256="8" * 64)),
                     ("a capture", lambda x: x["outputs"][0].update(sha256="7" * 64)),
                     ("the review items", lambda x: x["reviews"].append({"id": "y", "note": "more"}))):
    m3 = copy.deepcopy(m)
    change(m3)
    check(mo.review_hash(m3) != h, f"the review hash changes with {what}")

# ---------------------------------------------------------------- build fingerprint
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "src/hero").mkdir(parents=True)
    (root / "src/other").mkdir(parents=True)
    (root / "src/hero/Hero.tsx").write_bytes(b"export const a = 1;\r\n")
    (root / "src/other/x.ts").write_text("x", encoding="utf-8")
    (root / "package.json").write_text("{}", encoding="utf-8")
    d = piece(target={"route": "/", "files": ["src/hero/Hero.tsx"]})
    d.pop("fingerprint")
    f1 = mo.build_fingerprint(root, d)
    check(f1["files"] == 2 and not f1["partial"] and "src/hero/**" in f1["globs"], "the default fingerprint covers the target's folder and manifests")
    (root / "src/hero/Hero.tsx").write_bytes(b"export const a = 1;\n")
    check(mo.build_fingerprint(root, d)["sha256"] == f1["sha256"], "line endings don't change the fingerprint (CRLF checkouts)")
    (root / "src/other/x.ts").write_text("y", encoding="utf-8")
    check(mo.build_fingerprint(root, d)["sha256"] == f1["sha256"], "a file outside the globs doesn't change it")
    (root / "src/hero/motion.ts").write_text("export const t = 2;", encoding="utf-8")
    check(mo.build_fingerprint(root, d)["sha256"] != f1["sha256"], "a new file in the motion's folder changes it")
    (root / "brand/motion/x/out").mkdir(parents=True)
    d2 = piece(target={"route": "/", "files": []}, fingerprint={"globs": ["**"]})
    a1 = mo.build_fingerprint(root, d2)["sha256"]
    (root / "brand/motion/x/out/t0.png").write_bytes(b"png")
    check(mo.build_fingerprint(root, d2)["sha256"] == a1, "the piece's own outputs never enter the fingerprint")
    d3 = piece(target={"route": "/", "files": []})
    d3.pop("fingerprint")
    d3["capture"].pop("page", None)
    check(mo.build_fingerprint(root, d3)["partial"], "nothing naming the motion's code is a partial fingerprint")

check(bool(mo._glob_re("src/**/*.ts").match("src/a/b/c.ts")) and not mo._glob_re("src/*.ts").match("src/a/c.ts")
      and bool(mo._glob_re("src/**").match("src/a")), "path globs: ** spans folders, * stays in one")

# ---------------------------------------------------------------- signals
W = 64 * 36


def flat(v: int) -> bytes:
    return bytes([v]) * W


frames = [flat(40 + i) for i in range(30)] + [flat(200)] * 20 + [flat(40 + i) for i in range(30)]
times = [i * 1000 / 30 for i in range(len(frames))]
diffs = mo.frame_diffs(frames)
cuts = mo.cuts(diffs, times)
check([round(c["ms"]) for c in cuts] == [1000, 1667], f"cuts at the two picture changes ({[c['ms'] for c in cuts]})")
hl = mo.holds(diffs, times)
check(len(hl) == 1 and abs(hl[0]["fromMs"] - 1000) < 40 and abs(hl[0]["toMs"] - 1633) < 40, f"one hold over the still stretch ({hl})")
lp = mo.loop_candidates(frames, times, min_overlap=10)
check(bool(lp) and abs(lp[0]["lagMs"] - 1667) < 40 and lp[0]["score"] < 0.5, f"the loop repeats after 1667 ms ({lp[:1]})")
smooth = [flat(40 + i % 50) for i in range(90)]
check(not mo.cuts(mo.frame_diffs(smooth), [i * 33.3 for i in range(90)])[1:], "a slow continuous change is not a run of cuts")

# flashes: 4 per second at a small luminance change (below WCAG's 10 % general threshold)
dim, bright = flat(120), flat(140)
seq = [dim if (i // 4) % 2 == 0 else bright for i in range(60)]  # 30 fps, a change every 4 frames
check(not framecheck.flash_signal(seq, 30), "a small 4 Hz flicker is under the WCAG 2.3.1 approximation")
check(bool(framecheck.flash_signal(seq, 30, **mo.FLASH_POLICY)), "the stricter project rule (mo.FLASH_POLICY) finds it")

# ---------------------------------------------------------------- harness.config
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / ".claude").mkdir()
    (Path(tmp) / ".agents/harness.config").write_bytes(b"# c\r\nprofiles=web\r\ndev_url = \"http://localhost:5173\" \r\n\r\nx\r\n")
    cfg = harness_config(Path(tmp))
    check(cfg.get("dev_url") == "http://localhost:5173" and cfg.get("profiles") == "web", "harness.config reads CRLF lines and quotes")
    check(harness_config(Path(tmp) / "none") == {}, "no harness.config is an empty config")

print(f"unit: {'FAILED ' + str(failed) if failed else 'all passed'}")
sys.exit(1 if failed else 0)
