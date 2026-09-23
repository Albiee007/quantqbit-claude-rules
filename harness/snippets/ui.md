UI checklist (web / React Native / Android / iOS):
- Reuse the existing design system: tokens and components only. No parallel components, no raw hex/px/dp/pt/ms.
- Contrast: 4.5:1 text, 3:1 large text, UI boundaries, and focus indicators. Check light and dark.
- Targets: at least 24x24 CSS px (WCAG 2.5.8), 44x44 pt on iOS, 48x48 dp on Android.
- Keyboard operable, logical order, no traps. Focus visible and not obscured by sticky UI.
- Accessible names for every control. Visible labels, not placeholders. autocomplete on personal data.
- Never use color alone. Errors in text next to the field, with a fix, announced, input kept.
- Reflow at 320 px with no horizontal scroll. Text at 200% without clipping. Respect safe areas and insets.
- States: loading, empty, error, partial, success, disabled, offline, long/zero/many items.
- Motion 100-500 ms with token easing. Respect reduced motion.
- Verb-first buttons. No hard-coded or concatenated strings. Start/end (RTL-safe) layout.
- Follow platform conventions (Material 3, Apple HIG, web). Self-review with the pre-merge checklist.
Load skill: ui-ux (mandatory for UI work).
