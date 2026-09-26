# Project review — 2026-09-25

The review covered the harness installation/update lifecycle, metadata ownership,
hooks and settings policy, scaffold rendering, generated application helpers,
asset-checking scripts, and CI coverage. Existing staged store-mockup changes
were preserved. This is a maintenance review, not a claim that every possible
runtime, native build, or security scenario has been verified.

## Corrected findings

| Priority | Finding | Change |
| --- | --- | --- |
| High | Sync and scaffold uninstall trusted paths from manifests/locks; traversal or symlinked destinations could reach outside the intended tree. | Added path preflight before mutation and bounded uninstall directory pruning to the target. |
| High | Generated backend returned internal server-error messages to clients and accepted invalid HTTP status values. | Sanitized server responses, validated status codes, and delegated errors after headers were sent. Request IDs now precede JSON parsing. |
| High | Scaffold renderers could overwrite files such as README.md without `--force`, because the initial conflict list was incomplete. | All four platform writers preserve existing files unless force is requested. |
| Medium | `--src-dir` changed some references but left source files, compiler paths and test paths under `src`. | Made backend/frontend/mobile source paths and associated configuration templates consistent. Rejected unsafe source paths and unsafe project-name template values. |
| Medium | Empty-only or missing-only hash batches emitted no records. | Fixed the AWK join to identify its input file explicitly; added batch edge-case coverage. |
| Medium | `--theirs` completed its transaction before saving persistent backups. | Keep rollback active through backup persistence and use distinct per-process backup directories. |
| Medium | Backend TTL cache retained unlimited never-read keys and expired one tick late. | Added configurable bounded FIFO eviction, exact-deadline expiry and validated TTL/capacity inputs. |
| Medium | Retry accepted zero, fractional or infinite attempt counts; the first delay ignored its cap. | Validate attempts and timer ranges, cap the first delay, and test final-error propagation. |
| Medium | Fetch wrappers discarded Headers/tuple inputs; mobile URL joining could omit a slash. | Normalize headers through Headers, preserve multipart boundary handling, and normalize mobile relative URLs. |
| Medium | Backend/frontend lint scripts hid failures; frontend ESLint could not parse TypeScript. | Use a failing TypeScript check followed by size reporting; remove unused/broken ESLint scaffolding. This is a type-check gate, not a full style lint suite. |
| Medium | Mobile starter imported an undeclared gesture-handler dependency and allowed tests to pass with none discovered. | Removed the unnecessary import for the native-stack starter and require test discovery. |
| Low | Backend carried a UUID dependency for functionality already supplied by Node. | Use `node:crypto` randomUUID and remove UUID packages. |
| Low | Windows validation repeatedly probed Python launchers; sync tests spawned a hash process for every file. | Cache interpreter discovery per shell and calculate test-tree fingerprints in one Python process. |

## Verification

- Harness hooks: 72 checks passed, including policy, routing, JSON and deduplication.
- Validator: 20 scenarios passed, including deliberately invalid fixtures.
- Sync: 137 checks passed in Linux, including idempotence,
  rollback, migration, ownership, profiles, uninstall and CRLF behavior.
- Added helper regressions for empty/missing hash batches and path containment.
- All four platform render tests passed, including preserving an existing README.
- Generated backend: TypeScript build and 10 tests passed.
- Generated frontend: TypeScript/Vite build and 5 tests passed.
- Generated mobile: TypeScript check and 3 tests passed.
- All three generated JavaScript lint commands passed. Harness ShellCheck and
  Claude marketplace/plugin validation passed independently.
- Generated application checks used a custom `source` directory with optional
  auth/i18n and feature folders enabled, under Windows Node 20.20.1.
- Native Android/iOS builds and device runs were not performed.

The repository now runs generated-project checks on Ubuntu in CI and weekly.
This catches dependency-resolution drift even when no template changes land.
The Android CI scenario checks generation only. CI uses Node 22 for the
generated starters; that runner configuration was added but has not run remotely
as part of this local review.

## Remaining gaps and next maintenance work

1. **Modernize platform baselines as tested migrations.** *Done (2026-09-26):*
   frontend React 19 / Vite 8, backend Express 5 / Jest 30, mobile Expo SDK 57
   (versions from `expo install`), Android AGP 9.4 / Kotlin 2.4 / targetSdk 36
   (Play's current requirement) / compileSdk 37. Each starter was installed,
   type-checked, tested and built on Node 22.23 and 24.21 (WSL); the backend
   server answered `/healthz`; the Android APK ran on an API 37 emulator.
   `npm audit` is clean except a moderate `uuid` advisory inside Expo's build
   tooling (see CHANGELOG). Re-run this for every baseline bump.
2. **Add native CI.** *Done:* the committed Gradle wrapper matches Gradle's
   published checksum and is validated in CI; the `android-native` job builds,
   unit-tests, ktlints and lints the generated app, and the mobile starter
   job runs `expo-doctor`, Metro exports and `expo prebuild` for both platforms.
   Still open: an APK or iOS build from the Expo prebuild (needs NDK/Xcode;
   a scheduled job is the natural home) and on-device checks in CI.
3. **Make application scaffolding transactional.** *Done:* `init-scaffold.sh`
   stages and validates the full tree, plans against the project (refusing
   before any write), applies through the journal in `scaffold/lib/txn.sh`, and
   commits a v2 manifest recording origins and backups. `tests/scaffold.test.sh`
   covers conflicts, `--force` restore, locking, symlinks and a fault-injection
   matrix. Moving `sync.sh` onto `txn.sh` is optional follow-up work.
4. **Strengthen database lifecycle handling.** The SQL migration runner has
   per-file transactions but no cross-process migration lock or applied-file
   checksum. The server shutdown path does not close optional DB connections.
   Add database-backed integration tests before changing these contracts.
5. **Separate partial asset inspection from release completeness.** *Done:*
   `check_store_assets.py --release` requires every slot of the declared stores
   (from `--stores` or `store-assets.json`), rejects corrupt and mis-formatted
   images, and `tests/store-assets.test.sh` covers empty, corrupt and
   incomplete submissions with fixtures generated at run time.
6. **Treat hooks as guidance, not a security boundary.** The guard documents
   best-effort shell/JSON matching and indirect-read limitations. Enforce secret
   isolation through actual tool permissions and environment controls as well.
7. **Reduce renderer duplication.** *Done:* shared logic lives in
   `scaffold/lib/render-core.sh`; each platform renderer is a descriptor with
   its own variables, whitelist, path and feature mappings. Output equivalence
   is checked by `tests/scaffold-equiv.test.sh`.
8. **Make builds reproducible at project adoption.** Generate and commit a lockfile
   after creating a starter, use `npm ci` thereafter, and audit resolved packages.
   The template repository cannot supply one shared lockfile for all platforms.

## Maintenance contract

- Run helper, hook, validator, sync and scaffold suites before a harness release.
- Run `SCAFFOLD_BUILD=1 bash tests/scaffold.test.sh` for template changes.
- Run `SCAFFOLD_EQUIV_BASE=<ref> bash tests/scaffold-equiv.test.sh` for renderer
  refactors that must not change generated output (CI: run the workflow manually
  with `equiv_base` for Linux and macOS bash 3.2).
- Treat a weekly CI failure as dependency drift to investigate, not something to
  silence with `|| true` or a no-tests success flag.
- Regenerate `harness/manifest.tsv` after changes under `harness/`.
- For a published release, update VERSION, plugin metadata and CHANGELOG together.
  This review does not publish a release or assign a new version.
