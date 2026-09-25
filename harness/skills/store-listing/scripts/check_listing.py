#!/usr/bin/env python3
"""Check a store listing file against store limits and claim guardrails.

LISTING.md holds one fenced ```text block per field, each preceded by a marker:
  <!-- field: play.title | max 30 -->
  <!-- field: ios.keywords | max 100 bytes -->
Field names starting with "ios." or "play." are platform fields.

Checks:
  * every field is within its limit (characters, or bytes when marked)
  * ios.keywords: comma-separated, no spaces, no word already in ios.name/ios.subtitle
  * common banned claims (fixed prices, "free forever", "#1", "best", "guaranteed")
  * project guardrails from listing-guardrails.txt next to LISTING.md (or --guardrails):
      all: <regex>     banned in every field
      ios: <regex>     banned in ios.* fields (e.g. Android-only features)
      play: <regex>    banned in play.* fields
    Lines starting with # are comments. Patterns are case-insensitive.

Usage:
  python check_listing.py path/to/LISTING.md [--guardrails path] [--allow-prices]
Exit: 0 clean, 1 problems, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FIELD = re.compile(r"<!-- field: (\S+) \| max (\d+)( bytes)? -->\s*```text\n(.*?)\n```", re.S)
COMMON = [
    ("all", r"free forever"),
    ("all", r"(^|\s)#1(\s|$)|number one|no\. ?1\b"),
    ("all", r"\bbest\b.*\bapp\b|\bthe best\b"),
    ("all", r"\bguarantee(d|s)?\b"),
    ("all", r"\b100% (secure|safe|accurate)\b"),
]
PRICES = ("all", r"[$€£₹¥]\s?\d|\b\d+(\.\d+)?\s?(usd|eur|inr|gbp)\b|/month\b|/year\b")


def load_guardrails(path: Path) -> list[tuple[str, str]]:
    rules = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        scope, _, pattern = line.partition(":")
        scope, pattern = scope.strip().lower(), pattern.strip()
        if scope not in ("all", "ios", "play") or not pattern:
            raise ValueError(f"{path}:{n}: expected 'all|ios|play: <regex>'")
        re.compile(pattern)
        rules.append((scope, pattern))
    return rules


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("listing", type=Path)
    parser.add_argument("--guardrails", type=Path, help="default: listing-guardrails.txt next to the listing")
    parser.add_argument("--allow-prices", action="store_true", help="do not flag prices (only if prices are verified per country)")
    args = parser.parse_args()
    if not args.listing.is_file():
        print(f"not found: {args.listing}", file=sys.stderr)
        return 2

    text = args.listing.read_text(encoding="utf-8")
    fields = FIELD.findall(text)
    if not fields:
        print("no <!-- field: … --> blocks found; see templates/LISTING.template.txt", file=sys.stderr)
        return 2

    problems: list[str] = []
    values: dict[str, str] = {}
    for name, limit, in_bytes, body in fields:
        size = len(body.encode("utf-8")) if in_bytes else len(body)
        values[name] = body
        over = size > int(limit)
        if over:
            problems.append(f"{name} is {size}/{limit}{' bytes' if in_bytes else ''}")
        print(f"{'OVER' if over else 'OK  '} {name:20} {size:>5} / {limit}{' bytes' if in_bytes else ''}")

    kw = values.get("ios.keywords")
    if kw is not None:
        if re.search(r",\s|\s,", kw):
            problems.append("ios.keywords: remove spaces around commas (they waste bytes)")
        taken = set(re.findall(r"[a-z0-9]+", (values.get("ios.name", "") + " " + values.get("ios.subtitle", "")).lower()))
        dupes = [k for k in kw.lower().split(",") if k.strip() in taken]
        if dupes:
            problems.append(f"ios.keywords repeats words from the name/subtitle (already indexed): {dupes}")
        seen, repeated = set(), set()
        for k in kw.lower().split(","):
            (repeated if k in seen else seen).add(k)
        if repeated:
            problems.append(f"ios.keywords has repeated keywords: {sorted(repeated)}")

    rules = list(COMMON) + ([] if args.allow_prices else [PRICES])
    guard = args.guardrails or args.listing.with_name("listing-guardrails.txt")
    if guard.is_file():
        try:
            rules += load_guardrails(guard)
        except (ValueError, re.error) as exc:
            print(f"bad guardrails file: {exc}", file=sys.stderr)
            return 2
        print(f"\nguardrails: {guard.name} ({len(rules) - len(COMMON)} project rule(s))")
    elif args.guardrails:
        print(f"guardrails file not found: {guard}", file=sys.stderr)
        return 2

    for name, body in values.items():
        platform = name.split(".", 1)[0]
        for scope, pattern in rules:
            if scope != "all" and scope != platform:
                continue
            m = re.search(pattern, body, re.I | re.M)
            if m:
                problems.append(f"{name}: banned claim /{pattern}/ matched {m.group(0)!r}")

    print(f"\n{len(fields)} field(s) checked")
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("all fields within limits; no guardrail hits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
