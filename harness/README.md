# QuantQbit Agent Harness (vendored)

This project vendors the QuantQbit agent harness: shared agent rules, skills, agents and hooks, committed to git so every developer and every Claude Code session gets the same behaviour.

## Who owns what

| Path | Owner | May I edit it? |
|---|---|---|
| `.claude/rules/harness/*` | harness | No. Override in `.claude/rules/project/` |
| `.claude/skills/{coding-standards,design-patterns,ui-ux,seo,harness}/` | harness | No. Add your own skills under other names |
| `.claude/agents/{explorer,implementor,infra-implementor,reviewer,verifier}.md` | harness | No. Add your own agents under other names |
| `.claude/harness/*` (hooks, snippets, bin, lock, this README), `.claude/.gitattributes` | harness | No |
| `.claude/settings.json` | **generated** | No. Edit `.claude/settings.project.json` instead, then re-sync |
| `.claude/settings.project.json` | project | Yes: team-shared permissions, env and hooks |
| `.claude/harness.config` | project | Yes: profiles and verification commands |
| `.claude/rules/project/*` | project | Yes: project rules and overrides |
| `CLAUDE.md`, `AGENTS.md`, `AI_RULES.md` | project | Yes. The harness never touches them |
| `CLAUDE.local.md`, `.claude/settings.local.json` | you | Personal. Keep them gitignored |

Harness files carry a `harness:managed vX.Y.Z` marker. `.claude/harness/lock` records the version and content hash of every harness file, so local edits and stale files are detected, not silently overwritten.

## Commands

```bash
bash .claude/harness/bin/harness-doctor.sh          # health check: modified / missing / stale files
bash .claude/harness/bin/harness-sync.sh --dry-run  # preview an update
bash .claude/harness/bin/harness-sync.sh --commit   # update to the latest harness and commit
```

In Claude Code you can also ask "sync the harness" (the in-project `harness` skill runs the commands above), or use the plugin's `/quantqbit-claude-rules:harness-install` if the plugin is installed.

The sync uses the newest local harness source it finds (your installed plugin, `$HARNESS_HOME`, or `~/.local/share/quantqbit-claude-rules`), else clones the upstream repo. `--ref vX.Y.Z` pins a release; `--remote` takes the latest upstream.

## Why it is merge- and conflict-safe

- Harness files and project files never share a file. Your edits live in project-owned files, so a harness update cannot overwrite them and cannot conflict with them.
- A sync is all-or-nothing:
  1. It builds and validates the new state in a staging folder.
  2. It applies the files one by one, writing a journal as it goes.
  3. If anything fails, it rolls every change back.
  4. It writes the lock last.
- A harness file edited locally stops the sync and nothing is written. You then choose `--keep` or `--theirs`.
- The lock is deterministic: no timestamps. Two developers who sync the same version produce identical bytes. If the lock ever conflicts in a merge, keep either side and re-run sync.
