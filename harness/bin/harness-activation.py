#!/usr/bin/env python3
"""Report whether each agent will actually run the harness hooks in a project.

    python harness-activation.py <project> <target>[,<target>…]

Writing a hook file is not the same as the hooks being active: Codex runs
project hooks only in a trusted project and only after each hook was reviewed
(/hooks); Gemini CLI loads no settings hooks at all in an untrusted folder.
One line per target, tab separated:

    <target>  active|configured-untrusted|disabled|unknown  <what to do>

The script reads the agents' own user files (never writes them) and never sets
trust on the user's behalf. Exit code 0 (the report is informational).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None


def home() -> Path:
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~").expanduser()


def claude(root: Path) -> tuple[str, str]:
    for f in (root / ".claude/settings.json", root / ".claude/settings.local.json", home() / ".claude/settings.json"):
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("disableAllHooks") is True:
                return "disabled", f"{f} sets disableAllHooks; remove it"
        except (OSError, ValueError):
            continue
    return "active", "hooks run from .claude/settings.json"


def codex(root: Path) -> tuple[str, str]:
    cfg = Path(os.environ.get("CODEX_HOME") or home() / ".codex") / "config.toml"
    if tomllib is None:
        return "unknown", "Python 3.11+ is needed to read ~/.codex/config.toml"
    try:
        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except OSError:
        data = {}
    except ValueError:
        return "unknown", f"{cfg} does not parse"
    if data.get("features", {}).get("hooks") is False or data.get("features", {}).get("codex_hooks") is False:
        return "disabled", f"{cfg} turns hooks off ([features] hooks = false)"
    projects = data.get("projects", {})
    trusted = any(Path(p).resolve() == root.resolve() and v.get("trust_level") == "trusted"
                  for p, v in projects.items() if isinstance(v, dict))
    if not trusted:
        return "configured-untrusted", "trust this project in Codex (it asks on first run), then review the hooks with /hooks"
    hooks_file = str((root / ".codex/hooks.json").resolve())
    state = data.get("hooks", {}).get("state", {})
    if not any(k.startswith(hooks_file + ":") and isinstance(v, dict) and v.get("trusted_hash")
               for k, v in state.items()):
        return "configured-untrusted", "run /hooks in Codex and trust the harness hooks (and again after a harness update changes them)"
    return "active", "project trusted and hooks reviewed (re-review with /hooks after a harness update changes them)"


def gemini(root: Path) -> tuple[str, str]:
    if os.environ.get("GEMINI_CLI_TRUST_WORKSPACE") == "true":
        return "active", "GEMINI_CLI_TRUST_WORKSPACE=true"
    settings = home() / ".gemini/settings.json"
    try:
        if json.loads(settings.read_text(encoding="utf-8")).get("security", {}).get("folderTrust", {}).get("enabled") is False:
            return "active", "folder trust is off"
    except (OSError, ValueError):
        pass
    path = Path(os.environ.get("GEMINI_CLI_TRUSTED_FOLDERS_PATH") or home() / ".gemini/trustedFolders.json")
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        rules = {}
    best, verdict = -1, None
    here = root.resolve()
    for p, v in rules.items():
        base = Path(p).resolve()
        if v == "TRUST_PARENT":
            base = base.parent
        if here == base or base in here.parents:
            if len(str(base)) > best:
                best, verdict = len(str(base)), v
    if verdict in ("TRUST_FOLDER", "TRUST_PARENT"):
        return "active", "folder trusted"
    return "configured-untrusted", "trust this folder in Gemini CLI (/permissions), or no settings hooks load at all"


def cursor(root: Path) -> tuple[str, str]:
    return "unknown", "Cursor runs project hooks only in a trusted workspace; check Customize > Hooks"


def copilot(root: Path) -> tuple[str, str]:
    return "unknown", "Copilot loads repo hooks after you trust the folder; check with /env (CLI) or Chat: Configure Hooks (VS Code)"


def antigravity(root: Path) -> tuple[str, str]:
    try:
        entry = json.loads((root / ".agents/hooks.json").read_text(encoding="utf-8")).get("quantqbit-harness", {})
    except (OSError, ValueError):
        return "unknown", ".agents/hooks.json is missing or not JSON; re-run harness sync"
    if entry.get("enabled") is False:
        return "disabled", ".agents/hooks.json sets the harness hooks enabled: false"
    return "active", "no trust step is documented; check Customizations > Hooks"


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(argv[1])
    for t in argv[2].split(","):
        fn = globals().get(t)
        state, what = fn(root) if callable(fn) else ("unknown", "no activation check for this target")
        print(f"{t}\t{state}\t{what}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
