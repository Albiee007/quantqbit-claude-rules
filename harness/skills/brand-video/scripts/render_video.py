#!/usr/bin/env python3
"""Render branded videos from the project's creative direction (HTML scenes -> frames -> ffmpeg).

A piece is brand/video/<id>/video.json: scenes (template, timing, on-screen copy, voice-over line).
The look and motion come from the selected video concept, so every frame uses the project's own
backgrounds, type, accents and motion tokens. The default output is a silent video plus a
voice-over script, a voice prompt and planned captions, so the owner can record or generate the
voice anywhere.

  init      write a starter brand/video/<id>/video.json (never overwrites)
  motion-tokens  suggest motion tokens (durations, easing) from the direction's mood; --write adds
            them to the token file (non-destructive, keeps a .bak)
  lint      check a piece: timing in whole frames, vocabulary against the concept, placeholder copy,
            reading time, voice-over fit, and the built page (animation length, no endless ones)
  voice     write the voice-over script, voice prompt and planned captions (a draft folder)
  preview   a draft: contact sheet of each scene's still frame, a half-size draft video (when
            ffmpeg is present) and the voice files, under .preview/<run>/; no approval needed
  render    production: needs the direction, the video concept and the storyboard approved; renders
            every frame, encodes, checks, writes the run manifest, then publishes to out/
  check     the technical checks on an encoded file (default: the published one)
  status    what is approved, what was published and which review items are still open

Usage:
  python render_video.py init launch-teaser [--title "Launch teaser"] [--project .]
  python render_video.py motion-tokens [--write]
  python render_video.py lint launch-teaser [--concept brand/concepts/video/<run>/a.json]
  python render_video.py preview launch-teaser [--concept <file>] [--frames-only]
  python render_video.py render launch-teaser [--check-only] [--determinism 6] [--no-contrast]
  python render_video.py status [launch-teaser]
Common: --project DIR, --chrome PATH, --ffmpeg PATH.
Exit codes: 0 done (the report may still list REVIEW REQUIRED items), 1 a check or gate failed,
2 bad arguments, a missing dependency (Chrome, ffmpeg, Pillow) or a browser/encoder failure.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    import harnesslib
    from harnesslib import browser, cdp, pagecheck, schema
    from harnesslib import contrast as con
    from harnesslib import direction as dl
    from harnesslib import dtcg
    from harnesslib import ffmpeg as ffm
    from harnesslib import video as vd
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import (DirLock, InputError, OperationalError, Publisher, UsageError, canonical,
                                   dumps_pretty, run_id, self_ignoring_dir, sha256_file, sha256_text,
                                   write_atomic)
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)

QUALITY = 92  # JPEG frames into the encoder (M0: indistinguishable from PNG after H.264, faster)


def root_of(a: argparse.Namespace) -> Path:
    r = Path(a.project).resolve()
    if not r.is_dir():
        raise UsageError(f"--project {a.project}: not a folder")
    return r


def need_pillow():
    try:
        from PIL import Image  # noqa: F401
        from harnesslib import framecheck, imaging
        return imaging, framecheck
    except ImportError:
        raise OperationalError("Pillow is required: pip install pillow") from None


# ------------------------------------------------------------------ init / motion tokens

STARTER = {
    "schemaVersion": 1, "kind": "social", "formats": ["social-9x16"], "fps": 30,
    "scenes": [
        {"id": "hook", "template": "title", "duration": 3, "copy": {"head": "REPLACE: the promise, in five words",
                                                                    "sub": "REPLACE: who it is for"},
         "vo": "REPLACE: the opening line, said the way a person would say it."},
        {"id": "how", "template": "feature", "duration": 4, "copy": {"head": "REPLACE: what it does",
                                                                     "points": ["REPLACE: one", "REPLACE: two"]},
         "vo": "REPLACE: how it helps, in one sentence."},
        {"id": "end", "template": "end-card", "duration": 3, "copy": {"head": "REPLACE: the call to action",
                                                                      "url": "REPLACE: example.com"},
         "vo": "REPLACE: the call to action."},
    ],
    "voice": {"language": "en"},
    "captions": {"sidecar": ["srt", "vtt"]},
}


def init(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel = vd.piece_rel(a.id)
    target = root / rel
    if target.exists():
        raise UsageError(f"{rel} exists; edit it instead (pieces are never overwritten)")
    doc = dict(STARTER, id=a.id, title=a.title or a.id.replace("-", " ").capitalize())
    schema.check(doc, "video", rel)
    write_atomic(target, dumps_pretty(doc))
    self_ignoring_dir(target.parent / ".build", "render_video.py builds")
    self_ignoring_dir(target.parent / ".preview", "render_video.py drafts")
    print(f"wrote {rel}: replace every REPLACE line, then: render_video.py lint {a.id}")
    return 0


def suggest_motion(direction: dict) -> dict:
    """Motion tokens from the mood axes, anchored to ui-ux references/motion.md. A starting point
    for the concept round, not a rule: the creative-director adjusts them."""
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


def motion_tokens(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = dl.load_project(root)
    add = suggest_motion(p.direction)
    print(json.dumps(add, indent=2))
    print("Reference them from a video concept: motion.durations {fast, base, slow} -> {motion.duration.*}, "
          "motion.easing {standard, enter, exit, emphasis} -> {motion.easing.*}")
    if not a.write:
        print("(suggestion only; --write adds them to the token file)")
        return 0
    tok = root / p.direction["tokens"]["source"]
    ok = dtcg.merge_file(tok, add, set(a.replace or []))
    return 0 if ok else 1


# ------------------------------------------------------------------ resolving a piece

class Job:
    """Everything one command needs about a piece: project, piece, concept look, plan."""

    def __init__(self, a: argparse.Namespace, production: bool, lock: bool = False, strict: bool | None = None) -> None:
        """strict: plan with production rules (vocabulary and placeholders are errors); default production."""
        self.root = root_of(a)
        self.lock = None
        rel = vd.piece_rel(a.id)  # validates the id before anything is created
        if not (self.root / rel).is_file():
            raise UsageError(f"{rel} not found (render_video.py init {a.id} starts one)")
        if lock:
            build = self_ignoring_dir(self.root / vd.PIECES / a.id / ".build", "render_video.py builds")
            self.lock = DirLock(build / "render.lock", f"video {a.id}")
            self.lock.__enter__()  # held before any input is read (released by close())
        try:
            self.p = dl.load_project(self.root)
            self.pid = a.id
            self.rel, self.piece = vd.load_piece(self.p, a.id)
            self.production = production
            if production:
                self.gate = vd.gate_piece(self.p, a.id)
            else:
                try:
                    self.gate = vd.gate_piece(self.p, a.id)
                except (InputError, TokenError) as e:  # a draft can still use another concept
                    g0 = dl.Gate(False, [str(e).splitlines()[0]], [])
                    self.gate = vd.PieceGate(False, [f"the approved video concept does not load: {str(e).splitlines()[0]}"], [], g0)
            if production:
                if not self.gate.ok:
                    raise dl.GateError(f"video production of {self.rel} needs owner approval:\n  - " +
                                       "\n  - ".join(self.gate.problems) + "\n  Render a draft with: render_video.py preview " + a.id)
                self.concept_rel = self.gate.concept_gate.concept_rel
                if self.piece.get("concept") and self.piece["concept"] != self.concept_rel:
                    print(f"note: {self.rel} names {self.piece['concept']} for drafts; production uses the approved "
                          f"{self.concept_rel}")
                concept = dl.load_concept(self.p, self.concept_rel)  # type: ignore[arg-type]
                self.ad = dl.resolve_family(self.p, "video", concept)
            else:
                rel = getattr(a, "concept", None) or self.piece.get("concept")
                self.concept_rel, _, self.ad = dl.preview(self.p, "video", rel)
            self.fmt = self.piece["formats"][0]
            self.plan = vd.plan(self.p, a.id, self.piece, self.ad, self.fmt, production if strict is None else strict)
            self.size = vd.FORMATS[self.fmt]["size"]
            self.dir = self.root / vd.PIECES / a.id
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        if self.lock is not None:
            self.lock.__exit__(None, None, None)
            self.lock = None


def report_plan(job: Job) -> int:
    pl = job.plan
    print(f"{job.rel}: {len(pl.scenes)} scene(s), {pl.frames} frames = {pl.seconds:.2f} s at {pl.fps} fps, {job.fmt}; "
          f"concept {job.concept_rel}")
    for s in pl.scenes:
        print(f"  {s.id:<14} {s.template:<9} frames {s.start}-{s.start + s.frames - 1} ({s.frames / pl.fps:.2f} s), "
              f"in: {s.transition}{f' {s.overlap}f' if s.overlap else ''}, still {s.hold_start}-{s.hold_end - 1}")
    for w in pl.warnings:
        print(f"WARN  {w}")
    for e in pl.errors:
        print(f"FAIL  {e}")
    for r in pl.reviews:
        print(f"REVIEW REQUIRED  {r['note']}")
    return len(pl.errors)


# ------------------------------------------------------------------ rendering

def runtime_js() -> str:
    return (vd.MEDIA / "timeline.js").read_text(encoding="utf-8")


def open_page(b: cdp.Browser, page_path: Path, size: tuple[int, int]) -> tuple[cdp.Page, dict]:
    page = b.new_page(size)
    page.block_network()
    page.add_init_script(runtime_js())
    page.navigate(page_path.resolve().as_uri())
    info = page.evaluate("window.__hf.ready()", timeout=60)
    if page.errors:
        raise InputError("the composition has script errors: " + "; ".join(page.errors[:3]))
    if page.blocked:
        raise InputError("the composition asked for network resources (blocked): " + ", ".join(page.blocked[:3]))
    return page, info


def page_problems(info: dict, pl: vd.Plan) -> list[str]:
    out = []
    if info["frames"] != pl.frames:
        out.append(f"the page says {info['frames']} frames, the plan {pl.frames}")
    if info.get("infinite"):
        out.append(f"{info['infinite']} animation(s) never end; a video needs finite animations")
    if info["animationEndMs"] > pl.frames * 1000 / pl.fps + 0.5:
        out.append(f"animations run to {info['animationEndMs']:.0f} ms, past the end of the video "
                   f"({pl.frames * 1000 / pl.fps:.0f} ms)")
    return out


def seek(page: cdp.Page, n: int, fps: int) -> None:
    page.evaluate(f"window.__hf.seek({n}/{fps})")


class Probe:
    """Contrast, glyph, clipping and safe-area findings for each scene's still frame."""

    def __init__(self, job: Job) -> None:
        self.job = job
        self.findings: list[con.Finding] = []
        self.text: list[str] = []
        self.reviews: list[dict] = []
        self.stills: dict[str, bytes] = {}

    def scene(self, page: cdp.Page, sc: vd.ScenePlan, check: bool) -> None:
        job = self.job
        w, h = job.size
        seek(page, sc.probe, job.plan.fps)
        self.stills[sc.id] = page.screenshot("png")
        if not check:
            return
        pr = json.loads(page.evaluate(f"JSON.stringify(ArtDir.probeData({w}, {h}))"))

        def backdrop():
            from PIL import Image
            import io
            page.evaluate("(() => { const s = document.createElement('style'); s.id = '__nocap'; "
                          "s.textContent = '.cap { visibility: hidden !important; }'; document.head.appendChild(s); })()")
            seek(page, sc.probe, job.plan.fps)
            png = page.screenshot("png")
            page.evaluate("document.getElementById('__nocap').remove()")
            seek(page, sc.probe, job.plan.fps)
            return Image.open(io.BytesIO(png)).convert("RGB")

        f, t = pagecheck.evaluate(pr, job.ad, f"scene {sc.id} @ frame {sc.probe}", backdrop)
        self.findings += f
        self.text += t
        for i, x in enumerate(f):
            if x.result == con.REVIEW:
                self.reviews.append({"id": f"contrast:{sc.id}:{i + 1}", "check": "contrast", "kind": "technical",
                                     "note": x.line().strip()[:600], "evidence": f"sheet: scene {sc.id}"})
        safe = vd.FORMATS[job.fmt]["safe"][job.ad.get("safeAreas", "standard")]
        outside = [r["text"] for r in pr["runs"] if any(
            rect[0] < safe["left"] - 0.5 or rect[1] < safe["top"] - 0.5 or rect[2] > w - safe["right"] + 0.5
            or rect[3] > h - safe["bottom"] + 0.5 for rect in r["rects"])]
        if outside:
            self.reviews.append({"id": f"safe-area:{sc.id}", "check": "safe area", "kind": "suitability",
                                 "note": f"scene {sc.id}: text inside the platforms' UI zones ({job.fmt}): "
                                         + ", ".join(repr(x) for x in outside[:4])[:500]})


def render_frames(job: Job, chrome: str, build: vd.Build, dest: Path | None, ff: str | None, profile: str,
                  step: int = 1, scale: float = 1.0, check: bool = True, determinism: int = 0) -> tuple[Probe, dict, int]:
    """Render the frames into ffmpeg (or only the scene stills when ff is None). Returns
    (probe findings, determinism report, frames written)."""
    pl = job.plan
    probe = Probe(job)
    det: dict = {}
    sample = sorted({min(pl.frames - 1, round(i * (pl.frames - 1) / max(1, determinism - 1))) for i in range(determinism)}) if determinism else []
    hashes: dict[int, str] = {}
    written = 0
    with cdp.Browser.launch(chrome, job.size) as b:
        page, info = open_page(b, build.page, job.size)
        probs = page_problems(info, pl)
        if probs:
            raise InputError("the built composition does not match its plan: " + "; ".join(probs))
        first = None
        if dest is not None and ff is not None:
            from harnesslib import framecheck
            sc0 = pl.scenes[0]
            seek(page, sc0.probe, pl.fps)  # reached again after the encode: history must not matter
            first = framecheck.pixel_hash(page.screenshot("png"))
            out_fps = f"{pl.fps}/{step}" if step > 1 else pl.fps  # exact rate, so drafts keep the planned timing
            with ffm.Encoder(ff, profile, dest, out_fps) as enc:
                for n in range(0, pl.frames, step):
                    seek(page, n, pl.fps)
                    enc.write(page.screenshot("jpeg", QUALITY, job.size, scale))
                    written += 1
                    if n in sample:
                        from harnesslib import framecheck
                        hashes[n] = framecheck.pixel_hash(page.screenshot("png"))
            if pl.frames > 600 and written:
                print(f"encoded {written} frames")
        for sc in pl.scenes:
            probe.scene(page, sc, check)
        if first is not None:
            from harnesslib import framecheck
            if framecheck.pixel_hash(probe.stills[pl.scenes[0].id]) != first:
                raise InputError(f"scene {pl.scenes[0].id}: its still frame changed when it was reached again after "
                                 "the whole video (something in the page depends on playback history)")
    if sample:
        from harnesslib import framecheck
        with cdp.Browser.launch(chrome, job.size) as b:
            page, _ = open_page(b, build.page, job.size)
            again = {}
            for n in reversed(sample):  # a fresh browser, reached in the opposite order
                seek(page, n, pl.fps)
                again[n] = framecheck.pixel_hash(page.screenshot("png"))
        det = {"frames": sample, "differ": [n for n in sample if again[n] != hashes.get(n)]}
    return probe, det, written


def sheet(job: Job, probe: Probe, dest: Path) -> Path:
    imaging, _ = need_pillow()
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for sc in job.plan.scenes:
            f = Path(tmp) / f"{sc.id}.png"
            f.write_bytes(probe.stills[sc.id])
            paths.append(f)
        return imaging.sheet(paths, dest, cols=min(4, len(paths)), width=270)


def flash_reviews(ff: str, path: Path, fps: int) -> tuple[dict, list[dict]]:
    _, framecheck = need_pillow()
    frames, _, _ = ffm.gray_frames(ff, path)
    hits = framecheck.flash_signal(frames, fps)
    if not hits:
        return {"result": "PASS", "detail": "no flashing found by the WCAG 2.3.1 heuristic (a signal, not a conformance claim)"}, []
    return ({"result": "REVIEW REQUIRED", "detail": f"possible flashing at {', '.join(f'{t:.1f} s' for t in hits)}"},
            [{"id": f"flash:{t:.1f}".replace(".", "-"), "check": "flashing", "kind": "technical",
              "note": f"more than three flashes within one second from {t:.1f} s (heuristic; WCAG 2.3.1)"} for t in hits])


# ------------------------------------------------------------------ commands

def lint(a: argparse.Namespace) -> int:
    job = Job(a, production=False, strict=True)
    errors = report_plan(job)
    _, cue_errors, cue_reviews = vd.cues(job.plan, job.piece, job.ad)
    for e in cue_errors:
        print(f"FAIL  {e}")
    for r in cue_reviews:
        print(f"REVIEW REQUIRED  {r['note']}")
    errors += len(cue_errors)
    g = job.gate
    print("gate: " + ("storyboard approved" if g.ok else "NOT MET: " + "; ".join(g.problems)))
    if not a.static and not errors:
        chrome = browser.find_chrome(a.chrome)
        with tempfile.TemporaryDirectory() as tmp:
            build = vd.compose(job.p, job.pid, job.piece, job.plan, job.ad, job.fmt, Path(tmp) / "build", draft=True)
            with cdp.Browser.launch(chrome, job.size) as b:
                page, info = open_page(b, build.page, job.size)
                probs = page_problems(info, job.plan)
                _, framecheck = need_pillow()
                sc = job.plan.scenes[0]
                seek(page, sc.probe, job.plan.fps)
                first = framecheck.pixel_hash(page.screenshot("png"))
                seek(page, job.plan.frames - 1, job.plan.fps)
                seek(page, sc.probe, job.plan.fps)
                if framecheck.pixel_hash(page.screenshot("png")) != first:
                    probs.append("a frame changed when it was reached a second time (something in the page "
                                 "depends on playback history)")
            for x in probs:
                print(f"FAIL  page: {x}")
            errors += len(probs)
            print(f"page: {info['animations']} animations, {info['clips']} clips, ends at {info['animationEndMs']:.0f} ms")
    print(f"lint: {errors} problem(s)")
    return 1 if errors else 0


def voice(a: argparse.Namespace) -> int:
    job = Job(a, production=False)
    out = Path(a.out) if a.out else self_ignoring_dir(job.dir / ".preview", "render_video.py drafts") / run_id() / "voice"
    base = out.parent if out.name == "voice" else out

    def write(rel: str, text: str) -> None:
        write_atomic(base / rel, text)

    cue_list, errors, reviews = vd.write_text_outputs(write, job.pid, job.piece, job.plan, job.ad, job.p.direction["mood"])
    for e in errors:
        print(f"FAIL  {e}")
    for r in reviews:
        print(f"REVIEW REQUIRED  {r['note']}")
    print(f"wrote the voice-over script, voice prompt and planned captions ({len(cue_list)} line(s)) to {base / 'voice'}")
    return 1 if errors else 0


def preview(a: argparse.Namespace) -> int:
    job = Job(a, production=False)
    errors = report_plan(job)
    if errors:
        print(f"preview: {errors} problem(s) to fix first")
        return 1
    chrome = browser.find_chrome(a.chrome)
    ff = None
    if not a.frames_only:
        try:
            ff, _ = ffm.find_ffmpeg(a.ffmpeg)
        except OperationalError as e:
            print(f"note: {e}; writing the stills only")
    out = Path(a.out) if a.out else self_ignoring_dir(job.dir / ".preview", "render_video.py drafts") / run_id()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        build = vd.compose(job.p, job.pid, job.piece, job.plan, job.ad, job.fmt, Path(tmp) / "build", draft=True)
        step = max(1, round(job.plan.fps / 15))  # about 15 fps; the encoder gets the exact rate fps/step
        probe, _, n = render_frames(job, chrome, build, out / "draft.mp4" if ff else None, ff, "h264-draft",
                                    step=step, scale=0.5, check=not a.no_contrast)
    sheet(job, probe, out / "sheet.png")

    def write(rel: str, text: str) -> None:
        write_atomic(out / rel, text)

    _, cue_errors, cue_reviews = vd.write_text_outputs(write, job.pid, job.piece, job.plan, job.ad, job.p.direction["mood"])
    for f in probe.findings:
        if f.result != con.PASS:
            print(f.line())
    for t in probe.text:
        print(f"FAIL  text: {t}")
    for r in probe.reviews + cue_reviews:
        print(f"REVIEW REQUIRED  {r['note']}")
    for e in cue_errors:
        print(f"FAIL  {e}")
    print(f"draft ({job.concept_rel}, NOT approved for production) in {out}: sheet.png"
          + (f", draft.mp4 ({n} frames at half size)" if ff else "") + ", voice/")
    return 1 if probe.text or cue_errors or any(f.result == con.FAIL for f in probe.findings) else 0


def render(a: argparse.Namespace) -> int:
    job = Job(a, production=True, lock=True)
    try:
        return _render(a, job)
    finally:
        job.close()


def _render(a: argparse.Namespace, job: Job) -> int:
    errors = report_plan(job)
    _, cue_errors, _ = vd.cues(job.plan, job.piece, job.ad)
    for e in cue_errors:
        print(f"FAIL  {e}")
    errors += len(cue_errors)
    print("gate: storyboard approved (" + ", ".join(job.gate.records) + ")")
    if a.check_only or errors:
        print(f"check-only: {errors} problem(s)" if a.check_only else f"render refused: {errors} problem(s)")
        return 1 if errors else 0
    need_pillow()
    chrome = browser.find_chrome(a.chrome)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    pl, fmt, pid = job.plan, job.fmt, job.pid
    started = dl.now_utc()
    rid = run_id()
    profile = vd.FORMATS[fmt]["profile"]
    build_dir = job.dir / ".build" / rid
    checks: dict[str, dict] = {}
    reviews = list(pl.reviews)
    try:
        build = vd.compose(job.p, pid, job.piece, pl, job.ad, fmt, build_dir, draft=False)
        # The gate again, now that fonts, logo and motif are copied: equal hashes prove the copies the
        # frames come from are the bytes that were approved (nothing changed between check and copy).
        if vd.gate_piece(job.p, pid).hashes != job.gate.hashes:
            raise InputError(f"{job.rel} or something it uses changed while the render was starting; run it again")
        with Publisher(job.dir / "out", f"video {pid}", run=rid) as pub:
            mp4_rel = f"{fmt}/{pid}.mp4"
            mp4 = pub.stage_path(mp4_rel)
            probe, det, written = render_frames(job, chrome, build, mp4, ff, profile, check=not a.no_contrast,
                                                determinism=a.determinism)
            info = ffm.probe(fp, mp4)
            tech = ffm.check_profile(info, mp4, profile, pl.frames, job.size, pl.fps)
            checks["technical"] = {"result": "FAIL" if tech else "PASS",
                                   "detail": "; ".join(tech) or f"{ffm.PROFILES[profile]['label']}, {pl.frames} frames"}
            fl, fl_reviews = flash_reviews(ff, mp4, pl.fps)
            checks["flashing"] = fl
            reviews += fl_reviews
            counts = con.summary(probe.findings)
            checks["contrast"] = ({"result": "SKIPPED", "detail": "--no-contrast"} if a.no_contrast else
                                  {"result": con.overall(counts), "detail": f"{len(probe.findings)} text runs at the scenes' still frames"})
            checks["text"] = {"result": "SKIPPED" if a.no_contrast else ("FAIL" if probe.text else "PASS"),
                              "detail": "; ".join(probe.text)[:2000] or "glyph coverage and clipping of every text run"}
            reviews += probe.reviews
            safe = [r for r in probe.reviews if r["check"] == "safe area"]
            if a.no_contrast:
                checks["safe-area"] = {"result": "SKIPPED", "detail": "--no-contrast"}
                reviews.append({"id": "skipped:contrast-text-safe-area", "check": "skipped checks", "kind": "technical",
                                "note": "contrast, glyph coverage and safe areas were not checked (--no-contrast); "
                                        "look at every scene's text before using the video"})
            else:
                checks["safe-area"] = {"result": "REVIEW REQUIRED" if safe else "PASS",
                                   "detail": f"{len(safe)} scene(s) with text in the platforms' UI zones" if safe else
                                   f"all text inside the {fmt} safe insets ({job.ad.get('safeAreas', 'standard')})"}
            if det:
                checks["determinism"] = {"result": "FAIL" if det["differ"] else "PASS",
                                         "detail": f"frames {det['frames']} re-rendered in a fresh browser"
                                                   + (f"; differ: {det['differ']}" if det["differ"] else "")}
            checks["audio"] = {"result": "SKIPPED", "detail": "silent video (the default); see voice/ for the script and prompt"}
            sheet(job, probe, pub.stage_path(f"{pid}-sheet.png"))

            def write(rel: str, text: str) -> None:
                write_atomic(pub.stage_path(rel), text)

            _, cue_errors, cue_reviews = vd.write_text_outputs(write, pid, job.piece, pl, job.ad, job.p.direction["mood"])
            reviews += cue_reviews
            if cue_errors:
                checks["voice-over"] = {"result": "FAIL", "detail": "; ".join(cue_errors)[:2000]}
            elif cue_reviews:
                checks["voice-over"] = {"result": "REVIEW REQUIRED", "detail": f"{len(cue_reviews)} line(s) longer than their scene"}
            else:
                checks["voice-over"] = {"result": "PASS", "detail": "the planned voice-over fits its scenes"}
            for f in probe.findings:
                if f.result != con.PASS:
                    print(f.line())
            for name, c in checks.items():
                print(f"{c['result']:<16} {name}: {c['detail']}")
            failed = [k for k, c in checks.items() if c["result"] == "FAIL"]
            if failed:
                print(f"published nothing: {', '.join(failed)} failed; out/ is untouched")
                return 1
            outputs = []
            for rel in pub.staged():
                f = pub.stage / rel
                entry = {"path": (Path(vd.PIECES) / pid / "out" / rel).as_posix(), "sha256": sha256_file(f),
                         "bytes": f.stat().st_size}
                if rel == mp4_rel:
                    s = [x for x in info["streams"] if x.get("codec_type") == "video"][0]
                    entry.update(size=list(job.size), profile=profile, durationS=round(pl.seconds, 6), fps=pl.fps,
                                 frames=pl.frames, codec=s.get("codec_name", ""), pixFmt=s.get("pix_fmt", ""), audio=False)
                outputs.append(entry)
            status = "review-required" if reviews or any(c["result"] in ("REVIEW REQUIRED",) for c in checks.values()) else "complete"
            manifest = {"schemaVersion": 1, "runId": rid, "family": "video", "mode": "production", "tool": "render_video.py",
                        "startedAt": started, "finishedAt": dl.now_utc(),
                        "engine": {"api": harnesslib.API_VERSION, "browser": browser.version(chrome), "renderer": "ours",
                                   "capture": "screenshot", "ffmpeg": ffm.version(ff)},
                        "inputs": {"config": sha256_text(canonical(job.piece)),
                                   "direction": job.gate.concept_gate.direction[0] if job.gate.concept_gate.direction else None,
                                   "concept": job.gate.concept_gate.concept[0] if job.gate.concept_gate.concept else None,
                                   "assets": [{"path": x["path"], "sha256": x["sha256"]} for x in build.assets]},
                        "approvals": job.gate.records + pl.exceptions,
                        "fonts": [{"family": f["family"], "source": f.get("source", "local"), "weight": f["weight"],
                                   "style": f["style"], **({"sha256": f["sha256"]} if "sha256" in f else {})}
                                  for f in job.ad["faces"]],
                        "seed": None, "outputs": outputs, "checks": checks, "status": status,
                        "piece": {"path": job.rel, "hash": job.gate.hashes[0], "inputs": job.gate.hashes[1],  # type: ignore[index]
                                  "formats": [fmt], "frames": pl.frames, "fps": pl.fps, "captions": "planned"},
                        "reviews": reviews}
            path = dl.write_run_manifest(job.root, manifest)  # first: an interrupted publish stays traceable
            pub.publish(prune=True)
        print(f"published {len(outputs)} file(s) to {(Path(vd.PIECES) / pid / 'out').as_posix()}; run manifest "
              f"{path.relative_to(job.root).as_posix()} ({status})")
        if reviews:
            done = vd.acknowledged(dl.load_project(job.root), manifest)
            open_ = [r["id"] for r in reviews if r["id"] not in done]
            if open_:
                print(f"not cleared for use yet: {len(open_)} review item(s) open; after the owner has looked: "
                      f"direction.py approve --gate review --run {rid} --items <ids|all> --by ... --evidence ...")
            else:
                print(f"cleared for use: the owner already acknowledged these {len(done)} review item(s) for identical outputs")
        return 0
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)


def check(a: argparse.Namespace) -> int:
    root = root_of(a)
    vd.piece_rel(a.id)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    if a.file:  # a file of your own: judged against the piece's current plan
        job = Job(a, production=False)
        f, profile = Path(a.file), vd.FORMATS[job.fmt]["profile"]
        frames, size, fps = job.plan.frames, job.size, job.plan.fps
    else:  # the published file: judged against the run that made it
        runs = vd.piece_runs(root, a.id)
        if not runs:
            raise UsageError(f"{a.id}: no production run yet (render first, or pass a file)")
        out = [o for o in runs[-1]["outputs"] if o.get("profile")]
        if not out:
            raise InputError(f"run {runs[-1]['runId']} records no video output")
        o = out[0]
        f, profile, frames, size, fps = root / o["path"], o["profile"], o["frames"], tuple(o["size"]), int(o["fps"])
    if not f.is_file():
        raise UsageError(f"{f}: no such file (render first, or pass the file)")
    problems = ffm.check_profile(ffm.probe(fp, f), f, profile, frames, size, fps)  # type: ignore[arg-type]
    print(("FAIL  " if problems else "PASS  ") + f"technical ({profile}): " + ("; ".join(problems) or "as specified"))
    fl, _ = flash_reviews(ff, f, fps)
    print(f"{fl['result']:<16} flashing: {fl['detail']}")
    return 1 if problems else 0


def status(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = dl.load_project(root)
    ids = [a.id] if a.id else vd.list_pieces(root)
    if not ids:
        print("no video pieces (render_video.py init <id>)")
        return 0
    ok = True
    for pid in ids:
        try:
            g = vd.gate_piece(p, pid)
        except (InputError, TokenError) as e:
            print(f"{pid}: storyboard NOT MET: {str(e).splitlines()[0]}")
            ok = False
            continue
        print(f"{pid}: storyboard " + ("approved" if g.ok else "NOT MET: " + "; ".join(g.problems)))
        st = vd.piece_status(p, pid, g.hashes if g.ok else None)
        for line in st.lines:
            print(line)
        ok = ok and g.ok and st.published and not st.outstanding
    return 0 if ok else 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="the project root (holds brand/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("id")
    i.add_argument("--title")
    mt = sub.add_parser("motion-tokens")
    mt.add_argument("--write", action="store_true")
    mt.add_argument("--replace", action="append", help="with --write: replace this existing token path")
    li = sub.add_parser("lint")
    li.add_argument("id")
    li.add_argument("--concept")
    li.add_argument("--static", action="store_true", help="skip the browser part")
    vo = sub.add_parser("voice")
    vo.add_argument("id")
    vo.add_argument("--concept")
    vo.add_argument("--out")
    pv = sub.add_parser("preview")
    pv.add_argument("id")
    pv.add_argument("--concept")
    pv.add_argument("--frames-only", action="store_true")
    pv.add_argument("--no-contrast", action="store_true")
    pv.add_argument("--out")
    rn = sub.add_parser("render")
    rn.add_argument("id")
    rn.add_argument("--check-only", action="store_true")
    rn.add_argument("--no-contrast", action="store_true")
    rn.add_argument("--determinism", type=int, default=0, metavar="K",
                    help="re-render K frames in a fresh browser and compare (same machine)")
    ck = sub.add_parser("check")
    ck.add_argument("id")
    ck.add_argument("file", nargs="?")
    st = sub.add_parser("status")
    st.add_argument("id", nargs="?")
    for p_ in (i, mt, li, vo, pv, rn, ck, st):
        p_.add_argument("--project", default=argparse.SUPPRESS, help="the project root (holds brand/)")
    for p_ in (li, pv, rn, ck):
        p_.add_argument("--chrome")
        p_.add_argument("--ffmpeg")
    a = ap.parse_args()
    for k in ("chrome", "ffmpeg"):
        if not hasattr(a, k):
            setattr(a, k, None)
    if getattr(a, "determinism", 0) and not 2 <= a.determinism <= 30:
        ap.error("--determinism takes 2-30 frames")
    handlers = {"init": init, "motion-tokens": motion_tokens, "lint": lint, "voice": voice, "preview": preview,
                "render": render, "check": check, "status": status}
    try:
        return handlers[a.cmd](a)
    except (UsageError, OperationalError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:  # a file held by another program (Windows), a full disk
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
