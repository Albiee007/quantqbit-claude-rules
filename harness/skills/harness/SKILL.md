---
name: harness
description: Explains and operates the vendored agent harness in this project — ownership rules, how to override harness rules, how to check health (doctor) and how to update (sync). Use when the user asks about harness rules, wants to change or override a harness rule/skill/agent/setting, sees a harness:managed file, a harness lock conflict, a kept-local warning, or asks to sync/update/check the harness.
---

# Agent harness (in this project)

The harness is vendored into this repo and committed to git. `.claude/harness/README.md` has the full ownership table.

## Changing behaviour: never edit harness-managed files
| Want to… | Do this |
|---|---|
| Add or override a rule | Create `.claude/rules/project/<topic>.md`. Use `paths:` frontmatter to scope it to files. |
| Change permissions, env or hooks for the team | Edit `.claude/settings.project.json`, then run sync. `settings.json` is regenerated. |
| Change profiles or verification commands | Edit `.claude/harness.config`, then run sync. |
| Add an agent or skill | Use a new name under `.claude/agents/` or `.claude/skills/`. The harness names are reserved. |
| Personal preferences | Put them in `CLAUDE.local.md` or `.claude/settings.local.json` (gitignored). |

Precedence: project rules and `CLAUDE.md` override harness rules. The exceptions are `.env` and secrets handling, the Opus policy and the accessibility minimums, which cannot be overridden.

## Commands
```bash
bash .claude/harness/bin/harness-doctor.sh            # health: modified / missing / kept-local / stale
bash .claude/harness/bin/harness-sync.sh --dry-run    # preview an update
bash .claude/harness/bin/harness-sync.sh --commit     # update and commit on the current branch
```
On Windows PowerShell, use the matching `.ps1` scripts. They need Git Bash.

## Resolving problems
- **Doctor says modified:**
  1. Move the intent of the local edit into `.claude/rules/project/`.
  2. Run `harness-sync.sh --theirs`. The old copy is saved under `.claude/harness/.backup/`.
- **CONFLICT-UNMANAGED:** a project file uses a reserved harness name (agents `explorer`, `implementor`, `infra-implementor`, `verifier`, `reviewer`; skills `coding-standards`, `design-patterns`, `ui-ux`, `seo`, `harness`). Rename it. `--keep` does not apply here.
- **A write was denied with "falls under a mandatory skill":** read the named `.claude/skills/<skill>/SKILL.md`, apply its checklist, and retry the same write. It is allowed the second time. Set `checklists=inform` in `.claude/harness.config` to disable the gate.
- **"older than the installed" refusal:** the source is stale. Update the plugin (`claude plugin marketplace update quantqbit`, then `claude plugin update quantqbit-claude-rules@quantqbit`) or `git pull` your clone, then sync again.
- **Lock merge conflict:** keep either side (`git checkout --ours .claude/harness/lock`), then run sync. Sync re-derives the lock.
- **Sync exit 1:** nothing was written. Read the CONFLICT lines and choose `--keep` or `--theirs` with the user.
- **Sync exit 2:** the sync was rolled back automatically. Report the error.
