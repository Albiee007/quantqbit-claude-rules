#!/usr/bin/env python3
"""Lint built HTML against the seo skill's build-time checklist (offline, for CI).

Point it at build output (dist/, out/, build/, public/, .next/server/app) or single files.
Checks the raw HTML a crawler receives, the same signals check-url.sh prints for a live URL:

  errors    no <title> or more than one; no canonical, more than one, or a relative one;
            no <html lang>; no viewport meta; noindex in meta robots; images without alt;
            JSON-LD that does not parse or still holds {{ placeholders }};
            the same title on more than one page
  warnings  no meta description or more than one; title outside 30-65 characters;
            description outside 70-170; not exactly one <h1>; missing og:title,
            og:description, og:image or twitter:card; relative og:image;
            images without width/height; the same description on more than one page
Error pages (404.html, 500.html, _not-found.html, _global-error.html, ...) skip the
canonical and noindex checks. <title> inside inline SVG or MathML is ignored. Use --exclude
GLOB for other intentionally non-indexable pages (admin, previews).

Usage:
  python lint_html.py dist/ [--exclude "admin/**"] [--warnings-as-errors] [--json]
Exit: 0 clean (warnings allowed), 1 errors found, 2 bad input.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

from seo_io import InputError, emit, md_table, run

SKIP_DIRS = {"node_modules", ".git", "__pycache__"}
ERROR_PAGE = re.compile(r"^_?(404|410|500|50\d|error|global-error|not-found)(\.html?)?$", re.I)


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.titles: list[str] = []
        self.meta: dict[str, list[str]] = defaultdict(list)
        self.canonicals: list[str] = []
        self.h1 = 0
        self.images: list[dict] = []
        self.ld: list[str] = []
        self._in = None
        self._buf: list[str] = []
        self._svg = 0  # <title> inside inline SVG/MathML labels the graphic, not the page

    def handle_starttag(self, tag, attrs):
        at = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("svg", "math"):
            self._svg += 1
        elif tag == "html":
            self.lang = at.get("lang", "").strip() or None
        elif tag == "title" and not self._svg:
            self._in, self._buf = "title", []
        elif tag == "meta":
            name = (at.get("name") or at.get("property") or "").lower()
            if name:
                self.meta[name].append(at.get("content", ""))
        elif tag == "link" and "canonical" in at.get("rel", "").lower().split():
            self.canonicals.append(at.get("href", ""))
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            self.images.append(at)
        elif tag == "script" and at.get("type", "").lower() == "application/ld+json":
            self._in, self._buf = "ld", []

    def handle_endtag(self, tag):
        if tag in ("svg", "math") and self._svg:
            self._svg -= 1
        elif self._in == "title" and tag == "title":
            self.titles.append(" ".join("".join(self._buf).split()))
            self._in = None
        elif self._in == "ld" and tag == "script":
            self.ld.append("".join(self._buf))
            self._in = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)


def files(targets: list[Path], exclude: list[str]) -> list[tuple[Path, str]]:
    out = []
    for t in targets:
        if not t.exists():
            raise InputError(f"{t}: not found")
        if t.is_file():
            out.append((t, t.name))
            continue
        for f in sorted(t.rglob("*.htm*")):
            rel = f.relative_to(t).as_posix()
            if f.suffix.lower() in (".html", ".htm") and not SKIP_DIRS & set(f.relative_to(t).parts) \
                    and not any(fnmatch.fnmatch(rel, g) for g in exclude):
                out.append((f, rel))
    if not out:
        raise InputError("no .html files found")
    return out


def lint(path: Path) -> tuple[Page, list[str], list[str]]:
    page = Page()
    page.feed(path.read_text(encoding="utf-8", errors="replace"))
    err, warn = [], []
    error_page = bool(ERROR_PAGE.match(path.name)) or bool(ERROR_PAGE.match(path.parent.name) and path.stem == "index")
    if not page.titles:
        err.append("no <title>")
    elif len(page.titles) > 1:
        err.append(f"{len(page.titles)} <title> tags")
    elif not 30 <= len(page.titles[0]) <= 65:
        warn.append(f"title is {len(page.titles[0])} chars (aim ~50-60)")
    if not error_page:
        if not page.canonicals:
            err.append("no canonical")
        elif len(page.canonicals) > 1:
            err.append(f"{len(page.canonicals)} canonicals")
        elif not page.canonicals[0].startswith(("http://", "https://")):
            err.append(f"relative canonical '{page.canonicals[0]}'")
        robots = " ".join(page.meta.get("robots", []) + page.meta.get("googlebot", [])).lower()
        if "noindex" in robots:
            err.append("meta robots noindex")
    if not page.lang:
        err.append("no <html lang>")
    if not page.meta.get("viewport"):
        err.append("no viewport meta")
    desc = page.meta.get("description", [])
    if not desc:
        warn.append("no meta description")
    elif len(desc) > 1:
        warn.append(f"{len(desc)} meta descriptions")
    elif not 70 <= len(desc[0]) <= 170:
        warn.append(f"description is {len(desc[0])} chars (aim ~120-160)")
    if page.h1 != 1:
        warn.append(f"{page.h1} <h1> tags (want 1)")
    missing_og = [k for k in ("og:title", "og:description", "og:image", "twitter:card") if not page.meta.get(k)]
    if missing_og:
        warn.append("missing " + ", ".join(missing_og))
    for img in page.meta.get("og:image", [])[:1]:
        if not img.startswith(("http://", "https://")):
            warn.append(f"relative og:image '{img}'")
    no_alt = [i.get("src", "?") for i in page.images if "alt" not in i]
    if no_alt:
        err.append(f"{len(no_alt)} <img> without alt (e.g. {no_alt[0]})")
    no_dims = [i for i in page.images if not (("width" in i and "height" in i) or "aspect-ratio" in i.get("style", ""))]
    if no_dims:
        warn.append(f"{len(no_dims)} <img> without width/height")
    for block in page.ld:
        if "{{" in block:
            err.append("JSON-LD holds a {{ placeholder }}")
        try:
            json.loads(block)
        except ValueError as exc:
            err.append(f"JSON-LD does not parse ({exc.msg} at line {exc.lineno})")
    return page, err, warn


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("targets", nargs="+", type=Path)
    p.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    p.add_argument("--warnings-as-errors", action="store_true")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    results = []
    titles, descs = defaultdict(list), defaultdict(list)
    for path, rel in files(a.targets, a.exclude):
        page, err, warn = lint(path)
        results.append({"file": rel, "errors": err, "warnings": warn})
        if page.titles and not ERROR_PAGE.match(path.name):
            titles[page.titles[0].lower()].append(rel)
        if page.meta.get("description"):
            descs[page.meta["description"][0].strip().lower()].append(rel)
    by_file = {r["file"]: r for r in results}
    for t, fs in titles.items():
        if len(fs) > 1:
            for f in fs:
                by_file[f]["errors"].append(f"title shared with {len(fs) - 1} other page(s)")
    for d, fs in descs.items():
        if len(fs) > 1:
            for f in fs:
                by_file[f]["warnings"].append(f"description shared with {len(fs) - 1} other page(s)")
    n_err = sum(len(r["errors"]) for r in results)
    n_warn = sum(len(r["warnings"]) for r in results)
    bad = [r for r in results if r["errors"] or r["warnings"]]
    md = [f"# HTML SEO lint: {len(results)} pages, {n_err} errors, {n_warn} warnings", ""]
    if bad:
        md.append(md_table(["File", "Errors", "Warnings"],
                           [[r["file"], "; ".join(r["errors"]) or "-", "; ".join(r["warnings"]) or "-"] for r in bad]))
    else:
        md.append("All pages pass.")
    md += ["", "Raw HTML only: confirm client-rendered changes with a browser or URL Inspection, and schema with the "
           "Rich Results Test."]
    emit({"pages": len(results), "errors": n_err, "warnings": n_warn, "results": results}, a.json, "\n".join(md))
    return 1 if n_err or (a.warnings_as_errors and n_warn) else 0


if __name__ == "__main__":
    run(main)
