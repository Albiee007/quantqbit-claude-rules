# Context Discovery

Gather evidence before choosing sizes, fonts or ratios. Every type decision should be traceable to at least one item below. If an item can't be found, write the assumption down and mark it unverified.

## Evidence checklist

### People and reading
- [ ] **Audience:** age range (older readers need larger defaults and more contrast), expertise (experts tolerate density), accessibility needs stated in the brief or support tickets.
- [ ] **Reading context:** glance (dashboards, notifications, wayfinding), scan (lists, settings, e-commerce), sustained reading (articles, docs, contracts). Viewing distance (phone, desktop, TV, kiosk).
- [ ] **Usage conditions:** outdoor glare, motion (in-vehicle, walking), low-end devices, slow networks.

### Content
- [ ] **Density:** rows per screen, numbers per view, typical string length. Data-heavy views need tighter scales and tabular numerals.
- [ ] **Content types:** long prose, short UI labels, tables, code, formulas, user-generated text (unknown length and script), legal text.
- [ ] **Hierarchy depth:** how many heading levels real content uses. Count them on representative screens; don't assume six.

### Brand
- [ ] **Brand voice and existing guidelines:** `brand/`, `docs/brand*`, design-system site, Figma library notes, the `brand-assets` output.
- [ ] **Brand typefaces** already licensed, and whether the wordmark uses one of them.
- [ ] **Constraints:** a parent brand, white-label or theming per tenant, regulatory text rules.

### Platforms and languages
- [ ] **Platforms:** web (which browsers), React Native or Expo, Android (Compose or Views, min SDK), Apple (SwiftUI or UIKit, min OS). Each has its own scaling model ([platforms](platforms.md)).
- [ ] **Supported languages and scripts:** i18n config (`i18n.*`, `locales/`, `messages/`, `values-*/strings.xml`, `*.lproj`, `Localizable.xcstrings`), the locale switcher, the roadmap. Note RTL locales (ar, he, fa, ur) and CJK.
- [ ] **User-generated content** that can arrive in any script, even if the UI isn't localized.

## Inventory: fonts and where they load
Grep for these and record each hit (family, weights, formats, file size, loader):
- Web: `@font-face`, `font-family`, `<link rel="preload"`, `fonts.googleapis`, `use.typekit`, `next/font`, `@fontsource/*` and `@fontsource-variable/*` packages in `package.json`, Astro `fonts` option in `astro.config.*` and `<Font` from `astro:assets`, `font-display`, `unicode-range`, `public/fonts`, `assets/fonts`.
- React Native / Expo: `expo-font`, `useFonts`, `react-native.config.js` assets, `fontFamily:`.
- Android: `res/font/`, `FontFamily(`, `GoogleFont(`, `android:fontFamily`, `font_certs`.
- Apple: `UIAppFonts` in `Info.plist`, `.ttf`/`.otf` in the bundle, `Font.custom(`, `UIFont(name:`.

## Inventory: type tokens
- Tailwind: `tailwind.config.*` `theme.fontSize`, `fontFamily`, `lineHeight`; Tailwind v4 `@theme` blocks with `--font-*`, `--text-*`.
- CSS: custom properties `--font-*`, `--text-*`, `--type-*`, `--leading-*`, `--line-height-*`.
- DTCG: `*.tokens.json`, `tokens/**/*.json` with `"$type": "typography"`, `"fontFamily"`, `"fontWeight"`, `"dimension"`.
- Theme objects: `theme.ts`, `theme/typography.*`, MUI `createTheme({ typography })`, Chakra or styled-system `fontSizes`.
- Compose: `Type.kt`, `Typography(`, `TextStyle(`, `MaterialTheme.typography`.
- XML Views: `values/styles.xml`, `themes.xml`, `TextAppearance.*`, `dimens.xml` with `sp`.
- Apple: `Font+*.swift`, `UIFont+*.swift` extensions, `Font.TextStyle` usage, asset-catalog font references.
- Also note hard-coded literals (`font-size: 14px`, `fontSize = 14.sp` outside the theme, `.font(.system(size:))`): they are debt to migrate, not precedent to copy.

## Representative screens
Inspect at least: the densest data view, the longest reading view, a form with errors, the smallest supported viewport, the most-translated or longest-string locale, and one RTL screen if supported. Capture the sizes, weights and line heights actually rendered.

## When evidence conflicts
1. Accessibility minimums win over everything ([accessibility-checks](accessibility-checks.md)).
2. Documented project decisions (tokens, design-system doc, ADRs) win over undocumented code patterns.
3. Code that ships today wins over stale design files, unless the design file is newer and approved.
4. Platform conventions win over web habits on native platforms (use text styles and `sp`, not a ported px scale).
5. Measured evidence (analytics, usability findings, support tickets) wins over taste.
6. If two documented sources disagree and neither is clearly newer, don't guess: implement the accessible option, flag the conflict and ask.

## Decision record format
Add to the existing design docs (design-system doc, tokens README, `docs/adr/`, `brand/README.md`). Keep it short:

```md
### Type decision: <title> (<date>)
- Context: <evidence used: audience, density, platforms, scripts, screens inspected>
- Decision: <what changed: tokens, family, scale, loading>
- Rationale: <why this fits the evidence; which heuristics were used, labeled as heuristics>
- Alternatives: <options rejected and why>
- Verification: <checks run and results; checks not verified and why>
```

Record: new or removed family, scale or ratio change, new script support, loading strategy change, licence facts (licence name, permitted uses, where the licence file lives).

## Sources
- [WCAG 2.2](sources.md#w3c) (accessibility minimums that override all evidence), accessed 2026-10-02.
- [W3C: text size in translation](sources.md#w3c) (UGC and localized length), accessed 2026-10-02.
- [Astro fonts guide](sources.md#web-platform-docs) (`fonts` config option, `<Font />` from `astro:assets`, Fontsource provider), accessed 2026-10-02.
- Discovery checklist and conflict order are harness practice, not taken from an external standard.
