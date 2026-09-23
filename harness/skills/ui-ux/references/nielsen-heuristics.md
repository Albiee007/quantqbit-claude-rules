# Nielsen's 10 Usability Heuristics

Definitions are quoted from NN/g. Use them for heuristic evaluation. Rate each finding with the severity scale in [ux-review-rubric](ux-review-rubric.md).

## 1. Visibility of system status
- **Definition:** "The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time."
- **Apply:** Every action gets feedback: pressed state, loading, success, or error. Show the current location (active nav item, page title, breadcrumbs), selection state, save state, and connectivity. Response-time limits: 0.1 s feels instantaneous, 1 s keeps the flow of thought, 10 s is the limit of attention. Show progress for long operations.
- **Typical violations:** A submit button with no loading state. Silent autosave failure. No active state in the navigation. A spinner with no end on a 30-second export.

## 2. Match between the system and the real world
- **Definition:** "The design should speak the users' language. Use words, phrases, and concepts familiar to the user, rather than internal jargon."
- **Apply:** Use user vocabulary (research it). Follow real-world order and conventions (dates, currency, units in the user's locale). Use icons that match real objects.
- **Typical violations:** "Entity", "payload", "sync token" in UI copy. Raw enum or status codes. ISO timestamps shown to consumers.

## 3. User control and freedom
- **Definition:** "Users often perform actions by mistake. They need a clearly marked 'emergency exit' to leave the unwanted action without having to go through an extended process."
- **Apply:** Support undo and redo. Provide Cancel, Back, and Close on every modal, sheet, and wizard. Prefer undo to "Are you sure?" for reversible actions. Browser and system Back must work.
- **Typical violations:** A modal without a close control. A wizard with no Back. Delete with no undo. Back that exits the app from a nested screen.

## 4. Consistency and standards
- **Definition:** "Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions."
- **Apply:** Internal consistency: one term, one component, one style per concept (design-system components and tokens). External consistency: platform conventions (Material 3 on Android, HIG on Apple platforms, web norms).
- **Typical violations:** "Delete", "Remove", and "Trash" used for the same action. Three different button styles for primary actions. iOS-style controls on Android.

## 5. Error prevention
- **Definition:** "Good error messages are important, but the best designs carefully prevent problems from occurring in the first place."
- **Apply:** Constrain input (pickers, masks, `inputmode`), provide good defaults, confirm high-cost destructive actions, disable impossible choices with an explanation, and validate before commit. Prevent high-cost errors first.
- **Typical violations:** A free-text date field. "Delete account" next to "Save" with the same style. Allowing past dates for a future booking.

## 6. Recognition rather than recall
- **Definition:** "Minimize the user's memory load by making elements, actions, and options visible. Information required to use the design should be visible or easily retrievable when needed."
- **Apply:** Keep labels visible (placeholders are not labels). Show recent items and suggestions. Keep context visible across steps. Offer help in context.
- **Typical violations:** Placeholder-only labels that vanish on typing. Icon-only toolbars with no labels or tooltips. Asking for a value shown on a previous screen.

## 7. Flexibility and efficiency of use
- **Definition:** "Shortcuts — hidden from novice users — may speed up the interaction for the expert user so that the design can cater to both inexperienced and experienced users."
- **Apply:** Offer keyboard shortcuts, bulk actions, saved filters, and personalization, without making them required. Shortcuts must not conflict with assistive tech (WCAG 2.1.4).
- **Typical violations:** No bulk select in a table of hundreds of rows. Single-character shortcuts that cannot be turned off or remapped.

## 8. Aesthetic and minimalist design
- **Definition:** "Interfaces should not contain information that is irrelevant or rarely needed. Every extra unit of information competes with relevant units and diminishes their visibility."
- **Apply:** Prioritize content that supports the primary goal. Use progressive disclosure. One primary action per view.
- **Typical violations:** A dashboard with 20 equal-weight widgets. Marketing copy inside task flows. Decorative elements that compete with CTAs.

## 9. Help users recognize, diagnose, and recover from errors
- **Definition:** "Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution."
- **Apply:** Place the message next to its source. Use a redundant indicator (icon plus text plus color). Keep the user's input. Say what happened and how to fix it. See [content-microcopy](content-microcopy.md).
- **Typical violations:** "Error 500". "Invalid input". Clearing the form on error. Color-only red borders.

## 10. Help and documentation
- **Definition:** "It's best if the system doesn't need any additional explanation. However, it may be necessary to provide documentation to help users understand how to complete their tasks."
- **Apply:** Put help in context (inline hints, tooltips, empty-state tips). Make help searchable, task-oriented, and written as concrete steps. Keep help in a consistent location (WCAG 3.2.6).
- **Typical violations:** Help only in an external PDF. A help link that moves between pages. Tooltips as the only place for required information.

## Sources
- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://www.nngroup.com/articles/response-times-3-important-limits/
