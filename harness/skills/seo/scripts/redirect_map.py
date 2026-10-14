#!/usr/bin/env python3
"""Build and check an old -> new redirect map for a site migration.

build (default): python redirect_map.py OLD NEW [--format csv|nginx|netlify|next|json]
  OLD and NEW are URL lists: a crawl CSV (Address column, optional Title 1 / H1-1 /
  Status Code), a sitemap.xml (or sitemap index of local files), or a text file with
  one URL per line. Matching, in order:
    exact      same path
    normalised same path after lowercasing, dropping index/.html/.php and trailing slashes
    slug       same last path segment, unique among the new URLs
    title      title or H1 similarity >= --similarity (needs titles in both lists)
  Anything else is reported as UNMAPPED: choose a real successor or let it 404/410.
  The home page is never used as a catch-all (Google treats that as a soft 404).

check: python redirect_map.py --check MAP.csv [--new NEW]
  Validates an existing map (columns old,new or source,destination): self-redirects,
  chains (a target that is itself redirected), loops, duplicate sources, and targets
  that are missing from NEW or not 200 there.

Old URLs keep their host only when it differs from the target host. Redirects use 301.
Usage:
  python redirect_map.py old_crawl.csv new_sitemap.xml --format nginx > redirects.conf
  python redirect_map.py --check redirects.csv --new new_crawl.csv
Exit: 0 map clean, 1 unmapped URLs or map problems, 2 bad input.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from seo_io import InputError, md_table, num, read_table, resolve, run

URL_ALIASES = {"address": ["url", "loc", "page", "old", "new", "source", "destination"],
               "title": ["title 1", "page title"], "h1": ["h1-1"],
               "status": ["status code", "http status code", "response code"]}


def load_urls(path: Path) -> list[dict]:
    if not path.exists():
        raise InputError(f"{path}: file not found")
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if text.lstrip().startswith("<"):
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise InputError(f"{path}: not valid XML ({exc})") from None
        locs = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
        if root.tag.endswith("sitemapindex"):
            out = []
            for loc in locs:
                child = path.parent / Path(urlsplit(loc).path).name
                if not child.exists():
                    raise InputError(f"{path}: sitemap index lists {loc}; save it next to the index as {child.name}")
                out += load_urls(child)
            return out
        return [{"url": u, "title": "", "status": 200} for u in locs]
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    if "," in first or "\t" in first or ";" in first:
        table = read_table(path)
        cols = resolve(table[0].keys(), URL_ALIASES, {}, ("address",), str(path))
        return [{"url": r[cols["address"]].strip(),
                 "title": (r.get(cols.get("title", ""), "") or r.get(cols.get("h1", ""), "") or "").strip(),
                 "status": int(num(r.get(cols.get("status", ""), "200"), 200))}
                for r in table if r.get(cols["address"], "").strip()]
    return [{"url": ln.strip(), "title": "", "status": 200} for ln in text.splitlines()
            if ln.strip() and not ln.startswith("#")]


def path_of(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


def normalise(path: str) -> str:
    p = path.split("?")[0].lower()
    p = re.sub(r"/(index|default)\.(html?|php|aspx?)$", "/", p)
    p = re.sub(r"\.(html?|php|aspx?)$", "", p)
    return p.rstrip("/") or "/"


def slug(path: str) -> str:
    return normalise(path).rsplit("/", 1)[-1]


def build(old: list[dict], new: list[dict], similarity: float) -> tuple[list[dict], list[dict]]:
    new_live = [n for n in new if n["status"] == 200]
    by_path = {path_of(n["url"]): n for n in new_live}
    by_norm = {}
    for n in new_live:
        by_norm.setdefault(normalise(path_of(n["url"])), n)
    slugs: dict[str, list] = {}
    for n in new_live:
        slugs.setdefault(slug(path_of(n["url"])), []).append(n)
    mapped, unmapped = [], []
    for o in old:
        op = path_of(o["url"])
        hit, how = by_path.get(op), "exact"
        if not hit:
            hit, how = by_norm.get(normalise(op)), "normalised"
        if not hit and slug(op) not in ("", "/") and len(slugs.get(slug(op), [])) == 1:
            hit, how = slugs[slug(op)][0], "slug"
        if not hit and o["title"]:
            best, score = None, 0.0
            for n in new_live:
                if n["title"]:
                    s = difflib.SequenceMatcher(None, o["title"].lower(), n["title"].lower()).ratio()
                    if s > score:
                        best, score = n, s
            if best and score >= similarity:
                hit, how = best, f"title {score:.2f}"
        if hit and normalise(path_of(hit["url"])) == "/" and normalise(op) != "/":
            hit = None  # never send a deep page to the home page
        if hit and urlsplit(hit["url"]).netloc == urlsplit(o["url"]).netloc and path_of(hit["url"]) == op:
            continue  # unchanged URL: no redirect needed
        if hit:
            mapped.append({"old": o["url"], "new": hit["url"], "match": how})
        else:
            unmapped.append({"old": o["url"], "title": o["title"]})
    return mapped, unmapped


def check(rows: list[dict], new: list[dict] | None) -> list[dict]:
    problems = []
    sources: dict[str, str] = {}
    for r in rows:
        src, dst = r["old"], r["new"]
        if src in sources:
            problems.append({"old": src, "new": dst, "problem": f"duplicate source (also -> {sources[src]})"})
        sources[src] = dst
    key = lambda u: normalise(path_of(u)) + "@" + urlsplit(u).netloc  # noqa: E731
    by_key = {key(s): d for s, d in sources.items()}
    for src, dst in sources.items():
        if key(src) == key(dst):
            problems.append({"old": src, "new": dst, "problem": "redirects to itself"})
            continue
        seen, cur, hops = {key(src)}, dst, 1
        while key(cur) in by_key:
            if key(cur) in seen:
                problems.append({"old": src, "new": dst, "problem": "redirect loop"})
                break
            seen.add(key(cur))
            cur, hops = by_key[key(cur)], hops + 1
        else:
            if hops > 1:
                problems.append({"old": src, "new": dst, "problem": f"chain: {hops} hops; point straight at {cur}"})
    if new is not None:
        status = {key(n["url"]): n["status"] for n in new}
        for src, dst in sources.items():
            if key(dst) in by_key:
                continue
            s = status.get(key(dst))
            if s is None:
                problems.append({"old": src, "new": dst, "problem": "target not in the new site list"})
            elif s != 200:
                problems.append({"old": src, "new": dst, "problem": f"target returns {s}"})
    return problems


def render(mapped: list[dict], fmt: str) -> str:
    def src(m):
        o, n = urlsplit(m["old"]), urlsplit(m["new"])
        return path_of(m["old"]) if not o.netloc or o.netloc == n.netloc else m["old"]

    def dst(m):
        o, n = urlsplit(m["old"]), urlsplit(m["new"])
        return path_of(m["new"]) if o.netloc == n.netloc and n.netloc else m["new"]

    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["old", "new", "status", "match"])
        for m in mapped:
            w.writerow([m["old"], m["new"], 301, m["match"]])
        return buf.getvalue()
    if fmt == "nginx":
        lines = ["# map $request_uri $redirect_to { ... }  then: if ($redirect_to) { return 301 $redirect_to; }"]
        lines += [f"    {src(m)} {dst(m)};" for m in mapped]
        return "\n".join(lines) + "\n"
    if fmt == "netlify":
        return "".join(f"{src(m)}  {dst(m)}  301\n" for m in mapped)
    if fmt == "next":
        return json.dumps([{"source": src(m), "destination": dst(m), "permanent": True} for m in mapped], indent=2) + "\n"
    return json.dumps(mapped, indent=2) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("old", nargs="?", type=Path)
    p.add_argument("new", nargs="?", type=Path)
    p.add_argument("--check", type=Path, metavar="MAP.csv")
    p.add_argument("--new", dest="new_list", type=Path, help="with --check: the new site's URL list")
    p.add_argument("--format", choices=["report", "csv", "nginx", "netlify", "next", "json"], default="report")
    p.add_argument("--similarity", type=float, default=0.85)
    a = p.parse_args()

    if a.check:
        table = read_table(a.check)
        cols = resolve(table[0].keys(), {"old": ["source", "from", "old url"], "new": ["destination", "target", "to", "new url"]},
                       {}, ("old", "new"), str(a.check))
        rows = [{"old": r[cols["old"]].strip(), "new": r[cols["new"]].strip()} for r in table if r[cols["old"]].strip()]
        problems = check(rows, load_urls(a.new_list) if a.new_list else None)
        if a.format == "json":
            print(json.dumps({"rules": len(rows), "problems": problems}, indent=2))
        else:
            print(f"# Redirect map check: {len(rows)} rules, {len(problems)} problems\n")
            if problems:
                print(md_table(["Old", "New", "Problem"], [[x["old"], x["new"], x["problem"]] for x in problems]))
        return 1 if problems else 0

    if not (a.old and a.new):
        raise InputError("give OLD and NEW URL lists, or --check MAP.csv")
    mapped, unmapped = build(load_urls(a.old), load_urls(a.new), a.similarity)
    problems = check(mapped, load_urls(a.new))
    if a.format != "report":
        sys.stdout.write(render(mapped, a.format))
        if unmapped or problems:
            print(f"warning: {len(unmapped)} unmapped URLs, {len(problems)} map problems; run with --format report",
                  file=sys.stderr)
        return 1 if unmapped or problems else 0
    counts: dict[str, int] = {}
    for m in mapped:
        counts[m["match"].split()[0]] = counts.get(m["match"].split()[0], 0) + 1
    print(f"# Redirect map: {len(mapped)} mapped, {len(unmapped)} unmapped\n")
    print("Matches: " + (", ".join(f"{k} {v}" for k, v in counts.items()) or "none") + "\n")
    if unmapped:
        print("## Unmapped (no suitable target)\n")
        print(md_table(["Old URL", "Title"], [[u["old"], u["title"]] for u in unmapped]))
        print("\nChoose a real successor for each, or let it return 404/410. Never redirect them all to the home page.\n")
    if problems:
        print("## Map problems\n")
        print(md_table(["Old", "New", "Problem"], [[x["old"], x["new"], x["problem"]] for x in problems]) + "\n")
    print("## Review the non-exact matches\n")
    review = [m for m in mapped if m["match"] != "exact"]
    print(md_table(["Old", "New", "Match"], [[m["old"], m["new"], m["match"]] for m in review]) if review else "None.")
    print("\nNext: export with --format csv|nginx|netlify|next, then follow references/migration.md.")
    return 1 if unmapped or problems else 0


if __name__ == "__main__":
    run(main)
