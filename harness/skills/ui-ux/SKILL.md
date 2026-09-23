---
name: ui-ux
description: Mandatory UI/UX, accessibility (WCAG 2.2 AA) and design-system standards for any user-interface work — web, mobile, Android, iOS. Use when creating or changing screens, components, layouts, styles, forms, navigation, copy in UI, design tokens, or reviewing UI.
---

# UI/UX

**Mandatory** for every change that touches a user interface: web (React, Vue, Svelte, Astro, HTML/CSS), React Native, Android (Compose or XML), iOS/macOS (SwiftUI or UIKit). Follow the workflow, meet every minimum, and pass the pre-merge checklist before reporting UI work as done.

## Precedence
1. **Accessibility minimums (WCAG 2.2 AA plus platform minimums) are never overridable.** No project convention, design file, or user preference lowers them. If a design violates them, implement the accessible version and flag the difference.
2. **Project design system** (its tokens, components, patterns, content guide) overrides the generic values in this skill (scales, sizes, colors, durations).
3. **Platform guidelines:** Material 3 on Android, Apple HIG on Apple platforms, web conventions on the web.
4. Generic guidance in this skill and its references.

Explicit user instructions win on style, never on rule 1.

## Workflow
1. **Discover and reuse.** Before writing UI, find the existing design system: token files (`*.tokens.json`, `tokens/`, `theme.*`, `tailwind.config.*`, CSS custom properties, `Theme.kt`/`Color.kt`/`Type.kt`, `values/*.xml`, asset catalogs), the component library (`components/`, `ui/`, Storybook), and existing screens with similar patterns. **Reuse existing components and tokens. Never create a parallel button, color set, spacing scale, or theme.** Extend by adding a variant or prop to the existing component. If none exists, propose a minimal token set ([design-tokens-dtcg](references/design-tokens-dtcg.md)) and build on it.
2. **Tokens.** Style only through semantic tokens or theme accessors. No raw hex, rgb, px, dp, pt, ms, or cubic-bezier in components. Add a token only for a real, repeated need, named by role.
3. **Layout and responsive.** Mobile-first, content-driven breakpoints from tokens, a 4/8 spacing scale, container queries for components, safe areas and insets, reflow at 320 CSS px, readable measure ([responsive-layout](references/responsive-layout.md)).
4. **Components and all states.** Implement every applicable state: loading (skeleton or progress), empty, error, partial, success, disabled (with a reason), offline, and long or overflow content. Include interaction states: hover, focus-visible, pressed, selected, disabled, error ([forms-and-states](references/forms-and-states.md)).
5. **Content and microcopy.** Verb-first buttons, noun labels, the error formula (what happened plus how to fix it), sentence case, no hard-coded or concatenated strings, RTL-safe ([content-microcopy](references/content-microcopy.md)).
6. **Accessibility pass.** Semantics (native elements first), names, roles, and states, keyboard and focus order, visible and unobscured focus, contrast, target size, labels, announcements, reduced motion, zoom and text scaling ([wcag-22-aa](references/wcag-22-aa.md)).
7. **Platform check.** Web conventions, [material3](references/material3.md) (Android), or [apple-hig](references/apple-hig.md) (Apple). Use platform controls, navigation, type styles, and system settings (Dynamic Type, font scale, dark mode).
8. **Self-review.** Run the checklist below, plus automated tools where available (axe or Lighthouse, jsx-a11y lint, Android Accessibility Scanner or Lint, Xcode Accessibility Inspector). Score with [ux-review-rubric](references/ux-review-rubric.md). Report anything not verified.

## Pre-merge UI checklist
Every item must be true, or be reported as a known gap with a reason.

**Design system**
1. Existing components and tokens are reused. No parallel component, theme, or scale was introduced.
2. No raw color, size, spacing, radius, shadow, or duration values in component code. Tokens and theme only.

**Accessibility (WCAG 2.2 AA)**
3. Text contrast is at least **4.5:1**. Large text (at least 24 px, or at least 18.5 px bold) is at least **3:1**. Checked in light **and** dark themes.
4. UI component boundaries, states, icons that carry meaning, and **focus indicators** are at least **3:1** against adjacent colors (1.4.11).
5. Pointer targets are at least **24x24 CSS px** or meet the spacing exception (2.5.8). Touch: **44x44 pt** on iOS, **48x48 dp** on Android.
6. Everything is operable by keyboard (and switch or screen reader) in a logical order, with no traps. Esc closes overlays, and focus returns to the trigger.
7. Focus is always **visible** (2.4.7) and **not entirely obscured** by sticky headers, footers, or banners (2.4.11).
8. Every control, image, and icon button has an accessible name that contains its visible label. Decorative images are hidden. Semantics use native elements before ARIA.
9. Every input has a visible, persistent label (not a placeholder), a correct type or keyboard, and `autocomplete` (or platform autofill hints) for personal data. Paste is never blocked.
10. Errors are identified in text next to the field, with a fix, announced, and without clearing the user's input. Color is never the sole signal (1.4.1).
11. Status changes (saved, results count, errors in toasts) are announced without moving focus (4.1.3).
12. Every drag interaction has a single-pointer alternative (2.5.7). Multi-touch and path gestures have simple alternatives (2.5.1).
13. Headings, landmarks, and a unique page or screen title are present. The language is set.

**Layout and responsiveness**
14. Works from **320 CSS px** to wide screens with **no horizontal scrolling** (1.4.10). Wide content is bounded (about 65-75ch for prose).
15. Text scales to **200%** (browser zoom, Dynamic Type, Android font scale) without clipping or overlap. No fixed-height text containers. Zoom is never disabled.
16. Safe areas, system bars, notches, and the on-screen keyboard never cover content or controls.

**States and behavior**
17. Loading, empty, error, partial, success, disabled, and offline states are implemented where applicable, plus long-text, zero-item, and many-item cases.
18. Feedback starts within about **100 ms** of input. Anything over about 1 s shows progress. Submit is protected against double-submit.
19. Destructive actions are confirmed or undoable. Legal and financial submissions can be reviewed or reversed.
20. Motion is 100-500 ms, uses tokenized easing, never blocks input, and **respects reduced-motion settings**. Nothing flashes more than 3 times per second.

**Content and platform**
21. Buttons use specific verbs. Terminology is consistent. No jargon or error codes as primary text.
22. No hard-coded or concatenated UI strings. Plurals are handled. Logical (start/end) layout works in RTL.
23. Platform conventions are followed (navigation, back behavior, type styles, dark mode following the system).
24. One clear primary action per view. Visual grouping matches functional grouping.

## Top UX laws to apply by default
Full list with examples: [laws-of-ux](references/laws-of-ux.md). Heuristics: [nielsen-heuristics](references/nielsen-heuristics.md).
- **Jakob's Law:** use conventions users already know. Invent only with a strong reason.
- **Hick's Law / Choice Overload:** fewer choices, one recommended path, progressive disclosure.
- **Fitts's Law:** large, well-spaced targets. Primary actions within easy reach.
- **Doherty Threshold:** respond within 400 ms. Use optimistic UI and skeletons.
- **Proximity / Common Region / Similarity:** spacing and containers express structure ([gestalt](references/gestalt.md)).
- **Cognitive Load / Miller's Law / Working Memory:** chunk information, keep context visible, prefer recognition over recall.
- **Tesler's Law / Postel's Law:** the system absorbs complexity and accepts varied input formats.
- **Goal-Gradient / Zeigarnik:** show progress, save and resume unfinished work.
- **Peak-End Rule:** design success and error endings deliberately.
- **Von Restorff Effect:** make the key action distinct, never by color alone.

## Platform quick reference
| Topic | Web | Material 3 (Android) | Apple HIG (iOS) |
|---|---|---|---|
| Min target | 24x24 CSS px (WCAG). Use 44-48 px for touch-first primary controls | 48x48 dp | 44x44 pt (min 28x28 for dense secondary) |
| Base unit / grid | 4 px, 8 px steps | 4 dp baseline, 8 dp steps | 8 pt common. System margins and safe areas |
| Body text | 16 px (1rem), `rem` units | Body Large 16 sp / Body Medium 14 sp, `sp` units | Body 17 pt, text styles |
| Text scaling | Browser zoom 200%, reflow at 320 px | Font scale up to 200% | Dynamic Type incl. accessibility sizes |
| Breakpoints | Content-driven, project tokens | Compact < 600, Medium 600-839, Expanded 840-1199, Large 1200-1599, XL >= 1600 dp | Size classes: compact or regular |
| Top-level nav | Header nav or sidebar, hamburger for secondary | Nav bar (3-5) when compact, rail otherwise, drawer optional | Tab bar (icon plus label), sidebar on regular width |
| Contrast | 4.5:1 / 3:1 | 4.5:1 / 3:1 | 4.5:1 / 3:1, Increase Contrast |
| Motion | `prefers-reduced-motion` | Remove animations (duration scale 0) | Reduce Motion |
| Dark mode | `prefers-color-scheme`, semantic tokens | `darkColorScheme`, dynamic color | Asset catalog Any/Dark, semantic colors |
| Icons | Project icon set, accessible names | Material Symbols, `contentDescription` | SF Symbols, `accessibilityLabel` |

## References
- [laws-of-ux](references/laws-of-ux.md): all 30 Laws of UX with takeaways, examples, and violations
- [nielsen-heuristics](references/nielsen-heuristics.md): the 10 usability heuristics, how to apply them, typical violations
- [wcag-22-aa](references/wcag-22-aa.md): every WCAG 2.2 A/AA criterion as a testable rule, 2.2 additions, testing
- [gestalt](references/gestalt.md): grouping and perception principles for layout
- [design-tokens-dtcg](references/design-tokens-dtcg.md): DTCG 2025.10 format, token tiers, naming, theming, rules
- [material3](references/material3.md): M3 color roles, type scale, shape, elevation, layout, motion
- [apple-hig](references/apple-hig.md): targets, text sizes, Dynamic Type, SF Symbols, safe areas, navigation
- [typography-color](references/typography-color.md): type scale, measure, line height, contrast math, palettes, dark mode
- [responsive-layout](references/responsive-layout.md): breakpoints, grids, spacing, container queries, safe areas
- [forms-and-states](references/forms-and-states.md): forms, validation, and every UI state
- [motion](references/motion.md): durations, easing, reduced motion
- [navigation-and-ia](references/navigation-and-ia.md): IA, navigation patterns, breadcrumbs, search, wayfinding
- [content-microcopy](references/content-microcopy.md): labels, buttons, the error formula, i18n and RTL
- [ux-review-rubric](references/ux-review-rubric.md): severity-based review rubric for reviewer agents
