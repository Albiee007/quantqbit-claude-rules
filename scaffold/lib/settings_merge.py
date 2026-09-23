#!/usr/bin/env python3
"""Merge harness base settings with project-owned settings.

Usage: settings_merge.py <settings.base.json> <settings.project.json|-> <out>

Semantics (documented in harness/README.md):
  * objects merge recursively
  * arrays are unioned (base order first, then new project items), so the
    harness deny-list and hooks can never be dropped by a project
  * scalars: project wins, EXCEPT locked keys (below), which keep the base value
  * top-level "model", if the project sets one, must be Opus-family

Exit codes: 0 ok, 2 policy violation / bad input.
"""
import json
import sys

LOCKED = {
    ("env", "CLAUDE_CODE_SUBAGENT_MODEL"),
    ("env", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"),
}


def fail(msg):
    sys.stderr.write("[FAIL] settings-merge: %s\n" % msg)
    sys.exit(2)


def load(path):
    if path == "-":
        return {}
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        fail("cannot parse %s: %s" % (path, exc))
    if not isinstance(data, dict):
        fail("%s must contain a JSON object" % path)
    return data


def key(item):
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def merge(base, proj, path=()):
    if isinstance(base, dict) and isinstance(proj, dict):
        out = dict(base)
        for k, v in proj.items():
            sub = path + (k,)
            if sub in LOCKED:
                continue
            out[k] = merge(base[k], v, sub) if k in base else v
        return out
    if isinstance(base, list) and isinstance(proj, list):
        seen = {key(i) for i in base}
        out = list(base)
        for item in proj:
            if key(item) not in seen:
                seen.add(key(item))
                out.append(item)
        return out
    if isinstance(base, (dict, list)) and not isinstance(proj, type(base)):
        fail("type mismatch at %s: project cannot replace %s with %s"
             % (".".join(path) or "<root>", type(base).__name__, type(proj).__name__))
    return proj


def main():
    if len(sys.argv) != 4:
        fail("usage: settings_merge.py <base> <project|-> <out>")
    base, proj = load(sys.argv[1]), load(sys.argv[2])
    model = proj.get("model")
    if model is not None and "opus" not in str(model).lower():
        fail('project settings set model "%s"; harness policy requires Opus' % model)
    merged = merge(base, proj)
    with open(sys.argv[3], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
