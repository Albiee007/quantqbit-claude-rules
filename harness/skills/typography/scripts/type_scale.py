#!/usr/bin/env python3
"""Type tools for the typography skill: scales, media caption sizes, font records, token checks.

DTCG is the interchange: sizes are written as dimension tokens in px, and each platform's own form
(web rem or clamp() with a rem term, Android sp, Apple pt, React Native numbers) goes under
$extensions["org.quantqbit.platform"]. Ratios and line heights are heuristics; the token
$description says so.

  scale  a modular scale: --base for the body step, --ratio between steps
         [--fluid 360:1440 --max-ratio R] also writes a web clamp() from the --ratio scale at the
         narrow viewport to the --max-ratio scale at the wide one
  media  caption sizes for raster media (store frames, social images): the canvas px each text
         role needs to stay at least its minimum CSS px when the image is shown --display-width
         wide (its smallest intended display)
  font   record a font family token with its source, files (sha256), weights, scripts and licence
         evidence; the media renderers read it. --source local (files in the project; production
         renders use them) or system (no files; --availability says where it exists)
  check  every font token's record: files exist, hashes match, licence evidence present

Usage:
  python type_scale.py scale --base 16 --ratio 1.2 --steps caption,body,h3,h2,h1 --body body
                       [--platform web,android,ios,rn] [--fluid 360:1440 --max-ratio 1.25]
                       [--group typography.scale] [--out brand/tokens.json [--replace ...]]
  python type_scale.py media --canvas-width 1080 --display-width 320 --min headline=24,sub=15 [--out ...]
  python type_scale.py font --name display --family "Fraunces" --fallback "Georgia,serif" --source local
                       --file brand/fonts/Fraunces-Bold.woff2:700 [--file path:400:italic | path:100-900]
                       --license OFL-1.1 --license-evidence brand/fonts/OFL.txt [--scripts latin,latin-ext]
                       --out brand/tokens.json [--group font] [--project .]
  python type_scale.py font --name text --family "Segoe UI" --fallback "system-ui,sans-serif" --source system
                       --availability "Windows 10+ only; other systems fall back" --out brand/tokens.json
  python type_scale.py check --tokens brand/tokens.json [--project .]
Exit codes: 0 done, 1 invalid tokens or a merge conflict, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
try:
    from harnesslib import dtcg, typescale
    from harnesslib.fsutil import InputError, UsageError, resolve_inside, safe_rel, sha256_file
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)


def nest(group: str, name: str, value: dict) -> dict:
    doc: dict = {}
    node = doc
    for part in group.split("."):
        node = node.setdefault(part, {})
    node[name] = value
    return doc


def merge_into(path: Path, additions: dict, replace: str) -> int:
    names = {r.strip() for r in replace.split(",") if r.strip()}
    return 0 if dtcg.merge_file(path, additions, names) else 1


def scale(a: argparse.Namespace) -> int:
    names = [s.strip() for s in a.steps.split(",") if s.strip()]
    try:
        sizes = typescale.modular(a.base, a.ratio, names, a.body)
        wide = typescale.modular(a.base, a.max_ratio, names, a.body) if a.max_ratio else None
    except typescale.ScaleError as e:
        raise UsageError(str(e)) from None
    platforms = [p.strip() for p in a.platform.split(",") if p.strip()]
    for p in platforms:
        if p not in typescale.PLATFORMS:
            raise UsageError(f"--platform {p!r}: choose from {', '.join(typescale.PLATFORMS)}")
    fluid = None
    if a.fluid:
        try:
            lo, hi = (float(x) for x in a.fluid.split(":"))
        except ValueError:
            raise UsageError("--fluid must be MIN:MAX viewport widths in px") from None
        if wide is None:
            raise UsageError("--fluid needs --max-ratio (the scale at the wide viewport)")
        fluid = (lo, hi)
    group: dict = {}
    print(f"scale: body {a.body} = {a.base:g}, ratio {a.ratio:g}"
          + (f" -> {a.max_ratio:g} from {fluid[0]:g} to {fluid[1]:g} px viewports" if fluid else "") + " (heuristic)")
    for n in names:
        px = sizes[n]
        plat = {p: typescale.platform_value(px, p) for p in platforms}
        if fluid and "web" in plat:
            plat["web"] = typescale.fluid_clamp(px, wide[n], fluid[0], fluid[1])  # type: ignore[index]
        print(f"  {n:<10} {px:7.2f}  " + "  ".join(f"{k}={v}" for k, v in plat.items()))
        group[n] = {"$type": "dimension", "$value": {"value": round(px, 2), "unit": "px"},
                    "$description": f"modular scale, ratio {a.ratio:g} (heuristic)",
                    "$extensions": {dtcg.PLATFORM_EXT: plat}}
    if not a.out:
        return 0
    group_path, _, leaf = a.group.rpartition(".")
    doc = nest(group_path, leaf, group) if group_path else {leaf: group}
    return merge_into(Path(a.out), doc, a.replace)


def media(a: argparse.Namespace) -> int:
    pairs = {}
    for item in a.min.split(","):
        name, _, v = item.partition("=")
        try:
            pairs[name.strip()] = float(v)
        except ValueError:
            raise UsageError("--min takes name=px pairs, e.g. headline=24,sub=15") from None
    group = {}
    print(f"media: canvas {a.canvas_width:g} px wide, smallest display {a.display_width:g} CSS px")
    for name, min_px in pairs.items():
        try:
            px = typescale.media_px(min_px, a.canvas_width, a.display_width)
        except typescale.ScaleError as e:
            raise UsageError(str(e)) from None
        print(f"  {name:<10} >= {min_px:g} CSS px at display -> {px:.1f} canvas px ({px / a.canvas_width:.4f} of the width)")
        group[name] = {"$type": "dimension", "$value": {"value": round(px, 1), "unit": "px"},
                       "$description": f"raster media: >= {min_px:g} CSS px when shown {a.display_width:g} px wide",
                       "$extensions": {dtcg.PLATFORM_EXT: {"media": {"canvasWidth": a.canvas_width,
                                                                     "displayWidth": a.display_width,
                                                                     "minDisplayPx": min_px}}}}
    if not a.out:
        return 0
    return merge_into(Path(a.out), nest("typography", "media", group), a.replace)


def parse_file(spec: str, root: Path) -> dict:
    parts = spec.split(":")
    if len(parts) < 2:
        raise UsageError(f"--file {spec!r}: use path:weight[:italic] or path:min-max")
    path, weight = parts[0], parts[1]
    style = parts[2] if len(parts) > 2 else "normal"
    if style not in ("normal", "italic"):
        raise UsageError(f"--file {spec!r}: style must be normal or italic")
    try:
        w: object = [int(x) for x in weight.split("-")] if "-" in weight else int(weight)
    except ValueError:
        raise UsageError(f"--file {spec!r}: weight must be a number or a min-max range") from None
    try:
        rel = safe_rel(path, "--file")
        abs_path = resolve_inside(root, rel, "--file", must_exist=True)
    except InputError as e:
        raise UsageError(str(e)) from None
    return {"path": rel, "sha256": sha256_file(abs_path), "weight": w, "style": style}


def font(a: argparse.Namespace) -> int:
    root = Path(a.project).resolve()
    fams = [a.family] + [f.strip() for f in a.fallback.split(",") if f.strip()]
    meta: dict = {"source": a.source}
    if a.source == "local":
        if not a.file or not a.license or not a.license_evidence:
            raise UsageError("--source local needs --file (one or more), --license and --license-evidence")
        meta["files"] = [parse_file(f, root) for f in a.file]
        meta["license"] = a.license
        meta["licenseEvidence"] = a.license_evidence
    else:
        if not a.availability:
            raise UsageError("--source system needs --availability (which systems have the font)")
        meta["availability"] = a.availability
        if a.license:
            meta["license"] = a.license
        if a.provenance:
            meta["provenance"] = a.provenance
    if a.scripts:
        meta["scripts"] = [s.strip() for s in a.scripts.split(",") if s.strip()]
    tok = {"$type": "fontFamily", "$value": fams, "$extensions": {dtcg.FONT_EXT: meta}}
    print(f"font {a.group}.{a.name}: {', '.join(fams)} ({a.source}" +
          (f", {len(meta.get('files', []))} file(s), licence {a.license}" if a.source == "local" else "") + ")")
    return merge_into(Path(a.out), nest(a.group, a.name, tok), a.replace)


def check(a: argparse.Namespace) -> int:
    root = Path(a.project).resolve()
    if not Path(a.tokens).is_file():
        raise UsageError(f"{a.tokens}: file not found")
    toks = dtcg.Tokens.load(Path(a.tokens))
    errors = toks.check_all()
    fonts = 0
    for path in toks.paths():
        tok, ttype = toks.index[path]
        if ttype != "fontFamily" or dtcg.is_alias(tok["$value"]):
            continue
        fonts += 1
        meta = (tok.get("$extensions") or {}).get(dtcg.FONT_EXT)
        if not isinstance(meta, dict):
            errors.append(f"{path}: no {dtcg.FONT_EXT} record (source, files, licence); add one with 'font'")
            continue
        if meta.get("source") == "local":
            if not meta.get("license") or not meta.get("licenseEvidence"):
                errors.append(f"{path}: local font without license/licenseEvidence")
            for f in meta.get("files") or []:
                try:
                    p = resolve_inside(root, f.get("path", ""), path, must_exist=True)
                except InputError as e:
                    errors.append(str(e))
                    continue
                if f.get("sha256") and sha256_file(p) != f["sha256"]:
                    errors.append(f"{path}: {f['path']} changed since it was recorded")
            if not meta.get("files"):
                errors.append(f"{path}: local font with no files")
        elif meta.get("source") == "system":
            if not meta.get("availability"):
                errors.append(f"{path}: system font without an availability note")
        else:
            errors.append(f"{path}: source must be local or system")
    for e in errors:
        print(f"  FAIL  {e}")
    print(f"check: {len(toks.paths())} tokens, {fonts} font families, {len(errors)} problem(s)")
    return 1 if errors else 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scale")
    s.add_argument("--base", type=float, required=True)
    s.add_argument("--ratio", type=float, required=True)
    s.add_argument("--steps", required=True)
    s.add_argument("--body", required=True)
    s.add_argument("--platform", default="web")
    s.add_argument("--fluid")
    s.add_argument("--max-ratio", type=float)
    s.add_argument("--group", default="typography.scale")
    s.add_argument("--out")
    s.add_argument("--replace", default="")
    m = sub.add_parser("media")
    m.add_argument("--canvas-width", type=float, required=True)
    m.add_argument("--display-width", type=float, required=True)
    m.add_argument("--min", required=True)
    m.add_argument("--out")
    m.add_argument("--replace", default="")
    f = sub.add_parser("font")
    f.add_argument("--name", required=True)
    f.add_argument("--family", required=True)
    f.add_argument("--fallback", default="sans-serif")
    f.add_argument("--source", choices=["local", "system"], required=True)
    f.add_argument("--file", action="append", default=[])
    f.add_argument("--license")
    f.add_argument("--license-evidence")
    f.add_argument("--availability")
    f.add_argument("--provenance")
    f.add_argument("--scripts")
    f.add_argument("--group", default="font")
    f.add_argument("--out", required=True)
    f.add_argument("--replace", default="")
    f.add_argument("--project", default=".")
    c = sub.add_parser("check")
    c.add_argument("--tokens", required=True)
    c.add_argument("--project", default=".")
    a = ap.parse_args()
    try:
        return {"scale": scale, "media": media, "font": font, "check": check}[a.cmd](a)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
