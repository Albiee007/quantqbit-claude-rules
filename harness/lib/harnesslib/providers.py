"""Opt-in generation providers for brand-video: text-to-speech, word alignment and b-roll.

The harness never contains a vendor client or a key. A project that wants generated media declares
its own commands in brand/video/providers.json (a local TTS engine, a script that calls a paid
service, an aligner); the harness runs them only when the main session runs
`render_video.py generate`, after the owner asked for it (sub-agents are refused by the guard).

    {"schemaVersion": 1, "providers": {
       "tts":   {"label": "...", "command": ["{python}", "tools/tts.py", "--text", "{text}", "--out", "{out}"],
                 "env": ["VENDOR_API_KEY"], "terms": "where the licence/terms are recorded"},
       "align": {"label": "...", "command": [..., "{audio}", "{text}", "{out}"]},
       "broll": {"label": "...", "command": [..., "{prompt}", "{out}", "{width}", "{height}", "{seconds}"]}}}

- Placeholders are replaced in each argument; no shell is involved. Commands run from the project
  root with a timeout, and must write {out}.
- Credentials stay in the environment: "env" names the variables a command needs, their values
  are never read into a record, a hash or a log. Changing a provider, its command or a key changes
  no approval; the bytes it generates are hashed like any other media (the storyboard for pictures
  and recordings, the mix for voice takes).
- Every generated file is recorded in brand/video/<id>/media/provenance.json (provider label,
  kind, time, the sha256 of the file and of its input text), and a render lists AI-generated voice
  and media as disclosure review items.
"""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

from . import schema
from .direction import now_utc
from .fsutil import InputError, OperationalError, UsageError, dumps_pretty, load_json, sha256_file, sha256_text, write_atomic

CONFIG = "brand/video/providers.json"
KINDS = ("tts", "align", "broll")
TIMEOUT_S = 900
PLACEHOLDERS = {
    "tts": ("text", "out", "scene", "language", "casting", "prompt", "python"),
    "align": ("audio", "text", "out", "scene", "language", "python"),
    "broll": ("prompt", "out", "scene", "width", "height", "seconds", "fps", "python"),
}


def load(root: Path) -> dict:
    f = Path(root) / CONFIG
    if not f.is_file():
        raise UsageError(f"{CONFIG} not found: the project declares its own generation commands there "
                         "(see the brand-video references/providers.md)")
    data = load_json(f)
    schema.check(data, "video-providers", CONFIG)
    return data["providers"]


def provider(root: Path, kind: str) -> dict:
    p = load(root).get(kind)
    if not p:
        raise UsageError(f"{CONFIG} declares no {kind!r} provider")
    missing = [v for v in p.get("env") or [] if not os.environ.get(v)]
    if missing:
        raise OperationalError(f"the {kind} provider ({p['label']}) needs {', '.join(missing)} in the environment "
                               "(never in a project file)")
    return p


CMD_UNSAFE = re.compile(r'[&|<>^%"!\r\n]')  # what cmd.exe would interpret in a .cmd/.bat argument


def argv_for(kind: str, p: dict, values: dict) -> list[str]:
    """The command with its placeholders filled in, in one pass (a value is never expanded again)."""
    values = {k: str(v) for k, v in dict(values, python=sys.executable).items()}
    allowed = set(PLACEHOLDERS[kind])

    def fill(m: re.Match) -> str:
        return values.get(m[1], "") if m[1] in allowed else m[0]

    argv = [re.sub(r"\{(\w+)\}", fill, arg) for arg in p["command"]]
    prog = shutil.which(argv[0]) or argv[0]
    if os.name == "nt" and prog.lower().endswith((".cmd", ".bat")):
        bad = [a for a in argv[1:] if CMD_UNSAFE.search(a)]
        if bad:
            raise UsageError(f"the {kind} provider's command is a batch file ({Path(prog).name}), and an argument "
                             f"would be read by cmd.exe ({bad[0][:40]!r}); call a program or script directly, or pass "
                             "the text through a file placeholder ({text}, {prompt})")
    return argv


def run_bounded(argv: list[str], cwd: Path | None, timeout: float, env: dict | None = None) -> tuple[int, bytes, bytes]:
    """Run a command in its own process group; on a timeout stop the group (npx, node, a browser and
    whatever a provider script started), never just the first process."""
    extra = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True})
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, **extra)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except BaseException:
        _stop_group(proc)
        raise


def _stop_group(proc: subprocess.Popen) -> None:
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
    try:
        proc.kill()
        proc.communicate(timeout=10)
    except Exception:
        pass


def redact(text: str, p: dict) -> str:
    """A provider's output with the values of its keys replaced (a failing script may print them)."""
    for name in p.get("env") or []:
        v = os.environ.get(name)
        if v and len(v) >= 4:
            text = text.replace(v, "***")
    return text


def run(root: Path, kind: str, p: dict, values: dict, out: Path) -> None:
    """Run one provider command with its placeholders filled in. The command must write out."""
    argv = argv_for(kind, p, values)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    limit = p.get("timeoutS", TIMEOUT_S)
    try:
        rc, _, err = run_bounded(argv, root, limit)
    except subprocess.TimeoutExpired:
        raise OperationalError(f"the {kind} provider ({p['label']}) did not finish within {limit} s (stopped)") from None
    except OSError as e:
        raise OperationalError(f"the {kind} provider ({p['label']}) could not start {argv[0]}: {e}") from None
    if rc != 0:
        tail = redact(" | ".join(err.decode(errors="replace").strip().splitlines()[-3:]), p)
        raise OperationalError(f"the {kind} provider ({p['label']}) failed ({rc}): {tail}")
    if not out.is_file() or out.stat().st_size == 0:
        raise OperationalError(f"the {kind} provider ({p['label']}) wrote nothing to {out.name}")


# ------------------------------------------------------------------ provenance

def provenance_path(pieces: str, pid: str) -> str:
    return f"{pieces}/{pid}/media/provenance.json"


def read_provenance(root: Path, rel: str) -> dict:
    f = Path(root) / rel
    if not f.is_file():
        return {}
    data = load_json(f)
    schema.check(data, "video-provenance", rel)
    return data["files"]


def record(root: Path, rel: str, file_rel: str, kind: str, label: str, input_text: str) -> dict:
    files = read_provenance(root, rel)
    entry = {"kind": kind, "provider": label, "at": now_utc(), "sha256": sha256_file(Path(root) / file_rel),
             "input": sha256_text(input_text), "aiGenerated": kind in ("tts", "broll")}
    files[file_rel] = entry
    doc = {"schemaVersion": 1, "files": dict(sorted(files.items()))}
    schema.check(doc, "video-provenance", rel)
    write_atomic(Path(root) / rel, dumps_pretty(doc))
    return entry


def generated(root: Path, rel: str) -> dict[str, dict]:
    """The provenance entries whose file is still the generated bytes (an edited or replaced file is
    the owner's own again)."""
    out = {}
    for file_rel, e in read_provenance(root, rel).items():
        f = Path(root) / file_rel
        if f.is_file() and sha256_file(f) == e["sha256"]:
            out[file_rel] = e
    return out


def check_words(data: object, total: float) -> list[dict]:
    """A word alignment: {"words": [{"word", "start", "end"}...]} in seconds into the take."""
    if not isinstance(data, dict) or not isinstance(data.get("words"), list) or not data["words"]:
        raise InputError("an alignment is {\"words\": [{\"word\": ..., \"start\": s, \"end\": s}, ...]}")
    words, last = [], 0.0
    for i, w in enumerate(data["words"]):
        try:
            word, start, end = str(w["word"]), float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            raise InputError(f"alignment word {i}: needs word, start and end") from None
        if not (0 <= start <= end <= total + 0.05) or start + 1e-6 < last:
            raise InputError(f"alignment word {i} ({word!r}): {start:.3f}-{end:.3f} s is out of order or past the take "
                             f"({total:.2f} s)")
        words.append({"word": word, "start": round(start, 3), "end": round(end, 3)})
        last = start
    return words
