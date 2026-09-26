---
description: Scaffold a buildable starter for backend / frontend / mobile / android with the strict feature-organised folder layout
argument-hint: "[--platform=backend|frontend|mobile|android] [--project-name=NAME] [--src-dir=DIR] [--api-version=vN] [--features=a,b,c] [--android-package=ID] [--with-i18n] [--with-auth] [--force] [--dry-run] [--uninstall] [--force-unlock] [--non-interactive]"
---

# /init-project-scaffold

Initialise a **buildable per-platform project starter** inside the user's current workspace. Companion to `/init-project-rules` — the two scaffolders compose:

1. `/init-project-rules` stamps lint tooling and installs the agent harness (`.claude/` rules, skills, agents, hooks).
2. `/init-project-scaffold` stamps the application skeleton (per-platform buildable starter).

Either order works. Project instruction files (`CLAUDE.md`, `AI_RULES.md`, `.mcp.json`) are write-if-absent: they are never overwritten, even with `--force`. `CLAUDE.md` is not created when an `AGENTS.md` exists.

## What this command does

When invoked, run the scaffold script from the user's CURRENT working directory (do **not** `cd` elsewhere first):

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scaffold/init-scaffold.sh" $ARGUMENTS
```

- `${CLAUDE_PLUGIN_ROOT}` is the documented Claude Code variable for the plugin's installed root directory. It expands automatically — do not substitute it manually.
- `$ARGUMENTS` MUST be passed through verbatim so users can invoke with any of the listed flags.

## Platforms supported (v1)

| Flag | Stack | Build verification |
| --- | --- | --- |
| `--platform=backend` | Node + TypeScript + Express + Mongoose + pg | `npm install && npm run build && npm test && curl /healthz` |
| `--platform=frontend` | React + Vite + TypeScript | `npm install && npm run build && npm test` |
| `--platform=mobile` | React Native + Expo + TypeScript | `npm install && npm run lint && npm test && npm run doctor && npm run native:prebuild` |
| `--platform=android` | Kotlin + Compose + Retrofit (no Hilt/Room — see Stack non-goals) | `./gradlew :app:assembleDebug :app:testDebugUnitTest ktlintCheck :app:lintDebug` |

If `--platform=` is omitted, the dispatcher auto-detects by sniffing `build.gradle.kts`, `app.json`/Expo, Vite config, or Express/Fastify deps. Empty dir → interactive prompt.

## Safety guard

The stamp is all or nothing. The starter is rendered and validated in a staging area first; if any existing file would be replaced, the script lists it, writes nothing and exits 1. Existing `README.md`, `.gitignore`, `.editorconfig`, `.env.example` and `docs/` files are kept instead. A failure part-way exits 2 and rolls the project back. `--dry-run` shows the plan without writing.

To replace the files in the way, ask the user to confirm and re-run with `--force`: originals are backed up to `<target>/.claude.bak/<timestamp>.<pid>/`, and `--uninstall` restores them. A project that was already scaffolded needs `--uninstall` or `--force`. `CLAUDE.md`, `AI_RULES.md` and `.mcp.json` are never overwritten, even with `--force`. If a crashed run left a lock, re-run with `--force-unlock`.

## What gets produced

Buildable per-platform starter with:

- Root config (`package.json` / `build.gradle.kts`, `tsconfig.json`, `jest.config.cjs` / `vitest.config.ts`, `.env.example`, `Dockerfile`, `docker-compose.yml` where applicable).
- `CLAUDE.md` + `AI_RULES.md` (stamped from `_shared/` — pointing to `/init-project-rules` for the operational layer).
- `docs/` (9 files: system-architecture, api, data-models, business-flows, integrations, background-jobs, repo-structure, runbook, README).
- `src/` (or `app/` for android) with the strict feature-organised layout — every feature has the same fixed set of subfolders. Files live inside subfolders, never at the feature root.
- One working example feature (`health` on backend/frontend, `home` on mobile/android) — intentionally tiny, do not expand.
- One `_feature_template/` (or `_screen_template/`) with the 4 subfolders + `.gitkeep` markers for the user to rename.
- A `scripts/lint.sh` with a **warning-only** file-size cap at 500 lines.

## After generation

The scaffolded assets are **starter templates, not frozen contracts**. The user is encouraged to read through `${SRC_DIR}/README.md` and each feature's `README.md` to understand the layout convention, then start replacing the example feature with their domain features.

## Reference

For the full per-platform tree, substitution variables, env overrides, and prompt walkthrough, see [INSTALL.md](../INSTALL.md) at the root of this package.
