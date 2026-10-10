---
name: store-submission-precheck
description: Release gate for Google Play and Apple App Store submissions — audits store assets (sizes, alpha, counts), listing metadata, privacy disclosures (Data safety, App Privacy, privacy manifest), restricted permissions, in-app purchase and paywall consistency, review notes, public policy URLs, and cross-document contradictions, then returns a severity-ranked report. Use when preparing a mobile release or store listing update, before pressing Submit for Review or promoting a Play release, or when a store rejection needs diagnosing. Read-only; never edits.
---

# Store Submission Pre-check

A read-only audit that answers one question: **will this submission be accepted, and is everything it claims true?** Report findings with evidence; never fix them yourself. Fixes belong to `listing-copywriter`, `store-creative`, `icon-creator` or `implementor`.

## Inputs
- The mobile project (Expo `app.json`/`eas.json`, or native `android/` and `ios/`).
- The store-asset folder (screenshots, feature graphic, icons), the listing copy (`LISTING.md` or fastlane metadata), and any release runbook or review notes.
- Anything that can't be seen from the repo (App Store Connect answers, the Play Console forms, production env) is marked **NOT-VERIFIABLE**, with the exact field the owner must check.

## Workflow
1. **Inventory the release.** Record:
   - app id / bundle id, version and build number, and target platforms;
   - `supportsTablet`, since it decides whether iPad screenshots are needed;
   - the permissions requested, the sign-in methods, and whether IAP or subscriptions exist per platform.
2. **Check the assets in release mode:**
   `python .claude/skills/store-submission-precheck/scripts/check_store_assets.py <assets-root> --release`
   This checks every image against [store-specs](references/store-specs.md): exact sizes, no alpha where forbidden, per-slot counts, file size, and that each file really is an undamaged PNG or JPEG. In release mode, every slot the declared stores require must hold images; see **Release mode** below.
3. **Check the public URLs:**
   `bash .claude/skills/store-submission-precheck/scripts/check_public_urls.sh <privacy> <terms> <support> <data-deletion>`
   Any non-200 is a metadata rejection.
4. **Run the platform checklists:** [app-store-checklist](references/app-store-checklist.md) and [play-checklist](references/play-checklist.md). Every line gets PASS, FAIL, NOT-VERIFIABLE or N/A, with a file:line or command output as evidence.
5. **Run the consistency checks:** [consistency-checks](references/consistency-checks.md). These cover paywalls vs review notes, platform-gated features vs per-platform copy, feature flags vs claims, and uploads vs Data safety.
6. **Check the copy's limits and guardrails:** if the listing uses `store-listing` field blocks, run `python .claude/skills/store-listing/scripts/check_listing.py <LISTING.md>`.
7. **Report** in the format below. Rank the blockers first.

## Release mode
Without `--release` the checker only inspects what exists, so a missing folder passes; use that for drafts. For a submission, declare what is being shipped in `<assets-root>/store-assets.json` (paths are relative to the file):
```json
{"version": 1, "stores": ["play", "ios"],
 "ios":  {"app_json": "../app.json", "icon": "../assets/icon.png"},
 "play": {"icon": "../assets/play-icon-512.png", "tablet_slots": ["tablet10"]},
 "min_counts": {"play-phone": 4}}
```
- **Required with `--release` (harness defaults, from [store-slots.json](references/store-slots.json)):**
  - Play: phone screenshots, exactly one feature graphic, and the Play icon. Tablet slots are required when listed in `tablet_slots`.
  - iOS: iPhone 6.3″ screenshots (`ios/6.3`, 1206 × 2622 or 1179 × 2556). iPad 13″ when the app supports iPad (`ios.supports_tablet`, or read from `app_json`).
  - 6.9″ and 6.5″ are optional. See store-specs for why.
- **When the store asks for something else, declare it in `store-assets.json` `slots`.** Never edit the harness or write a one-off script.
  - Add a slot: `"ios-6.1": {"store": "ios", "folder": "ios/6.1", "sizes": ["1179x2556"], "need": "always"}`. A slot gives `store`, `folder` (inside `play/` or `ios/`), and either exact `sizes` or `{"rule": {"maxSide": N}}`. `count` and `need` are optional.
  - Change a built-in slot: `"ios-6.9": {"need": "always"}`. It takes `need`, `count` and `sizes` only.
  - `need` is one of `always`, `tablet`, `declared` (listed in `play.tablet_slots`) or `optional`.
  - Landscape sizes are accepted automatically.
- **`unknown-folder`:** images in a folder under `play/` or `ios/` that no slot reads (`ios/6.1/`, `ios/6.3/old/`) are a warning when inspecting and an ERROR with `--release`. Declare the folder or move the files.
- `--stores` and `--[no-]supports-tablet` override the file. Without either source of truth the check stops with exit 2 rather than guessing.
- Exit 0 = no errors, 1 = errors (each one is a BLOCKER), 2 = bad arguments or config. `--json` gives machine-readable findings.

## Severity
| Severity | Meaning | Examples |
|---|---|---|
| BLOCKER | The store will reject it, or it breaks a policy | A screenshot with alpha or the wrong size; a privacy URL returning 404; a restricted permission with no declaration; a paywall with no IAP on iOS |
| HIGH | A likely rejection, or a false claim to users | Copy promising a feature that's off in production; a Data safety form missing a data type; review notes contradicting the listing |
| MEDIUM | A quality or ranking loss | Fewer than 4 phone screenshots at 1080 px or more; an opaque adaptive icon foreground; a keyword field wasting bytes |
| LOW | Polish | Weak captions; an outdated What's New |

## Rules
- **Never edit files, submit builds, or touch store consoles.** Report only.
- **Verify before reporting.** Read the actual config and code. Label a finding `PLAUSIBLE` if you can't confirm it, and say what would confirm it.
- **Keep secrets out of the report:** never print tokens, keystore passwords, or `.env` values.
- **Don't guess what's outside the repo.** Production flags, console forms and the signed entitlements are NOT-VERIFIABLE until the owner confirms them.
- **Specs change.** If a check depends on a number in store-specs.md, say so, and link to the official page for re-checking.

## Report format
```
## Store pre-check — <app> <version> (<platforms>) — <date>
Verdict: READY | READY-WITH-FIXES | NOT READY

### Blockers
- [BLOCKER] <area> — <finding>. Evidence: <path:line | command output>. Fix: <specific change> (owner: <agent/person>).
### High / Medium / Low
- …
### Not verifiable from the repo
- <console / server item> — check: <exact field or command>.
### Passed
- <checklist areas that fully passed, one line each>
```

## References
- [store-specs](references/store-specs.md): every size, format, count and text limit (the single source of truth).
- [store-slots.json](references/store-slots.json): the same screenshot slots as data, read by `check_store_assets.py` and `store-mockups`. Projects extend it from `store-assets.json`, never by editing it.
- [app-store-checklist](references/app-store-checklist.md), [play-checklist](references/play-checklist.md)
- [consistency-checks](references/consistency-checks.md)
- Scripts: [check_store_assets.py](scripts/check_store_assets.py), [check_public_urls.sh](scripts/check_public_urls.sh)
