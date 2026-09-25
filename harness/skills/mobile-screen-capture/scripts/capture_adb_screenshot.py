#!/usr/bin/env python3
"""Capture one Android screen as a PNG without decoding its bytes as text."""

from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def adb_devices(adb: str) -> list[str]:
    result = subprocess.run(
        [adb, "devices", "-l"], capture_output=True, check=False, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not list ADB devices")
    serials: list[str] = []
    for line in result.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[1] == "device":
            serials.append(fields[0])
    return serials


def resolve_serial(adb: str, requested: str | None) -> str:
    if requested:
        return requested
    serials = adb_devices(adb)
    if len(serials) == 1:
        return serials[0]
    if not serials:
        raise RuntimeError("No online ADB devices found. Connect a device and retry.")
    choices = ", ".join(serials)
    raise RuntimeError(
        f"Multiple ADB devices are online ({choices}); pass --serial to select one."
    )


def capture(adb: str, serial: str, output: Path, overwrite: bool) -> tuple[int, int, int]:
    if output.exists() and not overwrite:
        raise RuntimeError(f"Output already exists; choose another path or pass --overwrite: {output}")

    result = subprocess.run(
        [adb, "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or f"ADB screenshot failed with exit code {result.returncode}")

    png = result.stdout
    if len(png) < 24 or not png.startswith(PNG_SIGNATURE):
        raise RuntimeError("ADB output was not a valid PNG screenshot")

    width, height = struct.unpack(">II", png[16:24])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(png)
    return width, height, len(png)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", help="ADB device serial; required when multiple devices are online")
    parser.add_argument("--out", required=True, type=Path, help="Local output PNG path")
    parser.add_argument("--adb", default="adb", help="ADB executable (default: adb on PATH)")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file")
    args = parser.parse_args()

    try:
        serial = resolve_serial(args.adb, args.serial)
        width, height, size = capture(args.adb, serial, args.out, args.overwrite)
    except (OSError, RuntimeError) as exc:
        print(f"capture failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved {args.out} ({width}x{height}, {size} bytes) from {serial}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())