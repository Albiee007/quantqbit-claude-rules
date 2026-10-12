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
import math
import os
import re
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
        # half size can be odd (1200x630 -> 600x315); 4:2:0 needs even sides
        "args": ["-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2," + BT709, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-profile:v", "high",
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "suffix": ".mp4",
    },
    # App Store app previews: H.264 at 30 fps, 15-30 s, at most 500 MB, with a stereo AAC track
    # (silent when the piece has no audio). Apple suggests 10-12 Mb/s, so the rate is capped there.
    "app-preview": {
        "label": "App Store preview: H.264 High, yuv420p, BT.709, 30 fps, 15-30 s, AAC stereo, at most 500 MB",
        "args": ["-vf", BT709, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-maxrate", "12M", "-bufsize", "24M",
                 "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        "suffix": ".mp4",
        "audio": "required", "fps": 30, "seconds": (15.0, 30.0), "maxBytes": 500_000_000,
    },
    # Transparent overlays (lower thirds, stingers) for an editor: frames arrive as PNG with alpha.
    "alpha-webm": {
        "label": "VP9 with alpha (yuva420p) in WebM, for editors and the web",
        "args": ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "24", "-deadline", "good",
                 "-auto-alt-ref", "0", "-row-mt", "0"],
        "suffix": ".webm", "frames": "png", "alpha": True,
    },
    "alpha-prores": {
        "label": "ProRes 4444 with alpha (yuva444p10le) in QuickTime, for editors",
        "args": ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"],
        "suffix": ".mov", "frames": "png", "alpha": True,
    },
}
H264 = ("h264-web", "h264-draft", "app-preview")
AUDIO_RATE = 48000

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

    def feed(self, path: Path, frames: int) -> None:
        """Frames spooled to a file by another worker (concatenated images), in order."""
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1 << 20)
                if not chunk:
                    break
                assert self.proc and self.proc.stdin
                try:
                    self.proc.stdin.write(chunk)
                except (BrokenPipeError, OSError):
                    raise OperationalError(f"ffmpeg stopped while encoding {self.dest.name}: {self._stderr()}") from None
        self.frames += frames

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


def check_profile(info: dict, path: Path, profile: str, frames: int, size: tuple[int, int], fps: int,
                  audio: bool = False) -> list[str]:
    """Problems with an encoded file against its profile (empty = PASS). audio: the file should
    carry the piece's mixed sound (the app-preview profile always wants a track, silent or not)."""
    v = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if len(v) != 1:
        return [f"{len(v)} video streams, want 1"]
    s = v[0]
    out = []
    spec = PROFILES.get(profile, {})
    a = [x for x in info.get("streams", []) if x.get("codec_type") == "audio"]
    if audio or spec.get("audio") == "required":
        if len(a) != 1:
            out.append(f"{len(a)} audio streams, want 1")
        else:
            x = a[0]
            if x.get("codec_name") != "aac":
                out.append(f"audio codec {x.get('codec_name')}, want aac")
            if x.get("channels") != 2:
                out.append(f"{x.get('channels')} audio channels, want 2 (stereo)")
            if str(x.get("sample_rate")) not in ("44100", "48000"):
                out.append(f"audio at {x.get('sample_rate')} Hz, want 44100 or 48000")
    elif a:
        out.append(f"{len(a)} audio stream(s) in a silent video")
    if "seconds" in spec:
        lo, hi = spec["seconds"]
        d = frames / fps if fps else 0
        if not lo <= d <= hi:
            out.append(f"lasts {d:.2f} s, want {lo:g}-{hi:g} s")
    if "fps" in spec and fps != spec["fps"]:
        out.append(f"{fps} fps, want {spec['fps']}")
    if "maxBytes" in spec and Path(path).stat().st_size > spec["maxBytes"]:
        out.append(f"{Path(path).stat().st_size:,} bytes, over {spec['maxBytes']:,}")
    if profile == "alpha-webm":
        tags = {k.lower(): str(v) for k, v in (s.get("tags") or {}).items()}
        if s.get("codec_name") != "vp9":
            out.append(f"codec {s.get('codec_name')}, want vp9")
        if tags.get("alpha_mode") != "1":
            out.append("no alpha channel (the WebM track lacks alpha_mode=1)")
    if profile == "alpha-prores":
        if s.get("codec_name") != "prores":
            out.append(f"codec {s.get('codec_name')}, want prores")
        if not str(s.get("pix_fmt", "")).startswith("yuva444"):
            out.append(f"pixel format {s.get('pix_fmt')}, want yuva444 (4444 with alpha)")
    if profile in H264:
        if s.get("codec_name") != "h264":
            out.append(f"codec {s.get('codec_name')}, want h264")
        if profile != "h264-draft" and s.get("profile") != "High":
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


def recording_frames(ff: str, src: Path, dest: Path, start: float, fps: int, count: int, size: tuple[int, int],
                     fit: str) -> int:
    """A screen recording as JPEG frames dest/00000.jpg... at the piece's fps (a variable-rate phone
    recording becomes one frame per video frame), scaled to cover or fit the format. The page
    shows frame n of the scene as file n, so seeking never decodes video in the browser. Returns
    how many frames the recording had (fewer than count: the page holds the last one)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    mode = "increase" if fit == "cover" else "decrease"
    _run([ff, "-v", "error", "-y", "-ss", f"{max(0.0, start):.3f}", "-i", str(src), "-an", "-vf",
          f"fps={fps},scale={size[0]}:{size[1]}:force_original_aspect_ratio={mode}:flags=lanczos,format=yuvj420p",
          "-frames:v", str(count), "-q:v", "2", "-start_number", "0", str(dest / "%05d.jpg")],
         f"frames of {Path(src).name}")
    return len(list(dest.glob("*.jpg")))


def alpha_range(ff: str, path: Path, profile: str) -> tuple[int, int] | None:
    """(min, max) alpha of the middle frame of an alpha file, or None when this ffmpeg can't decode
    the alpha (VP9 alpha needs the libvpx decoder)."""
    argv = [ff, "-v", "error"]
    if profile == "alpha-webm":
        argv += ["-c:v", "libvpx-vp9"]
    argv += ["-i", str(path), "-vf", "thumbnail=30,format=rgba", "-frames:v", "1", "-f", "rawvideo", "-"]
    try:
        data = _run(argv, f"alpha of {Path(path).name}").stdout
    except OperationalError:
        return None
    alpha = data[3::4]
    return (min(alpha), max(alpha)) if alpha else None


# ------------------------------------------------------------------ audio

def audio_info(fp: str, path: Path) -> dict:
    """{duration, channels, sampleRate, codec} of a file's first audio stream (InputError-free:
    OperationalError when it has none or can't be read)."""
    info = probe(fp, path, count_frames=False)
    a = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not a:
        raise OperationalError(f"{Path(path).name} has no audio stream")
    d = a[0].get("duration") or (info.get("format") or {}).get("duration") or 0
    return {"duration": float(d), "channels": a[0].get("channels"), "sampleRate": int(a[0].get("sample_rate") or 0),
            "codec": a[0].get("codec_name", "")}


def speech_span(ff: str, path: Path, noise_db: float = -40.0, gap: float = 0.15) -> tuple[float, float, float]:
    """(lead, end, total) seconds of a voice-over take: where the speech starts and ends inside the
    file (the room tone before and after is not speech), from ffmpeg's silencedetect."""
    r = _run([ff, "-hide_banner", "-nostats", "-i", str(path), "-af", f"silencedetect=noise={noise_db}dB:d={gap}",
              "-f", "null", "-"], f"silence in {Path(path).name}")
    err = r.stderr.decode(errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    # the decoded length (a header's duration is an estimate for mp3 and m4a)
    pcm = _run([ff, "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
               f"length of {Path(path).name}").stdout
    total = len(pcm) / 16000
    lead = ends[0] if starts and starts[0] <= 0.01 and ends else 0.0
    # trailing silence: a silence that starts after the speech and runs to the end of the file
    trailing = bool(starts) and starts[-1] > lead and (len(starts) > len(ends) or ends[-1] >= total - 0.1)
    end = starts[-1] if trailing else total
    if end <= lead:  # all silence: treat the whole take as the line
        return 0.0, total, total
    return round(lead, 3), round(end, 3), round(total, 3)


def _mix_graph(voices: list[tuple[int, float]], music: tuple[int, float, bool] | None, duration: float) -> tuple[str, str]:
    """A filtergraph that places each voice take at its delay and lays the music under it (ducked
    while someone speaks), cut to the video's length. Returns (graph, output label)."""
    fmt = f"aresample={AUDIO_RATE},aformat=sample_fmts=fltp:channel_layouts=stereo"
    parts, labels = [], []
    for k, (idx, delay) in enumerate(voices):
        # a take whose speech must start before its room tone ends is trimmed, not delayed
        head = f",atrim=start={-delay:.3f},asetpts=PTS-STARTPTS" if delay < 0 else ""
        ms = max(0, round(delay * 1000))
        parts.append(f"[{idx}:a]{fmt}{head},adelay={ms}|{ms}[v{k}]")
        labels.append(f"[v{k}]")
    if voices:
        # the voice bus lasts the whole video: sidechaincompress stops when its sidechain does
        parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0:duration=longest[vor]" if len(labels) > 1
                     else f"{labels[0]}anull[vor]")
        parts.append(f"[vor]apad,atrim=0:{duration:.3f}[vo]")
    out = "[pre]"
    if music:
        idx, gain, duck = music
        fade = max(0.0, duration - 1.0)
        parts.append(f"[{idx}:a]{fmt},volume={gain}dB,atrim=0:{duration:.3f},afade=t=out:st={fade:.3f}:d=1[mu]")
        if voices and duck:
            parts.append("[vo]asplit=2[vo1][vo2]")
            parts.append("[mu][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[ducked]")
            parts.append(f"[ducked][vo2]amix=inputs=2:normalize=0:duration=first{out}")
        elif voices:
            parts.append(f"[mu][vo]amix=inputs=2:normalize=0:duration=first{out}")
        else:
            parts.append(f"[mu]anull{out}")
    elif voices:
        parts.append(f"[vo]anull{out}")
    parts.append(f"{out}apad,atrim=0:{duration:.3f}[mixed]")
    return ";".join(parts), "[mixed]"


def mix(ff: str, dest: Path, duration: float, voices: list[tuple[Path, float]], music: tuple[Path, float, bool] | None,
        lufs: float = -16.0, true_peak: float = -1.5) -> dict:
    """Mix voice takes (file, start seconds) and music (file, gain dB, duck) into a 48 kHz stereo
    WAV of exactly duration seconds, normalised in two passes (EBU R128 loudnorm, linear). Returns
    the first pass's measurement."""
    inputs: list[str] = []
    vs = []
    for i, (f, start) in enumerate(voices):
        inputs += ["-i", str(f)]
        vs.append((i, start))
    mu = None
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music[0])]
        mu = (len(voices), music[1], music[2])
    if not inputs:
        raise ValueError("nothing to mix")
    graph, label = _mix_graph(vs, mu, duration)
    target = f"I={lufs}:TP={true_peak}:LRA=11"
    r = _run([ff, "-hide_banner", "-nostats", *inputs, "-filter_complex", f"{graph};{label}loudnorm={target}:print_format=json[o]",
              "-map", "[o]", "-f", "null", "-"], "mix (measure)")
    err = r.stderr.decode(errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err)
    if not m:
        raise OperationalError("mix: ffmpeg's loudnorm printed no measurement")
    meas = json.loads(m[0])
    if not math.isfinite(float(meas.get("input_i", "-inf"))):
        raise OperationalError("mix: the audio is silent (nothing to normalise)")
    second = (f"{target}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}"
              f":measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true")
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    _run([ff, "-hide_banner", "-v", "error", "-y", *inputs, "-filter_complex",
          f"{graph};{label}loudnorm={second},aresample={AUDIO_RATE},atrim=0:{duration:.3f}[o]",
          "-map", "[o]", "-ac", "2", "-ar", str(AUDIO_RATE), "-c:a", "pcm_s16le", str(dest)], "mix")
    return meas


def mux(ff: str, video: Path, audio: Path | None, dest: Path, duration: float, bitrate: str = "192k") -> None:
    """The video stream copied with an AAC stereo track: the mix, or silence when audio is None."""
    src = ["-i", str(audio)] if audio else ["-f", "lavfi", "-t", f"{duration:.3f}", "-i",
                                           f"anullsrc=r={AUDIO_RATE}:cl=stereo"]
    _run([ff, "-hide_banner", "-v", "error", "-y", "-i", str(video), *src, "-map", "0:v:0", "-map", "1:a:0",
          "-c:v", "copy", "-c:a", "aac", "-b:a", bitrate, "-ar", str(AUDIO_RATE), "-ac", "2",
          "-t", f"{duration:.3f}", "-movflags", "+faststart", str(dest)], f"mux {Path(dest).name}")


def loudness(ff: str, path: Path) -> tuple[float, float]:
    """(integrated loudness LUFS, true peak dBTP) of a file's audio, from ffmpeg's ebur128 filter."""
    r = _run([ff, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0", "-af", "ebur128=peak=true",
              "-f", "null", "-"], f"loudness of {Path(path).name}")
    err = r.stderr.decode(errors="replace")
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else err
    i = re.search(r"I:\s+(-?[0-9.]+|-inf)\s+LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[0-9.]+|-inf)\s+dBFS", summary)
    if not i:
        raise OperationalError(f"{Path(path).name}: ffmpeg's ebur128 printed no loudness")
    return float(i[1]), float(tp[1]) if tp else float("nan")


# Animated images and stills made from a format's master video (they have no encoder profile of
# their own; framecheck.anim_problems checks them).
ANIMATED = {
    "gif": {"label": "GIF, one 256-colour palette for the file, loops forever", "suffix": ".gif"},
    "webp-anim": {"label": "animated WebP (lossy, quality 80), loops forever", "suffix": ".webp"},
    "poster": {"label": "PNG still frame", "suffix": ".png"},
}


def _every(step: int, size: tuple[int, int]) -> str:
    """Every step-th frame of the master, scaled: a loop keeps the master's frames, never new ones."""
    return f"select='not(mod(n,{step}))',scale={size[0]}:{size[1]}:flags=lanczos"


def make_gif(ff: str, master: Path, dest: Path, step: int, rate: int, size: tuple[int, int]) -> None:
    vf = (f"{_every(step, size)},setpts=N/({rate}*TB),split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
          "[b][p]paletteuse=dither=sierra2_4a")
    _run([ff, "-v", "error", "-y", "-i", str(master), "-vf", vf, "-r", str(rate), "-loop", "0", str(dest)],
         f"GIF {Path(dest).name}")


def rgb_frames(ff: str, master: Path, step: int, size: tuple[int, int]) -> list[bytes]:
    """Every step-th frame of the master as raw RGB at size (for encoders outside ffmpeg)."""
    r = _run([ff, "-v", "error", "-i", str(master), "-vf", _every(step, size), "-fps_mode", "passthrough",
              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], f"decode {Path(master).name}")
    n = size[0] * size[1] * 3
    return [r.stdout[i:i + n] for i in range(0, len(r.stdout) - n + 1, n)]


def gray_frames(ff: str, path: Path, width: int = 64, passthrough: bool = False,
                crop: dict | None = None) -> tuple[list[bytes], int, int]:
    """Every decoded frame as 8-bit luma at a small width (for the flash and freeze signals).
    passthrough keeps every decoded frame of a variable-frame-rate file (one per timestamp in
    frame_times) instead of letting ffmpeg resample to the average rate; crop applies first."""
    vf = (_crop(crop) + "," if crop else "") + f"scale={width}:-2:flags=area,format=gray"
    r = _run([ff, "-v", "error", "-i", str(path), "-vf", vf, *(["-fps_mode", "passthrough"] if passthrough else []),
              "-f", "rawvideo", "-"], f"decode {Path(path).name}")
    data = r.stdout
    # height follows the aspect ratio; recover it from the byte count and the frame count
    pr = _run([ff, "-v", "error", "-i", str(path), "-vf", (_crop(crop) + "," if crop else "") + f"scale={width}:-2:flags=area",
               "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], f"decode {Path(path).name}").stdout
    info_h = len(pr) // width if pr else 0
    if not info_h:
        return [], width, 0
    size = width * info_h
    return [data[i:i + size] for i in range(0, len(data) - size + 1, size)], width, info_h


# ------------------------------------------------------------------ reference analysis (motion-ui)

def _crop(c: dict) -> str:
    return f"crop={int(c['w'])}:{int(c['h'])}:{int(c['x'])}:{int(c['y'])}"


def frame_times(fp: str, path: Path) -> list[float]:
    """Presentation time (seconds) of every decoded video frame, in decode order. For a variable
    frame rate, frame index / average fps is only approximate; these are the real times."""
    r = _run([fp, "-v", "error", "-select_streams", "v:0", "-show_entries",
              "frame=best_effort_timestamp_time,pts_time,pkt_dts_time", "-of", "json", str(path)],
             f"ffprobe frames {Path(path).name}")
    out = []
    for f in json.loads(r.stdout.decode("utf-8", errors="replace")).get("frames", []):
        t = f.get("best_effort_timestamp_time", f.get("pts_time", f.get("pkt_dts_time")))
        try:
            out.append(float(t))
        except (TypeError, ValueError):
            out.append(out[-1] if out else 0.0)
    return out


def extract_frames(ff: str, path: Path, dest: Path, indices: list[int] | None = None, crop: dict | None = None,
                   scale: int | None = None) -> list[Path]:
    """Decoded frames as PNG files dest/000001.png... (decode order, every frame kept). indices
    (0-based, sorted) keeps only those frames; files are numbered in the order kept."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    filters = []
    if indices is not None:
        if not indices:
            return []
        filters.append("select='" + "+".join(f"eq(n,{i})" for i in indices) + "'")  # quoted: commas need no escape
    if crop:
        filters.append(_crop(crop))
    if scale:
        filters.append(f"scale={int(scale)}:-2:flags=lanczos")
    argv = [ff, "-v", "error", "-y", "-i", str(path)]
    if filters:
        argv += ["-vf", ",".join(filters)]
    argv += ["-fps_mode", "passthrough", str(dest / "%06d.png")]
    _run(argv, f"extract frames {Path(path).name}")
    return sorted(dest.glob("*.png"))
