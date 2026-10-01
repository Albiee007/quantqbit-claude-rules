# Font Metrics and Pairing

## Metrics vocabulary
- **Units per em (UPM):** the size of the design grid, from the `head` table. Valid range 16–16384; 1000 (common in CFF/OTF) and 2048 (common in TrueType, a power of two) are typical. Every other metric is in these units; divide by UPM to get a fraction of the font size.
- **x-height:** height of lowercase letters (OS/2 `sxHeight`). **Cap height:** height of capitals (OS/2 `sCapHeight`, nominally the top of "H").
- **Ascender / descender:** extent above and below the baseline. **Line gap:** extra space the font requests between lines.
- At the same `font-size`, two fonts can look very different in size: the em box is the same, but the x-height and widths aren't.

### Vertical metrics tables
| Source | Fields | Used by |
|---|---|---|
| `hhea` | ascender, descender, lineGap | Apple platforms; many browsers on macOS |
| OS/2 typo | sTypoAscender, sTypoDescender, sTypoLineGap | Recommended for new layout engines; used on Windows when `USE_TYPO_METRICS` is set |
| OS/2 win | usWinAscent, usWinDescent | Windows clipping region (GDI clips outlines above/below) and legacy line spacing |

- `USE_TYPO_METRICS` (fsSelection bit 7) tells software to use the typo values for line spacing. The OpenType spec recommends that variable fonts set it and keep `hhea` equal to the typo values, with win values as the clipping box.
- **Symptoms of inconsistent metrics:** different line heights on macOS vs Windows, text not vertically centered in buttons, clipped diacritics or tall-script glyphs. Check a candidate font's tables (for example with `fonttools ttx -t hhea -t OS/2`) before adopting it; prefer fonts whose three sets agree.
- Android `includeFontPadding` and Compose `LineHeightStyle` exist largely to work around these metrics ([platforms](platforms.md)).

### Why x-height matters
- Apparent size and legibility at small sizes track x-height more than nominal size. A large x-height face can sit one step smaller; a small x-height face (many old-style serifs) needs a larger body size.
- Large x-height needs more line height and often slightly more tracking at small sizes.
- Fallback matching should target x-height (CSS `font-size-adjust: ex-height from-font` or a number such as `0.52`, or `size-adjust`; see [loading-and-licensing](loading-and-licensing.md)).

## Choosing a typeface (checklist)
- [ ] Covers every supported script and the punctuation, currency and symbols the product uses (check the character set, not the marketing page).
- [ ] Legible at the smallest size it will render: open apertures, distinct `Il1` and `0O`, generous x-height for UI text.
- [ ] Has the weights and styles the hierarchy needs, ideally as one variable font.
- [ ] Has the OpenType features needed: tabular and lining figures, case-sensitive forms, slashed zero, fractions if relevant.
- [ ] Sane vertical metrics (above).
- [ ] Licence fits all intended uses ([loading-and-licensing](loading-and-licensing.md)).
- [ ] Brand fit is shown on real content from representative screens, not a pangram.

## Pairing principles
- **Need first:** a second family must do a job the first can't (expressive display voice, long-form reading, code). Otherwise use weights, widths or optical sizes of one family.
- **Contrast in structure, harmony in proportion:** pair faces that differ clearly in construction (serif with sans, humanist with geometric) but share similar x-height ratios, widths and stroke contrast. Two similar-but-different sans faces look like a mistake.
- **Superfamilies** (sans, serif, mono designed together) give shared metrics and proportions with low risk.
- Assign roles: one family for body and UI, the other limited to specific token roles (headings, display, code). Never mix arbitrarily within a component.
- Match x-height across the pair by adjusting token sizes or `font-size-adjust`, so inline mixing (code in prose) doesn't jump.

## Variable fonts
Registered axes (OpenType axis registry):

| Tag | Axis | CSS high-level property |
|---|---|---|
| `wght` | Weight | `font-weight` (range in `@font-face`, for example `font-weight: 100 900`) |
| `wdth` | Width | `font-stretch` |
| `opsz` | Optical size | `font-optical-sizing` |
| `ital` | Italic | `font-style: italic` |
| `slnt` | Slant | `font-style: oblique <angle>` |

- Prefer the high-level properties. Use `font-variation-settings` only for custom axes (uppercase tags like `GRAD`, `XTRA`), because it overrides everything and doesn't cascade per axis: setting one axis resets the others you didn't list.
- Declare axis ranges in `@font-face` so the browser can match weights and styles.
- Grade (custom `GRAD` in some families) changes weight without changing width: useful for dark mode or hover without reflow, where available.
- Native: Compose `FontVariation.Settings` (Android 8.0+); Expo and React Native support differs per platform ([platforms](platforms.md)).

## Optical sizing
- Optical sizes adjust stroke contrast, spacing and details for small vs large sizes. With an `opsz` axis, CSS `font-optical-sizing: auto` (the default) lets the browser set `opsz` from the font size.
- Apple's system font uses dynamic optical sizing: it interpolates continuously by point size and adjusts tracking per size, so don't pick Text vs Display cuts manually in code. Design mockups may need manual tracking to match.
- For families with separate cuts (Text, Display, Caption), map cuts to token roles: Text for body and UI, Display for large headings only.

## Numerals
| Need | CSS `font-variant-numeric` | OpenType feature |
|---|---|---|
| Aligned columns, timers, prices, counters | `tabular-nums` | `tnum` |
| Running prose | `proportional-nums` | `pnum` |
| Figures at cap height (UI, tables) | `lining-nums` | `lnum` |
| Figures that blend with lowercase text (editorial) | `oldstyle-nums` | `onum` |
| Zero distinct from O | `slashed-zero` | `zero` |
| Fractions | `diagonal-fractions` / `stacked-fractions` | `frac` / `afrc` |
| Ordinals | `ordinal` | `ordn` |

- Values from different groups combine: `font-variant-numeric: tabular-nums lining-nums slashed-zero`.
- Only works if the font has the feature: verify in the font, then visually.
- React Native `fontVariant` supports a subset (tabular, proportional, lining, oldstyle, small caps).

## Other OpenType features
- **Kerning** on by default (`font-kerning: auto`); never disable for body text.
- **Ligatures:** keep standard ligatures (`liga`) on for prose; disable contextual or discretionary ligatures in code, inputs and identifiers (`font-variant-ligatures: none` in code blocks). Required ligatures for Arabic and Indic scripts must never be disabled.
- **Case-sensitive forms** (`case`): repositions punctuation and brackets for all-caps text.
- **Small caps:** use real small caps (`font-variant-caps: small-caps` with a font that has `smcp`), not synthesized ones.
- Disable synthesized bold and italic for families lacking those faces where fidelity matters (`font-synthesis: none`), and ship the real faces instead.

## Sources
- [OpenType `head` table](sources.md#unicode-and-opentype) (unitsPerEm range and recommendation), accessed 2026-10-02.
- [OpenType `hhea` table](sources.md#unicode-and-opentype), accessed 2026-10-02.
- [OpenType OS/2 table](sources.md#unicode-and-opentype) (typo/win metrics, USE_TYPO_METRICS, variable font recommendation), accessed 2026-10-02.
- [OpenType axis registry](sources.md#unicode-and-opentype) (ital, opsz, slnt, wdth, wght), accessed 2026-10-02.
- [CSS Fonts 4](sources.md#w3c) (font-variation-settings, font-optical-sizing, font-variant-numeric), accessed 2026-10-02.
- [CSS Fonts 5](sources.md#w3c) (font-size-adjust metrics, size-adjust), accessed 2026-10-02.
- [MDN font-variant-numeric](sources.md#web-platform-docs), accessed 2026-10-02.
- [Apple HIG Typography](sources.md#platforms) (dynamic optical sizes, tracking), accessed 2026-10-02.
- [Android Compose fonts](sources.md#platforms) (FontVariation), accessed 2026-10-02.
- [React Native text style props](sources.md#platforms) (fontVariant values), accessed 2026-10-02.
- Pairing principles and the typeface checklist are typographic practice (heuristic), not from a fetched standard.
