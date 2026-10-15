#!/usr/bin/env python3
"""Merge the harness hooks into an agent's own hook config, keeping the user's entries.

    python hooks_merge.py <flavor> <current|-> <out> [--remove]

flavor   cursor | gemini | codex | antigravity | copilot
current  the project's file as it is now ("-" if absent)
out      where to write the result; with --remove an empty result is written as
         an empty file, which sync.sh then deletes if the harness created it

Harness entries are recognised by the hook script path (.agents/harness/hooks/),
so they are replaced on every sync and removed on uninstall, while every other
entry, key and setting in the file is kept as it was. The file must be strict
JSON. Exit codes: 0 ok, 2 bad input (the file is not JSON, or has an unexpected
shape: nothing is written).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS = ".agents/harness/hooks/"
MARK = "harness/hooks/"   # matches both the project-relative and the .agents-relative form


def cmd(flavor: str, script: str) -> str:
    agent = "" if flavor == "cursor" else f" --agent {flavor}"
    if flavor == "cursor":
        # The exact command Claude Code's settings.json uses: Cursor drops a
        # .claude/settings.json hook that duplicates one of its own.
        return f'bash "$CLAUDE_PROJECT_DIR/{HOOKS}{script}"'
    if flavor == "gemini":
        return f'bash "$GEMINI_PROJECT_DIR/{HOOKS}{script}"{agent}'
    if flavor == "antigravity":
        return f"bash harness/hooks/{script}{agent}"   # runs in the folder holding hooks.json (.agents/)
    # codex and copilot run hooks in the project root (Codex: the session cwd).
    return f'bash "$(git rev-parse --show-toplevel)/{HOOKS}{script}"{agent}' if flavor == "codex" \
        else f"bash {HOOKS}{script}{agent}"


def harness_entries(flavor: str) -> dict:
    c = lambda s: cmd(flavor, s)  # noqa: E731
    if flavor == "cursor":
        h = lambda s, m=None, t=10: {**({"matcher": m} if m else {}), "command": c(s), "timeout": t}  # noqa: E731
        return {"sessionStart": [h("session-start.sh")],
                "beforeSubmitPrompt": [h("prompt-router.sh")],
                "preToolUse": [h("guard.sh"), h("file-context.sh", "Write|Delete")],
                "beforeReadFile": [h("guard.sh")],
                "postToolUse": [h("post-edit-lint.sh", "Write", 30)]}
    if flavor == "gemini":
        g = lambda name, s, m=None, t=10000: {**({"matcher": m} if m else {}), "hooks": [  # noqa: E731
            {"type": "command", "name": name, "command": c(s), "timeout": t}]}
        return {"SessionStart": [g("harness-session-start", "session-start.sh")],
                "BeforeAgent": [g("harness-prompt-router", "prompt-router.sh")],
                "BeforeTool": [g("harness-guard", "guard.sh", ".*"),
                               g("harness-file-context", "file-context.sh", "write_file|replace")],
                "AfterTool": [g("harness-post-edit-lint", "post-edit-lint.sh", "write_file|replace", 30000)]}
    if flavor in ("codex", "copilot"):
        def k(s, m=None, t=10):
            e = {"type": "command", "command": c(s), "timeout": t}
            if flavor == "copilot":
                e = {"type": "command", "bash": c(s), "timeoutSec": t}
            return {**({"matcher": m} if m else {}), "hooks": [e]} if flavor == "codex" else {**({"matcher": m} if m else {}), **e}
        edit = "apply_patch|Edit|Write" if flavor == "codex" else "Edit|Write"
        return {"SessionStart": [k("session-start.sh")],
                "UserPromptSubmit": [k("prompt-router.sh")],
                "PreToolUse": [k("guard.sh"), k("file-context.sh", edit)],
                "PostToolUse": [k("post-edit-lint.sh", edit, 30)]}
    if flavor == "antigravity":
        # Its payload does not name the event, so the command does (--event).
        a = lambda s, ev, t=10: {"type": "command", "command": f"{c(s)} --event {ev}", "timeout": t}  # noqa: E731
        return {"enabled": True,
                "SessionStart": [a("session-start.sh", "SessionStart")],
                "PreToolUse": [{"matcher": "", "hooks": [a("guard.sh", "PreToolUse"),
                                                         a("file-context.sh", "PreToolUse")]}],
                "PostToolUse": [{"matcher": "", "hooks": [a("post-edit-lint.sh", "PostToolUse", 30)]}]}
    raise ValueError(f"unknown flavor {flavor!r}")


ANTIGRAVITY_KEY = "quantqbit-harness"


def is_harness(entry) -> bool:
    return MARK in json.dumps(entry)


def strip(events: dict) -> dict:
    """Remove harness entries from an {event: [entries]} map; drop emptied events."""
    out = {}
    for ev, entries in events.items():
        if not isinstance(entries, list):
            out[ev] = entries
            continue
        kept = [e for e in entries if not is_harness(e)]
        if kept:
            out[ev] = kept
    return out


def merge(flavor: str, data: dict, remove: bool) -> dict:
    fresh = not data   # only a file the harness creates gets a "version" key from it
    if flavor == "antigravity":            # top-level keys are named hooks
        data.pop(ANTIGRAVITY_KEY, None)
        if not remove:
            data[ANTIGRAVITY_KEY] = harness_entries(flavor)
        return data
    hooks = data.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError('"hooks" is not an object')
    hooks = strip(hooks)
    if not remove:
        for ev, entries in harness_entries(flavor).items():
            hooks.setdefault(ev, [])
            hooks[ev] = hooks[ev] + entries
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    if flavor in ("cursor", "copilot") and data.get("hooks") and fresh:
        data = {"version": 1, **data}
    if remove and set(data) <= {"version"}:
        return {}
    return data


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--remove"]
    remove = "--remove" in argv
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    flavor, cur, out = args
    try:
        data = {} if cur == "-" or not Path(cur).is_file() or not Path(cur).read_text(encoding="utf-8").strip() \
            else json.loads(Path(cur).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("the top level is not an object")
        result = merge(flavor, data, remove)
    except (ValueError, OSError) as e:
        print(f"[FAIL] {cur}: {e} (it must be strict JSON; fix it and re-run)", file=sys.stderr)
        return 2
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        if result:
            f.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
