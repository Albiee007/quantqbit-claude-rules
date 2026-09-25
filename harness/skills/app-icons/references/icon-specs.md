# App icon specifications

Store listing sizes are in [store-specs](../../store-submission-precheck/references/store-specs.md). This file covers the **in-binary** icons.

## iOS
- **Master:** 1024 × 1024 PNG, **opaque** (no alpha), square corners. The system applies the mask, so don't draw rounded corners or a glossy shine.
- **iOS 18+:** optional **dark** (transparent background, the glyph lit for dark mode) and **tinted** (greyscale, which the system tints) variants. In Expo: `ios.icon: { light, dark, tinted }`; natively: `AppIcon.appiconset` appearances.
- **Legibility:** the icon must read at 40 px (Spotlight) and 29 pt (Settings). Avoid thin strokes, text and photographic detail.

## Android
- **Adaptive icon (API 26+):** a 108 × 108 dp canvas made of a **foreground** layer (a glyph on transparency) and a **background** layer (a colour or an image).
  - **Safe zone:** a circle of **66 dp** diameter in the centre (61% of the canvas). Launchers mask to circles, squircles or teardrops, and anything outside 72 dp can be cut off. Parallax moves the layers up to 18 dp.
  - Expo: `android.adaptiveIcon.foregroundImage` (1024 × 1024 PNG with transparency), `backgroundColor` or `backgroundImage`.
  - **An opaque foreground is a defect:** the mask crops the artwork and `backgroundColor` never shows.
- **Monochrome (Android 13+ themed icons):** `android.adaptiveIcon.monochromeImage`, a glyph whose alpha alone carries the shape (the system tints it). If it's missing, themed launchers show the full-colour icon among tinted ones.
- **Notification icon:** a **white silhouette on transparency**, 96 × 96 px source (24 dp; system sizes are 24/36/48/72/96 px). Android ignores colour and uses only the alpha, so an opaque or coloured icon shows as a solid square. Expo: `["expo-notifications", { "icon": "./…/notification-96.png", "color": "#hex" }]`. The `color` tints the icon in the expanded notification.
- **Legacy launcher icon (pre-26):** `mipmap-*/ic_launcher.png` (48/72/96/144/192 px). Expo generates it from `icon`.
- **Play Store icon:** 512 × 512, full-bleed square. Play applies the mask and shadow.

## Web and PWA
- `favicon.ico` (16/32/48), a 48 px PNG favicon, `apple-touch-icon` 180 × 180 opaque, PWA icons at 192 and 512, and a **maskable** 512 icon with its content inside the central 80% circle.

## Design rules for all platforms
- **One strong, simple shape** that survives 16 px and a circle mask. Test the icon at 16, 29, 40, 48 and 64 px.
- **No words.** At most one letter, and only if it's the brand mark.
- **Contrast:** at least 3:1 between the glyph and the background (WCAG non-text contrast).
- **Consistency:** the same mark on the store icon, the launcher, the splash and the favicon, and the same colours as the brand tokens.
- **No third-party marks** (Apple, Google, payment networks) inside the icon.
