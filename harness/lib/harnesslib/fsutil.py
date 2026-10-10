"""Strict JSON, safe paths, atomic writes, run IDs, locks and staged publishing.

- load_json() rejects duplicate keys and non-finite numbers (NaN, Infinity), which json.loads
  accepts by default.
- safe_rel() accepts only relative paths that stay inside their root: no absolute paths, drive
  letters, '..' segments, NUL bytes or backslashes; resolve_inside() also rejects symlinks that
  escape the root.
- write_atomic() writes a sibling temp file and os.replace()s it, keeping an optional recovery copy.
- Publisher stages files in a folder next to the destination and moves them into place under a
  per-destination lock, so a failed run leaves the previous outputs untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import time
from pathlib import Path
from typing import Any


class InputError(ValueError):
    """Invalid input data or an unmet gate (exit 1)."""


class UsageError(ValueError):
    """Invalid invocation: bad arguments, or a file named on the command line is missing (exit 2)."""


class OperationalError(RuntimeError):
    """Lock held, missing tool, I/O failure (exit 2)."""


# ------------------------------------------------------------------ JSON

def _no_dupes(pairs: list[tuple[str, Any]]) -> dict:
    out: dict = {}
    for k, v in pairs:
        if k in out:
            raise InputError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _no_constant(name: str) -> Any:
    raise InputError(f"non-finite number {name} is not allowed")


def loads_json(text: str, where: str = "JSON") -> Any:
    try:
        return json.loads(text, object_pairs_hook=_no_dupes, parse_constant=_no_constant)
    except InputError as e:
        raise InputError(f"{where}: {e}") from None
    except ValueError as e:
        raise InputError(f"{where}: invalid JSON ({e})") from None


def load_json(path: Path) -> Any:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        raise InputError(f"cannot read {path}: {e.strerror or e}") from None
    return loads_json(text, str(path))


def canonical(obj: Any) -> str:
    """Deterministic JSON for hashing: sorted keys, no whitespace, UTF-8 kept."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def dumps_pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def script_json(obj: Any) -> str:
    """JSON safe to embed in a <script> element: no '</', U+2028 or U+2029 can end or break it."""
    text = json.dumps(obj, ensure_ascii=False, allow_nan=False)
    return text.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


# ------------------------------------------------------------------ paths

_BAD_REL = re.compile(r"(^|/)\.\.(/|$)")


def safe_rel(value: str, what: str = "path") -> str:
    """Validate a project-relative path string and return it with forward slashes."""
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{what}: must be a non-empty relative path")
    if "\x00" in value or "\\" in value:
        raise InputError(f"{what}: {value!r} must use forward slashes and no NUL bytes")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value) or value.startswith("~"):
        raise InputError(f"{what}: {value!r} must be relative to the project")
    if _BAD_REL.search(value):
        raise InputError(f"{what}: {value!r} must not contain '..'")
    return value


def resolve_inside(root: Path, rel: str, what: str = "path", must_exist: bool = False) -> Path:
    """root/rel, refusing anything (including a symlink) that resolves outside root."""
    safe_rel(rel, what)
    base = Path(root).resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise InputError(f"{what}: {rel!r} resolves outside {base}") from None
    if must_exist and not target.exists():
        raise InputError(f"{what}: {rel!r} not found under {base}")
    return target


# ------------------------------------------------------------------ writes

def write_atomic(path: Path, text: str, backup: bool = False) -> Path | None:
    """Replace path with text in one step. With backup, an existing file is first copied to
    <name>.bak (overwriting an older .bak) and that recovery path is returned."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    saved = None
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        if backup and path.exists():
            saved = path.with_name(path.name + ".bak")
            shutil.copy2(path, saved)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()
    return saved


def run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)


def self_ignoring_dir(path: Path, note: str) -> Path:
    """Create a folder that git ignores entirely (a '*' .gitignore inside it)."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    gi = path / ".gitignore"
    if not gi.exists():
        gi.write_text(f"# {note}\n*\n", encoding="utf-8")
    return path


# ------------------------------------------------------------------ locks

class DirLock:
    """mkdir-based lock with an owner note; stale after max_age seconds."""

    def __init__(self, path: Path, what: str, max_age: float = 2 * 3600) -> None:
        self.path, self.what, self.max_age = Path(path), what, max_age

    def __enter__(self) -> "DirLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.mkdir()
        except FileExistsError:
            age = time.time() - self.path.stat().st_mtime
            if age < self.max_age and not self._owner_gone():
                owner = self.path / "owner"
                who = owner.read_text(encoding="utf-8").strip() if owner.is_file() else "unknown"
                raise OperationalError(f"{self.what} is locked by another run ({who}, {int(age // 60)} min ago); "
                                       f"wait for it. If none is running, delete {self.path}") from None
            shutil.rmtree(self.path, ignore_errors=True)
            self.path.mkdir()
        (self.path / "owner").write_text(f"pid {os.getpid()} on {socket.gethostname()}\n", encoding="utf-8")
        return self

    def __exit__(self, *exc: object) -> None:
        shutil.rmtree(self.path, ignore_errors=True)

    def _owner_gone(self) -> bool:
        """True when the lock names a process on this machine that no longer runs (a killed run).
        POSIX only: on Windows os.kill(pid, 0) would terminate the process."""
        if os.name == "nt":
            return False
        try:
            m = re.fullmatch(r"pid (\d+) on (.+)", (self.path / "owner").read_text(encoding="utf-8").strip())
        except OSError:
            return False
        if not m or m.group(2) != socket.gethostname():
            return False
        try:
            os.kill(int(m.group(1)), 0)
        except ProcessLookupError:
            return True
        except OSError:
            return False
        return False


# ------------------------------------------------------------------ staged publishing

OWNED = ".render-manifest.json"


class Publisher:
    """Stage outputs, then move them into dest under a lock.

    with Publisher(dest, "store renders") as pub:
        path = pub.stage_path("play/phone/01.png")   # write the file here
        ...checks...
        pub.publish(prune=True)                       # or leave the block without publishing
    Files listed in dest/.render-manifest.json by an earlier publish are "owned": prune=True deletes
    owned files this publish did not produce. Unowned files are never deleted, only reported.
    """

    def __init__(self, dest: Path, what: str, run: str | None = None) -> None:
        self.dest = Path(dest)
        self.what = what
        self.run = run  # recorded in the owned-files record when given (video runs)
        self.id = run_id()
        self.stage = self.dest / f".staging-{self.id}"
        self.lock = DirLock(self.dest / ".publish.lock", f"{what} output folder {self.dest}")
        self.published: list[str] = []
        self.removed: list[str] = []
        self.unowned_stale: list[str] = []

    def __enter__(self) -> "Publisher":
        self.stage.mkdir(parents=True, exist_ok=False)
        return self

    def __exit__(self, *exc: object) -> None:
        shutil.rmtree(self.stage, ignore_errors=True)

    def stage_path(self, rel: str) -> Path:
        p = self.stage / safe_rel(rel, "output")
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def staged(self) -> list[str]:
        return sorted(p.relative_to(self.stage).as_posix() for p in self.stage.rglob("*") if p.is_file())

    def owned(self) -> dict:
        f = self.dest / OWNED
        if not f.is_file():
            return {}
        try:
            data = load_json(f)
        except InputError:
            return {}
        return data.get("files", {}) if isinstance(data, dict) else {}

    def publish(self, prune: bool = False) -> None:
        """Move staged files into dest and record them as owned. prune: also delete files an
        earlier publish owned that this publish did not produce (a full release set)."""
        files = self.staged()
        with self.lock:
            previous = self.owned()
            record = dict(previous)
            for rel in files:
                target = self.dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    os.replace(self.stage / rel, target)
                except OSError as e:
                    done = ", ".join(self.published) or "nothing"
                    raise OperationalError(f"could not replace {target} ({e.strerror or e}); already replaced: {done}. "
                                           "Close any program holding the file (a video player) and run again") from None
                record[rel] = sha256_file(target)
                self.published.append(rel)
            if prune:
                keep = set(files)
                for rel in sorted(previous):
                    if rel not in keep:
                        p = self.dest / rel
                        if p.is_file():
                            p.unlink()
                            self.removed.append(rel)
                        record.pop(rel, None)
            doc = {"what": self.what, "files": record}
            if self.run:
                doc["run"] = self.run
            write_atomic(self.dest / OWNED, dumps_pretty(doc))

    def report_unowned(self, candidates: list[Path]) -> list[str]:
        owned = self.owned()
        out = []
        for p in candidates:
            rel = p.relative_to(self.dest).as_posix()
            if rel not in owned and rel not in self.published:
                out.append(rel)
        self.unowned_stale = out
        return out
