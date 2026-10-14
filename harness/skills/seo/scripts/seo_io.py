"""Shared input/output helpers for the seo data scripts (stdlib only).

Tables come from CSV/TSV exports (Search Console UI, API or BigQuery; Screaming Frog;
Bing Webmaster Tools; Clarity) whose headers differ by tool and language. Each script
declares canonical columns with aliases; headers are matched case- and punctuation-
insensitively, and `--map canonical=Header` overrides any match.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Iterable

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


class InputError(Exception):
    """Bad input: the script prints the message and exits 2."""


def norm_header(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.strip().lower())


def read_table(path: Path) -> list[dict[str, str]]:
    """Read a CSV, TSV or semicolon-separated file (UTF-8, BOM tolerated) into dict rows."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise InputError(f"{path}: file not found") from None
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-16")
        except (UnicodeDecodeError, UnicodeError):
            raise InputError(f"{path}: not UTF-8 or UTF-16 text") from None
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if not lines:
        raise InputError(f"{path}: empty file")
    first = lines[0]
    delim = max(("\t", ",", ";"), key=first.count)
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter=delim)
    rows = [{(k or "").strip(): (v or "").strip() for k, v in row.items() if k is not None} for row in reader]
    if not rows:
        raise InputError(f"{path}: header row but no data")
    return rows


def resolve(headers: Iterable[str], aliases: dict[str, list[str]], overrides: dict[str, str],
            required: Iterable[str], source: str) -> dict[str, str]:
    """Map canonical column -> actual header. Raises InputError naming what is missing."""
    by_norm = {norm_header(h): h for h in headers}
    found: dict[str, str] = {}
    for canon, names in aliases.items():
        if canon in overrides:
            want = overrides[canon]
            if want not in by_norm.values() and norm_header(want) not in by_norm:
                raise InputError(f"{source}: --map {canon}={want}: no such column")
            found[canon] = by_norm.get(norm_header(want), want)
            continue
        for name in [canon, *names]:
            if norm_header(name) in by_norm:
                found[canon] = by_norm[norm_header(name)]
                break
    missing = [c for c in required if c not in found]
    if missing:
        raise InputError(f"{source}: missing column(s) {', '.join(missing)}; have: {', '.join(headers)}. "
                         f"Use --map {missing[0]}=<header>.")
    return found


def parse_map(pairs: list[str] | None) -> dict[str, str]:
    out = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if not sep or not key or not value:
            raise InputError(f"--map {pair}: expected canonical=Header")
        out[key.strip()] = value.strip()
    return out


def num(text: str | None, default: float = 0.0) -> float:
    """Parse '1,234', '12.5%', '0.125', '' -> float. Percent strings become fractions."""
    if text is None:
        return default
    s = str(text).strip().replace("\u00a0", "").replace(" ", "")
    if not s or s in ("-", "--", "n/a", "N/A"):
        return default
    pct = s.endswith("%")
    s = s.rstrip("%")
    if s.count(",") and s.count("."):
        s = s.replace(",", "")
    elif s.count(",") == 1 and (len(s.split(",")[1]) != 3 or s.lstrip("-").startswith("0,")):
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        value = float(s)
    except ValueError:
        return default
    if math.isnan(value):
        return default
    return value / 100 if pct else value


def md_table(headers: list[str], rows: list[list]) -> str:
    def cell(v) -> str:
        if isinstance(v, float):
            v = f"{v:.3f}".rstrip("0").rstrip(".") if abs(v) < 1 else f"{v:,.1f}".rstrip("0").rstrip(".")
        return str(v).replace("|", "\\|").replace("\n", " ")
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(cell(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def emit(result: dict, as_json: bool, markdown: str) -> None:
    if as_json:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False, default=str)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(markdown.rstrip() + "\n")


def run(main) -> None:
    """Run main() -> int, turning InputError into exit 2 and keeping stdout UTF-8 on Windows."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    try:
        sys.exit(main())
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
