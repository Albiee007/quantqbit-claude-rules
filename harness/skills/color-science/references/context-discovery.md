# Context Discovery

Discover before deciding. Read the code and docs, read-only, and write down what you found before proposing any color. Ask the parent only for what the repo can't answer.

## 1. Brand
- Find the brand palette and guidelines: `brand/`, `docs/brand*`, `brand/tokens.json` (from `brand-assets`), design-system docs, Figma variables if a Figma link is given.
- Record each brand color with its **defined space and value** (hex alone usually implies sRGB; Pantone or CMYK values imply print). Note which colors are fixed (logo, legal) and which may be tuned for accessibility.
- Brand colors that fail contrast as text stay brand colors; use them as fills or accents and derive accessible text variants. Flag the gap; never lower the minimum.

## 2. Semantic needs
- **Text:** primary, secondary, disabled, inverse, link (visited if used), placeholder.
- **Surfaces:** default, raised/elevated, sunken, overlay/scrim, inverse.
- **Borders:** default, strong, focus, divider.
- **Actions:** primary, secondary, tertiary, danger. Each with hover, pressed, focus, selected, disabled.
- **Status:** success, warning, danger/error, info, neutral. Each with fg, bg, border, icon.
- **Data:** chart categorical set, sequential and diverging ramps (see [data-visualization](data-visualization.md)).
- List which roles already exist, which are missing, and which are near-duplicates to merge.

## 3. Themes supported
- Light, dark, high-contrast (web forced colors and `prefers-contrast`, Apple Increase Contrast, Android high-contrast text), dynamic color (Material You), brand or white-label themes.
- How the theme is chosen: system preference (`prefers-color-scheme`, `isSystemInDarkTheme()`, trait collection), in-app override, per-tenant config.
- Whether dark/high-contrast is in scope for this change. If the project supports a theme, the change must support it too.

## 3a. Audience and vision
- Who uses it: older users, low-vision users, outdoor or glare-heavy use, long reading sessions. Check user research, support tickets, accessibility statements.
- For older or low-vision audiences: consider AAA **7:1** (1.4.6) for body text as a recorded project decision (AA stays the floor), heavier text weights (thin weights read lighter), and avoid distinctions carried only by low-chroma hue differences; separate by lightness and add cues.
- Record the audience assumption in the decision record; if unknown, say so.

## 4. Content types
- Photos, illustrations, icons, logos, user-generated images, video, maps, embedded third-party content.
- Text over images or video needs a scrim or solid backing that guarantees contrast for the worst case ([product-palettes](product-palettes.md)).
- User-generated colors (tags, avatars, calendars) need a constrained, pre-validated set.

## 5. Data visualization
- Chart types in use, the data types they show (categorical, ordered, signed around a midpoint, cyclic), the maximum number of series, the chart library and its theming hooks.

## 6. Output media
| Medium | Ask / check |
|---|---|
| sRGB web | Default. Untagged colors and images are treated as sRGB (CSS Color 4). |
| P3 devices | Do target devices and browsers support it (`@media (color-gamut: p3)`, iOS, Android `wideColorGamut`)? Is a fallback defined? |
| HDR | Is HDR content in scope (video, photos)? Which encoding (PQ, HLG)? CSS HDR support is a Working Draft. |
| Print | Which press, paper, profile (named ICC output profile), proofing workflow? Who measures? |
| Signage / projection / outdoor | Ambient light, display tech, viewing distance. Contrast on paper ≠ contrast in sunlight. |
| Email / PDF / office docs | Limited CSS, no dark-mode control in many clients, embedded profiles in PDFs. |

## 7. Where tokens live
- **Tailwind:** `tailwind.config.{js,ts}` `theme.colors` / `theme.extend.colors`, or `@theme` blocks in CSS (Tailwind v4).
- **CSS custom properties:** `:root`, `[data-theme]`, `@media (prefers-color-scheme)`, `light-dark()` usage; files like `tokens.css`, `theme.css`, `globals.css`.
- **DTCG:** `*.tokens.json`, `tokens/`, Style Dictionary or Tokens Studio config ([design-tokens-dtcg](../../ui-ux/references/design-tokens-dtcg.md)).
- **CSS-in-JS / component libs:** `theme.ts`, MUI `createTheme`, Chakra, styled-components theme.
- **Jetpack Compose:** `ui/theme/Color.kt`, `Theme.kt` (`lightColorScheme`, `darkColorScheme`, `dynamicLightColorScheme`).
- **Android XML:** `res/values/colors.xml`, `res/values-night/`, `themes.xml`.
- **iOS / macOS:** `Assets.xcassets/*.colorset/Contents.json` (Any/Dark, High Contrast, sRGB vs Display P3), `Color` extensions.
- **React Native / Flutter:** theme objects, `ThemeData.colorScheme`.
- Search hints: `grep -rE "#[0-9a-fA-F]{3,8}\b|rgba?\(|oklch\(|hsl\(" src` finds raw values that should be tokens.

## 8. Decision record format
Append to the project's existing design doc, ADR folder or token `$description`. One record per decision:

```markdown
### Color decision: <role or change>  (<date>)
- Context: <themes, media, content, constraint that triggered this>
- Decision: <token name(s) and value per theme, with space, e.g. oklch(0.55 0.15 250) / sRGB #2f6fd6>
- Assumptions: <space, encoding, white point, observer, compositing backdrop, output profile>
- WCAG results: <pair, ratio, threshold, pass/fail, per theme and state>
- Supplementary: <APCA / ΔE / CVD notes, labeled informative>
- Heuristics used: <labeled, with what would validate them>
- Alternatives rejected: <and why>
- Not verified: <and why>
```

## Sources
- CSS Color 4, untagged content treated as sRGB: [W3C](sources.md#w3c).
- Media Queries 5 (`color-gamut`, `prefers-contrast`, `forced-colors`): [W3C](sources.md#w3c).
- CSS Color HDR status: [W3C](sources.md#w3c).
- Android wide color gamut and dynamic color; Apple HIG Color and Dark Mode: [Platforms](sources.md#platforms).
