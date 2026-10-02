"""Headless Chrome/Chromium/Edge helpers shared by the media renderers (bounded subprocesses)."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path

from .fsutil import OperationalError

TIMEOUT_S = 120  # one page render; a hung browser is an operational failure, not a wait forever


def _kill_group(proc: subprocess.Popen) -> None:
    """Stop the browser and any helper it started (renderer, GPU, crash handler)."""
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _run(argv: list[str], timeout: float) -> tuple[int, bytes, bytes]:
    """Run the browser with a hard time limit; returns (exit code, stdout, stderr).

    Output goes to temporary files, not pipes: browser helpers inherit the descriptors and can
    outlive the browser, and waiting for a pipe to close would then never end, even after a
    timeout. The browser gets its own process group so a timeout stops the helpers too, and any
    still running after a normal exit are stopped as well."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        extra = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
                 else {"start_new_session": True})
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, **extra)
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            proc.kill()
            proc.wait()
            raise
        if os.name != "nt":
            _kill_group(proc)
        out.seek(0)
        err.seek(0)
        return rc, out.read(), err.read()


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
        out = _run([chrome, "--version"], 20)[1].decode(errors="replace").strip()
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
    # --use-mock-keychain / --password-store=basic: headless Chrome on macOS can otherwise block on
    # keychain access (CI runners, locked sessions). They don't change what is rendered.
    return c + [f"--user-data-dir={profile}", "--allow-file-access-from-files", "--no-first-run",
                "--no-default-browser-check", "--use-mock-keychain", "--password-store=basic",
                f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={budget_ms}"]


def screenshot(chrome: str, url: str, size: tuple[int, int], dest: Path, budget_ms: int = 8000,
               transparent: bool = False) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            rc, _, err = _run(cmd(chrome, str(Path(tmp) / "profile"), size, budget_ms, transparent)
                              + [f"--screenshot={dest}", url], TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise OperationalError(f"{Path(dest).name}: the browser did not finish within {TIMEOUT_S} s") from None
    if rc != 0 or not Path(dest).is_file():
        raise OperationalError(f"{Path(dest).name}: Chrome failed ({rc}): {err.decode(errors='replace')[-300:]}")


def dump_dom(chrome: str, url: str, size: tuple[int, int], budget_ms: int = 8000) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            rc, out, err = _run(cmd(chrome, str(Path(tmp) / "profile"), size, budget_ms) + ["--dump-dom", url],
                                TIMEOUT_S)
        except subprocess.TimeoutExpired:
            raise OperationalError(f"--dump-dom did not finish within {TIMEOUT_S} s") from None
    if rc != 0:
        raise OperationalError(f"Chrome --dump-dom failed ({rc}): {err.decode(errors='replace')[-300:]}")
    return out.decode("utf-8", errors="replace")
