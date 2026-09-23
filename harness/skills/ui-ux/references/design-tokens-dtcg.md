# Design Tokens (W3C DTCG format)

Design tokens are the single source of truth for visual decisions (color, type, space, radius, elevation, motion). Components consume tokens and never raw values.

## Standard
- **W3C Design Tokens Community Group (DTCG) Format Module 2025.10** is the first stable version (announced October 28, 2025). It is a Community Group report, not a W3C Recommendation.
- Files: `.tokens` or `.tokens.json`. Media type `application/design-tokens+json` (or `application/json`).
- Companion modules exist for color and for resolving themes and modes (Resolver). Check designtokens.org before relying on them.
- If the project already uses another token format (Style Dictionary legacy `value`/`type`, Tokens Studio, platform theme files), keep it. Do not introduce a second format.

## Format essentials
- A **token** is an object with `$value` (required). Optional: `$type`, `$description`, `$extensions` (vendor data, reverse-domain keys), `$deprecated` (`true` or a reason string).
- A **group** is an object without `$value`. Groups may set `$type` (inherited by children), `$description`, `$deprecated`, and `$extends`. `$root` is a reserved token name for a group's base token.
- **Type resolution:** the token's own `$type`, else the nearest ancestor group's `$type`, else the token is invalid.
- **Names:** case-sensitive. Must not start with `$`. Must not contain `{`, `}`, or `.`.
- **Aliases:** `"$value": "{group.subgroup.token}"` resolves to the full value of the target. JSON Pointer `{"$ref": "#/group/token/$value/..."}` references a property inside a value. Aliases must not be circular.

### Types
| Type | `$value` shape |
|---|---|
| `color` | `{ "colorSpace": "srgb", "components": [r, g, b], "alpha"?: 0-1, "hex"?: "#rrggbb" }` |
| `dimension` | `{ "value": 16, "unit": "px" \| "rem" }` |
| `fontFamily` | string or array of strings |
| `fontWeight` | number 1-1000 or a keyword (`thin`, `light`, `normal`/`regular`, `medium`, `semi-bold`, `bold`, `extra-bold`, `black`, and so on) |
| `duration` | `{ "value": 200, "unit": "ms" \| "s" }` |
| `cubicBezier` | `[x1, y1, x2, y2]` |
| `number` | unitless number (for example line-height) |
| Composite: `strokeStyle`, `border`, `transition`, `shadow`, `gradient`, `typography` | objects of the sub-values above (for example `typography` = fontFamily, fontSize, fontWeight, letterSpacing, lineHeight) |

## Three tiers
1. **Primitive (reference, global):** raw palette and scales, named by what they are. `color.blue.600`, `space.4`, `radius.2`. Never used directly by components.
2. **Semantic (system, alias):** named by purpose, aliasing primitives. `color.text.primary`, `color.surface.default`, `color.border.focus`, `color.status.danger.fg`, `space.inset.md`, `radius.control`. **Themes (light, dark, high-contrast, brand) swap values at this tier only.**
3. **Component (optional):** named by component, part, and state, aliasing semantic tokens. `button.primary.bg.hover`, `input.border.error`. Add only when a component needs a deliberate deviation.

Rule: components reference semantic (or component) tokens. Semantic references primitive. Primitive holds raw values. Nothing skips a tier.

## Naming convention
`{category}.{concept}.{variant}.{state}`, lowercase, kebab-case segments. The DTCG group path gives the dots. Platform outputs map it (CSS `--color-text-primary`, Kotlin `ColorTextPrimary`, Swift `.colorTextPrimary`).
- Categories: `color`, `font`, `typography`, `space`, `size`, `radius`, `border`, `shadow`/`elevation`, `opacity`, `duration`, `easing`, `z` (layers), `breakpoint`.
- States: `default`, `hover`, `pressed`/`active`, `focus`, `selected`, `disabled`, `error`, `visited`.
- Name by role, not appearance. `color.text.danger`, not `color.red-text`.

## Example (DTCG 2025.10)
```json
{
  "color": {
    "$type": "color",
    "blue": {
      "600": { "$value": { "colorSpace": "srgb", "components": [0.145, 0.388, 0.922], "hex": "#2563eb" } }
    },
    "neutral": {
      "0":   { "$value": { "colorSpace": "srgb", "components": [1, 1, 1], "hex": "#ffffff" } },
      "900": { "$value": { "colorSpace": "srgb", "components": [0.067, 0.094, 0.153], "hex": "#111827" } }
    },
    "text": {
      "primary": { "$value": "{color.neutral.900}", "$description": "Body text on surface.default" }
    },
    "surface": {
      "default": { "$value": "{color.neutral.0}" }
    },
    "action": {
      "primary": { "$value": "{color.blue.600}" }
    }
  },
  "space": {
    "$type": "dimension",
    "1": { "$value": { "value": 4, "unit": "px" } },
    "2": { "$value": { "value": 8, "unit": "px" } },
    "4": { "$value": { "value": 16, "unit": "px" } },
    "inset": { "md": { "$value": "{space.4}" } }
  },
  "duration": {
    "$type": "duration",
    "fast": { "$value": { "value": 150, "unit": "ms" } }
  }
}
```
Dark theme: a second file (or Resolver mode) redefines only the semantic tokens, for example `color.text.primary` becomes `{color.neutral.0}` and `color.surface.default` becomes `{color.neutral.900}`. Components are unchanged.

## Theming and dark mode
- Every themed value is a semantic token with a value per theme. Components never branch on theme.
- Validate contrast for every foreground/background semantic pair **in every theme** (4.5:1 text, 3:1 large text and UI boundaries).
- Web: emit CSS custom properties per theme (`:root`, `[data-theme="dark"]`, `@media (prefers-color-scheme: dark)`), and set `color-scheme`. Android: `lightColorScheme`/`darkColorScheme` or `values-night`. iOS: asset-catalog color sets with Any/Dark appearances.

## Rules
- No raw hex, rgb, px, dp, pt, ms, or cubic-bezier in component code. Use tokens or theme accessors. Exceptions: `0`, `100%`, `1px` hairlines where the system has no token, and values inside the token source itself.
- One source of truth. Generate platform outputs (CSS variables, Tailwind theme, Compose theme, Swift) from the token source. Never hand-edit generated files.
- Reuse before adding. A new token needs a real, repeated need and a semantic name. Never add a near-duplicate (`blue-601`).
- Deprecate with `$deprecated` and an alias to the replacement before removal.
- Governance flow: tokens, then components, then patterns, then screens. Changes flow down. Screens never define styles components should own.

## Sources
- https://www.designtokens.org/
- https://www.designtokens.org/tr/2025.10/format/
