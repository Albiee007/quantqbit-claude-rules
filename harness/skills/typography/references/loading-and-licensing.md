# Loading and Licensing

Every custom face costs bytes, render time and possibly layout shift. Every font has a licence that may forbid the use you have in mind. Check both before adding one.

## Zero-cost option first
- System font stacks cost nothing to download and render natively: `font-family: system-ui, sans-serif;` plus `ui-serif`, `ui-monospace`, `ui-rounded` where supported. Native apps get the platform font with full Dynamic Type and font-scale support by default.
- Choose a custom face only when brand or coverage evidence requires it ([context-discovery](context-discovery.md)).

## Web: font-display
| Value | Behaviour | Use when |
|---|---|---|
| `swap` | Fallback shows almost immediately; web font swaps in whenever it arrives | Brand font matters and the fallback is metric-matched (otherwise visible reflow) |
| `fallback` | Very short invisible period, short swap window, then the fallback stays | Late swaps are worse than not swapping |
| `optional` | Very short invisible period, no swap: the font is used only if already available | Performance and stability first; font shows on later page views from cache |
| `block` | Short invisible period, then swap | Rarely; only for icon-like faces where fallback glyphs are meaningless (prefer SVG icons) |

- Pair `swap` with metric overrides (below) or the swap causes layout shift.
- `optional` is the most layout-stable choice for body text on content sites.

## Web: delivery
- **WOFF2 only** for modern browsers.
- **Preload only the critical faces** (body regular, maybe the main heading weight): `<link rel="preload" href="/fonts/x.woff2" as="font" type="font/woff2" crossorigin>`. `crossorigin` is required even for same-origin fonts, or the preload is wasted. Over-preloading steals bandwidth from other critical resources.
- Put `@font-face` rules inline in the document head or in the first stylesheet, so discovery doesn't wait on another request.
- **Subsetting and `unicode-range`:** split by script so browsers download only the slices a page uses; essential for CJK. Subsetting must be permitted by the licence.
- **Variable fonts:** one file replaces several static weights. It's usually smaller than three or more statics but bigger than one or two; compare actual bytes for the weights you use.
- **Self-hosting vs services:** self-hosting avoids third-party requests and the privacy exposure of sending visitor IPs to a font service (relevant under GDPR), and keeps fonts on your HTTP/2 or HTTP/3 origin. Services may handle subsetting and caching for you. If using a third-party origin, `preconnect` to it with `crossorigin`.
- Replace icon fonts with SVG icons.

## Web: matching the fallback (reduce CLS)
Define an adjusted local fallback face and put it second in the stack:
```css
@font-face {
  font-family: "Brand Fallback";
  src: local("Arial");
  size-adjust: 104%;        /* match x-height / average width */
  ascent-override: 92%;
  descent-override: 24%;
  line-gap-override: 0%;
}
body { font-family: "Brand", "Brand Fallback", system-ui, sans-serif; }
```
- `size-adjust` scales glyphs and metrics of that face (CSS Fonts 5; interoperable across major browsers since September 2023, when it became Baseline newly available; MDN lists it as Baseline widely available as of 2026-10-02). `ascent-override`, `descent-override`, `line-gap-override` replace the vertical metrics (CSS Fonts 4). Values above are placeholders: compute them from the two fonts' metrics or with a tool (framework font loaders such as `next/font` and Fontaine-style tools do this).
- `font-size-adjust` (Baseline 2024) normalizes x-height or cap height across the whole stack: `font-size-adjust: ex-height from-font`.
- Verify by toggling the web font off and comparing screenshots and line counts.

## Web: Core Web Vitals
- **LCP:** if the largest element is text in a web font, a font that hasn't loaded can delay its render and so delay LCP (web.dev: "in some situations"). Check which element is LCP in Lighthouse or the Performance panel before tuning.
- **`optional` vs `swap`:** `optional` caps render delay at about 100 ms and avoids swap-related layout shift (good for LCP and CLS) but skips a late font on that view. `swap` paints fallback text at once (good for LCP) but a late font shifts layout (CLS) unless the fallback is metric-matched.
- **Preload** makes the critical face discoverable early, which helps LCP when it's text, but takes bandwidth from other critical resources (often the LCP image). Preload only faces used above the fold; inlining `@font-face` can beat preload.
- **Field data wins:** confirm with CrUX or RUM, not one lab run.

## Web: CSS Font Loading API
- `document.fonts.load("1rem Brand")`, `document.fonts.ready`, `new FontFace(...)` plus `document.fonts.add()` give programmatic control: canvas text, measuring text after fonts arrive, staged loading.
- Don't use it to hide content until fonts load.

## Native bundling
- **Android:** fonts in `res/font/` (API 26+, or AndroidX for older), referenced via font-family XML or Compose `FontFamily(Font(R.font.x, FontWeight.Normal))`. **Downloadable fonts** via the Google Fonts provider (`GoogleFont.Provider` with certificates) avoid bundling, but need a fallback while downloading and Play services on the device.
- **Apple:** add files to the target and list each filename (with extension) under `UIAppFonts` in `Info.plist`. Reference by PostScript or family name; scale with `UIFontMetrics` or `relativeTo:` ([platforms](platforms.md)).
- **Expo / React Native:** the `expo-font` config plugin embeds fonts at build time (available at launch, needs a development build); `useFonts` loads at runtime (works in Expo Go and web, needs a splash-screen gate). Officially TTF and OTF. Android names the family from the filename, iOS from the font's internal name: name files after the PostScript name so one `fontFamily` string works on both.
- Bundle only weights and scripts you use; static subsets reduce app size.

## Licensing
Read the actual licence text (in the font package or foundry EULA) and answer each question before shipping:

| Question | Why it matters |
|---|---|
| Web embedding (`@font-face`) allowed? | Desktop licences often exclude it; web licences may cap pageviews |
| App embedding allowed? | Mobile and desktop app bundling is often a separate licence |
| Logo or wordmark use allowed? | Some EULAs restrict or require a separate licence; outlining a logo may still need one |
| Modification, subsetting, format conversion allowed? | Subsetting and WOFF2 conversion count as modification under some licences |
| Redistribution, number of users, domains or apps? | Seats, domains and app titles may be capped |
| Reserved Font Name? | OFL fonts with an RFN must be renamed if you distribute a modified version |

- **SIL OFL 1.1:** the OFL site states fonts can be used in documents, artwork, logos and websites, bundled in apps under conditions, and modified and redistributed; Reserved Font Names may force a rename of modified versions. Read the licence text and OFL-FAQ for selling, subsetting and RFN edge cases before relying on assumptions.
- **Apache 2.0** (some older Google-distributed fonts): permissive, with notice requirements. Read the licence file in the package.
- **Commercial EULAs:** vary by foundry and tier. Never assume a licence bought for design tools covers web or app use.
- **System fonts** (SF Pro, Segoe, Roboto on device) are licensed for use through the platform; don't extract and bundle them into other platforms or web fonts unless the licence explicitly permits it.
- **Record** licence name, licence file location, permitted uses and purchaser in the decision record ([context-discovery](context-discovery.md)).
- **The harness never bundles fonts.** It doesn't ship font files in skills or templates; projects add their own after licence review. If licence text isn't available, report the licence check as not verified.

## Sources
- [CSS Fonts 4](sources.md#w3c) (font-display, metric override descriptors), accessed 2026-10-02.
- [CSS Fonts 5](sources.md#w3c) (size-adjust, font-size-adjust metrics), accessed 2026-10-02.
- [web.dev: Best practices for fonts](sources.md#web-platform-docs) (LCP/CLS, `optional` vs `swap`, preload cost), accessed 2026-10-02.
- [MDN font-display](sources.md#web-platform-docs), [MDN size-adjust](sources.md#web-platform-docs), [MDN font-size-adjust](sources.md#web-platform-docs), [MDN CSS Font Loading API](sources.md#web-platform-docs), accessed 2026-10-02.
- [Android: fonts in XML](sources.md#platforms), [Android: Compose fonts](sources.md#platforms) (downloadable fonts), accessed 2026-10-02.
- [Apple UIAppFonts](sources.md#platforms), accessed 2026-10-02.
- [Expo fonts guide](sources.md#platforms), accessed 2026-10-02.
- [SIL Open Font License site](sources.md#licensing-and-font-sources), accessed 2026-10-02 (OFL-FAQ itself not accessed).
- "Field data wins" and checking the LCP element first are practice, not from a fetched page.
- Apache 2.0 text, GDPR implications of font services and the licence question list are not verified against a fetched source in this pass.
