"""Creative direction: loading, token resolution, content/input hashes, approvals and gates.

Files (project-owned, committed):
  brand/direction.json        the authority (schemas/direction.schema.json)
  brand/concepts/<family>/<run>/<id>.json   concepts (schemas/concept.schema.json)
  brand/approvals.json        owner approvals (schemas/approvals.schema.json), written only by
                              `direction.py approve` after the owner decides
  brand/runs/<family>/<run>.json  production run manifests
Hashes (version 2, written since 1.8):
  direction content = the direction minus `families` (requesting or briefing a family, and choosing
                      a concept, are not changes of direction); direction inputs = every resolved
                      role and font value, font file hashes and the motif asset hash.
  concept content   = the concept file; concept inputs = the direction content, the concept's own
                      family entry (requested, brief) and everything the concept resolves to for a
                      renderer (colours, type, font file hashes, motion values, the motif's hash).
  So a change reaches only what depends on it: briefing the video family leaves store approvals
  current, and a role colour invalidates the concepts that use it.
Version 1 (1.7) records carry no hashVersion. They are checked with the 1.7 algorithm on a copy of
the direction without the families 1.7 did not know (video), which reproduces what was approved;
their coarser coupling (any family's brief invalidates every concept) stays until re-approved.
A record approves (content, inputs). Change either and the gate reports the record as stale.
"""

from __future__ import annotations

import copy
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import color as col
from . import schema
from .dtcg import TokenError, Tokens, alias_target, is_alias, FONT_EXT
from .fsutil import (InputError, canonical, dumps_pretty, load_json, resolve_inside, run_id, safe_rel,
                     sha256_file, sha256_text, write_atomic)

DIRECTION = "brand/direction.json"
APPROVALS = "brand/approvals.json"
CONCEPTS = "brand/concepts"
RUNS = "brand/runs"
FAMILIES = ("store", "marketing", "icon", "illustration", "video")
V1_FAMILIES = ("store", "marketing", "icon", "illustration")  # the families 1.7 hashed
HASH_VERSION = 2
GENERIC_FONTS = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif",
                 "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "emoji"}
DEFAULT_DISPLAY_WIDTH = {"store": 320, "marketing": 500, "video": 360}
DEFAULT_HEAD_SCALE = {"store": 0.072, "marketing": 0.06, "video": 0.075}
DEFAULT_SUB_RATIO = 0.45


class GateError(InputError):
    """A production gate is not met (exit 1)."""


# ------------------------------------------------------------------ discovery and loading

def find_project(start: Path) -> Path | None:
    """The nearest folder at or above start that holds brand/direction.json (stops at a .git root)."""
    p = Path(start).resolve()
    if p.is_file():
        p = p.parent
    for d in [p, *p.parents]:
        if (d / DIRECTION).is_file():
            return d
        if (d / ".git").exists():
            return None
    return None


@dataclass
class Project:
    root: Path
    direction: dict
    tokens: Tokens
    approvals: list[dict] = field(default_factory=list)

    def rel(self, p: Path) -> str:
        return Path(p).resolve().relative_to(self.root.resolve()).as_posix()


def load_project(root: Path) -> Project:
    root = Path(root).resolve()
    f = root / DIRECTION
    if not f.is_file():
        raise InputError(f"no {DIRECTION} under {root}; the creative-director writes it (direction.py init)")
    data = load_json(f)
    schema.check(data, "direction", DIRECTION)
    tok_path = resolve_inside(root, data["tokens"]["source"], "tokens.source", must_exist=True)
    tokens = Tokens.load(tok_path)
    return Project(root, data, tokens, load_approvals(root))


def load_approvals(root: Path) -> list[dict]:
    f = Path(root) / APPROVALS
    if not f.is_file():
        return []
    data = load_json(f)
    schema.check(data, "approvals", APPROVALS)
    return data["records"]


# ------------------------------------------------------------------ references

def resolve_ref(p: Project, ref: str, expected: str | None = None) -> Any:
    """Resolve "{roles.x}", "{fonts.x}" (through the direction) or any token alias."""
    if not is_alias(ref):
        raise InputError(f"{ref!r} is not a token reference like {{color.brand.500}}")
    target = alias_target(ref)
    head, _, name = target.partition(".")
    if head in ("roles", "fonts") and name and "." not in name:
        table = p.direction["tokens"][head]
        if name not in table:
            raise InputError(f"{ref}: the direction defines no {head[:-1]} {name!r} ({', '.join(sorted(table))})")
        return resolve_ref(p, table[name], expected)
    return p.tokens.resolve(target, expected).value


def resolve_warnings(p: Project, ref: str) -> list[str]:
    """Warnings (legacy value forms) met while resolving a colour reference."""
    target = alias_target(ref)
    head, _, name = target.partition(".")
    if head in ("roles", "fonts") and name in p.direction["tokens"][head]:
        target = alias_target(p.direction["tokens"][head][name])
    return p.tokens.resolve(target).warnings


def color_css(p: Project, ref: str) -> str:
    return col.css_rgb(resolve_ref(p, ref, "color")["srgb"])


def color_rgba(p: Project, ref: str) -> tuple[float, float, float, float]:
    return resolve_ref(p, ref, "color")["srgb"]


def css_stack(families: list[str]) -> str:
    """A font-family value safe inside a double-quoted HTML style attribute (names in single quotes)."""
    return ", ".join(f if f in GENERIC_FONTS else "'" + f.replace("'", "").replace('"', "") + "'" for f in families)


def font_role(p: Project, role: str) -> dict:
    """A direction font role -> {family, stack, source, files[{path, abs, sha256, weight, style}], license}."""
    fonts = p.direction["tokens"]["fonts"]
    if role not in fonts:
        raise InputError(f"font role {role!r} is not defined in the direction ({', '.join(sorted(fonts))})")
    ref = alias_target(fonts[role])
    res = p.tokens.resolve(ref, "fontFamily")
    tok = p.tokens.index[res.path][0]
    meta = (tok.get("$extensions") or {}).get(FONT_EXT)
    if not isinstance(meta, dict):
        raise InputError(f"font role {role!r} ({res.path}) has no $extensions[\"{FONT_EXT}\"] record of its source "
                         "and licence; add it with type_scale.py font")
    source = meta.get("source")
    if source not in ("local", "system"):
        raise InputError(f"font role {role!r}: source must be 'local' or 'system' (network fonts are not used; "
                         "download the files with their licence and use 'local')")
    out = {"role": role, "token": res.path, "family": res.value[0], "families": list(res.value),
           "stack": css_stack(res.value), "source": source,
           "license": meta.get("license"), "licenseEvidence": meta.get("licenseEvidence"), "files": []}
    if source == "local":
        if not meta.get("license") or not meta.get("licenseEvidence"):
            raise InputError(f"font role {role!r}: local fonts need 'license' and 'licenseEvidence'")
        files = meta.get("files")
        if not isinstance(files, list) or not files:
            raise InputError(f"font role {role!r}: local fonts need a 'files' list")
        for fe in files:
            rel = safe_rel(fe.get("path", ""), f"font role {role} file")
            path = resolve_inside(p.root, rel, f"font role {role} file", must_exist=True)
            digest = sha256_file(path)
            if fe.get("sha256") and fe["sha256"] != digest:
                raise InputError(f"font role {role!r}: {rel} changed since it was recorded (sha256 differs); "
                                 "re-record it with type_scale.py font")
            out["files"].append({"path": rel, "abs": str(path), "sha256": digest,
                                 "weight": fe.get("weight", 400), "style": fe.get("style", "normal")})
    else:
        if not meta.get("availability"):
            raise InputError(f"font role {role!r}: system fonts need an 'availability' note (which systems have it)")
    return out


def face_for(font: dict, weight: float, italic: bool) -> dict | None:
    """The local file that serves weight/italic (exact weight, or a [min, max] variable range)."""
    style = "italic" if italic else "normal"
    for f in font["files"]:
        w = f["weight"]
        ok = (w[0] <= weight <= w[1]) if isinstance(w, list) else w == weight
        if ok and f["style"] == style:
            return f
    return None


# ------------------------------------------------------------------ hashes

def direction_core(direction: dict, version: int = HASH_VERSION) -> dict:
    core = copy.deepcopy(direction)
    if version >= 2:
        core.pop("families", None)
        return core
    fams = core.get("families", {})
    for name in [n for n in fams if n not in V1_FAMILIES]:
        del fams[name]  # 1.7 could not have hashed a family it did not know
    for fam in fams.values():
        fam.pop("selected", None)
    return core


def asset_sha(path: Path, version: int = HASH_VERSION) -> str:
    """The hash of a brand asset. From version 2, an SVG (text) is hashed with LF line endings, so a
    checkout with core.autocrlf (CRLF on Windows) hashes the same as everywhere else."""
    if version >= 2 and Path(path).suffix.lower() == ".svg":
        return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return sha256_file(path)


def direction_inputs(p: Project, version: int = HASH_VERSION) -> dict:
    d = p.direction
    roles = {}
    for k, v in sorted(d["tokens"]["roles"].items()):
        c = resolve_ref(p, v, "color")
        roles[k] = f"{c['hex']}/{c['alpha']}"
    fonts = {}
    for role in sorted(d["tokens"]["fonts"]):
        f = font_role(p, role)
        fonts[role] = {"families": f["families"], "source": f["source"], "license": f["license"],
                       "files": sorted((x["path"], x["sha256"]) for x in f["files"])}
    motif = None
    if d.get("motif", {}).get("asset"):
        mp = resolve_inside(p.root, d["motif"]["asset"], "motif.asset", must_exist=True)
        motif = asset_sha(mp, version)
    return {"roles": roles, "fonts": fonts, "motif": motif}


def direction_hashes(p: Project, version: int = HASH_VERSION) -> tuple[str, str]:
    return (sha256_text(canonical(direction_core(p.direction, version))),
            sha256_text(canonical(direction_inputs(p, version))))


def record_version(rec: dict) -> int:
    return rec.get("hashVersion", 1)


def _refs(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += _refs(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _refs(v)
    elif is_alias(obj):
        out.append(obj)
    return out


# ------------------------------------------------------------------ concepts

def concept_path(family: str, run: str, cid: str) -> str:
    return f"{CONCEPTS}/{family}/{run}/{cid}.json"


def load_concept(p: Project, rel: str) -> dict:
    safe_rel(rel, "concept")
    path = resolve_inside(p.root, rel, "concept", must_exist=True)
    data = load_json(path)
    schema.check(data, "concept", rel)
    fam = data["family"]
    errs = schema.validate(data["spec"], {"$ref": f"#/$defs/{fam}Spec"}, schema.load("concept"), "$.spec")
    if errs:
        raise InputError(f"{rel}: spec does not match the {fam} concept schema:\n  " + "\n  ".join(errs[:40]))
    expected = concept_path(fam, data["run"], data["id"])
    if rel != expected:
        raise InputError(f"{rel}: a {fam} concept with run {data['run']} and id {data['id']} must live at {expected}")
    problems = spec_problems(p, fam, data["spec"])
    if problems:
        raise InputError(f"{rel}:\n  " + "\n  ".join(problems))
    if "path" in data["preview"]:
        pv = resolve_inside(p.root, data["preview"]["path"], "preview.path")
        if pv.is_file() and sha256_file(pv) != data["preview"]["sha256"]:
            raise InputError(f"{rel}: preview {data['preview']['path']} no longer matches its recorded sha256")
    return data


def spec_problems(p: Project, family: str, spec: dict) -> list[str]:
    """Semantic checks the schema can't express. Every token reference must resolve."""
    errs: list[str] = []
    for ref in _refs(spec):
        try:
            resolve_ref(p, ref)
        except (InputError, TokenError) as e:
            errs.append(str(e))
    if family in ("store", "marketing", "video"):
        bgs = spec["backgrounds"]
        if not bgs:
            errs.append("backgrounds: define at least one")
        for name, b in bgs.items():
            if b["recipe"] == "solid" and "color" not in b:
                errs.append(f"backgrounds.{name}: a solid background needs 'color'")
            if b["recipe"] == "linear" and "stops" not in b:
                errs.append(f"backgrounds.{name}: a linear background needs 'stops'")
        if spec["defaultBackground"] not in bgs:
            errs.append(f"defaultBackground {spec['defaultBackground']!r} is not one of the backgrounds")
        if spec["defaultLayout"] not in spec["layouts"]:
            errs.append(f"defaultLayout {spec['defaultLayout']!r} is not one of the allowed layouts")
        fg = spec.get("featureGraphic")
        if fg and fg["background"] not in bgs:
            errs.append(f"featureGraphic.background {fg['background']!r} is not one of the backgrounds")
        fonts = p.direction["tokens"]["fonts"]
        for part in ("head", "sub", "kicker"):
            ts = spec["caption"].get(part)
            if ts and ts["font"] not in fonts:
                errs.append(f"caption.{part}.font {ts['font']!r} is not a direction font role ({', '.join(sorted(fonts))})")
        if spec.get("motif", {}).get("use") and not p.direction.get("motif", {}).get("asset"):
            errs.append("motif.use is true but the direction has no motif.asset")
    if family == "video":
        errs += _video_spec_problems(p, spec)
    if family == "icon":
        b = spec["background"]
        if b["recipe"] == "solid" and "color" not in b:
            errs.append("background: a solid background needs 'color'")
        if b["recipe"] == "linear" and "stops" not in b:
            errs.append("background: a linear background needs 'stops'")
    return errs


def _video_spec_problems(p: Project, spec: dict) -> list[str]:
    errs: list[str] = []
    m = spec["motion"]
    for group, want in (("durations", "duration"), ("easing", "cubicBezier")):
        for name, ref in m[group].items():
            try:
                resolve_ref(p, ref, want)
            except (InputError, TokenError) as e:
                errs.append(f"motion.{group}.{name}: {e}")
    if m["defaultTransition"] not in m["transitions"]:
        errs.append(f"motion.defaultTransition {m['defaultTransition']!r} is not one of motion.transitions")
    end = spec.get("endCard")
    if end and end.get("background", spec["defaultBackground"]) not in spec["backgrounds"]:
        errs.append(f"endCard.background {end['background']!r} is not one of the backgrounds")
    sub = spec.get("subtitles")
    fonts = p.direction["tokens"]["fonts"]
    if sub and sub["font"] not in fonts:
        errs.append(f"subtitles.font {sub['font']!r} is not a direction font role ({', '.join(sorted(fonts))})")
    if spec.get("logo"):
        try:
            resolve_inside(p.root, spec["logo"], "logo", must_exist=True)
        except InputError as e:
            errs.append(str(e))
    return errs


def concept_hashes(p: Project, rel: str, concept: dict, version: int = HASH_VERSION) -> tuple[str, str]:
    content = sha256_text(canonical({"path": rel, "concept": concept}))
    if version >= 2:
        fam = dict(p.direction["families"].get(concept["family"]) or {})
        fam.pop("selected", None)
        resolved_family = _portable(resolve_family(p, concept["family"], concept))
        files = {}
        for key, rel_ in (("motif", (resolved_family.get("motif") or {}).get("asset")), ("logo", resolved_family.get("logo"))):
            if rel_:
                files[key] = asset_sha(resolve_inside(p.root, rel_, key, must_exist=True))
        inputs = sha256_text(canonical({"direction": sha256_text(canonical(direction_core(p.direction, 2))),
                                        "family": fam, "resolved": resolved_family, "files": files}))
        return content, inputs
    d_content, d_inputs = direction_hashes(p, 1)
    resolved = {r: _jsonable(resolve_ref(p, r)) for r in sorted(set(_refs(concept["spec"])))}
    fonts = {}
    for ts in (concept["spec"].get("caption") or {}).values():
        if isinstance(ts, dict) and "font" in ts:
            f = font_role(p, ts["font"])
            fonts[ts["font"]] = sorted((x["path"], x["sha256"]) for x in f["files"])
    inputs = sha256_text(canonical({"direction": [d_content, d_inputs], "resolved": resolved, "fonts": fonts}))
    return content, inputs


def _portable(obj: Any) -> Any:
    """A resolved family without machine-specific absolute paths (hashes must match on every OS)."""
    if isinstance(obj, dict):
        return {k: _portable(v) for k, v in obj.items() if k != "abs"}
    if isinstance(obj, list):
        return [_portable(v) for v in obj]
    return obj


def _jsonable(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items() if k != "srgb"}
    return v


# ------------------------------------------------------------------ approvals and gates

def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _latest(records: list[dict], **match: Any) -> dict | None:
    hits = [r for r in records if all(r.get(k) == v for k, v in match.items())]
    return hits[-1] if hits else None


@dataclass
class Gate:
    ok: bool
    problems: list[str]
    records: list[str]
    direction: tuple[str, str] | None = None
    concept: tuple[str, str] | None = None
    concept_rel: str | None = None
    legacy: list[str] = field(default_factory=list)  # current records still on 1.7 (version 1) hashing


def _stale_what(rec: dict, now: tuple[str, str], content: str, inputs: str) -> str:
    return content if rec["hash"] != now[0] else inputs


def gate(p: Project, family: str | None) -> Gate:
    """Is the direction approved as it stands, and (for a family) the selected concept too?"""
    problems: list[str] = []
    records: list[str] = []
    legacy: list[str] = []
    dh = direction_hashes(p)
    rec = _latest(p.approvals, gate="direction", subject=DIRECTION)
    if rec is None:
        problems.append("the direction has no owner approval (Gate 1)")
    else:
        now = direction_hashes(p, record_version(rec))
        if (rec["hash"], rec["inputs"]) != now:
            what = _stale_what(rec, now, "its content", "a token, font or motif it resolves")
            problems.append(f"the direction approval {rec['id']} is stale: {what} changed since {rec['at']}")
        else:
            records.append(rec["id"])
            if record_version(rec) < HASH_VERSION:
                legacy.append(rec["id"])
    g = Gate(not problems, problems, records, dh, legacy=legacy)
    if family is None:
        return g
    fam = p.direction["families"].get(family)
    if not fam or not fam.get("requested"):
        g.problems.append(f"the direction does not request the {family} family")
    elif not fam.get("selected"):
        g.problems.append(f"no {family} concept is selected (Gate 2: the owner picks one, then direction.py approve)")
    else:
        rel = fam["selected"]
        g.concept_rel = rel
        concept = load_concept(p, rel)
        if concept["family"] != family:
            g.problems.append(f"{rel} is a {concept['family']} concept, not {family}")
        crec = _latest(p.approvals, gate="concept", family=family, subject=rel)
        try:
            g.concept = concept_hashes(p, rel, concept)
        except InputError:
            if crec is None or record_version(crec) >= 2:
                raise
            g.concept = None  # a 1.7 record is judged by the 1.7 hashing alone
        if crec is None:
            g.problems.append(f"the {family} concept {rel} has no owner approval (Gate 2)")
        else:
            now = concept_hashes(p, rel, concept, record_version(crec))
            if (crec["hash"], crec["inputs"]) != now:
                what = _stale_what(crec, now, "the concept file", "the direction or a value it resolves")
                g.problems.append(f"the {family} concept approval {crec['id']} is stale: {what} changed since {crec['at']}")
            else:
                g.records.append(crec["id"])
                if record_version(crec) < HASH_VERSION:
                    g.legacy.append(crec["id"])
    g.ok = not g.problems
    return g


def approve(p: Project, gate_name: str, by: str, evidence: str, recorded_by: str,
            family: str | None = None, concept_rel: str | None = None, scope: str | None = None) -> dict:
    """Record an owner decision bound to the current hashes. The caller (the main session) must have
    the owner's decision in hand; agents never call this on their own."""
    by, evidence = (by or "").strip(), (evidence or "").strip()
    if not by or len(evidence) < 3:
        raise InputError("an approval needs --by (the owner) and --evidence (where and how they decided)")
    if gate_name == "direction":
        h = direction_hashes(p)
        subject = DIRECTION
    elif gate_name == "concept":
        if family not in FAMILIES or not concept_rel:
            raise InputError("a concept approval needs --family and --concept")
        concept = load_concept(p, concept_rel)
        if concept["family"] != family:
            raise InputError(f"{concept_rel} is a {concept['family']} concept, not {family}")
        dg = gate(p, None)
        if not dg.ok:
            raise GateError("approve the direction first: " + "; ".join(dg.problems))
        fam = p.direction["families"].get(family)
        if not fam or not fam.get("requested"):
            raise InputError(f"the direction does not request the {family} family; the director adds it first")
        fam["selected"] = concept_rel  # selection is excluded from the direction hash
        write_atomic(p.root / DIRECTION, dumps_pretty(p.direction))
        h = concept_hashes(p, concept_rel, concept)
        subject = concept_rel
    elif gate_name == "exception":
        if not scope:
            raise InputError("an exception approval needs --scope (what it allows)")
        h = (sha256_text(scope), sha256_text(canonical(direction_hashes(p))))
        subject = DIRECTION
    else:
        raise InputError(f"unknown gate {gate_name!r} (storyboard, mix and review approvals are recorded "
                         "through harnesslib.video)")
    return record_approval(p, gate_name, subject, h, by, evidence, recorded_by,
                           family=family if gate_name != "direction" else None, scope=scope)


def record_approval(p: Project, gate_name: str, subject: str, h: tuple[str, str], by: str, evidence: str,
                    recorded_by: str, family: str | None = None, scope: str | None = None,
                    extra: dict | None = None) -> dict:
    """Append one owner decision to brand/approvals.json (hash version 2)."""
    by, evidence = (by or "").strip(), (evidence or "").strip()
    if not by or len(evidence) < 3:
        raise InputError("an approval needs --by (the owner) and --evidence (where and how they decided)")
    rec = {"id": run_id(), "gate": gate_name, "subject": subject, "hash": h[0], "inputs": h[1],
           "by": by, "evidence": evidence, "at": now_utc(), "recordedBy": recorded_by, "hashVersion": HASH_VERSION}
    if family:
        rec["family"] = family
    if scope:
        rec["scope"] = scope
    rec.update(extra or {})
    p.approvals.append(rec)
    doc = {"schemaVersion": 1, "records": p.approvals}
    schema.check(doc, "approvals", APPROVALS)
    write_atomic(p.root / APPROVALS, dumps_pretty(doc))
    return rec


def exception_approved(p: Project, scope: str) -> str | None:
    rec = _latest(p.approvals, gate="exception", scope=scope)
    if not rec:
        return None
    want = (sha256_text(scope), sha256_text(canonical(direction_hashes(p, record_version(rec)))))
    return rec["id"] if (rec["hash"], rec["inputs"]) == want else None


# ------------------------------------------------------------------ resolution for renderers

def resolve_family(p: Project, family: str, concept: dict) -> dict:
    """Everything a renderer needs, as plain JSON (colours are CSS strings, fonts are stacks)."""
    spec = concept["spec"]
    if family == "illustration":
        return {"style": spec["style"], "lighting": spec["lighting"], "background": spec["background"],
                "texture": spec.get("texture"), "shot": spec.get("shot"), "storyWorld": spec["storyWorld"],
                "ratio": spec["ratio"], "negatives": spec.get("negatives", []),
                "palette": [{"ref": r, "hex": resolve_ref(p, r, "color")["hex"]} for r in spec["palette"]]}
    if family == "icon":
        b = spec["background"]
        bg = {"recipe": b["recipe"], "space": b.get("space", "oklab"), "angle": b.get("angle", 180)}
        if b["recipe"] == "solid":
            bg["color"] = resolve_ref(p, b["color"], "color")["hex"]
        else:
            bg["stops"] = [resolve_ref(p, s, "color")["hex"] for s in b["stops"]]
        return {"background": bg, "glyphScale": spec["glyphScale"], "glyphOffset": spec.get("glyphOffset", [0, 0]),
                "qualityTarget": spec.get("qualityTarget")}
    roles = {k: color_css(p, v) for k, v in p.direction["tokens"]["roles"].items()}
    backgrounds = {}
    for name, b in spec["backgrounds"].items():
        out: dict = {"recipe": b["recipe"], "space": b.get("space", "oklab"), "angle": b.get("angle", 180),
                     "text": {k: color_css(p, v) for k, v in b["text"].items()}}
        out["text"].setdefault("accent", roles["accent"])
        out["text"].setdefault("onAccent", roles.get("onAccent", roles["canvas"]))
        if b["recipe"] == "solid":
            out["color"] = color_css(p, b["color"])
        else:
            out["stops"] = [color_css(p, s) for s in b["stops"]]
        out["panel"] = color_css(p, b["panel"]) if "panel" in b else roles.get("surface", roles["canvas"])
        backgrounds[name] = out
    fonts_used: dict[str, dict] = {}
    caption = {"align": spec["caption"]["align"], "accent": spec["caption"].get("accent", "color"),
               "headScale": spec["caption"].get("headScale", DEFAULT_HEAD_SCALE[family]),
               "subRatio": spec["caption"].get("subRatio", DEFAULT_SUB_RATIO)}
    faces = []
    for part in ("head", "sub", "kicker"):
        ts = spec["caption"].get(part)
        if not ts:
            continue
        f = fonts_used.setdefault(ts["font"], font_role(p, ts["font"]))
        weight, italic = ts["weight"], ts.get("italic", False)
        caption[part] = {"family": f["family"], "stack": f["stack"], "weight": weight, "italic": italic,
                         "tracking": ts.get("tracking", 0), "lineHeight": ts.get("lineHeight", 1.15 if part == "head" else 1.35),
                         "case": ts.get("case", "as-written"), "source": f["source"]}
        if f["source"] == "local":
            face = face_for(f, weight, italic)
            if face is None:
                raise InputError(f"caption.{part}: font role {ts['font']!r} has no local file for weight {weight}"
                                 f"{' italic' if italic else ''}; add it with type_scale.py font")
            faces.append({"family": f["family"], "weight": weight, "style": "italic" if italic else "normal",
                          "path": face["path"], "abs": face["abs"], "sha256": face["sha256"]})
        else:
            faces.append({"family": f["family"], "weight": weight, "style": "italic" if italic else "normal",
                          "source": "system"})
    type_roles = {}
    for role in p.direction["tokens"]["fonts"]:
        f = fonts_used.get(role) or font_role(p, role)
        type_roles[role] = {"family": f["family"], "stack": f["stack"]}
    out = {"family": family, "roles": roles, "type": type_roles, "backgrounds": backgrounds, "caption": caption,
           "layouts": spec["layouts"], "defaultLayout": spec["defaultLayout"],
           "defaultBackground": spec["defaultBackground"],
           "displayWidth": spec.get("displayWidth", DEFAULT_DISPLAY_WIDTH[family]),
           "faces": _dedupe_faces(faces), "motif": None}
    if family == "store":
        dv = spec["device"]
        out["device"] = {"style": dv["style"], "radius": dv.get("radius", 0.11), "shadow": dv.get("shadow", "soft"),
                         "bezel": color_css(p, dv["bezel"]) if "bezel" in dv else roles["ink"]}
        out["featureGraphic"] = spec.get("featureGraphic") or {"layout": "split-device-right",
                                                              "background": spec["defaultBackground"]}
    if family in ("marketing", "video") and spec.get("logo"):
        out["logo"] = spec["logo"]
    if family == "video":
        out.update(_resolve_video(p, spec, roles))
    m = spec.get("motif")
    if m and m.get("use"):
        out["motif"] = {"asset": p.direction["motif"]["asset"], "opacity": m.get("opacity", 0.12),
                        "placement": m.get("placement", "corner"), "scale": m.get("scale", 0.6)}
    return out


VIDEO_TEMPLATES = ("title", "feature", "stat", "end-card")


def _ms(p: Project, ref: str) -> int:
    d = resolve_ref(p, ref, "duration")
    return round(d["value"] * (1000 if d["unit"] == "s" else 1))


def _resolve_video(p: Project, spec: dict, roles: dict) -> dict:
    """The motion, pace, subtitle and end-card values of a video concept, ready for the page."""
    m = spec["motion"]
    motion = {"durations": {k: _ms(p, v) for k, v in m["durations"].items()},
              "easing": {k: "cubic-bezier({})".format(", ".join(f"{x:g}" for x in resolve_ref(p, v, "cubicBezier")))
                         for k, v in m["easing"].items()},
              "stagger": {"perItemMs": m.get("stagger", {}).get("perItemMs", 40),
                          "maxItems": m.get("stagger", {}).get("maxItems", 5)},
              "transitions": m["transitions"], "defaultTransition": m["defaultTransition"],
              "textIn": m["textIn"], "textOut": m.get("textOut", "none"), "motifMotion": m.get("motifMotion", "none")}
    motion["easing"].setdefault("emphasis", motion["easing"]["standard"])
    pace = {"readingWpm": spec["pace"]["readingWpm"], "minHold": spec["pace"]["minHold"],
            "voWpm": spec["pace"].get("voWpm", 150)}
    out: dict = {"motion": motion, "pace": pace, "sceneTemplates": spec.get("sceneTemplates", list(VIDEO_TEMPLATES)),
                 "endCard": {"background": (spec.get("endCard") or {}).get("background", spec["defaultBackground"]),
                             "logo": (spec.get("endCard") or {}).get("logo", True)},
                 "music": spec.get("music"), "voice": spec.get("voice"), "safeAreas": spec.get("safeAreas", "standard")}
    sub = spec.get("subtitles")
    if sub:
        f = font_role(p, sub["font"])
        out["subtitles"] = {"style": sub["style"], "position": sub["position"], "family": f["family"], "stack": f["stack"],
                            "weight": sub["weight"], "ink": color_css(p, sub["ink"]),
                            "plate": color_css(p, sub["plate"]) if "plate" in sub else roles["canvas"],
                            "maxCharsPerLine": sub.get("maxCharsPerLine", 32), "maxLines": sub.get("maxLines", 2)}
    return out


def _dedupe_faces(faces: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in faces:
        key = (f["family"], f["weight"], f["style"])
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


@dataclass
class Production:
    project: Project
    family: str
    concept_rel: str
    concept: dict
    resolved: dict
    gate: Gate


def production(p: Project, family: str) -> Production:
    """The resolved, approved family for a production command, or GateError with every reason."""
    g = gate(p, family)
    if not g.ok:
        raise GateError(f"{family} production needs owner approval:\n  - " + "\n  - ".join(g.problems) +
                        "\n  Render a draft with the preview command meanwhile.")
    concept = load_concept(p, g.concept_rel)  # type: ignore[arg-type]
    return Production(p, family, g.concept_rel, concept, resolve_family(p, family, concept), g)  # type: ignore[arg-type]


def preview(p: Project, family: str, concept_rel: str | None) -> tuple[str, dict, dict]:
    """A draft: any concept (or the selected one), no approval needed. Never for production output."""
    rel = concept_rel or (p.direction["families"].get(family) or {}).get("selected")
    if not rel:
        raise InputError(f"preview needs --concept (no {family} concept is selected yet)")
    concept = load_concept(p, rel)
    if concept["family"] != family:
        raise InputError(f"{rel} is a {concept['family']} concept, not {family}")
    return rel, concept, resolve_family(p, family, concept)


# ------------------------------------------------------------------ run manifests

def write_run_manifest(root: Path, manifest: dict) -> Path:
    schema.check(manifest, "run-manifest", "run manifest")
    path = Path(root) / RUNS / manifest["family"] / f"{manifest['runId']}.json"
    if path.exists():
        raise InputError(f"{path} exists; run manifests are immutable")
    write_atomic(path, dumps_pretty(manifest))
    return path
