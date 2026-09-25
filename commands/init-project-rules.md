---
description: Install lint tooling and the QuantQbit agent harness (rules, skills, agents, hooks) into the current project
argument-hint: "[--non-interactive] [--project-name=NAME] [--code-subdir=DIR] [--force] [--no-harness]"
---

# /init-project-rules

Set up the current project in two steps:

1. **Lint tooling**, tailored to the detected stacks: `.editorconfig`, `.shellcheckrc`, `.yamllint`, `.ansible-lint`, `scripts/lint.sh` and `Makefile`, placed under the code subdirectory. Existing files are kept unless `--force` is passed, in which case they are backed up first.
2. **The agent harness**, installed transactionally. It adds the core rules, the mandatory skills (coding-standards, design-patterns, ui-ux, seo), the Opus agents (plus six store and brand agents with their skills in mobile projects), the hooks and a generated `settings.json`.

## Run

From the user's CURRENT working directory (do **not** `cd` elsewhere first):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scaffold/init.sh" $ARGUMENTS
```

Pass `$ARGUMENTS` through verbatim. `${CLAUDE_PLUGIN_ROOT}` expands automatically.

## Afterwards

- Show the user the plan the harness sync printed and the files it changed.
- Existing `CLAUDE.md`, `AGENTS.md` and `AI_RULES.md` are left untouched. When neither `CLAUDE.md` nor `AGENTS.md` exists, a `CLAUDE.md` stub is seeded.
- If the sync reports conflicts (exit 1), nothing was written. Explain what `CONFLICT-*` means. For CONFLICT-MODIFIED the user chooses `--keep` or `--theirs`; for CONFLICT-UNMANAGED they rename their file (reserved harness name) or use `--theirs` (their copy is saved under `.claude/harness/.backup/`). Re-run with `bash "${CLAUDE_PLUGIN_ROOT}/scaffold/sync.sh" --target <root> <flag>`.
- Suggest committing the result on the current branch, staging explicit paths only. `sync.sh --commit` does this.

To update the harness later, use the `harness-install` skill, or run `bash .claude/harness/bin/harness-sync.sh`. See `harness/README.md` and `INSTALL.md`.
