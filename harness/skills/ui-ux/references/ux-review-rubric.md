# UX Review Rubric (for reviewer agents)

Use this rubric to review any UI change: diff, screenshot, running app, or design. Report findings, not opinions. Every finding names the category, severity, location, evidence, the violated rule (WCAG SC, heuristic, law, or token rule), and a concrete fix.

## Severity
| Level | Meaning | Merge impact |
|---|---|---|
| **Critical** | Blocks a task for some users, fails a WCAG 2.2 A/AA SC, loses data, or is a misleading or dark pattern | **Blocks merge** |
| **Major** | Significant friction, inconsistency, or a design-system breach. Users succeed only with effort, or the change will not scale | Fix before merge unless explicitly waived with a ticket |
| **Minor** | Polish, small inconsistency, or a copy tweak. Task unaffected | Fix now or ticket it |

When unsure between two levels, pick the higher one if it affects accessibility or data. Otherwise pick the lower one.

## Scoring
For each category, score **Pass** (no findings above Minor), **Needs work** (Major present), or **Fail** (Critical present). The overall result is the worst category result. Output format:

```
UI REVIEW: FAIL | NEEDS WORK | PASS
[Critical] A11y > Keyboard: src/components/Menu.tsx:42 - menu items are divs with onClick, not reachable by Tab (WCAG 2.1.1). Fix: use <button> / menu pattern with arrow keys.
[Major] Design system > Tokens: Card.tsx:18 - raw #3B82F6 and padding 14px. Fix: color.action.primary, space.3/space.4.
[Minor] Content > Buttons: "Submit" on invoice form. Fix: "Send invoice".
```

## Categories and example findings

### 1. Accessibility (WCAG 2.2 AA): see [wcag-22-aa](wcag-22-aa.md)
- **Critical:** Text contrast below 4.5:1 (or below 3:1 for large text). A control not operable by keyboard. A keyboard trap. No visible focus or `outline: none` without a replacement. Missing accessible name on an icon button. An input with no label. Focus entirely hidden by a sticky header. A target under 24x24 CSS px with no spacing exception. A drag-only interaction. A CAPTCHA or password field that blocks paste. Information conveyed by color alone. Horizontal scroll at 320 px. Auto-playing motion with no pause. Error not announced or not described in text.
- **Major:** Wrong heading order. Missing landmarks or skip link. Focus not returned after closing a dialog. Status message not in a live region. Reduced motion ignored for non-essential animation. `aria-*` misuse where native semantics exist. Touch targets below the platform guideline (44 pt / 48 dp) but at least 24 px.
- **Minor:** Redundant `title` attributes. Verbose alt text. Decorative image not hidden.

### 2. Design-system compliance: see [design-tokens-dtcg](design-tokens-dtcg.md)
- **Critical:** A new parallel component or theme that duplicates an existing one (a second Button or a second color system).
- **Major:** Raw hex, px, dp, pt, or ms values in components. Primitive tokens used directly in components. A one-off component variant that should be a prop. Overriding component internals with ad-hoc CSS. Hand-editing generated token files.
- **Minor:** Near-miss spacing (for example 14 px where the scale gives 12 or 16). Inconsistent radius or elevation among siblings.

### 3. States and resilience: see [forms-and-states](forms-and-states.md)
- **Critical:** Data loss on error or navigation. No error handling on an async action (silent failure). A double-submit that can create duplicate payments or records.
- **Major:** Missing loading, empty, or error state. A spinner with no timeout or retry. Layout breaks with long text, zero items, or many items. Offline not handled on mobile. Disabled button with no explanation.
- **Minor:** Skeleton that does not match the final layout. Loading indicator flash on fast responses.

### 4. Forms: see [forms-and-states](forms-and-states.md)
- **Critical:** Placeholder used as the only label. Errors shown only by color. Form cleared on error.
- **Major:** Validation while the user is still typing the first time. No `autocomplete` on personal data. Wrong input type or keyboard. Error far from the field. No error summary on long forms. Asking for the same data twice.
- **Minor:** Inconsistent required or optional marking. Hint text only after an error.

### 5. Layout and responsiveness: see [responsive-layout](responsive-layout.md)
- **Critical:** Content or controls unreachable at some supported size (clipped, off-screen, under a system bar or notch). Zoom disabled.
- **Major:** Breakpoints not from tokens. Lines over about 80 characters. Fixed-height text containers. Hover-only actions on touch. Missing safe-area or inset handling.
- **Minor:** Inconsistent alignment or grid. Unbalanced whitespace. Grouping that contradicts proximity.

### 6. Visual hierarchy, typography, and color: see [typography-color](typography-color.md), [gestalt](gestalt.md)
- **Major:** No clear primary action, or several competing primaries. Type sizes off the scale. Body text under 16 px on web. Dark theme not verified, or pairs failing contrast only in dark mode. Status color without an icon or text.
- **Minor:** Too many font weights. Inconsistent icon style or size. Justified body text.

### 7. Interaction and motion: see [motion](motion.md)
- **Major:** No feedback within about 100 ms on press or submit. Animation blocks input. Animations over 500 ms on routine UI. Layout-property animations causing jank. Destructive action without undo or confirmation.
- **Minor:** Easing mismatched (ease-in on enter). Inconsistent durations.

### 8. Navigation and IA: see [navigation-and-ia](navigation-and-ia.md)
- **Critical:** A dead end with no way back. Back or browser history broken. A modal with no close control.
- **Major:** No current-location indicator. Actions placed in a tab bar. Tabs hidden or disabled. Page title not unique. No URL for a web view. Focus not managed on SPA route change.
- **Minor:** Breadcrumb wording mismatches page titles.

### 9. Content and microcopy: see [content-microcopy](content-microcopy.md)
- **Major:** Error messages without a fix ("Invalid input", codes). Hard-coded or concatenated strings (i18n blocker). Physical left/right styles that break RTL. Jargon or internal names in UI. Generic link text ("click here").
- **Minor:** Title Case where sentence case is the standard. Vague button verbs ("OK", "Submit"). Inconsistent terminology.

### 10. Platform conventions: see [material3](material3.md), [apple-hig](apple-hig.md)
- **Major:** iOS-only patterns on Android or the reverse (for example a custom back button that ignores the system Back). Ignoring Dynamic Type or font scale. Not using system text styles or theme typography. Non-standard controls where a platform control exists.
- **Minor:** Icons not from the platform or project icon set. Slightly off-spec component spacing.

### 11. Usability heuristics and ethics: see [nielsen-heuristics](nielsen-heuristics.md), [laws-of-ux](laws-of-ux.md)
- **Critical:** Dark patterns: pre-checked consent or upsell, confirmshaming, hidden costs, roach-motel cancellation, disguised ads.
- **Major:** Choice overload in a critical step. No progress indication in multi-step flows. Unfamiliar patterns where a convention exists (Jakob's Law). No undo for common mistakes.
- **Minor:** Missing shortcuts for expert flows. Rarely needed information given prominence.

## Review procedure
1. Identify the platforms, design system, and changed surfaces. Load the relevant references.
2. Run automated checks where available (axe, Lighthouse, lint, Accessibility Scanner or Inspector). Treat their output as a starting point only.
3. Walk each changed flow: keyboard only, screen reader spot-check, 320 px and wide, 200% text, dark mode, reduced motion, and error, empty, and loading states.
4. Check the diff for tokens-only styling and reuse of existing components.
5. Report using the format above, sorted Critical first, and list what was not verified.

## Sources
- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://lawsofux.com/
- https://www.designtokens.org/tr/2025.10/format/
