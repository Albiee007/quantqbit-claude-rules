#!/usr/bin/env python3
"""Creative direction: write, check, approve and resolve a project's visual direction.

  init      write a draft brand/direction.json (refuses if one exists) and its DIRECTION.md summary
  validate  the direction and every concept: schema, token references, font records and licences,
            and each concept's declared caption/background pairs (computed contrast)
  status    which gates are met: the direction (Gate 1) and each requested family's concept (Gate 2)
  approve   record an owner decision bound to the current content and resolved inputs. Run only by
            the main session after the owner has decided; --by and --evidence are required
  summary   regenerate brand/DIRECTION.md from brand/direction.json (never edit the .md by hand)
  concept   new: a concept skeleton at brand/concepts/<family>/<run>/<id>.json
            check: validate one concept and print what it resolves to, its contrast pairs and signals
  resolve   the resolved values a renderer or illustrator uses (JSON); draft concepts are labelled
  signals   diagnostic: features that repeat the harness's 1.6 defaults (never a gate)
  compare   diagnostic: structure and palette distance between two images (needs Pillow)
  runs      list production run manifests under brand/runs/
  migrate   report what predates 1.7 (1.6 mockup kits, copies of the 1.6 templates, plan entries that
            point at harness templates) and how to move each one; changes nothing

Usage:
  python direction.py init --name "Fernway" [--project .] [--tokens brand/tokens.json]
  python direction.py validate [--project .]
  python direction.py status [--project .]
  python direction.py approve --gate direction --by "Owner Name" --evidence "chat 2026-10-02: 'approved'"
  python direction.py approve --gate concept --family store --concept brand/concepts/store/<run>/b.json --by ... --evidence ...
  python direction.py approve --gate exception --scope "store:frame:05-brand:layout=inset" --by ... --evidence ...
  python direction.py concept new --family store --id b --name "Field notes" [--run <run id>]
  python direction.py concept check brand/concepts/store/<run>/b.json
  python direction.py resolve store [--concept <file>]
  python direction.py signals <concept.json | frames.json | plan.md | file.svg | file.html>
  python direction.py compare a.png b.png
  python direction.py migrate
Exit codes: 0 done, 1 invalid data or an unmet gate, 2 bad arguments or a missing dependency.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    from harnesslib import contrast as con
    from harnesslib import direction as dl
    from harnesslib import fingerprint, schema
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import (InputError, OperationalError, UsageError, dumps_pretty, load_json, run_id,
                                   write_atomic)
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)


def root_of(a: argparse.Namespace) -> Path:
    r = Path(a.project).resolve()
    if not r.is_dir():
        raise UsageError(f"--project {a.project}: not a folder")
    return r


# ------------------------------------------------------------------ init / summary

def skeleton(name: str, tokens: str) -> dict:
    return {
        "schemaVersion": 1, "project": name, "revision": 1,
        "summary": "DRAFT: replace with two or three sentences on how this product should look and feel, and why.",
        "tokens": {"source": tokens,
                   "roles": {"canvas": "{color.canvas}", "ink": "{color.ink}", "inkMuted": "{color.inkMuted}",
                             "accent": "{color.accent}"},
                   "fonts": {"display": "{font.display}", "text": "{font.text}"}},
        "context": {"facts": [], "preferences": [], "inferences": [],
                    "openQuestions": ["Which existing brand choices must be kept?"]},
        "mood": {"keywords": [], "axes": {}},
        "references": [], "antiReferences": [], "keep": [],
        "families": {f: {"requested": False} for f in dl.FAMILIES},
        "exceptions": [],
    }


def init(a: argparse.Namespace) -> int:
    root = root_of(a)
    target = root / dl.DIRECTION
    if target.exists():
        raise UsageError(f"{target} exists; edit it (and bump 'revision') instead of starting another")
    doc = skeleton(a.name, a.tokens)
    schema.check(doc, "direction", dl.DIRECTION)
    write_atomic(target, dumps_pretty(doc))
    print(f"wrote {target} (draft). Fill it from the project's context, then: direction.py validate")
    write_summary(root, quiet=False)
    return 0


def _fmt_list(items: list, fmt) -> list[str]:
    return [fmt(x) for x in items] or ["- none recorded"]


def write_summary(root: Path, quiet: bool = True) -> Path:
    d = load_json(root / dl.DIRECTION)
    schema.check(d, "direction", dl.DIRECTION)
    try:
        p = dl.load_project(root)
        g = dl.gate(p, None)
        gate_line = "approved (Gate 1)" if g.ok else "; ".join(g.problems)
        problem = None
    except (InputError, TokenError) as e:
        p, gate_line, problem = None, "not checked: the direction does not resolve yet", str(e).splitlines()[0]
    lines = [f"# Creative direction: {d['project']}", "",
             "<!-- Generated from brand/direction.json by direction.py summary. Edit the JSON, then re-run summary. -->", "",
             f"Revision {d['revision']}. Status: {gate_line}.", ""]
    if problem:
        lines += [f"Resolution problem: {problem}", ""]
    if d.get("summary"):
        lines += [d["summary"], ""]
    c = d["context"]
    lines += ["## Context", "", "Facts (with sources):"]
    lines += _fmt_list(c["facts"], lambda x: f"- {x['text']} (source: {x['source']})")
    lines += ["", "Owner preferences:"]
    lines += _fmt_list(c["preferences"], lambda x: f"- {x['text']} ({x['by']}: {x['evidence']})")
    lines += ["", "Inferences (unconfirmed):"]
    lines += _fmt_list(c["inferences"], lambda x: f"- {x['text']} (basis: {x['basis']})")
    lines += ["", "Open questions:"]
    lines += _fmt_list(c["openQuestions"], lambda x: f"- {x}")
    m = d["mood"]
    lines += ["", "## Mood", "", "Keywords: " + (", ".join(m["keywords"]) or "none"), ""]
    for axis, v in m["axes"].items():
        left, right = axis.split("-", 1)
        lines.append(f"- {axis}: {v:+.2f} ({'toward ' + (left if v < 0 else right) if abs(v) > 0.05 else 'neutral'})")
    lines += ["", "## References", ""]
    lines += _fmt_list(d.get("references", []), lambda x: f"- {x['what']}: {x['why']}")
    lines += ["", "Anti-references:"]
    lines += _fmt_list(d.get("antiReferences", []), lambda x: f"- {x['what']}: {x['why']}")
    lines += ["", "Keep from the existing identity:"]
    lines += _fmt_list(d.get("keep", []), lambda x: f"- {x}")
    if d.get("motif"):
        lines += ["", "## Motif", "", d["motif"]["idea"] + (f" (`{d['motif']['asset']}`)" if d["motif"].get("asset") else "")]
    lines += ["", "## Tokens", "", f"Source: `{d['tokens']['source']}`", "", "| Role | Token | Value |", "|---|---|---|"]
    for role, ref in d["tokens"]["roles"].items():
        val = "?"
        if p:
            try:
                val = dl.resolve_ref(p, ref, "color")["hex"]
            except (InputError, TokenError):
                val = "unresolved"
        lines.append(f"| {role} | `{ref}` | {val} |")
    lines += ["", "| Font role | Token | Stack, source, licence |", "|---|---|---|"]
    for role, ref in d["tokens"]["fonts"].items():
        val = "?"
        if p:
            try:
                f = dl.font_role(p, role)
                val = f"{f['stack']}; {f['source']}; {f.get('license') or 'n/a'}"
            except (InputError, TokenError) as e:
                val = f"unresolved ({str(e).splitlines()[0][:80]})"
        lines.append(f"| {role} | `{ref}` | {val} |")
    lines += ["", "## Families", "", "| Family | Requested | Selected concept | Gate 2 |", "|---|---|---|---|"]
    for fam in dl.FAMILIES:
        f = d["families"].get(fam, {"requested": False})
        state = "-"
        if p and f.get("requested"):
            try:
                gg = dl.gate(p, fam)
                own = [x for x in gg.problems if x not in g.problems]
                state = "approved" if gg.ok else "; ".join(own) or "waiting for Gate 1"
            except (InputError, TokenError) as e:
                state = f"error: {str(e).splitlines()[0][:80]}"
        lines.append(f"| {fam} | {'yes' if f.get('requested') else 'no'} | {f.get('selected', '-')} | {state} |")
        if f.get("brief"):
            lines.append(f"|  | brief: {f['brief']} | | |")
    if d.get("exceptions"):
        lines += ["", "## Exceptions", ""] + [f"- `{x['id']}`: {x['text']}" for x in d["exceptions"]]
    recs = dl.load_approvals(root)
    lines += ["", "## Approvals", ""]
    lines += _fmt_list(recs, lambda r: f"- {r['at']} {r['gate']}{' ' + r['family'] if r.get('family') else ''}: "
                                       f"{r['subject']} by {r['by']} ({r['evidence']}); recorded by {r['recordedBy']}")
    out = root / "brand" / "DIRECTION.md"
    write_atomic(out, "\n".join(lines) + "\n")
    if not quiet:
        print(f"wrote {out}")
    return out


def summary(a: argparse.Namespace) -> int:
    write_summary(root_of(a), quiet=False)
    return 0


# ------------------------------------------------------------------ validate / status

def concept_files(root: Path) -> list[str]:
    base = root / dl.CONCEPTS
    return sorted(p.relative_to(root).as_posix() for p in base.glob("*/*/*.json")) if base.is_dir() else []


def pair_findings(r: dict, family: str) -> list[con.Finding]:
    """Computed contrast of each background's caption colours (head and sub) at the concept's sizes."""
    out = []
    cap = r["caption"]
    dw = r["displayWidth"]
    head_px = cap["headScale"] * dw
    sizes = {"head": (head_px, cap["head"]["weight"]), "sub": (head_px * cap["subRatio"], cap["sub"]["weight"])}
    for name, b in r["backgrounds"].items():
        for kind, (px, weight) in sizes.items():
            fg = b["text"][kind]
            need = con.col.text_threshold(px, weight)
            where = f"{family} background {name!r}"
            if b["recipe"] == "solid":
                out.append(con.judge_computed(where, f"{px:.1f}px/{weight:g}", kind, con.computed_solid(fg, b["color"]), need))
            else:
                ratio = con.computed_gradient(fg, b["stops"], b["space"])
                f = con.judge_computed(where, f"{px:.1f}px/{weight:g}", kind, ratio, need, "whole-gradient bound")
                if f.result == con.FAIL:
                    f = con.Finding(where, f.text, kind, ratio, need, con.REVIEW, "computed",
                                    "fails somewhere on the gradient; the render checks where the text sits")
                out.append(f)
    return out


def validate(a: argparse.Namespace) -> int:
    root = root_of(a)
    errors = 0
    try:
        p = dl.load_project(root)
    except (InputError, TokenError) as e:
        print(f"FAIL  direction: {e}")
        return 1
    try:
        dl.direction_hashes(p)
        print(f"ok    {dl.DIRECTION} (revision {p.direction['revision']}): schema, tokens and fonts resolve")
    except (InputError, TokenError) as e:
        print(f"FAIL  direction: {e}")
        errors += 1
    if not errors:
        warns = {w for ref in p.direction["tokens"]["roles"].values() for w in dl.resolve_warnings(p, ref)}
        for w in sorted(warns):
            print(f"WARN  {w}")
    if not p.direction["context"]["facts"]:
        print("WARN  context.facts is empty: cite the project sources the direction rests on")
    for rel in concept_files(root):
        try:
            c = dl.load_concept(p, rel)
            r = dl.resolve_family(p, c["family"], c)
        except (InputError, TokenError) as e:
            print(f"FAIL  {rel}: {e}")
            errors += 1
            continue
        print(f"ok    {rel} ({c['family']}: {c['name']})")
        if c["family"] in ("store", "marketing"):
            for f in pair_findings(r, c["family"]):
                if f.result != con.PASS:
                    print(f.line())
                errors += f.result == con.FAIL
    print(f"validate: {errors} problem(s). Contrast is computed for declared pairs at the concept's sizes "
          "(display width stated in the concept); renders re-check what they draw.")
    return 1 if errors else 0


def status(a: argparse.Namespace) -> int:
    p = dl.load_project(root_of(a))
    g = dl.gate(p, None)
    print(f"Gate 1 direction: {'approved' if g.ok else 'NOT MET: ' + '; '.join(g.problems)}")
    ok = g.ok
    for fam in dl.FAMILIES:
        f = p.direction["families"].get(fam) or {}
        if not f.get("requested"):
            continue
        gg = dl.gate(p, fam)
        own = [x for x in gg.problems if x not in g.problems]
        print(f"Gate 2 {fam}: {'approved (' + gg.concept_rel + ')' if gg.ok else 'NOT MET: ' + '; '.join(own or gg.problems)}")
        ok = ok and gg.ok
    return 0 if ok else 1


def approve(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = dl.load_project(root)
    rec = dl.approve(p, a.gate, a.by, a.evidence, a.recorded_by, a.family, a.concept, a.scope)
    print(f"recorded {rec['gate']} approval {rec['id']} for {rec['subject']} by {rec['by']}")
    write_summary(root)
    return 0


# ------------------------------------------------------------------ concepts

SPEC_SKELETONS = {
    "store": {"backgrounds": {"primary": {"recipe": "solid", "color": "{roles.canvas}",
                                          "text": {"head": "{roles.ink}", "sub": "{roles.inkMuted}"}}},
              "caption": {"head": {"font": "display", "weight": 700}, "sub": {"font": "text", "weight": 400}, "align": "start"},
              "device": {"style": "frame"}, "layouts": ["caption-top"], "defaultLayout": "caption-top",
              "defaultBackground": "primary"},
    "marketing": {"backgrounds": {"primary": {"recipe": "solid", "color": "{roles.canvas}",
                                              "text": {"head": "{roles.ink}", "sub": "{roles.inkMuted}"}}},
                  "caption": {"head": {"font": "display", "weight": 700}, "sub": {"font": "text", "weight": 400}, "align": "start"},
                  "layouts": ["type-start"], "defaultLayout": "type-start", "defaultBackground": "primary"},
    "icon": {"background": {"recipe": "solid", "color": "{roles.accent}"}, "glyphScale": 0.58},
    "illustration": {"style": "DRAFT: one render style from story-art references/style-vocabulary.md",
                     "palette": ["{roles.canvas}", "{roles.accent}"], "lighting": "DRAFT", "background": "DRAFT",
                     "storyWorld": {"setting": "DRAFT", "register": "DRAFT"}, "ratio": "4:3"},
}


def concept_new(a: argparse.Namespace) -> int:
    root = root_of(a)
    run = a.run or run_id()
    rel = dl.concept_path(a.family, run, a.id)
    target = root / rel
    if target.exists():
        raise UsageError(f"{rel} exists; concepts are never overwritten (use a new --id or a new run)")
    doc = {"schemaVersion": 1, "family": a.family, "id": a.id, "run": run, "author": a.author, "name": a.name,
           "idea": "DRAFT: one sentence tying this concept to the direction's mood, motif and audience.",
           "levers": [], "risks": [], "spec": SPEC_SKELETONS[a.family],
           "preview": {"unavailable": "not rendered yet"}}
    schema.check(doc, "concept", rel)
    write_atomic(target, dumps_pretty(doc))
    print(f"wrote {rel}")
    return 0


def concept_check(a: argparse.Namespace) -> int:
    root = root_of(a)
    p = dl.load_project(root)
    try:
        rel = Path(a.file).resolve().relative_to(root).as_posix()
    except ValueError:
        raise UsageError(f"{a.file} is not inside the project {root}") from None
    c = dl.load_concept(p, rel)
    r = dl.resolve_family(p, c["family"], c)
    print(f"ok    {rel}: {c['family']} concept {c['id']!r} ({c['name']})")
    print(f"      preview: {c['preview'].get('path') or 'unavailable: ' + c['preview']['unavailable']}")
    fails = 0
    if c["family"] in ("store", "marketing"):
        for f in pair_findings(r, c["family"]):
            print(f.line())
            fails += f.result == con.FAIL
        sigs = fingerprint.resolved_signals(r)
    elif c["family"] == "icon":
        sigs = fingerprint.icon_signals(r)
    else:
        sigs = fingerprint.text_signals(json.dumps(r))
    for s in sigs:
        print(f"      signal {s['id']}: {s['label']} ({s['detail']})")
    if sigs:
        print("      (signals are for critique, not a verdict: keep what the direction keeps on purpose)")
    return 1 if fails else 0


def resolve(a: argparse.Namespace) -> int:
    p = dl.load_project(root_of(a))
    if a.concept:
        rel, c, r = dl.preview(p, a.family, a.concept)
    else:
        rel, c, r = dl.preview(p, a.family, None)
    g = dl.gate(p, a.family)
    r = {k: v for k, v in r.items() if k != "faces"} | {"faces": [{k: v for k, v in f.items() if k != "abs"} for f in r.get("faces", [])]}
    status_ = "approved" if g.ok and g.concept_rel == rel else "DRAFT (not approved for production)"
    print(json.dumps({"concept": rel, "status": status_, "resolved": r}, indent=2, ensure_ascii=False))
    return 0


# ------------------------------------------------------------------ diagnostics

def signals(a: argparse.Namespace) -> int:
    path = Path(a.file)
    if not path.is_file():
        raise UsageError(f"{a.file}: file not found")
    text = path.read_text(encoding="utf-8", errors="replace")
    sigs: list[dict]
    if path.suffix == ".json":
        data = load_json(path)
        if isinstance(data, dict) and data.get("schemaVersion") == 1 and "spec" in data:
            sigs = fingerprint.icon_signals(data["spec"]) if data.get("family") == "icon" else fingerprint.palette_signals(data["spec"])
        elif isinstance(data, dict) and "frames" in data and "format" not in data:
            sigs = fingerprint.legacy_kit_signals(data)
        else:
            sigs = fingerprint.palette_signals(data)
    else:
        sigs = fingerprint.text_signals(text)
    for s in sigs:
        print(f"signal {s['id']}: {s['label']} ({s['detail']})")
    print(f"{len(sigs)} signal(s) of the 1.6 defaults. Diagnostic only: a project may keep these on purpose.")
    return 0


def compare(a: argparse.Namespace) -> int:
    for f in (a.a, a.b):
        if not Path(f).is_file():
            raise UsageError(f"{f}: file not found")
    try:
        from harnesslib import imaging
    except ImportError:
        raise OperationalError("compare needs Pillow (pip install pillow)") from None
    r = imaging.compare(Path(a.a), Path(a.b))
    print(f"structure (average hash): {r['ahash_distance']}/{r['ahash_bits']} bits differ")
    print(f"palette: weighted deltaE-OK {r['palette_delta_e_ok']} between dominant colours")
    print(f"normalised: {r['normalised']}. Diagnostic only; review the images side by side.")
    return 0


SKIP = {"node_modules", ".git", ".build", ".preview", "dist", "build", ".expo", "Pods", ".venv", "venv", "__pycache__", ".claude"}


def walk(root: Path, max_depth: int = 7):
    for d, dirs, files in os.walk(root):
        depth = len(Path(d).relative_to(root).parts)
        dirs[:] = [] if depth >= max_depth else sorted(x for x in dirs if x not in SKIP)
        for f in files:
            yield Path(d) / f


def migrate(a: argparse.Namespace) -> int:
    root = root_of(a)
    items: list[str] = []
    for f in walk(root):
        rel = f.relative_to(root).as_posix()
        if f.name == "frames.json" and (f.parent / "screens.js").is_file():
            try:
                cfg = load_json(f)
            except InputError:
                continue
            if isinstance(cfg, dict) and "format" not in cfg:
                sigs = ", ".join(sorted({s["id"] for s in fingerprint.legacy_kit_signals(cfg)})) or "none"
                items.append(f"{rel}: a 1.6 mockup kit. It renders unchanged (legacy adapter). To give it the project's "
                             "look: approve a direction and a store concept, then follow store-mockups "
                             f"references/art-direction.md 'Migrating a 1.6 kit'. 1.6 signals: {sigs}")
        elif f.suffix in (".html", ".htm", ".svg"):
            text = f.read_text(encoding="utf-8", errors="replace")
            ids = {s["id"] for s in fingerprint.text_signals(text)}
            if "harness:og-1.6-template" in ids:
                items.append(f"{rel}: a copy of the 1.6 Open Graph template. It still exports; to move it, add the asset to "
                             "brand/canvas.json and replace its plan entry with {\"canvas\": \"<id>\", ...} (brand-assets "
                             "references/asset-matrix.md)")
            if "harness:circle-check-logo" in ids:
                items.append(f"{rel}: the 1.6 logo placeholder geometry (a circle with a check); replace it with the "
                             "chosen direction's mark")
        elif f.name == "exports.json":
            try:
                plan = load_json(f)
            except InputError:
                continue
            for i, e in enumerate((plan or {}).get("exports") or []):
                if isinstance(e, dict) and ".claude/skills/" in str(e.get("src", "")).replace("\\", "/"):
                    items.append(f"{rel} entry {i + 1}: exports a harness template directly ({e['src']}); copy it into "
                                 "brand/ or use a canvas entry, because harness templates change between releases")
    for line in items:
        print(f"- {line}")
    print(f"migrate: {len(items)} item(s) found; nothing was changed")
    return 0


def runs(a: argparse.Namespace) -> int:
    base = root_of(a) / dl.RUNS
    files = sorted(base.glob(f"{a.family or '*'}/*.json")) if base.is_dir() else []
    for f in files:
        m = load_json(f)
        print(f"{m['runId']}  {m['family']:<12} {m['status']:<16} {len(m['outputs'])} file(s)  {m['tool']}")
    if not files:
        print("no production runs recorded")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".", help="the project root (holds brand/)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--name", required=True)
    i.add_argument("--tokens", default="brand/tokens.json")
    sub.add_parser("validate")
    sub.add_parser("status")
    sub.add_parser("summary")
    ap_ = sub.add_parser("approve")
    ap_.add_argument("--gate", required=True, choices=["direction", "concept", "exception"])
    ap_.add_argument("--family", choices=dl.FAMILIES)
    ap_.add_argument("--concept")
    ap_.add_argument("--scope")
    ap_.add_argument("--by", required=True)
    ap_.add_argument("--evidence", required=True)
    ap_.add_argument("--recorded-by", default="main session")
    c = sub.add_parser("concept")
    csub = c.add_subparsers(dest="ccmd", required=True)
    cn = csub.add_parser("new")
    cn.add_argument("--family", required=True, choices=dl.FAMILIES)
    cn.add_argument("--id", required=True)
    cn.add_argument("--name", required=True)
    cn.add_argument("--run")
    cn.add_argument("--author", default="")
    cc = csub.add_parser("check")
    cc.add_argument("file")
    r = sub.add_parser("resolve")
    r.add_argument("family", choices=dl.FAMILIES)
    r.add_argument("--concept")
    s = sub.add_parser("signals")
    s.add_argument("file")
    cp = sub.add_parser("compare")
    cp.add_argument("a")
    cp.add_argument("b")
    rn = sub.add_parser("runs")
    rn.add_argument("--family", choices=dl.FAMILIES)
    sub.add_parser("migrate")
    for p_ in (i, ap_, r, s, cp, rn, cn, cc, *[sub.choices[n] for n in ("validate", "status", "summary", "migrate")]):
        p_.add_argument("--project", default=argparse.SUPPRESS, help="the project root (holds brand/)")
    a = ap.parse_args()
    handlers = {"init": init, "validate": validate, "status": status, "approve": approve, "summary": summary,
                "resolve": resolve, "signals": signals, "compare": compare, "runs": runs, "migrate": migrate}
    try:
        if a.cmd == "concept":
            return concept_new(a) if a.ccmd == "new" else concept_check(a)
        return handlers[a.cmd](a)
    except (UsageError, OperationalError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
