#!/usr/bin/env python3
"""Audit how search and AI bots reach the site, from server/CDN logs or a bot report.

Inputs (several files allowed; .gz is read transparently):
  * combined/common access logs (nginx, Apache, Caddy in common format)
  * W3C extended logs with a #Fields: header (CloudFront standard logs, IIS)
  * JSON lines from CDNs (Cloudflare Logpush, Fastly, Vercel, generic): user agent, path,
    status and client IP are found through field aliases
  * a CSV report (Microsoft Clarity Bot Activity export or any table) with a user agent or
    bot name column, optional path, status and a request-count column. The Clarity column
    names are matched by alias and should be confirmed against a real export.

Bots are classified with references/ai-bots.json (search, training, user-initiated). Each
bot gets one status and one fix:
  blocked       >= 50% of requests answered 401/403 (WAF/CDN rules)
  throttled     >= 10% answered 429
  erroring      >= 5% answered 5xx
  robots        requests to paths its robots.txt group disallows (needs --robots); a bot
                that honours robots.txt doing this is often an impostor using its name
  over-scraping >= --scrape-ratio requests per unique path (and >= 100 requests)
  healthy       none of the above
A user-agent string proves nothing. With --ranges TOKEN=FILE (the operator's published
IP ranges JSON, or a plain list of CIDRs) requests are checked against those ranges;
otherwise identity is reported as unverified. Nothing is fetched from the network.

Usage:
  python bot_log_audit.py access.log [more.log.gz] [--robots robots.txt]
      [--ranges Googlebot=googlebot.json --ranges GPTBot=gptbot.json] [--json]
Exit: 0 report written, 2 bad input.
"""

from __future__ import annotations

import argparse
import gzip
import ipaddress
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from seo_io import InputError, emit, md_table, num, pct, read_table, resolve, run

BOTS_FILE = Path(__file__).resolve().parent.parent / "references" / "ai-bots.json"
COMBINED = re.compile(r'^(\S+) \S+ \S+ \[[^\]]*\] "(?:\S+) (\S+)[^"]*" (\d{3}) \S+(?: "[^"]*" "([^"]*)")?')
JSON_KEYS = {
    "ua": ["ClientRequestUserAgent", "user_agent", "userAgent", "http_user_agent", "cs(User-Agent)", "ua",
           "request_user_agent", "useragent"],
    "path": ["ClientRequestURI", "ClientRequestPath", "path", "request_uri", "url", "uri", "cs-uri-stem", "request_path"],
    "status": ["EdgeResponseStatus", "status", "status_code", "sc-status", "OriginResponseStatus", "response_status"],
    "ip": ["ClientIP", "client_ip", "remote_addr", "ip", "c-ip", "clientIp", "x-forwarded-for"],
}
CSV_ALIASES = {"ua": ["user agent", "useragent", "bot", "bot name", "crawler", "agent"],
               "path": ["url", "page", "path", "request path"], "status": ["status code", "response code", "http status"],
               "ip": ["client ip", "ip address"], "count": ["requests", "request count", "hits", "ai bot requests", "count"]}


def load_bots() -> list[dict]:
    try:
        data = json.loads(BOTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"cannot read {BOTS_FILE}: {exc}") from None
    bots = [b for b in data["bots"] if b["purpose"] != "control"]
    return sorted(bots, key=lambda b: -len(b["token"]))


def open_text(path: Path):
    if not path.exists():
        raise InputError(f"{path}: file not found")
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8-sig", errors="replace")


def records(path: Path):
    """Yield (ua, path, status, ip, count) from any supported log or report format."""
    if path.suffix.lower() in (".csv", ".tsv"):
        table = read_table(path)
        cols = resolve(table[0].keys(), CSV_ALIASES, {}, ("ua",), str(path))
        for row in table:
            yield (row.get(cols["ua"], ""), row.get(cols.get("path", ""), "") or "", int(num(row.get(cols.get("status", ""), ""))),
                   row.get(cols.get("ip", ""), "") or "", int(num(row.get(cols.get("count", ""), "1"), 1)) if "count" in cols else 1)
        return
    fields: list[str] | None = None
    with open_text(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("#Fields:"):
                fields = line[8:].split()
                continue
            if line.startswith("#"):
                continue
            if line.lstrip().startswith("{"):
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                get = lambda k: next((str(obj[x]) for x in JSON_KEYS[k] if x in obj and obj[x] is not None), "")  # noqa: E731
                yield get("ua"), get("path"), int(num(get("status"))), get("ip").split(",")[0].strip(), 1
                continue
            if fields:
                parts = line.split("\t") if "\t" in line else line.split()
                rec = dict(zip(fields, parts))
                ua = unquote(unquote(rec.get("cs(User-Agent)", ""))).replace("+", " ")
                yield ua, rec.get("cs-uri-stem", ""), int(num(rec.get("sc-status", ""))), rec.get("c-ip", ""), 1
                continue
            m = COMBINED.match(line)
            if m:
                yield m.group(4) or "", m.group(2), int(m.group(3)), m.group(1), 1


def parse_robots(path: Path) -> dict[str, list[tuple[bool, str]]]:
    groups: dict[str, list] = {}
    agents: list[str] = []
    in_rules = False
    for raw in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, value = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                agents, in_rules = [], False
            agents.append(value.lower())
            groups.setdefault(value.lower(), [])
        elif key in ("allow", "disallow") and agents:
            in_rules = True
            if value or key == "allow":
                for ag in agents:
                    groups[ag].append((key == "allow", value))
    return groups


def rule_match(pattern: str, path: str) -> bool:
    if not pattern:
        return False
    rx = re.escape(pattern).replace(r"\*", ".*")
    if rx.endswith(r"\$"):
        rx = rx[:-2] + "$"
    return re.match(rx, path) is not None


def disallowed(groups: dict, token: str, path: str) -> bool:
    rules = groups.get(token.lower(), groups.get("*", []))
    best_len, allowed = -1, True
    for allow, pattern in rules:
        if rule_match(pattern, path) and (len(pattern) > best_len or (len(pattern) == best_len and allow)):
            best_len, allowed = len(pattern), allow
    return not allowed


def load_ranges(spec: str) -> tuple[str, list]:
    token, sep, file = spec.partition("=")
    if not sep:
        raise InputError(f"--ranges {spec}: expected TOKEN=FILE")
    try:
        data = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InputError(f"--ranges {spec}: {exc}") from None
    cidrs = []
    items = data.get("prefixes", []) if isinstance(data, dict) else data
    for item in items:
        value = item if isinstance(item, str) else item.get("ipv4Prefix") or item.get("ipv6Prefix")
        if value:
            cidrs.append(ipaddress.ip_network(value, strict=False))
    if not cidrs:
        raise InputError(f"--ranges {spec}: no prefixes found")
    return token.lower(), cidrs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("logs", nargs="+", type=Path)
    p.add_argument("--robots", type=Path)
    p.add_argument("--ranges", action="append", default=[], metavar="TOKEN=FILE")
    p.add_argument("--scrape-ratio", type=float, default=20)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    bots = load_bots()
    robots = parse_robots(a.robots) if a.robots else None
    ranges = dict(load_ranges(s) for s in a.ranges)

    stats: dict[str, dict] = {}
    other: Counter = Counter()
    total = 0
    for path in a.logs:
        for ua, req, status, ip, count in records(path):
            total += count
            low = ua.lower()
            bot = next((b for b in bots if b["token"].lower() in low or b["operator"].lower() + " " + b["token"].lower() == low), None)
            if not bot:
                if re.search(r"bot|crawl|spider|slurp|fetch", low):
                    other[ua[:80]] += count
                continue
            s = stats.setdefault(bot["token"], {"bot": bot, "requests": 0, "paths": set(), "codes": Counter(),
                                               "disallowed": 0, "verified": 0, "checked": 0})
            s["requests"] += count
            pth = urlsplit(req).path if "://" in req else req.split("?")[0]
            if pth:
                s["paths"].add(pth)
            s["codes"][status] += count
            if robots is not None and pth and disallowed(robots, bot["token"], pth):
                s["disallowed"] += count
            cidrs = ranges.get(bot["token"].lower())
            if cidrs and ip:
                try:
                    addr = ipaddress.ip_address(ip)
                except ValueError:
                    continue
                s["checked"] += count
                if any(addr in c for c in cidrs):
                    s["verified"] += count
    if total == 0:
        raise InputError("no log lines recognised; supported: combined, W3C #Fields, JSON lines, CSV report")

    rows = []
    for token, s in sorted(stats.items(), key=lambda kv: -kv[1]["requests"]):
        b, n, codes = s["bot"], s["requests"], s["codes"]
        share = lambda pred: sum(c for k, c in codes.items() if pred(k)) / n  # noqa: E731
        blocked, throttled, erroring = share(lambda k: k in (401, 403)), share(lambda k: k == 429), share(lambda k: k >= 500)
        ratio = n / max(1, len(s["paths"]))
        if blocked >= 0.5:
            status = "blocked"
            fix = {"search": f"allowlist verified {token} in CDN/WAF bot rules: you are missing from {b['operator']} answers",
                   "training": "intentional? blocking training bots is a business decision: record it in the robots policy",
                   "user": f"people asking {b['operator']} about your pages get nothing: allow it if visibility matters"}[b["purpose"]]
        elif throttled >= 0.1:
            status, fix = "throttled", f"raise the rate limit for verified {token}, or serve cached pages to it"
        elif erroring >= 0.05:
            status, fix = "erroring", "fix the 5xx responses on its top paths (timeouts, origin errors)"
        elif s["disallowed"] and b["robots"] == "yes":
            status, fix = "robots", ("requests to disallowed paths: verify the IPs (impostors reuse this name); "
                                     "if verified, check the robots.txt group it reads")
        elif n >= 100 and ratio >= a.scrape_ratio:
            status, fix = "over-scraping", "cache aggressively and rate-limit; check for crawl traps (facets, calendars)"
        else:
            status, fix = "healthy", "none"
        verified = (f"{s['verified'] / s['checked']:.0%} of {s['checked']}" if s["checked"] else "unverified")
        rows.append({"token": token, "operator": b["operator"], "purpose": b["purpose"], "requests": n,
                     "unique_paths": len(s["paths"]), "ok_2xx": round(share(lambda k: 200 <= k < 300), 3),
                     "blocked": round(blocked, 3), "throttled": round(throttled, 3), "errors_5xx": round(erroring, 3),
                     "disallowed_hits": s["disallowed"], "identity": verified, "status": status, "fix": fix})
    unseen = [b["token"] for b in bots if b["purpose"] == "search" and b["token"] not in stats]
    md = [f"# Bot access audit", "", f"{total:,} requests read; {sum(r['requests'] for r in rows):,} from known search/AI bots.", "",
          md_table(["Bot", "Operator", "Purpose", "Requests", "Paths", "2xx", "401/403", "429", "5xx", "Disallowed", "Identity",
                    "Status"],
                   [[r["token"], r["operator"], r["purpose"], r["requests"], r["unique_paths"], pct(r["ok_2xx"]), pct(r["blocked"]),
                     pct(r["throttled"]), pct(r["errors_5xx"]), r["disallowed_hits"] if robots is not None else "-",
                     r["identity"], r["status"]] for r in rows]), "", "## Fixes", ""]
    md += [f"- **{r['token']}** ({r['status']}): {r['fix']}." for r in rows if r["status"] != "healthy"] or ["- None: every bot seen is healthy."]
    if unseen:
        md += ["", f"Search bots never seen: {', '.join(unseen)}. If these logs cover all traffic, check robots.txt and "
               "the CDN/WAF bot settings."]
    if other:
        md += ["", "Other bot-like user agents (not classified): " + "; ".join(f"{ua} ({c})" for ua, c in other.most_common(5))]
    md += ["", "Data gaps: logs cover only the hosts and period supplied; CDN-cached hits are missing from origin logs; "
           "user-agent strings can be faked, so treat unverified identities with care."]
    emit({"requests": total, "bots": rows, "unseen_search_bots": unseen, "other": dict(other.most_common(20))}, a.json, "\n".join(md))
    return 0


if __name__ == "__main__":
    run(main)
