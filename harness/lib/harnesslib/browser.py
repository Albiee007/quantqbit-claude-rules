"""Headless Chrome/Chromium/Edge helpers shared by the media renderers (bounded subprocesses)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .fsutil import OperationalError

TIMEOUT_S = 120  # one page render; a hung browser is an operational failure, not a wait forever


def find_chrome(explicit: str | None) -> str:
    candidates = [explicit, os.environ.get("CHROME")]
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            candidates += [str(Path(base) / "Google/Chrome/Application/chrome.exe"),
                           str(Path(base) / "Microsoft/Edge/Application/msedge.exe")]
    candidates += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                   "/Applications/Chromium.app/Contents/MacOS/Chromium",
                   "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    candidates += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                                             "microsoft-edge", "chrome")]
    for c in candidates:
        if c and Path(c).is_file():
            return c
    raise OperationalError("Chrome/Chromium/Edge not found; pass --chrome PATH or set CHROME")


def version(chrome: str) -> str:
    """'<name> <version>' when the binary reports it (Windows builds often don't), else the file name."""
    try:
        r = subprocess.run([chrome, "--version"], capture_output=True, timeout=20)
        out = r.stdout.decode(errors="replace").strip()
        if re.search(r"\d+\.\d+", out):
            return out[:200]
    except (OSError, subprocess.TimeoutExpired):
        pass
    m = re.search(r"(\d+\.\d+\.\d+\.\d+)", str(Path(chrome).resolve()))
    return f"{Path(chrome).name} {m.group(1) if m else '(version not reported)'}"[:200]


def cmd(chrome: str, profile: str, size: tuple[int, int], budget_ms: int = 8000, transparent: bool = False) -> list[str]:
    c = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1"]
    if transparent:
        c.append("--default-background-color=00000000")
    return c + [f"--user-data-dir={profile}", "--allow-file-access-from-files", "--no-first-run",
                f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={budget_ms}"]


def screenshot(chrome: str, url: str, size: tuple[int, int], dest: Path, budget_ms: int = 8000,
               transparent: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(cmd(chrome, str(Path(tmp) / "profile"), size, budget_ms, transparent)
                               + [f"--screenshot={dest}", url], capture_output=True, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise OperationalError(f"{Path(dest).name}: the browser did not finish within {TIMEOUT_S} s") from None
    if r.returncode != 0 or not Path(dest).is_file():
        raise OperationalError(f"{Path(dest).name}: Chrome failed ({r.returncode}): "
                               f"{r.stderr.decode(errors='replace')[-300:]}")


def dump_dom(chrome: str, url: str, size: tuple[int, int], budget_ms: int = 8000) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(cmd(chrome, str(Path(tmp) / "profile"), size, budget_ms) + ["--dump-dom", url],
                               capture_output=True, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise OperationalError(f"--dump-dom did not finish within {TIMEOUT_S} s") from None
    if r.returncode != 0:
        raise OperationalError(f"Chrome --dump-dom failed ({r.returncode}): {r.stderr.decode(errors='replace')[-300:]}")
    return r.stdout.decode("utf-8", errors="replace")
