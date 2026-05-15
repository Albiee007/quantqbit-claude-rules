# quantqbit-claude-rules

A two-layer Claude Code scaffolder. The **operational layer** ships custom sub-agents, hooks, deterministic guard-rails, and lint configs via `/init-project-rules`. The **project-skeleton layer** stamps buildable per-platform starters (backend / frontend / mobile / android) with strict feature-organised folder discipline via `/init-project-scaffold`. The two compose: run `/init-project-rules` first to get `.claude/`, then `/init-project-scaffold` to stamp the app skeleton on top.

## What you get

### `/init-project-rules` — operational layer

- Custom sub-agents (`infra-explorer`, `ansible-implementor`, `compose-implementor`, `script-implementor`, `lint-runner`) for read-only exploration, ansible/compose/script implementation, and lint runs.
- Path-scoped rule files (`bash.md`, `ansible.md`, `compose.md`, `terraform.md`) that load only when matching files are touched.
- Deterministic `permissions.deny` covering `.env` writes, `git add -A`, and `rm -rf /` by default; `terraform destroy`, `docker system prune`, and push-to-main are opt-in.
- `SessionStart` and `PostToolUse` hooks for context injection and per-edit lint.
- Standard lint configs (`.editorconfig`, `.shellcheckrc`, `.yamllint`, `.ansible-lint`) plus a unified `lint.sh` runner.

### `/init-project-scaffold` — project skeleton layer (v0.2.0)

- Buildable starters for four platforms: **backend** (Node + TS + Express + Mongoose + pg), **frontend** (React + Vite + TS), **mobile** (React Native + Expo + TS), **android** (Kotlin + Compose + Retrofit).
- Strict feature-organised folder discipline — every feature has the same fixed set of subfolders. Files live inside, never at the feature root.
- File-size soft cap at 500 lines, **warning-only** by default (upgradable with `--strict`).
- Naming conventions enforced via suffixes (`*.routes.*`, `*.controller.*`, `*.service.*`, etc.).
- One working example feature per platform (`/healthz` on backend/frontend, `home` on mobile/android) — intentionally tiny.
- Shared `docs/` template (system-architecture, api, data-models, business-flows, integrations, background-jobs, repo-structure, runbook) across all platforms.

## Install

Two install paths are supported — a Claude Code plugin (recommended once you have a private package URL) and a standalone scaffolder for workspaces that don't want the plugin layer.

**Plugin (recommended):**

```bash
claude plugin install <YOUR-GIT-URL-HERE>

# then, inside any workspace, run them in order:
/init-project-rules         # operational layer (.claude/, hooks, lint)
/init-project-scaffold      # project skeleton (per-platform buildable starter)
```

**Standalone:**

```bash
git clone <your-private-url> ~/.local/share/quantqbit-claude-rules

# operational layer:
bash ~/.local/share/quantqbit-claude-rules/scaffold/init.sh

# project skeleton:
bash ~/.local/share/quantqbit-claude-rules/scaffold/init-scaffold.sh \
  --platform=backend  # or frontend | mobile | android
```

The curl-pipe-bash one-liner (`bash <(curl -fsSL .../init.sh)`) does **not** work for this scaffolder: `init.sh` resolves its sibling `lib/` and `templates/` directories from `${BASH_SOURCE[0]}`, which under process substitution becomes `/dev/fd/63` — so the script can't find its own dependencies. Clone first, then run.

Replace `<YOUR-GIT-URL-HERE>` and `<your-private-url>` with your private GitLab/GitHub URL after publishing.

## Quick start

A typical interactive run:

```text
$ /init-project-rules
Project name? MyApp
Code subdir? [./] ./infra/
Block destructive ops (terraform destroy, docker system prune)? [y/N] y
Block git push to main/master? [y/N] n
Stamped CLAUDE.md, .claude/, lint configs, and lint.sh into ./infra/. Detected: bash, ansible, terraform.
```

## What gets installed

```text
<workspace>/
├── CLAUDE.md
├── .claude/
│   ├── settings.json
│   ├── hooks/
│   │   ├── session-start-context.sh
│   │   └── post-edit-lint.sh
│   └── rules/
│       ├── bash.md
│       ├── ansible.md
│       ├── compose.md
│       └── terraform.md
├── .editorconfig
└── <code-subdir>/
    ├── .shellcheckrc
    ├── .yamllint
    ├── .ansible-lint
    ├── scripts/lint.sh
    └── Makefile
```

## Stack detection

The scaffolder auto-detects bash, ansible, docker compose, and terraform from files present in the target workspace. Rule files and lint config sections are emitted only for stacks it detects, so a pure-bash project doesn't get terraform clutter and an ansible-only project doesn't get a compose rule file.

## Status

**v0.2.0** — adds `/init-project-scaffold` for buildable per-platform starters (backend / frontend / mobile / android) on top of the existing `/init-project-rules` operational layer.

- v0.1.1: `/init-project-rules` tested across three independent projects.
- v0.2.0: `/init-project-scaffold` tested with end-to-end buildable verification on each of the four platforms.

See [INSTALL.md](./INSTALL.md) for prompts, substitution variables, env overrides, and customisation guidance for both commands.

## License

MIT. See [LICENSE](./LICENSE).
