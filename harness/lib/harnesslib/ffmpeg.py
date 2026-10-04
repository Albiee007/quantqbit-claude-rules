"""ffmpeg and ffprobe helpers for the video renderer (bounded subprocesses, no shell).

ffmpeg is an external program like the browser: found on PATH (or $FFMPEG / --ffmpeg), never
bundled. Encoding goes through output profiles; each profile also says what its file must look
like, so the checks depend on what was asked for (an alpha or GIF profile has other rules than
H.264 for the web).

    with Encoder(ff, "h264-web", dest, fps=30) as enc:
        enc.write(jpeg_bytes)          # one encoded frame (JPEG or PNG) per call
    problems = check_profile(probe(ffprobe, dest), "h264-web", frames=90, size=(1080, 1920), fps=30)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .fsutil import OperationalError

TIMEOUT_S = 600  # one encode or probe; a hung ffmpeg is an operational failure

# RGB frames from the browser become BT.709 limited-range YUV explicitly: without the matrix,
# swscale converts with BT.601 and leaves the colour tags empty (M0: about 3 levels off).
BT709 = ("scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p,"
         "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv")

PROFILES = {
    "h264-web": {
        "label": "H.264 High, yuv420p, BT.709, fast start (web and social)",
        "args": ["-vf", BT709, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "suffix": ".mp4",
    },
    "h264-draft": {
        "label": "H.264 draft (previews only)",
        "args": ["-vf", BT709, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-profile:v", "high",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "suffix": ".mp4",
    },
}

INSTALL_ADVICE = {
    "win32": "install it (for example the gyan.dev 'essentials' build, or 'choco install ffmpeg') and put its bin "
             "folder on PATH, or pass --ffmpeg PATH",
    "darwin": "install it with 'brew install ffmpeg', or pass --ffmpeg PATH",
    "linux": "install it with your package manager (for example 'sudo apt-get install ffmpeg'), or pass --ffmpeg PATH",
}


def find_ffmpeg(explicit: str | None = None) -> tuple[str, str]:
    """(ffmpeg, ffprobe) paths, or OperationalError (exit 2) with install advice for this OS."""
    for given, what in ((explicit, "--ffmpeg"), (os.environ.get("FFMPEG"), "$FFMPEG")):
        if given and not Path(given).is_file() and not Path(given + ".exe").is_file():
            raise OperationalError(f"{what} {given}: no such file")
    candidates = [explicit, os.environ.get("FFMPEG"), shutil.which("ffmpeg")]
    for c in candidates:
        if c and not Path(c).is_file() and Path(c + ".exe").is_file():
            c += ".exe"
        if c and Path(c).is_file():
            ff = str(Path(c))
            name = Path(ff).name.replace("ffmpeg", "ffprobe")
            fp = os.environ.get("FFPROBE") or str(Path(ff).with_name(name))
            if not Path(fp).is_file():
                fp = shutil.which("ffprobe") or ""
            if not fp or not Path(fp).is_file():
                raise OperationalError(f"found ffmpeg at {ff} but no ffprobe next to it or on PATH")
            return ff, fp
    advice = INSTALL_ADVICE.get(sys.platform, INSTALL_ADVICE["linux"])
    raise OperationalError(f"ffmpeg was not found; {advice}")


def version(ff: str) -> str:
    try:
        out = subprocess.run([ff, "-hide_banner", "-version"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "ffmpeg (version not reported)"
    first = out.splitlines()[0] if out else "ffmpeg"
    return first.replace(" Copyright", "|").split("|")[0].strip()[:200]


def _run(argv: list[str], what: str, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    try:
        r = subprocess.run(argv, input=stdin, capture_output=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        raise OperationalError(f"{what}: ffmpeg did not finish within {TIMEOUT_S} s") from None
    except OSError as e:
        raise OperationalError(f"{what}: could not run {argv[0]}: {e}") from None
    if r.returncode != 0:
        tail = r.stderr.decode(errors="replace").strip().splitlines()[-3:]
        raise OperationalError(f"{what}: ffmpeg failed ({r.returncode}): {' | '.join(tail)}")
    return r


class Encoder:
    """Frames in (image2pipe), one video file out. Leaving the block finishes the file; an
    exception inside the block stops ffmpeg and removes the partial file."""

    def __init__(self, ff: str, profile: str, dest: Path, fps: int, codec: str = "mjpeg") -> None:
        if profile not in PROFILES:
            raise ValueError(f"unknown profile {profile}")
        self.dest = Path(dest)
        self.dest.parent.mkdir(parents=True, exist_ok=True)
        self.argv = [ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-vcodec", codec,
                     "-framerate", str(fps), "-i", "-", *PROFILES[profile]["args"], "-r", str(fps), str(self.dest)]
        self.frames = 0
        self.proc: subprocess.Popen | None = None
        self._err = None

    def __enter__(self) -> "Encoder":
        import tempfile
        self._err = tempfile.TemporaryFile()
        try:
            self.proc = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._err)
        except OSError as e:
            self._err.close()
            raise OperationalError(f"could not run ffmpeg ({self.argv[0]}): {e}") from None
        return self

    def write(self, frame: bytes) -> None:
        assert self.proc and self.proc.stdin
        try:
            self.proc.stdin.write(frame)
        except (BrokenPipeError, OSError):
            raise OperationalError(f"ffmpeg stopped while encoding {self.dest.name}: {self._stderr()}") from None
        self.frames += 1

    def _stderr(self) -> str:
        if self._err is None:
            return ""
        self._err.seek(0)
        return " | ".join(self._err.read().decode(errors="replace").strip().splitlines()[-3:])

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self.proc
        try:
            if exc_type is None:
                try:
                    self.proc.stdin.close()  # type: ignore[union-attr]
                except OSError:
                    pass  # ffmpeg already stopped; its exit code and stderr say why
                try:
                    rc = self.proc.wait(TIMEOUT_S)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    raise OperationalError(f"ffmpeg did not finish {self.dest.name} within {TIMEOUT_S} s") from None
                if rc != 0:
                    raise OperationalError(f"ffmpeg failed on {self.dest.name} ({rc}): {self._stderr()}")
            else:
                self.proc.kill()
                self.proc.wait()
                self.dest.unlink(missing_ok=True)
        finally:
            if self._err is not None:
                self._err.close()


def probe(fp: str, path: Path, count_frames: bool = True) -> dict:
    argv = [fp, "-v", "error", "-show_streams", "-show_format", "-of", "json"]
    if count_frames:
        argv.insert(3, "-count_frames")
    r = _run(argv + [str(path)], f"ffprobe {Path(path).name}")
    return json.loads(r.stdout.decode("utf-8", errors="replace"))


def faststart(path: Path) -> bool:
    """True when the 'moov' index comes before the media data (playback can start before download)."""
    with open(path, "rb") as f:
        head = f.read(1 << 20)
    moov, mdat = head.find(b"moov"), head.find(b"mdat")
    return moov != -1 and (mdat == -1 or moov < mdat)


def check_profile(info: dict, path: Path, profile: str, frames: int, size: tuple[int, int], fps: int) -> list[str]:
    """Problems with an encoded file against its profile (empty = PASS)."""
    v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if len(v) != 1:
        return [f"{len(v)} video streams, want 1"]
    s = v[0]
    out = []
    if profile in ("h264-web", "h264-draft"):
        if s.get("codec_name") != "h264":
            out.append(f"codec {s.get('codec_name')}, want h264")
        if profile == "h264-web" and s.get("profile") != "High":
            out.append(f"profile {s.get('profile')}, want High")
        if s.get("pix_fmt") != "yuv420p":
            out.append(f"pixel format {s.get('pix_fmt')}, want yuv420p")
        for key in ("color_space", "color_primaries", "color_transfer"):
            if s.get(key) != "bt709":
                out.append(f"{key} {s.get(key)}, want bt709")
        if not faststart(path):
            out.append("the moov index is not at the front (faststart)")
    if (s.get("width"), s.get("height")) != tuple(size):
        out.append(f"{s.get('width')}x{s.get('height')}, want {size[0]}x{size[1]}")
    if s.get("r_frame_rate") != f"{fps}/1":
        out.append(f"frame rate {s.get('r_frame_rate')}, want {fps}/1")
    got = s.get("nb_read_frames") or s.get("nb_frames")
    if str(got) != str(frames):
        out.append(f"{got} frames, want {frames}")
    return out


def gray_frames(ff: str, path: Path, width: int = 64) -> tuple[list[bytes], int, int]:
    """Every decoded frame as 8-bit luma at a small width (for the flash and freeze signals)."""
    r = _run([ff, "-v", "error", "-i", str(path), "-vf", f"scale={width}:-2:flags=area,format=gray",
              "-f", "rawvideo", "-"], f"decode {Path(path).name}")
    data = r.stdout
    # height follows the aspect ratio; recover it from the byte count and the frame count
    pr = _run([ff, "-v", "error", "-i", str(path), "-vf", f"scale={width}:-2:flags=area", "-frames:v", "1",
               "-f", "rawvideo", "-pix_fmt", "gray", "-"], f"decode {Path(path).name}").stdout
    info_h = len(pr) // width if pr else 0
    if not info_h:
        return [], width, 0
    size = width * info_h
    return [data[i:i + size] for i in range(0, len(data) - size + 1, size)], width, info_h
