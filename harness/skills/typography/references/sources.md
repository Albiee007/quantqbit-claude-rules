# Sources

Dated index for the typography skill. "Accessed 2026-10-02" means the page was fetched successfully on that date and the cited points were checked against it. "Not accessed" means cited by title only; contents not verified. All guidance in this skill is paraphrased.

## W3C
- WCAG 2.2 (W3C Recommendation, 12 Dec 2024): SC 1.4.4, 1.4.8, 1.4.10, 1.4.12. https://www.w3.org/TR/WCAG22/ (accessed 2026-10-02)
- Understanding SC 1.4.4 Resize Text (failures F69, F80, F94). https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html (accessed 2026-10-02)
- Understanding SC 1.4.8 Visual Presentation (AAA; 80 characters, 40 for CJK). https://www.w3.org/WAI/WCAG22/Understanding/visual-presentation.html (accessed 2026-10-02)
- Understanding SC 1.4.10 Reflow (320 CSS px, 256 CSS px, two-dimensional exceptions). https://www.w3.org/WAI/WCAG22/Understanding/reflow.html (accessed 2026-10-02)
- Understanding SC 1.4.12 Text Spacing (override values, script exception, user-side tools). https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html (accessed 2026-10-02)
- CSS Fonts Module Level 4 (Working Draft, 13 Sep 2026): font-display, metric override descriptors, font-variation-settings, font-optical-sizing, font-variant-numeric. https://www.w3.org/TR/css-fonts-4/ (accessed 2026-10-02)
- CSS Fonts Module Level 5 (Working Draft, 13 Sep 2026): size-adjust, font-size-adjust metric keywords and from-font. https://www.w3.org/TR/css-fonts-5/ (accessed 2026-10-02)
- CSS Text Module Level 3 (Candidate Recommendation Draft, 14 Aug 2026): word-break, line-break, hyphens and language, text-transform. https://www.w3.org/TR/css-text-3/ (accessed 2026-10-02)
- W3C Internationalization: Structural markup and right-to-left text in HTML. https://www.w3.org/International/questions/qa-html-dir (accessed 2026-10-02)
- W3C Internationalization: Styling using language attributes. https://www.w3.org/International/questions/qa-css-lang (accessed 2026-10-02)
- W3C Internationalization: Text size in translation. https://www.w3.org/International/articles/article-text-size (accessed 2026-10-02)
- Requirements for Chinese Text Layout (CLREQ, Group Note Draft, 1 Sep 2026). https://www.w3.org/TR/clreq/ (accessed 2026-10-02)
- Requirements for Japanese Text Layout (JLREQ). https://www.w3.org/TR/jlreq/ (accessed 2026-10-02)

## Web platform docs
- web.dev: Best practices for fonts. https://web.dev/articles/font-best-practices (accessed 2026-10-02)
- MDN: `size-adjust` descriptor (Baseline widely available; across browsers since September 2023). https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/size-adjust (accessed 2026-10-02)
- MDN: `font-display` descriptor. https://developer.mozilla.org/en-US/docs/Web/CSS/@font-face/font-display (accessed 2026-10-02)
- MDN: `font-size-adjust`. https://developer.mozilla.org/en-US/docs/Web/CSS/font-size-adjust (accessed 2026-10-02)
- MDN: `text-size-adjust`. https://developer.mozilla.org/en-US/docs/Web/CSS/text-size-adjust (accessed 2026-10-02)
- MDN: `font-variant-numeric`. https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric (accessed 2026-10-02)
- MDN: CSS Font Loading API. https://developer.mozilla.org/en-US/docs/Web/API/CSS_Font_Loading_API (accessed 2026-10-02)
- Astro: Using custom fonts (`fonts` config option, `<Font />` from `astro:assets`, providers incl. Fontsource). https://docs.astro.build/en/guides/fonts/ (accessed 2026-10-02)

## Unicode and OpenType
- UAX #9 Unicode Bidirectional Algorithm (Unicode 18.0.0, revision 52, 2026-09-01). https://www.unicode.org/reports/tr9/ (accessed 2026-10-02)
- UAX #14 Unicode Line Breaking Algorithm (Unicode 18.0.0, 2026-09-01). https://www.unicode.org/reports/tr14/ (accessed 2026-10-02)
- OpenType spec index (OpenType 1.9.1). https://learn.microsoft.com/en-us/typography/opentype/spec/ (not accessed directly; individual tables below were)
- OpenType `head` table (unitsPerEm). https://learn.microsoft.com/en-us/typography/opentype/spec/head (accessed 2026-10-02)
- OpenType `hhea` table. https://learn.microsoft.com/en-us/typography/opentype/spec/hhea (accessed 2026-10-02)
- OpenType `OS/2` table (typo and win metrics, USE_TYPO_METRICS, sxHeight, sCapHeight). https://learn.microsoft.com/en-us/typography/opentype/spec/os2 (accessed 2026-10-02)
- OpenType design-variation axis tag registry. https://learn.microsoft.com/en-us/typography/opentype/spec/dvaraxisreg (accessed 2026-10-02)
- HarfBuzz text shaping library. https://harfbuzz.github.io/ (accessed 2026-10-02)

## Platforms
- Apple HIG: Typography (HTML page is script-rendered; content read from the documentation data endpoint https://developer.apple.com/tutorials/data/design/human-interface-guidelines/typography.json). https://developer.apple.com/design/human-interface-guidelines/typography (accessed 2026-10-02)
- Apple: `UIFontMetrics` (via data endpoint). https://developer.apple.com/documentation/uikit/uifontmetrics (accessed 2026-10-02)
- Apple: `adjustsFontForContentSizeCategory` (via data endpoint). https://developer.apple.com/documentation/uikit/uicontentsizecategoryadjusting/adjustsfontforcontentsizecategory (accessed 2026-10-02)
- Apple: `Font.custom(_:size:relativeTo:)` (via data endpoint). https://developer.apple.com/documentation/swiftui/font/custom(_:size:relativeto:) (accessed 2026-10-02)
- Apple: `ScaledMetric` (via data endpoint). https://developer.apple.com/documentation/swiftui/scaledmetric (accessed 2026-10-02)
- Apple: `UIAppFonts` (via data endpoint). https://developer.apple.com/documentation/bundleresources/information-property-list/uiappfonts (accessed 2026-10-02)
- Android: Work with fonts in Compose. https://developer.android.com/develop/ui/compose/text/fonts (accessed 2026-10-02)
- Android: Style paragraph in Compose (LineHeightStyle, includeFontPadding). https://developer.android.com/develop/ui/compose/text/style-paragraph (accessed 2026-10-02)
- Android: Add a font as an XML resource. https://developer.android.com/guide/topics/ui/look-and-feel/fonts-in-xml (accessed 2026-10-02)
- Android 14 features: nonlinear font scaling to 200%. https://developer.android.com/about/versions/14/features#non-linear-font-scaling (accessed 2026-10-02)
- Material Components for Android: Typography doc (M3 baseline roles and sizes). https://github.com/material-components/material-components-android/blob/master/docs/theming/Typography.md (accessed 2026-10-02, raw file)
- Material Design 3: Type scale tokens. https://m3.material.io/styles/typography/type-scale-tokens (not accessed — cited by title; contents not verified)
- React Native: Text. https://reactnative.dev/docs/text (accessed 2026-10-02)
- React Native: Text style props. https://reactnative.dev/docs/text-style-props (accessed 2026-10-02)
- Expo: Fonts. https://docs.expo.dev/develop/user-interface/fonts/ (accessed 2026-10-02)
- Expo: Localization guide (RTL: `expo-localization` plugin options `supportsRTL`/`forcesRTL`, `Updates.reloadAsync()`, iOS `supportedLocales`). https://docs.expo.dev/guides/localization/ (accessed 2026-10-02)
- React Native: I18nManager (`allowRTL`, `forceRTL` take effect on next app start). https://reactnative.dev/docs/i18nmanager (accessed 2026-10-02)
- React Native source, Android `TextAttributes.kt` (lineHeight via `toPixelFromSP` when `allowFontScaling`) and `PixelUtil.kt` (`TypedValue.applyDimension(COMPLEX_UNIT_SP)`), main branch. https://github.com/facebook/react-native/tree/main/packages/react-native/ReactAndroid/src/main/java/com/facebook/react (accessed 2026-10-02, raw files)
- React Native source, iOS `RCTAttributedTextUtils.mm` (lineHeight multiplied by `RCTEffectiveFontSizeMultiplierFromTextAttributes`), main branch, New Architecture renderer. https://github.com/facebook/react-native/tree/main/packages/react-native/ReactCommon/react/renderer/textlayoutmanager (accessed 2026-10-02, raw file)

## Licensing and font sources
- SIL Open Font License site. https://openfontlicense.org/ (accessed 2026-10-02; the OFL-FAQ document was not read)
- Noto fonts project (OFL-1.1). https://github.com/notofonts (accessed 2026-10-02)
- Apache License 2.0. https://www.apache.org/licenses/LICENSE-2.0 (not accessed — cited by title; contents not verified)

## Research
- Baymard Institute: Readability, the optimal line length. https://baymard.com/blog/line-length-readability (accessed 2026-10-02)
- Wery, J. J. & Diliberto, J. A. (2017). The effect of a specialized dyslexia font, OpenDyslexic, on reading rate and accuracy. Annals of Dyslexia 67(2), 114–127. doi:10.1007/s11881-016-0127-1. Abstract read via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1007/s11881-016-0127-1 and metadata via https://api.crossref.org/works/10.1007/s11881-016-0127-1 (accessed 2026-10-02; full text not read)
- Rello, L. & Baeza-Yates, R. (2013). Good fonts for dyslexia. ASSETS '13. doi:10.1145/2513383.2513447. Metadata via https://api.crossref.org/works/10.1145/2513383.2513447 (accessed 2026-10-02; abstract and findings not accessed — not verified)

## Inaccessible or not verified
- m3.material.io (script-rendered; no content returned). The Material Components Android typography doc was used instead.
- Apple developer HTML pages return no content to a plain fetch; the JSON data endpoints above were used.
- PubMed and Europe PMC (cookie wall, HTTP 403), ACM Digital Library (HTTP 403), SpringerLink (authentication redirect): full papers not read.
- fonts.google.com/noto (script-rendered); the Noto GitHub organization was used instead.
- OFL-FAQ, Apache License 2.0 text, the OpenType spec index page: not fetched.
- Android "Make apps more accessible" page was fetched but contained no text-scaling guidance, so it isn't cited.
