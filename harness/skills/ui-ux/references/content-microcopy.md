# Content and Microcopy

UI text is interface. Write for scanning, in the user's language, and consistently. When the project has a content style guide or glossary, it wins.

## Voice and style
- Plain language at about grade 8 or lower. Short sentences. Active voice. Address the user as "you".
- **Sentence case** for everything (buttons, titles, labels, menu items) unless the project style guide says otherwise.
- Be specific and concise. Front-load the key word ("Delete 3 files?", not "Are you sure you want to...").
- One term per concept across the product (a glossary). Do not alternate "Remove", "Delete", and "Trash" for the same action (Nielsen #4, WCAG 3.2.4).
- No jargon, internal names, error codes, or raw enums shown as primary text.
- No blame, no humor in errors, no "Oops!", and no exclamation marks in errors.
- Numbers as numerals. Dates, times, numbers, and currency formatted by locale (never hand-built strings).

## Labels
- Field labels are nouns and name the data ("Email address"), not instructions ("Enter your email here").
- Do not end labels with colons in modern UI. Be consistent either way.
- Link text describes the destination ("View invoice #1042", not "Click here" or "Read more"). If a short visible label is needed, extend the accessible name with context.
- Icon-only controls need an accessible name, plus a tooltip on pointer devices. Unfamiliar icons need a visible label.

## Buttons and actions
- Start with a **verb** that names the outcome: "Save changes", "Send invoice", "Create project". Avoid "OK", "Yes/No", "Submit", or "Continue" when a specific verb fits.
- The button label matches the title or question that triggers it ("Delete project?" leads to [Delete project] [Cancel]).
- Destructive actions name the object and consequence: "Delete 3 files permanently". Use the danger style, put them away from the primary action, and never make them the default.
- One primary action per view. Secondary actions use lower-emphasis styles.
- Loading labels keep the verb: "Saving..." then "Saved".

## Error message formula
**What happened + why (if useful) + how to fix it**, placed next to the problem, in plain language, keeping the user's input.

| Bad | Good |
|---|---|
| Invalid input | Enter an email address in the format name@example.com |
| Error 403 | You don't have permission to edit this project. Ask the owner for edit access. |
| Password invalid | Use at least 12 characters |
| Something went wrong | We couldn't save your changes because the connection dropped. Your edits are kept. Try again. |
| Required | Enter your last name |

- Field errors start with the fix ("Enter...", "Choose...", "Use...").
- System errors say what the user can do now (retry, save a draft, contact support with a reference ID).
- Match severity: inline for fields, a banner for page-level problems, a dialog only for blocking decisions.

## Confirmation, success, and empty text
- Confirmation dialogs: question title ("Discard draft?"), one line on the consequence, then specific verbs. Prefer undo over confirmation for reversible actions.
- Success: state what happened and what is next ("Invoice sent to ana@example.com. We'll notify you when it's paid.").
- Empty states: what goes here, why it is empty, and a CTA ([forms-and-states](forms-and-states.md)).
- Help and hint text: short, contextual, shown before the error happens.

## Accessibility of text
- The visible label is contained in the accessible name (2.5.3). Headings and labels describe their purpose (2.4.6).
- Do not rely on sensory wording alone ("the green button", "on the right") (1.3.3).
- Set the page or app language (3.1.1) and mark passages in other languages (3.1.2).
- Abbreviations: expand on first use when they are not common.

## Internationalization (i18n) and RTL readiness
- **No hard-coded strings.** All UI text comes from resource files (i18n keys, `strings.xml`, `Localizable.strings` / String Catalogs). Keys describe meaning, not position.
- **No concatenation** of translated fragments. Use full sentences with placeholders (`"{count} files deleted"`). Use ICU MessageFormat or platform plurals for **plurals** and gender (languages have up to 6 plural categories).
- Leave room for expansion. Translations are often much longer than English (short labels expand the most). Let text wrap. No fixed widths on text. Test with pseudo-localization (long plus accented).
- Format dates, times, numbers, currency, units, lists, and names with locale APIs (`Intl.*`, `DateTimeFormatter`, `Formatter`). Do not assume name order or address format.
- **RTL:** use logical properties (`margin-inline-start`, `text-align: start`) and leading/trailing (iOS) or start/end (Android). Set `dir="rtl"` / `android:supportsRtl="true"`. Mirror directional icons (back arrows, chevrons, progress) but not universal ones (play, clocks, checkmarks, logos, media controls). Use `dir="auto"` or bidi isolation (`<bdi>`, `unicode-bidi: isolate`) for user-generated text.
- Do not put text in images. Do not use culture-specific metaphors, idioms, or color meanings without review.
- Icons and emoji are not substitutes for words in critical UI.
- Sort and search with locale-aware collation.

## Sources
- https://www.nngroup.com/articles/error-message-guidelines/
- https://www.nngroup.com/articles/errors-forms-design-guidelines/
- https://www.nngroup.com/articles/ten-usability-heuristics/
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Logical_properties_and_values
- https://developer.apple.com/design/human-interface-guidelines/buttons
- https://developer.android.com/guide/topics/ui/accessibility/apps
- https://www.w3.org/TR/WCAG22/
