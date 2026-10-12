"""Motion pieces: brand/motion/<id>/motion.json -> lint, approvals, build fingerprints, runs, reviews.

A motion piece says what a hero, cinematic or reference-driven motion shows and when (scenes, timed
rows per track, viewports, the asset plan, reduced-motion and control behaviour) and how to capture
it. Its look comes from the selected motion concept, so the piece never sets a colour or a font.

Three words, three fingerprints (motion-ui references/motion-spec.md):
  approved  Gate 3: the owner accepts the intent. Bound to the parts visual, timing, assetPlan and
            reference (each hashed so a stale record can say what changed) and to the motion
            concept's approval hashes. Asset bytes, the app's code, capture settings and analysis
            notes are not part of it: assets are approved as a plan before they exist.
  verified  a run of `motion.py verify` that is complete for its platform and driver: every
            required check ran. It records the build fingerprint (the content of the project files
            that make up the motion), the resolved target, the effective capture settings, the asset
            bytes and the output hashes.
  reviewed  the owner acknowledged the REVIEW REQUIRED items of one verified run. The record binds
            to the run's review hash, so a change to the code, the target, the capture settings, an
            asset or an output needs a new verify and a new look, even when motion.json is unchanged.
Real-time recordings are evidence outputs: never byte-identical, so they are not in the review hash
(the build fingerprint still binds the acknowledgement to the code that was recorded).
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from . import direction as dl
from . import schema
from .fsutil import InputError, canonical, load_json, resolve_inside, sha256_text

PIECES = "brand/motion"
RUNS_DIR = f"{dl.RUNS}/motion"
PIECE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
AUTOPLAY_LIMIT_MS = 5000  # WCAG 2.2.2: moving content that starts by itself and lasts longer needs a control
# The harness rule "nothing flashes more than 3 times per second" also counts flashes below the WCAG 2.3.1
# general threshold: a smaller changed area and a smaller luminance change (framecheck.flash_signal).
FLASH_POLICY = {"area": 0.01, "delta": 0.05}
EASING_WORDS = ("linear", "hold", "cut", "step", "smootherstep", "spring")
MAX_DEFAULT_TIMES = 60

# Built-in viewports. Projects add their own in customViewports ({"size": "WxH", "like": "<built-in>"}).
VIEWPORTS: dict[str, dict] = {
    "desktop": {"size": (1440, 900), "dpr": 1, "mobile": False, "label": "desktop 1440x900"},
    "tablet": {"size": (820, 1180), "dpr": 2, "mobile": True, "label": "tablet 820x1180 @2x"},
    "mobile": {"size": (390, 844), "dpr": 3, "mobile": True, "label": "phone 390x844 @3x"},
}
VIEWPORT_SIDE = (240, 3840)
CUSTOM_SIZE = re.compile(r"^([1-9][0-9]{2,3})x([1-9][0-9]{2,3})$")

# What each capture driver can establish (references/platform-mobile.md has the matrix in prose).
# required: the evidence a run must hold to be complete; a missing one makes it incomplete.
CAPABILITIES: dict[str, dict] = {
    "web": {"visual": True, "behaviour": True, "reduced": True, "semantic": True, "ceiling": "complete",
            "required": ["visual", "behaviour", "reduced-motion", "recording", "compare"]},
    "expo-web": {"visual": True, "behaviour": True, "reduced": True, "semantic": True, "ceiling": "complete (web only)",
                 "required": ["visual", "behaviour", "reduced-motion", "recording", "compare"]},
    "adb": {"visual": False, "behaviour": False, "reduced": False, "semantic": False, "ceiling": "incomplete",
            "required": ["visual", "semantic", "recording"]},
    "frames": {"visual": True, "behaviour": False, "reduced": False, "semantic": False, "ceiling": "complete with a recording and manual review",
               "required": ["visual", "recording"]},
    "file": {"visual": False, "behaviour": False, "reduced": False, "semantic": False, "ceiling": "incomplete",
             "required": ["visual", "semantic", "recording"]},
}
DRIVERS_FOR = {"web": ("web",), "react-native": ("expo-web", "adb", "file"), "android-compose": ("adb", "frames", "file"),
               "ios": ("file", "frames")}
SKIP_DIRS = {"node_modules", ".git", ".build", ".preview", "dist", "build", ".expo", "Pods", ".venv", "venv",
             "__pycache__", ".claude", ".next", ".nuxt", ".svelte-kit", ".turbo", "coverage", "out", ".gradle"}
MANIFESTS = ("package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "app.json",
             "app.config.js", "app.config.ts", "build.gradle", "build.gradle.kts", "settings.gradle.kts", "Podfile.lock")


# ------------------------------------------------------------------ loading

def piece_rel(pid: str) -> str:
    if not PIECE_ID.match(pid or ""):
        raise InputError(f"piece id {pid!r}: lower-case letters, digits and dashes (it names brand/motion/<id>/)")
    return f"{PIECES}/{pid}/motion.json"


def list_pieces(root: Path) -> list[str]:
    base = Path(root) / PIECES
    return sorted(d.name for d in base.iterdir() if (d / "motion.json").is_file()) if base.is_dir() else []


def load_piece(root: Path, pid: str) -> tuple[str, dict]:
    rel = piece_rel(pid)
    path = resolve_inside(root, rel, "motion piece", must_exist=True)
    data = load_json(path)
    schema.check(data, "motion", rel)
    if data["id"] != pid:
        raise InputError(f"{rel}: id {data['id']!r} must match its folder {pid!r}")
    check_viewports(data, rel)
    return rel, data


def viewport_spec(piece: dict, name: str) -> dict:
    """One viewport as the capture uses it: a built-in, or a customViewports entry resolved
    against the built-in it is like (size and dpr given, the rest inherited)."""
    custom = (piece.get("customViewports") or {}).get(name)
    if custom is None:
        if name not in VIEWPORTS:
            raise InputError(f"viewport {name!r} is neither built in ({', '.join(VIEWPORTS)}) nor declared in customViewports")
        out = dict(VIEWPORTS[name])
        out["name"] = name
        return out
    where = f"customViewports.{name}"
    like = custom.get("like")
    if like not in VIEWPORTS:
        raise InputError(f"{where}.like: {like!r} must name a built-in viewport ({', '.join(VIEWPORTS)})")
    m = CUSTOM_SIZE.match(custom.get("size") or "")
    w, h = (int(m[1]), int(m[2])) if m else (0, 0)
    if not (m and VIEWPORT_SIDE[0] <= w <= VIEWPORT_SIDE[1] and VIEWPORT_SIDE[0] <= h <= VIEWPORT_SIDE[1]):
        raise InputError(f"{where}.size: {custom.get('size')!r} must be WxH with each side {VIEWPORT_SIDE[0]}-{VIEWPORT_SIDE[1]} px")
    base = VIEWPORTS[like]
    return {"name": name, "size": (w, h), "dpr": custom.get("dpr", base["dpr"]), "mobile": base["mobile"],
            "label": custom.get("label", f"{w}x{h}, like {like}"), "like": like}


def check_viewports(piece: dict, where: str) -> None:
    for name in piece.get("customViewports") or {}:
        try:
            viewport_spec(piece, name)
        except InputError as e:
            raise InputError(f"{where}: {e}") from None
    for name in piece["viewports"]:
        try:
            viewport_spec(piece, name)
        except InputError as e:
            raise InputError(f"{where}: viewports: {e}") from None


# ------------------------------------------------------------------ timing

def scene_spans(piece: dict) -> list[tuple[str, float, float]]:
    """(scene id, start ms, end ms) on the piece's timeline, in order."""
    out, t = [], 0.0
    for sc in piece["scenes"]:
        out.append((sc["id"], t, t + sc["durationMs"]))
        t += sc["durationMs"]
    return out


def expected_scene(piece: dict, ms: float) -> str | None:
    """The scene the spec shows at ms (loops wrap; interaction pieces have no time-scene mapping)."""
    if piece["loop"]["mode"] == "interaction":
        return None
    total = sum(s["durationMs"] for s in piece["scenes"])
    if total <= 0:
        return None
    t = ms % total if piece["loop"]["mode"] == "time-loop" else min(ms, total - 1e-6)
    for sid, a, b in scene_spans(piece):
        if a <= t < b:
            return sid
    return piece["scenes"][-1]["id"]


def capture_times(piece: dict) -> list[float]:
    """capture.times, or times derived from the spec: each scene shortly after it arrives and at its
    middle, every row's start and end, and the loop end (the seam). At most MAX_DEFAULT_TIMES."""
    given = (piece.get("capture") or {}).get("times")
    if given:
        return sorted(set(float(t) for t in given))
    length = piece["loop"]["lengthMs"]
    mode = piece["loop"]["mode"]
    pts: set[float] = {0.0}
    if mode == "scroll" and piece.get("input", {}).get("scroll"):
        for _, ms in piece["input"]["scroll"]["progressMap"]:
            pts.add(float(ms))
    elif mode == "interaction" and piece.get("input", {}).get("sequence"):
        for s in piece["input"]["sequence"]:
            pts.add(float(s["atMs"]))
            pts.add(float(s["atMs"]) + 250)
    else:
        for _, a, b in scene_spans(piece):
            pts.add(a + min(120.0, (b - a) / 4))
            pts.add((a + b) / 2)
        for r in piece["rows"]:
            pts.add(float(r["startMs"]))
            pts.add(float(r["endMs"]))
        if mode == "time-loop":
            pts.add(float(length))
    out = sorted(t for t in pts if 0 <= t <= length)
    if len(out) > MAX_DEFAULT_TIMES:
        step = len(out) / MAX_DEFAULT_TIMES
        out = sorted({out[int(i * step)] for i in range(MAX_DEFAULT_TIMES)} | {out[-1]})
    return [round(t, 3) for t in out]


def automatic_motion(piece: dict) -> dict:
    """How long motion runs by itself (WCAG 2.2.2): an endless loop is infinite however short it is,
    N repeats are N x length, a one-shot is its length. Scroll and interaction motion only moves
    when a person acts, unless autoplay says otherwise."""
    loop = piece["loop"]
    mode = loop["mode"]
    autoplay = loop.get("autoplay", mode in ("time-loop", "once"))
    if not autoplay:
        return {"autoplay": False, "totalMs": 0.0, "needsControl": False}
    if mode == "time-loop":
        rep = loop.get("repeat", "infinite")
        total = math.inf if rep == "infinite" else float(rep) * loop["lengthMs"]
    else:
        total = float(loop["lengthMs"])
    return {"autoplay": True, "totalMs": total, "needsControl": total > AUTOPLAY_LIMIT_MS}


# ------------------------------------------------------------------ motion tokens

def suggest_motion(direction: dict) -> dict:
    """Motion tokens from the mood axes, anchored to ui-ux references/motion.md. A starting point
    for the concept round, not a rule: the creative-director adjusts them. Shared by
    render_video.py motion-tokens and motion.py tokens."""
    axes = direction.get("mood", {}).get("axes", {})
    energy = axes.get("calm-energetic", 0.0)
    playful = -min(0.0, axes.get("playful-serious", 0.0))
    base = round(400 - 140 * energy)
    durs = {"fast": round(base * 0.55), "base": base, "slow": round(base * 1.6)}
    easing = {"standard": [0.2, 0, 0, 1], "enter": [0.05, 0.7, 0.1, 1], "exit": [0.3, 0, 0.8, 0.15],
              "emphasis": [0.34, 1.56, 0.64, 1] if playful > 0.3 else [0.2, 0, 0, 1]}
    return {"motion": {
        "$description": "Motion for video and UI, suggested by render_video.py motion-tokens from the direction's mood",
        "duration": {k: {"$type": "duration", "$value": {"value": v, "unit": "ms"}} for k, v in durs.items()},
        "easing": {k: {"$type": "cubicBezier", "$value": v} for k, v in easing.items()}}}


# ------------------------------------------------------------------ lint

@dataclass
class Lint:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reviews: list[dict] = field(default_factory=list)


def lint(p: dl.Project | None, rel: str, piece: dict, resolved: dict | None, stage: str = "spec") -> Lint:
    """Checks the schema can't express. stage 'spec' (before Gate 3: assets may be plans) or
    'verify' (every planned asset must exist with its provenance or licence)."""
    out = Lint()
    E, W = out.errors.append, out.warnings.append
    pid = piece["id"]
    names = set(piece["viewports"]) | set(piece.get("customViewports") or {})
    ref = piece.get("reference")
    if ref and ref.get("designedViewport") and ref["designedViewport"] not in names:
        E(f"reference.designedViewport {ref['designedViewport']!r} is not one of the viewports ({', '.join(sorted(names))})")
    if ref and not ref.get("sha256"):
        (E if stage == "verify" else W)("the reference is not recorded yet: motion.py probe <id> --record (its hash, size, fps)")
    # mediums against the concept
    medium = piece["fidelity"]["medium"]
    if resolved is not None and medium not in resolved["mediums"]:
        scope = f"motion:{pid}:medium={medium}"
        if p is None or not dl.exception_approved(p, scope):
            E(f"fidelity.medium {medium!r} is not one of the concept's mediums ({', '.join(resolved['mediums'])}); "
              f"change it or get an exception approved: --gate exception --scope \"{scope}\"")
    if piece["fidelity"]["claim"] in ("original-footage", "generated-footage") and medium != "video":
        W(f"fidelity.claim {piece['fidelity']['claim']!r} with medium {medium!r}: footage claims usually mean a video medium")
    # timing
    mode = piece["loop"]["mode"]
    length = piece["loop"]["lengthMs"]
    total = sum(s["durationMs"] for s in piece["scenes"])
    if mode in ("time-loop", "once") and total != length:
        E(f"the scenes last {total} ms; loop.lengthMs is {length} ms (they must match)")
    for sc in piece["scenes"]:
        if sc.get("holdMs", 0) > sc["durationMs"]:
            E(f"scene {sc['id']}: holdMs {sc['holdMs']} is longer than the scene ({sc['durationMs']} ms)")
        tr = sc.get("transitionIn") or {}
        if tr.get("durationMs", 0) > sc["durationMs"]:
            E(f"scene {sc['id']}: transitionIn lasts {tr['durationMs']} ms, longer than the scene")
    scene_ids = {s["id"] for s in piece["scenes"]}
    last = -1.0
    for i, r in enumerate(piece["rows"]):
        where = f"rows[{i}]"
        if r["endMs"] < r["startMs"]:
            E(f"{where}: endMs {r['endMs']} is before startMs {r['startMs']}")
        if r["endMs"] > length:
            E(f"{where}: ends at {r['endMs']} ms, after the piece ({length} ms)")
        if r["startMs"] < last:
            E(f"{where}: starts at {r['startMs']} ms, before the row above it (keep rows in time order)")
        last = max(last, r["startMs"])
        if r.get("scene") and r["scene"] not in scene_ids:
            E(f"{where}: scene {r['scene']!r} is not a scene of the piece")
        e = r.get("easing")
        if e and e not in EASING_WORDS:
            if p is None:
                pass
            else:
                try:
                    dl.resolve_ref(p, e, "cubicBezier")
                except Exception as ex:  # noqa: BLE001  (token errors and input errors alike)
                    E(f"{where}: easing {e!r}: {ex} (use a cubicBezier token or one of {', '.join(EASING_WORDS)})")
    # input
    has_input = bool(piece.get("input"))
    if mode in ("scroll", "interaction") and not has_input:
        E(f"loop.mode {mode} needs input ({'input.scroll' if mode == 'scroll' else 'input.sequence'}): what the capture does instead of waiting")
    if mode in ("time-loop", "once") and has_input:
        E(f"loop.mode {mode} takes no input (input is for scroll and interaction pieces)")
    if mode == "scroll" and has_input and not piece["input"].get("scroll"):
        E("loop.mode scroll needs input.scroll")
    if mode == "interaction" and has_input and not piece["input"].get("sequence"):
        E("loop.mode interaction needs input.sequence")
    # automatic motion (WCAG 2.2.2)
    auto = automatic_motion(piece)
    ctl = piece["motionControl"]
    if auto["needsControl"]:
        runs = "repeats without end" if math.isinf(auto["totalMs"]) else f"runs {auto['totalMs'] / 1000:g} s"
        if ctl["kind"] == "none":
            if ctl.get("essentialJustification"):
                out.reviews.append({"id": "motion-control:essential", "check": "pause stop hide", "kind": "suitability",
                                    "note": f"the motion starts by itself and {runs}, with no pause, stop or hide control; "
                                            f"the spec says it is essential: {ctl['essentialJustification']}"})
            else:
                E(f"the motion starts by itself and {runs} (over {AUTOPLAY_LIMIT_MS // 1000} s): WCAG 2.2.2 needs a way to "
                  "pause, stop or hide it (motionControl.kind and selector), or an essentialJustification the owner accepts")
    if ctl["kind"] != "none" and not ctl.get("selector") and piece["capture"]["driver"] in ("web", "expo-web"):
        E(f"motionControl.kind {ctl['kind']} needs a selector (the control the checks press)")
    # reduced motion and resilience
    st = piece["reducedMotion"].get("staticAt")
    if st and st["scene"] not in scene_ids:
        E(f"reducedMotion.staticAt.scene {st['scene']!r} is not a scene of the piece")
    # assets
    assets = {a["id"]: a for a in piece.get("assets") or []}
    for sc in piece["scenes"]:
        for m in sc.get("media") or []:
            if m not in assets:
                E(f"scene {sc['id']}: media {m!r} is not in assets")
    fb = piece["resilience"].get("fallback")
    if fb and fb not in assets:
        E(f"resilience.fallback {fb!r} is not in assets")
    for a in assets.values():
        where = f"asset {a['id']}"
        plan = a.get("plan") or {}
        if a["origin"] == "generated" and not (plan.get("brief") or plan.get("prompt")):
            E(f"{where}: a generated asset needs plan.brief or plan.prompt (what the owner approves before it exists)")
        if a["origin"] in ("licensed", "footage") and not (a.get("license") or plan.get("license")):
            E(f"{where}: {a['origin']} needs a licence (license, or plan.license before it exists)")
        if stage == "verify":
            if not a.get("path"):
                E(f"{where}: planned but not added yet (set its path once the file exists)")
                continue
            try:
                resolve_inside(p.root if p else Path("."), a["path"], where, must_exist=True)
            except InputError as e:
                E(str(e))
            if a["origin"] == "generated" and not a.get("provenance"):
                E(f"{where}: a generated asset needs provenance (the story-art plan.md that records its prompt)")
            elif a["origin"] == "generated":
                try:
                    resolve_inside(p.root if p else Path("."), a["provenance"], f"{where} provenance", must_exist=True)
                except InputError as e:
                    E(str(e))
    # capture
    cap = piece["capture"]
    if cap["driver"] not in DRIVERS_FOR[piece["platform"]]:
        E(f"capture.driver {cap['driver']!r} does not fit platform {piece['platform']!r} "
          f"({', '.join(DRIVERS_FOR[piece['platform']])})")
    if cap["driver"] in ("web", "expo-web") and not (cap.get("path") or cap.get("page")):
        E("capture needs path (with a base URL) or page (a project HTML file)")
    if CAPABILITIES[cap["driver"]]["ceiling"] != "complete":
        W(f"capture.driver {cap['driver']}: {CAPABILITIES[cap['driver']]['ceiling']}; native motion is evidence-only in this release")
    return out


# ------------------------------------------------------------------ approval (Gate 3: the intent)

def _parts(piece: dict) -> dict:
    """Hashes of what the owner approves, in parts so a stale record can say what changed."""
    def scene_visual(s: dict) -> dict:
        return {"id": s["id"], "label": s.get("label"), "layout": s.get("layout"), "media": s.get("media"),
                "transition": (s.get("transitionIn") or {}).get("kind")}
    visual = {"platform": piece["platform"], "fidelity": piece["fidelity"], "viewports": piece["viewports"],
              "customViewports": piece.get("customViewports"), "scenes": [scene_visual(s) for s in piece["scenes"]],
              "reducedMotion": piece["reducedMotion"], "motionControl": piece["motionControl"],
              "resilience": piece["resilience"]}
    timing = {"loop": piece["loop"],
              "scenes": [{"id": s["id"], "durationMs": s["durationMs"], "holdMs": s.get("holdMs"),
                          "transitionMs": (s.get("transitionIn") or {}).get("durationMs")} for s in piece["scenes"]],
              "rows": piece["rows"], "tracks": piece.get("tracks"), "input": piece.get("input")}
    asset_plan = sorted(({"id": a["id"], "role": a["role"], "origin": a["origin"], "plan": a.get("plan")}
                         for a in piece.get("assets") or []), key=lambda x: x["id"])
    ref = piece.get("reference")
    reference = None if not ref else {k: ref.get(k) for k in ("sha256", "crop", "source", "license", "designedViewport", "offsetMs")}
    return {k: sha256_text(canonical(v)) for k, v in (("visual", visual), ("timing", timing), ("assetPlan", asset_plan),
                                                       ("reference", reference))}


PART_WORDS = {"visual": "scenes, layout, viewports, controls or reduced motion", "timing": "timing",
              "assetPlan": "the asset plan", "reference": "the reference"}


def piece_hashes(rel: str, piece: dict, g: dl.Gate) -> tuple[tuple[str, str], dict]:
    parts = _parts(piece)
    content = sha256_text(canonical({"path": rel, "parts": parts}))
    inputs = sha256_text(canonical({"concept": g.concept_rel, "hashes": list(g.concept or ())}))
    return (content, inputs), parts


@dataclass
class PieceGate:
    ok: bool
    problems: list[str]
    records: list[str]
    concept_gate: dl.Gate
    hashes: tuple[str, str] | None = None
    parts: dict | None = None


def gate_piece(p: dl.Project, pid: str) -> PieceGate:
    g = dl.gate(p, "motion")
    problems = list(g.problems)
    records = list(g.records)
    rel, piece = load_piece(p.root, pid)
    if not g.ok:
        return PieceGate(False, problems + [f"the motion spec {rel} can be approved once the motion concept is"], records, g)
    h, parts = piece_hashes(rel, piece, g)
    rec = dl._latest(p.approvals, gate="storyboard", family="motion", subject=rel)
    if rec is None:
        problems.append(f"the motion spec {rel} has no owner approval (Gate 3: review SPEC.md, then direction.py approve "
                        f"--gate storyboard --family motion --piece {pid})")
    elif (rec["hash"], rec["inputs"]) != h:
        if rec["hash"] != h[0]:
            changed = [k for k, v in parts.items() if (rec.get("parts") or {}).get(k) != v] or ["the spec"]
            what = " and ".join(PART_WORDS.get(c, c) for c in changed)
        else:
            what = "the motion concept or a value it resolves"
        problems.append(f"the motion spec approval {rec['id']} is stale: {what} changed since {rec['at']}")
    else:
        records.append(rec["id"])
    return PieceGate(not problems, problems, records, g, h, parts)


def approve_storyboard(p: dl.Project, pid: str, by: str, evidence: str, recorded_by: str) -> dict:
    g = dl.gate(p, "motion")
    if not g.ok:
        raise dl.GateError("approve the direction and the motion concept first: " + "; ".join(g.problems))
    rel, piece = load_piece(p.root, pid)
    resolved = dl.resolve_family(p, "motion", dl.load_concept(p, g.concept_rel))  # type: ignore[arg-type]
    lt = lint(p, rel, piece, resolved, "spec")
    if lt.errors:
        raise InputError(f"{rel} has problems to fix before it can be approved:\n  - " + "\n  - ".join(lt.errors))
    if piece.get("reference") and not piece["reference"].get("sha256"):
        raise InputError(f"{rel}: record the reference first (motion.py probe {pid} --record), so the approval names it")
    h, parts = piece_hashes(rel, piece, g)
    return dl.record_approval(p, "storyboard", rel, h, by, evidence, recorded_by, family="motion", extra={"parts": parts})


# ------------------------------------------------------------------ build fingerprint

def _glob_re(pattern: str) -> re.Pattern:
    """A path glob: ** spans folders, * and ? stay inside one segment."""
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
            continue
        if pattern.startswith("**", i):
            out += ".*"
            i += 2
            continue
        out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
        i += 1
    return re.compile(f"^{out}$")


def fingerprint_globs(root: Path, piece: dict) -> tuple[list[str], bool]:
    """(globs, partial): the piece's fingerprint.globs, or the folders of target.files plus the
    package manifests that exist. partial = nothing names the motion's code."""
    given = (piece.get("fingerprint") or {}).get("globs")
    if given:
        return list(given), False
    globs: list[str] = []
    for f in (piece.get("target") or {}).get("files") or []:
        parent = Path(f).parent.as_posix()
        globs.append(f if parent in ("", ".") else f"{parent}/**")
    page = (piece.get("capture") or {}).get("page")
    if page:
        parent = Path(page).parent.as_posix()
        globs.append(page if parent in ("", ".") else f"{parent}/**")
    partial = not globs
    globs += [m for m in MANIFESTS if (Path(root) / m).is_file()]
    return sorted(set(globs)), partial


def _project_files(root: Path) -> list[str]:
    root = Path(root)
    try:
        # paths come back relative to root, also when root is a folder inside a larger repository
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True,
                           timeout=60, check=False)
        if r.returncode == 0:
            return sorted(x for x in r.stdout.decode("utf-8", "replace").split("\0") if x)
    except (OSError, subprocess.TimeoutExpired):
        pass
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
        for f in files:
            out.append((Path(d) / f).relative_to(root).as_posix())
    return sorted(out)


_OWN = re.compile(rf"^(?:{re.escape(PIECES)}/[^/]+/(?:\.build|\.preview|out|reference)/|{re.escape(dl.RUNS)}/)")


def build_fingerprint(root: Path, piece: dict) -> dict:
    """The content of the project files the motion is made of: sha256 over (path, bytes with LF line
    endings) of every file a glob matches. Content, not commits: committing the verified work keeps
    it; editing a file it covers changes it."""
    globs, partial = fingerprint_globs(root, piece)
    pats = [_glob_re(g) for g in globs]
    entries = []
    for rel in _project_files(root):
        if _OWN.match(rel) or not any(pt.match(rel) for pt in pats):
            continue
        f = Path(root) / rel
        if not f.is_file():
            continue
        entries.append([rel, hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()])
    return {"kind": "content", "sha256": sha256_text(canonical(entries)), "files": len(entries), "globs": globs,
            "partial": partial or not entries}


def asset_files(root: Path, piece: dict) -> list[dict]:
    out = []
    for a in piece.get("assets") or []:
        if a.get("path"):
            f = resolve_inside(root, a["path"], f"asset {a['id']}", must_exist=True)
            entry = {"path": a["path"], "sha256": dl.asset_sha(f)}
            lic = a.get("license") or (a.get("plan") or {}).get("license")
            if lic:
                entry["license"] = lic[:200]
            out.append(entry)
    return sorted(out, key=lambda x: x["path"])


# ------------------------------------------------------------------ runs and reviews

def runs_dir(root: Path) -> Path:
    return Path(root) / RUNS_DIR


def review_hash(manifest: dict) -> str:
    """What a review acknowledgement binds to: the approved intent, the build, the target, the
    capture settings, the asset bytes, every deterministic output and the review items listed."""
    outputs = sorted((o["path"], o["sha256"]) for o in manifest["outputs"] if o.get("kind") != "evidence")
    return sha256_text(canonical({
        "piece": [manifest["piece"]["hash"], manifest["piece"]["inputs"]],
        "build": manifest.get("build"), "target": manifest.get("target"), "capture": manifest.get("captureConfig"),
        "assets": sorted((a["path"], a["sha256"]) for a in manifest["inputs"].get("assets") or []),
        "outputs": outputs, "reviews": sorted((r["id"], r["note"]) for r in manifest.get("reviews") or [])}))


def piece_runs(root: Path, pid: str) -> list[dict]:
    base = runs_dir(root)
    rel = piece_rel(pid)
    out = []
    for f in sorted(base.glob("*.json")) if base.is_dir() else []:
        m = load_json(f)
        if (m.get("piece") or {}).get("path") == rel:
            schema.check(m, "run-manifest", f"{RUNS_DIR}/{f.name}")
            out.append(m)
    return out


def acknowledged(p: dl.Project, manifest: dict) -> set[str]:
    h = review_hash(manifest)
    done: set[str] = set()
    for r in p.approvals:
        if r.get("gate") == "review" and r.get("family") == "motion" and r.get("hash") == h:
            done |= set(r.get("items") or [])
    return done


def approve_review(p: dl.Project, run: str, items: list[str], by: str, evidence: str, recorded_by: str) -> dict:
    f = runs_dir(p.root) / f"{run}.json"
    if not f.is_file():
        raise InputError(f"no motion run {run} under {RUNS_DIR}/")
    m = load_json(f)
    schema.check(m, "run-manifest", f.name)
    if m.get("completeness") != "complete":
        missing = "; ".join(f"{x['id']}: {x['reason']}" for x in m.get("missing") or []) or "required evidence is missing"
        raise InputError(f"run {run} is incomplete ({missing}); an incomplete run can't be reviewed. Fix what is "
                         "missing and verify again")
    ids = [r["id"] for r in m.get("reviews") or []]
    if not ids:
        raise InputError(f"run {run} has nothing to review")
    if items == ["all"]:
        items = ids
    unknown = sorted(set(items) - set(ids))
    if unknown:
        raise InputError(f"run {run} has no review item(s) {', '.join(unknown)} (it has: {', '.join(ids)})")
    h = (review_hash(m), sha256_text(canonical(sorted(items))))
    return dl.record_approval(p, "review", f"{RUNS_DIR}/{run}.json", h, by, evidence, recorded_by, family="motion",
                              extra={"run": run, "items": sorted(items)})


@dataclass
class PieceStatus:
    approved: bool
    verified: bool
    reviewed: bool
    run: str | None
    lines: list[str]


def piece_status(p: dl.Project, pid: str, pg: PieceGate | None = None) -> PieceStatus:
    """approved, verified and reviewed, each on its own line, with what keeps it from being true."""
    from .fsutil import sha256_file
    pg = pg or gate_piece(p, pid)
    lines = [f"{pid}: approved (Gate 3): " + ("yes" if pg.ok else "NO: " + "; ".join(pg.problems))]
    runs = piece_runs(p.root, pid)
    if not runs:
        lines.append(f"{pid}: verified: NO: no verify run yet")
        lines.append(f"{pid}: reviewed: NO: nothing to review")
        return PieceStatus(pg.ok, False, False, None, lines)
    m = runs[-1]
    why: list[str] = []
    if m.get("completeness") != "complete":
        why.append("the last run is incomplete (" + "; ".join(x["id"] for x in m.get("missing") or []) + ")")
    if pg.hashes is not None and (m["piece"]["hash"], m["piece"]["inputs"]) != tuple(pg.hashes):
        why.append("the run predates the current approved spec")
    _, piece = load_piece(p.root, pid)
    now_build = build_fingerprint(p.root, piece)
    if (m.get("build") or {}).get("sha256") != now_build["sha256"]:
        why.append("the app's code changed since the run (build fingerprint differs)")
    try:
        now_assets = asset_files(p.root, piece)
    except InputError as e:
        now_assets = []
        why.append(str(e))
    if sorted((a["path"], a["sha256"]) for a in now_assets) != sorted((a["path"], a["sha256"]) for a in m["inputs"].get("assets") or []):
        why.append("an asset changed since the run")
    for o in m["outputs"]:
        f = p.root / o["path"]
        if not f.is_file():
            why.append(f"{o['path']} is missing")
        elif sha256_file(f) != o["sha256"]:
            why.append(f"{o['path']} differs from the run's record")
    verified = pg.ok and not why
    lines.append(f"{pid}: verified: " + (f"yes (run {m['runId']})" if verified else f"NO (run {m['runId']}): " + "; ".join(why or ["not approved"])))
    done = acknowledged(p, m)
    open_ = [r for r in m.get("reviews") or [] if r["id"] not in done]
    reviewed = verified and not open_
    if reviewed:
        lines.append(f"{pid}: reviewed: yes" + (f" ({len(done)} item(s) acknowledged)" if done else " (nothing to review)"))
    else:
        lines.append(f"{pid}: reviewed: NO: " + ("verify first" if not verified else f"{len(open_)} review item(s) open"))
        if verified and open_:
            lines += [f"    - {r['id']}: {r['note']}" for r in open_]
            lines.append(f"  after the owner has looked: direction.py approve --gate review --run {m['runId']} --items <ids|all> "
                         "--by ... --evidence ...")
    return PieceStatus(pg.ok, verified, reviewed, m["runId"], lines)


# ------------------------------------------------------------------ signals from reference frames

def mad(a: bytes, b: bytes) -> float:
    return sum(abs(x - y) for x, y in zip(a, b)) / (len(a) or 1)


def frame_diffs(frames: list[bytes]) -> list[float]:
    """diffs[i] = mean absolute luma change from frame i to frame i + 1."""
    return [mad(frames[i], frames[i + 1]) for i in range(len(frames) - 1)]


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def cuts(diffs: list[float], times: list[float], window: int = 6, ratio: float = 4.0, floor: float = 6.0) -> list[dict]:
    """Frames where the picture jumps: a change at least `ratio` times the local median change
    (and above `floor` levels), larger than its neighbours. A signal for a person to check."""
    out = []
    for i, d in enumerate(diffs):
        lo, hi = max(0, i - window), min(len(diffs), i + window + 1)
        around = [diffs[j] for j in range(lo, hi) if j != i]
        base = max(_median(around), 0.25)
        if d >= floor and d >= ratio * base and d >= max(diffs[max(0, i - 1):i + 2]):
            out.append({"frame": i + 1, "ms": round(times[i + 1], 1), "change": round(d, 2), "strength": round(d / base, 1)})
    return out


def holds(diffs: list[float], times: list[float], still: float = 0.6, min_ms: float = 300) -> list[dict]:
    """Stretches where nothing visible moves (every change below `still` levels) for at least min_ms."""
    out, start = [], None
    for i, d in enumerate(diffs + [math.inf]):
        if d < still:
            if start is None:
                start = i
        else:
            if start is not None:
                a, b = times[start], times[min(i, len(times) - 1)]
                if b - a >= min_ms:
                    out.append({"fromMs": round(a, 1), "toMs": round(b, 1)})
            start = None
    return out


def loop_candidates(frames: list[bytes], times: list[float], min_overlap: int = 10, top: int = 3,
                    sample: int = 60) -> list[dict]:
    """Lags at which the recording repeats itself: for each lag L the mean change between frame i
    and frame i + L over the overlap (sampled), lowest first. A recording that holds one full loop
    and the start of the next shows the loop length as a low score."""
    n = len(frames)
    scores = []
    for lag in range(max(2, min_overlap), n - min_overlap + 1):
        overlap = n - lag
        step = max(1, overlap // sample)
        idx = range(0, overlap, step)
        s = sum(mad(frames[i], frames[i + lag]) for i in idx) / max(1, len(idx))
        scores.append((s, lag))
    if not scores:
        return []
    # keep local minima only, best first
    by_lag = {lag: s for s, lag in scores}
    minima = [(s, lag) for s, lag in scores if s <= by_lag.get(lag - 1, math.inf) and s <= by_lag.get(lag + 1, math.inf)]
    minima.sort()
    return [{"lagMs": round(times[lag] - times[0], 1), "lagFrames": lag, "score": round(s, 2)} for s, lag in minima[:top]]


def nearest_offsets(a: list[float], b: list[float]) -> list[dict]:
    """For each time in a, the nearest time in b and the offset (b - a)."""
    out = []
    for t in a:
        if not b:
            break
        m = min(b, key=lambda x: abs(x - t))
        out.append({"ms": round(t, 1), "nearest": round(m, 1), "offsetMs": round(m - t, 1)})
    return out


# ------------------------------------------------------------------ processes

class ProcessScope:
    """Every process a command starts is registered here and stopped when the scope ends: on
    success, on failure, on Ctrl-C, on SIGTERM/SIGBREAK and on --timeout. Only registered processes
    are stopped. $MOTION_PID_LOG (tests) receives one 'start <pid> <what>' / 'stop <pid>' line each."""

    def __init__(self, timeout_s: float | None = None) -> None:
        self.timeout_s = timeout_s
        self.procs: list[tuple[subprocess.Popen, str]] = []
        self.cleanups: list = []
        self.timed_out = False
        self._timer: threading.Timer | None = None
        self._old: dict = {}

    def _log(self, line: str) -> None:
        f = os.environ.get("MOTION_PID_LOG")
        if f:
            with open(f, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def adopt(self, proc: subprocess.Popen, what: str) -> subprocess.Popen:
        self.procs.append((proc, what))
        self._log(f"start {proc.pid} {what}")
        return proc

    def on_close(self, fn) -> None:
        self.cleanups.append(fn)

    def _raise(self, signum, frame):  # noqa: ARG002
        raise KeyboardInterrupt(f"signal {signum}")

    def _expire(self) -> None:
        import _thread
        self.timed_out = True
        _thread.interrupt_main()

    def __enter__(self) -> "ProcessScope":
        for name in ("SIGTERM", "SIGBREAK"):
            sig = getattr(signal, name, None)
            if sig is not None:
                try:
                    self._old[sig] = signal.signal(sig, self._raise)
                except (ValueError, OSError):
                    pass
        if self.timeout_s:
            self._timer = threading.Timer(self.timeout_s, self._expire)
            self._timer.daemon = True
            self._timer.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        if self._timer:
            self._timer.cancel()
        from . import browser
        for proc, _ in reversed(self.procs):
            if proc.poll() is None:
                browser.kill_group(proc)
                try:
                    proc.kill()
                    proc.wait(timeout=10)
                except Exception:  # noqa: BLE001
                    pass
            self._log(f"stop {proc.pid}")
        self.procs.clear()
        for fn in reversed(self.cleanups):
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass
        self.cleanups.clear()
        for sig, old in self._old.items():
            try:
                signal.signal(sig, old)
            except (ValueError, OSError):
                pass
        self._old.clear()
