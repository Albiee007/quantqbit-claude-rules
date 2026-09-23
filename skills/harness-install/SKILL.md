---
name: harness-install
description: Installs, updates, previews or removes the QuantQbit agent harness (core rules, mandatory skills, Opus agents, hooks, generated settings) in the current project using the plugin's transactional sync. Use when the user asks to install, set up, add, update, upgrade, sync, preview or uninstall the harness, "agent rules" or "claude rules" in a repo.
argument-hint: "[--dry-run|--diff|--commit|--keep|--theirs|--profiles=web,mobile,backend,infra|--uninstall]"
---

# Harness install / update (plugin)

This skill runs the harness sync engine that ships with this plugin, against the user's current project.

## Steps
1. Confirm the target is the project root (usually the current working directory, at the git top level).
2. Preview first. Always do this unless the user already asked for a specific mode:
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scaffold/sync.sh" --target "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" --dry-run
   ```
   Show the user the plan: the operations, detected profiles, and any seeds.
3. Apply with the user's flags (`$ARGUMENTS`). Add `--commit` only if the user wants a commit. It commits explicit paths on the current branch and never pushes.
   ```bash
   bash "${CLAUDE_PLUGIN_ROOT}/scaffold/sync.sh" --target "<root>" $ARGUMENTS
   ```
4. Report the exit code, the files changed, and anything `kept-local`, orphaned or migrated.

## Exit codes and what to do
- `0`: done.
- `1`: nothing was written. Explain the cause, then let the user choose:
  - **CONFLICT-MODIFIED:** a harness file was edited locally. Recommend moving the change into `.claude/rules/project/`, then re-running with `--theirs`. `--keep` keeps the local version (doctor keeps flagging it).
  - **CONFLICT-UNMANAGED:** a project file sits at a harness path. Rename it, or use `--theirs`.
  - **Dirty tree:** commit or stash the changes under the harness paths, or pass `--allow-dirty`.
- `2`: error. Everything was rolled back automatically. Show the error.

## Never
- Never edit files under `.claude/rules/harness/`, `.claude/harness/`, or the harness skills and agents by hand to "fix" a sync.
- Never pass `--theirs` or `--allow-dirty` without the user agreeing.
- Never push. Never touch `.env` files.
