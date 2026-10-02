#!/usr/bin/env python3
"""Colour tools for the color-science skill: OKLCH ramps, WCAG contrast, pair checks, conversions.

  ramp      a tonal ramp at one hue: target OKLCH lightness per step (uniform between --light and
            --dark unless --lightness lists them), chroma tapered toward the ends (a stated
            heuristic) and reduced per step until it fits sRGB (CSS Color 4 gamut mapping).
            Prints each step with its WCAG contrast against white and black; --out merges the
            ramp into a DTCG token file without overwriting existing tokens (--replace names any
            you mean to change; the old file is kept as <name>.bak).
  contrast  one pair: full-precision ratio compared with the threshold, printed truncated.
  check     a pairs file against a token file, in the color-science report format.
  convert   one colour in sRGB hex, OKLab and OKLCH, with its gamut status.

Assumptions (stated in every report): sRGB (IEC 61966-2-1), D65, gamma-encoded values, WCAG 2.x
relative luminance with the 0.04045 threshold, alpha composited source-over in gamma space.

Usage:
  python palette.py ramp --name brand --seed "#2f7d6d" [--steps 50,100,200,300,400,500,600,700,800,900,950]
                    [--light 0.97 --dark 0.24 | --lightness 0.97,0.93,...] [--taper 0.5]
                    [--group color] [--out brand/tokens.json [--replace color.brand.500]]
  python palette.py contrast "#5b6470" "#ffffff" [--size 16 --weight 400 | --large | --non-text] [--tokens f]
  python palette.py check --tokens brand/tokens.json --pairs pairs.json
  python palette.py convert "oklch(0.62 0.14 160)"
pairs.json: [{"fg": "{color.ink}", "bg": "{color.canvas}", "kind": "text|large|non-text", "where": "body"}]
Exit codes: 0 done, 1 a pair fails, a merge conflicts or a token file is invalid, 2 bad arguments.
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
    from harnesslib import color as col
    from harnesslib import dtcg
    from harnesslib.fsutil import InputError, UsageError, load_json
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)

ASSUME = "Assumptions: sRGB IEC 61966-2-1, D65, gamma-encoded; WCAG 2.x luminance (0.04045); ratios truncated for display."
WHITE, BLACK = (1.0, 1.0, 1.0), (0.0, 0.0, 0.0)


def existing(path: str) -> Path:
    p = Path(path)
    if not p.is_file():
        raise UsageError(f"{path}: file not found")
    return p


def floats(text: str, what: str) -> list[float]:
    try:
        return [float(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise UsageError(f"{what}: expected comma-separated numbers") from None


def ramp(args: argparse.Namespace) -> int:
    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    if len(steps) < 2 or len(set(steps)) != len(steps):
        raise UsageError("--steps needs at least two unique names")
    if args.seed:
        L0, C0, H0 = col.oklab_to_oklch(col.srgb_to_oklab(col.parse(args.seed)[:3]))
        hue = args.hue if args.hue is not None else H0
        chroma = args.chroma if args.chroma is not None else C0
    else:
        if args.hue is None or args.chroma is None:
            raise UsageError("give --seed, or both --hue and --chroma")
        hue, chroma = args.hue, args.chroma
    if hue is None:
        hue, chroma = 0.0, 0.0  # an achromatic seed gives a neutral ramp
    if not 0 <= chroma <= 0.5:
        raise UsageError("--chroma must be 0..0.5")
    if args.lightness:
        lights = floats(args.lightness, "--lightness")
        if len(lights) != len(steps):
            raise UsageError(f"--lightness lists {len(lights)} values for {len(steps)} steps")
        spacing = "supplied"
    else:
        if not 0 < args.dark < args.light < 1:
            raise UsageError("need 0 < --dark < --light < 1")
        n = len(steps) - 1
        lights = [args.light + (args.dark - args.light) * i / n for i in range(len(steps))]
        spacing = f"uniform from {args.light} to {args.dark}"
    if not (all(a > b for a, b in zip(lights, lights[1:])) or all(a < b for a, b in zip(lights, lights[1:]))):
        raise UsageError("target lightness must be strictly monotonic across the steps")
    if not 0 <= args.taper <= 1:
        raise UsageError("--taper must be 0..1")

    group: dict = {}
    print(f"ramp {args.name}: hue {hue:.1f} deg, chroma {chroma:.3f}, lightness {spacing}, "
          f"taper {args.taper} (heuristic), gamut-mapped to sRGB")
    print(f"  {'step':<6} {'L':>5} {'C want':>7} {'C got':>6} {'hex':<8} {'vs white':>9} {'vs black':>9}")
    nearest = None
    for i, (name, L) in enumerate(zip(steps, lights)):
        t = i / (len(steps) - 1)
        want = chroma * (1 - args.taper * (2 * abs(t - 0.5)) ** 2)
        rgb = col.gamut_map_oklch((L, want, hue))
        got = col.oklab_to_oklch(col.srgb_to_oklab(rgb))
        cw, cb = col.contrast_ratio(rgb, WHITE), col.contrast_ratio(rgb, BLACK)
        print(f"  {name:<6} {L:5.3f} {want:7.3f} {got[1]:6.3f} {col.to_hex(rgb):<8} "
              f"{col.display_ratio(cw):>7}:1 {col.display_ratio(cb):>7}:1")
        group[name] = dtcg.color_token((*rgb, 1.0), oklch=(L, got[1], hue if got[1] > col.ACHROMATIC_C else None),
                                       description=f"OKLCH target L {L:.3f}, C {want:.3f}, h {hue:.1f}; mapped to sRGB")
        if args.seed:
            d = col.delta_e_ok(col.srgb_to_oklab(rgb), col.srgb_to_oklab(col.parse(args.seed)[:3]))
            if nearest is None or d < nearest[1]:
                nearest = (name, d)
    if nearest:
        print(f"  seed {args.seed} is nearest step {nearest[0]} (deltaE-OK {nearest[1]:.3f}); "
              "equal OKLCH lightness does not mean equal WCAG contrast, so check each pair you use")
    print(ASSUME)
    if not args.out:
        return 0
    doc: dict = {}
    node = doc
    for part in args.group.split("."):
        node = node.setdefault(part, {})
    node[args.name] = group
    return merge_into(Path(args.out), doc, args.replace)


def merge_into(path: Path, additions: dict, replace: str) -> int:
    names = {r.strip() for r in replace.split(",") if r.strip()}
    return 0 if dtcg.merge_file(path, additions, names) else 1


def color_arg(value: str, tokens: dtcg.Tokens | None) -> tuple[float, float, float, float]:
    if dtcg.is_alias(value):
        if tokens is None:
            raise UsageError(f"{value}: pass --tokens to resolve token references")
        return tokens.resolve(value, "color").value["srgb"]
    try:
        return col.parse(value)
    except col.ColorError as e:
        raise UsageError(str(e)) from None


def need_of(kind: str, size: float | None, weight: float) -> float:
    if kind in ("large", "non-text"):
        return col.TEXT_LARGE if kind == "large" else col.NON_TEXT
    if size is not None:
        return col.text_threshold(size, weight)
    return col.TEXT_NORMAL


def contrast(args: argparse.Namespace) -> int:
    tokens = dtcg.Tokens.load(existing(args.tokens)) if args.tokens else None
    fg, bg = color_arg(args.fg, tokens), color_arg(args.bg, tokens)
    if bg[3] < 1:
        raise InputError("the backdrop must be opaque; composite it onto its own backdrop first")
    shown_fg = col.composite(fg, bg[:3])
    ratio = col.contrast_ratio(shown_fg, bg[:3])
    kind = "non-text" if args.non_text else "large" if args.large else "text"
    need = need_of(kind, args.size, args.weight)
    ok = ratio >= need
    print(f"{'PASS' if ok else 'FAIL'}  {args.fg} on {args.bg}: {col.display_ratio(ratio, need)}:1 "
          f"(needs {need:g}:1 for {kind}{f' at {args.size:g}px/{args.weight:g}' if args.size else ''})")
    if fg[3] < 1:
        print(f"  composited text colour {col.to_hex(shown_fg)} (alpha {fg[3]:g})")
    print(ASSUME)
    return 0 if ok else 1


def check(args: argparse.Namespace) -> int:
    tokens = dtcg.Tokens.load(existing(args.tokens))
    pairs = load_json(existing(args.pairs))
    if not isinstance(pairs, list) or not pairs:
        raise UsageError("--pairs must be a non-empty JSON list")
    fails = 0
    print("Section 1, WCAG 2.2 conformance")
    for i, pr in enumerate(pairs):
        if not isinstance(pr, dict) or "fg" not in pr or "bg" not in pr:
            raise InputError(f"pair {i + 1}: needs fg and bg")
        kind = pr.get("kind", "text")
        if kind not in ("text", "large", "non-text"):
            raise InputError(f"pair {i + 1}: kind must be text, large or non-text")
        fg, bg = color_arg(pr["fg"], tokens), color_arg(pr["bg"], tokens)
        if bg[3] < 1:
            raise InputError(f"pair {i + 1}: the backdrop must be opaque")
        ratio = col.contrast_ratio(col.composite(fg, bg[:3]), bg[:3])
        need = need_of(kind, None, 400)
        ok = ratio >= need
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {pr.get('where', f'pair {i + 1}')}: {pr['fg']} on {pr['bg']} "
              f"{col.display_ratio(ratio, need)}:1 (needs {need:g}:1, {kind})")
    print("Section 3, Assumptions\n  " + ASSUME)
    print("Section 4, Not verified\n  every theme and state not listed above; CVD simulation (not part of this tool)")
    return 1 if fails else 0


def convert(args: argparse.Namespace) -> int:
    rgba = color_arg(args.color, None)
    lab = col.srgb_to_oklab(rgba[:3])
    L, C, H = col.oklab_to_oklch(lab)
    inside = col.in_gamut(rgba)
    print(f"input   {args.color}")
    print(f"oklab   {lab[0]:.4f} {lab[1]:.4f} {lab[2]:.4f}")
    print(f"oklch   {L:.4f} {C:.4f} {'none' if H is None else f'{H:.2f}'}")
    if inside:
        print(f"srgb    {col.to_hex(rgba)} (in gamut)")
    else:
        mapped = col.gamut_map_oklch((L, C, H))
        print(f"srgb    outside sRGB; gamut-mapped (CSS Color 4) to {col.to_hex(mapped)}")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("ramp")
    r.add_argument("--name", required=True)
    r.add_argument("--seed")
    r.add_argument("--hue", type=float)
    r.add_argument("--chroma", type=float)
    r.add_argument("--steps", default="50,100,200,300,400,500,600,700,800,900,950")
    r.add_argument("--light", type=float, default=0.97)
    r.add_argument("--dark", type=float, default=0.24)
    r.add_argument("--lightness")
    r.add_argument("--taper", type=float, default=0.5)
    r.add_argument("--group", default="color")
    r.add_argument("--out")
    r.add_argument("--replace", default="")
    c = sub.add_parser("contrast")
    c.add_argument("fg")
    c.add_argument("bg")
    c.add_argument("--tokens")
    c.add_argument("--size", type=float)
    c.add_argument("--weight", type=float, default=400)
    c.add_argument("--large", action="store_true")
    c.add_argument("--non-text", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("--tokens", required=True)
    k.add_argument("--pairs", required=True)
    v = sub.add_parser("convert")
    v.add_argument("color")
    args = ap.parse_args()
    try:
        return {"ramp": ramp, "contrast": contrast, "check": check, "convert": convert}[args.cmd](args)
    except UsageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except InputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
