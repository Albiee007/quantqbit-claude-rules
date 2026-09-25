# In-app (UI) icons

Launcher icons are the brand; in-app icons are the interface. Both should look like one product.

## One family, used consistently
- **Pick one family** and use it everywhere: Ionicons (Expo default, via `@expo/vector-icons`), Material Symbols (Android, web) or SF Symbols (native iOS). Mixing families gives mismatched stroke weights and corner radii.
- **Outline vs filled:** outline for inactive states and filled for active or selected ones (e.g. tab bars: `home-outline` → `home`). Don't mix the two in a single row.
- **Sizes on a scale:** 16 / 20 / 24 / 32 dp or pt. In a 44 pt / 48 dp touch target the icon is 20–24 and the rest is padding.
- **Meaning:** one icon per concept across the app (e.g. `wallet-outline` always means "trip money"). Pair icons with labels, except for universal ones (back, close, search, more).
- **Accessibility:** icon-only buttons need an accessible name (`accessibilityLabel`). Decorative icons are hidden from screen readers. Keep 3:1 contrast against the background.

## Custom icons
- Draw them on the family's grid (24 px with 2 px padding for Material and Ionicons), matching its stroke width (about 1.5–2 px at 24) and corner style.
- Export SVG. For React Native, use `react-native-svg` components or an icon font built from the SVGs. Don't mix PNG icons into a vector set.
- Name by meaning, not by look: `trip-money`, not `wallet-blue`.

## Third-party marks
Don't draw payment-app, bank or social logos unless the app has a licence and the stores' IP rules allow it. Use a neutral glyph or monogram with the name in text (the app keeps working, and review stays clean).
