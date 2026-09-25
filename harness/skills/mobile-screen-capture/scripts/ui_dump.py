#!/usr/bin/env python3
"""List the tappable elements on an Android device's current screen.

Runs `uiautomator dump` on the device, reads the XML back through
`adb exec-out` (binary-safe, so OEM warnings or odd encodings don't corrupt
it), and prints each clickable node's label, bounds and tap centre. Read-only:
it never taps anything.

Usage:
  python ui_dump.py --serial <serial>
  python ui_dump.py --serial <serial> --all --xml-out uia.xml
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# No __pycache__ next to the harness copy (the harness refuses to ship it).
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_adb_screenshot import resolve_serial  # noqa: E402

DEVICE_XML = "/sdcard/harness-uia.xml"
BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def dump(adb: str, serial: str) -> bytes:
    run = subprocess.run(
        [adb, "-s", serial, "shell", "uiautomator", "dump", DEVICE_XML],
        capture_output=True, check=False,
    )
    if run.returncode != 0:
        raise RuntimeError(run.stderr.decode("utf-8", "replace").strip() or "uiautomator dump failed")
    cat = subprocess.run([adb, "-s", serial, "exec-out", "cat", DEVICE_XML], capture_output=True, check=False)
    if cat.returncode != 0:
        raise RuntimeError(cat.stderr.decode("utf-8", "replace").strip() or "could not read the dump")
    data = cat.stdout
    start = data.find(b"<?xml")
    if start < 0:
        start = data.find(b"<hierarchy")
    if start < 0:
        raise RuntimeError("the dump contains no <hierarchy> document (screen may be secure or animating)")
    return data[start:]


def label(node: ET.Element) -> str:
    for key in ("text", "content-desc", "resource-id"):
        value = (node.get(key) or "").strip()
        if value:
            return value if key != "resource-id" else "#" + value.split("/")[-1]
    return "(no label)"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--serial", help="ADB device serial; required when several devices are online")
    parser.add_argument("--adb", default="adb", help="ADB executable (default: adb on PATH)")
    parser.add_argument("--all", action="store_true", help="also list non-clickable nodes that have text")
    parser.add_argument("--xml-out", type=Path, help="save the raw hierarchy XML here")
    args = parser.parse_args()

    try:
        serial = resolve_serial(args.adb, args.serial)
        xml = dump(args.adb, serial)
        root = ET.fromstring(xml)
    except (OSError, RuntimeError, ET.ParseError) as exc:
        print(f"ui dump failed: {exc}", file=sys.stderr)
        return 1

    if args.xml_out:
        args.xml_out.parent.mkdir(parents=True, exist_ok=True)
        args.xml_out.write_bytes(xml)

    rows = 0
    print(f"{'#':>3}  {'centre':>11}  {'bounds':<24} label")
    for node in root.iter("node"):
        clickable = node.get("clickable") == "true"
        if not clickable and not (args.all and (node.get("text") or node.get("content-desc"))):
            continue
        m = BOUNDS.match(node.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        rows += 1
        mark = "" if clickable else "  (not clickable)"
        print(f"{rows:>3}  {(x1 + x2) // 2:>5},{(y1 + y2) // 2:<5}  {node.get('bounds', ''):<24} {label(node)}{mark}")
    print(f"\n{rows} element(s) on {serial}. Check a centre against a fresh screenshot before tapping it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
