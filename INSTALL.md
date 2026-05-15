# Install & Customisation Guide

This guide covers prerequisites, the two supported install paths, every prompt and substitution variable, customisation, updating, and troubleshooting for `quantqbit-claude-rules`.

## Prerequisites

- **Bash**: Git Bash (Windows) or any POSIX bash (macOS/Linux). PowerShell users go through Git Bash via the included `init.ps1` shim — the shim shells out to `bash`, it does not reimplement the scaffolder in PowerShell.
- **`sed`**: always present on supported platforms; used by the renderer's pure-`sed` fallback path.
- **`jq` OR Python 3**: for JSON validation of the stamped `settings.json` — one is enough, the script auto-detects which is present and skips the validation step gracefully if neither is found (with a `[WARN]` line).
- **`envsubst`** *(optional)*: faster variable substitution path in the renderer. The renderer falls back to pure-`sed` if it is missing, so this is purely a performance optimisation.
- **For the plugin path**: Claude Code installed and authenticated (so `claude plugin install` and the `/init-project-rules` command are available).
- **For lint runs** *(optional, used post-install)*: `shellcheck`, `yamllint`, `ansible-lint`, `terraform fmt` — install only the ones matching your detected stacks.

## Install paths

### Plugin path (recommended)

```bash
claude plugin install <git-url>
# then in any target workspace:
/init-project-rules
```

The slash command runs the same scaffolder as the standalone path, just orchestrated by Claude Code. The plugin contributes the sub-agents and the slash command; the scaffolder under `scaffold/` does the actual file stamping into the target workspace.

### Standalone path

```bash
git clone <git-url> ~/.local/share/quantqbit-claude-rules
cd /path/to/your/target/workspace
bash ~/.local/share/quantqbit-claude-rules/scaffold/init.sh
```

The standalone path is useful when you want the rules and lint configs but don't want to install the Claude Code plugin layer (e.g., for projects that don't use Claude Code at all but still want the unified `lint.sh`).

> Note: there is no curl-pipe-bash one-liner. `init.sh` resolves its sibling `lib/` and `templates/` directories from `${BASH_SOURCE[0]}`, which under process substitution becomes `/dev/fd/63`, so the script can't find its dependencies. Always clone first.

## Interactive prompts

The scaffolder asks four questions:

| Prompt | Default | Variable |
|---|---|---|
| `Project name?` | (none — required) | `PROJECT_NAME` |
| `Code subdir?` (where the actual code lives, e.g., `./` or `./infra/`) | `./` | `CODE_SUBDIR` |
| `Block destructive ops (terraform destroy, docker system prune)? [y/N]` | `n` | `OPT_IN_DESTRUCTIVE` |
| `Block git push to main/master? [y/N]` | `n` | `OPT_IN_PUSH_MAIN` |

**Notes on each prompt:**

- `Project name` — used for the `# <name> — Claude Code Rules` header in `CLAUDE.md` and in the SessionStart hook's context block. Choose something short and recognisable (e.g., `MyApp`, not `My Application v2`).
- `Code subdir` — points at the directory where lint configs and the `lint.sh` runner should live. For mono-repos with a single code root, leave it at `./`. For repos that nest code under `infra/` or `services/`, set it to that subdirectory so the lint configs sit next to the code they govern.
- `Block destructive ops` — opt-in because some workflows legitimately need `terraform destroy` (ephemeral environments) or `docker system prune` (CI cleanup). Default off; flip to `y` for prod-only workspaces.
- `Block git push to main/master` — opt-in because trunk-based workflows push directly to main. Default off; flip to `y` for repos with mandatory PR review.

## CLI flags

`init.sh` accepts the following flags. All flags are optional; with no flags it runs in interactive mode against the current directory.

| Flag | Meaning |
|---|---|
| `--help, -h` | Print usage and exit. |
| `--non-interactive` | Skip prompts; read defaults from `QQR_*` env vars. |
| `--force` | Overwrite existing target files (creates `.claude.bak/<timestamp>/` backups first). |
| `--uninstall` | Reverse a previous stamp. Reads `<target>/.claude/.scaffold-manifest-rules.txt` and removes every file listed. Backups under `.claude.bak/` are preserved. Empty directories are left behind. |
| `--target=<path>` | Target workspace directory (default: current directory). |
| `--project-name=<name>` | Pre-fill project name (overrides `QQR_PROJECT_NAME`). |
| `--code-subdir=<dir>` | Pre-fill code subdir (overrides `QQR_CODE_SUBDIR`). |

`--target=`, `--project-name=`, and `--code-subdir=` fail loudly when given an empty value (e.g. `--target=`) rather than silently falling back to a default — pass a real value or omit the flag entirely.

### Phase 0 status dashboard

Before stamping, `init.sh` prints a ✓/✗ dashboard of every file the rules layer cares about (`CLAUDE.md`, `.claude/settings.json`, `.claude/rules`, `.claude/hooks`, `lint.sh`, `Makefile`, `.editorconfig`). On a clean workspace it proceeds; on a populated workspace without `--force`, it shows the dashboard and exits 1 with a clear "Re-run with --force or --uninstall" message. With `--force`, it shows the dashboard and proceeds (clobbered files are backed up first).

### Uninstall round-trip

```bash
# Stamp:
bash init.sh --non-interactive --project-name=Foo
# (creates files + writes .claude/.scaffold-manifest-rules.txt)

# Reverse:
bash init.sh --uninstall --target=/path/to/workspace
# Reads the manifest, removes every listed file, removes the manifest.
# Backups under .claude.bak/<ts>/ are preserved for manual recovery.
```

## Substitution variables

The renderer expands these variables when stamping templates into the target workspace:

| Variable | Source | Example |
|---|---|---|
| `PROJECT_NAME` | Prompt | `MyApp` |
| `CODE_SUBDIR` | Prompt | `./infra/` |
| `STACK_LIST` | Auto-detect | `bash, ansible, docker, terraform` |
| `HAS_BASH` | Auto-detect | `true` |
| `HAS_ANSIBLE` | Auto-detect | `true` |
| `HAS_COMPOSE` | Auto-detect | `false` |
| `HAS_TERRAFORM` | Auto-detect | `true` |
| `CITATION_BASH` | First matching `**/*.sh` | `scripts/deploy.sh` |
| `CITATION_ANSIBLE` | First matching `ansible/**/*.yml` | `ansible/roles/web/tasks/main.yml` |
| `CITATION_COMPOSE` | First matching `docker-compose*.yml` | `docker/compose.yml` |
| `CITATION_TERRAFORM` | First matching `*.tf` | `terraform/modules/network/main.tf` |
| `HAS_GIT` | `git rev-parse` | `true` |
| `DENY_DESTRUCTIVE` | Opt-in | (multi-line JSON entries) |
| `DENY_PUSH_MAIN` | Opt-in | (multi-line JSON entries) |

Auto-detect runs against the target workspace tree before prompting, so the prompts can short-circuit on stacks that aren't present.

## Non-interactive mode

For CI or scripted setup, pass everything via environment variables and `--non-interactive`:

```bash
QQR_PROJECT_NAME=MyApp QQR_CODE_SUBDIR=./infra/ \
QQR_OPT_IN_DESTRUCTIVE=true QQR_OPT_IN_PUSH_MAIN=false \
  bash init.sh --non-interactive --target=/path/to/workspace
```

The boolean env vars accept any of `true`, `y`, `yes`, `1` (case-insensitive) to opt in; anything else — including empty — opts out. Both `QQR_OPT_IN_DESTRUCTIVE=true` and the older `QQR_OPT_IN_DESTRUCTIVE=y` work.

## What gets installed

```text
<workspace>/
├── CLAUDE.md                              # stamped project rules + Known traps stub
├── .claude/
│   ├── settings.json                      # permissions.deny + hook registrations
│   ├── hooks/
│   │   ├── session-start-context.sh       # injects last-activity context per session
│   │   └── post-edit-lint.sh              # runs targeted lint after each edit
│   └── rules/
│       ├── bash.md                        # path-scoped: loads on **/*.sh edits
│       ├── ansible.md                     # path-scoped: loads on ansible/**/*.yml
│       ├── compose.md                     # path-scoped: loads on docker-compose*.yml
│       └── terraform.md                   # path-scoped: loads on **/*.tf
├── .editorconfig                          # shared whitespace + EOL rules
└── <code-subdir>/
    ├── .shellcheckrc                      # shellcheck config (if HAS_BASH)
    ├── .yamllint                          # yamllint config (if HAS_ANSIBLE or HAS_COMPOSE)
    ├── .ansible-lint                      # ansible-lint config (if HAS_ANSIBLE)
    ├── scripts/lint.sh                    # unified lint entrypoint, stack-aware
    └── Makefile                           # `make lint` shim around lint.sh
```

Files for stacks the scaffolder didn't detect are skipped, not stubbed. For example, a workspace with no `*.tf` files won't get `.claude/rules/terraform.md`, won't get a terraform block in `lint.sh`, and won't have terraform mentioned in the stamped `CLAUDE.md` `Stack` section.

### File-by-file reference

- **`CLAUDE.md`** — top-level project rules. Stamped from `templates/CLAUDE.md.tmpl` with `PROJECT_NAME`, `STACK_LIST`, and per-stack citation paths filled in. Section headers are stable across stacks; section bodies are stack-conditional.
- **`.claude/settings.json`** — registers the two hooks and applies `permissions.deny` (the always-on entries plus any opt-in entries). JSON is validated post-render via `jq` or `python3 -m json.tool`.
- **`.claude/hooks/session-start-context.sh`** — runs once per session. Prints a short context block (project name, stack, last activity). Edit this to inject project-specific telemetry.
- **`.claude/hooks/post-edit-lint.sh`** — runs after every Write/Edit. Detects the file's stack from extension and runs the matching linter on just that file (not the whole tree).
- **`.claude/rules/*.md`** — path-scoped rule files with frontmatter glob patterns. Claude only loads them when an in-scope file is touched, keeping the rule budget tight.
- **`.editorconfig`** — workspace-wide whitespace and EOL rules. Always stamped (no stack gating).
- **`<code-subdir>/.shellcheckrc`**, **`.yamllint`**, **`.ansible-lint`** — per-tool configs, stamped only for detected stacks.
- **`<code-subdir>/scripts/lint.sh`** — the unified runner. Accepts no args (lints everything), `--changed` (only git-changed files), or a path (lints just that file).
- **`<code-subdir>/Makefile`** — thin shim with `make lint` calling `scripts/lint.sh`. Skipped if a `Makefile` already exists at that path.

## How the renderer works

The scaffolder runs in four phases, all under `scaffold/`:

1. **`lib/detect.sh`** scans the target workspace for stack markers (`**/*.sh`, `ansible/`, `docker-compose*.yml`, `*.tf`) and exports `HAS_*` and `CITATION_*` variables.
2. **`lib/prompt.sh`** asks the four interactive questions (or reads `QQR_*` env vars in `--non-interactive` mode).
3. **`lib/render.sh`** walks `templates/` and stamps each file into the target, expanding variables via `envsubst` (fast path) or `sed` (fallback). Stack-conditional sections use `<!-- IF:HAS_BASH -->` markers stripped by the renderer.
4. **`lib/validate.sh`** runs `jq` or `python3` over `settings.json` to confirm valid JSON, and `bash -n` over the stamped hook scripts to catch syntax errors.

Each phase is callable independently, which makes the scaffolder easy to debug when a single stack's output looks wrong.

## Customisation

The stamped output is the start, not the end. Common follow-ups:

- **Edit `CLAUDE.md`** — fill in the empty `Known traps` section with project-specific lessons (failed deploys, API quirks, security incidents). Add Conventions sections for any in-house naming or layout standards. The template is intentionally light so it doesn't drift from the agent rules; treat it as a per-project overlay.
- **Adjust `permissions.deny`** in `.claude/settings.json` — for example, add `Bash(sudo*)` if your team prefers no sudo from agents, or expand the destructive list with `kubectl delete*` for k8s-heavy projects. The opt-in deny entries (`DENY_DESTRUCTIVE`, `DENY_PUSH_MAIN`) are good templates to copy from when adding new rules.
- **Replace the `SessionStart` hook's `last_activity` line** — the stamped script reads from a generic source (the workspace's most recently modified file). Repoint it at your project-specific telemetry (CI status, deploy log, issue tracker) for richer context injection at session start.
- **Add a custom rule file** under `.claude/rules/` — follow the path-scoped frontmatter pattern from `bash.md` so it loads only when relevant files are touched. This keeps the rule budget focused: agents only see what's relevant to the current edit.
- **Tune `lint.sh`** — the runner is a stack-aware shell script, not a generated artefact you should fear editing. Add project-specific checks (e.g., a custom `tflint` rule, a repo-local linter) by appending steps to the matching stack block.

## Verifying the install

After the scaffolder finishes, sanity-check the result:

```bash
# settings.json is valid JSON
jq . .claude/settings.json

# hook scripts are syntactically valid
bash -n .claude/hooks/session-start-context.sh
bash -n .claude/hooks/post-edit-lint.sh

# lint.sh runs end-to-end (warnings are fine, hard failures are not)
bash <code-subdir>/scripts/lint.sh
```

If you're using the plugin path, also restart your Claude Code session and confirm `/init-project-rules` is listed under `/help` and the sub-agents appear under the agent picker.

## Updating

To pull a newer version of the rules into an existing workspace:

```bash
cd ~/.local/share/quantqbit-claude-rules && git pull
cd /path/to/your/target/workspace
bash ~/.local/share/quantqbit-claude-rules/scaffold/init.sh --force
```

`--force` overwrites stamped files. Hand-edited content (e.g., your `Known traps` in `CLAUDE.md`) will be lost, so commit local edits to git first. A `--backup` flag may be added in a later release.

## Troubleshooting

- **`init.sh` errors out with "file exists"** — usually means a stamped file is already present from a previous run. Either re-run with `--force` (overwrites all stamped files), or move/rename the existing file if you want to preserve hand edits before re-stamping.
- **PowerShell native fallback prints "not yet implemented"** — the `init.ps1` shim requires Git Bash or WSL on the `PATH`. Install one of them and re-run. A native PowerShell port is not on the roadmap; the renderer relies on POSIX text tooling that is awkward to reimplement cross-shell.
- **Hook scripts not firing** — check that `.claude/settings.json` paths are relative to the workspace root (not absolute paths from the scaffolder's machine), then restart your Claude Code session so hooks are re-registered. Hook registration happens at session start, not on settings.json change.
- **`lint.sh` exits non-zero with no flags** — usually a tool is missing. Check the `[WARN]` lines in the output; install the named tool (`shellcheck`, `yamllint`, `ansible-lint`, `terraform`, etc.) and re-run. The runner treats missing tools as warnings, not failures, but flags genuine lint findings as failures.
- **Sub-agents not visible** — the plugin path needs Claude Code restarted after `claude plugin install`. The standalone path doesn't ship the agents (only the rules + lint configs); use the plugin path if you want the sub-agents.
- **`CITATION_*` variables show generic paths** — the auto-detect picks the first matching file by lexical order. If you want a more representative example, set the citation manually via env var (e.g., `QQR_CITATION_BASH=scripts/deploy-prod.sh`) before running.

## Caveats

- **Python is intentionally not covered** — Python tooling (poetry vs pip, ruff vs flake8, mypy strictness) is too divisive to ship a single opinionated config. Fork the rules manually if you need Python-specific guidance.
- **`Known traps` ships empty** — the `CLAUDE.md` template emits the section header with no content. Fill it in per project as you accumulate lessons.
- **`init.ps1` is a thin shim** — it requires Git Bash on the `PATH`. There is no native PowerShell port and one is not planned; PowerShell-only environments should use WSL.

---

# Part 2 — `/init-project-scaffold` (project-skeleton layer, v0.2.0)

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

- `CLAUDE.md`, `AI_RULES.md`, `README.md`, `.editorconfig`, `.gitignore`, `.env.example`.
- `docs/` (9 files: system-architecture, api, data-models, business-flows, integrations, background-jobs, repo-structure, runbook, index README).
- Platform-specific build config (`package.json`+`tsconfig.json`+`jest.config.ts` for JS/TS; `build.gradle.kts`+`settings.gradle.kts`+`gradle/wrapper/...` for android).
- `${SRC_DIR}/` (or `app/` for android) with the strict feature-organised layout — see the plan for the per-platform tree.
- One working example feature (`health` on backend/frontend; `home` on mobile/android) — tiny, do not expand.
- One `_feature_template/` (or `_screen_template/`) with the canonical subfolders + `.gitkeep`.
- A `scripts/lint.sh` (or equivalent) with a **warning-only** file-size cap at 500 lines.

## Stack non-goals (locked for v1)

The scaffolder deliberately omits: Prisma, Drizzle, BullMQ, Redis, OpenTelemetry, CQRS, event buses, GraphQL, tRPC, Passport, Hilt, Room, Dagger, KSP-heavy plugins, Next.js, Redux, MobX, UI libraries (MUI/Chakra/Mantine), CI workflows. See the plan §Stack non-goals for the full list and rationale.

## After stamping

The starters are **buildable but minimal**. Replace the example feature with your domain features, fill in `AI_RULES.md` with project-specific rules, and update `docs/*.md` as the project evolves. Each per-feature `README.md` documents the 4-subfolder rule once — agents should follow that rule when adding new features.

## Troubleshooting (scaffold-specific)

- **"renderer lib not found"** — your install is incomplete. Ensure the plugin or clone includes `scaffold/lib/render-<platform>.sh`.
- **`npm install` fails after stamp** — usually network or registry issues unrelated to the scaffolder. Re-run with a fresh terminal; check `npm config get registry`.
- **`./gradlew assembleDebug` fails on first run** — confirm `ANDROID_HOME` is set and the platform tools matching the stamped `compileSdk` are installed. The scaffolder stamps a `local.properties.example` showing the expected shape.
- **Auto-detect picked the wrong platform** — pass `--platform=` explicitly to override.
