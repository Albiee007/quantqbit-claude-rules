#!/usr/bin/env python3
"""Export brand masters and marketing canvases to PNG at exact sizes with headless Chrome/Edge.

Sources:
  SVG      centred on a transparent canvas with optional padding (logos, marks, lockups)
  HTML     a page of your own, screenshotted at the window size
  canvas   a social / Open Graph / email-header / banner image from brand/canvas.json, drawn in the
           approved marketing concept's look (layouts, backgrounds and type from the direction).
           Production exports need the owner-approved direction and marketing concept; --preview
           renders drafts with any concept into a folder of its own instead.
--flatten fills transparency with a colour and saves RGB (stores reject alpha in screenshots,
feature graphics and the App Store icon). For canvases, "flatten": true uses the background.

Every file is rendered to a temporary folder, re-opened and checked (exact size, RGB when
flattened, not blank), then moved into place; a failed export leaves existing files untouched.
A source still holding a template placeholder ({{...}}) is refused.
Text contrast: canvases are checked like store frames (computed where the backdrop colour is known,
sampled estimates otherwise, at the concept's smallest display width); HTML pages of your own are
sampled at their own size, so a passing result there is REVIEW REQUIRED. --no-contrast skips both.

One-off exports:
  python export_svg.py brand/mark.svg --size 2048x2048 --out brand/png
  python export_svg.py brand/mark.svg brand/mark-mono.svg --size 1024x1024 --size 512x512 --pad 0.1 --out brand/png
The whole brand set from one plan file (paths relative to the plan's folder, except canvas ids):
  python export_svg.py --plan brand/exports.json [--only og-image]
  {"exports": [{"src": "mark.svg", "sizes": ["2048x2048", "1024x1024"], "out": "png"},
               {"canvas": "og", "out": "../web/public", "name": "og-image", "flatten": true}]}
  optional per entry: "name" (output base name), "pad", "flatten", "contrast": false;
  canvas entries may set "sizes" (default: the canvas's own size)
Drafts of every canvas entry, without approval, into one folder:
  python export_svg.py --plan brand/exports.json --preview out/creative/marketing-draft [--concept <file>]
Needs Pillow and Chrome, Chromium or Edge (or --chrome PATH).
Exit codes: 0 done, 1 a check or gate failed, 2 bad arguments, a missing dependency or a browser failure.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
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
    from harnesslib import browser, pagecheck, schema
    from harnesslib import color as col
    from harnesslib import contrast as con
    from harnesslib import direction as dl
    from harnesslib.dtcg import TokenError
    from harnesslib.fsutil import (DirLock, InputError, OperationalError, UsageError, canonical, load_json, resolve_inside,
                                   run_id, script_json, self_ignoring_dir, sha256_file, sha256_text)
except ImportError:
    print("the harness media library is missing (.claude/harness/lib); re-run harness sync", file=sys.stderr)
    raise SystemExit(2)
try:
    from PIL import Image
    from harnesslib import imaging
except ImportError:  # pragma: no cover
    print("Pillow is required: pip install pillow", file=sys.stderr)
    raise SystemExit(2)

MEDIA = Path(harnesslib.__file__).resolve().parent.parent / "media"
CANVAS_SIZES = {"og": (1200, 630), "square": (1080, 1080), "story": (1080, 1920), "email-header": (1200, 300)}
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")

# Lists every visible text run with its colour, size, weight and boxes (appended to a copy of the page).
PROBE_JS = """<script>addEventListener('load', () => setTimeout(() => {
  const runs = [], W = innerWidth, H = innerHeight;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const text = n.textContent.trim(), el = n.parentElement;
    if (!text || !el || el.closest('script,style,noscript')) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    const rects = [...range.getClientRects()]
      .map((r) => [Math.max(0, r.left), Math.max(0, r.top), Math.min(W, r.right), Math.min(H, r.bottom)])
      .filter(([l, t, r, b]) => r - l >= 2 && b - t >= 2);
    if (rects.length) runs.push({ text: text.slice(0, 40), color: cs.color, size: parseFloat(cs.fontSize),
      weight: Number(cs.fontWeight) || 400, rects });
  }
  const pre = document.createElement('pre'); pre.id = 'probe'; pre.style.display = 'none';
  pre.textContent = JSON.stringify({ runs }); document.body.appendChild(pre);
}, 300));</script>"""
HIDE_TEXT = ("<style>body * { color: transparent !important; -webkit-text-fill-color: transparent !important; "
             "text-shadow: none !important; }</style>")


def parse_size(value: str) -> tuple[int, int]:
    try:
        w, h = (int(v) for v in value.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError(f"size must be WxH, got {value}") from None
    if not (1 <= w <= 8192 and 1 <= h <= 8192):
        raise argparse.ArgumentTypeError(f"size {value} is outside 1..8192")
    return w, h


def page_copy(src: Path, tmp: Path, extra: str, tag: str) -> str:
    """A copy of an HTML page with `extra` appended; <base> keeps its relative URLs pointing at src's folder."""
    text = src.read_text(encoding="utf-8")
    base = f'<base href="{src.resolve().parent.as_uri()}/">'
    text = re.sub(r"(<head[^>]*>)", lambda m: m.group(1) + base, text, count=1, flags=re.I) if re.search(r"<head", text, re.I) else base + text
    text = re.sub(r"(</body>)", lambda m: extra + m.group(1), text, count=1, flags=re.I) if re.search(r"</body>", text, re.I) else text + extra
    page = tmp / f"{tag}-{src.stem}.html"
    page.write_text(text, encoding="utf-8")
    return page.as_uri()


def hex_rgba(value: str) -> tuple[int, int, int, int]:
    v = value.lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", v):
        raise UsageError(f"flatten must be #RRGGBB, got {value}")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) + (255,)  # type: ignore[return-value]


def html_contrast(chrome: str, src: Path, size: tuple[int, int], flatten: str | None, tmp: Path) -> list[con.Finding]:
    """A page of your own: every text run against the pixels behind it (sampled estimates)."""
    dom = browser.dump_dom(chrome, page_copy(src, tmp, PROBE_JS, "probe"), size, 5000)
    m = re.search(r'<pre id="probe"[^>]*>(.*?)</pre>', dom, re.S)
    where = f"{src.name} @ {size[0]}x{size[1]}"
    if not m:
        return [con.Finding(where, "(page)", "text", None, 4.5, con.REVIEW, "sampled", "the probe returned nothing")]
    runs = json.loads(html.unescape(m.group(1)))["runs"]
    shot = tmp / f"bg-{src.stem}.png"
    browser.screenshot(chrome, page_copy(src, tmp, HIDE_TEXT, "bg"), size, shot, 5000, transparent=True)
    bg = Image.open(shot).convert("RGBA")
    backdrop = Image.new("RGBA", bg.size, hex_rgba(flatten) if flatten else (255, 255, 255, 255))
    backdrop.alpha_composite(bg)
    rgb = backdrop.convert("RGB")
    return [con.judge_sampled(where, r["text"], "text", imaging.percentile5(imaging.sample_ratios(rgb, r["rects"], r["color"])),
                              col.text_threshold(r["size"], r["weight"])) for r in runs]


def verify(dest: Path, size: tuple[int, int], flatten: bool) -> str | None:
    with Image.open(dest) as im:
        if im.size != size:
            return f"{im.size[0]}x{im.size[1]}, want {size[0]}x{size[1]}"
        if flatten and im.mode != "RGB":
            return f"mode {im.mode}, want RGB (flattened)"
        rgba = im.convert("RGBA")
        if rgba.getchannel("A").getextrema()[1] == 0:
            return "fully transparent"
        if all(lo == hi for lo, hi in rgba.convert("RGB").getextrema()) and not flatten and rgba.getchannel("A").getextrema()[0] == 255:
            return "a single flat colour (did the source load?)"
    return None


# ------------------------------------------------------------------ canvases

def canvas_size(asset: dict) -> tuple[int, int]:
    s = asset["size"]
    return CANVAS_SIZES[s] if s in CANVAS_SIZES else parse_size(s)


def load_canvas(p: dl.Project, cid: str) -> dict:
    f = p.root / "brand" / "canvas.json"
    if not f.is_file():
        raise InputError("canvas entries need brand/canvas.json (see brand-assets references/asset-matrix.md)")
    data = load_json(f)
    schema.check(data, "canvas", "brand/canvas.json")
    for a in data["assets"]:
        if a["id"] == cid:
            if a.get("slots", {}).get("image") and not a.get("imageLicense"):
                raise InputError(f"canvas {cid}: an image slot needs 'imageLicense' (who owns it, model release)")
            return a
    raise InputError(f"brand/canvas.json has no asset {cid!r}")


def build_canvas(p: dl.Project, asset: dict, ad: dict, size: tuple[int, int], dest: Path) -> Path:
    """The canvas page for one asset in dest (fonts, artdir runtime, assets, generated data)."""
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "fonts").mkdir(parents=True)
    (dest / "assets").mkdir()
    shutil.copyfile(MEDIA / "canvas.html", dest / "canvas.html")
    shutil.copyfile(MEDIA / "artdir.js", dest / "artdir.js")
    css = ["/* generated by export_svg.py from the approved marketing concept */"]
    for face in ad["faces"]:
        if face.get("source") == "system":
            continue
        name = f"{face['sha256'][:12]}{Path(face['path']).suffix}"
        shutil.copyfile(face["abs"], dest / "fonts" / name)
        css.append(f"@font-face {{ font-family: {json.dumps(face['family'])}; src: url(fonts/{name}); "
                   f"font-weight: {face['weight']}; font-style: {face['style']}; }}")
    (dest / "fonts.generated.css").write_text("\n".join(css) + "\n", encoding="utf-8")
    slots = {}
    for slot, rel in (asset.get("slots") or {}).items():
        src = resolve_inside(p.root, rel, f"canvas {asset['id']} slot {slot}", must_exist=True)
        shutil.copyfile(src, dest / "assets" / f"{slot}{src.suffix}")
        slots[slot] = f"assets/{slot}{src.suffix}"
    if "logo" not in slots and ad.get("logo"):
        src = resolve_inside(p.root, ad["logo"], "concept logo", must_exist=True)
        shutil.copyfile(src, dest / "assets" / f"logo{src.suffix}")
        slots["logo"] = f"assets/logo{src.suffix}"
    page_ad = {k: v for k, v in ad.items() if k != "faces" and not k.startswith("_")}
    page_ad["faces"] = [{k: v for k, v in f.items() if k in ("family", "weight", "style")} for f in ad["faces"]]
    if ad.get("motif"):
        src = resolve_inside(p.root, ad["motif"]["asset"], "motif.asset", must_exist=True)
        shutil.copyfile(src, dest / "assets" / "motif.svg")
        page_ad["motif"] = dict(ad["motif"], src="assets/motif.svg")
    if asset.get("layout") and asset["layout"] not in ad["layouts"]:
        scope = f"marketing:canvas:{asset['id']}:layout={asset['layout']}"
        if not dl.exception_approved(p, scope):
            raise InputError(f"canvas {asset['id']}: layout {asset['layout']!r} is outside the approved concept "
                             f"({', '.join(ad['layouts'])}); the owner can allow it: direction.py approve --gate exception "
                             f"--scope \"{scope}\"")
    if asset.get("background") and asset["background"] not in ad["backgrounds"]:
        raise InputError(f"canvas {asset['id']}: background {asset['background']!r} is not in the concept")
    (dest / "direction.generated.js").write_text("window.AD = " + script_json(page_ad) + ";\n", encoding="utf-8")
    data = {"width": size[0], "height": size[1], "asset": asset, "slots": slots}
    (dest / "canvas.generated.js").write_text("window.CANVAS = " + script_json(data) + ";\n", encoding="utf-8")
    return dest / "canvas.html"


def canvas_checks(chrome: str, page: Path, size: tuple[int, int], ad: dict, cid: str) -> tuple[list[con.Finding], list[str]]:
    base = page.resolve().as_uri()
    dom = browser.dump_dom(chrome, f"{base}?probe=1", size)
    m = re.search(r'<pre id="probe"[^>]*>(.*?)</pre>', dom, re.S)
    if not m:
        raise InputError(f"canvas {cid}: the caption probe returned nothing (a script error in the copy or slots?)")
    pr = json.loads(html.unescape(m.group(1)))

    def backdrop():
        with tempfile.TemporaryDirectory() as tmp:
            shot = Path(tmp) / "bg.png"
            browser.screenshot(chrome, f"{base}?nocap=1", size, shot)
            with Image.open(shot) as im:
                return im.convert("RGB")

    return pagecheck.evaluate(pr, ad, f"canvas {cid} @ {size[0]}x{size[1]}", backdrop)


# ------------------------------------------------------------------ export

def render_one(chrome: str, job: dict, url: str, size: tuple[int, int], tmp: Path, transparent: bool) -> Image.Image:
    raw = tmp / f"raw-{run_id()}.png"
    browser.screenshot(chrome, url, size, raw, 5000, transparent=transparent)
    img = Image.open(raw).convert("RGBA")
    if img.size != size:
        raise InputError(f"{job['label']}: got {img.size}, want {size}")
    return img


def export(chrome: str, job: dict, tmp: Path, check_contrast: bool, publish: list) -> tuple[int, list[con.Finding], list[str]]:
    """Render one source at each size into tmp; queue (staged, final) pairs on publish.
    Returns (problems, contrast findings, font problems)."""
    out: Path = job["out"]
    problems = 0
    findings: list[con.Finding] = []
    fonts: list[str] = []
    for w, h in job["sizes"]:
        flatten = job.get("flatten")
        if job["kind"] == "canvas":
            page = build_canvas(job["project"], job["asset"], job["ad"], (w, h), job["build"] / f"{job['asset']['id']}-{w}x{h}")
            url = page.resolve().as_uri()
            if flatten is True:
                flatten = job["flatten_color"]
        elif job["kind"] == "svg":
            pad_x, pad_y = round(w * job.get("pad", 0.0)), round(h * job.get("pad", 0.0))
            wrapper = tmp / f"wrap-{job['src'].stem}-{w}x{h}.html"
            wrapper.write_text(
                "<!doctype html><html><body style=\"margin:0;background:transparent\">"
                f"<img src=\"{job['src'].resolve().as_uri()}\" style=\"position:absolute;left:{pad_x}px;top:{pad_y}px;"
                f"width:{w - 2 * pad_x}px;height:{h - 2 * pad_y}px;object-fit:contain\"></body></html>",
                encoding="utf-8")
            url = wrapper.as_uri()
        else:
            url = job["src"].resolve().as_uri()
        img = render_one(chrome, job, url, (w, h), tmp, transparent=True)
        if flatten:
            bg = Image.new("RGBA", img.size, hex_rgba(flatten))
            bg.alpha_composite(img)
            img = bg.convert("RGB")
        staged = tmp / f"out-{run_id()}.png"
        img.save(staged, optimize=True)
        dest = out / f"{job['base']}-{w}x{h}.png"
        problem = verify(staged, (w, h), bool(flatten))
        if problem:
            problems += 1
            print(f"FAIL  {dest}: {problem}")
        else:
            print(f"ok    {dest.name}  {w}x{h}{'  (flattened)' if flatten else ''}")
            publish.append((staged, dest))
        if check_contrast and job.get("contrast", True):
            if job["kind"] == "canvas":
                f, fp = canvas_checks(chrome, page, (w, h), job["ad"], job["asset"]["id"])
                findings += f
                fonts += fp
            elif job["kind"] == "html":
                findings += html_contrast(chrome, job["src"], (w, h), flatten if isinstance(flatten, str) else None, tmp)
    return problems, findings, fonts


def check_placeholders(job: dict) -> str | None:
    if job["kind"] == "canvas":
        return None
    hits = sorted(set(PLACEHOLDER.findall(job["src"].read_text(encoding="utf-8", errors="replace"))))
    return f"{job['src'].name} still holds template placeholders {', '.join(hits)}" if hits else None


def load_plan(plan: Path, only: list[str]) -> list[dict]:
    if not plan.is_file():
        raise UsageError(f"plan {plan} not found")
    data = load_json(plan)
    root = plan.resolve().parent
    jobs = []
    for i, e in enumerate(data.get("exports") or []):
        if "canvas" in e:
            unknown = set(e) - {"canvas", "sizes", "out", "name", "flatten", "contrast"}
            if unknown or not e.get("out"):
                raise InputError(f"plan entry {i + 1}: a canvas entry needs canvas and out" +
                                 (f"; unknown keys {sorted(unknown)}" if unknown else ""))
            job = {"kind": "canvas", "canvas": e["canvas"], "out": root / e["out"], "name": e.get("name") or e["canvas"],
                   "sizes": [parse_size(s) for s in e.get("sizes") or []], "flatten": e.get("flatten"),
                   "contrast": e.get("contrast", True), "label": f"canvas {e['canvas']}"}
            if not only or job["name"] in only or e["canvas"] in only:
                jobs.append(job)
            continue
        unknown = set(e) - {"src", "sizes", "out", "name", "pad", "flatten", "contrast"}
        if unknown or not e.get("src") or not e.get("sizes") or not e.get("out"):
            raise InputError(f"plan entry {i + 1}: needs src, sizes and out" + (f"; unknown keys {sorted(unknown)}" if unknown else ""))
        src = root / e["src"]
        job = dict(e, src=src, out=root / e["out"], sizes=[parse_size(s) for s in e["sizes"]], label=src.name,
                   kind="svg" if src.suffix.lower() == ".svg" else "html")
        if not only or job.get("name", src.stem) in only or src.stem in only:
            jobs.append(job)
    if not jobs:
        raise InputError(f"plan {plan}: no exports" + (f" match --only {only}" if only else ""))
    return jobs


def prepare_canvas_jobs(jobs: list[dict], plan: Path | None, preview: Path | None, concept: str | None) -> tuple[dl.Project | None, dict]:
    canvas_jobs = [j for j in jobs if j["kind"] == "canvas"]
    if not canvas_jobs:
        return None, {}
    root = dl.find_project(plan.resolve().parent if plan else Path.cwd())
    if root is None:
        raise dl.GateError("canvas entries need brand/direction.json at or above the plan (run the creative-director first)")
    p = dl.load_project(root)
    info: dict = {}
    if preview is None:
        prod = dl.production(p, "marketing")
        ad = prod.resolved
        info = {"direction": prod.gate.direction[0] if prod.gate.direction else None,
                "concept": prod.gate.concept[0] if prod.gate.concept else None, "approvals": prod.gate.records}
        build = self_ignoring_dir(root / "brand" / ".build", "export_svg.py canvas builds") / "canvas"
    else:
        rel, _, ad = dl.preview(p, "marketing", concept)
        g = dl.gate(p, "marketing")
        print(f"concept: {rel} ({'approved' if g.ok and g.concept_rel == rel else 'DRAFT, not approved for production'})")
        build = Path(tempfile.mkdtemp(prefix="canvas-preview-"))
    for j in canvas_jobs:
        j.update(project=p, ad=ad, build=build, asset=load_canvas(p, j["canvas"]))
        if not j["sizes"]:
            j["sizes"] = [canvas_size(j["asset"])]
        bgname = j["asset"].get("background") or ad["defaultBackground"]
        b = ad["backgrounds"][bgname]
        j["flatten_color"] = col.to_hex(col.parse(b["color"] if b["recipe"] == "solid" else b["stops"][0]))
        if preview is not None:
            j["out"] = preview
    return p, info


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src", type=Path, nargs="*", help=".svg or .html masters")
    parser.add_argument("--plan", type=Path, help="JSON plan listing every export (see above)")
    parser.add_argument("--only", action="append", default=[], help="with --plan: export only this source stem or name; repeatable")
    parser.add_argument("--size", type=parse_size, action="append", help="WxH; repeatable")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--name", help="output base name (default: source stem; one source only)")
    parser.add_argument("--pad", type=float, default=0.0, help="SVG padding as a share of each side (0-0.4)")
    parser.add_argument("--flatten", help="fill transparency with #RRGGBB and save RGB")
    parser.add_argument("--no-contrast", action="store_true", help="skip the text contrast check")
    parser.add_argument("--preview", type=Path, help="with --plan: render only the canvas entries, as drafts, into this folder")
    parser.add_argument("--concept", help="with --preview: a marketing concept file (default: the selected one)")
    parser.add_argument("--chrome")
    args = parser.parse_args()
    try:
        if args.plan:
            if args.src or args.size or args.out:
                parser.error("--plan replaces SRC, --size and --out")
            jobs = load_plan(args.plan, args.only)
            if args.preview:
                jobs = [j for j in jobs if j["kind"] == "canvas"]
                if not jobs:
                    raise UsageError("--preview renders canvas entries and the plan has none")
        else:
            if args.preview:
                parser.error("--preview needs --plan")
            if not args.src or not args.size or not args.out:
                parser.error("give SRC..., --size and --out (or --plan)")
            if args.name and len(args.src) > 1:
                parser.error("--name needs a single source")
            if args.flatten:
                hex_rgba(args.flatten)
            jobs = [{"src": s, "sizes": args.size, "out": args.out, "name": args.name, "pad": args.pad, "flatten": args.flatten,
                     "label": s.name, "kind": "svg" if s.suffix.lower() == ".svg" else "html"} for s in args.src]
        for job in jobs:
            if job["kind"] != "canvas" and (not job["src"].is_file() or job["src"].suffix.lower() not in (".svg", ".html", ".htm")):
                raise UsageError(f"{job['src']}: src must be an existing .svg or .html file")
            if job["kind"] != "canvas":
                job["base"] = job.get("name") or job["src"].stem
            else:
                job["base"] = job["name"]
            if not 0 <= float(job.get("pad", 0) or 0) <= 0.4:
                raise UsageError(f"{job['label']}: pad must be 0-0.4")
        holders = [m for m in (check_placeholders(j) for j in jobs) if m]
        if holders:
            for m in holders:
                print(f"FAIL  {m}; replace them before exporting")
            return 1
        project, info = prepare_canvas_jobs(jobs, args.plan, args.preview, args.concept)
        chrome = browser.find_chrome(args.chrome)
        started = dl.now_utc()
        problems = 0
        findings: list[con.Finding] = []
        fonts: list[str] = []
        publish: list[tuple[Path, Path]] = []
        with tempfile.TemporaryDirectory() as tmp:
            for job in jobs:
                pr, f, fp = export(chrome, job, Path(tmp), not args.no_contrast, publish)
                problems += pr
                findings += f
                fonts += fp
            if findings:
                for f in findings:
                    if f.result != con.PASS:
                        print(f.line())
                counts = con.summary(findings)
                print(f"contrast: {counts[con.PASS]} PASS, {counts[con.FAIL]} FAIL, {counts[con.REVIEW]} REVIEW REQUIRED")
            for line in fonts:
                print(f"FAIL  text: {line}")
            failed = problems + sum(f.result == con.FAIL for f in findings) + len(fonts)
            if failed:
                print(f"exported nothing: {failed} problem(s); existing files are untouched")
                return 1
            lock_dir = (project.root / "brand" / ".build") if project and not args.preview else Path(tmp)
            with DirLock(lock_dir / "publish.lock", "brand exports"):
                for staged, dest in publish:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(staged), str(dest))
        review = any(f.result == con.REVIEW for f in findings)
        print(f"exported {len(publish)} file(s) from {len(jobs)} source(s); 0 problem(s)"
              + ("; status REVIEW REQUIRED: look at the text marked above" if review else ""))
        canvas_published = [(d) for _, d in publish if any(j["kind"] == "canvas" and d.parent == j["out"] for j in jobs)]
        if project and not args.preview and canvas_published:
            write_manifest(project, info, jobs, canvas_published, chrome, started, findings, fonts, args.no_contrast)
        return 0
    except (UsageError, OperationalError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (InputError, TokenError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def write_manifest(p: dl.Project, info: dict, jobs: list[dict], files: list[Path], chrome: str, started: str,
                   findings: list[con.Finding], fonts: list[str], skipped: bool) -> None:
    outputs = []
    for f in files:
        with Image.open(f) as im:
            size = list(im.size)
        outputs.append({"path": Path(os.path.relpath(f, p.root)).as_posix(), "sha256": sha256_file(f),
                        "bytes": f.stat().st_size, "size": size})
    canvas_jobs = [j for j in jobs if j["kind"] == "canvas"]
    ad = canvas_jobs[0]["ad"]
    counts = con.summary(findings)
    contrast = ("SKIPPED", "--no-contrast") if skipped else (con.overall(counts), f"{len(findings)} text runs")
    checks = {"verify": {"result": "PASS", "detail": f"{len(files)} file(s)"},
              "contrast": {"result": contrast[0], "detail": contrast[1]},
              "text": {"result": "SKIPPED" if skipped else "PASS", "detail": "glyph coverage and clipping of every caption run"}}
    status = "review-required" if any(c["result"] in ("REVIEW REQUIRED", "SKIPPED") for c in checks.values()) else "complete"
    assets = []
    for j in canvas_jobs:
        for slot, rel in (j["asset"].get("slots") or {}).items():
            path = resolve_inside(p.root, rel, slot, must_exist=True)
            entry = {"path": rel, "sha256": sha256_file(path)}
            if slot == "image":
                entry["license"] = j["asset"].get("imageLicense", "")
            assets.append(entry)
    manifest = {"schemaVersion": 1, "runId": run_id(), "family": "marketing", "mode": "production", "tool": "export_svg.py",
                "startedAt": started, "finishedAt": dl.now_utc(),
                "engine": {"api": harnesslib.API_VERSION, "browser": browser.version(chrome)},
                "inputs": {"config": sha256_text(canonical([j["asset"] for j in canvas_jobs])), "direction": info.get("direction"),
                           "concept": info.get("concept"), "assets": assets},
                "approvals": info.get("approvals", []),
                "fonts": [{"family": f["family"], "source": f.get("source", "local"), "weight": f["weight"], "style": f["style"],
                           **({"sha256": f["sha256"]} if "sha256" in f else {})} for f in ad["faces"]],
                "seed": None, "outputs": outputs, "checks": checks, "status": status}
    path = dl.write_run_manifest(p.root, manifest)
    print(f"run manifest: {path.relative_to(p.root).as_posix()} ({status})")


if __name__ == "__main__":
    raise SystemExit(main())
