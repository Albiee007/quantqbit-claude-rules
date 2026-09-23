# Apple Human Interface Guidelines (iOS, iPadOS, macOS, watchOS, tvOS, visionOS)

Use for SwiftUI and UIKit/AppKit work. Prefer system components, system colors, text styles, and SF Symbols. They adapt automatically to Dynamic Type, Dark Mode, Increase Contrast, and localization.

## Hit targets (control size)
| Platform | Default | Minimum |
|---|---|---|
| iOS, iPadOS | 44x44 pt | 28x28 pt |
| macOS | 28x28 pt | 20x20 pt |
| watchOS | 44x44 pt | 28x28 pt |
| tvOS | 66x66 pt | 56x56 pt |
| visionOS | 60x60 pt | 28x28 pt |

Harness rule: interactive elements on iOS and iPadOS use **44x44 pt**. Treat the minimum as an exception for dense secondary controls only. Spacing matters as much as size: about **12 pt** padding around bezeled elements and about **24 pt** around elements without a bezel.

## Text size
| Platform | Default | Minimum |
|---|---|---|
| iOS, iPadOS | 17 pt | 11 pt |
| macOS | 13 pt | 10 pt |
| tvOS | 29 pt | 23 pt |
| visionOS | 17 pt | 12 pt |
| watchOS | 16 pt | 12 pt |

- Avoid Ultralight, Thin, and Light weights for UI text. Prefer Regular, Medium, Semibold, or Bold.
- Let people enlarge text by at least **200%** (140% on watchOS).

### iOS text styles (default "Large" content size; pt size / leading)
Large Title 34/41, Title 1 28/34, Title 2 22/28, Title 3 20/25, Headline 17/22 (Semibold), Body 17/22, Callout 16/21, Subheadline 15/20, Footnote 13/18, Caption 1 12/16, Caption 2 11/13. Use `.font(.body)` or `UIFont.preferredFont(forTextStyle:)`, never fixed point sizes.

## Dynamic Type
- Support every content size, including the accessibility sizes. Use text styles, or scale custom fonts (`Font.custom(_:size:relativeTo:)`, `UIFontMetrics`) and set `adjustsFontForContentSizeCategory`.
- Keep truncation minimal at large sizes. Let text wrap. Switch horizontal stacks to vertical at accessibility sizes (`ViewThatFits`, `dynamicTypeSize.isAccessibilitySize`).
- Scale meaningful icons with text (SF Symbols do this automatically).
- Test at the smallest size and the largest accessibility size.

## Contrast (Apple's WCAG AA guidance)
| Text size | Weight | Minimum ratio |
|---|---|---|
| Up to 17 pt | All | 4.5:1 |
| 18 pt and up | All | 3:1 |
| All | Bold | 3:1 |

Harness rule: follow WCAG exactly (bold counts as large only from 14 pt). Check both light and dark appearances. If defaults cannot meet contrast, support Increase Contrast. Prefer system and semantic colors (`.primary`, `.secondary`, `Color(.label)`, `Color(.systemBackground)`), which have accessible variants. Never hard-code system color values.

## Color and Dark Mode
- Support light and dark. Do not add an app-only appearance switch; follow the system setting.
- Custom colors live in an asset catalog Color Set with Any/Dark (and high-contrast) variants.
- Use the label color hierarchy (primary, secondary, tertiary, quaternary) and system background colors (base vs elevated).
- Do not use one color for different meanings. Do not redefine semantic system colors.
- Provide separate light and dark assets where an image or icon does not work in both.

## SF Symbols
- Prefer SF Symbols for interface icons. They align with San Francisco text, scale with Dynamic Type, and adapt to weight.
- Rendering modes: monochrome, hierarchical, palette, multicolor. Confirm legibility in each context.
- Match symbol weight to adjacent text weight. Use the `.fill` variant for selected tab states where the platform does.
- Icon-only buttons need an accessibility label. Custom symbols need accessibility descriptions.
- Symbol animations must be purposeful and sparse.

## Layout and safe areas
- Respect safe areas, layout margins, and readable content guides. Never put controls under the status bar, Dynamic Island or camera housing, or home indicator. Backgrounds may extend edge to edge (`ignoresSafeArea` only for backgrounds).
- Lay out by **size class** (compact or regular, per axis), never by device model or orientation. Keep functionality the same when size class changes. Show more or less of it, and switch from tab bar to sidebar on regular width where appropriate.
- Order content by importance: top and leading side first. Use leading/trailing, not left/right, so RTL works.
- tvOS: inset primary content 60 pt from top and bottom and 80 pt from the sides.
- macOS: avoid critical controls at the very bottom of a window.

## Navigation patterns
- **Tab bar:** top-level sections only, for navigation, never actions. Each tab gets a symbol and a short label (one word where possible). Do not hide or disable tabs; explain empty content instead. Badges only for critical new information. Avoid overflow into a "More" tab.
- **Hierarchical:** `NavigationStack`/`NavigationSplitView` push and pop with a back button showing the previous title. Support the edge-swipe back gesture.
- **Modal:** sheets for self-contained tasks, with clear Cancel and Done (or Save). Destructive confirmations use alerts or confirmation dialogs with a destructive role.
- **Sidebar / split view:** for iPad and Mac with regular width.

## Buttons and controls
- Every custom button has a visible pressed state.
- Label actions with verbs ("Add to Cart"). Use familiar symbols for familiar actions (share, delete).
- Roles: normal, primary (default; responds to Return), cancel, destructive (system red). Never make a destructive action the default.

## Motion
- Add motion only with purpose. Keep feedback animations brief and precise. Avoid motion on very frequent interactions. Let people cancel or skip animations. Never make motion the only carrier of information.
- Honor **Reduce Motion** (`accessibilityReduceMotion`, `UIAccessibility.isReduceMotionEnabled`). Replace zoom, scale, parallax, and peripheral motion with fades or no animation. Avoid animating depth (z-axis) changes.

## Accessibility APIs
- `accessibilityLabel` (what it is), `accessibilityHint` (result, optional), `accessibilityValue`, traits (`.isButton`, `.isHeader`, `.isSelected`). Group related elements (`accessibilityElement(children: .combine)`).
- Support VoiceOver, Voice Control (visible label equals the spoken name), Switch Control, Bold Text, Increase Contrast, Reduce Transparency, and Assistive Access where relevant.
- Test with Accessibility Inspector and VoiceOver on device.

## Sources
- https://developer.apple.com/design/human-interface-guidelines/accessibility
- https://developer.apple.com/design/human-interface-guidelines/typography
- https://developer.apple.com/design/human-interface-guidelines/layout
- https://developer.apple.com/design/human-interface-guidelines/color
- https://developer.apple.com/design/human-interface-guidelines/dark-mode
- https://developer.apple.com/design/human-interface-guidelines/sf-symbols
- https://developer.apple.com/design/human-interface-guidelines/tab-bars
- https://developer.apple.com/design/human-interface-guidelines/buttons
- https://developer.apple.com/design/human-interface-guidelines/motion
