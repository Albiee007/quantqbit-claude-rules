---
name: app-icons
description: Mobile app icon production and audit — iOS 1024 opaque icon (plus iOS 18 dark/tinted), Android adaptive foreground/background with safe zones, Android 13 monochrome themed icon, notification silhouette, Play 512 icon, favicon/PWA/maskable set, Expo app.json wiring, and in-app UI icon consistency. Use when creating or replacing an app icon, fixing launcher/notification icon problems, preparing icon assets for a store release, or auditing icon configuration.
---

# App Icons

Make one mark work everywhere, from a 1024 px store tile to a 24 dp status-bar silhouette, and wire it correctly into the app's config.

## Inputs
- **A master glyph:** SVG, or a transparent PNG of at least 1024 px. If only an SVG exists, export it with `brand-assets` (`export_svg.py --size 2048x2048`). If there's no mark yet, get one from `brand-asset-creator` first.
- **The brand background colour and accent,** taken from the theme or brand tokens.
- **The project type:** Expo (`app.json`), native Android (`res/mipmap-*`, `ic_launcher.xml`) or native iOS (`Assets.xcassets/AppIcon.appiconset`).

## Workflow
1. **Audit what ships today:**
   `python .claude/skills/app-icons/scripts/make_icon_set.py check --app-json app.json`
   It checks:
   - the iOS icon is 1024 × 1024 and opaque;
   - the adaptive foreground has transparency and sits inside the safe zone;
   - `monochromeImage`, the notification icon (a white silhouette on transparency), the splash, and the favicon size.

   For native projects, inspect the same points by hand against [icon-specs](references/icon-specs.md).
2. **Design check on the master:**
   - one simple shape that survives 16 px and a circle mask;
   - no text, and no third-party marks;
   - at least 3:1 contrast on the background colour.

   Preview it at 16, 29, 40, 48 and 64 px before generating.
3. **Generate the set:**
   `python .claude/skills/app-icons/scripts/make_icon_set.py generate --master <glyph.png> --bg "#RRGGBB" --out assets/icons`
   - It produces the opaque iOS icon, the adaptive foreground and background, the monochrome and notification silhouettes, the Play 512, and the favicon, apple-touch, PWA and maskable icons.
   - It also writes `expo-icon-snippet.json`.
   - `--glyph-scale` (default 0.6) sets how much of the tile the glyph fills. The adaptive and maskable versions are capped to their safe zones automatically.
   - Monochrome and notification icons keep only the alpha channel. If the mark relies on inner colour contrast (e.g. a check drawn in brand colour inside a white disc), pass `--mono <cut-out.png>`, a single-colour master with those details transparent, or the silhouette becomes a solid blob. Always open `android/monochrome.png` and look at it.
4. **Wire it up.**
   - **Expo:** merge the snippet into `app.json`: `icon`, `android.adaptiveIcon.{foregroundImage, backgroundColor, monochromeImage}`, and the `expo-notifications` `icon`/`color`. Add iOS dark and tinted variants via `ios.icon` if you have them.
   - **Native:** Android `mipmap-anydpi-v26/ic_launcher.xml` with `<foreground>`, `<background>` and `<monochrome>`; iOS `AppIcon.appiconset`.
5. **Verify.**
   - Re-run `check` until there's nothing at MEDIUM or above.
   - Build a dev client and look at the result on a device: the launcher with circle and squircle masks, the themed-icon setting, a real push notification, and iOS light, dark and tinted home screens.
6. **In-app icons.** If the task touches UI icons, follow [in-app-icons](references/in-app-icons.md): one family, outline vs filled by state, a size scale, accessible names.

## Rules
- **Never overwrite existing icon files in place** without the owner's go-ahead. Generate into a new folder, then switch the config.
- **The iOS icon is always opaque, and the notification icon is always white on transparency.** These aren't style choices.
- **Keep third-party logos out** of icons and UI icon sets (store IP rules).
- **Changing the app icon changes the brand:** show the owner a before and after preview before switching the config.
- **Store listing icons** (Play 512, App Store 1024) must match the launcher icon. `store-precheck-auditor` checks them against [store-specs](../store-submission-precheck/references/store-specs.md).

## Output
- An icon folder with every size listed above, the Expo snippet or native resource changes, and the `check` output before and after.
- A short report: the defects found, the files generated, the config changed, and the on-device checks still to do.

## References
- [icon-specs](references/icon-specs.md): platform specs, safe zones, notification rules.
- [in-app-icons](references/in-app-icons.md): UI icon family rules.
- Script: [make_icon_set.py](scripts/make_icon_set.py).
