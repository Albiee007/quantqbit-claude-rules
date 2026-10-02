# Multilingual and RTL Typography

Treat every supported language, and every script that user-generated content can contain, as a first-class rendering target.

## Shaping
- Shaping turns a Unicode character sequence into positioned glyphs: contextual forms, ligatures, mark placement, reordering. It's done by the platform engine: HarfBuzz (Android, Chrome, Firefox, Linux, many apps), CoreText (Apple), DirectWrite (Windows). HarfBuzz can also run on top of those stacks.
- You don't implement shaping, but you can break it: by applying letter spacing to cursive scripts, by splitting strings into styled spans mid-cluster, by disabling required ligatures, or by choosing a font without the script's OpenType layout tables.
- **Never** render text by drawing characters one at a time (canvas loops, per-letter animation spans) for complex scripts.

## Complex scripts
- **Arabic, Persian, Urdu:** letters join and change form by position; marks stack above and below. No `letter-spacing`, no per-character styling, no synthetic italic. Line height usually needs to be generous for marks. Urdu often uses the Nastaliq style, which is much taller: test separately.
- **Indic (Devanagari, Bengali, Tamil, and others):** conjuncts and vowel signs that reorder visually before the consonant; a headline (shirorekha) in Devanagari. Never break or style between a consonant and its marks. Allow extra line height.
- **Thai, Lao, Khmer, Myanmar:** no spaces between words; stacked vowel and tone marks above and below. Line breaking needs dictionary-based segmentation, which UAX #14 leaves to the implementation: test on real devices and browsers.
- **Vietnamese:** stacked diacritics on Latin letters; check the font has the precomposed and combining forms, and clearance at tight line heights.

## CJK (Chinese, Japanese, Korean)
- Han and kana are set on a square character frame with no extra spacing between characters (solid setting). **No letter-spacing** on CJK body text.
- **Line height:** CJK typically needs more than Latin; JLREQ describes a line gap of roughly 50–100% of the character size. Start around 1.6–1.8 for body (heuristic) and test.
- **Measure** counts characters on the grid. WCAG 1.4.8 (AAA) caps at 40 characters for CJK; JLREQ describes line length as a multiple of the character size.
- **Punctuation** is full-width and occupies a full frame; placement differs by region (centered in Traditional Chinese for Taiwan and Hong Kong, at the corner for Mainland Simplified). The font must match the region.
- **Line breaking:** prohibition rules (kinsoku) keep closing punctuation from starting a line and opening brackets from ending one. CSS `line-break: strict` applies stricter rules; `normal` is usually right for UI.
- **Korean** uses spaces between words: `word-break: keep-all` keeps words whole instead of breaking between any syllables.
- Bold and italic: many CJK fonts have few weights; italic is not a CJK convention, so use weight, color or emphasis marks (`text-emphasis`) instead.
- Font files are large: subset or use `unicode-range` slicing ([loading-and-licensing](loading-and-licensing.md)).

## Line breaking and hyphenation
- UAX #14 defines break opportunities; browsers and platforms tailor it per language. Let the platform break lines; don't insert manual breaks in translatable strings.
- CSS: `word-break: normal | break-all | keep-all`, `line-break: auto | loose | normal | strict | anywhere`, `overflow-wrap: anywhere` for long URLs and IDs in narrow containers.
- `hyphens: auto` only works when the content language is known: set `lang` on the element or an ancestor. Hyphenation quality varies by browser and language; test the target locales.
- Long compound words (German, Finnish, Dutch) overflow narrow buttons and table headers: allow wrapping or `hyphens: auto` with `lang`.

## Bidirectional text (RTL)
- UAX #9 resolves mixed-direction text. Base direction comes from markup, not CSS: `<html dir="rtl" lang="ar">`. Don't use CSS `direction` for base direction.
- **Logical properties** everywhere: `margin-inline-start`, `padding-inline-end`, `inset-inline-start`, `text-align: start`, `border-start-start-radius`. Native: `start`/`end` in Compose and Android XML, leading/trailing in SwiftUI and Auto Layout, `start`/`end` style props in React Native.
- **Isolate user or data content** whose direction is unknown: `dir="auto"` on the element, `<bdi>` for inline values (usernames, product names), Unicode isolates (FSI…PDI) in plain-text contexts like notifications. Isolates replaced the older embedding controls because embeddings leaked into surrounding text.
- **Numbers in RTL:** digits keep left-to-right order inside RTL text; phone numbers, ranges and versions with neutral separators can reorder. Wrap them in an LTR isolate when order matters. Some locales use native digits (Arabic-Indic, Persian): format with the locale's number formatter, not string concatenation.
- **Mirroring:** brackets mirror automatically. Mirror directional icons (back, forward, progress, reply, undo in some cases, list bullets); don't mirror icons of real-world objects (clocks, media play, checkmarks, logos). Charts' time axes generally stay LTR unless research for the locale says otherwise.
- Use `dirname` on form fields when submitted text direction matters downstream.

### Native RTL
- **React Native:** layout follows `I18nManager.isRTL`. `I18nManager.allowRTL(bool)` and `forceRTL(bool)` persist and take effect on the **next app start**, not immediately; reload after changing them (Expo: `Updates.reloadAsync()` from `expo-updates`, not in Expo Go). `forceRTL` is for testing, not production.
- **Expo app config:** RTL options go on the `expo-localization` plugin: `"plugins": [["expo-localization", { "supportsRTL": true }]]`; `"forcesRTL": true` for testing. On iOS the device language must also be in the app's `supportedLocales`.
- **RN text:** `textAlign: 'auto'` (default) follows natural direction; Expo docs note `'left'` behaves as start in RTL layouts (left/right swap), so use `'right'` only for deliberate physical alignment. `writingDirection` (`'auto' | 'ltr' | 'rtl'`) is iOS-only. Use `start`/`end` style props (`marginStart`, `paddingEnd`) over left/right.
- **Android:** `android:supportsRtl="true"` on `<application>`; `start`/`end` attributes (`layout_marginStart`, `paddingEnd`, `gravity="start"`) in XML; Compose follows `LocalLayoutDirection` and uses start/end automatically.
- **Apple:** UIKit `semanticContentAttribute` (`.forceLeftToRight` for media controls and similar), leading/trailing constraints, `.natural` text alignment; SwiftUI `\.layoutDirection` environment (override in previews to test RTL) and `.flipsForRightToLeftLayoutDirection(true)` on directional images.

## Language tagging and glyph selection
- Set `lang` on the root and on any element whose language differs. It drives font fallback, hyphenation, `text-transform` rules (Turkish dotted i), quotes and line breaking.
- **Han unification:** one code point can need different glyph shapes in Japanese, Simplified Chinese, Traditional Chinese and Korean. With correct `lang` (`ja`, `zh-Hans`, `zh-Hant`, `ko`), fonts with locale-specific forms and system fallback pick the right shapes. Without it, users see the wrong regional glyphs.
- Use `:lang()` selectors to assign per-language families or line heights in CSS; it respects inheritance.
- Native: set the locale on text (Compose `LocaleList` in `TextStyle`, Android `textLocale`, Apple `NSAttributedString` language attribute) when mixing CJK languages in one view.

## Fallback coverage per script
- For each supported script, name the font that renders it on each platform (brand font, then system or bundled fallback). Missing glyphs show as tofu boxes or as a mismatched system face.
- Noto is a broad-coverage open-source family set (OFL) intended to cover Unicode scripts; use it as a coverage option or reference, not a default brand choice. Bundle only the scripts you need.
- Tune each fallback's size to the primary font's x-height (`size-adjust` per `@font-face`, or per-script token sizes): some scripts look small at the same nominal size.

## Text expansion
- Translations are longer than English, especially short strings. W3C's guidance (citing IBM figures): strings up to about 10 characters can grow 200–300%; around 11–20 characters about 180–200%; long text over about 70 characters about 130%. Plan for **at least 30% on paragraphs and much more on labels**.
- Some scripts are taller (Thai, Arabic, Devanagari) or wider (CJK full-width) regardless of character count.
- Never size buttons, tabs or table columns to English text. Don't abbreviate to fit; other languages may have no abbreviation.

## Testing
- **Pseudo-localization** (heuristic, standard i18n practice): accented and padded strings (about +30–50% length, wrapped in brackets) reveal hard-coded strings, truncation and concatenation. Android has built-in pseudolocales (`en-XA` accented, `ar-XB` RTL) in developer options; enable `pseudoLocalesEnabled` in the build.
- Test one real RTL locale, one CJK locale, one complex-script locale and the longest-string locale on each platform.
- Test mixed content: an English product name inside Arabic text, a Hebrew username inside an English list, numbers and URLs in RTL.

## Sources
- [HarfBuzz](sources.md#unicode-and-opentype) (shaping; integration with CoreText, DirectWrite, Uniscribe), accessed 2026-10-02.
- [UAX #9 Bidirectional Algorithm](sources.md#unicode-and-opentype) (isolates, mirroring), accessed 2026-10-02.
- [UAX #14 Line Breaking](sources.md#unicode-and-opentype) (tailoring, SA class dictionary breaking), accessed 2026-10-02.
- [CSS Text 3](sources.md#w3c) (word-break, line-break, hyphens and `lang`), accessed 2026-10-02.
- [W3C: Structural markup and right-to-left text in HTML](sources.md#w3c) (dir, dir=auto, bdi, dirname, logical properties), accessed 2026-10-02.
- [W3C: Styling using language attributes](sources.md#w3c) (`:lang()`, regional font preference), accessed 2026-10-02.
- [JLREQ](sources.md#w3c) and [CLREQ](sources.md#w3c) (solid setting, line gap, punctuation, prohibition rules), accessed 2026-10-02.
- [Understanding 1.4.8](sources.md#w3c) (40-character CJK measure), accessed 2026-10-02.
- [W3C: Text size in translation](sources.md#w3c) (expansion figures), accessed 2026-10-02.
- [Noto fonts project](sources.md#licensing-and-font-sources), accessed 2026-10-02.
- [Expo localization guide](sources.md#platforms) (`expo-localization` RTL options, `reloadAsync`, `textAlign: 'left'`), [React Native I18nManager](sources.md#platforms) (next-start behaviour), [React Native text style props](sources.md#platforms) (`writingDirection` iOS-only, `textAlign` values), accessed 2026-10-02.
- Not verified this pass: `android:supportsRtl`, Compose `LocalLayoutDirection`, UIKit `semanticContentAttribute`, SwiftUI `layoutDirection` and `flipsForRightToLeftLayoutDirection`; stated from platform knowledge.
- Android pseudolocale names, script-specific line-height notes and the icon-mirroring list are platform and i18n practice not verified against a fetched page in this pass.
