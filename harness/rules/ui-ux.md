---
paths:
  - "**/*.{tsx,jsx,vue,svelte,astro,html,css,scss,sass,less}"
  - "**/*.{swift,xib,storyboard}"
  - "**/res/layout/**/*.xml"
  - "**/res/values/**/*.xml"
  - "**/*{Screen,View,Component,Activity,Fragment}.kt"
  - "**/{components,ui,screens,views,pages,app,styles,theme}/**"
  - "**/tailwind.config.*"
---

# UI/UX Rules

**Load skill `ui-ux` before any UI change (mandatory).** It holds the workflow, the pre-merge checklist, and platform references. These rules are the non-negotiable floor.

## Precedence
Accessibility minimums below are never overridable. Project design-system tokens and components override generic values. Then platform guidelines (Material 3, Apple HIG, web conventions).

## Design system
- Find and reuse existing tokens, theme, and components first. Never create a parallel button, color set, spacing scale, or theme. Extend existing components with variants or props.
- Tokens only: no raw hex, rgb, px, dp, pt, ms, or cubic-bezier in component code. Components use semantic tokens. Themes (dark, high contrast) swap semantic values only.
- Spacing on the 4/8 scale. Type from the type scale. Breakpoints from tokens.

## Accessibility minimums (WCAG 2.2 AA)
- Contrast: text **4.5:1**. Large text (at least 24 px, or at least 18.5 px bold) **3:1**. UI boundaries, meaningful icons, and focus indicators **3:1**. Check light and dark.
- Targets: at least **24x24 CSS px** (or spacing exception). **44x44 pt** on iOS. **48x48 dp** on Android.
- Full keyboard operability, logical focus order, no traps. Focus always **visible** and **not obscured** by sticky UI.
- Native semantics first. Every control has an accessible name containing its visible label. Decorative media hidden.
- Visible, persistent labels (placeholders are not labels). `autocomplete` or autofill hints on personal data. Never block paste.
- Never convey information by color alone. Errors in text, next to the field, announced, input preserved.
- Reflow at **320 CSS px** without horizontal scroll. Text scales to **200%** (zoom, Dynamic Type, font scale) without loss. Never disable zoom.
- Drag actions have a single-pointer alternative. Status messages are announced via live regions or platform announcements.
- Respect reduced motion. Nothing flashes more than 3 times per second. Auto-moving content over 5 s can be paused.

## States
Implement every applicable state: loading (skeleton or progress), empty (with CTA), error (cause plus recovery), partial, success, disabled (with reason), offline, and long, zero, or many items. Include hover, focus-visible, pressed, selected, disabled, and error interaction states.

## Behavior and content
- Feedback within about 100 ms. Progress for anything over about 1 s. Prevent double-submit.
- Destructive actions are confirmable or undoable.
- Motion 100-500 ms with token easing. Never blocks input.
- Verb-first button labels. The error message says what happened and how to fix it. No hard-coded or concatenated strings. Logical start/end properties for RTL.
- Follow platform conventions: system Back, navigation patterns, type styles, and dark mode that follows the system.

## Done means
The `ui-ux` pre-merge checklist passes, automated a11y checks run where available, and unverified items are reported.
