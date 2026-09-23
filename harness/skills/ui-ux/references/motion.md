# Motion

Motion explains change (where something came from or went, what changed, what responds). It is never decoration for its own sake and never the only carrier of information.

## Durations
| Use | Duration |
|---|---|
| Micro feedback (press, toggle, hover, checkbox) | 100-150 ms |
| Small component changes (expand, fade, tooltip) | 150-250 ms |
| Medium transitions (dialogs, sheets, menus, page elements) | 250-400 ms |
| Large or full-screen transitions | 300-500 ms |
| Exits | slightly shorter than the matching entrance |

- Stay within **100-500 ms** for UI transitions. Longer only for deliberate, non-blocking storytelling.
- Larger distance or area means a longer duration. Mobile-sized movements run shorter than tablet or desktop ones.
- Feedback must start within 100 ms of input (0.1 s feels instantaneous) and should complete within the 400 ms Doherty threshold.
- Material 3 tokens: short 50-200, medium 250-400, long 450-600, extra-long 700-1000 ms ([material3](material3.md)).
- Use duration and easing **tokens**. No literal ms or cubic-bezier values in components.

## Easing
- **Enter / appear:** decelerate (ease-out). Fast start, gentle stop. M3 emphasized decelerate `cubic-bezier(0.05, 0.7, 0.1, 1)`.
- **Exit / leave:** accelerate (ease-in). M3 emphasized accelerate `cubic-bezier(0.3, 0, 0.8, 0.15)`.
- **Move or resize on screen:** standard (ease-in-out). M3 standard `cubic-bezier(0.2, 0, 0, 1)`.
- **Linear:** only for continuous loops (spinners, progress) and opacity cross-fades.
- Use springs (SwiftUI, Compose, Framer Motion) with high damping for UI. Avoid bouncy overshoot on functional UI.

## Rules
- Animate only `transform` and `opacity` on the web (compositor-friendly). Avoid animating layout properties (`width`, `height`, `top`, `margin`). Target 60 fps with no jank.
- Motion must never block input. Users can act or interrupt mid-animation. Do not make people wait for an animation to finish, especially a repeated one.
- Avoid motion on very frequent interactions (typing, every list scroll).
- Keep the spatial model consistent: things that come from the right return to the right, and sheets rise from and fall to the bottom. Mirror direction in RTL.
- Related elements move together (common fate). Stagger list items lightly, with a cap on total delay, or not at all.
- Loading motion: skeleton shimmer is subtle and low-contrast, and stops when reduced motion is on.
- No auto-playing motion longer than 5 s without pause, stop, or hide (WCAG 2.2.2). Nothing flashes more than 3 times per second (2.3.1). Avoid sustained oscillation (Apple HIG notes about 0.2 Hz is especially uncomfortable).
- Parallax, zoom, large-scale scaling, spinning, and panning of large areas are vestibular triggers. Avoid them, or remove them under reduced motion.

## Reduced motion (mandatory)
Respect the OS setting on every platform:
- Web: `@media (prefers-reduced-motion: reduce)`. Replace movement with opacity fades or instant changes. Keep essential feedback (focus, state change).
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
  ```
  Prefer opt-in (`@media (prefers-reduced-motion: no-preference) { ... }`) for large or decorative motion. JS animation libraries: check `matchMedia('(prefers-reduced-motion: reduce)')` (for example Framer Motion `useReducedMotion`).
- iOS: `@Environment(\.accessibilityReduceMotion)` / `UIAccessibility.isReduceMotionEnabled`. Swap slides and zooms for cross-fades. Also honor Reduce Transparency and Dim Flashing Lights for video.
- Android: honor animator duration scale 0 ("Remove animations"). Compose respects it for standard animations. Check `Settings.Global.ANIMATOR_DURATION_SCALE` for custom ones.
- Auto-playing video or carousels: do not autoplay under reduced motion, and always provide pause.

## Sources
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion
- https://developer.apple.com/design/human-interface-guidelines/motion
- https://developer.apple.com/design/human-interface-guidelines/accessibility
- https://android.googlesource.com/platform/frameworks/support/+/androidx-main/compose/material3/material3/src/commonMain/kotlin/androidx/compose/material3/tokens/ (MotionTokens.kt)
- https://www.nngroup.com/articles/response-times-3-important-limits/
- https://lawsofux.com/doherty-threshold/
- https://www.w3.org/TR/WCAG22/
