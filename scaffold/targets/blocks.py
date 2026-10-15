#!/usr/bin/env python3
"""Write the harness block into an instruction file the project owns (AGENTS.md, GEMINI.md).

    python blocks.py <flavor> <current|-> <out> <rules_dir> [--remove]

flavor     agents-md (Codex: the core rules inline, then an index of the
           path-scoped rules) | gemini-md (Gemini CLI: an @import of the core
           rules, then the same index)
current    the project's file now ("-" if absent)
out        the result; with --remove an empty result means "delete the file"
           (sync.sh only deletes it if the harness created it)
rules_dir  the staged neutral rules (.agents/harness/rules/ in the stage)

Only the text between the markers is the harness's:

    <!-- harness:begin vX - managed by harness sync; edit outside this block -->
    …
    <!-- harness:end -->

A file without the markers gets the block appended once. Prints two hashes on
stdout: the sha256 of the block found in the current file ("-" if none) and of
the block written ("-" when removed), so sync.sh can tell a hand edit inside
the block from its own last write. Exit codes: 0 ok, 2 bad input.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

BEGIN_RE = re.compile(r"<!-- harness:begin[^\n]*-->\n")
END = "<!-- harness:end -->"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rule_globs(text: str) -> list[str]:
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---\n", 4)
    front = text[4:end].split("\n") if end > 0 else []
    out, on = [], False
    for ln in front:
        if ln.startswith("paths:"):
            on = True
            continue
        m = re.match(r"\s*-\s*(.+)$", ln)
        if on and m:
            out.append(m.group(1).strip().strip("'\""))
        elif on:
            on = False
    return out


def title(text: str, fallback: str) -> str:
    return next((ln[2:].strip() for ln in text.split("\n") if ln.startswith("# ")), fallback)


def strip_marker(text: str) -> str:
    """Drop frontmatter and the harness:managed marker line."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            text = text[end + 5:]
    lines = text.split("\n")
    if lines and "harness:managed" in lines[0]:
        lines = lines[1:]
    return "\n".join(lines).strip("\n")


def block_body(flavor: str, rules_dir: Path, version: str) -> str:
    core = rules_dir / "00-core.md"
    parts = [f"<!-- harness:begin v{version} - managed by harness sync; edit outside this block -->"]
    if flavor == "agents-md":
        parts.append(strip_marker(core.read_text(encoding="utf-8")))
    else:
        parts.append("@./.agents/harness/rules/00-core.md")
    index = []
    for f in sorted(rules_dir.glob("*.md")):
        if f.name == "00-core.md":
            continue
        text = f.read_text(encoding="utf-8")
        globs = rule_globs(text)
        if globs:
            index.append(f"- {title(strip_marker(text), f.stem)}: when you work on `{'`, `'.join(globs)}`, "
                         f"read `.agents/harness/rules/{f.name}` first.")
    if index:
        parts.append("## Harness path rules\nThese rules apply only to matching files. Read the rule before you "
                     "change such a file:\n" + "\n".join(index))
    parts.append(END)
    return "\n\n".join(parts) + "\n"


def find_block(text: str) -> tuple[int, int] | None:
    m = BEGIN_RE.search(text)
    if not m:
        return None
    e = text.find(END, m.end())
    if e < 0:
        raise ValueError("a harness:begin marker without harness:end")
    e += len(END)
    if text[e:e + 1] == "\n":
        e += 1
    return m.start(), e


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if a != "--remove"]
    remove = "--remove" in argv
    if len(args) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    flavor, cur, out, rules_dir, version = args
    if flavor not in ("agents-md", "gemini-md"):
        print(f"[FAIL] unknown block flavor {flavor}", file=sys.stderr)
        return 2
    try:
        text = Path(cur).read_text(encoding="utf-8").replace("\r\n", "\n") if cur != "-" and Path(cur).is_file() else ""
        span = find_block(text)
        old = sha(text[span[0]:span[1]]) if span else "-"
        if remove:
            new_block = ""
        else:
            new_block = block_body(flavor, Path(rules_dir), version)
        if span:
            result = text[:span[0]] + new_block + text[span[1]:]
        elif new_block:
            result = (text.rstrip("\n") + "\n\n" if text.strip() else "") + new_block
        else:
            result = text
        if remove:
            result = result.rstrip("\n") + "\n" if result.strip() else ""
    except (OSError, ValueError, UnicodeDecodeError) as e:
        print(f"[FAIL] {cur}: {e}", file=sys.stderr)
        return 2
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(result)
    print(old, sha(new_block) if new_block else "-")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
