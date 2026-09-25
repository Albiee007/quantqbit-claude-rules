# App Store (iOS) pre-submission checklist

Each item says **how to verify** it. Mark every item PASS, FAIL, NOT-VERIFIABLE (outside the repo) or N/A, with evidence.

## Build and binary
- [ ] **Version and build number** increased; `app.json` / `Info.plist` / `package.json` agree.
- [ ] **Current SDK:** the build uses the Xcode and iOS SDK Apple currently requires (see "submit apps"). In EAS, pin the image rather than using `latest`.
- [ ] **Export compliance:** `ITSAppUsesNonExemptEncryption` is set. In Expo, `ios.config.usesNonExemptEncryption`; verify with `npx expo config --type introspect`, because `--type public` strips this key.
- [ ] **Privacy manifest:** `PrivacyInfo.xcprivacy` (Expo `ios.privacyManifests`) declares the required-reason APIs you actually use (UserDefaults CA92.1, FileTimestamp C617.1, DiskSpace E174.1, SystemBootTime 35F9.1 and so on). If one is missing, Apple sends an ITMS-91053 email after upload.
- [ ] **Push entitlement:** `aps-environment` is `production` in the **signed** archive. Check it in Xcode Organizer; the project file only states the intent.
- [ ] **Background modes** declared only where there's a handler (no silent-push mode without one).
- [ ] **OTA updates:** changes delivered over the air must not change the app's primary purpose (2.5.2). Keep automatic updates conservative.

## Account, auth and privacy
- [ ] **Sign in with Apple** offered if any third-party sign-in (Google, Facebook) is offered (4.8). Test cancellation, repeat sign-in, and private-relay email.
- [ ] **Account deletion** available in the app (5.1.1(v)), including revoking the Apple token and reauthenticating.
- [ ] **App Privacy questionnaire** in App Store Connect answered. This is **separate from** the privacy manifest, and the two must agree. Cover data types, purposes, linkage and tracking.
- [ ] **Permission prompts** appear only after a user action, with a purpose string that says why (e.g. `NSContactsUsageDescription`, `NSCameraUsageDescription`).
- [ ] **ATT prompt** only if the app tracks across apps. With no tracking SDK, there's no ATT prompt.
- [ ] **Public URLs return HTTP 200:** privacy, terms, support/help, and data deletion. Run `bash .claude/skills/store-submission-precheck/scripts/check_public_urls.sh <urls…>`.

## Payments
- [ ] **Digital features or content** sold in the app use In-App Purchase (3.1.1). Real-world payments between people, such as settling a debt through an external payment app, are not digital goods.
- [ ] **If there's no IAP on iOS,** no paywalled feature appears in iOS screenshots or copy as if it could be bought. The review notes must agree with the listing (see [consistency-checks](consistency-checks.md)).
- [ ] **Subscriptions** show their price, period and terms before purchase, and link to the terms and privacy policy.

## Product page
- [ ] **Screenshots:** 6.9″ (plus iPad 13″ if the app supports iPad), with sizes and no alpha per [store-specs](store-specs.md). Run `python .claude/skills/store-submission-precheck/scripts/check_store_assets.py <folder>`.
- [ ] **Screenshots match the submitted build** (2.3.3); recapture if the UI changed. Mockups must be faithful rebuilds of real screens.
- [ ] **No Android-only features, Google Play wording or Android frames** in iOS assets.
- [ ] **Name, subtitle and keywords** within their limits; no competitor trademarks in keywords (2.3.7).
- [ ] **Age rating, DSA trader status, pricing and territories** complete.

## Review package
- [ ] **Reviewer demo account** that works against production, with seeded data and a step-by-step review path.
- [ ] **Review notes** explain non-obvious flows: external payment hand-offs, platform-gated features, why permissions are asked for.
- [ ] **Core functions work without optional integrations** (e.g. when an external payment app isn't installed).

## Device gate (TestFlight)
Test on a physical device: fresh install, upgrade, login, logout, deletion, permissions allowed and denied, deep and universal links, offline and error states, safe areas, keyboard, VoiceOver spot check, and Larger Text.
