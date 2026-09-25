#!/usr/bin/env python3
"""Remove byte-identical duplicate screenshots and write an INDEX.md skeleton.

Duplicates are found by SHA-256, never by visual similarity. Within a
duplicate group the kept copy is the one whose name marks an end state
(bottom, end, final, caught, last) if there is one, otherwise the
lowest-numbered file. The index groups files by area: the part of the name
between the leading number and the position word, e.g. "12-groups-bottom.png"
belongs to "groups".

Usage:
  python dedupe_index.py <folder> --dry-run
  python dedupe_index.py <folder> --device "Pixel 8 1080x2400" --write-index
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import sys
from collections import OrderedDict
from pathlib import Path

END_WORDS = re.compile(r"(bottom|end|final|caught|last|terminal)", re.I)
POSITION = re.compile(
    r"-(top|middle|mid|bottom|lower|upper|scroll|check|restored|final|more|end|start|\d+)$", re.I
)


def natural_key(p: Path) -> tuple:
    m = re.match(r"(\d+)", p.name)
    return (int(m.group(1)) if m else 10**9, p.name.lower())


def area_of(p: Path) -> str:
    stem = re.sub(r"^\d+[-_]?", "", p.stem)
    while True:
        new = POSITION.sub("", stem)
        if new == stem:
            break
        stem = new
    return stem or "misc"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="report duplicates without deleting")
    parser.add_argument("--device", default="<device model> <W>x<H>", help="device line for the index")
    parser.add_argument("--write-index", action="store_true", help="write INDEX.md (refuses to overwrite)")
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"not a folder: {args.folder}", file=sys.stderr)
        return 2
    files = sorted(args.folder.glob("*.png"), key=natural_key)
    groups: "OrderedDict[str, list[Path]]" = OrderedDict()
    for f in files:
        groups.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), []).append(f)

    removed = 0
    for same in groups.values():
        if len(same) < 2:
            continue
        keep = next((f for f in same if END_WORDS.search(f.stem)), same[0])
        for f in same:
            if f is keep:
                continue
            print(f"{'would remove' if args.dry_run else 'removed'} {f.name} (same bytes as {keep.name})")
            if not args.dry_run:
                f.unlink()
            removed += 1
    remaining = sorted(args.folder.glob("*.png"), key=natural_key) if not args.dry_run else files
    print(f"{removed} duplicate(s) {'found' if args.dry_run else 'removed'}; {len(files) - removed} screenshot(s) kept")

    if args.write_index:
        index = args.folder / "INDEX.md"
        if index.exists():
            print(f"{index} exists; not overwriting", file=sys.stderr)
            return 1
        areas: "OrderedDict[str, list[str]]" = OrderedDict()
        for f in remaining:
            areas.setdefault(area_of(f), []).append(f.name)
        lines = [
            "# Mobile app screenshots", "",
            f"**Captured:** {dt.date.today():%d %B %Y}  ",
            f"**Device:** {args.device}", "",
            "Long feeds and lists are saved as successive scroll captures through their final visible entries. "
            "Exact duplicate files were removed; end-state captures were kept. "
            "Forms were inspected without submitting and settings were left unchanged. <!-- edit if not true -->", "",
        ]
        for area, names in areas.items():
            title = area.replace("-", " ").replace("_", " ").capitalize()
            lines.append(f"## {title}")
            lines.append("")
            lines.append("- " + ", ".join(f"`{n}`" for n in names))
            lines.append("")
        index.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"wrote {index}. Add the scroll endpoints and unsubmitted forms, and no personal data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
