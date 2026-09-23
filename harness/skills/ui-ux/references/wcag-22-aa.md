# WCAG 2.2 Level A + AA

Target: **WCAG 2.2 Level AA** (all Level A and AA success criteria). WCAG 2.2 is a W3C Recommendation and backward compatible with 2.1 and 2.0. **[2.2]** marks criteria new in 2.2. **4.1.1 Parsing is obsolete and removed in 2.2.** AAA criteria are out of scope except where noted as good practice.

Native-app mapping: "CSS px" becomes pt (iOS) or dp (Android). "Page" becomes screen. Keyboard includes hardware keyboards, switch access, and screen-reader navigation.

## 1. Perceivable

### 1.1 Text alternatives
- **1.1.1 Non-text Content (A):** Every meaningful image, icon, and control has a text alternative with the same purpose. Decorative images are hidden from assistive tech (`alt=""`, `aria-hidden`, `contentDescription = null`, `accessibilityHidden(true)`).

### 1.2 Time-based media
- **1.2.1 Audio-only and Video-only (Prerecorded) (A):** Provide a transcript for audio-only content and a transcript or audio track for video-only content.
- **1.2.2 Captions (Prerecorded) (A):** Prerecorded video with audio has synchronized captions.
- **1.2.3 Audio Description or Media Alternative (Prerecorded) (A):** Provide audio description or a full text alternative for prerecorded video.
- **1.2.4 Captions (Live) (AA):** Live video with audio has captions.
- **1.2.5 Audio Description (Prerecorded) (AA):** Prerecorded video has audio description of visual-only information.

### 1.3 Adaptable
- **1.3.1 Info and Relationships (A):** Structure conveyed visually (headings, lists, tables, labels, groups, required state) is exposed programmatically (semantic HTML or ARIA, native accessibility traits).
- **1.3.2 Meaningful Sequence (A):** DOM or accessibility order matches the meaningful reading order.
- **1.3.3 Sensory Characteristics (A):** Instructions do not rely only on shape, size, position, or sound ("click the round button on the right").
- **1.3.4 Orientation (AA):** Content is not locked to portrait or landscape unless essential.
- **1.3.5 Identify Input Purpose (AA):** Fields collecting user data declare their purpose (HTML `autocomplete` tokens, `textContentType` on iOS, `autofillHints` on Android).

### 1.4 Distinguishable
- **1.4.1 Use of Color (A):** Color is never the only means of conveying information, state, or action. Add text, icon, pattern, or underline.
- **1.4.2 Audio Control (A):** Audio that auto-plays for more than 3 seconds can be paused, stopped, or volume-controlled independently.
- **1.4.3 Contrast (Minimum) (AA):** Text contrast is at least **4.5:1**. Large text (at least 18 pt / about 24 CSS px, or 14 pt bold / about 18.5 CSS px bold) is at least **3:1**. Exempt: inactive (disabled) components, pure decoration, logotypes, incidental text.
- **1.4.4 Resize Text (AA):** Text can be resized to **200%** without loss of content or function (no clipping or overlap).
- **1.4.5 Images of Text (AA):** Use real text, not images of text (except logos or essential cases).
- **1.4.10 Reflow (AA):** No two-dimensional scrolling at **320 CSS px** width (vertical-scrolling content) or **256 CSS px** height (horizontal-scrolling content). 320 px equals 1280 px at 400% zoom. Exempt: content that needs 2D layout (maps, data tables, diagrams, video, games, toolbars).
- **1.4.11 Non-text Contrast (AA):** UI component boundaries and states (inputs, checkboxes, toggles, focus indicators) and meaningful graphics are at least **3:1** against adjacent colors.
- **1.4.12 Text Spacing (AA):** No loss of content when users set line height 1.5x, paragraph spacing 2x, letter spacing 0.12x, and word spacing 0.16x the font size. Do not use fixed heights on text containers.
- **1.4.13 Content on Hover or Focus (AA):** Tooltips and popovers shown on hover or focus are **dismissible** (Esc) without moving pointer or focus, **hoverable** (the pointer can move onto them), and **persistent** until dismissed or no longer relevant.

## 2. Operable

### 2.1 Keyboard accessible
- **2.1.1 Keyboard (A):** All functionality works with a keyboard, with no timing requirement on individual keystrokes.
- **2.1.2 No Keyboard Trap (A):** Focus can always move away from any component using standard keys (Tab, Shift+Tab, Esc). Modals trap focus intentionally but must be closable.
- **2.1.4 Character Key Shortcuts (A):** Single-character shortcuts can be turned off, remapped, or are only active when the component has focus.

### 2.2 Enough time
- **2.2.1 Timing Adjustable (A):** Time limits can be turned off, adjusted (to at least 10x), or extended (warned first, at least 20 seconds to extend, at least 10 times). Exempt: real-time events, essential limits, and limits over 20 hours.
- **2.2.2 Pause, Stop, Hide (A):** Moving, blinking, or scrolling content that starts automatically, lasts more than 5 seconds, and runs in parallel with other content can be paused, stopped, or hidden. The same applies to auto-updating content.

### 2.3 Seizures and physical reactions
- **2.3.1 Three Flashes or Below Threshold (A):** Nothing flashes more than 3 times in any 1-second period (or flashes stay below the general and red flash thresholds).

### 2.4 Navigable
- **2.4.1 Bypass Blocks (A):** Provide a skip link or landmarks/headings so users can bypass repeated blocks.
- **2.4.2 Page Titled (A):** Each page or screen has a descriptive, unique title (`<title>`, navigation title).
- **2.4.3 Focus Order (A):** Focus order preserves meaning and operability. No positive `tabindex`. Focus moves into opened dialogs and returns to the trigger on close.
- **2.4.4 Link Purpose (In Context) (A):** Link purpose is clear from the link text plus its context. No bare "click here" or "read more" without context.
- **2.4.5 Multiple Ways (AA):** More than one way to find a page within a set of pages (navigation plus search, sitemap, or links), except for steps in a process.
- **2.4.6 Headings and Labels (AA):** Headings and labels describe topic or purpose.
- **2.4.7 Focus Visible (AA):** Every keyboard-focusable component has a visible focus indicator. Never `outline: none` without a replacement.
- **2.4.11 Focus Not Obscured (Minimum) (AA) [2.2]:** A focused component is not entirely hidden by author-created content (sticky headers or footers, cookie banners, chat widgets). Fix with `scroll-padding` or `scroll-margin`, or non-overlapping sticky UI.
- AAA, good practice: **2.4.13 Focus Appearance [2.2]**: indicator area at least a 2 CSS px perimeter with at least 3:1 change contrast.

### 2.5 Input modalities
- **2.5.1 Pointer Gestures (A):** Multipoint or path-based gestures (pinch, swipe paths) have a single-pointer alternative (buttons).
- **2.5.2 Pointer Cancellation (A):** Actions fire on up-event (release), or can be aborted or undone. No down-event activation.
- **2.5.3 Label in Name (A):** The accessible name contains the visible label text, ideally at the start (voice control users say what they see).
- **2.5.4 Motion Actuation (A):** Shake or tilt functions have a UI alternative and can be disabled.
- **2.5.7 Dragging Movements (AA) [2.2]:** Every drag action (sortable lists, sliders, maps, kanban) has a single-pointer non-drag alternative (buttons, menus, tap-to-move), unless dragging is essential.
- **2.5.8 Target Size (Minimum) (AA) [2.2]:** Pointer targets are at least **24x24 CSS px**. Exceptions: **Spacing** (an undersized target's 24 px diameter circle, centered on its bounding box, intersects no other target or circle), **Equivalent** (another conforming control does the same thing), **Inline** (in a sentence or constrained by line-height), **User agent control** (unstyled native control), **Essential**.
- AAA, good practice: **2.5.5 Target Size (Enhanced)**: 44x44 CSS px.

## 3. Understandable

### 3.1 Readable
- **3.1.1 Language of Page (A):** The default language is set (`<html lang>`, app locale).
- **3.1.2 Language of Parts (AA):** Passages in another language are marked (`lang` on the element).

### 3.2 Predictable
- **3.2.1 On Focus (A):** Receiving focus does not trigger a change of context (navigation, submit, new window).
- **3.2.2 On Input (A):** Changing a setting (select, checkbox, typing) does not change context unless the user was warned beforehand.
- **3.2.3 Consistent Navigation (AA):** Repeated navigation appears in the same relative order across pages.
- **3.2.4 Consistent Identification (AA):** Components with the same function are identified consistently (same label and icon).
- **3.2.6 Consistent Help (A) [2.2]:** Help mechanisms (contact details, chat, FAQ link, self-help) that repeat across pages appear in the same relative order.

### 3.3 Input assistance
- **3.3.1 Error Identification (A):** Detected input errors are identified and described to the user in text.
- **3.3.2 Labels or Instructions (A):** Inputs have visible labels or instructions (required fields, formats).
- **3.3.3 Error Suggestion (AA):** When a correction is known, suggest it ("Enter a date after 01/01/2025").
- **3.3.4 Error Prevention (Legal, Financial, Data) (AA):** Legal, financial, or data-deleting submissions are reversible, checked, or confirmed (review step).
- **3.3.7 Redundant Entry (A) [2.2]:** Information already entered in the same process is auto-populated or selectable. Do not ask twice (for example, "billing same as shipping"). Exceptions: essential re-entry, security, expired data.
- **3.3.8 Accessible Authentication (Minimum) (AA) [2.2]:** No cognitive function test (remembering or transcribing a password or code, solving puzzles) in any authentication step unless there is an alternative or assistance. Allow paste and password managers. Object-recognition and personal-content challenges are permitted. Never block paste into password or OTP fields.

## 4. Robust
- **4.1.1 Parsing:** Obsolete and removed in WCAG 2.2. Do not cite it.
- **4.1.2 Name, Role, Value (A):** Every UI component exposes an accessible name, role, and state or value, and changes are announced (native elements first, ARIA only when needed, Compose `semantics`, SwiftUI accessibility modifiers).
- **4.1.3 Status Messages (AA):** Status messages (saved, N results, errors in toasts) are announced without moving focus (`role="status"`, `role="alert"`, `aria-live`, `announceForAccessibility`, `UIAccessibility.post`).

## New in 2.2 (summary)
AA/A: 2.4.11, 2.5.7, 2.5.8, 3.2.6, 3.3.7, 3.3.8. AAA: 2.4.12, 2.4.13, 3.3.9. Removed: 4.1.1.

## Testing
1. **Automated scan** (catches only a subset of issues; never sufficient alone): axe-core (`@axe-core/playwright`, jest-axe, browser extension), Lighthouse accessibility, eslint-plugin-jsx-a11y or vuejs-accessibility, Android Accessibility Scanner and Lint, Xcode Accessibility Inspector audit.
2. **Keyboard walk:** Tab through every interactive element. Check visible focus, logical order, no traps, Esc closes overlays, focus returns to the trigger, and focus is never hidden under sticky UI.
3. **Screen reader:** NVDA + Firefox/Chrome or JAWS (Windows), VoiceOver (macOS Safari, iOS), TalkBack (Android). Verify names, roles, states, headings, landmarks, and live announcements.
4. **Zoom and reflow:** Browser at 1280 px and 400% zoom (320 px), text-only 200%, and a text-spacing bookmarklet. On native: largest Dynamic Type and accessibility sizes, Android font scale 200%.
5. **Contrast:** Measure every text and background token pair and every UI boundary in light and dark themes.
6. **Motion:** Enable reduced motion (OS setting) and verify.
7. **Target size:** Measure small icons, chips, and inline controls (24 px rule and spacing circle).

## Sources
- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
