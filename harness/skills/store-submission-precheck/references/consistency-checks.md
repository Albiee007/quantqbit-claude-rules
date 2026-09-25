# Cross-document consistency checks

Most store rejections and 1-star "this is misleading" reviews come from two documents disagreeing, not from any single mistake. For each pair, find both sides, quote them, and report the mismatch.

| Check | Side A | Side B | Typical failure |
|---|---|---|---|
| Paywalls | iOS review notes ("no subscriptions or paywalls") | Listing, screenshots or in-app entitlements (a Premium tier, locked features) | Apple 2.1 or 3.1.1 rejection, or reviewers finding a paywall the notes denied |
| Platform-gated features | Code gates (`Platform.OS === 'android'`, server `X-Client-Platform`) | iOS listing text and iOS screenshots | An iOS listing promising Android-only SMS import or receipt scanning |
| Server feature flags | Backend config (`FEATURE_X_ENABLED`, `.env.example` defaults) | Listing copy promising the feature | A feature that's off in production but advertised |
| Data collection | Code uploads (API payloads, SDKs) | Play Data safety, Apple App Privacy, and the public privacy policy | A Data safety rejection (e.g. undeclared contacts) |
| Permissions | Merged manifest / Info.plist purpose strings | Listing and privacy policy | A permission requested that no feature explains |
| Sign-in methods | Auth screens in the build | Copy ("Sign in with Apple, Google or email") | Copy naming a method the build doesn't have |
| Currencies, regions, languages | The real supported lists in code | Copy numbers ("28 currencies", "10 languages") | A number that is true for one feature but written as if it applied to everything |
| Screenshots vs build | Mockup screens | The current UI | 2.3.3: labels, tabs or flows that changed since the screenshots were made |
| Pricing | Store product prices (local currency) | Any price in copy or images | A fixed price that's wrong in other countries |
| Names | App name, bundle display name, icon wordmark | Listing title | An old brand left in `app.json`, the icon or the web manifest |

## How to find side A quickly
- **Entitlements and paywalls:** grep the code for `premium|entitlement|paywall|isPro|subscription`, then read the tier defaults.
- **Platform gates:** grep for `Platform.OS|isAndroid|isIOS|X-Client-Platform`.
- **Feature flags:** grep `.env.example` and the config modules for `_ENABLED`.
- **Uploads:** grep the API services for payload fields, and list the SDKs in `package.json` or the Gradle and Pods files.
- **Review notes:** usually in a release runbook (`*RUNBOOK*.md`, `*SUBMISSION*.md`) or in App Store Connect. Ask for them if they aren't in the repo.

When side B lives outside the repo (App Store Connect answers, the Play Console form, production env), report it as **NOT-VERIFIABLE**. Name the exact field to check, and never assume it is correct.
