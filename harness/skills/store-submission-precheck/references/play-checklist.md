# Google Play pre-submission checklist

Each item says **how to verify** it. Mark every item PASS, FAIL, NOT-VERIFIABLE or N/A, with evidence.

## Build
- [ ] **versionCode increased** and **versionName set**; in Expo, `android.versionCode` / `version` (or EAS `autoIncrement`).
- [ ] **Target API level** meets Play's current requirement (check the policy page; it rises every year).
- [ ] **App Bundle (.aab) signed** with the upload key; Play App Signing enrolled.
- [ ] **Permissions:** the merged manifest contains only permissions the app uses. Strip unused ones with a config plugin in Expo, because `android/` is regenerated. Check with `aapt dump permissions` or the Play Console bundle explorer.

## Restricted and sensitive permissions
- [ ] **SMS and Call Log** (`READ_SMS`, `RECEIVE_SMS`, `READ_CALL_LOG` …) are allowed only for approved core uses, and expense tracking is *not* on the default list. You need an accepted Permissions Declaration, or remove the permission. Even with a declaration, upload only the parsed fields, never raw message bodies.
- [ ] **Contacts, location, camera:** each needs a user-visible purpose, and a request made in context.
- [ ] **`QUERY_ALL_PACKAGES`, accessibility services, `MANAGE_EXTERNAL_STORAGE`:** avoid them, or declare and justify them.
- [ ] **Foreground service types** declared if any are used.

## Data safety form (Play Console)
- [ ] Every data type the app **collects or shares** is declared: contacts, financial info, messages, identifiers, photos and so on, with purpose, optional or required, and whether it's encrypted in transit.
- [ ] **Matches the privacy policy and the code.** A past rejection came from undeclared contact uploads. Trace every upload in the code: API payloads, analytics SDKs, crash reporters.
- [ ] **Account deletion:** an in-app path **and** a web URL for deletion requests.

## Store listing
- [ ] **Title** (30) states the brand and at most a short descriptor. No "best", "#1", "free" or emoji spam, and no keyword stuffing.
- [ ] **Short description (80) and full description (4000)** are accurate. Premium features are marked, and there's no claim the build can't back (see the `store-listing` skill's guardrails).
- [ ] **Graphics:** icon 512, feature graphic 1024 × 500, and 2–8 phone screenshots (at least 4 at 1080 px or more for recommendations), per [store-specs](store-specs.md). Run `check_store_assets.py`.
- [ ] **Content rating questionnaire** complete; **target audience** set (declaring children brings Families policy duties).
- [ ] **Ads declaration** correct; **app access** instructions and a demo login for reviewers if the app is gated behind a login.

## Release
- [ ] **Internal or closed testing track first.** New personal developer accounts must run a closed test with the required number of testers and days before production.
- [ ] **Staged rollout** percentage chosen; release notes (500) written.
- [ ] **Pre-launch report** reviewed: crashes, accessibility, security warnings.
