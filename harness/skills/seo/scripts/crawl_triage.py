#!/usr/bin/env python3
"""Rank crawl issues by the internal link equity they affect, then give the top fixes.

Input: a crawl export with one row per URL. Screaming Frog "Internal: All" works as is;
Sitebulb, Lumar and other crawlers work through header aliases or --map canonical=Header:
  address, status_code, content_type, indexability, indexability_status, title, h1,
  canonical, meta_robots, x_robots, depth, inlinks, unique_inlinks, redirect_url
Optional --inlinks: a Screaming Frog "All Inlinks" export (Source, Destination) used to
count unique linking pages when the crawl has no inlinks column.

Issues (severity follows references/technical.md):
  Critical  5xx; canonical to another host or to a 4xx/5xx URL
  High      4xx linked internally; redirect loops and chains of 3+ hops
  Medium    internal links to redirects; noindex or canonicalised-away pages that are
            heavily linked; orphan indexable pages; missing title; duplicate titles
  Low       indexable pages deeper than --max-depth clicks
Score = severity weight x (unique inlinks + 1); depth breaks ties. The report lists the
top three fixes (issue types by total score), effort (S <= 1 h, M <= 1 day, L > 1 day)
and a this-week list of the highest-scoring URLs.

Usage:
  python crawl_triage.py internal_all.csv [--inlinks all_inlinks.csv] [--max-depth 3] [--top 10] [--json]
Exit: 0 report written, 2 bad input.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from seo_io import InputError, emit, md_table, num, parse_map, read_table, resolve, run

ALIASES = {
    "address": ["url", "page", "page url", "full url"],
    "status_code": ["status code", "http status code", "response code", "http status", "status"],
    "content_type": ["content type", "content-type", "mime type"],
    "indexability": ["indexable"],
    "indexability_status": ["indexability status", "non-indexable reason"],
    "title": ["title 1", "page title", "title tag"],
    "h1": ["h1-1", "h1 1"],
    "canonical": ["canonical link element 1", "canonical url", "canonical link"],
    "meta_robots": ["meta robots 1", "robots meta"],
    "x_robots": ["x-robots-tag 1", "x robots tag"],
    "depth": ["crawl depth", "click depth", "level"],
    "inlinks": ["internal inlinks", "no. of inlinks"],
    "unique_inlinks": ["unique internal inlinks", "unique inlinks count"],
    "redirect_url": ["redirect url", "redirect target", "location"],
}
SEVERITY = {"Critical": 8, "High": 4, "Medium": 2, "Low": 1}
FIXES = {
    "server-error": ("Fix 5xx responses (logs, timeouts, upstream errors) on the listed URLs", "M"),
    "canonical-broken": ("Point canonicals at the live 200 URL on the production host", "S"),
    "broken-linked": ("Update or remove internal links to 4xx URLs; 301 removed pages with a true successor", "S"),
    "redirect-loop": ("Break redirect loops: each URL redirects once, to a final 200", "S"),
    "redirect-chain": ("Collapse chains to one hop and update links to the final URL", "S"),
    "linked-redirect": ("Update internal links (nav, templates, content) to the final URLs", "M"),
    "noindex-linked": ("Stop linking heavily to noindex/canonicalised pages, or make them indexable if they matter", "M"),
    "orphan": ("Link orphan pages from relevant hubs, or remove them from the sitemap if they don't matter", "M"),
    "title-missing": ("Add unique, descriptive titles (template fix first)", "S"),
    "title-duplicate": ("Make titles unique per page; fix the template that repeats them", "M"),
    "deep": ("Bring important deep pages within 3 clicks (hub links, breadcrumbs, pagination)", "L"),
}


def norm(url: str) -> str:
    return url.strip().rstrip("/") if url.strip() not in ("", "/") else url.strip()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("crawl", type=Path)
    p.add_argument("--inlinks", type=Path, help="All Inlinks export (Source, Destination)")
    p.add_argument("--map", action="append", metavar="canonical=Header")
    p.add_argument("--max-depth", type=int, default=3)
    p.add_argument("--heavy", type=int, default=10, help="noindex pages with at least this many unique inlinks")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    table = read_table(a.crawl)
    cols = resolve(table[0].keys(), ALIASES, parse_map(a.map), ("address", "status_code"), str(a.crawl))
    get = lambda row, c: row.get(cols[c], "") if c in cols else ""  # noqa: E731

    link_count: dict[str, set] = defaultdict(set)
    if a.inlinks:
        links = read_table(a.inlinks)
        lcols = resolve(links[0].keys(), {"source": ["from"], "destination": ["to", "target"]}, {},
                        ("source", "destination"), str(a.inlinks))
        for row in links:
            link_count[norm(row[lcols["destination"]])].add(norm(row[lcols["source"]]))

    pages = {}
    for row in table:
        url = norm(get(row, "address"))
        if not url:
            continue
        uniq = num(get(row, "unique_inlinks"), -1)
        if uniq < 0:
            uniq = len(link_count[url]) if a.inlinks else num(get(row, "inlinks"), 0)
        pages[url] = {
            "status": int(num(get(row, "status_code"))), "html": "html" in get(row, "content_type").lower() or not get(row, "content_type"),
            "indexable": get(row, "indexability").lower() in ("indexable", "true", "yes", "1") if "indexability" in cols else None,
            "reason": get(row, "indexability_status"), "title": get(row, "title"), "canonical": norm(get(row, "canonical")),
            "robots": (get(row, "meta_robots") + " " + get(row, "x_robots")).lower(),
            "depth": int(num(get(row, "depth"), -1)), "inlinks": int(uniq), "redirect": norm(get(row, "redirect_url")),
        }
    if not pages:
        raise InputError(f"{a.crawl}: no URLs")
    host = Counter(urlsplit(u).netloc for u in pages).most_common(1)[0][0]

    issues = []

    def add(kind, sev, url, detail):
        info = pages[url]
        issues.append({"type": kind, "severity": sev, "url": url, "detail": detail, "inlinks": info["inlinks"],
                       "depth": info["depth"], "score": SEVERITY[sev] * (info["inlinks"] + 1)})

    titles = defaultdict(list)
    for url, info in pages.items():
        s = info["status"]
        indexable = info["indexable"] if info["indexable"] is not None else (
            s == 200 and "noindex" not in info["robots"] and (not info["canonical"] or info["canonical"] == url))
        if s >= 500:
            add("server-error", "Critical", url, f"HTTP {s}")
        elif 400 <= s < 500 and info["inlinks"] > 0:
            add("broken-linked", "High", url, f"HTTP {s}, linked from {info['inlinks']} pages")
        elif 300 <= s < 400:
            hops, seen, cur = 0, {url}, url
            while cur in pages and 300 <= pages[cur]["status"] < 400 and pages[cur]["redirect"]:
                cur = pages[cur]["redirect"]
                hops += 1
                if cur in seen:
                    hops = -1
                    break
                seen.add(cur)
            if hops == -1:
                add("redirect-loop", "High", url, "redirect loop")
            elif hops >= 2:
                add("redirect-chain", "High" if hops >= 3 else "Medium", url, f"{hops} hops to {cur}")
            elif info["inlinks"] > 0:
                add("linked-redirect", "Medium", url, f"linked {info['inlinks']}x, redirects to {info['redirect'] or '?'}")
        if s == 200 and info["html"]:
            canon = info["canonical"]
            if canon and canon != url:
                target = pages.get(canon)
                other_host = urlsplit(canon).netloc not in ("", host)
                if other_host or (target and target["status"] >= 400):
                    add("canonical-broken", "Critical", url,
                        f"canonical to {'another host' if other_host else 'HTTP ' + str(target['status'])}: {canon}")
            if not indexable and info["inlinks"] >= a.heavy:
                add("noindex-linked", "Medium", url, f"non-indexable ({info['reason'] or 'noindex/canonicalised'}), "
                                                     f"{info['inlinks']} unique inlinks")
            if indexable:
                if info["inlinks"] == 0 and info["depth"] != 0:
                    add("orphan", "Medium", url, "no internal inlinks (found via sitemap or URL list)")
                if not info["title"]:
                    add("title-missing", "Medium", url, "no <title>")
                else:
                    titles[info["title"].strip().lower()].append(url)
                if info["depth"] > a.max_depth:
                    add("deep", "Low", url, f"{info['depth']} clicks from the start URL")
    for title, urls in titles.items():
        if len(urls) > 1:
            for url in urls:
                add("title-duplicate", "Medium", url, f"title shared by {len(urls)} pages")

    by_type: dict[str, list] = defaultdict(list)
    for i in issues:
        by_type[i["type"]].append(i)
    ranked = sorted(by_type.items(), key=lambda kv: -sum(i["score"] for i in kv[1]))
    fixes = [{"type": t, "severity": items[0]["severity"], "urls": len(items),
              "inlinks_affected": sum(i["inlinks"] for i in items), "fix": FIXES[t][0], "effort": FIXES[t][1]}
             for t, items in ranked]
    week = sorted(issues, key=lambda i: (-i["score"], i["depth"]))[: a.top]

    md = [f"# Crawl triage: {host}", "", f"{len(pages)} URLs, {len(issues)} issues in {len(by_type)} types. "
          "Weighted by unique internal inlinks (the link equity each issue wastes).", "", "## Top three fixes", ""]
    for n, f in enumerate(fixes[:3], 1):
        md.append(f"{n}. **{f['fix']}** - {f['severity']}, {f['urls']} URLs, {f['inlinks_affected']} inlinks affected, "
                  f"effort {f['effort']}.")
    md += ["", "## All issue types", "", md_table(["Type", "Severity", "URLs", "Inlinks affected", "Effort"],
           [[f["type"], f["severity"], f["urls"], f["inlinks_affected"], f["effort"]] for f in fixes]), "",
           "## This week", "", md_table(["URL", "Issue", "Severity", "Inlinks", "Detail"],
           [[i["url"], i["type"], i["severity"], i["inlinks"], i["detail"]] for i in week]), "",
           "Data gaps: one crawl is one snapshot; JavaScript-rendered links count only if the crawler rendered JS; "
           "orphans need the sitemap or URL list in the crawl."]
    emit({"host": host, "urls": len(pages), "fixes": fixes, "this_week": week, "issues": issues}, a.json, "\n".join(md))
    return 0


if __name__ == "__main__":
    run(main)
