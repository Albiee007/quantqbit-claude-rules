#!/usr/bin/env python3
"""Merge harness base settings with project-owned settings.

Usage:
  settings_merge.py <settings.base.json> <settings.project.json|-> <out>
      Build the generated .claude/settings.json.
  settings_merge.py --migrate <existing settings.json> <settings.project.json|-> <out>
      First install into a project that already has a hand-written
      .claude/settings.json: fold it (plus any existing settings.project.json)
      into the project-owned settings.project.json, dropping harness-v0.x
      leftovers and a non-Opus "model" (each removal is reported on stderr).

Merge semantics (documented in INSTALL.md):
  * objects merge recursively
  * arrays are unioned (base order first, then new project items), so the
    harness deny-list and hooks can never be dropped by a project
  * scalars: project wins, EXCEPT locked keys (below), which keep the base value
  * top-level "model", if the project sets one, must be Opus-family

Exit codes: 0 ok, 2 policy violation / bad input.
"""
import json
import re
import sys

LOCKED = {
    ("env", "CLAUDE_CODE_SUBAGENT_MODEL"),
    ("env", "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"),
}

# Entries written by quantqbit-claude-rules v0.x templates that the harness
# replaces. Removed only during the one-time migration of a pre-existing file.
V0_HOOK_RE = re.compile(r"\.claude/hooks/(session-start-context|post-edit-lint)\.sh")
V0_DENIES = {"Edit(**/.env.*)", "Write(**/.env.*)"}


def fail(msg):
    sys.stderr.write("[FAIL] settings-merge: %s\n" % msg)
    sys.exit(2)


def note(msg):
    sys.stderr.write("[INFO] migrate: %s\n" % msg)


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


def is_opus(model):
    return "opus" in str(model).lower()


def strip_v0(settings):
    """Remove harness-v0.x hook commands and the over-broad .env.* denies."""
    perms = settings.get("permissions")
    if isinstance(perms, dict):
        for field in ("deny", "allow"):
            items = perms.get(field)
            if isinstance(items, list):
                kept = [i for i in items if not (field == "deny" and i in V0_DENIES)]
                for gone in [i for i in items if i not in kept]:
                    note("removed v0.x deny %s (it also blocked .env.example; the harness guard replaces it)" % gone)
                perms[field] = kept
    hooks = settings.get("hooks")
    if isinstance(hooks, dict):
        for event in list(hooks):
            groups = hooks[event]
            if not isinstance(groups, list):
                continue
            new_groups = []
            for group in groups:
                inner = group.get("hooks") if isinstance(group, dict) else None
                if isinstance(inner, list):
                    kept = [h for h in inner
                            if not (isinstance(h, dict) and V0_HOOK_RE.search(str(h.get("command", ""))))]
                    for gone in [h for h in inner if h not in kept]:
                        note("removed v0.x %s hook: %s" % (event, gone.get("command")))
                    if not kept:
                        continue
                    group = dict(group, hooks=kept)
                new_groups.append(group)
            if new_groups:
                hooks[event] = new_groups
            else:
                del hooks[event]
        if not hooks:
            del settings["hooks"]
    return settings


def main():
    args = sys.argv[1:]
    migrate = bool(args) and args[0] == "--migrate"
    if migrate:
        args = args[1:]
    if len(args) != 3:
        fail("usage: settings_merge.py [--migrate] <base> <project|-> <out>")
    base, proj = load(args[0]), load(args[1])

    if migrate:
        merged = strip_v0(merge(base, proj))
        model = merged.get("model")
        if model is not None and not is_opus(model):
            note('removed "model": "%s" (harness policy is Opus; a personal model choice belongs in '
                 '.claude/settings.local.json)' % model)
            del merged["model"]
    else:
        model = proj.get("model")
        if model is not None and not is_opus(model):
            fail('project settings set model "%s"; harness policy requires Opus '
                 '(a personal choice belongs in .claude/settings.local.json)' % model)
        merged = merge(base, proj)

    with open(args[2], "w", encoding="utf-8", newline="\n") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    main()
