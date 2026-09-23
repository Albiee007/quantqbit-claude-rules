# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/). For the harness:

- **Major:** layout or lock-format changes.
- **Minor:** new skills, rules or agents.
- **Patch:** content fixes.

Every entry has **Upgrade notes** for anything a project needs to act on.

## [1.0.0] - 2026-09-23

### Added
- **Vendored agent harness** (`harness/`), synced into each project's `.claude/` by `scaffold/sync.sh`, so rules are committed to git and shared with every developer.
  - **Transactional:** each sync stages, validates, then applies with a journal. It rolls back on any failure and writes the lock last.
  - **Conflict-safe:**
    - Harness files and project files never share a file.
    - The lock is deterministic (no timestamps), and hashes ignore CRLF differences.
    - A locally modified harness file aborts the sync until you choose `--keep` or `--theirs`.
  - **Profiles:** `web`, `mobile`, `backend`, `infra`, auto-detected on first install.
  - **Settings:** `settings.json` is generated from the harness base plus the project-owned `settings.project.json`.
  - **Tools:** `harness-doctor` (health check) and a `harness-sync` bootstrap, each as `.sh` and `.ps1`.
- **Core rules** (`00-core.md`, always loaded): precedence, Opus-only policy, plan mode, orchestration table, mandatory-skill routing, verification gates, cross-platform scripts, `.env` protection, git branch policy, YAGNI.
- **Mandatory skills:**
  - `coding-standards`: SOLID, naming, errors, testing, OWASP Top 10:2025 and ASVS 5.0, review checklist, language notes.
  - `design-patterns`: a decision gate, all 23 GoF patterns with TS examples, architectural patterns, anti-patterns.
  - `ui-ux`: all 30 Laws of UX, Nielsen's 10 heuristics, WCAG 2.2 AA, Gestalt, DTCG 2025.10 tokens, Material 3, Apple HIG, a review rubric.
  - `seo`: our own synthesis covering technical SEO, content and E-E-A-T, schema, Core Web Vitals, GEO/AI search, hreflang, local, images, sitemaps, e-commerce, programmatic SEO, playbooks, a 0–100 audit score and `check-url.sh`.
  - `harness`: in-project help for the harness itself.
- **Path-scoped rules:** coding, tests, security, ui-ux, seo, bash, powershell (new), ansible, compose (with a Dockerfile section), terraform.
- **Agents (all Opus):** `explorer`, `implementor`, `infra-implementor`, `verifier`, `reviewer` (lenses: code, patterns, ux, seo, security).
- **Hooks (pure bash, about 80 ms):**
  - `guard`: blocks non-Opus sub-agents and real `.env` files, while allowing `.env.example` and similar templates.
  - `prompt-router` and `file-context`: inject the mandatory checklists.
  - `session-start`: shows a harness summary and health warnings.
  - `post-edit-lint`: lints edited files.
- **Enforced Opus:** via `CLAUDE_CODE_SUBAGENT_MODEL=opus`, `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`, `model: opus` on every agent, and the guard hook.
- **Plugin skills:** `harness-install` and `project-scaffold`. Also a `marketplace.json`.
- **Release tooling:**
  - `scaffold/lib/release.sh` generates the manifest, with per-file versions.
  - `scaffold/lib/validate-harness.sh` checks model policy, frontmatter, size budgets, hygiene, links and release consistency.
  - `tests/` holds the sync scenarios, hook tests and validator tests, run in CI on Linux, macOS and Windows.

### Changed
- **`/init-project-rules`** now stamps only lint tooling (under `CODE_SUBDIR`, write-if-absent), then installs the harness. Opt-in deny rules go into `settings.project.json`.
- **`/init-project-scaffold`** never overwrites `CLAUDE.md`, `AI_RULES.md` or `.mcp.json`, and skips `CLAUDE.md` when an `AGENTS.md` exists. The shared `CLAUDE.md` template no longer repeats the harness core rules.
- **Stamp manifests** use relative paths plus content hashes. `--uninstall` keeps files that were edited after stamping.
- **Agent roster:** the old agents were consolidated. `infra-explorer` became `explorer`; `ansible-`, `compose-` and `script-implementor` became `infra-implementor`; `lint-runner` became `verifier`.

### Fixed
- The `CLAUDE.md` collision between the two commands.
- Lint files were landing at the repo root instead of `CODE_SUBDIR`.
- The MCP config was written to `.claude/mcp.json`, which Claude Code ignores. It is now the root `.mcp.json`.
- A deny rule on `.env.*` also blocked `.env.example` edits, because deny rules take precedence over allow rules.

### Removed
- Stamped `.claude/hooks/*`, `.claude/rules/*` and the `CLAUDE.md` / `settings.json` templates. The harness supersedes them.

### Upgrade notes
- Projects stamped with v0.x: run `bash scaffold/sync.sh --target <project> --dry-run`.
  - Old `.claude/rules/*.md` and `.claude/hooks/*` files stay in place as project-owned files. Delete them once the harness versions are in.
  - An existing `.claude/settings.json` is moved automatically to `.claude/settings.project.json`, and `settings.json` becomes generated.

## [0.2.0]
- Initial public release: `/init-project-rules` and `/init-project-scaffold` (backend / frontend / mobile / android).
