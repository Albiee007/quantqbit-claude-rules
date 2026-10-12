#!/usr/bin/env python3
"""Hero, cinematic and reference-driven UI motion: analyse a reference, specify, capture, verify.

A piece is brand/motion/<id>/motion.json: scenes, timed rows per track, viewports, the asset plan,
reduced-motion and control behaviour, and how to capture it. Its look comes from the selected
motion concept. The reference (a video or screen recording) is analysis material only: it lives in
brand/motion/<id>/reference/, which git ignores, and is never shipped.

  init      write a starter motion.json (never overwrites); --reference copies the file into the
            piece's ignored reference/ folder
  probe     reference metadata: size, rotation, frame rate, VFR, presentation timestamps, a crop
            suggestion; --record writes its hash and facts into motion.json
  frames    extract reference frames named by frame and time (--every MS, --at MS,MS, --all)
  sheet     labelled contact sheets of the extracted frames (or of a capture run); records what was
            presented. Sheets prove extraction, not review
  cuts      cut, hold and loop-length signals from the reference (for a person to check)
  inspect   record that a person reviewed a time range (the only writer of analysis.reviewed)
  tokens    suggest motion tokens from the direction's mood (--write adds them)
  lint      check a piece: timing, rows, mediums against the concept, assets, WCAG 2.2.2 controls
  spec      write SPEC.md, what the owner reads before approving the spec (Gate 3)
  capture   visual lane, draft: screenshots at spec times per viewport (no approval needed)
  check     behaviour lane, draft: real-time pause/stop/hide, hidden tab, WebGL loss, errors
  record    real-time recording (draft evidence): browser screencast, adb screenrecord or --file
  compare   reference frames next to captures at matched times, with signals (always REVIEW REQUIRED)
  verify    production: needs Gate 3 and every planned asset; runs both lanes, the recording and the
            comparison, writes the run manifest; publishes to out/ only when the run is complete
  status    approved, verified and reviewed, each with what keeps it from being true
  clean     delete the piece's .build and .preview folders (never reference/ or out/)

Usage:
  python motion.py init hero [--reference rec.mp4] [--platform web] [--project .]
  python motion.py probe hero [--record]
  python motion.py frames hero --every 250 | --at 0,4100 | --all [--crop x,y,w,h | --no-crop] [--scale 480]
  python motion.py sheet hero [--run <draft run>] [--cols 6] [--width 240]
  python motion.py cuts hero
  python motion.py inspect hero --range 4000-4500 --mode every-frame --by "Name" --note "title exit"
  python motion.py lint hero [--stage verify]
  python motion.py spec hero
  python motion.py capture hero [--viewport mobile] [--at 0,1200] [--reduced] [--determinism 3] [--base-url URL]
  python motion.py check hero [--viewport desktop] [--base-url URL]
  python motion.py record hero [--seconds 12] [--adb [--serial S] | --file F]
  python motion.py compare hero --run <draft run> | --frames DIR | --recording F
  python motion.py verify hero [--base-url URL] [--determinism 3] [--frames DIR] [--recording F] [--timeout 900]
  python motion.py status [hero]
Common: --project DIR, --chrome PATH, --ffmpeg PATH, --timeout SECONDS.
Exit codes: 0 done (a report may list REVIEW REQUIRED or SKIPPED), 1 a check, the lint or a gate failed (and an
incomplete verify run under CI=true), 2 bad arguments, a missing dependency, an unreachable URL or a browser,
ffmpeg or adb failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    import harnesslib
    from harnesslib import browser, cdp, dtcg, schema
    from harnesslib import direction as dl
    from harnesslib import ffmpeg as ffm
    from harnesslib import motion as mo
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import (DirLock, InputError, OperationalError, Publisher, UsageError, canonical, dumps_pretty,
                                   load_json, run_id, self_ignoring_dir, sha256_file, sha256_text, write_atomic)
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)

MANY_FRAMES = 1500


def root_of(a: argparse.Namespace) -> Path:
    r = Path(a.project).resolve()
    if not r.is_dir():
        raise UsageError(f"--project {a.project}: not a folder")
    return r


def need_pillow():
    try:
        from PIL import Image  # noqa: F401
        from harnesslib import framecheck, imaging, motioncap
        return imaging, framecheck, motioncap
    except ImportError:
        raise OperationalError("Pillow is required: pip install pillow") from None


def piece_dir(root: Path, pid: str) -> Path:
    mo.piece_rel(pid)
    return root / mo.PIECES / pid


def load(root: Path, pid: str) -> tuple[str, dict]:
    rel = mo.piece_rel(pid)
    if not (root / rel).is_file():
        raise UsageError(f"{rel} not found (motion.py init {pid} starts one)")
    return mo.load_piece(root, pid)


def save(root: Path, rel: str, piece: dict) -> None:
    schema.check(piece, "motion", rel)
    write_atomic(root / rel, dumps_pretty(piece))


def project(root: Path, required: bool = True) -> dl.Project | None:
    if not (root / dl.DIRECTION).is_file():
        if required:
            raise InputError(f"no {dl.DIRECTION}: the creative-director writes the direction first (creative-direction skill)")
        return None
    return dl.load_project(root)


def analysis_dir(root: Path, pid: str) -> Path:
    d = self_ignoring_dir(piece_dir(root, pid) / ".build", "motion.py working files") / "analysis"
    d.mkdir(parents=True, exist_ok=True)
    return d


def reference_file(root: Path, piece: dict, given: str | None) -> Path:
    if given:
        f = Path(given)
        if not f.is_file():
            raise UsageError(f"{given}: no such file")
        return f
    ref = piece.get("reference")
    if not ref:
        raise UsageError("the piece has no reference (motion.py init <id> --reference FILE, or set reference.path)")
    f = root / ref["path"]
    if not f.is_file():
        raise UsageError(f"{ref['path']} is not on this machine (references are git-ignored); copy it there first")
    return f


def parse_crop(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise UsageError(f"--crop {text!r}: give x,y,w,h in pixels") from None
    return {"x": x, "y": y, "w": w, "h": h}


def parse_ms_list(text: str | None) -> list[float]:
    if not text:
        return []
    try:
        return sorted({float(v) for v in text.split(",") if v.strip()})
    except ValueError:
        raise UsageError(f"{text!r}: give milliseconds separated by commas") from None


def ci() -> bool:
    return os.environ.get("CI", "").lower() in ("1", "true", "yes")


# ------------------------------------------------------------------ init

def starter(pid: str, title: str, platform: str) -> dict:
    driver = {"web": "web", "react-native": "expo-web", "android-compose": "frames", "ios": "file"}[platform]
    return {
        "schemaVersion": 1, "id": pid, "title": title, "platform": platform,
        "target": {"route": "/", "files": []},
        "reference": None,
        "fidelity": {"targets": ["composition", "motion"], "medium": "css" if platform == "web" else
                     {"react-native": "reanimated", "android-compose": "compose", "ios": "swiftui"}[platform],
                     "claim": "code-only", "limits": []},
        "viewports": ["desktop", "mobile"] if platform == "web" else ["mobile"],
        "loop": {"mode": "time-loop", "lengthMs": 6000, "repeat": "infinite", "autoplay": True},
        "scenes": [{"id": "s1", "label": "REPLACE: what the first scene shows", "durationMs": 3000, "holdMs": 600},
                   {"id": "s2", "label": "REPLACE: what the second scene shows", "durationMs": 3000, "holdMs": 600,
                    "transitionIn": {"kind": "crossfade", "durationMs": 400}}],
        "rows": [{"startMs": 0, "endMs": 3000, "scene": "s1", "track": "camera", "action": "REPLACE: what moves and how",
                  "easing": "linear", "confidence": "assumed"},
                 {"startMs": 3000, "endMs": 6000, "scene": "s2", "track": "camera", "action": "REPLACE: what moves and how",
                  "easing": "linear", "confidence": "assumed"}],
        "assets": [],
        "reducedMotion": {"strategy": "static-complete", "staticAt": {"scene": "s1", "ms": 1500}},
        "motionControl": {"kind": "pause", "selector": "REPLACE: the pause button, e.g. button[aria-label='Pause motion']"},
        "resilience": {"hiddenTab": "pause", "contextLoss": "n/a"},
        "capture": {"driver": driver, **({"path": "/"} if driver in ("web", "expo-web") else {}), "seekMode": "auto",
                    "ready": {"timeoutMs": 60000}},
        "analysis": {"extracted": [], "presented": [], "reviewed": [], "observations": [], "hypotheses": [],
                     "referenceTraits": [], "projectConstraints": []},
    }


def init(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel = mo.piece_rel(a.id)
    target = root / rel
    if target.exists():
        raise UsageError(f"{rel} exists; edit it instead (pieces are never overwritten)")
    doc = starter(a.id, a.title or a.id.replace("-", " ").capitalize(), a.platform)
    d = target.parent
    if a.reference:
        src = Path(a.reference)
        if not src.is_file():
            raise UsageError(f"--reference {a.reference}: no such file")
        refdir = self_ignoring_dir(d / "reference", "motion.py references: analysis material, never committed or shipped")
        dest = refdir / src.name
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        doc["reference"] = {"path": (Path(mo.PIECES) / a.id / "reference" / src.name).as_posix(),
                            "source": "REPLACE: where the reference came from (who supplied it, original URL)",
                            "license": "REPLACE: the permission to use it for analysis"}
    schema.check(doc, "motion", rel)
    write_atomic(target, dumps_pretty(doc))
    self_ignoring_dir(d / ".build", "motion.py working files")
    self_ignoring_dir(d / ".preview", "motion.py drafts")
    print(f"wrote {rel}: replace every REPLACE line" + (f", then: motion.py probe {a.id} --record" if a.reference else
                                                          f", then: motion.py lint {a.id}"))
    return 0


# ------------------------------------------------------------------ reference analysis

def probe(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel, piece = load(root, a.id)
    f = reference_file(root, piece, a.file)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    info = ffm.probe(fp, f)
    v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if not v:
        raise InputError(f"{f.name}: no video stream")
    s = v[0]
    times = ffm.frame_times(fp, f)
    counted = int(s.get("nb_read_frames") or 0)
    deltas = [b - c for c, b in zip(times, times[1:])]
    mean = sum(deltas) / len(deltas) if deltas else 0
    vfr = bool(deltas) and (max(deltas) - min(deltas) > max(0.002, mean * 0.1) or s.get("r_frame_rate") != s.get("avg_frame_rate"))
    rotation = 0
    for sd in s.get("side_data_list") or []:
        if "rotation" in sd:
            rotation = int(float(sd["rotation"]))
    rotation = rotation or int(float((s.get("tags") or {}).get("rotate", 0) or 0))
    crop = None
    try:
        r = subprocess.run([ff, "-hide_banner", "-t", "6", "-i", str(f), "-vf", "cropdetect=24:2:0", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=120, check=False)
        found = [ln.rsplit("crop=", 1)[1].split()[0] for ln in r.stderr.splitlines() if "crop=" in ln]
        if found:
            w, h, x, y = (int(z) for z in found[-1].split(":"))
            if (w, h) != (int(s["width"]), int(s["height"])):
                crop = {"x": x, "y": y, "w": w, "h": h}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    out = {"file": f.name, "sha256": sha256_file(f), "size": [int(s["width"]), int(s["height"])], "rotation": rotation,
           "codec": s.get("codec_name"), "fps": s.get("r_frame_rate"), "avgFps": s.get("avg_frame_rate"), "vfr": vfr,
           "durationS": round(times[-1] - times[0] + (mean or 0), 4) if times else float(info["format"].get("duration", 0)),
           "frames": len(times), "countedFrames": counted, "firstPtsS": times[0] if times else None,
           "cropSuggestion": crop, "frameTimesMs": [round(t * 1000, 3) for t in times]}
    write_atomic(analysis_dir(root, a.id) / "probe.json", dumps_pretty(out))
    print(f"{f.name}: {out['size'][0]}x{out['size'][1]}, {out['fps']} ({'VFR' if vfr else 'constant'}), {len(times)} frames, "
          f"{out['durationS']:.2f} s" + (f", rotated {rotation} deg" if rotation else ""))
    if counted and counted != len(times):
        print(f"WARN  ffprobe counted {counted} frames but listed {len(times)} timestamps; frame times come from the list")
    if vfr:
        print("note  variable frame rate: frames are named by presentation time, never index / fps")
    if crop:
        print(f"note  black borders: a crop of x={crop['x']} y={crop['y']} w={crop['w']} h={crop['h']} would remove them "
              "(app chrome needs your own crop: --crop on frames, reference.crop in the piece)")
    if a.record:
        ref = piece.get("reference")
        if not ref:
            raise UsageError("--record needs a reference in the piece (set reference.path, source and license)")
        if a.file and Path(a.file).resolve() != (root / ref["path"]).resolve():
            raise UsageError("--record records the piece's own reference.path, not --file")
        ref.update(sha256=out["sha256"], size=out["size"], fps=str(out["fps"])[:20], frames=len(times),
                   durationS=out["durationS"], vfr=vfr, rotation=rotation)
        save(root, rel, piece)
        print(f"recorded the reference in {rel} (sha256 {out['sha256'][:12]}...)")
    return 0


def _times_ms(root: Path, pid: str, piece: dict, f: Path, fp: str) -> list[float]:
    pj = analysis_dir(root, pid) / "probe.json"
    if pj.is_file():
        data = load_json(pj)
        if data.get("sha256") == sha256_file(f):
            return [float(t) for t in data["frameTimesMs"]]
    return [round(t * 1000, 3) for t in ffm.frame_times(fp, f)]


def _ranges(ms: list[float], all_ms: list[float], mode: str) -> dict:
    lo, hi = min(ms), max(ms)
    inside = [t for t in all_ms if lo <= t <= hi]
    every = len(set(ms)) >= len(inside)
    return {"fromMs": lo, "toMs": hi, "frames": len(set(ms)), "mode": "all" if every else mode}


def frames_cmd(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel, piece = load(root, a.id)
    f = reference_file(root, piece, None)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    times = _times_ms(root, a.id, piece, f, fp)
    if not times:
        raise InputError(f"{f.name}: no decodable frames")
    t0 = times[0]
    rel_t = [t - t0 for t in times]
    if a.all:
        idx = list(range(len(times)))
        mode = "all"
    elif a.every:
        want = [k * a.every for k in range(int(rel_t[-1] // a.every) + 1)]
        idx = sorted({min(range(len(rel_t)), key=lambda i: abs(rel_t[i] - w)) for w in want})
        mode = "every"
    elif a.at:
        idx = sorted({min(range(len(rel_t)), key=lambda i: abs(rel_t[i] - w)) for w in parse_ms_list(a.at)})
        mode = "at"
    else:
        raise UsageError("say which frames: --every MS, --at MS,MS or --all")
    if len(idx) > MANY_FRAMES:
        print(f"WARN  {len(idx)} frames: this takes disk space and time (motion.py clean {a.id} removes them)")
    crop = None if a.no_crop else (parse_crop(a.crop) or (piece.get("reference") or {}).get("crop"))
    dest = analysis_dir(root, a.id) / "frames"
    dest.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        written = []
        for k in range(0, len(idx), 400):  # bounded command lines
            chunk = idx[k:k + 400]
            sub = Path(tmp) / f"c{k}"
            files = ffm.extract_frames(ff, f, sub, chunk if not a.all else None, crop, a.scale)
            if a.all:
                files = files[:len(idx)]
                chunk = idx[:len(files)]
            if len(files) != len(chunk):
                raise InputError(f"asked for {len(chunk)} frames, ffmpeg wrote {len(files)}: the timestamp list and the "
                                 "decoder disagree (see motion.py probe)")
            for i, src in zip(chunk, files):
                out = dest / f"f{i:06d}-{rel_t[i]:09.1f}ms.png".replace(" ", "0")
                os.replace(src, out)
                written.append(out)
            if a.all:
                break
    piece.setdefault("analysis", {}).setdefault("extracted", []).append(
        {**_ranges([rel_t[i] for i in idx], rel_t, mode), **({"at": a.at[:40]} if a.at else {})})
    piece["analysis"]["extracted"] = piece["analysis"]["extracted"][-200:]
    save(root, rel, piece)
    print(f"{len(written)} frame(s) in {dest.relative_to(root).as_posix()}/ (named f<frame>-<ms>ms.png"
          + (f", cropped {crop['w']}x{crop['h']}" if crop else "") + ")")
    return 0


def _frame_files(d: Path) -> list[tuple[int, float, Path]]:
    out = []
    for p in sorted(d.glob("f*-*ms.png")):
        try:
            idx = int(p.name[1:7])
            ms = float(p.name.split("-", 1)[1][:-6])
        except ValueError:
            continue
        out.append((idx, ms, p))
    return out


def sheet_cmd(a: argparse.Namespace) -> int:
    imaging, _, _ = need_pillow()
    root = root_of(a)
    rel, piece = load(root, a.id)
    if a.run:
        base = piece_dir(root, a.id) / ".preview" / a.run / "captures"
        if not base.is_dir():
            raise UsageError(f"no captures for draft run {a.run} under .preview/")
        for vp in sorted(x for x in base.iterdir() if x.is_dir()):
            shots = sorted(vp.glob("t*.png"), key=lambda p: float(p.stem[1:]))
            dest = base.parent / "sheets" / f"{vp.name}.png"
            imaging.sheet(shots, dest, cols=a.cols, width=a.width, labels=[f"{vp.name} t={p.stem[1:]} ms" for p in shots])
            print(f"{dest.relative_to(root).as_posix()}: {len(shots)} capture(s)")
        return 0
    frames = _frame_files(analysis_dir(root, a.id) / "frames")
    if not frames:
        raise UsageError(f"no extracted frames yet (motion.py frames {a.id} --every 250)")
    sheets = analysis_dir(root, a.id) / "sheets"
    shutil.rmtree(sheets, ignore_errors=True)
    off = float((piece.get("reference") or {}).get("offsetMs") or 0)
    per = a.cols * a.rows
    pages = []
    for k in range(0, len(frames), per):
        chunk = frames[k:k + per]
        labels = []
        for idx, ms, _ in chunk:
            sc = mo.expected_scene(piece, ms - off) if ms >= off else None
            labels.append(f"f{idx} {ms / 1000:.3f}s" + (f" {sc}" if sc else ""))
        dest = sheets / f"sheet-{k // per + 1:02d}.png"
        imaging.sheet([p for _, _, p in chunk], dest, cols=a.cols, width=a.width, labels=labels)
        pages.append(dest)
    f = reference_file(root, piece, None)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    times = _times_ms(root, a.id, piece, f, fp)
    rel_all = [t - times[0] for t in times]
    shown = [ms for _, ms, _ in frames]
    coverage = {"frames": len(frames), "of": len(times), "pages": [p.name for p in pages],
                "range": [min(shown), max(shown)], "everyFrame": len(set(shown)) >= len([t for t in rel_all if min(shown) <= t <= max(shown)])}
    write_atomic(sheets / "coverage.json", dumps_pretty(coverage))
    piece.setdefault("analysis", {}).setdefault("presented", []).append(_ranges(shown, rel_all, "every"))
    piece["analysis"]["presented"] = piece["analysis"]["presented"][-200:]
    save(root, rel, piece)
    print(f"{len(pages)} sheet(s), {len(frames)} of {len(times)} frames, in {sheets.relative_to(root).as_posix()}/. "
          f"Sheets show frames; record what you actually reviewed with motion.py inspect.")
    return 0


def cuts_cmd(a: argparse.Namespace) -> int:
    root = root_of(a)
    _, piece = load(root, a.id)
    f = reference_file(root, piece, a.file)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    times = [t / 1000 for t in _times_ms(root, a.id, piece, f, fp)] if not a.file else ffm.frame_times(fp, f)
    crop = (piece.get("reference") or {}).get("crop") if not a.file else None
    gray, _, _ = ffm.gray_frames(ff, f, 64, passthrough=True, crop=crop)
    if len(gray) != len(times):
        print(f"WARN  decoded {len(gray)} frames for {len(times)} timestamps; using the first {min(len(gray), len(times))}")
    n = min(len(gray), len(times))
    gray, ms = gray[:n], [(t - times[0]) * 1000 for t in times[:n]]
    diffs = mo.frame_diffs(gray)
    cut_list = mo.cuts(diffs, ms)
    hold_list = mo.holds(diffs, ms)
    loops = mo.loop_candidates(gray, ms, min_overlap=max(10, n // 10))
    out = {"file": f.name, "frames": n, "cuts": cut_list, "holds": hold_list, "loopCandidates": loops,
           "note": "signals for a person to check against the frames, never a verdict"}
    d = analysis_dir(root, a.id)
    write_atomic(d / "cuts.json", dumps_pretty(out))
    write_atomic(d / "motion-energy.csv", "ms,change\n" + "".join(f"{ms[i + 1]:.1f},{x:.3f}\n" for i, x in enumerate(diffs)))
    print(f"{f.name}: {n} frames")
    for c in cut_list:
        print(f"  cut   at {c['ms']:>9.1f} ms (frame {c['frame']}): change {c['change']} ({c['strength']}x local)")
    for h in hold_list:
        print(f"  hold  {h['fromMs']:.0f}-{h['toMs']:.0f} ms")
    for lp in loops:
        print(f"  loop? repeats after {lp['lagMs']:.0f} ms (score {lp['score']}; lower = closer repeat)")
    print(f"signals only; check them against the sheets. Details: {(d / 'cuts.json').relative_to(root).as_posix()}")
    return 0


def inspect_cmd(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel, piece = load(root, a.id)
    try:
        lo, hi = (float(x) for x in a.range.split("-", 1))
    except ValueError:
        raise UsageError(f"--range {a.range!r}: give FROM-TO in ms, e.g. 4000-4500") from None
    if hi < lo:
        raise UsageError("--range: TO is before FROM")
    shown = (piece.get("analysis") or {}).get("presented") or []
    cover = [r for r in shown if r["fromMs"] <= lo and hi <= r["toMs"] and (a.mode == "sampled" or r.get("mode") == "all")]
    if not cover:
        need = "every frame of it presented (frames --all, then sheet)" if a.mode == "every-frame" else "frames presented on a sheet"
        raise InputError(f"{lo:g}-{hi:g} ms was not presented for review: it needs {need}. Presented: "
                         + (", ".join(f"{r['fromMs']:g}-{r['toMs']:g} ({r.get('mode')})" for r in shown) or "nothing yet"))
    piece["analysis"].setdefault("reviewed", []).append({"fromMs": lo, "toMs": hi, "mode": a.mode, "note": (a.note or "")[:400],
                                                        "by": a.by.strip()[:80], "at": dl.now_utc()})
    save(root, rel, piece)
    print(f"recorded: {a.by} reviewed {lo:g}-{hi:g} ms ({a.mode})")
    return 0


# ------------------------------------------------------------------ tokens, lint, spec, status

def tokens(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = project(root)
    add = mo.suggest_motion(p.direction)
    print(json.dumps(add, indent=2))
    print("Reference them from the motion concept: motion.durations {fast, base, slow, ...} -> {motion.duration.*}, "
          "motion.easing {standard, enter, exit, ...} -> {motion.easing.*}. Scene and camera timings that need their "
          "own names (motion.duration.scene, motion.easing.camera) are added by the creative-director.")
    if not a.write:
        print("(suggestion only; --write adds them to the token file)")
        return 0
    return 0 if dtcg.merge_file(root / p.direction["tokens"]["source"], add, set(a.replace or [])) else 1


def concept_for(p: dl.Project, piece: dict, production: bool) -> tuple[str | None, dict | None, str]:
    g = dl.gate(p, "motion")
    if g.ok:
        c = dl.load_concept(p, g.concept_rel)  # type: ignore[arg-type]
        return g.concept_rel, dl.resolve_family(p, "motion", c), "approved"
    if production:
        raise dl.GateError("motion production needs the approved motion concept:\n  - " + "\n  - ".join(g.problems))
    rel = piece.get("concept") or (p.direction["families"].get("motion") or {}).get("selected")
    if not rel:
        return None, None, "no motion concept yet (the creative-director requests the motion family)"
    _, c, r = dl.preview(p, "motion", rel)
    return rel, r, "DRAFT (not approved)"


PLACEHOLDER = "REPLACE"


def _placeholders(obj, path="$") -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k != "analysis":
                out += _placeholders(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _placeholders(v, f"{path}[{i}]")
    elif isinstance(obj, str) and PLACEHOLDER in obj:
        out.append(path)
    return out


def lint_piece(p: dl.Project | None, rel: str, piece: dict, stage: str, production: bool = False) -> tuple[mo.Lint, str, str | None]:
    resolved, crel, cstate = None, None, "no direction yet"
    if p is not None:
        crel, resolved, cstate = concept_for(p, piece, production)
    lt = mo.lint(p, rel, piece, resolved, stage)
    for ph in _placeholders(piece):
        lt.errors.append(f"{ph}: still says {PLACEHOLDER}")
    return lt, cstate, crel


def lint(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel, piece = load(root, a.id)
    p = project(root, required=False)
    lt, cstate, crel = lint_piece(p, rel, piece, a.stage)
    auto = mo.automatic_motion(piece)
    print(f"{rel}: {piece['platform']}, {len(piece['scenes'])} scene(s), {len(piece['rows'])} row(s), "
          f"{piece['loop']['mode']} {piece['loop']['lengthMs']} ms, viewports {', '.join(piece['viewports'])}; "
          f"concept {crel or '-'} ({cstate})")
    print("      automatic motion: " + ("none (starts on input)" if not auto["autoplay"] else
                                         ("repeats without end" if auto["totalMs"] == float("inf") else f"{auto['totalMs'] / 1000:g} s"))
          + (f"; control: {piece['motionControl']['kind']}" if auto["needsControl"] else ""))
    print(f"      capture: {piece['capture']['driver']} ({mo.CAPABILITIES[piece['capture']['driver']]['ceiling']})")
    for w in lt.warnings:
        print(f"WARN  {w}")
    for e in lt.errors:
        print(f"FAIL  {e}")
    for r in lt.reviews:
        print(f"REVIEW REQUIRED  {r['note']}")
    if p is not None and not lt.errors:
        try:
            pg = mo.gate_piece(p, a.id)
            print("gate: spec approved (Gate 3)" if pg.ok else "gate: " + "; ".join(pg.problems))
        except (InputError, TokenError) as e:
            print(f"gate: {str(e).splitlines()[0]}")
    return 1 if lt.errors else 0


def spec(a: argparse.Namespace) -> int:
    root = root_of(a)
    rel, piece = load(root, a.id)
    p = project(root, required=False)
    lt, cstate, crel = lint_piece(p, rel, piece, "spec")
    resolved = None
    if p is not None and crel:
        try:
            resolved = dl.resolve_family(p, "motion", dl.load_concept(p, crel))
        except (InputError, TokenError):
            resolved = None
    cap = mo.CAPABILITIES[piece["capture"]["driver"]]
    auto = mo.automatic_motion(piece)
    L = [f"# Motion spec: {piece.get('title') or piece['id']}", "",
         f"<!-- Generated from {rel} by motion.py spec. Edit the JSON, then re-run spec. -->", "",
         f"Platform **{piece['platform']}**, capture driver **{piece['capture']['driver']}** "
         f"(what a run can establish: {cap['ceiling']}).",
         f"Concept: `{crel or '-'}` ({cstate}).", ""]
    if lt.errors:
        L += ["## Problems to fix before approval", ""] + [f"- {e}" for e in lt.errors] + [""]
    fid = piece["fidelity"]
    L += ["## Fidelity", "", f"- Targets: {', '.join(fid['targets'])}", f"- Medium: {fid['medium']}",
          f"- What it is made of: {fid['claim']}"]
    L += [f"- Limit: {x}" for x in fid.get("limits") or []] + [""]
    ref = piece.get("reference")
    if ref:
        rv = (piece.get("analysis") or {}).get("reviewed") or []
        L += ["## Reference (analysis only, never shipped)", "", f"- Source: {ref['source']}", f"- Licence: {ref['license']}",
              f"- File: `{ref['path']}`" + (f", sha256 `{ref['sha256'][:16]}...`" if ref.get("sha256") else " (not recorded)"),
              f"- Designed viewport: {ref.get('designedViewport', '-')}" + (f", crop {ref['crop']}" if ref.get("crop") else ""),
              "- Reviewed by a person: " + ("; ".join(f"{r['fromMs']:g}-{r['toMs']:g} ms {r['mode']} ({r['by']})" for r in rv) or "nothing recorded"),
              ""]
    L += ["## Viewports", "", "| Viewport | Size | DPR |", "|---|---|---|"]
    for name in piece["viewports"]:
        v = mo.viewport_spec(piece, name)
        L.append(f"| {name} | {v['size'][0]}x{v['size'][1]} | {v['dpr']:g} |")
    L += ["", "## Timeline", "", f"{piece['loop']['mode']}, {piece['loop']['lengthMs']} ms"
          + (f", repeat {piece['loop'].get('repeat', 'infinite')}" if piece['loop']['mode'] == 'time-loop' else ""), "",
          "| Scene | From | To | Hold | In | Media | Label |", "|---|---|---|---|---|---|---|"]
    for (sid, s0, s1), sc in zip(mo.scene_spans(piece), piece["scenes"]):
        tr = sc.get("transitionIn") or {}
        L.append(f"| {sid} | {s0:g} | {s1:g} | {sc.get('holdMs', 0)} | {tr.get('kind', '-')}"
                 f"{' ' + str(tr.get('durationMs')) + ' ms' if tr.get('durationMs') else ''} | {', '.join(sc.get('media') or []) or '-'} | {sc.get('label', '')} |")
    L += ["", "| From | To | Scene | Track | Action | Easing | Confidence |", "|---|---|---|---|---|---|---|"]
    for r in piece["rows"]:
        L.append(f"| {r['startMs']:g} | {r['endMs']:g} | {r.get('scene', '-')} | {r['track']} | {r['action']} | "
                 f"{r.get('easing', '-')} | {r['confidence']} |")
    if resolved:
        L += ["", "Motion tokens from the concept: " + ", ".join(f"{k} {v['ms']} ms" for k, v in resolved["motion"]["durations"].items())
              + "; easing " + ", ".join(f"{k} {v['css']}" for k, v in resolved["motion"]["easing"].items())]
    L += ["", "## Assets (approved as a plan; the files bind at review)", ""]
    if piece.get("assets"):
        L += ["| Asset | Role | Origin | Plan | File |", "|---|---|---|---|---|"]
        for x in piece["assets"]:
            pl = x.get("plan") or {}
            L.append(f"| {x['id']} | {x['role']} | {x['origin']} | {(pl.get('brief') or pl.get('prompt') or pl.get('source') or '-')[:120]} | "
                     f"{x.get('path', 'not yet')} |")
    else:
        L.append("None: the motion is drawn in code.")
    ctl = piece["motionControl"]
    L += ["", "## People and resilience", "",
          "- Automatic motion: " + ("none (starts on input)" if not auto["autoplay"] else
                                    ("repeats without end" if auto["totalMs"] == float("inf") else f"{auto['totalMs'] / 1000:g} s")),
          f"- Control: {ctl['kind']}" + (f" (`{ctl['selector']}`)" if ctl.get("selector") else "")
          + (f"; essential because: {ctl['essentialJustification']}" if ctl.get("essentialJustification") else ""),
          f"- Reduced motion: {piece['reducedMotion']['strategy']}"
          + (f" at {piece['reducedMotion']['staticAt']['scene']}" if piece["reducedMotion"].get("staticAt") else ""),
          f"- Hidden tab: {piece['resilience']['hiddenTab']}; fallback: {piece['resilience'].get('fallback', '-')}; "
          f"WebGL context loss: {piece['resilience'].get('contextLoss', 'n/a')}", ""]
    sheets = analysis_dir(root, a.id) / "sheets"
    if sheets.is_dir():
        L += ["## Reference sheets", ""] + [f"- `{x.relative_to(root).as_posix()}`" for x in sorted(sheets.glob("*.png"))] + [""]
    L += ["## Approval", "", "After the owner has read this and decided:",
          f"`direction.py approve --gate storyboard --family motion --piece {piece['id']} --by \"<owner>\" --evidence \"<where they said so>\"`", ""]
    out = piece_dir(root, a.id) / "SPEC.md"
    write_atomic(out, "\n".join(L))
    print(f"wrote {out.relative_to(root).as_posix()}" + (f" ({len(lt.errors)} problem(s) listed)" if lt.errors else ""))
    return 1 if lt.errors else 0


def status(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = project(root)
    ids = [a.id] if a.id else mo.list_pieces(root)
    if not ids:
        print("no motion pieces (motion.py init <id>)")
        return 0
    ok = True
    for pid in ids:
        try:
            st = mo.piece_status(p, pid)
        except (InputError, TokenError) as e:
            print(f"{pid}: NOT MET: {str(e).splitlines()[0]}")
            ok = False
            continue
        for line in st.lines:
            print(line)
        ok = ok and st.reviewed
    return 0 if ok else 1


# ------------------------------------------------------------------ capture lanes

class Ctx:
    """One capture command: project, piece, target, tools and the process scope."""

    def __init__(self, a: argparse.Namespace, production: bool) -> None:
        self.a = a
        self.root = root_of(a)
        self.rel, self.piece = load(self.root, a.id)
        self.pid = a.id
        self.dir = piece_dir(self.root, a.id)
        self.production = production
        self.driver = self.piece["capture"]["driver"]
        self.cap = mo.CAPABILITIES[self.driver]
        self.target = None
        self.chrome = None

    def web(self) -> None:
        from harnesslib import motioncap as mc
        self.target = mc.resolve_target(self.root, self.piece, mc.base_url(self.a.base_url, self.root))
        mc.check_reachable(self.target)
        self.chrome = browser.find_chrome(self.a.chrome)

    def viewports(self) -> list[dict]:
        names = self.piece["viewports"]
        only = getattr(self.a, "viewport", None)
        if only:
            if only not in names:
                raise UsageError(f"--viewport {only}: the piece's viewports are {', '.join(names)}")
            names = [only]
        return [mo.viewport_spec(self.piece, n) for n in names]

    def record_viewport(self) -> dict:
        p = self.piece
        name = getattr(self.a, "viewport", None) or p["capture"].get("recordViewport") or \
            (p.get("reference") or {}).get("designedViewport") or p["viewports"][0]
        return mo.viewport_spec(p, name)


def visual_lane(ctx: Ctx, scope: mo.ProcessScope, out: Path, checks: dict, reviews: list, meta: dict,
                times: list[float] | None = None, determinism: int = 0) -> dict:
    """Screenshots at spec times per viewport, page facts, the reduced-motion frame, determinism."""
    _, _, mc = need_pillow()
    piece = ctx.piece
    times = times or mo.capture_times(piece)
    seq = sorted((piece.get("input") or {}).get("sequence") or [], key=lambda x: x["atMs"])
    # page facts (essential elements, overflow, invisible focus) where a scene has settled: the
    # capture nearest each scene's middle (titles that fade in are not missing at a scene's start)
    mids = [(s0 + s1) / 2 for _, s0, s1 in mo.scene_spans(piece)] if piece["loop"]["mode"] != "interaction" else [times[-1]]
    fact_times = {min(times, key=lambda t: abs(t - m)) for m in mids}
    modes, shots_by_vp, first = {}, {}, None
    scene_bad, missing_ess, overflow, hidden_focus, uncontrolled, blocked, exc, cons = [], [], [], set(), {}, set(), [], []
    for vp in ctx.viewports():
        v = mc.open_visual(ctx.chrome, piece, vp, ctx.target, scope)
        modes[vp["name"]] = {"mode": v.mode, "bootSteps": v.boot_steps}
        shots = {}
        for t in times:
            png, st = mc.capture_at(v, piece, t, seq)
            rel = f"captures/{vp['name']}/t{t:g}.png"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            (out / rel).write_bytes(png)
            meta[rel] = {"viewport": vp["name"], "atMs": t, "size": [vp["size"][0] * vp["dpr"], vp["size"][1] * vp["dpr"]]}
            shots[t] = png
            want = mo.expected_scene(piece, t)
            if st and st.get("sceneId") and want and st["sceneId"] != want:
                scene_bad.append(f"{vp['name']} t={t:g}: the app shows {st['sceneId']}, the spec {want}")
            if t in fact_times:
                facts = mc.page_facts(v.page, piece, vp)
                missing_ess += [f"{vp['name']} t={t:g}: {s}" for s in facts["missing"]]
                if facts["overflow"]:
                    overflow.append(f"{vp['name']}: content {facts['overflow']} px wide in a {vp['size'][0]} px viewport")
                hidden_focus |= set(facts["hiddenFocus"])
        if v.mode == "virtual-clock":
            info = v.page.evaluate("JSON.stringify(window.__motionClock.info())")
            for k, n in (json.loads(info).get("uncontrolled") or {}).items():
                uncontrolled[k] = max(uncontrolled.get(k, 0), n)
        blocked |= set(v.page.blocked)
        exc += v.page.exceptions
        cons += v.page.console_errors
        scene_bad += v.problems
        shots_by_vp[vp["name"]] = shots
        first = first or (vp, shots)
        v.close()
    # sheets
    imaging, _, _ = need_pillow()
    for name, shots in shots_by_vp.items():
        ordered = sorted(shots)
        rel = f"sheets/{name}.png"
        imaging.sheet([out / f"captures/{name}/t{t:g}.png" for t in ordered], out / rel, cols=4, width=320,
                      labels=[f"{name} t={t:g} ms {mo.expected_scene(piece, t) or ''}" for t in ordered])
        meta[rel] = {"viewport": name}
    mode_names = sorted({m["mode"] for m in modes.values()})
    checks["visual"] = {"result": "PASS", "detail": f"{sum(len(s) for s in shots_by_vp.values())} capture(s), "
                        f"{len(times)} time(s) x {len(shots_by_vp)} viewport(s), {', '.join(mode_names)}; boot steps "
                        + ", ".join(f"{k} {m['bootSteps']}" for k, m in modes.items())}
    checks["scenes"] = ({"result": "FAIL", "detail": "; ".join(scene_bad)[:2000]} if scene_bad else
                        {"result": "PASS", "detail": "window.__motion.state() matched the spec's scene at every capture"}
                        if any(m["mode"] == "app-seek" for m in modes.values()) else
                        {"result": "SKIPPED", "detail": "no window.__motion.state() to read the scene from; compare the sheets"})
    checks["essential"] = ({"result": "FAIL", "detail": "not visible: " + "; ".join(missing_ess)[:1900]} if missing_ess else
                           {"result": "PASS", "detail": f"{len(piece['capture'].get('essential') or [])} essential element(s) visible"}
                           if piece["capture"].get("essential") else {"result": "SKIPPED", "detail": "capture.essential lists nothing"})
    checks["overflow"] = {"result": "FAIL", "detail": "; ".join(overflow)} if overflow else {"result": "PASS", "detail": "no horizontal overflow on mobile viewports"}
    if hidden_focus:
        checks["hidden-focus"] = {"result": "REVIEW REQUIRED", "detail": "focusable but invisible: " + "; ".join(sorted(hidden_focus))[:1900]}
        reviews.append({"id": "hidden-focus", "check": "invisible focus", "kind": "technical",
                        "note": "focusable elements are invisible (opacity 0 or hidden) but still take focus: "
                                + "; ".join(sorted(hidden_focus))[:400] + ". Make them inert or remove them while hidden"})
    else:
        checks["hidden-focus"] = {"result": "PASS", "detail": "no invisible element takes focus"}
    if uncontrolled:
        checks["clock-sources"] = {"result": "REVIEW REQUIRED", "detail": f"not on the virtual clock: {uncontrolled}"}
        reviews.append({"id": "clock-sources", "check": "uncontrolled time", "kind": "technical",
                        "note": f"the page uses time sources the capture cannot hold still ({', '.join(uncontrolled)}); "
                                "their frames may differ from run to run"})
    if blocked:
        checks["network"] = {"result": "REVIEW REQUIRED", "detail": "blocked: " + ", ".join(sorted(blocked))[:1900]}
        reviews.append({"id": "blocked-requests", "check": "network", "kind": "technical",
                        "note": f"the page asked for {len(blocked)} other origin(s), blocked during capture: "
                                + ", ".join(sorted(blocked))[:300] + ". Allow them in capture.allowOrigins or remove them"})
    if exc:
        checks["page-errors"] = {"result": "FAIL", "detail": "; ".join(dict.fromkeys(exc))[:2000]}
    if cons:
        reviews.append({"id": "console-errors", "check": "console", "kind": "technical",
                        "note": "console errors during capture: " + "; ".join(dict.fromkeys(cons))[:400]})
    # loop seam (time loops): the frame at the loop's end should be the opening frame again
    if piece["loop"]["mode"] == "time-loop" and first:
        vp, shots = first
        a0, aL = shots.get(0.0), shots.get(float(piece["loop"]["lengthMs"]))
        if a0 is not None and aL is not None:
            how = mc.same(a0, aL)
            if how == "different":
                checks["loop-seam"] = {"result": "REVIEW REQUIRED", "detail": f"{vp['name']}: the frame at {piece['loop']['lengthMs']} ms differs from 0 ms"}
                reviews.append({"id": "loop-seam", "check": "loop seam", "kind": "content",
                                "note": f"the loop does not return to its opening frame at {piece['loop']['lengthMs']} ms "
                                        "(a visible seam or drift); intended?"})
            else:
                checks["loop-seam"] = {"result": "PASS", "detail": f"{vp['name']}: the loop returns to its opening frame ({how})"}
    # determinism: a fresh browser, same times
    if determinism and first:
        vp, shots = first
        pick = [t for t in sorted(shots)][:: max(1, len(shots) // determinism)][:determinism]
        v = mc.open_visual(ctx.chrome, piece, vp, ctx.target, scope)
        verdicts = []
        for t in pick:
            png, _ = mc.capture_at(v, piece, t, seq)
            verdicts.append((t, mc.same(shots[t], png)))
        v.close()
        bad = [f"t={t:g}" for t, how in verdicts if how == "different"]
        near = [f"t={t:g}" for t, how in verdicts if how == "near-identical"]
        checks["determinism"] = {"result": "FAIL" if bad else "PASS",
                                 "detail": (f"differ in a fresh browser at {', '.join(bad)}" if bad else
                                            f"{len(pick)} time(s) re-captured in a fresh browser: identical"
                                            + (f" (rasterisation noise only at {', '.join(near)})" if near else ""))}
    return {"modes": modes, "times": times}


def reduced_lane(ctx: Ctx, scope: mo.ProcessScope, out: Path, checks: dict, reviews: list, meta: dict) -> None:
    _, _, mc = need_pillow()
    piece = ctx.piece
    st = piece["reducedMotion"]
    at = float((st.get("staticAt") or {}).get("ms", 0))
    problems, notes = [], []
    for vp in ctx.viewports():
        v = mc.open_visual(ctx.chrome, piece, vp, ctx.target, scope, reduced=True, force_virtual=True)
        a, _ = mc.capture_at(v, piece, at)
        b, _ = mc.capture_at(v, piece, at + 2500)
        facts = mc.page_facts(v.page, piece, vp)
        v.close()
        rel = f"reduced/{vp['name']}.png"
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(a)
        meta[rel] = {"viewport": vp["name"]}
        how = mc.same(a, b)
        if st["strategy"] == "static-complete" and how == "different":
            problems.append(f"{vp['name']}: the page still moves with reduced motion on (frames {at:g} and {at + 2500:g} ms differ)")
        notes.append(f"{vp['name']} {how}")
        if facts["missing"]:
            problems.append(f"{vp['name']}: essential elements not visible with reduced motion: {', '.join(facts['missing'])}")
    if problems:
        checks["reduced-motion"] = {"result": "FAIL", "detail": "; ".join(problems)[:2000]}
    elif st["strategy"] == "static-complete":
        checks["reduced-motion"] = {"result": "PASS", "detail": "static and complete over 2.5 s: " + ", ".join(notes)}
    else:
        checks["reduced-motion"] = {"result": "REVIEW REQUIRED", "detail": f"strategy {st['strategy']}: frames captured; judge them by eye"}
        reviews.append({"id": "reduced-motion", "check": "reduced motion", "kind": "suitability",
                        "note": f"reduced motion keeps some motion ({st['strategy']}); look at reduced/ and confirm it is gentle enough"})


def behaviour_lane(ctx: Ctx, scope: mo.ProcessScope, checks: dict, reviews: list, omitted: list) -> None:
    """Real time, no virtual clock: the app's own controls, a really hidden tab, WebGL loss."""
    _, _, mc = need_pillow()
    piece = ctx.piece
    vp = ctx.record_viewport()
    live = mc.open_live(ctx.chrome, piece, vp, ctx.target, scope)
    try:
        if piece["motionControl"]["kind"] != "none":
            checks["control"] = mc.check_control(live, piece)
        else:
            checks["control"] = {"result": "SKIPPED", "detail": "motionControl.kind none"}
            if mo.automatic_motion(piece)["needsControl"]:
                omitted.append({"id": "control", "reason": "no control; the spec's essential justification is a review item"})
        checks["hidden-tab"] = mc.check_hidden_tab(live, piece)
        if checks["hidden-tab"]["result"] == "SKIPPED":
            omitted.append({"id": "hidden-tab", "reason": checks["hidden-tab"]["detail"]})
            reviews.append({"id": "hidden-tab", "check": "hidden tab", "kind": "technical",
                            "note": "the browser could not hide the tab; switch tabs by hand and check the motion does not jump"})
        elif checks["hidden-tab"]["result"] == "REVIEW REQUIRED":
            reviews.append({"id": "hidden-tab", "check": "hidden tab", "kind": "technical", "note": checks["hidden-tab"]["detail"]})
        if piece["capture"].get("webgl"):
            checks["context-loss"] = mc.check_context_loss(live)
            if checks["context-loss"]["result"] == "REVIEW REQUIRED":
                reviews.append({"id": "context-loss", "check": "WebGL context loss", "kind": "technical",
                                "note": checks["context-loss"]["detail"]})
        if piece["loop"]["mode"] == "interaction":
            for act in sorted(piece["input"]["sequence"], key=lambda x: x["atMs"]):
                mc._do_input(live.page, act)
                live.page.pump(0.3)
            checks["input-replay"] = {"result": "PASS", "detail": f"{len(piece['input']['sequence'])} input step(s) replayed in real time"}
        if live.page.exceptions:
            prev = checks.get("page-errors", {}).get("detail", "")
            checks["page-errors"] = {"result": "FAIL", "detail": (prev + "; " if prev else "") + "; ".join(dict.fromkeys(live.page.exceptions))[:1500]}
        checks.setdefault("page-errors", {"result": "PASS", "detail": "no uncaught exceptions"})
    finally:
        live.browser.close()


def record_lane(ctx: Ctx, scope: mo.ProcessScope, out: Path, ff: str, seconds: float | None, meta: dict) -> dict:
    _, _, mc = need_pillow()
    piece = ctx.piece
    vp = ctx.record_viewport()
    length = piece["loop"]["lengthMs"] / 1000
    secs = seconds or min(60.0, length * 1.25 + 1.0)
    live = mc.open_live(ctx.chrome, piece, vp, ctx.target, scope)
    rel = f"recording/{vp['name']}.mp4"
    try:
        stats = mc.record(live, secs, ff, out / rel)
    finally:
        live.browser.close()
    meta[rel] = {"viewport": vp["name"], "kind": "evidence", "fps": stats["fps"], "frames": stats["encodedFrames"]}
    return {"viewport": vp["name"], "path": rel, **stats}


def flash_checks(ff: str, mp4: Path, checks: dict, reviews: list) -> dict:
    _, framecheck, _ = need_pillow()
    gray, _, _ = ffm.gray_frames(ff, mp4)
    wcag = framecheck.flash_signal(gray, 30)
    policy = framecheck.flash_signal(gray, 30, **mo.FLASH_POLICY)
    if wcag:
        checks["flashing"] = {"result": "REVIEW REQUIRED", "detail": f"WCAG 2.3.1 general flash (approximation): >3 flashes/s at {wcag} s"}
        reviews.append({"id": "flash:wcag", "check": "flashing", "kind": "technical",
                        "note": f"more than three large flashes in one second at {wcag} s (WCAG 2.3.1 approximation); check frame by frame"})
    elif policy:
        checks["flashing"] = {"result": "REVIEW REQUIRED", "detail": f"project policy (ui-ux #20): >3 flashes/s below the WCAG threshold at {policy} s"}
        reviews.append({"id": "flash:policy", "check": "flashing", "kind": "technical",
                        "note": f"something flashes more than three times a second at {policy} s; below the WCAG 2.3.1 threshold "
                                "but over the harness rule (nothing flashes more than 3 times per second)"})
    else:
        checks["flashing"] = {"result": "PASS", "detail": "no window with more than three flashes (WCAG approximation and the stricter project rule)"}
    ms = [i * 1000 / 30 for i in range(len(gray))]
    loops = mo.loop_candidates(gray, ms, min_overlap=max(10, len(gray) // 8), top=2)
    return {"loopCandidates": loops, "cuts": [c["ms"] for c in mo.cuts(mo.frame_diffs(gray), ms)]}


def compare_lane(ctx: Ctx, out: Path, ff: str, fp: str, captures: dict[float, Path], vp_name: str, meta: dict,
                 recording_cuts: list[float] | None = None) -> dict:
    """Reference frames at the capture times (+ offsetMs) next to the captures, with signals."""
    imaging, _, _ = need_pillow()
    from PIL import Image
    piece = ctx.piece
    ref = piece["reference"]
    f = ctx.root / ref["path"]
    if not f.is_file():
        raise FileNotFoundError(ref["path"])
    raw = ffm.frame_times(fp, f)
    times = [t - raw[0] for t in raw]
    off = float(ref.get("offsetMs") or 0) / 1000
    ts = sorted(captures)
    idx = [min(range(len(times)), key=lambda i: abs(times[i] - (t / 1000 + off))) for t in ts]
    pairs, signals = [], []
    with tempfile.TemporaryDirectory() as tmp:
        files = ffm.extract_frames(ff, f, Path(tmp), sorted(set(idx)), ref.get("crop"))
        by_idx = dict(zip(sorted(set(idx)), files))
        for t, i in zip(ts, idx):
            a = Image.open(by_idx[i]).convert("RGB")
            b = Image.open(captures[t]).convert("RGB")
            h = 360
            a = a.resize((max(1, round(a.width * h / a.height)), h))
            b = b.resize((max(1, round(b.width * h / b.height)), h))
            pair = Image.new("RGB", (a.width + b.width + 8, h), (24, 24, 28))
            pair.paste(a, (0, 0))
            pair.paste(b, (a.width + 8, 0))
            pp = Path(tmp) / f"pair-{t:g}.png"
            pair.save(pp)
            pairs.append(pp)
            sig = imaging.compare(by_idx[i], captures[t])
            signals.append({"ms": t, "referenceFrame": i, "structureBits": sig["ahash_distance"], "paletteDeltaE": sig["palette_delta_e_ok"]})
        rel = f"compare/{vp_name}.png"
        imaging.sheet(pairs, out / rel, cols=2, width=640, labels=[f"t={t:g} ms: reference | build" for t in ts])
    meta[rel] = {"viewport": vp_name}
    gray, _, _ = ffm.gray_frames(ff, f, 64, passthrough=True, crop=ref.get("crop"))
    n = min(len(gray), len(times))
    rms = [t * 1000 for t in times[:n]]
    ref_cuts = [c["ms"] - off * 1000 for c in mo.cuts(mo.frame_diffs(gray[:n]), rms)]
    spec_cuts = [s for _, s, _ in mo.scene_spans(piece)][1:]
    data = {"viewport": vp_name, "pairs": signals, "referenceCuts": ref_cuts,
            "specSceneStarts": spec_cuts, "offsetsToSpec": mo.nearest_offsets(ref_cuts, spec_cuts),
            "offsetsToRecording": mo.nearest_offsets(ref_cuts, recording_cuts or []),
            "note": "structure bits: 0 = same layout; palette deltaE is expected to differ where the brand replaces the reference look"}
    write_atomic(out / "compare/compare.json", dumps_pretty(data))
    meta["compare/compare.json"] = {}
    return data


# ------------------------------------------------------------------ draft commands

def draft_dir(ctx: Ctx, rid: str) -> Path:
    d = self_ignoring_dir(ctx.dir / ".preview", "motion.py drafts") / rid
    d.mkdir(parents=True, exist_ok=True)
    return d


def print_checks(checks: dict, reviews: list) -> None:
    for name, c in checks.items():
        print(f"{c['result']:<16} {name}: {c['detail']}")
    for r in reviews:
        print(f"REVIEW REQUIRED  {r['note']}")


def capture(a: argparse.Namespace) -> int:
    ctx = Ctx(a, production=False)
    if ctx.driver not in ("web", "expo-web"):
        raise UsageError(f"capture drives a browser; the {ctx.driver} driver brings its own frames (verify --frames DIR)")
    ctx.web()
    rid = run_id()
    out = draft_dir(ctx, rid)
    checks, reviews, meta = {}, [], {}
    with mo.ProcessScope(a.timeout) as scope:
        info = visual_lane(ctx, scope, out, checks, reviews, meta, parse_ms_list(a.at) or None, a.determinism)
        if a.reduced:
            reduced_lane(ctx, scope, out, checks, reviews, meta)
    print_checks(checks, reviews)
    print(f"draft (not a verified run) in {out.relative_to(ctx.root).as_posix()}/: captures/, sheets/; modes "
          + ", ".join(f"{k} {v['mode']}" for k, v in info["modes"].items()))
    return 1 if any(c["result"] == "FAIL" for c in checks.values()) else 0


def check(a: argparse.Namespace) -> int:
    ctx = Ctx(a, production=False)
    if ctx.driver not in ("web", "expo-web"):
        raise UsageError(f"check drives a browser; the {ctx.driver} driver has no behaviour lane in this release")
    ctx.web()
    checks, reviews, omitted = {}, [], []
    with mo.ProcessScope(a.timeout) as scope:
        behaviour_lane(ctx, scope, checks, reviews, omitted)
    print_checks(checks, reviews)
    for o in omitted:
        print(f"SKIPPED          {o['id']}: {o['reason']}")
    return 1 if any(c["result"] == "FAIL" for c in checks.values()) else 0


def adb_record(a: argparse.Namespace, scope: mo.ProcessScope, dest: Path, seconds: float) -> dict:
    adb = shutil.which("adb")
    if not adb:
        raise OperationalError("adb not found on PATH (Android platform-tools)")
    base = [adb] + (["-s", a.serial] if a.serial else [])
    remote = f"/sdcard/motion-{run_id()}.mp4"
    secs = int(min(180, max(1, round(seconds))))
    proc = scope.adopt(subprocess.Popen(base + ["shell", "screenrecord", "--time-limit", str(secs), remote],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE), "adb screenrecord")
    scope.on_close(lambda: subprocess.run(base + ["shell", "rm", "-f", remote], capture_output=True, timeout=30, check=False))
    try:
        proc.wait(timeout=secs + 30)
    except subprocess.TimeoutExpired:
        raise OperationalError("adb screenrecord did not finish") from None
    if proc.returncode != 0:
        raise OperationalError(f"adb screenrecord failed ({proc.returncode}): {proc.stderr.read().decode(errors='replace')[-300:]}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(base + ["pull", remote, str(dest)], capture_output=True, timeout=120, check=False)
    if r.returncode != 0:
        raise OperationalError(f"adb pull failed: {r.stderr.decode(errors='replace')[-300:]}")
    return {"seconds": secs, "source": "adb screenrecord (180 s limit; secure windows record black)"}


def record_cmd(a: argparse.Namespace) -> int:
    ctx = Ctx(a, production=False)
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    rid = run_id()
    out = draft_dir(ctx, rid)
    vp = ctx.record_viewport()
    dest = out / f"recording/{vp['name']}.mp4"
    with mo.ProcessScope(a.timeout) as scope:
        if a.file:
            src = Path(a.file)
            if not src.is_file():
                raise UsageError(f"--file {a.file}: no such file")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"took in {src.name} as the recording")
        elif a.adb:
            adb_record(a, scope, dest, a.seconds or ctx.piece["loop"]["lengthMs"] / 1000 * 1.25 + 1)
        else:
            if ctx.driver not in ("web", "expo-web"):
                raise UsageError(f"the {ctx.driver} driver records with --adb or takes a recording with --file")
            ctx.web()
            meta: dict = {}
            stats = record_lane(ctx, scope, out, ff, a.seconds, meta)
            print(f"screencast: {stats['frames']} frames in {stats['seconds']} s ({stats['effectiveFps']} fps, longest gap "
                  f"{stats['longestGapMs']} ms), encoded at {stats['fps']} fps")
    info = ffm.probe(fp, dest, count_frames=False)
    dur = float(info.get("format", {}).get("duration", 0))
    print(f"draft recording: {dest.relative_to(ctx.root).as_posix()} ({dur:.1f} s). Pacing evidence, never frame-exact.")
    return 0


def compare_cmd(a: argparse.Namespace) -> int:
    ctx = Ctx(a, production=False)
    if not ctx.piece.get("reference"):
        raise UsageError("the piece has no reference to compare with")
    ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    vp = ctx.record_viewport()["name"]
    if a.run:
        base = ctx.dir / ".preview" / a.run
        if not (base / "captures").is_dir():
            base = ctx.dir / "out"
        caps_dir = base / "captures" / vp
    elif a.frames:
        caps_dir = Path(a.frames)
    else:
        caps_dir = None
    rec_cuts = None
    if a.recording:
        gray, _, _ = ffm.gray_frames(ff, Path(a.recording))
        rec_cuts = [c["ms"] for c in mo.cuts(mo.frame_diffs(gray), [i * 1000 / 30 for i in range(len(gray))])]
    if caps_dir is None or not caps_dir.is_dir():
        raise UsageError("give --run <draft run> (captures of the designed viewport) or --frames DIR (t<ms>.png files)")
    caps = {}
    for f in caps_dir.glob("t*.png"):
        try:
            caps[float(f.stem[1:])] = f
        except ValueError:
            continue
    if not caps:
        raise UsageError(f"{caps_dir}: no t<ms>.png captures")
    out = draft_dir(ctx, run_id())
    data = compare_lane(ctx, out, ff, fp, caps, vp, {}, rec_cuts)
    for s in data["pairs"]:
        print(f"  t={s['ms']:>8g} ms  reference frame {s['referenceFrame']:>5}  structure {s['structureBits']:>3}/256  "
              f"palette dE {s['paletteDeltaE']}")
    for o in data["offsetsToSpec"]:
        print(f"  reference cut at {o['ms']:g} ms; nearest spec scene start {o['nearest']:g} ms (offset {o['offsetMs']:+g} ms)")
    print(f"REVIEW REQUIRED  look at {(out / 'compare').relative_to(ctx.root).as_posix()}/ side by side; signals are not a verdict")
    return 0


# ------------------------------------------------------------------ verify (production)

def verify(a: argparse.Namespace) -> int:
    root = root_of(a)
    mo.piece_rel(a.id)
    build = self_ignoring_dir(piece_dir(root, a.id) / ".build", "motion.py working files")
    with DirLock(build / "verify.lock", f"motion {a.id}"):
        return _verify(a)


def _verify(a: argparse.Namespace) -> int:
    ctx = Ctx(a, production=True)
    root, piece, pid = ctx.root, ctx.piece, ctx.pid
    p = project(root)
    pg = mo.gate_piece(p, pid)
    if not pg.ok:
        raise dl.GateError(f"verifying {ctx.rel} needs the owner's approval:\n  - " + "\n  - ".join(pg.problems)
                           + f"\n  Capture drafts meanwhile: motion.py capture {pid} --draft")
    lt, _, crel = lint_piece(p, ctx.rel, piece, "verify", production=True)
    for w in lt.warnings:
        print(f"WARN  {w}")
    if lt.errors:
        for e in lt.errors:
            print(f"FAIL  {e}")
        print(f"verify refused: {len(lt.errors)} problem(s)")
        return 1
    print("gate: spec approved (" + ", ".join(pg.records) + ")")
    need_pillow()
    started, rid = dl.now_utc(), run_id()
    checks: dict[str, dict] = {}
    reviews: list[dict] = list(lt.reviews)
    meta: dict[str, dict] = {}
    missing: list[dict] = []
    omitted: list[dict] = []
    evidence: dict = {}
    required = list(ctx.cap["required"])
    have: set[str] = set()
    ff = fp = None
    try:
        ff, fp = ffm.find_ffmpeg(a.ffmpeg)
    except OperationalError as e:
        ff_problem = str(e)
    else:
        ff_problem = ""
    fingerprint = mo.build_fingerprint(root, piece)
    if fingerprint["partial"]:
        reviews.append({"id": "build:partial", "check": "build fingerprint", "kind": "technical",
                        "note": f"the build fingerprint covers {fingerprint['files']} file(s) ({', '.join(fingerprint['globs'])}); "
                                "list the motion's code in target.files or fingerprint.globs so code changes reach the review"})
    assets = mo.asset_files(root, piece)
    stage = Path(tempfile.mkdtemp(prefix="motion-verify-", dir=ctx.dir / ".build"))
    target_rec, capture_cfg = None, {"driver": ctx.driver}
    determinism = a.determinism if a.determinism is not None else 3
    try:
        with mo.ProcessScope(a.timeout) as scope:
            if ctx.driver in ("web", "expo-web"):
                ctx.web()
                target_rec = ctx.target.record()
                info = visual_lane(ctx, scope, stage, checks, reviews, meta, None, determinism)
                have.add("visual")
                reduced_lane(ctx, scope, stage, checks, reviews, meta)
                have.add("reduced-motion")
                behaviour_lane(ctx, scope, checks, reviews, omitted)
                have.add("behaviour")
                capture_cfg = {"driver": ctx.driver, "browser": browser.version(ctx.chrome),
                               "flags": cdp.SEEK_FLAGS + (["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] if piece["capture"].get("webgl") else []),
                               "viewports": [{"name": v["name"], "size": list(v["size"]), "dpr": v["dpr"], "mobile": v["mobile"]} for v in ctx.viewports()],
                               "times": info["times"], "seek": {k: m["mode"] for k, m in info["modes"].items()},
                               "stepMs": piece["capture"].get("stepMs", round(1000 / 60, 3)), "determinism": determinism,
                               "colorScheme": piece["capture"].get("colorScheme"), "webgl": bool(piece["capture"].get("webgl"))}
                if ctx.driver == "expo-web":
                    reviews.append({"id": "native-runtime-unverified", "check": "platform", "kind": "technical",
                                    "note": "captured on Expo web; the native runtime (Reanimated/Skia on device) was not verified. "
                                            "Record it on a device (record --adb) and look at it"})
                if ff:
                    rec = record_lane(ctx, scope, stage, ff, None, meta)
                    have.add("recording")
                    evidence["recording"] = rec
                    evidence.update(flash_checks(ff, stage / rec["path"], checks, reviews))
                    capture_cfg["ffmpeg"] = ffm.version(ff)
                else:
                    checks["recording"] = {"result": "SKIPPED", "detail": ff_problem}
                if piece.get("reference"):
                    if ff and (root / piece["reference"]["path"]).is_file():
                        vp = ctx.record_viewport()["name"]
                        caps = {t: stage / f"captures/{vp}/t{t:g}.png" for t in info["times"]
                                if (stage / f"captures/{vp}/t{t:g}.png").is_file()}
                        if caps:
                            data = compare_lane(ctx, stage, ff, fp, caps, vp, meta, evidence.get("cuts"))
                            have.add("compare")
                            checks["compare"] = {"result": "REVIEW REQUIRED", "detail": f"{len(data['pairs'])} pair(s) at the designed viewport {vp}"}
                            reviews.append({"id": "compare", "check": "reference comparison", "kind": "suitability",
                                            "note": f"look at compare/{vp}.png: the build next to the reference at the same times "
                                                    "(signals in compare/compare.json are not a verdict)"})
                        else:
                            checks["compare"] = {"result": "SKIPPED", "detail": f"no captures at the designed viewport {vp}"}
                    else:
                        why = ff_problem or f"{piece['reference']['path']} is not on this machine (references are git-ignored)"
                        checks["compare"] = {"result": "SKIPPED", "detail": why}
                else:
                    required.remove("compare")
                    omitted.append({"id": "compare", "reason": "no reference: nothing to compare with"})
            else:
                target_rec = {"kind": {"adb": "device", "frames": "frames", "file": "recording"}[ctx.driver]}
                capture_cfg = {"driver": ctx.driver}
                if ctx.driver == "frames":
                    if a.frames and Path(a.frames).is_dir():
                        n = 0
                        for f in sorted(Path(a.frames).glob("t*.png")):
                            rel = f"captures/{ctx.record_viewport()['name']}/{f.name}"
                            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(f, stage / rel)
                            meta[rel] = {"viewport": ctx.record_viewport()["name"], "atMs": float(f.stem[1:])}
                            n += 1
                        if n:
                            have.add("visual")
                            checks["visual"] = {"result": "PASS", "detail": f"{n} frame(s) from the project's own deterministic test (--frames)"}
                    if "visual" not in have:
                        checks["visual"] = {"result": "SKIPPED", "detail": "pass --frames DIR with t<ms>.png files from the project's test"}
                    for item, note in (("semantic", "accessibility semantics (labels, focus, screen reader) on the device"),
                                       ("reduced-motion", "the system 'remove animations' setting on the device")):
                        reviews.append({"id": f"manual:{item}", "check": "manual", "kind": "technical",
                                        "note": f"not checkable from frames: verify {note} by hand"})
                if a.recording or ctx.driver == "adb":
                    vp = ctx.record_viewport()["name"]
                    rel = f"recording/{vp}.mp4"
                    (stage / rel).parent.mkdir(parents=True, exist_ok=True)
                    if a.recording:
                        shutil.copy2(a.recording, stage / rel)
                    else:
                        adb_record(a, scope, stage / rel, piece["loop"]["lengthMs"] / 1000 * 1.25 + 1)
                    meta[rel] = {"viewport": vp, "kind": "evidence"}
                    have.add("recording")
                    if ff:
                        evidence.update(flash_checks(ff, stage / rel, checks, reviews))
                else:
                    checks["recording"] = {"result": "SKIPPED", "detail": "pass --recording FILE (device or simulator recording)"}
                for item in ("visual", "semantic"):
                    if item in required and item not in have and ctx.driver in ("adb", "file"):
                        checks[item] = {"result": "SKIPPED", "detail": f"the {ctx.driver} driver cannot capture this (no native adapter yet)"}
        if scope.timed_out:
            raise OperationalError(f"verify timed out after {a.timeout:g} s; every process it started was stopped")
        for item in required:
            if item not in have:
                c = checks.get(item) or {}
                missing.append({"id": item, "reason": c.get("detail") or "not produced"})
        complete = not missing
        if missing:
            reviews.append({"id": "incomplete", "check": "completeness", "kind": "technical",
                            "note": "the run is incomplete: " + "; ".join(f"{m['id']}: {m['reason']}" for m in missing)[:500]})
        print_checks(checks, [])
        failed = [k for k, c in checks.items() if c["result"] == "FAIL"]
        if failed:
            print(f"published nothing: {', '.join(failed)} failed")
            return 1
        # the gate again: nothing the approval covers changed while the run was going
        if mo.gate_piece(dl.load_project(root), pid).hashes != pg.hashes:
            raise InputError(f"{ctx.rel} or the concept changed during the run; verify again")
        if mo.build_fingerprint(root, piece)["sha256"] != fingerprint["sha256"]:
            raise InputError("the app's code changed during the run; verify again")
        out_rel = Path(mo.PIECES) / pid / ("out" if complete else f".preview/{rid}")
        files = sorted(x.relative_to(stage).as_posix() for x in stage.rglob("*") if x.is_file())
        outputs = []
        for rel in files:
            f = stage / rel
            entry = {"path": (out_rel / rel).as_posix(), "sha256": sha256_file(f), "bytes": f.stat().st_size}
            m = meta.get(rel) or {}
            for k in ("viewport", "atMs", "kind", "fps", "frames", "size"):
                if k in m:
                    entry[k] = m[k]
            outputs.append(entry)
        status_ = "review-required" if reviews or any(c["result"] == "REVIEW REQUIRED" for c in checks.values()) else "complete"
        concept_gate = pg.concept_gate
        manifest = {"schemaVersion": 1, "runId": rid, "family": "motion", "mode": "production", "tool": "motion.py",
                    "startedAt": started, "finishedAt": dl.now_utc(),
                    "engine": {"api": harnesslib.API_VERSION, "renderer": "ours",
                               "capture": (sorted({m for m in (capture_cfg.get("seek") or {}).values()}) or [ctx.driver if ctx.driver in ("adb", "frames", "file") else "realtime"])[0],
                               **({"browser": capture_cfg["browser"]} if capture_cfg.get("browser") else {}),
                               **({"ffmpeg": ffm.version(ff)} if ff else {})},
                    "inputs": {"config": sha256_text(canonical(piece)),
                               "direction": concept_gate.direction[0] if concept_gate.direction else None,
                               "concept": concept_gate.concept[0] if concept_gate.concept else None,
                               "assets": assets},
                    "approvals": pg.records,
                    "fonts": [{"family": t["family"], "source": t["source"]} for t in
                              dl.resolve_family(p, "motion", dl.load_concept(p, crel))["type"].values()] if crel else [],
                    "seed": piece["capture"].get("seed"), "outputs": outputs, "checks": checks, "status": status_,
                    "piece": {"path": ctx.rel, "hash": pg.hashes[0], "inputs": pg.hashes[1],  # type: ignore[index]
                              "viewports": piece["viewports"], "platform": piece["platform"], "driver": ctx.driver},
                    "build": fingerprint, "target": target_rec or {"kind": "url"}, "captureConfig": capture_cfg,
                    "completeness": "complete" if complete else "incomplete", "missing": missing, "omitted": omitted,
                    "evidence": evidence, "reviews": reviews}
        path = dl.write_run_manifest(root, manifest)
        if complete:
            with Publisher(ctx.dir / "out", f"motion {pid}", run=rid) as pub:
                for rel in files:
                    dest = pub.stage_path(rel)
                    shutil.copy2(stage / rel, dest)
                pub.publish(prune=True)
        else:
            dest_dir = draft_dir(ctx, rid)
            for rel in files:
                (dest_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stage / rel, dest_dir / rel)
        where = "published to " + (Path(mo.PIECES) / pid / "out").as_posix() if complete else \
            f"NOT published (incomplete); outputs kept in {out_rel.as_posix()}/"
        print(f"run {rid}: {len(outputs)} file(s) {where}; manifest {path.relative_to(root).as_posix()} ({status_}, "
              f"{'complete' if complete else 'INCOMPLETE'})")
        if not complete:
            for m in missing:
                print(f"MISSING  {m['id']}: {m['reason']}")
            print("an incomplete run can't be reviewed; fix what is missing and verify again")
            return 1 if ci() else 0
        done = mo.acknowledged(dl.load_project(root), manifest)
        open_ = [r["id"] for r in reviews if r["id"] not in done]
        if open_:
            for r in reviews:
                if r["id"] in open_:
                    print(f"REVIEW REQUIRED  {r['id']}: {r['note']}")
            print(f"not reviewed yet: {len(open_)} item(s); after the owner has looked: direction.py approve --gate review "
                  f"--run {rid} --items <ids|all> --by ... --evidence ...")
        else:
            print("reviewed: the owner already acknowledged these items for this build, target, settings and outputs")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def clean(a: argparse.Namespace) -> int:
    root = root_of(a)
    d = piece_dir(root, a.id)
    if not d.is_dir():
        raise UsageError(f"{d.relative_to(root).as_posix()} does not exist")
    removed = []
    for name in (".build", ".preview"):
        x = d / name
        gi = x / ".gitignore"
        if x.is_dir():
            if not gi.is_file() or "*" not in gi.read_text(encoding="utf-8", errors="replace").split():
                print(f"kept {x.relative_to(root).as_posix()}: it is not a folder motion.py made (no self-ignoring .gitignore)")
                continue
            shutil.rmtree(x)
            removed.append(name)
    print(f"removed {', '.join(removed) or 'nothing'} under {d.relative_to(root).as_posix()}/ (reference/ and out/ kept)")
    return 0


# ------------------------------------------------------------------ main

def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="the project root (holds brand/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("id")
    i.add_argument("--title")
    i.add_argument("--reference")
    i.add_argument("--platform", default="web", choices=list(mo.DRIVERS_FOR))
    pr = sub.add_parser("probe")
    pr.add_argument("id")
    pr.add_argument("--file")
    pr.add_argument("--record", action="store_true")
    fr = sub.add_parser("frames")
    fr.add_argument("id")
    g = fr.add_mutually_exclusive_group()
    g.add_argument("--every", type=float, metavar="MS")
    g.add_argument("--at", metavar="MS,MS")
    g.add_argument("--all", action="store_true")
    fr.add_argument("--crop", metavar="X,Y,W,H")
    fr.add_argument("--no-crop", action="store_true")
    fr.add_argument("--scale", type=int, metavar="WIDTH")
    sh = sub.add_parser("sheet")
    sh.add_argument("id")
    sh.add_argument("--run")
    sh.add_argument("--cols", type=int, default=6)
    sh.add_argument("--rows", type=int, default=8)
    sh.add_argument("--width", type=int, default=240)
    cu = sub.add_parser("cuts")
    cu.add_argument("id")
    cu.add_argument("--file")
    ins = sub.add_parser("inspect")
    ins.add_argument("id")
    ins.add_argument("--range", required=True)
    ins.add_argument("--mode", required=True, choices=["every-frame", "sampled"])
    ins.add_argument("--by", required=True)
    ins.add_argument("--note", default="")
    tk = sub.add_parser("tokens")
    tk.add_argument("--write", action="store_true")
    tk.add_argument("--replace", action="append")
    li = sub.add_parser("lint")
    li.add_argument("id")
    li.add_argument("--stage", choices=["spec", "verify"], default="spec")
    sp = sub.add_parser("spec")
    sp.add_argument("id")
    st = sub.add_parser("status")
    st.add_argument("id", nargs="?")
    ca = sub.add_parser("capture")
    ca.add_argument("id")
    ca.add_argument("--draft", action="store_true", help="captures are always drafts; verify makes the production run")
    ca.add_argument("--viewport")
    ca.add_argument("--at", metavar="MS,MS")
    ca.add_argument("--reduced", action="store_true")
    ca.add_argument("--determinism", type=int, default=0, metavar="K")
    ck = sub.add_parser("check")
    ck.add_argument("id")
    ck.add_argument("--draft", action="store_true")
    ck.add_argument("--viewport")
    rc = sub.add_parser("record")
    rc.add_argument("id")
    rc.add_argument("--viewport")
    rc.add_argument("--seconds", type=float)
    rc.add_argument("--adb", action="store_true")
    rc.add_argument("--serial")
    rc.add_argument("--file")
    cp = sub.add_parser("compare")
    cp.add_argument("id")
    cp.add_argument("--run")
    cp.add_argument("--frames")
    cp.add_argument("--recording")
    cp.add_argument("--viewport")
    ve = sub.add_parser("verify")
    ve.add_argument("id")
    ve.add_argument("--determinism", type=int, metavar="K", help="re-capture K times in a fresh browser (default 3; 0 skips)")
    ve.add_argument("--frames", help="frames driver: a folder of t<ms>.png from the project's own deterministic test")
    ve.add_argument("--recording", help="adb, frames or file driver: a device or simulator recording")
    ve.add_argument("--serial")
    ve.add_argument("--viewport")
    cl = sub.add_parser("clean")
    cl.add_argument("id")
    for p_ in sub.choices.values():
        p_.add_argument("--project", default=argparse.SUPPRESS, help="the project root (holds brand/)")
    for p_ in (pr, fr, sh, cu, ca, ck, rc, cp, ve):
        p_.add_argument("--chrome")
        p_.add_argument("--ffmpeg")
        p_.add_argument("--base-url")
        p_.add_argument("--timeout", type=float, default=None, help="stop (and stop every process started) after SECONDS")
    a = ap.parse_args()
    for k in ("chrome", "ffmpeg", "base_url", "timeout", "viewport", "serial"):
        if not hasattr(a, k):
            setattr(a, k, None)
    if getattr(a, "determinism", None) and not 0 <= a.determinism <= 30:
        ap.error("--determinism takes 0-30")
    handlers = {"init": init, "probe": probe, "frames": frames_cmd, "sheet": sheet_cmd, "cuts": cuts_cmd, "inspect": inspect_cmd,
                "tokens": tokens, "lint": lint, "spec": spec, "status": status, "capture": capture, "check": check,
                "record": record_cmd, "compare": compare_cmd, "verify": verify, "clean": clean}
    try:
        return handlers[a.cmd](a)
    except KeyboardInterrupt as e:
        print(f"error: stopped ({e or 'interrupted or --timeout reached'}); every process this command started was stopped",
              file=sys.stderr)
        return 2
    except (UsageError, OperationalError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
