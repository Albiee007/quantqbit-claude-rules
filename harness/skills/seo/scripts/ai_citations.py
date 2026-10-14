#!/usr/bin/env python3
"""Sort AI-search opportunities into owned / contested / under-represented / absent.

Inputs (any combination; at least one of --bing-queries or --prompts):
  --bing-queries  Bing Webmaster Tools AI Performance "grounding queries" export: the
                  phrases Copilot used to retrieve and cite your pages, with citation counts
  --bing-pages    the AI Performance page export (cited pages and counts): top cited pages
  --search        a search performance export (Search Console or Bing): query, impressions,
                  position. Queries you rank for in the top 10 but that never ground a
                  citation are "under-represented".
  --prompts       a prompt-library results CSV kept by hand (template in
                  references/ai-visibility.md): prompt, engine, cited (yes/no), competitors
                  (names or domains, ";"-separated). Run the prompts yourself in each assistant;
                  this script never queries an AI service.
The Bing export column names are matched by alias (query/grounding query, citations,
citation share, page/url) and are provisional until confirmed against a real export; use
--map to fix. Bing's own Citation Share (preview, June 2026) is shown when the export has it.

Buckets and the one move for each:
  owned             cited and ranking (or cited with no competitor in the answer): keep it fresh
  contested         cited, but competitors are cited in the same answers: out-evidence them
  under-represented ranking top 10 but rarely or never cited: make the passage citable
  absent            asked, never cited: build or expand the page that answers it
Grounding queries are machine-written retrieval phrases, not user searches, so matching
them to search queries is approximate (normalised text, then word overlap >= 0.8).

Usage:
  python ai_citations.py --bing-queries grounding.csv [--bing-pages pages.csv]
      [--search gsc_queries.csv] [--prompts prompt_results.csv] [--min-citations 3] [--json]
Exit: 0 report written, 2 bad input.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from seo_io import InputError, emit, md_table, num, parse_map, read_table, resolve, run

ALIASES = {
    "query": ["grounding query", "grounding queries", "top queries", "keyword", "search query", "prompt"],
    "citations": ["citation", "total citations", "citation count", "times cited"],
    "share": ["citation share", "share of citations"],
    "page": ["url", "cited page", "top pages", "address"],
    "impressions": ["impr"],
    "position": ["average position", "avg position", "avg. position"],
    "engine": ["assistant", "platform", "model", "ai engine"],
    "cited": ["cited us", "we are cited", "our citation", "brand cited"],
    "competitors": ["competitors cited", "other sources", "competitor"],
}
MOVES = {
    "owned": "keep it: refresh facts and dates, keep the answer-first passage, watch for new competitors",
    "contested": "out-evidence them: first-hand data, a clearer direct answer, stronger entity signals and sources",
    "under-represented": "make the ranking passage citable: answer in the first sentence, define terms, cite numbers; "
                         "confirm Bingbot/AI bots can fetch the page",
    "absent": "build or expand a page that answers this directly, then earn mentions on the sources the engines cite",
}
YES = {"yes", "y", "true", "1", "cited", "x"}


def key(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def similar(a: str, b: str) -> bool:
    if a == b:
        return True
    sa, sb = set(a.split()), set(b.split())
    return bool(sa and sb) and len(sa & sb) / len(sa | sb) >= 0.8


def table(path: Path | None, overrides: dict, need: tuple[str, ...]) -> tuple[list[dict], dict]:
    if not path:
        return [], {}
    rows = read_table(path)
    return rows, resolve(rows[0].keys(), ALIASES, overrides, need, str(path))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bing-queries", type=Path)
    p.add_argument("--bing-pages", type=Path)
    p.add_argument("--search", type=Path)
    p.add_argument("--prompts", type=Path)
    p.add_argument("--map", action="append", metavar="canonical=Header")
    p.add_argument("--min-citations", type=float, default=3, help="below this a ranking query counts as rarely cited")
    p.add_argument("--min-impressions", type=float, default=50)
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    if not (a.bing_queries or a.prompts):
        raise InputError("give --bing-queries and/or --prompts")
    ov = parse_map(a.map)

    cited: dict[str, float] = defaultdict(float)
    share: dict[str, float] = {}
    gq, gcols = table(a.bing_queries, ov, ("query", "citations"))
    for r in gq:
        if r[gcols["query"]].strip():
            cited[key(r[gcols["query"]])] += num(r[gcols["citations"]])
            if "share" in gcols and r[gcols["share"]].strip():
                share[key(r[gcols["query"]])] = num(r[gcols["share"]])

    buckets: dict[str, list] = {k: [] for k in MOVES}
    sq, scols = table(a.search, ov, ("query", "impressions", "position"))
    cited_keys = list(cited)
    for r in sq:
        q = r[scols["query"]].strip()
        if not q:
            continue
        impr, pos = num(r[scols["impressions"]]), num(r[scols["position"]])
        if impr < a.min_impressions or pos > 10 or pos <= 0:
            continue
        k = key(q)
        n = cited.get(k)
        if n is None:
            n = sum(c for ck, c in cited.items() if similar(k, ck)) if cited_keys else 0
        item = {"query": q, "position": round(pos, 1), "impressions": int(impr), "citations": int(n)}
        if k in share:
            item["share"] = share[k]
        if n >= a.min_citations:
            buckets["owned"].append(item)
        else:
            buckets["under-represented"].append(item)

    pr, pcols = table(a.prompts, ov, ("query", "cited"))
    prompts: dict[str, dict] = {}
    for r in pr:
        q = r[pcols["query"]].strip()
        if not q:
            continue
        rec = prompts.setdefault(key(q), {"query": q, "runs": 0, "cited": 0, "competitors": defaultdict(int), "engines": set()})
        rec["runs"] += 1
        rec["cited"] += r[pcols["cited"]].strip().lower() in YES
        if "engine" in pcols and r[pcols["engine"]].strip():
            rec["engines"].add(r[pcols["engine"]].strip())
        if "competitors" in pcols:
            for c in re.split(r"[;|]", r[pcols["competitors"]]):
                if c.strip():
                    rec["competitors"][c.strip()] += 1
    for rec in prompts.values():
        comp = sorted(rec["competitors"], key=lambda c: -rec["competitors"][c])
        item = {"query": rec["query"], "runs": rec["runs"], "cited_runs": rec["cited"], "engines": sorted(rec["engines"]),
                "competitors": comp[:5]}
        if rec["cited"] == 0:
            buckets["absent"].append(item)
        elif comp:
            buckets["contested"].append(item)
        else:
            buckets["owned"].append(item)

    if not sq and not pr:
        for k, n in sorted(cited.items(), key=lambda kv: -kv[1]):
            item = {"query": k, "citations": int(n)}
            if k in share:
                item["share"] = share[k]
            buckets["owned" if n >= a.min_citations else "under-represented"].append(item)

    pages = []
    bp, bcols = table(a.bing_pages, ov, ("page", "citations"))
    for r in bp:
        pages.append({"page": r[bcols["page"]], "citations": int(num(r[bcols["citations"]]))})
    pages.sort(key=lambda x: -x["citations"])

    md = ["# AI citation share", ""]
    md.append(" | ".join(f"{k}: {len(v)}" for k, v in buckets.items()))
    for name, items in buckets.items():
        if not items:
            continue
        md += ["", f"## {name.title()} ({len(items)})", "", f"Move: {MOVES[name]}.", ""]
        searched = [i for i in items if "runs" not in i]
        asked = [i for i in items if "runs" in i]
        if searched:
            md.append(md_table(["Query", "Position", "Impressions", "Citations", "Citation share"],
                               [[i["query"], i.get("position", "-"), i.get("impressions", "-"), i.get("citations", 0),
                                 f"{i['share']:.0%}" if "share" in i else "-"] for i in searched[: a.top]]))
        if searched and asked:
            md.append("")
        if asked:
            md.append(md_table(["Prompt", "Runs", "Cited", "Engines", "Competitors cited"],
                               [[i["query"], i["runs"], i["cited_runs"], ", ".join(i["engines"]), ", ".join(i["competitors"])]
                                for i in asked[: a.top]]))
    if pages:
        md += ["", "## Most cited pages", "", md_table(["Page", "Citations"], [[x["page"], x["citations"]] for x in pages[:10]])]
    md += ["", "Data gaps: Bing's report covers Copilot and Bing AI surfaces only and is a preview; prompt results vary "
           "by run, location and account, so repeat each prompt and compare trends, not single answers."]
    emit({"buckets": buckets, "moves": MOVES, "top_pages": pages[:10]}, a.json, "\n".join(md))
    return 0


if __name__ == "__main__":
    run(main)
