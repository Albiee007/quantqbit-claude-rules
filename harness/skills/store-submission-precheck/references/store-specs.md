# Store specifications (single source of truth)

The other store skills (`store-mockups`, `store-listing`, `app-icons`, `brand-assets`) link here instead of repeating these numbers. Check the official pages before a release: stores change these specs without notice. Last reviewed 2026-10-10.

The screenshot slots below are also data: [store-slots.json](store-slots.json) holds each slot's folder, sizes, count and when it is required, and both `check_store_assets.py` and `store-mockups` read it. These are the **harness defaults**. When a store asks for something else, a project declares it in its own `store-assets.json` `slots` (a new slot, or a different `need`, `count` or `sizes` for a built-in one) and in `frames.json` `sizes` for rendering. It never edits the harness files. See the store-submission-precheck skill, **Release mode**.

## Google Play

| Asset | Size / format | Count | Notes |
|---|---|---|---|
| App icon | 512 × 512, 32-bit PNG (alpha allowed), ≤ 1024 KB | 1 | Full-bleed square. Play applies the rounded mask and shadow, so don't bake them in |
| Feature graphic | 1024 × 500, JPEG or 24-bit PNG, **no alpha** | 1 (required) | Keep the key content away from the centre, where a video play button can be overlaid, and away from the edges |
| Phone screenshots | JPEG or 24-bit PNG, no alpha; each side 320–3840 px; the long side at most 2× the short side | 2–8 | For recommendation eligibility, use **at least 4 at 9:16 (or 16:9) with a short side of at least 1080 px**. 1080 × 1920 is the safe default |
| 7″ tablet screenshots | same format; each side 320–7680 px, long side at most 2× the short side; e.g. 1200 × 1920 | up to 8 | Needed for the tablet listing. Large-screen recommendations want every side 1080–7680 px (16:9 or 9:16) |
| 10″ tablet screenshots | same format and limits; e.g. 1620 × 2880 or 1600 × 2560 | up to 8 | Short side 1080–7680 px for large-screen eligibility |
| Promo video | YouTube URL, ads off | 0–1 | |
| Each image file | ≤ 8 MB | | |

**Play text limits:** title 30 characters, short description 80, full description 4000, release notes 500 per language.

## Apple App Store

| Asset | Size / format | Count | Notes |
|---|---|---|---|
| App icon | 1024 × 1024 PNG, **no alpha**, no rounded corners | 1 | iOS applies the mask. iOS 18+ can also take dark and tinted variants in the asset catalog |
| iPhone 6.3″ screenshots (App Store Connect: "iPhone with Dynamic Island, medium display"; also serves 6.1″) | 1206 × 2622 or 1179 × 2556 (portrait; landscape is the same numbers swapped) | 1–10 | **Required** for iPhone apps (slot `ios-6.3`, folder `ios/6.3`) |
| iPhone 6.9″ screenshots ("large display") | 1290 × 2796, 1320 × 2868 or 1260 × 2736 | 1–10 | Optional (slot `ios-6.9`). Apple scales screenshots down to smaller displays, never up, so a 6.3″ set can't fill this slot |
| iPhone 6.5″ screenshots | 1242 × 2688 or 1284 × 2778 | 1–10 | Optional fallback (slot `ios-6.5`). See the note below |
| iPad 13″ screenshots | 2064 × 2752 or 2048 × 2732 | 1–10 | Required **only** when the app supports iPad (`ios.supportsTablet: true` in Expo) |
| App previews | 15–30 s video per size | 0–3 | Must show the app itself |
| Screenshot format | JPEG or PNG, RGB, **no alpha channel** | | App Store Connect rejects images with alpha. Flatten them |

**Which iPhone set is required (checked 2026-10-10).** Apple's "Required device sizes" list names the medium Dynamic Island iPhone (6.3″), plus iPad 13″ when the app runs on iPad. The 6.5″ row of the same page still says it is required when large Dynamic Island (6.9″) screenshots aren't provided, which contradicts that list. The harness defaults follow the required-device list: `ios-6.3` always, `ios-6.9` and `ios-6.5` optional, `ios-ipad13` when the app supports iPad. If App Store Connect asks for a different set, override `need` in the project's `store-assets.json` (e.g. `"slots": {"ios-6.5": {"need": "always"}}`) instead of waiting for a harness release.

**iOS text limits:** app name 30 characters, subtitle 30, promotional text 170 (can change without a new version), keywords **100 bytes** (comma-separated, no spaces after commas, don't repeat words from the name or subtitle), description 4000, What's New 4000.

**Changing the name or subtitle** needs a new app version submitted for review. Promotional text doesn't.

## Content rules that apply to images
- **Apple 2.3.3 / 2.3.4:** screenshots and previews must show the app in use and match the submitted build. Frames and captions are fine; features that aren't in the app are not. Don't use Android device frames on iOS, or the other way round.
- **Apple 2.3.7, Google metadata policy:** no other apps' names, trademarks or prices; no fake ranking claims ("#1"); no misleading badges.
- **Both stores:** no real customer data in screenshots. Use fictional, internally consistent demo data.
- **Platform-gated features** (e.g. Android-only SMS import) must not appear in the other platform's images or copy.
- **Galleries draw gaps between frames,** and search results show frames one at a time. In continuous (panorama) sets, only decoration may cross a frame edge. Text and a frame's main phone stay inside one frame.

## Official references
- Play: [Store listing assets](https://support.google.com/googleplay/android-developer/answer/9866151), [Metadata policy](https://support.google.com/googleplay/android-developer/answer/9898842)
- Apple: [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/), [App information](https://developer.apple.com/help/app-store-connect/reference/app-information/), [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
