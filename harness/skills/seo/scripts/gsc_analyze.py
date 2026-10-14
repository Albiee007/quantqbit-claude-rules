#!/usr/bin/env python3
"""Analyse Google Search Console performance exports: striking distance, CTR gaps,
content decay, keyword cannibalisation and core-update winners/losers.

Input: CSV/TSV exports with some of these columns (header names are auto-detected;
override with --map canonical=Header):
  query, page, date, clicks, impressions, ctr, position
Works with the Performance report UI export (Queries.csv or Pages.csv), Search Analytics
API rows saved as CSV, Looker Studio exports, and the BigQuery bulk export
(`searchdata_url_impression`: url, query, clicks, impressions, sum_position).
Rows with the same key are summed; position is impression-weighted.

Modes:
  striking  <csv>               queries at positions 4-15 with enough impressions, grouped by page
  ctr       <csv>               rows whose CTR is below ~70% of the site's OWN CTR at that position
  decay     <recent> <previous> pages (or queries) losing clicks, with a diagnosis and one action
  cannibal  <csv>               queries where 2+ of your pages compete (needs query AND page)
  update    <csv> --date D      pages that won or lost around a core update (needs date AND page)

Search Console anonymises rare queries and the API returns top rows only, so totals are
partial; every report ends with a data-gaps line. Nothing is fetched from the network.

Usage:
  python gsc_analyze.py striking queries.csv [--min-impressions 50] [--top 25] [--json]
  python gsc_analyze.py ctr queries.csv [--ratio 0.7]
  python gsc_analyze.py decay last-3-months.csv same-3-months-last-year.csv [--min-clicks 20]
  python gsc_analyze.py cannibal query-page.csv [--brand "acme|acme app"] [--dominance 0.8]
  python gsc_analyze.py update daily-page.csv --date 2026-08-20 [--window 28] [--rollout 14]
Exit: 0 report written, 2 bad input.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from seo_io import InputError, emit, md_table, num, parse_map, pct, read_table, resolve, run

ALIASES = {
    "query": ["top queries", "queries", "search query", "keyword"],
    "page": ["top pages", "pages", "url", "landing page", "address"],
    "date": ["data_date", "day"],
    "clicks": ["url clicks"],
    "impressions": ["impr", "url impressions"],
    "ctr": ["url ctr", "site ctr"],
    "position": ["average position", "avg position", "avg. position", "url position"],
    "sum_position": ["sumposition"],
}

GAPS = ("Data gaps: Search Console anonymises rare queries and exports top rows only, so totals are "
        "partial; AI features and SERP layout change CTR independently of your pages.")


class Row:
    __slots__ = ("query", "page", "date", "clicks", "impressions", "pos_sum")

    def __init__(self, query="", page="", date=""):
        self.query, self.page, self.date = query, page, date
        self.clicks = self.impressions = self.pos_sum = 0.0

    @property
    def position(self) -> float:
        return self.pos_sum / self.impressions if self.impressions else 0.0

    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0


def load(path: Path, overrides: dict, need: tuple[str, ...], key: tuple[str, ...]) -> list[Row]:
    table = read_table(path)
    cols = resolve(table[0].keys(), ALIASES, overrides, ("impressions", *need), str(path))
    if "position" not in cols and "sum_position" not in cols:
        raise InputError(f"{path}: needs a position (or BigQuery sum_position) column")
    if "clicks" not in cols and "ctr" not in cols:
        raise InputError(f"{path}: needs a clicks or ctr column")
    agg: dict[tuple, Row] = {}
    for raw in table:
        k = tuple(raw.get(cols[c], "").strip() if c in cols else "" for c in key)
        if "query" in key and not k[key.index("query")]:
            continue  # anonymised query rows carry no query text
        impr = num(raw.get(cols["impressions"]))
        if impr <= 0:
            continue
        clicks = num(raw.get(cols["clicks"])) if "clicks" in cols else round(num(raw.get(cols["ctr"])) * impr)
        if "sum_position" in cols:
            pos = num(raw.get(cols["sum_position"])) / impr + 1  # BigQuery positions are zero-based sums
        else:
            pos = num(raw.get(cols["position"]))
        row = agg.get(k)
        if row is None:
            row = agg[k] = Row(**dict(zip(key, k)))
        row.clicks += clicks
        row.impressions += impr
        row.pos_sum += pos * impr
    if not agg:
        raise InputError(f"{path}: no rows with impressions")
    return list(agg.values())


def ctr_curve(rows: list[Row], min_bucket: float = 100) -> dict[int, float]:
    """The site's own CTR by rounded position (1-20), monotone non-increasing."""
    clicks: dict[int, float] = defaultdict(float)
    impr: dict[int, float] = defaultdict(float)
    for r in rows:
        b = max(1, round(r.position))
        if b <= 20:
            clicks[b] += r.clicks
            impr[b] += r.impressions
    curve, last = {}, None
    for b in range(1, 21):
        if impr[b] >= min_bucket:
            value = clicks[b] / impr[b]
            last = value if last is None else min(last, value)
        if last is not None:
            curve[b] = last
    return curve


def expected(curve: dict[int, float], position: float) -> float | None:
    return curve.get(max(1, min(20, round(position))))


def mode_striking(rows: list[Row], a) -> tuple[dict, str]:
    curve = ctr_curve(rows)
    hits = []
    for r in rows:
        if a.low <= r.position <= a.high and r.impressions >= a.min_impressions:
            exp = expected(curve, r.position)
            weak_ctr = exp is not None and r.ctr < a.ratio * exp
            if weak_ctr:
                action = "title tweak: snippet under-performs for this position"
            elif r.position <= 10:
                action = "on-page addition: cover this query's subtopic in a section and heading"
            else:
                action = "internal links from strong pages with this query as anchor, then expand"
            target = curve.get(3, max(curve.values(), default=0))
            gain = max(0.0, r.impressions * target - r.clicks)
            hits.append({"query": r.query, "page": r.page, "position": round(r.position, 1),
                         "impressions": int(r.impressions), "clicks": int(r.clicks), "ctr": round(r.ctr, 4),
                         "potential_clicks": int(gain), "action": action})
    hits.sort(key=lambda h: (-h["potential_clicks"], -h["impressions"]))
    pages: dict[str, list] = defaultdict(list)
    for h in hits:
        pages[h["page"] or "(no page column)"].append(h)
    page_rank = sorted(pages.items(), key=lambda kv: -sum(h["potential_clicks"] for h in kv[1]))
    md = [f"# Striking distance (positions {a.low:g}-{a.high:g}, impressions >= {a.min_impressions:g})", "",
          f"{len(hits)} queries on {len(pages)} pages. Potential clicks = impressions x the site's own CTR at "
          "position 3, minus current clicks (an estimate, not a forecast).", ""]
    for page, items in page_rank[: a.top]:
        md += [f"## {page}", "", md_table(["Query", "Pos", "Impr", "CTR", "Potential", "Action"],
               [[h["query"], h["position"], h["impressions"], pct(h["ctr"]), h["potential_clicks"], h["action"]]
                for h in items[:10]]), ""]
    md.append(GAPS)
    return {"mode": "striking", "count": len(hits), "curve": curve, "pages": dict(page_rank[: a.top])}, "\n".join(md)


def mode_ctr(rows: list[Row], a) -> tuple[dict, str]:
    curve = ctr_curve(rows)
    if not curve:
        raise InputError("not enough impressions to build a CTR curve (need >= 100 per position bucket)")
    gaps = []
    for r in rows:
        exp = expected(curve, r.position)
        if exp and r.position < 20 and r.impressions >= a.min_impressions and r.ctr < a.ratio * exp:
            gaps.append({"query": r.query, "page": r.page, "position": round(r.position, 1),
                         "impressions": int(r.impressions), "ctr": round(r.ctr, 4), "expected_ctr": round(exp, 4),
                         "missed_clicks": int(r.impressions * exp - r.clicks)})
    gaps.sort(key=lambda g: -g["missed_clicks"])
    label = "query" if any(g["query"] for g in gaps) else "page"
    md = [f"# CTR gaps (CTR below {a.ratio:.0%} of the site's own curve)", "",
          "Site curve: " + ", ".join(f"pos {b}: {pct(v)}" for b, v in curve.items() if b <= 10), "",
          md_table([label.title(), "Pos", "Impr", "CTR", "Expected", "Missed clicks"],
                   [[g[label] or g["page"], g["position"], g["impressions"], pct(g["ctr"]), pct(g["expected_ctr"]),
                     g["missed_clicks"]] for g in gaps[: a.top]]), "",
          "Fix: rewrite the title and meta description for the query intent; check snippet eligibility "
          "(dates, structured data) and whether an AI Overview or ads sit above the result.", "", GAPS]
    return {"mode": "ctr", "curve": curve, "gaps": gaps[: a.top], "count": len(gaps)}, "\n".join(md)


def mode_decay(recent: list[Row], previous: list[Row], label: str, a) -> tuple[dict, str]:
    prev = {getattr(r, label): r for r in previous}
    now = {getattr(r, label): r for r in recent}
    out = []
    for key, p in prev.items():
        if p.clicks < a.min_clicks:
            continue
        n = now.get(key) or Row(**{label: key})
        change = (n.clicks - p.clicks) / p.clicks
        if change > -a.drop:
            continue
        dpos = n.position - p.position if n.impressions else None
        dctr = (n.ctr - p.ctr) / p.ctr if p.ctr and n.impressions else None
        dimpr = (n.impressions - p.impressions) / p.impressions
        if n.clicks < 0.05 * p.clicks:
            diag, action = "traffic gone: check status, noindex, canonical, redirect", "investigate"
        elif dpos is not None and n.position > 20:
            diag, action = "no longer competitive (position > 20)", "consolidate"
        elif dpos is not None and dpos >= 2 and dctr is not None and dctr <= -0.2:
            diag, action = "rankings and CTR both down", "rewrite"
        elif dpos is not None and dpos >= 2:
            diag, action = f"rankings down {dpos:.1f} positions", "refresh"
        elif dctr is not None and dctr <= -0.2:
            diag, action = f"CTR down {dctr:+.0%} at a stable position", "rewrite title/meta"
        elif dimpr <= -0.2:
            diag, action = f"demand down: impressions {dimpr:+.0%}, position and CTR stable", "leave"
        else:
            diag, action = "mixed small declines", "refresh"
        out.append({label: key, "clicks_before": int(p.clicks), "clicks_now": int(n.clicks), "change": round(change, 3),
                    "position_before": round(p.position, 1), "position_now": round(n.position, 1) if n.impressions else None,
                    "diagnosis": diag, "action": action})
    out.sort(key=lambda o: o["clicks_now"] - o["clicks_before"])
    md = [f"# Content decay (clicks down >= {a.drop:.0%}, at least {a.min_clicks:g} clicks before)", "",
          md_table([label.title(), "Before", "Now", "Change", "Pos before", "Pos now", "Diagnosis", "Action"],
                   [[o[label], o["clicks_before"], o["clicks_now"], f"{o['change']:+.0%}", o["position_before"],
                     o["position_now"] if o["position_now"] is not None else "-", o["diagnosis"], o["action"]]
                    for o in out[: a.top]]), "",
          "Actions: refresh = update facts, add missing subtopics and first-hand evidence; rewrite title/meta = "
          "snippet only; rewrite = rework the page for current intent; consolidate = merge into a stronger page "
          "and 301; leave = demand fell, not the page; investigate = technical cause first.",
          "Compare equal-length periods, ideally year over year, so seasonality cancels out.", "", GAPS]
    return {"mode": "decay", "unit": label, "count": len(out), "pages": out[: a.top]}, "\n".join(md)


def mode_cannibal(rows: list[Row], a) -> tuple[dict, str]:
    brand = re.compile(a.brand, re.I) if a.brand else None
    groups: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        if r.impressions >= a.min_page_impressions and not (brand and brand.search(r.query)):
            groups[r.query].append(r)
    issues, overlap = [], 0
    for query, pages in groups.items():
        if len(pages) < 2:
            continue
        total_clicks = sum(p.clicks for p in pages)
        total_impr = sum(p.impressions for p in pages)
        if total_impr < a.min_impressions:
            continue
        keeper = max(pages, key=lambda p: (p.clicks, -p.position, p.impressions))
        share = keeper.clicks / total_clicks if total_clicks else keeper.impressions / total_impr
        if share >= a.dominance:
            overlap += 1
            continue
        others = sorted((p for p in pages if p is not keeper), key=lambda p: -p.impressions)
        close = [p for p in others if abs(p.position - keeper.position) <= 3 and p.clicks > 0]
        if close:
            fix = ("same intent? consolidate the competing page into the keeper and 301 it; different intent? "
                   "differentiate titles, H1s and internal anchors")
        else:
            fix = "point to the keeper: internal link from the weaker page with this query as anchor; de-target its title"
        issues.append({"query": query, "impressions": int(total_impr), "clicks": int(total_clicks),
                       "keeper": keeper.page, "keeper_share": round(share, 3),
                       "competing": [{"page": p.page, "position": round(p.position, 1), "clicks": int(p.clicks),
                                      "impressions": int(p.impressions)} for p in others],
                       "fix": fix})
    issues.sort(key=lambda i: -i["impressions"])
    md = [f"# Keyword cannibalisation", "",
          f"{len(issues)} queries where your pages split the traffic (keeper share < {a.dominance:.0%}); "
          f"{overlap} more queries show harmless overlap (one page already dominates).", ""]
    for i in issues[: a.top]:
        md += [f"## {i['query']}  ({i['impressions']} impressions, {i['clicks']} clicks)", "",
               f"Keeper: {i['keeper']} ({i['keeper_share']:.0%} of clicks)", "",
               md_table(["Competing page", "Pos", "Clicks", "Impr"],
                        [[c["page"], c["position"], c["clicks"], c["impressions"]] for c in i["competing"]]), "",
               f"Fix: {i['fix']}.", ""]
    md.append("Check intent in the live results before merging: two pages can rank for one query and serve "
              "different needs. " + GAPS)
    return {"mode": "cannibal", "count": len(issues), "overlap": overlap, "queries": issues[: a.top]}, "\n".join(md)


def parse_date(text: str) -> dt.date | None:
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def mode_update(rows: list[Row], a) -> tuple[dict, str]:
    try:
        day = dt.date.fromisoformat(a.date)
    except (TypeError, ValueError):
        raise InputError("update needs --date YYYY-MM-DD (the update's announced start)") from None
    before = (day - dt.timedelta(days=a.window), day)
    after = (day + dt.timedelta(days=a.rollout), day + dt.timedelta(days=a.rollout + a.window))
    sums: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    seen_before = seen_after = False
    for r in rows:
        d = parse_date(r.date)
        if d is None:
            continue
        if before[0] <= d < before[1]:
            sums[r.page][0] += r.clicks
            seen_before = True
        elif after[0] <= d < after[1]:
            sums[r.page][1] += r.clicks
            seen_after = True
    if not (seen_before and seen_after):
        raise InputError(f"no rows in both windows: before {before[0]}..{before[1] - dt.timedelta(days=1)}, "
                         f"after {after[0]}..{after[1] - dt.timedelta(days=1)}")
    out = []
    for page, (b, f) in sums.items():
        if max(b, f) < a.min_clicks:
            continue
        change = (f - b) / b if b else 1.0
        label = "winner" if change >= a.threshold else "loser" if change <= -a.threshold else "flat"
        out.append({"page": page, "before": int(b), "after": int(f), "change": round(change, 3), "label": label})
    out.sort(key=lambda o: o["after"] - o["before"])

    def section(page: str) -> str:
        path = urlsplit(page).path if "://" in page else page
        parts = [p for p in path.split("/") if p]
        return "/" + parts[0] + "/" if len(parts) > 1 else "/"

    losers = [o for o in out if o["label"] == "loser"]
    all_sections = defaultdict(int)
    loser_sections = defaultdict(int)
    for o in out:
        all_sections[section(o["page"])] += 1
    for o in losers:
        loser_sections[section(o["page"])] += 1
    pattern = []
    for sec, n in sorted(loser_sections.items(), key=lambda kv: -kv[1]):
        share_l, share_a = n / len(losers), all_sections[sec] / len(out)
        if n >= 3 and share_l >= 1.5 * share_a:
            pattern.append({"section": sec, "losers": n, "loser_share": round(share_l, 3), "site_share": round(share_a, 3)})
    counts = {k: sum(1 for o in out if o["label"] == k) for k in ("winner", "loser", "flat")}
    md = [f"# Core update: {a.date}", "",
          f"Before {before[0]}..{before[1] - dt.timedelta(days=1)} vs after {after[0]}..{after[1] - dt.timedelta(days=1)} "
          f"(skipping {a.rollout} rollout days). Winner/loser = clicks {a.threshold:+.0%} or more.", "",
          f"{counts['winner']} winners, {counts['loser']} losers, {counts['flat']} flat.", ""]
    if pattern:
        md += ["## Shared pattern among losers", "",
               md_table(["Section", "Losers", "Share of losers", "Share of site"],
                        [[p["section"], p["losers"], pct(p["loser_share"]), pct(p["site_share"])] for p in pattern]),
               "", "A section over-represented among losers points at a template or content type, not single pages.", ""]
    md += ["## Biggest losers", "", md_table(["Page", "Before", "After", "Change"],
           [[o["page"], o["before"], o["after"], f"{o['change']:+.0%}"] for o in losers[: a.top]]), "",
           "## Biggest winners", "", md_table(["Page", "Before", "After", "Change"],
           [[o["page"], o["before"], o["after"], f"{o['change']:+.0%}"] for o in reversed(out[-a.top:])
            if o["label"] == "winner"]), "",
           "Core updates reassess overall helpfulness; recovery comes from improving the losing content type, "
           "not from quick on-page tweaks, and may take until the next update. " + GAPS]
    return {"mode": "update", "date": a.date, "counts": counts, "pattern": pattern, "pages": out}, "\n".join(md)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["striking", "ctr", "decay", "cannibal", "update"])
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--map", action="append", metavar="canonical=Header")
    p.add_argument("--top", type=int, default=25)
    p.add_argument("--min-impressions", type=float, default=50)
    p.add_argument("--ratio", type=float, default=0.7, help="CTR below this share of expected is a gap")
    p.add_argument("--low", type=float, default=4)
    p.add_argument("--high", type=float, default=15)
    p.add_argument("--min-clicks", type=float, default=20)
    p.add_argument("--drop", type=float, default=0.2, help="decay: clicks drop that counts (0.2 = 20%%)")
    p.add_argument("--brand", help="cannibal: regex of brand queries to skip")
    p.add_argument("--dominance", type=float, default=0.8)
    p.add_argument("--min-page-impressions", type=float, default=10)
    p.add_argument("--date")
    p.add_argument("--window", type=int, default=28)
    p.add_argument("--rollout", type=int, default=14)
    p.add_argument("--threshold", type=float, default=0.2)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    overrides = parse_map(a.map)
    want = 2 if a.mode == "decay" else 1
    if len(a.files) != want:
        raise InputError(f"{a.mode} takes {want} file(s), got {len(a.files)}")

    if a.mode in ("striking", "ctr"):
        table_cols = read_table(a.files[0])[0].keys()
        cols = resolve(table_cols, ALIASES, overrides, (), str(a.files[0]))
        key = tuple(c for c in ("query", "page") if c in cols)
        if not key:
            raise InputError(f"{a.files[0]}: needs a query or page column; have: {', '.join(table_cols)}. "
                             "Use --map query=<header> or --map page=<header>.")
        rows = load(a.files[0], overrides, key, key)
        result, md = (mode_striking if a.mode == "striking" else mode_ctr)(rows, a)
    elif a.mode == "decay":
        cols = resolve(read_table(a.files[0])[0].keys(), ALIASES, overrides, (), str(a.files[0]))
        label = "page" if "page" in cols else "query"
        recent = load(a.files[0], overrides, (label,), (label,))
        previous = load(a.files[1], overrides, (label,), (label,))
        result, md = mode_decay(recent, previous, label, a)
    elif a.mode == "cannibal":
        rows = load(a.files[0], overrides, ("query", "page"), ("query", "page"))
        result, md = mode_cannibal(rows, a)
    else:
        rows = load(a.files[0], overrides, ("page", "date"), ("page", "date"))
        result, md = mode_update(rows, a)
    emit(result, a.json, md)
    return 0


if __name__ == "__main__":
    run(main)
