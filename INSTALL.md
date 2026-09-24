# Install & Customisation Guide

This is the full reference. New here? Start with [GETTING-STARTED.md](./GETTING-STARTED.md).

It covers the **agent harness** (Part 1), **`/init-project-rules`** lint tooling (Part 2), and **`/init-project-scaffold`** starters (Part 3).

## Prerequisites

- **Bash:** Git Bash on Windows, or any bash on macOS or Linux. The `.ps1` entry points are thin wrappers that locate Git Bash; WSL's `bash.exe` is not used.
- **Tools:** `git`, `awk`, `sed`, and `sha256sum` or `shasum`. These are standard on every supported OS.
- **Python 3:** needed whenever `.claude/settings.project.json` exists, and to migrate an existing `.claude/settings.json`. `python3`, `python` and the Windows `py` launcher are all found. `jq` is not required.
- **`envsubst`:** required by `init.sh` and `init-scaffold.sh` only. It ships with Git Bash; on macOS run `brew install gettext`, on Debian/Ubuntu install `gettext-base`.
- **`make`:** optional; `make lint` just wraps `scripts/lint.sh`. Git Bash has no `make`.
- **Windows + project-scaffold:** run `git config --global core.longpaths true` once (some starter template paths are long).
- **Repository access:** the GitHub repo is private, so installing needs read access plus working git credentials.
- **Optional linters:** used by hooks and `lint.sh` when present. `shellcheck`, `yamllint`, `ansible-lint`, `terraform`, `docker`.

---

# Part 1 — The agent harness

## What it is

Harness content (under `harness/` in this repo) is **vendored into each project's `.claude/` directory and committed to git**, so every developer and every Claude Code session gets the same rules. No developer needs the plugin installed.

| Ships to the project | What it does |
|---|---|
| `.claude/rules/harness/00-core.md` | Always-loaded core rules: precedence, Opus-only, plan mode, orchestration, mandatory skills, verification, `.env`, git policy, YAGNI |
| `.claude/rules/harness/*.md` | Path-scoped rules: coding, tests, security, ui-ux, seo, bash, powershell, ansible, compose, terraform |
| `.claude/skills/{coding-standards,design-patterns,ui-ux,seo,harness}/` | Mandatory knowledge skills, with progressive-disclosure references |
| `.claude/agents/{explorer,implementor,infra-implementor,verifier,reviewer}.md` | The coordinated agent roster. All run on Opus. |
| `.claude/harness/hooks/*.sh` | `guard` (Opus + `.env` enforcement), `prompt-router` and `file-context` (mandatory checklists), `session-start`, `post-edit-lint` |
| `.claude/settings.json` | **Generated**: harness base settings merged with `.claude/settings.project.json` |
| `.claude/harness/lock` | Version and content hash of every harness file |

## Install into a project

```bash
# Plugin, from a terminal (or use /plugin marketplace add … and /plugin install … inside Claude Code):
claude plugin marketplace add Albiee007/quantqbit-claude-rules
claude plugin install quantqbit-claude-rules@quantqbit
# restart Claude Code; then, in a project: "install the harness",
# or /quantqbit-claude-rules:init-project-rules (lint tooling + harness)

# Without the plugin:
git clone https://github.com/Albiee007/quantqbit-claude-rules ~/.local/share/quantqbit-claude-rules
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target /path/to/project --dry-run
bash ~/.local/share/quantqbit-claude-rules/scaffold/sync.sh --target /path/to/project --commit
```

PowerShell: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scaffold\sync.ps1 --target C:\path\to\project --dry-run`.

Never add the marketplace from your working copy of this repo: a local-path marketplace copies untracked and gitignored files into the plugin cache. Use the GitHub form, or a clean clone.

On first install, sync:
- auto-detects **profiles** (see below) and writes them to `.claude/harness.config`.
- seeds `.claude/rules/project/README.md` and, only if **no** `CLAUDE.md` or `AGENTS.md` exists, a `CLAUDE.md` stub.
- moves an existing `.claude/settings.json` into the project-owned `.claude/settings.project.json`, so nothing is lost.
- never modifies `CLAUDE.md`, `AGENTS.md` or `AI_RULES.md`.

## Profiles

| Profile | Adds |
|---|---|
| (always) | core, coding/tests/security rules, coding-standards, design-patterns, harness skills, all agents and hooks, bash/powershell rules |
| `web` | ui-ux + seo skills and rules |
| `mobile` | ui-ux skill and rule |
| `backend` | compose/Dockerfile rule |
| `infra` | ansible, terraform, compose rules |

To change profiles, edit `profiles=` in `.claude/harness.config` and re-sync, or pass `--profiles`. That also rewrites `profiles=` in `harness.config`, in the same transaction. Files that are no longer selected are removed if unmodified, and kept as project-owned if you had edited them.

## Updating

```bash
bash .claude/harness/bin/harness-sync.sh --dry-run          # preview
bash .claude/harness/bin/harness-sync.sh --diff             # preview with diffs
bash .claude/harness/bin/harness-sync.sh --commit           # apply + commit on the current branch
bash .claude/harness/bin/harness-sync.sh --ref vX.Y.Z       # pin a pushed release tag (clones upstream)
bash .claude/harness/bin/harness-sync.sh --remote            # latest upstream default branch
```

The bootstrap picks its source in this order:
1. `--source DIR`
2. `--ref TAG` or `--remote`: a shallow clone of upstream (`$HARNESS_SOURCE_URL`, else the lock's https `source`, else the canonical GitHub URL).
3. Otherwise, the **newest** local source among: `$HARNESS_HOME`, `$CLAUDE_PLUGIN_ROOT`, the installed plugin copy (`~/.claude/plugins/cache/quantqbit/…`, or under `$CLAUDE_CONFIG_DIR` when that is set), and `~/.local/share/quantqbit-claude-rules`. A local clone is never pulled automatically: run `git -C <clone> pull` first.
4. With no local source, the same upstream clone as in step 2.

A source older than the installed harness is refused (exit 1). Pass `--allow-downgrade` only when you mean to roll back.

## Sync guarantees

| Guarantee | How |
|---|---|
| All-or-nothing | New state is built and validated in `.claude/harness/.tmp/`, then applied with a journal. Any failure rolls every file back (exit 2). The lock is written last. |
| Never clobbers local work | A harness file whose hash differs from the lock → `CONFLICT-MODIFIED`. A pre-existing file at a harness path → `CONFLICT-UNMANAGED`. Both abort with nothing written (exit 1). |
| Safe to repeat | Unchanged files are no-ops. Re-running the same version changes 0 files. |
| Merge-conflict safe | Harness and project files never share a file. The lock is deterministic (sorted, no timestamps), so the same version produces identical bytes on every machine. Hashes ignore CRLF differences. |
| No concurrent runs | An atomic `mkdir` mutex. A stale mutex is cleared with `--force-unlock`. |
| Clean working tree | Sync refuses when harness paths have uncommitted changes (`--allow-dirty` overrides). |

Resolving conflicts:
- **`--keep`** (CONFLICT-MODIFIED only): keep your local version. It is marked `kept-local` in the lock, and the doctor keeps reporting it.
- **`--theirs`:** take the harness version. Your previous copy is saved under `.claude/harness/.backup/<time>/` (gitignored).
- **CONFLICT-UNMANAGED:** one of your files uses a reserved harness name. The agents are `explorer`, `implementor`, `infra-implementor`, `verifier` and `reviewer`. The skills are `coding-standards`, `design-patterns`, `ui-ux`, `seo` and `harness`. The other reserved path is `.claude/.gitattributes`. Rename yours, or use `--theirs`; `--keep` does not apply.
- **Recommended:** move the intent of your edit into `.claude/rules/project/`, then use `--theirs`.
- **Git merge conflict inside `.claude/harness/lock` or `.claude/settings.json`:** take either side of those files, `git add` them and finish the merge commit, then run `harness-sync.sh --commit`.

## Customising (without conflicts)

| Want to… | Edit (project-owned) |
|---|---|
| Add or override rules | `.claude/rules/project/*.md` (add `paths:` frontmatter to scope a rule) |
| Team permissions, env, extra hooks | `.claude/settings.project.json`, then re-sync |
| Profiles, lint/test commands, staging branch | `.claude/harness.config` |
| Project overview and conventions | `CLAUDE.md` / `AGENTS.md` |
| Your own agents or skills | New names under `.claude/agents/` and `.claude/skills/` |
| Personal preferences | `CLAUDE.local.md`, `.claude/settings.local.json` (gitignore both) |

**Settings merge rules:**
- Objects merge recursively.
- Arrays are unioned, so harness deny rules and hooks cannot be dropped.
- For scalar values, the project wins.
- `env.CLAUDE_CODE_SUBAGENT_MODEL*` stays locked to Opus, and a non-Opus `model` is rejected.

## Health check

```bash
bash .claude/harness/bin/harness-doctor.sh     # exit 0 healthy, 1 warnings, 2 errors
```

It reports:
- modified or missing harness files and `kept-local` rows
- unmanaged files in harness-owned folders
- conflict markers in the lock
- personal files that are not gitignored
- a newer harness version, when the source can be found

## Enforcement layers

1. **Rules and skills** (context): the core rule is always loaded. Path-scoped rules load when a matching file is read. Skills load on demand, and the core rule makes them mandatory.
2. **Hooks** (checklist injection): `prompt-router` matches keywords in your prompt, and `file-context` matches files before they are written. Each injects the relevant checklist once per agent context (the main thread and each sub-agent).
3. **Hard enforcement:**
   - `CLAUDE_CODE_SUBAGENT_MODEL=opus` forces Opus: verified on Claude Code 2.1.214, where it overrides agent frontmatter. `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` is set as well, for versions that support it.
   - The `guard` hook denies non-Opus Agent calls. It also denies Read/Edit/Write/Grep calls and Bash/PowerShell commands that name a real `.env` file or a `.env*` glob, in any letter case. `.env.example` and similar templates stay allowed. This is best-effort pattern matching: it cannot see indirect reads such as `grep -r .` or `find -exec cat`, so add `.env*` and `!.env.example` to your root `.gitignore` (sync does not do this for you). Gitignore does not stop an agent reading a file; it keeps secrets out of commits.
   - `file-context` denies the first UI or SEO file write in each agent context once (even if the prompt router already showed the checklist), with the checklist and the skill to load; the retry is allowed. Set `checklists=inform` in `harness.config` to only add the checklist instead.
   - Each hook typically takes 0.1–0.3 s on an idle Windows machine and 1–2 s under load or antivirus scanning (mostly bash start-up); less on macOS and Linux.
   - `harness:managed vX` stamps show each file's own `file_version`: files unchanged since an earlier release keep the older number. That is expected.
   - `permissions.deny` blocks `git add -A`, force-push and `rm -rf /`.

> **Note:** project settings use `defaultMode: "plan"`, which takes precedence over a personal `bypassPermissions` default. Override it in `.claude/settings.project.json` if your team prefers another mode.

## Uninstall

```bash
bash /path/to/quantqbit-claude-rules/scaffold/sync.sh --target . --uninstall
```

This removes unmodified harness files and the lock. Modified files and project-owned files stay in place.

## Maintaining the harness (this repo)

```bash
bash scaffold/lib/release.sh                # regenerate harness/manifest.tsv (per-file versions)
bash scaffold/lib/validate-harness.sh       # policy, frontmatter, size budgets, hygiene, links, release consistency
bash tests/hooks.test.sh && bash tests/validate.test.sh && bash tests/sync.test.sh
```

To release:
1. Edit the files under `harness/`.
2. Bump `VERSION` and the version in `.claude-plugin/plugin.json`. The marketplace entry carries no version.
3. Add a `CHANGELOG.md` entry that includes **Upgrade notes**.
4. Run `release.sh`, then `validate-harness.sh`.
5. Tag the release and push the tag: `git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z`. Check it with `git ls-remote --tags origin vX.Y.Z`.

A file's `file_version` changes only when its content changes, so project upgrade diffs stay minimal.

---

# Part 2 — `/init-project-rules` (lint tooling + harness)

`scaffold/init.sh` does two things:
1. It stamps lint tooling tailored to the detected stacks: `.editorconfig` at the root, and under `CODE_SUBDIR` the files `.shellcheckrc`, `.yamllint`, `.ansible-lint`, `scripts/lint.sh` and `Makefile`.
2. It runs the harness sync.

Existing files are **kept** unless you pass `--force`, which backs each one up to `.claude.bak/<timestamp>/` before replacing it.

| Prompt / flag | Env var (`--non-interactive`) | Meaning |
|---|---|---|
| Project name / `--project-name=` | `QQR_PROJECT_NAME` | Used in the lint tooling headers |
| Code subdir / `--code-subdir=` | `QQR_CODE_SUBDIR` | Where the lint configs and `scripts/lint.sh` go |
| Block destructive ops? | `QQR_OPT_IN_DESTRUCTIVE` | Adds `terraform destroy` and `docker system/volume prune` denies to `settings.project.json` |
| Block push to main? | `QQR_OPT_IN_PUSH_MAIN` | Adds `git push *main*`/`*master*` denies to `settings.project.json` |
| `--force` | | Replace existing lint files, with backups |
| `--no-harness` | | Stamp lint tooling only |
| `--uninstall` | | Remove stamped lint files that are still unmodified (manifest: relative paths + hashes). For the harness, use `sync.sh --uninstall`. |

```bash
QQR_PROJECT_NAME=MyApp QQR_CODE_SUBDIR=./infra \
  bash ~/.local/share/quantqbit-claude-rules/scaffold/init.sh --non-interactive
```

`scripts/lint.sh` lints everything for the detected stacks. `make lint` wraps it, and works from the Makefile's own directory. Lint configs are stamped only for detected stacks: `.shellcheckrc` for bash, `.ansible-lint` for Ansible, and `.yamllint` for Ansible or Compose.

---

# Part 3 — `/init-project-scaffold` (project-skeleton layer)

Stamps a **buildable per-platform starter** on top of the operational rules layer above. Run `/init-project-rules` first for `.claude/` and `CLAUDE.md` (operational), then `/init-project-scaffold` for the application skeleton.

## Supported platforms

| Platform | Stack | Build smoke test |
| --- | --- | --- |
| `backend` | Node + TypeScript + Express + Mongoose + pg | `npm install && npm run build && npm test && curl localhost:3000/healthz` |
| `frontend` | React + Vite + TypeScript | `npm install && npm run build && npm test` |
| `mobile` | React Native + Expo + TypeScript | `npm install && npx expo prebuild --no-install && npx tsc --noEmit` |
| `android` | Kotlin + Compose + Retrofit (no Hilt/Room) | `./gradlew :app:assembleDebug :app:testDebugUnitTest ktlintCheck` |

The dispatcher auto-detects an existing project shape when no `--platform=` is supplied:
- `build.gradle.kts`/`build.gradle` → android
- `app.json` + `expo` in `package.json` deps → mobile
- `react` + Vite config → frontend
- `express`/`fastify` in deps → backend
- empty dir → interactive prompt

## Interactive prompts (`/init-project-scaffold`)

| Prompt | Default | Variable |
| --- | --- | --- |
| `Platform?` (if not auto-detected) | (auto) | `PLATFORM` |
| `Project name?` | (none — required) | `PROJECT_NAME` |
| `Source directory?` | `src` (or `app` for android) | `SRC_DIR` |
| `API version?` (backend only) | `v1` | `API_VERSION` |
| `Features (CSV, optional)?` | (none) | `FEATURES_CSV` |
| `Android package id?` (android only) | (none — required) | `ANDROID_PACKAGE` |
| `Enable i18n stub?` (backend) | `n` | `WITH_I18N` |
| `Enable auth stub?` (frontend/mobile) | `n` | `WITH_AUTH` |

## CLI flags

```text
--platform=<backend|frontend|mobile|android>   Skip auto-detect; pick the renderer.
--target=<path>                                Target dir (default: current).
--project-name=<name>                          Pre-fill project name.
--src-dir=<dir>                                Source directory (default: src).
--api-version=<vN>                             Backend API version (default: v1).
--features=<a,b,c>                             CSV of feature folders to stamp.
--android-package=<id>                         Reverse-DNS package id.
--with-i18n                                    Enable optional i18n stub.
--with-auth                                    Enable optional auth stub.
--non-interactive                              Skip prompts; use QQPS_* env vars.
--force                                        Overwrite existing files (backed up first).
--help, -h                                     Print usage and exit.
```

## Environment variables (`--non-interactive`)

| Variable | Purpose |
| --- | --- |
| `QQPS_PROJECT_NAME` | Project name |
| `QQPS_SRC_DIR` | Source directory (default `src`) |
| `QQPS_API_VERSION` | API version (default `v1`) |
| `QQPS_FEATURES` | CSV of feature names to stamp |
| `QQPS_ANDROID_PACKAGE` | Reverse-DNS Android package id |
| `QQPS_WITH_I18N` | `true`/`false` |
| `QQPS_WITH_AUTH` | `true`/`false` |

Example:

```bash
QQPS_PROJECT_NAME=MyApi QQPS_FEATURES=users,posts \
  bash /path/to/scaffold/init-scaffold.sh --platform=backend --non-interactive
```

## What gets stamped

Every platform produces (from `templates/_shared/` + the per-platform tree):

- `CLAUDE.md`, `AI_RULES.md` and root `.mcp.json`, each **only if absent** (never overwritten, even with `--force`; `CLAUDE.md` is skipped when an `AGENTS.md` exists), plus `README.md`, `.editorconfig`, `.gitignore` and `.env.example`.
- `docs/` (9 files: system-architecture, api, data-models, business-flows, integrations, background-jobs, repo-structure, runbook, index README).
- Platform-specific build config: `package.json` and `tsconfig.json`, plus `jest.config.cjs` (backend) or `vite.config.ts`/`vitest.config.ts` (frontend); `build.gradle.kts`, `settings.gradle.kts` and `gradle/wrapper/...` for Android.
- `${SRC_DIR}/` (or `app/` for Android) with the strict feature-organised layout. See `scaffold/templates/<platform>/` for the per-platform tree.
- One working example feature (`health` on backend/frontend; `home` on mobile/android) — tiny, do not expand.
- One `_feature_template/` (or `_screen_template/`) with the canonical subfolders + `.gitkeep`.
- A `scripts/lint.sh` (or equivalent) with a **warning-only** file-size cap at 500 lines.

## Stack non-goals (locked for v1)

The scaffolder deliberately omits: Prisma, Drizzle, BullMQ, Redis, OpenTelemetry, CQRS, event buses, GraphQL, tRPC, Passport, Hilt, Room, Dagger, KSP-heavy plugins, Next.js, Redux, MobX, UI libraries (MUI/Chakra/Mantine), CI workflows.

## After stamping

The starters are **buildable but minimal**. Replace the example feature with your domain features, fill in `AI_RULES.md` with project-specific rules, and update `docs/*.md` as the project evolves. Each per-feature `README.md` documents the 4-subfolder rule once — agents should follow that rule when adding new features.

## Troubleshooting (scaffold-specific)

- **"renderer lib not found"** — your install is incomplete. Ensure the plugin or clone includes `scaffold/lib/render-<platform>.sh`.
- **`npm install` fails after stamp** — usually network or registry issues unrelated to the scaffolder. Re-run with a fresh terminal; check `npm config get registry`.
- **`./gradlew assembleDebug` fails on first run** — confirm `ANDROID_HOME` is set and the platform tools matching the stamped `compileSdk` are installed. Create `local.properties` with `sdk.dir=<path to your Android SDK>` if Gradle cannot find the SDK.
- **Auto-detect picked the wrong platform** — pass `--platform=` explicitly to override.
