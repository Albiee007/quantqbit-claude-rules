# quantqbit-claude-rules

**QuantQbit agent harness for Claude Code.** One source of truth for agent rules, mandatory skills, agents and hooks. It is **vendored into each project's `.claude/` directory and committed to git**, so every developer and every session behaves the same. Updates are transactional and never conflict with project-owned files.

## What every project gets

| Layer | Contents |
|---|---|
| **Core rules** (always loaded, ≤150 lines) | Precedence, Opus-only sub-agents, plan mode, the orchestration table, mandatory-skill routing, verification gates, cross-platform scripts, `.env` protection, git branch policy, YAGNI |
| **Mandatory skills** | **coding-standards**: SOLID, naming, errors, testing, OWASP Top 10:2025, review checklist · **design-patterns**: a decision gate plus all 23 GoF patterns with examples, architectural patterns, anti-patterns · **ui-ux**: 30 Laws of UX, Nielsen heuristics, WCAG 2.2 AA, Gestalt, DTCG tokens, Material 3, Apple HIG · **seo**: technical SEO, E-E-A-T, schema, Core Web Vitals, AI search (GEO), hreflang, local, a 0–100 audit score |
| **Path-scoped rules** | coding, tests, security, ui-ux, seo, bash, powershell, ansible, compose/Dockerfile, terraform |
| **Agents** (all Opus) | `explorer` → `implementor` / `infra-implementor` → `verifier` → `reviewer` (lenses: code, patterns, ux, seo, security) |
| **Hooks** (pure bash, ~80 ms) | `guard` (enforces Opus, blocks real `.env` files), `prompt-router` and `file-context` (inject mandatory checklists), `session-start`, `post-edit-lint` |
| **Settings** | Generated from the harness base plus the project's own `settings.project.json` |

## Why it is safe to share through git

- **Separate ownership.** Harness files (`.claude/rules/harness/`, harness skills, agents, `.claude/harness/`) and project files (`CLAUDE.md`, `AGENTS.md`, `.claude/rules/project/`, `settings.project.json`, `harness.config`) never share a file.
- **Transactional sync.** The new state is staged and validated, applied with a journal, and fully rolled back on any failure. The lock is written last.
- **Drift detection.** `.claude/harness/lock` records the version and content hash of every file. Local edits abort the sync (you choose `--keep` or `--theirs`), and `harness-doctor` reports stale, modified or missing files.
- **Deterministic lock.** No timestamps, and hashes ignore CRLF differences. The same version produces identical bytes on every machine.

## Quick start

```bash
# Plugin
/plugin marketplace add Albiee007/quantqbit-claude-rules
/plugin install quantqbit-claude-rules@quantqbit
/init-project-rules            # lint tooling + harness, or just ask: "install the harness"
/init-project-scaffold         # optional: buildable backend / frontend / mobile / android starter

# Without the plugin
git clone https://github.com/Albiee007/quantqbit-claude-rules ~/.local/share/quantqbit-claude-rules
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target . --dry-run
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target . --commit
```

Inside a project that already has the harness:

```bash
bash .claude/harness/bin/harness-doctor.sh           # health check
bash .claude/harness/bin/harness-sync.sh --commit    # update to the latest harness
```

PowerShell users: every entry point has a `.ps1` twin, which uses Git Bash.

## Repository layout

```text
harness/                 SOURCE OF TRUTH (vendored into projects)
  core/00-core.md          always-loaded rules
  rules/                   path-scoped rules
  skills/                  coding-standards, design-patterns, ui-ux, seo, harness
  agents/                  explorer, implementor, infra-implementor, verifier, reviewer
  hooks/ snippets/ bin/    enforcement hooks, injected checklists, doctor + sync bootstrap
  settings.base.json       base settings (Opus force, deny rules, hooks)
  profiles.tsv             which files ship to which profile (web, mobile, backend, infra)
  manifest.tsv             generated: per-file dest, version, hash, profiles
scaffold/
  sync.sh / sync.ps1       transactional sync engine
  init.sh / init.ps1       /init-project-rules: lint tooling + harness
  init-scaffold.sh (+ps1)  /init-project-scaffold: per-platform starters
  lib/                     release.sh, validate-harness.sh, settings_merge.py, renderers
skills/                  plugin skills: harness-install, project-scaffold
commands/                /init-project-rules, /init-project-scaffold
tests/                   sync, hooks and validator test suites
```

## Development

```bash
bash scaffold/lib/release.sh            # regenerate the manifest after editing harness/
bash scaffold/lib/validate-harness.sh   # model policy, frontmatter, size budgets, hygiene, links, versions
bash tests/hooks.test.sh; bash tests/validate.test.sh; bash tests/sync.test.sh
```

CI runs these tests on Ubuntu, macOS and Windows (`.github/workflows/validate.yml`). See [INSTALL.md](./INSTALL.md) for everything else, [CHANGELOG.md](./CHANGELOG.md) for versions and upgrade notes, and [CREDITS.md](./CREDITS.md) for sources.

## License

MIT. See [LICENSE](./LICENSE).
