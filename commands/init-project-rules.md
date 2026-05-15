---
description: Scaffold project agent-rules + lint configs into the current workspace
argument-hint: [--force] [--non-interactive]
---

# /init-project-rules

Initialise the agent-rules scaffold from this plugin inside the user's current project.

## What this command does

When invoked, run the scaffold script from the user's CURRENT working directory (do **not** `cd` elsewhere first):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scaffold/init.sh" $ARGUMENTS
```

- `${CLAUDE_PLUGIN_ROOT}` is the documented Claude Code variable for the plugin's installed root directory (see https://code.claude.com/docs/en/plugins-reference under "Environment variables"). It expands automatically — do not substitute it manually.
- `$ARGUMENTS` MUST be passed through verbatim so users can invoke `/init-project-rules --force`, `/init-project-rules --non-interactive`, or both.

## Safety guard

Without `--force`, the script will refuse to run if either of these already exist in the workspace:

- `CLAUDE.md`
- `.claude/settings.json`

This is **intentional**. It prevents accidental overwrite of an existing agent contract. If the user genuinely wants to regenerate, ask them to confirm and re-run with `--force`.

## What the script produces

The script will:

1. **Auto-detect installed stacks** by scanning the workspace — bash, ansible, compose, terraform — and tailor the generated rules + lint configs accordingly.
2. **Prompt for project metadata** (interactively unless `--non-interactive` is passed):
   - Project name
   - Code subdirectory (the path inside the repo that holds the code being linted)
   - Optional opt-in deny patterns for the agent permissions file
3. **Stamp templates** into the workspace at:
   - `CLAUDE.md`
   - `.claude/settings.json`
   - `.claude/hooks/`
   - `.claude/rules/`
   - `.editorconfig`
   - `<subdir>/.shellcheckrc`
   - `<subdir>/.yamllint`
   - `<subdir>/.ansible-lint`
   - `<subdir>/scripts/lint.sh`
   - `<subdir>/Makefile`
4. **Validate the generated files** — `bash -n` on shell scripts and a JSON parse on `settings.json` — and abort with a clear error if anything is malformed.

## After generation

The scaffolded assets are **starter templates, not frozen contracts**. The user is encouraged to read through and edit `CLAUDE.md`, the rule files under `.claude/rules/`, and the lint configs to match the project's specific conventions. The defaults are sensible but not opinionated about your domain.

## Reference

For the full list of prompts, environment variable overrides, and per-file customisation notes, point the user at `INSTALL.md` at the root of this rules package.
