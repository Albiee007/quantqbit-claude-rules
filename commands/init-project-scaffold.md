---
description: Scaffold a buildable starter for backend / frontend / mobile / android with the strict feature-organised folder layout
argument-hint: [--platform=backend|frontend|mobile|android] [--project-name=NAME] [--src-dir=DIR] [--api-version=vN] [--features=a,b,c] [--android-package=ID] [--with-i18n] [--with-auth] [--force] [--non-interactive]
---

# /init-project-scaffold

Initialise a **buildable per-platform project starter** inside the user's current workspace. Companion to `/init-project-rules` — the two scaffolders compose:

1. `/init-project-rules` stamps the operational `.claude/` rules + lint configs layer.
2. `/init-project-scaffold` stamps the application skeleton on top (per-platform buildable starter).

Recommended order: run `/init-project-rules` first, then `/init-project-scaffold` for the platform of choice.

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
| `--platform=mobile` | React Native + Expo + TypeScript | `npm install && npx expo prebuild --no-install && npx tsc --noEmit` |
| `--platform=android` | Kotlin + Compose + Retrofit (no Hilt/Room — see Stack non-goals) | `./gradlew assembleDebug && ./gradlew testDebugUnitTest && ./gradlew ktlintCheck` |

If `--platform=` is omitted, the dispatcher auto-detects by sniffing `build.gradle.kts`, `app.json`/Expo, Vite config, or Express/Fastify deps. Empty dir → interactive prompt.

## Safety guard

Without `--force`, the script refuses to overwrite any of these if already present:

- `CLAUDE.md`, `AI_RULES.md`
- `package.json`, `build.gradle.kts`, `build.gradle`, `app.json`
- `src/`, `app/`, `docs/`

To regenerate, ask the user to confirm and re-run with `--force` — clobbered files are first backed up to `<target>/.claude.bak/<timestamp>/`.

## What gets produced

Buildable per-platform starter with:

- Root config (`package.json` / `build.gradle.kts`, `tsconfig.json`, `jest.config.ts`, `.env.example`, `Dockerfile`, `docker-compose.yml` where applicable).
- `CLAUDE.md` + `AI_RULES.md` (stamped from `_shared/` — pointing to `/init-project-rules` for the operational layer).
- `docs/` (9 files: system-architecture, api, data-models, business-flows, integrations, background-jobs, repo-structure, runbook, README).
- `src/` (or `app/` for android) with the strict feature-organised layout — every feature has the same fixed set of subfolders. Files live inside subfolders, never at the feature root.
- One working example feature (`health` on backend/frontend, `home` on mobile/android) — intentionally tiny, do not expand.
- One `_feature_template/` (or `_screen_template/`) with the 4 subfolders + `.gitkeep` markers for the user to rename.
- A `scripts/lint.sh` with a **warning-only** file-size cap at 500 lines (use `--strict` to upgrade to error).

## After generation

The scaffolded assets are **starter templates, not frozen contracts**. The user is encouraged to read through `${SRC_DIR}/README.md` and each feature's `README.md` to understand the layout convention, then start replacing the example feature with their domain features.

## Reference

For the full per-platform tree, substitution variables, env overrides, and prompt walkthrough, see [INSTALL.md](../INSTALL.md) at the root of this package.
