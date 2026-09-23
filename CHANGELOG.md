# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/). For the harness:

- **Major:** layout or lock-format changes.
- **Minor:** new skills, rules or agents.
- **Patch:** content fixes.

Every entry has **Upgrade notes** for anything a project needs to act on.

## [1.0.1] - 2026-09-24

End-to-end verification (isolated plugin installs, a standalone clone, Windows PowerShell, a second developer on a CRLF checkout, and live headless Claude Code sessions) found the issues below. Everything listed was reproduced independently before it was fixed.

### Fixed
- **Plugin could not be installed** (blocker): `plugin.json` `repository` was an object; Claude Code requires a string. Also added `author`, a marketplace description, quoted command `argument-hint`s, and moved `version` to `plugin.json` only. `claude plugin validate --strict` now passes and runs in `validate-harness.sh`.
- **PowerShell entry points were broken** (blocker): the `.ps1` wrappers exported `MSYS_NO_PATHCONV=1`, so native `git.exe`/`python.exe` got unresolvable paths. This made `sync.ps1` fail on any project with a `settings.json`, silently ignore `--commit`, and skip the dirty-tree guard. All five wrappers now share one template and prefer Git for Windows' bash over WSL's. The bash scripts also clear an inherited `MSYS_NO_PATHCONV`.
- **CRLF scripts on Windows clones:** a harness-owned `.claude/.gitattributes` now pins `*.sh` and the lock to LF, so hooks keep working under WSL, Linux and containers. The doctor flags CRLF scripts. `session-start.sh` now tolerates a CRLF lock.
- **Non-deterministic lock:** the `source` line now always holds the canonical upstream URL. It no longer records the syncing checkout's remote (local paths, SSH forms and tokens leaked into committed locks and churned between developers). The bootstrap only trusts https URLs from a lock.
- **Silent downgrades:** sync refuses a source older than the installed harness (`--allow-downgrade` to override). The doctor compares versions by order and finds the installed plugin copy.
- **Settings flows:**
  - Editing `settings.project.json` and re-syncing is no longer refused by the dirty-tree guard, and `--commit` includes it.
  - A pre-existing `settings.json` is merged into an existing `settings.project.json` instead of conflicting.
  - v0.x hook entries, the over-broad `.env.*` denies and a non-Opus `model` are dropped during that one-time migration, each with a notice.
- **`--profiles` did not persist:** it now updates `profiles=` in `harness.config` inside the same transaction.
- **`.env` guard gaps:** the guard now covers Grep and PowerShell, matches case-insensitively, and catches `.env*` globs and comma/paren boundaries. It no longer blocks exclusion arguments (`--exclude=.env*`) or read-only metadata commands (`ls`, `git check-ignore`), which had pushed the model toward riskier commands. Deny rules were added for `.env.staging`, `.env.development` and `.env.test`.
- **Sub-agents never got checklists:** checklist dedupe was keyed on the session only. It is now keyed per agent context.
- **Checklists arrived too late:** a checklist attached to a write came after the content was composed. The first UI or SEO write in each agent context is now denied once, with the checklist and the skill to load, and the retry is allowed. Set `checklists=inform` in `harness.config` to only inform.
- **`--theirs` lost data:** overwritten files are now kept under `.claude/harness/.backup/<time>/` (gitignored).
- **Smaller fixes:**
  - The generated settings `file_version` no longer churns.
  - Uninstall removes empty harness dirs and lists the project files it leaves.
  - `init.sh` no longer leaks its staging dir or passes `--allow-dirty`, and it stamps lint configs only for detected stacks.
  - The Makefile recipe works from its own directory.
  - `check-url.sh --help` works.
  - `post-edit-lint` handles Windows paths.
  - Old dedupe markers are pruned.
  - `additionalDirectories` was removed.
  - The bootstrap accepts `--source=`/`--ref=`, reports a missing tag cleanly (exit 2), and adds `--remote`.
  - The Python lookup also tries the Windows `py -3` launcher.

### Changed
- Docs: a new [GETTING-STARTED.md](./GETTING-STARTED.md), corrected install commands, prerequisites per OS, private-repo access, measured hook latency (about 80–300 ms per hook on Windows), and conflict semantics (`--keep` applies only to CONFLICT-MODIFIED).

### Upgrade notes
- **Projects on v1.0.0:** run `bash .claude/harness/bin/harness-sync.sh --dry-run`, then `--commit`.
  - Expect every managed file to update once (the marker text changed to plain ASCII) and a new `.claude/.gitattributes`.
  - If a project has its own `.claude/.gitattributes`, it conflicts. Merge its rules into a root `.gitattributes`, then re-sync.
- **Windows clones made before this release:** re-checkout once to pick up LF scripts: `git rm -r --cached -q .claude && git checkout -- .claude`.
- **Projects migrated from v0.x under 1.0.0:** remove the v0.x `hooks` entries and the `Edit/Write(**/.env.*)` denies from `.claude/settings.project.json`, delete `.claude/hooks/` and the old `.claude/rules/{bash,ansible,compose,terraform}.md`, then re-sync. The doctor lists these leftovers.

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
