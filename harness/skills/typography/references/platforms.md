# Platforms

Implement type tokens in each platform's native scaling model. Never port a px scale to native platforms as fixed numbers.

## Web
- **Units:** font sizes in `rem` (relative to the user's default); `em` for component-relative sizing; unitless `line-height`. No `px` on text, no pure `vw`.
- **Fluid type:** `clamp(min-rem, rem + vw, max-rem)` ([hierarchy-and-measure](hierarchy-and-measure.md)). Container queries with `cqi` plus a `rem` term for component-level scaling.
- **`font-size-adjust`** (Baseline 2024) keeps x-height consistent across fallback fonts: `font-size-adjust: ex-height from-font`.
- **`text-size-adjust`:** controls mobile text inflation; not Baseline, prefixed in WebKit. Use `-webkit-text-size-adjust: 100%` only to stop landscape inflation; **never `none`**, which can block users' text enlargement.
- **Never disable zoom:** no `user-scalable=no` or `maximum-scale=1` in the viewport meta.
- **Logical properties** for all inline spacing and alignment (`margin-inline`, `padding-block`, `text-align: start`) so RTL works ([multilingual-and-rtl](multilingual-and-rtl.md)).
- Tokens: CSS custom properties (`--font-size-body: 1rem`), the Tailwind theme, or DTCG tokens compiled to both. Components consume tokens, not literals.

## React Native
- **`allowFontScaling` defaults to `true`.** Keep it. Don't turn it off globally (for example via `Text.defaultProps`).
- **`maxFontSizeMultiplier`:** caps scaling per node; `0` means no cap; unset inherits. Use a cap only on space-constrained chrome (tab bar labels, badges) and keep it generous (for example 1.5–2, heuristic); never on body text. Better: let layout adapt.
- **`PixelRatio.getFontScale()`** reads the current scale to switch layouts (stack horizontal rows vertically at large scales), not to shrink text.
- **`adjustsFontSizeToFit`** shrinks text to fit: avoid for essential content; it defeats the user's chosen size.
- **`numberOfLines`** truncates: only for non-essential previews with the full text reachable.
- **`fontVariant`:** `tabular-nums`, `lining-nums`, `oldstyle-nums`, `proportional-nums`, `small-caps`.
- **Numeric sizes are unitless dp,** already multiplied by the user font scale when `allowFontScaling` is on. They aren't px debt; don't convert them.
- **`fontFamily`** takes a single name (no CSS-style stack, no fallback). Wrap `Text` in shared components (`AppText`, `AppHeading`) that apply tokens.
- **Per-locale or per-script family map** in the shared component, since there's no fallback stack:
  ```ts
  const families = { latin: 'Brand-Regular', ar: 'NotoSansArabic-Regular', ja: undefined /* system */ };
  const fontFamily = families[scriptFor(locale)] ?? families.latin;
  ```
  Pick per-script `lineHeight` from the same map (taller scripts need more). Text in an unexpected script (user content) falls back to the system font per glyph on each OS; check it renders and fits.
- **Custom font naming:** Android resolves the family from the font filename, iOS from the name inside the font. Name files after the PostScript name; with static files, each weight may need its own `fontFamily` name on Android unless registered as a family.
- **`includeFontPadding`** (Android, default `true`) adds extra top and bottom padding; set `false` with `textAlignVertical: 'center'` when vertical centering is off, then recheck tall scripts for clipping.
- **`lineHeight`** is an absolute number, not a multiplier: derive it from the size token (`size * ratio`). With `allowFontScaling` on, current React Native source scales it with the font scale on both platforms (Android converts it as sp; iOS multiplies by the effective font size multiplier), and `maxFontSizeMultiplier` caps both. Older versions and the legacy iOS renderer not verified: confirm on device. Overlap at large scales usually comes from fixed container `height`s or a `lineHeight` tuned for Latin applied to a taller script.
- **Android 14+ nonlinear scaling:** current React Native source converts sp with `TypedValue.applyDimension`, which follows the nonlinear curve, so large sizes grow proportionally less. Not verified for older RN versions; test at 200%.
- `system-ui`, `ui-serif`, `ui-monospace`, `ui-rounded` generic families work on iOS.

## Android (Compose and Views)
- **`sp` for text size and line height,** `dp` for layout. Line height in `sp` or `em` so it scales with the text.
- **Nonlinear font scaling (Android 14+):** user font scale goes up to 200%, and large text grows proportionally less than small text to preserve hierarchy. Don't compute sizes with `Configuration.fontScale` or `scaledDensity`; use `TypedValue.applyDimension` / `deriveDimension` for sp↔px conversion.
- **Compose:** define one `Typography(...)` with all M3 roles set from project tokens and pass it to `MaterialTheme`; read via `MaterialTheme.typography.bodyLarge`. Customize with `TextStyle.copy()` or `merge()`, not new literals.
- **Fonts:** `FontFamily(Font(R.font.x, FontWeight.Normal), ...)` from `res/font`; variable fonts with `FontVariation.Settings(FontVariation.weight(...), ...)` on Android 8.0+; downloadable Google Fonts via `GoogleFont.Provider` with a fallback family.
- **`includeFontPadding`** now defaults to `false` in Compose (since the 2024.01 BOM). **`LineHeightStyle`** controls where text sits inside its line height (`Alignment.Center`, `Proportional`, and others) and trimming of the first and last line (`Trim.Both`, `FirstLineTop`, `LastLineBottom`; trim needs `includeFontPadding = false`).
- **Avoid fixed heights** on anything containing text (`Modifier.height` on buttons, rows, chips); use `heightIn(min = ...)` so it grows. Use `softWrap`, and `maxLines` with `overflow` only for non-essential text.
- **Views:** `TextAppearance.*` styles with `android:textSize` and `android:lineHeight` in `sp`; `wrap_content` heights; `autoSizeTextType` only where shrinking is acceptable.

## Apple (SwiftUI and UIKit)
- **Dynamic Type text styles first:** `.font(.body)`, `.headline`, `.largeTitle` in SwiftUI; `UIFont.preferredFont(forTextStyle:)` in UIKit. They scale through every content size, including the accessibility sizes, and get system tracking and optical sizing.
- **Custom fonts:** SwiftUI `.font(.custom("Brand-Regular", size: 17, relativeTo: .body))` scales relative to a text style (`custom(_:size:)` scales relative to body; `custom(_:fixedSize:)` doesn't scale: avoid for content). UIKit: `UIFontMetrics(forTextStyle: .body).scaledFont(for: base)`, optionally with `maximumPointSize` for tight chrome only.
- **`adjustsFontForContentSizeCategory = true`** on labels, text fields and text views so they update live; it works only for fonts from `preferredFont` or `UIFontMetrics`.
- **`@ScaledMetric(relativeTo: .body)`** scales spacing, icon sizes and paddings with text; `UIFontMetrics.scaledValue(for:)` in UIKit.
- **Accessibility sizes:** test the largest. Switch `HStack` to `VStack` (`ViewThatFits`, or `dynamicTypeSize.isAccessibilitySize`), allow multi-line labels (`lineLimit(nil)`), don't truncate. Use `.dynamicTypeSize(...)` range limits only on chrome that can't grow, never on content.
- **SF Pro:** a variable system font with dynamic optical sizes and per-size tracking; let the system apply them rather than choosing Text or Display cuts in code. Avoid Ultralight, Thin and Light for UI text.
- **Legibility weight:** respect the Bold Text setting (`legibilityWeight == .bold` in SwiftUI, `UIAccessibility.isBoldTextEnabled` in UIKit); system fonts handle it, custom fonts need you to map to a heavier weight.
- Register bundled fonts under `UIAppFonts` ([loading-and-licensing](loading-and-licensing.md)).

## Sources
- [CSS Fonts 5](sources.md#w3c) and [MDN font-size-adjust](sources.md#web-platform-docs), accessed 2026-10-02.
- [MDN text-size-adjust](sources.md#web-platform-docs), accessed 2026-10-02.
- [Understanding 1.4.4](sources.md#w3c) (viewport units failure), accessed 2026-10-02.
- [React Native Text](sources.md#platforms) and [text style props](sources.md#platforms), accessed 2026-10-02.
- [React Native source: Android TextAttributes/PixelUtil, iOS RCTAttributedTextUtils](sources.md#platforms) (lineHeight scaling, `applyDimension`), main branch, accessed 2026-10-02.
- [Expo fonts guide](sources.md#platforms) (naming differences), accessed 2026-10-02.
- [Android 14 nonlinear font scaling](sources.md#platforms), [Compose fonts](sources.md#platforms), [Compose paragraph style](sources.md#platforms), [fonts in XML](sources.md#platforms), accessed 2026-10-02.
- [Apple HIG Typography](sources.md#platforms), [UIFontMetrics](sources.md#platforms), [adjustsFontForContentSizeCategory](sources.md#platforms), [Font.custom relativeTo](sources.md#platforms), [ScaledMetric](sources.md#platforms), accessed 2026-10-02 via the developer documentation data endpoint.
- Not verified this pass: Bold Text APIs (`legibilityWeight`, `isBoldTextEnabled`), `ViewThatFits`, `dynamicTypeSize` modifiers, the React Native static-weight family naming detail, and per-glyph system fallback for unmatched scripts in RN; they're stated from platform knowledge.
