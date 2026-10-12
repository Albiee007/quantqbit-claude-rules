"""HyperFrames (HeyGen, Apache-2.0) as an optional second frame renderer for brand-video.

`render_video.py render <id> --engine hyperframes` exports the composition as a HyperFrames
project (index.html plus its fonts, assets and scripts, without our seek runtime: HyperFrames
brings its own window.__hf), asks the pinned HyperFrames CLI for a PNG sequence, and feeds those
frames to the same encoder, profiles and checks as our own engine. So the file format, colour
handling, sound, manifest and approvals are the same; only who drew the frames differs, and a
parity signal compares HyperFrames' frames with ours at every scene's still frame.

It needs Node.js 22 or later and the CLI: HYPERFRAMES_BIN (or --hyperframes) naming an installed
`hyperframes` executable, or else `npx --yes hyperframes@<PIN>` (which downloads it). Render
telemetry, on by default in HyperFrames, is turned off. The composition must use only what
HyperFrames' runtime seeks: Web Animations and CSS keyframes. Recording and custom scenes rely on
our runtime and are refused.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .fsutil import InputError, OperationalError
from .providers import run_bounded

PIN = "0.8.119"  # checked in the M0 spike: WAAPI composition time, CSS keyframes clip-relative
TIMEOUT_S = 1800
UNSUPPORTED = ("recording", "custom")


def find(explicit: str | None = None, node: str | None = None) -> tuple[list[str], dict]:
    """(argv prefix, environment) to run the CLI. Raises OperationalError with what to install."""
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1")
    if node:
        env["PATH"] = str(Path(node).parent) + os.pathsep + env.get("PATH", "")
    node_bin = node or shutil.which("node", path=env.get("PATH"))
    if not node_bin:
        raise OperationalError("the HyperFrames engine needs Node.js 22 or later on PATH (or --node PATH)")
    try:
        v = subprocess.run([node_bin, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        raise OperationalError(f"could not run {node_bin}: {e}") from None
    m = re.match(r"v(\d+)", v)
    if not m or int(m[1]) < 22:
        raise OperationalError(f"the HyperFrames engine needs Node.js 22 or later; {node_bin} is {v or 'unknown'}")
    given = explicit or os.environ.get("HYPERFRAMES_BIN")
    if given:
        if not Path(given).is_file():
            raise OperationalError(f"HyperFrames CLI {given}: no such file")
        return [given], env
    npx = shutil.which("npx", path=env.get("PATH"))
    if not npx:
        raise OperationalError("the HyperFrames engine needs npx (it comes with Node.js), or HYPERFRAMES_BIN")
    return [npx, "--yes", f"hyperframes@{PIN}"], env


def version(prefix: list[str], env: dict) -> str:
    try:
        _, raw, _ = run_bounded([*prefix, "--version"], None, 300, env)
    except (OSError, subprocess.TimeoutExpired):
        return f"hyperframes {PIN} (version not reported)"
    m = re.search(r"\d+\.\d+\.\d+", raw.decode(errors="replace"))
    return f"hyperframes {m[0] if m else PIN}"


def export(build_dir: Path, dest: Path) -> Path:
    """The composition as a HyperFrames project in dest: video.html becomes index.html without our
    runtime's script tag (HyperFrames injects its own window.__hf)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(build_dir, dest)
    page = dest / "video.html"
    html = page.read_text(encoding="utf-8")
    tag = '<script src="timeline.js"></script>'
    if html.count(tag) != 1:
        raise OperationalError("the composition page no longer loads timeline.js as expected; the HyperFrames export "
                               "can't remove our runtime (update harnesslib/hyperframes.py)")
    html = html.replace(tag + "\n", "", 1).replace(tag, "", 1)
    (dest / "index.html").write_text(html, encoding="utf-8")
    page.unlink()
    (dest / "timeline.js").unlink(missing_ok=True)
    return dest


def render_png(prefix: list[str], env: dict, project: Path, out: Path, fps: int) -> list[Path]:
    """Every frame as an RGBA PNG, in order."""
    if out.exists():
        shutil.rmtree(out)
    argv = [*prefix, "render", str(project), "--format", "png-sequence", "-o", str(out), "--fps", str(fps),
            "--workers", "1", "--quiet", "--strict"]
    try:
        rc, so, se = run_bounded(argv, project, TIMEOUT_S, env)
    except subprocess.TimeoutExpired:
        raise OperationalError(f"HyperFrames did not finish within {TIMEOUT_S} s (stopped)") from None
    except OSError as e:
        raise OperationalError(f"could not run HyperFrames ({argv[0]}): {e}") from None
    if rc != 0:
        tail = " | ".join((se or so).decode(errors="replace").strip().splitlines()[-4:])
        raise OperationalError(f"HyperFrames failed ({rc}): {tail}")
    frames = frame_files(out)
    if not frames:
        raise OperationalError(f"HyperFrames wrote no PNG frames to {out}")
    return frames


def frame_files(folder: Path) -> list[Path]:
    """The PNG frames in folder, in frame order: by the last number in each name (frame_9 before
    frame_10), only the folder itself."""
    def key(f: Path) -> tuple[int, str]:
        nums = re.findall(r"\d+", f.stem)
        return (int(nums[-1]) if nums else -1, f.name)
    return sorted((f for f in Path(folder).glob("*.png") if f.is_file()), key=key)


def refuse(scenes: list) -> None:
    bad = [s.id for s in scenes if s.template in UNSUPPORTED]
    if bad:
        raise InputError(f"the HyperFrames engine draws Web Animations and CSS keyframes only; scene(s) "
                         f"{', '.join(bad)} use recording or custom templates, which need our engine (--engine ours)")
