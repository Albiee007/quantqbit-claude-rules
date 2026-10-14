#!/usr/bin/env python3
"""Render staged harness files for a target agent (called by scaffold/sync.sh).

The harness source is written in Claude Code's format. Each target's map
(scaffold/targets/<target>.map) names a renderer per kind; this script rewrites
the staged copy in place:

    python render.py <list.tsv>

Each row: renderer  target  staged_file  logical_dest  dest
(logical_dest is "<kind>:<path>", dest the project path).

Renderers
  claude-core   keep the <!-- agent:claude --> blocks of the core rules, drop the others
  paths         neutral prose: Claude Code paths become the shared ones (.agents/…)
  core          paths + the <!-- agent:other --> blocks of the core rules
  mdc           Cursor rule (.mdc): description/globs/alwaysApply frontmatter
  instructions  Copilot path-scoped instructions: applyTo frontmatter
  ag-rule       Antigravity rule: trigger/globs frontmatter
  <t>-agent     a sub-agent in target t's format (cursor, copilot, gemini, antigravity, codex)

Exit codes: 0 ok, 2 bad input.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MARK = "harness:managed"

# Claude Code paths in the prose, and what every other agent reads instead.
NEUTRAL_PATHS = [
    (".claude/skills/", ".agents/skills/"),
    (".claude/rules/harness/", ".agents/harness/rules/"),
    (".claude/rules/project/", "AGENTS.md"),
]
AGENT_DIRS = {
    "cursor": ".cursor/agents/",
    "copilot": ".github/agents/",
    "gemini": ".gemini/agents/",
    "antigravity": ".agents/agents/",
    "codex": ".codex/agents/",
}

# Claude Code tool names in agent frontmatter, mapped per target. None = no tools field.
TOOLS = {
    "copilot": {"Read": ["read"], "Edit": ["edit"], "Write": ["edit"], "Glob": ["search"],
                "Grep": ["search"], "Bash": ["execute"], "WebFetch": ["web"]},
    "gemini": {"Read": ["read_file", "read_many_files", "list_directory"], "Edit": ["replace"],
               "Write": ["write_file"], "Glob": ["glob"], "Grep": ["grep_search"],
               "Bash": ["run_shell_command"], "WebFetch": ["web_fetch"]},
    "antigravity": {"Read": ["view_file", "list_dir"], "Edit": ["replace_file_content", "multi_replace_file_content"],
                    "Write": ["write_to_file"], "Glob": ["find_by_name"], "Grep": ["grep_search"],
                    "Bash": ["run_command"], "WebFetch": ["read_url_content"]},
}


def split_front(text: str) -> tuple[list[str], str]:
    """Frontmatter lines (without the --- fences) and the rest."""
    if not text.startswith("---\n"):
        return [], text
    end = text.find("\n---\n", 4)
    if end < 0:
        return [], text
    return text[4:end].split("\n"), text[end + 5:]


def front_scalar(lines: list[str], key: str) -> str:
    for ln in lines:
        if ln.startswith(key + ":"):
            v = ln[len(key) + 1:].strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
                v = v[1:-1]
            return v
    return ""


def front_list(lines: list[str], key: str) -> list[str]:
    out, on = [], False
    for ln in lines:
        if ln.startswith(key + ":"):
            on = True
            rest = ln[len(key) + 1:].strip()
            if rest:
                out += [x.strip().strip("'\"") for x in rest.strip("[]").split(",") if x.strip()]
                on = False
            continue
        if on:
            m = re.match(r"\s*-\s*(.+)$", ln)
            if not m:
                on = False
                continue
            out.append(m.group(1).strip().strip("'\""))
    return out


def expand_braces(glob: str) -> list[str]:
    """**/*.{ts,tsx} -> **/*.ts, **/*.tsx (comma lists can't hold braces)."""
    m = re.search(r"\{([^{}]*)\}", glob)
    if not m:
        return [glob]
    out = []
    for alt in m.group(1).split(","):
        out += expand_braces(glob[:m.start()] + alt + glob[m.end():])
    return out


def globs_of(lines: list[str]) -> list[str]:
    out: list[str] = []
    for g in front_list(lines, "paths"):
        for e in expand_braces(g):
            if e not in out:
                out.append(e)
    return out


def agent_blocks(text: str, keep: str) -> str:
    """Keep <!-- agent:KEEP --> … <!-- /agent --> blocks (unwrapped), drop the other agent's."""
    def sub(m: re.Match) -> str:
        return m.group(2) if m.group(1) == keep else ""
    text = re.sub(r"<!-- agent:(\w+) -->\n(.*?)<!-- /agent -->\n", sub, text, flags=re.S)
    return text


def neutral(text: str, target: str) -> str:
    for a, b in NEUTRAL_PATHS:
        text = text.replace(a, b)
    if target in AGENT_DIRS:
        text = text.replace(".claude/agents/", AGENT_DIRS[target])
    return text


def body_after_marker(body: str) -> tuple[str, str]:
    """The harness:managed marker line (right after the frontmatter) and the body after it."""
    first, _, rest = body.partition("\n")
    if MARK in first:
        return first, rest
    return "", body


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_core(logical: str) -> bool:
    return logical.startswith("core:")


def render_rule(kind: str, text: str, logical: str, target: str) -> str:
    front, body = split_front(text)
    body = agent_blocks(body, "other") if is_core(logical) else body
    marker, rest = body_after_marker(neutral(body, target))
    title = next((ln[2:].strip() for ln in rest.split("\n") if ln.startswith("# ")), logical.split(":", 1)[1])
    globs = globs_of(front)
    head = []
    if kind == "mdc":
        head = [f"description: {yaml_str(title)}"]
        head += ["alwaysApply: true"] if not globs else [f"globs: {','.join(globs)}", "alwaysApply: false"]
    elif kind == "instructions":
        head = [f"applyTo: {yaml_str(','.join(globs) if globs else '**')}"]
    elif kind == "ag-rule":
        head = ["trigger: always_on"] if not globs else ["trigger: glob", f"globs: {yaml_str(', '.join(globs))}"]
        head.append(f"description: {yaml_str(title)}")
    out = "---\n" + "\n".join(head) + "\n---\n"
    if marker:
        out += marker + "\n"
    return out + rest


def render_agent(target: str, text: str) -> str:
    front, body = split_front(text)
    marker, rest = body_after_marker(neutral(body, target))
    name = front_scalar(front, "name")
    desc = front_scalar(front, "description")
    tools = [t.strip() for t in front_scalar(front, "tools").split(",") if t.strip()]
    if target == "codex":
        mark = marker.replace("<!--", "#").replace("-->", "").strip() if marker else ""
        esc = rest.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        return (f"{mark}\n" if mark else "") + f"name = {yaml_str(name)}\ndescription = {yaml_str(desc)}\n" \
            f'developer_instructions = """\n{esc}"""\n'
    head = [f"name: {name}", f"description: {yaml_str(desc)}"]
    if target in TOOLS:
        mapped: list[str] = []
        for t in tools:
            for m in TOOLS[target].get(t, []):
                if m not in mapped:
                    mapped.append(m)
        head.append("tools: [" + ", ".join(yaml_str(m) for m in mapped) + "]")
    elif target == "cursor" and not ({"Edit", "Write"} & set(tools)):
        head.append("readonly: true")
    out = "---\n" + "\n".join(head) + "\n---\n"
    if marker:
        out += marker + "\n"
    return out + rest


def render(renderer: str, target: str, path: Path, logical: str) -> None:
    text = path.read_text(encoding="utf-8")
    if renderer == "claude-core":
        text = agent_blocks(text, "claude")
    elif renderer == "paths":
        text = neutral(text, target)
    elif renderer == "core":
        text = neutral(agent_blocks(text, "other"), target)
    elif renderer in ("mdc", "instructions", "ag-rule"):
        text = render_rule(renderer, text, logical, target)
    elif renderer.endswith("-agent"):
        text = render_agent(renderer[: -len("-agent")], text)
    else:
        raise ValueError(f"unknown renderer {renderer!r}")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: render.py <list.tsv>", file=sys.stderr)
        return 2
    for line in Path(argv[1]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        renderer, target, staged, logical = line.split("\t")[:4]
        try:
            render(renderer, target.split(",")[0], Path(staged), logical)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            print(f"[FAIL] render {renderer} {staged}: {e}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
