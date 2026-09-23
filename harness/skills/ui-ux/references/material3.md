# Material Design 3 (Android and Material web)

Use for Android (Compose or XML Views) and any product built on Material. Prefer `MaterialTheme` tokens and M3 components over custom ones. The project's own theme overrides these baseline values.

## Accessibility minimums (Android)
- Touch target at least **48x48 dp** (icon may be 24 dp; pad to 48). Compose M3 components enforce this via `minimumInteractiveComponentSize()`. Keep it.
- Text contrast **4.5:1** (text under 18 sp, or bold under 14 sp), otherwise **3:1**.
- Text sizes in **sp** (respect font scale up to 200%). Layout sizes in **dp**. Never fixed-height text containers.
- `contentDescription` on icon buttons, meaningful images, and custom controls. `null` for decorative elements. Do not describe `Text` (it is read automatically). Do not append the role ("Submit", not "Submit button"). Set `Role` semantics on custom controls. Merge semantics for list rows.

## Color roles
Every `on*` role is the content color for its paired container role. Always pair them and never mix pairs.
- **Accent:** `primary`/`onPrimary`, `primaryContainer`/`onPrimaryContainer`, the same set for `secondary` and `tertiary`, plus `inversePrimary`. Fixed variants (`primaryFixed`, `primaryFixedDim`, `onPrimaryFixed`, `onPrimaryFixedVariant`, and the same for secondary and tertiary) stay the same across light and dark.
- **Error:** `error`/`onError`, `errorContainer`/`onErrorContainer`.
- **Surfaces:** `surface`, `surfaceDim`, `surfaceBright`, `surfaceContainerLowest`, `surfaceContainerLow`, `surfaceContainer`, `surfaceContainerHigh`, `surfaceContainerHighest`, with `onSurface` and `onSurfaceVariant`. `inverseSurface`/`inverseOnSurface` for snackbars.
- **Lines:** `outline` (important boundaries, for example text-field borders, which must meet 3:1), `outlineVariant` (decorative dividers).
- Dynamic color (Android 12+) derives schemes from the wallpaper. Keep brand or semantic colors (success, warning) harmonized and still contrast-checked.
- Use tonal surface containers for hierarchy instead of custom grays.

## Type scale (baseline, sp: size / line height / tracking)
| Role | Large | Medium | Small |
|---|---|---|---|
| Display | 57 / 64 / -0.2 | 45 / 52 / 0 | 36 / 44 / 0 |
| Headline | 32 / 40 / 0 | 28 / 36 / 0 | 24 / 32 / 0 |
| Title | 22 / 28 / 0 (Regular) | 16 / 24 / 0.2 (Medium) | 14 / 20 / 0.1 (Medium) |
| Body | 16 / 24 / 0.5 | 14 / 20 / 0.2 | 12 / 16 / 0.4 |
| Label | 14 / 20 / 0.1 (Medium) | 12 / 16 / 0.5 (Medium) | 11 / 16 / 0.5 (Medium) |

Display, Headline, and Body are Regular (400). Title Medium/Small and all Labels are Medium (500). Access them via `MaterialTheme.typography.*` or `?attr/textAppearance*`. Values are from the Compose M3 tokens; the m3.material.io spec lists slightly different tracking (for example -0.25, 0.15, 0.25). Use the theme, never literals.

## Shape scale (corner radius)
None 0 dp, Extra small 4 dp, Small 8 dp, Medium 12 dp, Large 16 dp, (Large increased 20 dp), Extra large 28 dp, (Extra large increased 32 dp, Extra extra large 48 dp), Full 50% (pill or circle). Use `MaterialTheme.shapes.*`.

## Elevation
Levels 0 / 1 / 3 / 6 / 8 / 12 dp. M3 expresses elevation mainly as **tonal** surface color (surface containers), with shadows reserved for elements that need separation (FAB, menus, dialogs). Do not stack custom shadows.

## Layout
- **Grid:** 4 dp baseline. Components and spacing in multiples of 4 (most spacing in 8 dp steps).
- **Window size classes (width):** Compact < 600 dp (phone portrait). Medium 600-839 dp (tablet or unfolded portrait). Expanded 840-1199 dp (tablet landscape). Large 1200-1599 dp. Extra-large >= 1600 dp (desktop). **Height:** Compact < 480 dp, Medium 480-899 dp, Expanded >= 900 dp.
- Decide layout by window size class (`currentWindowAdaptiveInfo()`), never by device type or orientation.
- **Margins (typical):** 16 dp in compact, 24 dp from medium up, with a 24 dp spacer between panes. Follow the project's layout tokens when they exist.
- **Panes:** a single pane in compact, moving to two panes as width grows (expanded and up). Canonical layouts: list-detail, supporting pane, feed.
- **Navigation:** navigation bar when width or height is compact (3-5 destinations; with more than 5, use a rail or drawer). Navigation rail otherwise. A navigation drawer is an option from expanded width up. `NavigationSuiteScaffold` picks bar or rail automatically.
- Edge-to-edge: draw behind system bars and apply `WindowInsets` (safe drawing) padding to content and controls.

## Motion tokens
- Durations (ms): short 50/100/150/200, medium 250/300/350/400, long 450/500/550/600, extra-long 700-1000.
- Easing: standard `(0.2, 0, 0, 1)`, standard decelerate `(0, 0, 0, 1)`, standard accelerate `(0.3, 0, 1, 1)`, emphasized decelerate `(0.05, 0.7, 0.1, 1)`, emphasized accelerate `(0.3, 0, 0.8, 0.15)`.
- Respect the system "Remove animations" setting (animator duration scale 0).

## Components: do and don't
- Use M3 components (`Button`, `FilledTonalButton`, `OutlinedButton`, `TextButton`, `TextField`/`OutlinedTextField`, `TopAppBar`, `NavigationBar`, `ModalBottomSheet`, `Snackbar`) before building custom ones.
- One filled (high-emphasis) button per screen area. A FAB is only for the screen's primary constructive action.
- Snackbars for brief, low-priority feedback with at most one action. Not for errors that need input.
- Show `supportingText` and `isError` for field errors, plus text. Never color alone.

## Sources
- https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes
- https://developer.android.com/develop/ui/compose/layouts/adaptive/build-adaptive-navigation
- https://developer.android.com/guide/topics/ui/accessibility/apps
- https://raw.githubusercontent.com/material-components/material-components-android/master/docs/theming/Typography.md
- https://raw.githubusercontent.com/material-components/material-components-android/master/docs/theming/Color.md
- https://raw.githubusercontent.com/material-components/material-components-android/master/docs/theming/Shape.md
- https://android.googlesource.com/platform/frameworks/support/+/androidx-main/compose/material3/material3/src/commonMain/kotlin/androidx/compose/material3/tokens/ (TypeScaleTokens.kt, ElevationTokens.kt, MotionTokens.kt)
- https://m3.material.io/components/navigation-bar/overview (via search summary)
