---
name: project-scaffold
description: Scaffolds a buildable per-platform project starter. Use when the user wants to scaffold a buildable per-platform project starter (backend, frontend web, mobile, or Android) with strict feature-organised folder discipline. Trigger phrases include "scaffold project", "scaffold backend", "init backend skeleton", "create folder structure", "Strapi-like layout", "feature-organised layout", "set up src structure", "new express app", "new react app", "new vite app", "new expo app", "new react native app", "new android project", "new kotlin app", "buildable starter", "set up new repo", "init project skeleton". Stamps a buildable starter with config/, middlewares/, models/, lib/, api/<version>/<feature>/{routes,controllers,services,types}/ (backend) or analogous strict layouts per platform, plus docs/, scripts/, migrations/, CLAUDE.md and AI_RULES.md (only if absent), and a working example feature. The skill shells out to the quantqbit-claude-rules plugin's init-scaffold.sh.
---

# Project Scaffold Skill

Stamps a **buildable per-platform project skeleton** with strict feature-organised folder discipline into the user's current workspace. Four platforms are supported in v1:

| Platform | Stack | Build verification |
| --- | --- | --- |
| `backend` | Node + TypeScript + Express + Mongoose + pg | `npm install && npm run build && npm test && curl /healthz` |
| `frontend` | React + Vite + TypeScript | `npm install && npm run build && npm test` |
| `mobile` | React Native + Expo + TypeScript | `npm install && npx expo prebuild --no-install && npx tsc --noEmit` |
| `android` | Kotlin + Compose + Retrofit (no Hilt/Room) | `./gradlew :app:assembleDebug :app:testDebugUnitTest ktlintCheck` |

## When this skill activates

Activate this skill when the user asks for any of:

- A new project skeleton ("scaffold a new backend service", "set up a fresh expo app", "init an android project").
- A folder structure that matches the strict Strapi-like / LawyersApp-like pattern (`config/`, `middlewares/`, `models/`, `lib/`, `api/v1/<feature>/{routes,controllers,services,types}/`).
- A "buildable starter" — meaning the stamped output runs out of the box, not just empty folders.

Do **not** activate for:

- Adding a single feature to an existing project (use the existing repo's conventions instead).
- Setting up `.claude/` rules + hooks + lint configs only (that's the companion `/init-project-rules` slash command).

## How this skill works

The skill is thin — it locates the **`quantqbit-claude-rules`** plugin's `init-scaffold.sh` and invokes it. The scaffolder lives with the plugin so installation, updates, and templates ship together.

### Resolution order

When the skill is triggered, locate the scaffolder by trying these paths **in order**:

1. **`${CLAUDE_PLUGIN_ROOT}/scaffold/init-scaffold.sh`** — if the `quantqbit-claude-rules` plugin is installed in the current Claude Code session.
2. **`~/.local/share/quantqbit-claude-rules/scaffold/init-scaffold.sh`** — standalone-clone path documented in the plugin's README.
3. **`$PROJECT_SCAFFOLD_HOME/scaffold/init-scaffold.sh`** — environment-variable override for users who clone to a non-default location.

If none resolve, tell the user: "I can't find the project-scaffold runner. Install the `quantqbit-claude-rules` plugin (`claude plugin marketplace add Albiee007/quantqbit-claude-rules`, then `claude plugin install quantqbit-claude-rules@quantqbit`) or clone the repo to `~/.local/share/quantqbit-claude-rules` (or set `$PROJECT_SCAFFOLD_HOME` to a custom path) and re-run."

### Invocation

Once the scaffolder is located:

1. **Confirm the target directory** with the user (default = current working directory). Surface a one-line summary of what will be stamped.
2. **Confirm the platform** — either from the user's request ("scaffold a backend") or by auto-detection. If the directory already has a `package.json` / `build.gradle.kts` / `app.json`, point that out and ask whether to use `--force` (with backup) or pick a different platform.
3. **Run the scaffolder** with the chosen flags. On Unix:

   ```bash
   bash <resolved-path>/init-scaffold.sh --platform=<platform> [other flags]
   ```

   On Windows native PowerShell:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File <resolved-path>\init-scaffold.ps1 --platform=<platform> [other flags]
   ```

   The `.ps1` wrapper needs Git for Windows installed (it finds Git Bash itself) and forwards to `init-scaffold.sh`.

4. **Pass through user-supplied flags** verbatim. The scaffolder accepts: `--platform=`, `--target=`, `--project-name=`, `--src-dir=`, `--api-version=`, `--features=`, `--android-package=`, `--with-i18n`, `--with-auth`, `--force`, `--non-interactive`.

### After the stamp

Surface the produced tree at a high level (top-level folders only) and recommend the user's next steps:

1. Open `${SRC_DIR}/README.md` and the example feature's `README.md` to understand the 4-subfolder rule.
2. Replace the example feature (`health` on backend/frontend; `home` on mobile/android) with their first domain feature.
3. Fill in `AI_RULES.md` with project-specific rules (verification gates, prompt hygiene, forbidden actions).
4. Run the build smoke test (table above) to confirm the starter compiles + tests pass.
5. If they haven't already, run `/init-project-rules` for the operational `.claude/` layer.

## Companion command

The `/init-project-scaffold` slash command (shipped by the same `quantqbit-claude-rules` plugin) does exactly what this skill orchestrates. The skill is the natural-language entry point; the slash command is the explicit-args entry point. Both end up running `init-scaffold.sh`.

## Skill scope (out of scope for v1)

This skill **only** scaffolds. It does not:

- Add CI/CD workflows (deferred to a future `--with-ci=` flag).
- Add backend frameworks beyond Express, frontend frameworks beyond Vite+React, mobile beyond Expo, or Android beyond plain Kotlin+Compose+Retrofit.
- Bundle UI component libraries, state management libraries, or authentication providers (the user picks).
- Bundle Prisma / Drizzle / BullMQ / Redis / OpenTelemetry / Hilt / Room / KSP plugins (see the plugin's INSTALL.md §Stack non-goals).

If the user asks for any of the above, explain what's locked in v1 and offer to either (a) scaffold the v1 starter and let them add the missing piece manually, or (b) scaffold and then make targeted follow-up edits to introduce the missing piece.
