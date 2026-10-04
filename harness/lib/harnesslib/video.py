"""Video pieces: brand/video/<id>/video.json -> frame plan, hashes, gates, voice files and reviews.

A piece says what a video shows and when (scenes, copy, voice-over lines). Its look and motion come
from the selected video concept (direction.resolve_family), so the piece never sets a colour or a
font. Approvals:
  Gate 1 direction, Gate 2 video concept (direction.py), then Gate 3 storyboard: the owner approves
  the piece itself (its visuals, timing and script, each hashed separately so a stale record can say
  what changed) against the concept it was resolved with. Audio never enters these hashes.
  review: after a render, the owner acknowledges the REVIEW REQUIRED items of that run. The record
  binds to the run's output hashes, so a byte-identical re-render keeps it and any change needs a new
  look.

Frame arithmetic (references/composition-contract.md): seconds become whole frames with
floor(s * fps + 0.5); a scene's duration includes its still "hold"; an incoming transition overlaps
the previous scene's tail; a clip shows frames [start, start + frames). Every format of a piece
shares one timeline.
"""

from __future__ import annotations

import math
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import direction as dl
from . import schema
from .fsutil import (InputError, canonical, dumps_pretty, load_json, resolve_inside, script_json, sha256_file,
                     sha256_text)

PIECES = "brand/video"
MEDIA = Path(__file__).resolve().parent.parent / "media"
PIECE_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

# Safe insets keep text clear of the platforms' own buttons and captions. They are a heuristic
# shared by Reels, Shorts and TikTok (measured from their UI in 2026); "strict" leaves more room.
FORMATS: dict[str, dict] = {
    "social-9x16": {"size": (1080, 1920), "min": 3.0, "max": 90.0, "profile": "h264-web",
                    "label": "9:16 vertical (Reels, Shorts, TikTok)",
                    "safe": {"standard": {"top": 220, "right": 120, "bottom": 400, "left": 90},
                             "strict": {"top": 260, "right": 140, "bottom": 480, "left": 120}}},
}
PLACEHOLDER = re.compile(r"\bREPLACE\b|\{\{[^}]*\}\}|\bTODO\b|lorem ipsum", re.I)


def frames_of(seconds: float, fps: int) -> int:
    return math.floor(seconds * fps + 0.5)


def words(text: str | None) -> int:
    return len(re.findall(r"[\w’'-]+", re.sub(r"</?em>", "", text or "")))


# ------------------------------------------------------------------ loading

def piece_rel(pid: str) -> str:
    if not PIECE_ID.match(pid or ""):
        raise InputError(f"piece id {pid!r}: lower-case letters, digits and dashes (it names brand/video/<id>/)")
    return f"{PIECES}/{pid}/video.json"


def load_piece(p: dl.Project, pid: str) -> tuple[str, dict]:
    rel = piece_rel(pid)
    path = resolve_inside(p.root, rel, "video piece", must_exist=True)
    data = load_json(path)
    schema.check(data, "video", rel)
    if data["id"] != pid:
        raise InputError(f"{rel}: id {data['id']!r} must match its folder {pid!r}")
    return rel, data


def list_pieces(root: Path) -> list[str]:
    base = Path(root) / PIECES
    return sorted(d.name for d in base.iterdir() if (d / "video.json").is_file()) if base.is_dir() else []


# ------------------------------------------------------------------ the frame plan

@dataclass
class ScenePlan:
    id: str
    template: str
    start: int
    frames: int
    overlap: int
    transition: str
    enter: int
    hold_start: int
    hold_end: int
    probe: int
    layout: str
    background: str
    copy: dict
    vo: str
    read_seconds: float

    def page(self) -> dict:
        return {"id": self.id, "template": self.template, "start": self.start, "frames": self.frames,
                "overlap": self.overlap, "transition": self.transition, "enter": self.enter,
                "layout": self.layout, "background": self.background, "copy": self.copy}


@dataclass
class Plan:
    fps: int
    frames: int
    scenes: list[ScenePlan]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reviews: list[dict] = field(default_factory=list)  # {id, check, kind, note}
    exceptions: list[str] = field(default_factory=list)  # approval records that allowed something

    @property
    def seconds(self) -> float:
        return self.frames / self.fps


def _drawn(template: str, copy: dict, ad: dict) -> tuple[list[str], int]:
    """What a scene draws (its texts, in reading order) and how many parts its entrance animates,
    by the same rules as media/motion.js: a kicker only when the concept has a kicker style, points
    only on feature scenes, url (or else sub) on the end card, the logo when the end card shows it,
    and with word-stagger the headline (or the stat's value) counted word by word."""
    kicker = copy.get("kicker") if (ad.get("caption") or {}).get("kicker") else None
    by_word = ad["motion"]["textIn"] == "word-stagger"

    def head_parts(text: str | None) -> int:
        if not text:
            return 0
        return len(re.sub(r"</?em>", "", text).split()) if by_word else 1

    if template == "stat":
        texts = [kicker, copy.get("value"), copy.get("label"), copy.get("sub")]
        n = bool(kicker) + head_parts(copy.get("value")) + bool(copy.get("label")) + bool(copy.get("sub"))
    elif template == "end-card":
        tail = copy.get("url") or copy.get("sub")
        logo = bool(ad.get("logo")) and ad["endCard"]["logo"]
        texts = [kicker, copy.get("head"), tail]
        n = int(logo) + bool(kicker) + head_parts(copy.get("head")) + bool(tail)
    else:
        points = list(copy.get("points") or []) if template == "feature" else []
        texts = [kicker, copy.get("head"), copy.get("sub")] + points
        n = bool(kicker) + head_parts(copy.get("head")) + bool(copy.get("sub")) + len(points)
    return [t for t in texts if t], int(n)


def _text_parts(template: str, copy: dict, ad: dict) -> int:
    return _drawn(template, copy, ad)[1]


def _on_screen(template: str, copy: dict, ad: dict) -> str:
    return " ".join(_drawn(template, copy, ad)[0])


def plan(p: dl.Project | None, pid: str, piece: dict, ad: dict, fmt: str, production: bool) -> Plan:
    """Whole-frame timing of every scene, with the problems found on the way (errors block a render;
    warnings and reviews are reported)."""
    fps = piece["fps"]
    m, pace = ad["motion"], ad["pace"]
    out = Plan(fps, 0, [])

    def ms_frames(ms: float) -> int:
        return math.ceil(ms * fps / 1000 - 1e-9)

    def allowed(kind: str, sid: str, value: str, vocab: list[str]) -> bool:
        if value in vocab:
            return True
        scope = f"video:{pid}:scene:{sid}:{kind}={value}"
        rec = dl.exception_approved(p, scope) if p is not None else None
        if rec:
            out.exceptions.append(rec)
            return True
        msg = (f"scene {sid}: {kind} {value!r} is outside the concept ({', '.join(vocab)}); the owner can allow it: "
               f"direction.py approve --gate exception --scope \"{scope}\"")
        (out.errors if production else out.warnings).append(msg)
        return not production

    text_in_ms = 0 if m["textIn"] == "none" else m["durations"]["base"]
    text_out = 0 if m["textOut"] == "none" else ms_frames(m["durations"]["fast"])
    raw = []
    for i, sc in enumerate(piece["scenes"]):
        sid = sc["id"]
        for key in ("duration", "hold"):
            if key in sc and abs(frames_of(sc[key], fps) / fps - sc[key]) > 0.001:
                out.warnings.append(f"scene {sid}: {key} {sc[key]} s is not a whole number of frames at {fps} fps "
                                    f"(rendered as {frames_of(sc[key], fps)} frames)")
        n = frames_of(sc["duration"], fps)
        tr = (sc.get("transitionIn") or {}).get("type") or ("cut" if i == 0 else m["defaultTransition"])
        if i == 0 and tr != "cut":
            out.warnings.append(f"scene {sid}: the first scene has nothing to transition from; {tr!r} is ignored")
            tr = "cut"
        if tr != "cut":
            allowed("transition", sid, tr, m["transitions"])
        tr_ms = (sc.get("transitionIn") or {}).get("duration")
        overlap = 0 if tr == "cut" else frames_of(tr_ms, fps) if tr_ms is not None else ms_frames(m["durations"]["base"])
        layout = sc.get("layout") or ad["defaultLayout"]
        allowed("layout", sid, layout, ad["layouts"])
        if sc["template"] not in ad["sceneTemplates"]:
            allowed("template", sid, sc["template"], ad["sceneTemplates"])
        bgname = sc.get("background") or (ad["endCard"]["background"] if sc["template"] == "end-card" else ad["defaultBackground"])
        if bgname not in ad["backgrounds"]:
            out.errors.append(f"scene {sid}: background {bgname!r} is not in the concept ({', '.join(ad['backgrounds'])})")
        copy = sc.get("copy") or {}
        need = {"title": ("head",), "feature": ("head",), "stat": ("value",), "end-card": ("head",)}[sc["template"]]
        for k in need:
            if not copy.get(k):
                out.errors.append(f"scene {sid}: a {sc['template']} scene needs copy.{k}")
        for k, v in list(copy.items()) + [("vo", sc.get("vo", ""))]:
            for text in (v if isinstance(v, list) else [v]):
                if isinstance(text, str) and PLACEHOLDER.search(text):
                    (out.errors if production else out.warnings).append(f"scene {sid}: placeholder copy in {k}: {text[:60]!r}")
        parts = _text_parts(sc["template"], copy, ad)
        stagger = m["stagger"]["perItemMs"] * max(0, min(parts, m["stagger"]["maxItems"]) - 1)
        enter = overlap + (ms_frames(text_in_ms + stagger) if parts and text_in_ms else 0)
        raw.append((sc, sid, n, tr, overlap, enter, layout, bgname, copy))
    start = 0
    for i, (sc, sid, n, tr, overlap, enter, layout, bgname, copy) in enumerate(raw):
        if i > 0:
            start = start + raw[i - 1][2] - overlap
        if overlap >= n:
            out.errors.append(f"scene {sid}: the {tr} transition ({overlap} frames) is as long as the scene ({n} frames)")
        next_overlap = raw[i + 1][4] if i + 1 < len(raw) else 0
        hold_end = n - next_overlap - (text_out if i + 1 < len(raw) else 0)
        if "hold" in sc:
            hold_start = n - frames_of(sc["hold"], fps)
            if hold_start < enter:
                out.errors.append(f"scene {sid}: hold {sc['hold']} s starts before the entrance ends "
                                  f"({enter / fps:.2f} s into the scene)")
        else:
            hold_start = enter
        usable = hold_end - hold_start
        if usable < frames_of(pace["minHold"], fps):
            out.errors.append(f"scene {sid}: the still part lasts {max(usable, 0) / fps:.2f} s, under the concept's "
                              f"minimum hold of {pace['minHold']} s (lengthen the scene or shorten its transitions)")
        on_screen = _on_screen(sc["template"], copy, ad)
        read = words(on_screen) / pace["readingWpm"] * 60 + 0.5 if on_screen else 0.0
        if usable > 0 and read > usable / fps + 1e-9:
            out.reviews.append({"id": f"reading:{sid}", "check": "reading time", "kind": "content",
                                "note": f"scene {sid}: {words(on_screen)} words need about {read:.1f} s at "
                                        f"{pace['readingWpm']:g} wpm; the still part lasts {usable / fps:.1f} s"})
        probe = start + hold_start + max(usable, 1) // 2
        out.scenes.append(ScenePlan(sid, sc["template"], start, n, overlap, tr, enter, hold_start, hold_end,
                                    probe, layout, bgname, copy, sc.get("vo", ""), read))
    out.frames = (out.scenes[-1].start + out.scenes[-1].frames) if out.scenes else 0
    f = FORMATS[fmt]
    if not f["min"] <= out.seconds <= f["max"]:
        out.errors.append(f"{fmt}: the piece lasts {out.seconds:.2f} s; this format takes {f['min']:g}-{f['max']:g} s")
    return out


# ------------------------------------------------------------------ hashes and gates

def _parts(piece: dict) -> dict:
    visual = {"kind": piece["kind"], "formats": piece["formats"],
              "scenes": [{k: s.get(k) for k in ("id", "template", "layout", "background", "copy")} for s in piece["scenes"]]}
    timing = {"fps": piece["fps"], "scenes": [{k: s.get(k) for k in ("id", "duration", "hold", "transitionIn")}
                                              for s in piece["scenes"]]}
    script = {"scenes": [{"id": s["id"], "vo": s.get("vo")} for s in piece["scenes"]], "voice": piece.get("voice")}
    return {k: sha256_text(canonical(v)) for k, v in (("visual", visual), ("timing", timing), ("script", script))}


def piece_hashes(p: dl.Project, rel: str, piece: dict, g: dl.Gate) -> tuple[tuple[str, str], dict]:
    """((content, inputs), parts) for the storyboard gate. Inputs: the video concept's approval
    hashes (which cover every resolved colour, type and motion value, the motif and the logo)."""
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
    g = dl.gate(p, "video")
    problems = list(g.problems)
    records = list(g.records)
    rel, piece = load_piece(p, pid)
    if not g.ok:
        return PieceGate(False, problems + [f"the storyboard of {rel} can be approved once the video concept is"], records, g)
    h, parts = piece_hashes(p, rel, piece, g)
    rec = dl._latest(p.approvals, gate="storyboard", subject=rel)
    if rec is None:
        problems.append(f"the storyboard {rel} has no owner approval (Gate 3: preview it, then direction.py approve "
                        f"--gate storyboard --piece {pid})")
    elif (rec["hash"], rec["inputs"]) != h:
        if rec["hash"] != h[0]:
            changed = [k for k, v in parts.items() if (rec.get("parts") or {}).get(k) != v] or ["the piece"]
            what = " and ".join({"visual": "on-screen content", "timing": "timing", "script": "the voice-over script"}.get(c, c)
                                for c in changed)
        else:
            what = "the video concept or a value it resolves"
        problems.append(f"the storyboard approval {rec['id']} is stale: {what} changed since {rec['at']}")
    else:
        records.append(rec["id"])
    return PieceGate(not problems, problems, records, g, h, parts)


def approve_storyboard(p: dl.Project, pid: str, by: str, evidence: str, recorded_by: str) -> dict:
    g = dl.gate(p, "video")
    if not g.ok:
        raise dl.GateError("approve the direction and the video concept first: " + "; ".join(g.problems))
    rel, piece = load_piece(p, pid)
    ad = dl.resolve_family(p, "video", dl.load_concept(p, g.concept_rel))  # type: ignore[arg-type]
    pl = plan(p, pid, piece, ad, piece["formats"][0], production=True)
    _, cue_errors, _ = cues(pl, piece, ad)
    if pl.errors or cue_errors:
        raise InputError(f"{rel} has problems to fix before it can be approved:\n  - " + "\n  - ".join(pl.errors + cue_errors))
    h, parts = piece_hashes(p, rel, piece, g)
    return dl.record_approval(p, "storyboard", rel, h, by, evidence, recorded_by, family="video", extra={"parts": parts})


# ------------------------------------------------------------------ runs and reviews

def runs_dir(root: Path) -> Path:
    return Path(root) / dl.RUNS / "video"


def outputs_hash(manifest: dict) -> str:
    """What a review acknowledgement binds to: the run's outputs and the review items it listed (so
    an acknowledgement can't be reused for other files or a shortened list)."""
    return sha256_text(canonical({"outputs": sorted((o["path"], o["sha256"]) for o in manifest["outputs"]),
                                  "reviews": sorted((r["id"], r["note"]) for r in manifest.get("reviews") or [])}))


def piece_runs(root: Path, pid: str) -> list[dict]:
    base = runs_dir(root)
    rel = piece_rel(pid)
    out = []
    for f in sorted(base.glob("*.json")) if base.is_dir() else []:
        m = load_json(f)
        if (m.get("piece") or {}).get("path") == rel:
            schema.check(m, "run-manifest", f"{dl.RUNS}/video/{f.name}")
            out.append(m)
    return out


def acknowledged(p: dl.Project, manifest: dict) -> set[str]:
    h = outputs_hash(manifest)
    done: set[str] = set()
    for r in p.approvals:
        if r.get("gate") == "review" and r.get("hash") == h:
            done |= set(r.get("items") or [])
    return done


def approve_review(p: dl.Project, run: str, items: list[str], by: str, evidence: str, recorded_by: str) -> dict:
    f = runs_dir(p.root) / f"{run}.json"
    if not f.is_file():
        raise InputError(f"no video run {run} under {dl.RUNS}/video/")
    m = load_json(f)
    schema.check(m, "run-manifest", f.name)
    ids = [r["id"] for r in m.get("reviews") or []]
    if not ids:
        raise InputError(f"run {run} has nothing to review")
    if items == ["all"]:
        items = ids
    unknown = sorted(set(items) - set(ids))
    if unknown:
        raise InputError(f"run {run} has no review item(s) {', '.join(unknown)} (it has: {', '.join(ids)})")
    rel = f"{dl.RUNS}/video/{run}.json"
    h = (outputs_hash(m), sha256_text(canonical(sorted(items))))
    return dl.record_approval(p, "review", rel, h, by, evidence, recorded_by, family="video",
                              extra={"run": run, "items": sorted(items)})


@dataclass
class PieceStatus:
    run: str | None
    published: bool
    missing: list[str]
    outstanding: list[dict]
    lines: list[str]


def piece_status(p: dl.Project, pid: str, current: tuple[str, str] | None = None) -> PieceStatus:
    """The last production run of a piece: published as recorded? review items open? current is the
    storyboard's approved hashes now; a run made from other ones is not the approved piece."""
    runs = piece_runs(p.root, pid)
    if not runs:
        return PieceStatus(None, False, [], [], [f"{pid}: no production run yet"])
    m = runs[-1]
    missing = []
    if current is not None and (m["piece"]["hash"], m["piece"]["inputs"]) != tuple(current):
        missing.append("the published output predates the current storyboard approval; render it again")
    if m["status"] == "review-required" and not m.get("reviews"):
        missing.append("the run says review-required but lists no review items (the manifest was edited?)")
    for o in m["outputs"]:
        f = p.root / o["path"]
        if not f.is_file():
            missing.append(f"{o['path']} is missing")
        elif sha256_file(f) != o["sha256"]:
            missing.append(f"{o['path']} differs from the run's record")
    done = acknowledged(p, m)
    outstanding = [r for r in m.get("reviews") or [] if r["id"] not in done]
    lines = [f"{pid}: last run {m['runId']} ({m['status']}), {len(m['outputs'])} output(s)"]
    if missing:
        lines.append("  NOT PUBLISHED as approved and recorded: " + "; ".join(missing))
    if outstanding:
        lines.append(f"  not cleared for use: {len(outstanding)} review item(s) open")
        lines += [f"    - {r['id']}: {r['note']}" for r in outstanding]
        lines.append(f"  after the owner has looked: direction.py approve --gate review --run {m['runId']} "
                     f"--items <ids|all> --by ... --evidence ...")
    elif not missing:
        lines.append("  cleared for use" + (f" ({len(done)} review item(s) acknowledged)" if done else ""))
    return PieceStatus(m["runId"], not missing, missing, outstanding, lines)


# ------------------------------------------------------------------ voice-over script, prompt, captions

def cues(pl: Plan, piece: dict, ad: dict) -> tuple[list[dict], list[str], list[dict]]:
    """Planned voice-over windows and subtitle cues. Without a recording the timing is an
    estimate (words at the concept's voice pace); it is labelled 'planned' everywhere."""
    fps = pl.fps
    wpm = ad["pace"]["voWpm"]
    max_chars = (piece.get("captions") or {}).get("maxCharsPerLine") or (ad.get("subtitles") or {}).get("maxCharsPerLine", 32)
    lines_per_cue = (ad.get("subtitles") or {}).get("maxLines", 2)
    out, errors, reviews = [], [], []
    prev_end: float | None = None
    for sc in pl.scenes:
        if not sc.vo.strip():
            continue
        n = words(sc.vo)
        est = n / wpm * 60
        # a line starts once the scene has arrived, and never over the previous line
        start = (sc.start + sc.overlap) / fps + 0.15
        if prev_end is not None:
            start = max(start, prev_end + 0.2)
        window_end = (sc.start + sc.frames) / fps
        end = start + est
        fits = end <= window_end + 1e-9
        if not fits:
            reviews.append({"id": f"vo-fit:{sc.id}", "check": "voice-over fit", "kind": "content",
                            "note": f"scene {sc.id}: {n} words take about {est:.1f} s at {wpm:g} wpm; the scene leaves "
                                    f"{window_end - start:.1f} s (the line runs into the next scene)"})
        if end > pl.seconds + 1e-9:
            errors.append(f"scene {sc.id}: the planned voice-over ends at {end:.2f} s, after the video ({pl.seconds:.2f} s); "
                          "shorten the lines or lengthen the scenes")
        prev_end = end
        out.append({"scene": sc.id, "start": round(start, 3), "end": round(end, 3), "words": n, "text": sc.vo.strip(),
                    "fits": fits, "subtitles": _subtitle_cues(sc.vo.strip(), start, end, max_chars, lines_per_cue)})
    return out, errors, reviews


def _wrap(text: str, width: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def _subtitle_cues(text: str, start: float, end: float, width: int, per_cue: int) -> list[dict]:
    lines = _wrap(text, width)
    groups = [lines[i:i + per_cue] for i in range(0, len(lines), per_cue)]
    total = sum(len(" ".join(g)) for g in groups) or 1
    out, t = [], start
    for g in groups:
        span = (end - start) * len(" ".join(g)) / total
        out.append({"start": round(t, 3), "end": round(t + span, 3), "lines": g})
        t += span
    return out


def _ts(t: float, sep: str) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def srt(cue_list: list[dict]) -> str:
    out, i = [], 1
    for c in cue_list:
        for s in c["subtitles"]:
            out += [str(i), f"{_ts(s['start'], ',')} --> {_ts(s['end'], ',')}", *s["lines"], ""]
            i += 1
    return "\n".join(out)


def vtt(cue_list: list[dict]) -> str:
    out = ["WEBVTT", "", "NOTE planned timing: estimated from the script, not aligned to a recording.", ""]
    for c in cue_list:
        for s in c["subtitles"]:
            out += [f"{_ts(s['start'], '.')} --> {_ts(s['end'], '.')}", *s["lines"], ""]
    return "\n".join(out)


def script_md(pid: str, piece: dict, pl: Plan, cue_list: list[dict], ad: dict) -> str:
    by_scene = {c["scene"]: c for c in cue_list}
    total_words = sum(c["words"] for c in cue_list)
    lines = [f"# Voice-over script: {piece.get('title') or pid}", "",
             "<!-- Generated by render_video.py from video.json. Edit the scenes' \"vo\" lines there, not this file. -->", "",
             f"Length {pl.seconds:.1f} s ({pl.frames} frames at {pl.fps} fps). Voice-over: {total_words} words at about "
             f"{ad['pace']['voWpm']:g} words a minute. Timings are planned estimates until a recording exists.", "",
             "| # | Scene | Time | On screen | Voice-over | Words | Fits |", "|---|---|---|---|---|---|---|"]
    for i, sc in enumerate(pl.scenes, 1):
        c = by_scene.get(sc.id)
        t = f"{sc.start / pl.fps:.1f}–{(sc.start + sc.frames) / pl.fps:.1f} s"
        screen = _on_screen(sc.template, sc.copy, ad).replace("|", "/").replace("<em>", "").replace("</em>", "")
        lines.append(f"| {i} | {sc.id} ({sc.template}) | {t} | {screen or '-'} | {(c['text'] if c else '-').replace('|', '/')} | "
                     f"{c['words'] if c else 0} | {('yes' if c['fits'] else 'NO: too long') if c else '-'} |")
    lines += ["", "## Read-through", ""]
    for c in cue_list:
        lines.append(f"[{_ts(c['start'], '.')[3:]}] {c['text']}")
    return "\n".join(lines) + "\n"


def voice_prompt_md(pid: str, piece: dict, pl: Plan, cue_list: list[dict], ad: dict, mood: dict) -> str:
    cv = ad.get("voice") or {}
    pv = piece.get("voice") or {}
    lang = pv.get("language", "en")
    casting = pv.get("casting") or cv.get("casting") or "not set: the creative-director adds voice casting to the video concept"
    pace = cv.get("pace", "measured")
    lines = [f"# Voice prompt: {piece.get('title') or pid}", "",
             "<!-- Generated by render_video.py from video.json and the video concept. Use it with any voice tool or a "
             "voice actor; drop the recording into brand/video/" + pid + "/media/vo/ when audio mixing is available. -->", "",
             "## Casting", "", f"- Voice: {casting}",
             f"- Register: {cv.get('register') or 'match the mood below'}",
             f"- Accent: {cv.get('accent') or 'neutral for the audience'}",
             f"- Language: {lang}", "",
             "## Delivery", "",
             f"- Pace: {pace}, about {ad['pace']['voWpm']:g} words a minute ({sum(c['words'] for c in cue_list)} words in "
             f"{pl.seconds:.1f} s of video)",
             f"- Mood: {', '.join(mood.get('keywords') or []) or 'see brand/DIRECTION.md'}"]
    if pv.get("delivery"):
        lines.append(f"- Notes: {pv['delivery']}")
    if ad.get("music"):
        mu = ad["music"]
        lines.append(f"- Music under it (for reference): {mu.get('mood', '-')}" +
                     (f", {mu['bpm'][0]:g}-{mu['bpm'][1]:g} bpm" if mu.get("bpm") else "") +
                     (f", energy {mu['energy']}" if mu.get("energy") else ""))
    if pv.get("pronunciations"):
        lines += ["", "## Pronunciation", ""] + [f"- {x['text']}: say \"{x['say']}\"" for x in pv["pronunciations"]]
    lines += ["", "## Lines and timing", "",
              "Record each line as its own take if you can (one file per scene, named after the scene id), with "
              "half a second of room tone before and after. 48 kHz WAV, mono, peaks below -1 dBFS.", ""]
    for c in cue_list:
        lines.append(f"- `{c['scene']}` ({_ts(c['start'], '.')[3:]}–{_ts(c['end'], '.')[3:]}, about "
                     f"{c['end'] - c['start']:.1f} s): {c['text']}")
    if not cue_list:
        lines.append("- No voice-over lines in this piece yet (add \"vo\" to the scenes in video.json).")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ composition

@dataclass
class Build:
    page: Path
    assets: list[dict]  # {path (project-relative), sha256, role}


def compose(p: dl.Project, pid: str, piece: dict, pl: Plan, ad: dict, fmt: str, dest: Path, draft: bool) -> Build:
    """The composition for one format in dest: the runtime, fonts, logo and motif copied in (a
    snapshot: the render reads only these copies), verified against the hashes the gates used."""
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "fonts").mkdir(parents=True)
    (dest / "assets").mkdir()
    for name in ("timeline.js", "motion.js", "artdir.js"):
        shutil.copyfile(MEDIA / name, dest / name)
    w, h = FORMATS[fmt]["size"]
    root = (f'<div id="root" data-composition-id="{pid}" data-width="{w}" data-height="{h}" '
            f'data-duration="{pl.frames / pl.fps:.6f}" data-fps="{pl.fps}" data-no-timeline></div>')
    html = (MEDIA / "video.html").read_text(encoding="utf-8").replace('<div id="root"></div>', root, 1)
    (dest / "video.html").write_text(html, encoding="utf-8")
    assets: list[dict] = []
    css = ["/* generated by render_video.py from the video concept */"]
    for face in ad["faces"]:
        if face.get("source") == "system":
            continue
        name = f"{face['sha256'][:12]}{Path(face['path']).suffix}"
        target = dest / "fonts" / name
        shutil.copyfile(face["abs"], target)
        if sha256_file(target) != face["sha256"]:
            raise InputError(f"{face['path']} changed while the render was starting; run it again")
        assets.append({"path": face["path"], "sha256": face["sha256"], "role": "font"})
        css.append(f"@font-face {{ font-family: {script_json(face['family'])}; src: url(fonts/{name}); "
                   f"font-weight: {face['weight']}; font-style: {face['style']}; }}")
    (dest / "fonts.generated.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    page_ad = {k: v for k, v in ad.items() if k != "faces"}
    page_ad["faces"] = [{k: v for k, v in f.items() if k in ("family", "weight", "style")} for f in ad["faces"]]
    files = {}
    for role, rel in (("logo", ad.get("logo")), ("motif", (ad.get("motif") or {}).get("asset"))):
        if not rel:
            continue
        src = resolve_inside(p.root, rel, role, must_exist=True)
        target = dest / "assets" / f"{role}{src.suffix}"
        shutil.copyfile(src, target)
        assets.append({"path": rel, "sha256": sha256_file(target), "role": role})
        files[role] = f"assets/{role}{src.suffix}"
    if "motif" in files:
        page_ad["motif"] = dict(ad["motif"], src=files["motif"])
    safe = FORMATS[fmt]["safe"][ad.get("safeAreas", "standard")]
    data = {"id": pid, "width": w, "height": h, "fps": pl.fps, "frames": pl.frames, "safe": safe, "draft": draft,
            "assets": {k: v for k, v in files.items() if k == "logo"}, "scenes": [s.page() for s in pl.scenes]}
    (dest / "direction.generated.js").write_text("window.AD = " + script_json(page_ad) + ";\n", encoding="utf-8")
    (dest / "video.generated.js").write_text("window.VIDEO = " + script_json(data) + ";\n", encoding="utf-8")
    return Build(dest / "video.html", assets)


def write_text_outputs(write, pid: str, piece: dict, pl: Plan, ad: dict, mood: dict) -> tuple[list[dict], list[str], list[dict]]:
    """script.md, voice-prompt.md, cues.json and the planned caption sidecars, through write(rel, text)."""
    cue_list, errors, reviews = cues(pl, piece, ad)
    write("voice/script.md", script_md(pid, piece, pl, cue_list, ad))
    write("voice/voice-prompt.md", voice_prompt_md(pid, piece, pl, cue_list, ad, mood))
    write("voice/cues.json", dumps_pretty({"piece": pid, "timing": "planned", "fps": pl.fps, "frames": pl.frames,
                                           "cues": cue_list}))
    side = (piece.get("captions") or {}).get("sidecar", ["srt", "vtt"])
    if cue_list:
        if "srt" in side:
            write("voice/captions.planned.srt", srt(cue_list))
        if "vtt" in side:
            write("voice/captions.planned.vtt", vtt(cue_list))
    return cue_list, errors, reviews
