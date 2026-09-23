# Forms and UI States

## Forms

### Structure
- Single column. One field per row, except tightly related pairs (city and postal code, or expiry and CVC) on wide screens.
- Ask only for what is needed. Mark optional fields "(optional)" when most are required, or mark required fields ("required", with `*` explained) when most are optional. Be consistent within the form.
- Group related fields (`fieldset` + `legend`, or section headings). Split long forms into steps with a progress indicator ("Step 2 of 4").
- Order fields in the user's mental model (name, then email, then address). Do not split a single value across several inputs unless the format demands it (OTP inputs must still support paste).
- Do not ask twice (WCAG 3.3.7): "same as shipping", prefill known data.

### Labels and help
- Every input has a **visible, persistent label** tied programmatically (`<label for>`, `aria-labelledby`; Compose `label =`; SwiftUI `TextField("Email", ...)` plus accessibility label). **Placeholders are not labels.** Use them only for format examples, and never put required information in them.
- Labels above fields (best for scanning and localization). Keep labels short, specific, and in sentence case.
- Put format and constraint hints below the label, **before** the user types ("At least 12 characters"), linked with `aria-describedby`.
- The accessible name includes the visible label text (2.5.3).

### Input types and autofill
- Use the right type and keyboard: `type="email|tel|url|number|search|date"`, `inputmode="numeric|decimal|tel|email"`. Use `inputmode="numeric"` with `type="text"` for card numbers, OTPs, and postal codes. `KeyboardOptions(keyboardType=...)` on Android and `.keyboardType` on iOS.
- Always set **`autocomplete`** on personal-data fields (1.3.5): `name`, `given-name`, `family-name`, `email`, `tel`, `username`, `current-password`, `new-password`, `one-time-code`, `street-address`, `address-line1`, `postal-code`, `country`, `organization`, `bday`, `cc-name`, `cc-number`, `cc-exp`, `cc-csc`. iOS `textContentType`, Android `autofillHints` / `ContentType`.
- Never block paste. Allow password managers. Offer show/hide password (3.3.8). `autocomplete="off"` does not stop password managers; do not rely on it.
- Be liberal in accepted formats (spaces and dashes in phone and card numbers, case-insensitive email). Normalize on the server (Postel's Law).
- Prefer pickers, segmented controls, or radios over free text when options are few and known. Prefer visible radios over a select for a handful of options (about 5 or fewer).

### Validation timing
- **Do not validate while the user is still typing a field for the first time.** Validate on blur (leaving the field) or on submit.
- After a field has shown an error, re-validate **as the user types** so the error clears as soon as it is fixed.
- Positive inline feedback only for complex fields (password strength, username availability).
- On submit with errors: keep every value, move focus to an **error summary** at the top (web: linked list of errors) or to the first invalid field, and announce it (`role="alert"`, or focus change).
- Disable submit only during submission (to prevent double submit, with a loading label). Do not disable it to signal invalid input; let users submit and see the errors.
- Server errors map back to the relevant fields when possible.

### Error presentation
- Show the message **next to the field** (below it), in text, with an icon and error color (never color alone, 1.4.1). Set `aria-invalid="true"` and link the message via `aria-describedby`. Compose `isError` + `supportingText` and `semantics { error(...) }`.
- The field boundary in the error state still meets 3:1.
- Wording follows the formula in [content-microcopy](content-microcopy.md): what happened plus how to fix it.
- Legal, financial, or data-deleting submissions: review step, confirmation, or undo (3.3.4).
- Session timeouts: warn before expiry and allow extension (2.2.1). Preserve entered data after re-authentication.

## UI states: every data-driven view implements all that apply

| State | Requirements |
|---|---|
| **Loading (initial)** | Under about 1 s: show nothing (avoid flashing). 1-10 s: **skeleton** matching the final layout for full views, spinner for a single module. Over 10 s: determinate **progress** with an estimate and a way to cancel. Announce via `aria-busy` / live region. Reserve space to avoid layout shift. No frame-only skeletons |
| **Refreshing / background** | Keep existing content visible. Use a subtle inline indicator. Do not replace content with a skeleton |
| **Empty (first use)** | Explain what will appear here and why it is empty, and give a direct CTA ("Create your first project"). Never a blank area |
| **Empty (no results)** | Echo the query or filters, suggest fixes (clear filters, check spelling), and offer a reset action |
| **Error (whole view)** | Plain-language cause, recovery action (Retry), keep any cached data, no stack traces or codes as the main message (a support reference ID is fine as secondary) |
| **Partial** | Some data failed: show what loaded, flag the failed section inline with retry. Do not fail the whole page |
| **Success** | Confirm the outcome near the action or with a status message (announced, 4.1.3). Say what changed and what is next. Toasts stay long enough to read, pause on hover or focus, not the only record of critical results |
| **Disabled** | Visibly disabled, but explain why when it is not obvious (helper text or tooltip reachable by keyboard). Prefer hiding impossible actions or allowing the action and then explaining. Disabled controls are exempt from contrast rules but should stay legible |
| **Read-only** | Distinct from disabled: text is selectable and focusable, value is readable |
| **Offline / degraded** | Detect and show a persistent, non-blocking notice. Queue actions or explain what is unavailable. Show cached content with a timestamp |
| **Permission / no access** | Explain why access is denied and how to get it (request access, sign in) |
| **Interaction states** | Default, hover (pointer only), focus-visible, pressed/active, selected/checked, dragged, disabled, error. Focus must be distinct from hover and selected |
| **Long / overflow content** | Long names, 0 and 10k+ items, large numbers, translations that are much longer than the source language, and missing images all render without breaking layout (truncate with full text available, wrap, or paginate) |

Checks: every async call has loading, error, and empty handling in the UI. Optimistic updates roll back visibly on failure. Pagination or virtualization for long lists.

## Sources
- https://www.nngroup.com/articles/errors-forms-design-guidelines/
- https://www.nngroup.com/articles/error-message-guidelines/
- https://www.nngroup.com/articles/skeleton-screens/
- https://www.nngroup.com/articles/empty-state-interface-design/
- https://www.nngroup.com/articles/response-times-3-important-limits/
- https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/autocomplete
- https://www.w3.org/TR/WCAG22/
