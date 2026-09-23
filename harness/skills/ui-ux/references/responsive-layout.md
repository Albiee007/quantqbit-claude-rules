# Responsive Layout

## Principles
- **Mobile-first:** base styles target the narrowest layout. Enhance with `min-width` queries.
- **Content-driven breakpoints:** add a breakpoint where the content breaks (line length exceeds about 75ch, a row overflows, a card gets too narrow), not at device widths. Use the project's breakpoint tokens. Never invent ad-hoc values.
- **Intrinsic layout first:** flex-wrap, `grid-template-columns: repeat(auto-fit, minmax(min(16rem, 100%), 1fr))`, `min()`/`max()`/`clamp()`. Media queries are for structural changes only.
- **Container queries for components:** a component adapts to its container, not the viewport. Page layout uses media queries.
- Same functionality at every size. Hide nothing essential on mobile. Rearrange or disclose progressively instead.

## Reflow and zoom (WCAG)
- Must work at **320 CSS px** wide (1280 px at 400% zoom) with **no horizontal scrolling** (1.4.10). Exempt: data tables, maps, diagrams, and similar, which scroll inside their own container.
- Text resize to 200% without loss (1.4.4). Text spacing overrides (1.4.12). No fixed heights on text containers. Avoid `overflow: hidden` that clips text.
- Do not lock orientation (1.3.4).
- Check 320, 375, 768, 1024, 1280, 1440+ px, and zoomed states.

## Breakpoint reference (use project tokens first)
| System | Values |
|---|---|
| Material 3 window classes (dp) | Compact < 600, Medium 600-839, Expanded 840-1199, Large 1200-1599, Extra-large >= 1600 |
| Apple | Size classes: compact or regular, per axis (no fixed px) |
| Tailwind defaults (min-width) | sm 640, md 768, lg 1024, xl 1280, 2xl 1536 px |

Web media queries in `em` or `rem` (`@media (min-width: 48em)`) scale with user font settings.

## Grid and spacing
- **Spacing scale:** 4 px (dp, pt) base unit. Use steps of 4 up to 16, then 8-based steps: 0, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96. Every margin, padding, and gap comes from the spacing tokens.
- Spacing expresses grouping (see [gestalt](gestalt.md)): inside a component is smaller than between components, which is smaller than between sections.
- **Column grid:** 4 columns on compact, 8 on medium, 12 on wide (web and M3 convention). Gutters 16-24 px. Page margins 16 px on phones, 24 px or more on tablets and up.
- **Max content width:** constrain reading content (about 65-75ch) and page containers (commonly 1200-1440 px) so lines do not stretch on wide screens.
- Align to a baseline or 4 px grid. Keep consistent edges; mixed alignment breaks scanning.

## Container queries (web)
```css
.card-list { container: cards / inline-size; }
@container cards (inline-size > 40rem) {
  .card { display: grid; grid-template-columns: 8rem 1fr; }
}
```
Units `cqi`/`cqb` (container inline or block size) can drive fluid sizing inside components.

## Safe areas and insets
- Web: `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`, then pad fixed and edge UI with `env(safe-area-inset-top|right|bottom|left)`. Never set `maximum-scale=1` or `user-scalable=no`.
- Use dynamic viewport units (`100dvh`, `100svh`) instead of `100vh` for full-height mobile layouts (browser toolbars).
- iOS: respect the safe area and layout margins. Only backgrounds ignore the safe area.
- Android: edge-to-edge with `WindowInsets` (`safeDrawing`, `systemBars`, `ime`) applied to content. Handle the keyboard (IME) so focused inputs stay visible.
- Sticky headers and footers must not hide focused elements (2.4.11). Use `scroll-padding-top`/`scroll-padding-bottom` equal to their height.

## Touch vs pointer
- Target sizes: at least 24x24 CSS px (web minimum), 44x44 pt (iOS), 48x48 dp (Android). On touch-first web, use 44-48 px for primary controls.
- Do not rely on hover. Every hover-revealed action must be reachable by tap and keyboard. Use `@media (hover: hover) and (pointer: fine)` for hover-only enhancements.
- Put primary mobile actions in the thumb zone (bottom half). Put destructive actions away from frequently tapped controls.

## Images and media
- Responsive images (`srcset`/`sizes`, `<picture>`), `max-width: 100%`, explicit `width`/`height` or `aspect-ratio` to prevent layout shift.
- Tables on narrow screens: horizontal scroll inside a labelled, focusable container (`role="region"`, `aria-label`, `tabindex="0"`), or a stacked card layout that keeps header-to-value association.

## RTL and logical properties
Use logical properties so layouts mirror automatically: `margin-inline-start`, `padding-inline`, `inset-inline-end`, `border-start-start-radius`, `text-align: start`. Native: leading/trailing (iOS), `start`/`end` (Android). See [content-microcopy](content-microcopy.md).

## Sources
- https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_queries
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Logical_properties_and_values
- https://developer.android.com/develop/ui/compose/layouts/adaptive/use-window-size-classes
- https://developer.apple.com/design/human-interface-guidelines/layout
