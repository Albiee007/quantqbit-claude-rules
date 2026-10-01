# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org/). For the harness:

- **Major:** layout or lock-format changes.
- **Minor:** new skills, rules or agents.
- **Patch:** content fixes.

Every entry has **Upgrade notes** for anything a project needs to act on.

## [1.5.0] - 2026-10-02

Product story art becomes a harness capability. On a real website revamp, four feature-pillar illustrations (friends on a trip, flatmates in a kitchen, a currency-exchange counter, a sofa and a spending chart) were made ad hoc: context gathered by hand, a style prompt reinvented, full-resolution files dug out of Canva through a scratch design, and a one-off export script. Owner review caught a ₿-like glyph that had to be regenerated. The new skill and agent make that a repeatable, reviewed workflow.

### Added
- **Agent `illustrator`** (web and mobile profiles): collects product context, storyboards one scene per real feature pillar, locks a style bible, generates through the session's image provider, returns a contact sheet for owner approval, and exports budgeted web files with provenance recorded. Its `tools` list is the core file and shell tools (the validator requires one); when the session's MCP image tools aren't granted to it, it returns the prompts and the parent generates.
- **Skill `story-art`** (web and mobile profiles):
  - Workflow: context pack → storyboard → locked style bible → prompts → one-at-a-time generation → review gate with owner approval → full-resolution retrieval → web export → integration guidance → provenance, all recorded in one `out/story-art/<date>/plan.md`.
  - References: `providers.md` (Canva MCP step by step, including `quota_cooldown`, signed thumbnail URLs that 403 when resized, the `copy-design` scratch fallback when `create-design` hits `quota_exceeded`, `update_fill` to swap one image, expiring export URLs; Figma Weave and API-key providers outlined), `scenario-patterns.md`, `prompt-template.md` (style bible, scene template, negative list, a worked example) and `review-checklist.md`.
  - `scripts/export_art.py`: `export` writes `<prefix>-<scene>-<width>.{avif,webp}` at each width, steps quality down to fit per-width byte budgets (defaults 1200 px ≤ 120 KB, 640 px ≤ 50 KB), keeps AVIF under 80% of the WebP size (WebP only when Pillow lacks AVIF), and merges the entries into a site manifest without dropping other keys. It refuses two sources with one scene name (`trip.png` and `trip.jpg`) and a manifest it can't merge into before encoding anything, writes nothing if a budget can't be met, and stages the images and manifest so they land together. `sheet` builds a labelled contact sheet. Pillow only, no Chrome.
- **Snippet `art.md`** (web and mobile profiles): the brand and story art checklist. The prompt router injects it for `illustration(s)`, `artwork`, `story art`, `scene art`, `hero image/art/illustration`, `logo(s)` and `brand assets/identity/kit`, so web projects get it too (the store snippet is mobile-only).
- **Routing:** core §4 orchestration row and §5 mandatory-skill row; the store snippet and the mobile session roster name the illustrator; web projects get their own roster line (`brand-asset-creator → illustrator`).
- **Tests:** `tests/story-art.test.sh` (fixtures generated with Pillow; skipped locally without it, a failure in CI; covers duplicate scene names and a broken manifest), run in CI; sync tests for the mobile and web installs, including the art snippet; hook tests for the new keywords on mobile and web installs, a no-trigger case and both rosters.

### Changed
- `brand-assets` and `brand-asset-creator` hand the palette hexes to `illustrator`.
- Reserved names (sync's conflict message and reserved-agent check, harness README, harness skill, harness-install skill, INSTALL) include `illustrator` and `story-art`.

### Upgrade notes
- **Web and mobile projects** receive `.claude/agents/illustrator.md`, `.claude/skills/story-art/` and `.claude/harness/snippets/art.md` on the next sync. If a `.gitignore` rule hides `.claude/skills/`, sync names the rule and prints the exceptions to add.
- If a project already has its own agent named `illustrator` or skill named `story-art`, sync reports CONFLICT-UNMANAGED. Rename yours, then re-run.
- `export_art.py` needs **Python 3.9+ with Pillow**; AVIF output needs Pillow 11.3+ (or a build with libavif). Older Pillow writes WebP only.
- **Image generation** uses the session's MCP tools (Canva by default). To let the agent call them directly, add a project agent under another name whose `tools` include your MCP server; otherwise the parent session runs generation.
- If your site has a render script that rewrites its image manifest, make it preserve `art-*` entries.

## [1.4.0] - 2026-09-27

Store and brand work now produces fewer, cleaner files. In a real project, one screenshot refresh left 161 new or changed files in git. They included a second copy of the mockup sources, agent-written render, verify and contrast scripts, engine files mixed into the sources, and brand exports of every variant at every size.

### Added
- **`render_frames.py render --all`**: the release set in one command.
  - Renders every size and the feature graphic.
  - Removes PNGs of renamed or dropped frames.
  - Writes the contact sheet, plus Android and iOS strips with a seam report for continuous sets.
  - Re-checks every file: exact size, RGB, under 8 MB.
  - Runs the new caption contrast check and `check_store_assets.py`, and exits non-zero on any failure.
  - Chrome runs in parallel (`--jobs`, default 4). `--out` renders to another folder.
- **`render_frames.py contrast`**: a caption contrast check measured on the rendered pixels. Headlines need 3:1 (large text) and other caption text 4.5:1. `frame.html` gains `&probe=1` and `&nocap=1` modes for it.
- **`export_svg.py --plan brand/exports.json`** exports the whole brand set from one re-runnable plan (`--only` to pick entries).
  - It accepts several sources per call.
  - It re-checks every file it writes (size, RGB when flattened, not blank) and checks text contrast on HTML sources (4.5:1, or 3:1 for large text; `--no-contrast` skips it).
- **`make_icon_set.py generate --no-web`** skips the favicon and PWA icons for apps with no web target.
- **`.claude/skills/.gitignore`** (new vendored file) keeps the `__pycache__/` folders out of git. Python writes them there when the skills' scripts are imported.
- `tests/store-render.test.sh` (59 checks), run in CI on Linux, macOS and Windows with the runner's Chrome.

### Changed
- **One mockup kit per project.**
  - `render_frames.py init` refuses when the project already has a kit (`--new` overrides) and writes the kit's `.gitignore`.
  - The engine and generated files (`frame.html`, `objects.js`, `frames.generated.js`, `icons.generated.js`, the Ionicons font, copies of project photos) now live in `<kit>/.build/`, which ignores itself. The kit holds only the files you edit.
  - A lock in `.build/` refuses a second render on the same kit while one is running.
- The template `app.css` no longer declares the Ionicons `@font-face`; the build injects it.
- `store-mockups` skill and `store-creative` agent:
  - Reuse the existing kit and render into its gitignored `out/`, not a new dated folder with a copy of the sources.
  - Never run two renders on the same kit at once.
  - Keep rendered PNGs out of git, or use Git LFS.
  - Finish with `render --all`.
- `brand-assets` skill, asset matrix and `brand-asset-creator` agent:
  - A **core set** by default: the six SVG masters, a 2048 mark PNG, the splash image and the OG image.
  - Extra variants, sizes, email headers and promo banners only for a use the owner names.
  - Every export is listed in `brand/exports.json`, and each file is written once, where it's used.
  - No export or verify scripts of the agent's own.
- `snippets/store.md` states the lean-output rules.

### Fixed
- The gitignore guard in `sync.sh` and `harness-doctor.sh` reported a harness file as ignored when a `!` rule re-included it: `git check-ignore -v` also prints negation matches. The guard's suggested fix now lists `!/.claude/skills/.gitignore` too.

### Upgrade notes
- **Existing kits:**
  - `render` prints a NOTE listing the old engine files at the kit root (`frame.html`, `objects.js`, `frames.generated.js`, `icons.generated.js`, `assets/Ionicons.ttf`). They are no longer used; delete them unless you edited them on purpose.
  - A kit without a `.gitignore` gets one on its next render.
- **Old outputs:** earlier dated output folders and copies of the kit are not touched. Delete them yourself once the new `out/` set is signed off.
- **Name clash:** if your project already has its own `.claude/skills/.gitignore`, sync reports it as CONFLICT-UNMANAGED. Merge in `__pycache__/` and `*.pyc` and re-run with `--theirs`.

## [1.3.1] - 2026-09-27

### Fixed
- **Intermittent failures on macOS in `harness-sync`, `harness-doctor` and `sync.sh`.** They read one field from the lock with `tr | awk '… exit'`. Under `pipefail`, awk exiting at the first match broke the pipe while `tr` was still writing (`tr: stdout: Broken pipe`) once the lock outgrew the pipe buffer (16 KB on macOS, 64 KB on Linux). A sync, update or health check could then fail at random. awk now reads the lock directly.
- `detect.sh` (`init.sh` stack detection) used `find | head -n1`, which could fail the same way in a large project; it now uses `find -print -quit`.
- `tests/sync.test.sh` prints the sync or doctor output behind a failed check, which is how the cause above was found in CI.

### Upgrade notes
- Run `bash .claude/harness/bin/harness-sync.sh --remote --commit` to pick up the fixed `harness-sync.sh` and `harness-doctor.sh`.

## [1.3.0] - 2026-09-26

Starter platform baselines move to current releases, verified by installing, type-checking, testing and building the generated projects on Node 22 and 24.

### Changed
- **Frontend starter:** React 19.3, React Router 8 (the `react-router` package replaces `react-router-dom`), Vite 8, Vitest 5, jsdom 30, Testing Library 16 with `@testing-library/dom` declared, Zod 4 and TypeScript 6.0. The tsconfig drops the deprecated `baseUrl` (paths are `./`-relative), the Vite configs use `import.meta.dirname`, components import the `JSX` type from React, and the Dockerfile builds on `node:24-alpine`. `engines.node` is `>=22.22`.
- **Backend starter:** Express 5.2, Mongoose 9, Zod 4, Jest 30 with ts-jest 29.4, supertest 7.3 and TypeScript 6.0 with `node16` module resolution (no deprecated `baseUrl`). `validate()` no longer assigns `req.query`, which is a getter in Express 5 and threw at runtime; a new unit test covers query and body parsing. Dockerfile stages use `node:24-alpine`; `engines.node` is `>=22.22`.
- **Mobile starter:** Expo SDK 57 (React Native 0.86, React 19.2), with every native package at the version `expo install` resolves for that SDK: React Navigation 7, AsyncStorage 2.2, safe-area-context 5.7, screens 4.26. Also `expo-dev-client`, which the `development` EAS profile already declared; jest-expo 57 (Jest 29) with Testing Library 14 and `test-renderer`, whose `render` is now awaited; Zod 4 and TypeScript 6.0. The app starts from an `index.ts` using `registerRootComponent` (replacing `expo/AppEntry`). The custom `babel.config.js` is removed, so Expo's default applies (the file named a preset SDK 57 no longer exposes). The npm script `prebuild` is renamed `native:prebuild`, so npm no longer treats it as a pre-hook, and a new `doctor` script runs `expo install --check` and `expo-doctor`. CI now runs `expo-doctor`, Metro exports for Android and iOS, and `expo prebuild` for both platforms with an assertion on the generated application ID.
- **Android starter:** AGP 9.4 with built-in Kotlin (the `org.jetbrains.kotlin.android` plugin is gone), Kotlin 2.4.20, Compose BOM 2026.09, ktlint-gradle 14.2, Retrofit 3 and current AndroidX, all in a `gradle/libs.versions.toml` catalog. targetSdk 36 is what Google Play requires from 2026-08-31, and compileSdk 37 is what current AndroidX needs. The starter ships the **official Gradle 9.8.0 wrapper** (jar, scripts and a pinned distribution checksum) instead of stub scripts that asked you to generate one, so `./gradlew` works right after stamping. `enableEdgeToEdge()` is on, with the home screen padded for the system bars. `checkFileSize` is now a plain Gradle task (no bash; Windows-friendly and configuration-cache safe). The Kotlin sources are ktlint-clean, with `.editorconfig` allowing PascalCase `@Composable` functions. The anydpi mipmap folder no longer carries a redundant `-v26`. A new CI job validates the wrapper, then assembles, unit-tests, ktlints and lints the generated app.
- **Fixed (macOS):** on the stock `/bin/bash` 3.2 the Android renderer turned `com.example.app` into `com\/example\/app`, so package directories got backslashes in their names. The package path is now computed with `tr`, and the transactional scaffolder's path check is what caught it.
- `tests/scaffold.test.sh`: the build checks now stop at the first failing step (before, only the last command's status counted) and print the log.

### Upgrade notes
- Android: building a stamped project needs a JDK 17+ and an Android SDK. AGP installs the API 37 platform itself once the SDK licences are accepted.
- Only newly stamped projects change. Existing projects keep their dependencies; to follow, apply the same bumps and run the project's checks.
- `npm audit` on the mobile starter reports a moderate `uuid` advisory inside Expo's build tooling (`xcode`); it is not shipped in the app bundle, and the only fix npm offers is a breaking downgrade, so wait for an Expo patch.
- TypeScript stays on 6.0 in the starters: TypeScript 7 (the native compiler) is not yet supported by `ts-jest`, and Expo pins its own version.

## [1.2.0] - 2026-09-26

Store assets get a release gate, and the application scaffolder becomes transactional on a shared renderer core.

### Added
- **`check_store_assets.py --release`** (store-submission-precheck). A submission gate: every slot the declared stores require must hold valid images: Play phone screenshots, exactly one feature graphic and the Play icon; iPhone 6.9″; iPad 13″ when the app supports iPad; and any Play tablet slots you list. Stores and the iPad answer come from `--stores`/`--[no-]supports-tablet` or a `store-assets.json` next to the assets (which can read `supportsTablet` from `app.json` and raise minimum counts). Without them, release mode stops with exit 2 rather than guessing.
- `--json` output with stable finding codes, and `tests/store-assets.test.sh`, which builds its image fixtures with Pillow at run time. CI installs Pillow and runs it on all three OSes.

### Fixed
- **Store asset checks no longer pass on nothing.** Before, a missing or empty screenshot folder was only INFO, and an empty `ios/6.9/` or `ios/ipad13/` passed. Release mode now reports them as errors.
- A corrupt or truncated image is an ERROR line instead of a Python traceback. The real file format is checked (a GIF or WebP renamed `.png` is an error), as are CMYK and 16-bit images. Intermediate `*.raw.png` renders and hidden files are ignored with a warning instead of being counted. More than one feature graphic is an error.
- Play tablet screenshots may be up to 7680 px per side (they were capped at the phone limit of 3840), and a short side under 1080 px warns about large-screen eligibility. `store-specs.md` now states the same limits.

### Changed
- **Scaffold renderers share one core.** `scaffold/lib/render-core.sh` now holds the substitution, write/backup, shared-template, main-pass, per-feature and required-directory logic. Each `render-<platform>.sh` only describes its platform (variables, envsubst whitelist, skip rules, path tokens, item template, required dirs). Generated output is unchanged, which `tests/scaffold-equiv.test.sh` checks against a base ref.
- ShellCheck (via `validate-harness.sh`) now also covers `init-scaffold.sh`, the renderers, `txn.sh` and `manifest.sh`.
- **Application scaffolding is transactional.** `init-scaffold.sh` renders into a staging tree, validates it, and plans against the project before writing anything. Any existing file the starter would replace now stops the run and is listed (previously only seven names were checked and other files were silently kept, leaving a mixed tree). Changes are journaled and a failure rolls the project back. The manifest is written last and records the directories created and the originals `--force` replaced. The journal and lock logic comes from `sync.sh` and is shared through the new `scaffold/lib/txn.sh`.
- `--uninstall` (both `init-scaffold.sh` and `init.sh`) is all or nothing and restores originals that `--force` replaced instead of deleting them.
- New `--dry-run` and `--force-unlock` flags. Exit codes match `sync.sh`: `0` ok, `1` refused with nothing written, `2` failed and rolled back.
- Features named like the built-in example (`health`, or `home` on mobile) or listed twice are rejected up front. A target directory is only created after all input is valid.
- `scripts/*.sh` in every starter are now executable (previously only Android).

### Upgrade notes
- Store gates: run `check_store_assets.py <assets> --release` with `--stores` (or add `store-assets.json`). Inspect mode, without `--release`, keeps the old lenient behaviour for drafts, but corrupt or mis-formatted images are now errors there too.
- Scaffolding into a non-empty project: files that would be replaced now stop the run. Preview with `--dry-run`; use `--force` to replace them (backed up, and restored by `--uninstall`).
- Re-running the scaffolder on a scaffolded project now needs `--uninstall` first, or `--force`.
- Manifests written by this version use a v2 row format. Older scaffolders refuse to uninstall them (no files are touched); this version reads v1 and legacy manifests.

## [1.1.0] - 2026-09-25

Mobile app-store and brand personas, distilled from a real store refresh of an Expo app (device capture → mockups → listing copy → pre-submission checks). Each persona is an Opus agent with its own skill, so they can run on their own or in parallel.

### Added
- **Agents (mobile profile; `brand-asset-creator` also web):**
  - `screen-capturer`: read-only real-device walkthroughs (ADB, or iOS through a connector or the Simulator) into a dated, indexed screenshot folder.
  - `store-creative`: storyboard, captions, demo-data ledger, faithful HTML rebuilds of real screens, every Play and App Store size, the feature graphic, and a contact sheet.
  - `listing-copywriter`: a code-verified claims truth table, then Play and iOS listing fields checked by script.
  - `store-precheck-auditor`: a read-only release gate with a severity-ranked READY / NOT READY report.
  - `icon-creator`: icon audit and generation across iOS, Android adaptive, monochrome, notification, Play and web, plus Expo wiring.
  - `brand-asset-creator`: brief, three logo directions, SVG masters, tokens, splash and social exports.
- **Skills:**
  - `mobile-screen-capture`: workflow, an ADB and an iOS reference, `capture_adb_screenshot.py` (binary-safe PNGs), `ui_dump.py` (tappable elements and their centres), `dedupe_index.py` (exact-hash dedupe plus an INDEX.md skeleton).
  - `store-mockups`: an HTML kit (`frame.html`, `app.css`, example screens, demo data, `frames.json`), `render_frames.py` (headless Chrome/Edge, RGB flatten, exact-size and < 8 MB checks, Ionicons copied from the project's `node_modules`), `contact_sheet.py`, storyboard and demo-data references, and a worked example.
    - **Optional continuous (panorama) style,** chosen per project with `init --style continuous` or `"layout": "continuous"`. The gallery is built as one strip, so a ribbon, coins, receipts, calendar tiles and tilted phones flow across frame edges.
    - It's fully configurable: per-frame backgrounds, caption position and tone, device position and tilt, and an object library in `objects.js` (ribbon, coin, chip, receipt, calendar, toast, card, phone, brand, image, text, html). Projects add their own types in `custom-objects.js`.
    - Guardrails, checked by `render --check-only`: text never crosses a seam; each frame's main phone stays inside it; brand-only frames are Android-only and not first (App Store 2.3.3); every photo needs a `license`.
    - `contact_sheet.py --strip --check-seams` previews the strip the way stores show it and measures continuity at each seam.
  - `store-listing`: a LISTING template with field markers, and `check_listing.py` (limits, iOS keyword hygiene, common banned claims, project `listing-guardrails.txt`). References for field limits, claims guardrails and ASO.
  - `store-submission-precheck`: `store-specs.md` (the single source of truth for store sizes and limits), App Store and Play checklists, cross-document consistency checks, `check_store_assets.py` and `check_public_urls.sh`.
  - `app-icons`: `make_icon_set.py` (`generate` from one master glyph; `check` for an Expo `app.json`), icon specs, in-app icon rules.
  - `brand-assets`: `export_svg.py` (SVG/HTML to exact-size PNGs), a logo master template, an Open Graph template, logo principles, the asset matrix.
- **Routing:** a `store` checklist snippet (mobile only), prompt-router keywords (store, ASO, screenshots, icons, logo, splash, ADB, Data safety), and file-context paths (`app.json`, `eas.json`, `store-assets/`, `fastlane/`, `*.xcassets`, `res/mipmap-*`). Session start shows the store roster where it's installed.
- **Validator:** rejects binary files under `harness/` (sync would corrupt them), checks CRLF in `html/css/js/svg/template/txt` files, and compiles every harness `*.py`.
- **Tests:** mobile and web profile installs, backend exclusion, the new prompt and file routes, the session roster, and the new validator failures.

### Changed
- The `.gitignore` fix that sync suggests now lists the harness skills the project's profile actually installs, instead of a fixed list.
- Reserved names (sync's conflict message and reserved-agent check, harness README, harness skill, INSTALL) include the six new agents and skills.

### Upgrade notes
- **Mobile projects** receive six new agents under `.claude/agents/` and six skills under `.claude/skills/` on the next sync. If a `.gitignore` rule hides `.claude/skills/`, sync names the rule and prints the exceptions to add.
- If a project already has its own agent or skill with one of the new names, sync reports CONFLICT-UNMANAGED. Rename yours, then re-run.
- The new scripts need **Python 3.9+ with Pillow** (`pip install pillow`). Rendering also needs **Chrome, Chromium or Edge**.

## [1.0.3] - 2026-09-24

Found by piloting 1.0.2 on a real project (`quantqbit-site`).

### Fixed
- **Harness files hidden by `.gitignore`:** a project rule such as `/.claude/skills/` silently kept the harness skills out of git, so teammates would never get them. Sync now refuses before writing anything, names the rule and suggests the narrower rule (`/.claude/skills/*` plus `!` lines for the harness skills). A dry run warns instead. The doctor reports an error for already-installed harness files that are ignored.
- **`--commit` failing silently:** when `git add` or `git commit` failed, sync stopped with no message. It now says the sync was applied, shows the commit message to use and exits 1.
- **Line-ending warnings on Windows:** the shipped `.claude/.gitattributes` asked for CRLF `.ps1` files while sync writes LF, and had no rule for `.gitattributes`/`.gitignore`. All of these are now LF (PowerShell runs LF scripts fine).
- **CI:** the Ubuntu hook test fixture lacked a shebang, which failed only where shellcheck is installed; the Actions steps moved off Node 20.

### Upgrade notes
- If sync reports ignored harness files, narrow the named `.gitignore` rule as suggested, commit, and re-run.

## [1.0.2] - 2026-09-24

A second end-to-end verification of 1.0.1 (clean clone, plugin install and update, a newcomer following GETTING-STARTED.md on Windows and WSL, live headless sessions, an adversarial diff review) found these; each was reproduced independently before fixing.

### Fixed
- **Guard bypass (security):** in 1.0.1 a newline after an allowed metadata command (`ls`, `git status`, `Get-ChildItem`) let a following `.env` read through. The exemption now applies per command segment (newline, `;`, `&&`, `||`, `&`), and any piping, redirection, grouping or substitution disables it. Brace expansion (`{.env,x}`), NTFS stream names (`.env:x`) and trailing dots are also caught. `grep --exclude=.env* …; git check-ignore .env` is no longer a false positive.
- **Dangerous CRLF recovery advice:** the command in the 1.0.1 doctor, guide and changelog (`… && git checkout -- .claude`) failed and left every `.claude` file staged for deletion. Corrected to `git rm -r --cached -q .claude && git checkout HEAD -- .claude`.
- **`--commit` over-reach:** uncommitted `settings.project.json` edits were committed even when the sync changed nothing. It is now committed only when this run regenerated `settings.json` from it; otherwise sync warns.
- **Slow sync on Windows:** staging now uses one batched awk and one `mkdir` instead of about five forks per file, and the apply loop no longer forks for `dirname`. First installs drop from 70–110 s to well under the 2-minute tool timeout.
- **`sync.sh --help`** printed only the title line.
- **Write gate:** it now has its own per-agent marker, so a checklist the prompt router already showed no longer skips it. If the marker cannot be written, the hook falls back to inform, so it can never deny forever.
- **`--profiles`** is now saved even when `harness.config` does not exist; a plain sync falls back to the lock's profiles before auto-detecting.
- **Smaller fixes:**
  - A non-strict-JSON `settings.json` at migration gets a clear message, not "python 3 is required".
  - `--dry-run` now warns about uncommitted harness paths that the real run would refuse.
  - A project agent that keeps a reserved `name:` is flagged.
  - Uninstall mentions a leftover `.claude/harness/.backup/` and removes empty dirs.
  - `harness.config` is pinned to LF.
  - The ineffective `Write(path)` deny rules were removed (Edit rules cover writes); the validator rejects them.
  - Prompt-router false positives for plain "session", "ci", "cd" and "workflow" were removed.
  - The Makefile recipe works from paths containing spaces again.

### Changed
- Docs: plugin commands are namespaced (`/quantqbit-claude-rules:init-project-rules`), realistic hook latency, lock/settings merge-conflict steps, the rename-and-commit conflict fix, `.gitignore` advice for `.env*`, a local pre-tag test step, and `vX.Y.Z` placeholders instead of untagged versions.

### Upgrade notes
- Projects on 1.0.0 or 1.0.1: `bash .claude/harness/bin/harness-sync.sh --dry-run`, then `--commit`.
- If you ran the 1.0.1 CRLF command and have staged deletions under `.claude/`, run `git restore --staged .claude` first.

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
- **Windows clones made before this release:** commit or stash `.claude` edits, then re-checkout once to pick up LF scripts: `git rm -r --cached -q .claude && git checkout HEAD -- .claude`. (The command first published here, ending in `git checkout -- .claude`, fails and stages deletions; see 1.0.2.)
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
