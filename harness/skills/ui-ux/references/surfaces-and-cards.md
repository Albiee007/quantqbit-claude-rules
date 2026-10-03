# Surfaces and cards

Apply this polish pass to cards, tiles, list rows, and dialogs. These are craft heuristics, not WCAG requirements or a replacement design system. The project's components and tokens win under [precedence](../SKILL.md#precedence); accessibility floors always apply. Numeric craft examples below are fallback defaults to define in token sources only when the project has no equivalent tokens. Contrast ratios are standards, not defaults.

## Polish pass: six decisions
| Decision | Implement and review |
|---|---|
| Hierarchy | One dominant element per component: title, key value, or primary action. Use size and weight steps from the existing type scale; supporting content must not compete. See [hierarchy-and-measure](../../typography/references/hierarchy-and-measure.md). |
| Spacing | Express proximity with inset > between groups > between related lines. Fallback on the 4/8 scale: 24 / 16 / 8 px respectively. Use semantic spacing tokens, not literals. See [gestalt](gestalt.md). |
| Color | At most three text tiers: primary, secondary, tertiary, each a semantic token verified on its actual background in every theme. All normal text needs 4.5:1; 3:1 applies only to large text as defined in [wcag-22-aa](wcag-22-aa.md). Tertiary is the lowest-emphasis gray that passes, never decorative gray. One accent role per component, reserved for the key value and primary action; reinforce with size, weight, or a label. Status colors retain text or icons and never become competing accents. |
| Depth | Choose treatment from the background table below. A restrained raised-surface recipe uses a subtle border (fallback 1 px), an optional surface gradient slightly lighter at the top, and a soft shadow offset downward. Keep one implied light source and two shadow tokens, rest and raised. This is not a requirement to put every effect on every surface. In forced colors, shadows disappear: retain a real border. A boundary needed to identify a control or state must meet 3:1; decorative borders need not. |
| Corners | Inner radius = max(0, outer radius − inset), then snap to an existing radius token (or floor at the system's small radius token). Fallback example: 24 px outer − 8 px inset = 16 px inner. Use the actual edge-to-edge inset, including border thickness. Siblings share radius and elevation tokens. |
| Motion | Motion confirms, never performs. Optional defaults: entrance stagger 30–50 ms per item, capped at six animated items and 300 ms maximum start delay; hover lift a few px with raised shadow; button press scale about 0.97; duration 150–300 ms, ease-out. Use tokens within [motion](motion.md)'s 100–500 ms range. Hover lift requires `(hover: hover) and (pointer: fine)`; remove lift, stagger, and press scale under reduced motion. |

### Nested radius in CSS
Compute and snap the inner token in the token source; CSS cannot discover the nearest token. This illustration assumes the subtraction already lands on a project radius token. Otherwise consume the precomputed `--radius-surface-inner` directly.

```css
.surface {
  border-radius: var(--radius-surface);
  padding: var(--space-surface-inset);
}
.surface__media {
  border-radius: max(0px, calc(var(--radius-surface) - var(--space-surface-edge-inset)));
}
```

`0px` is the mathematical floor, not a new radius token. For asymmetric insets, compute each corner from its adjacent edges rather than assuming one uniform inner radius.

## When something is a card
A card represents one entity, one title, one subject, and one destination. Product, article, and project summaries fit. Form sections, settings groups, and page layout regions are panels or groups; boxing everything as cards hides hierarchy. Static summaries can use the same surface styling without pretending to be clickable.

## Background decides the treatment
| Background | Default treatment | Review check |
|---|---|---|
| White / base page | Border | The surface remains identifiable against the page. |
| Tinted / gray page | Soft shadow or contrasting tonal surface | Elevation reads without adding a heavy outline. |
| Inside a panel | Flat; group with dividers or spacing | No additional card container or shadow. |

Never combine border + heavy shadow + tint. A subtle structural border may accompany a soft shadow where needed for contrast or forced colors. Use theme tokens rather than literal white or gray.

## Clickable cards
On the web, use exactly one native title link stretched across the surface. Its accessible name is the visible title; do not wrap the whole card and its headings in an anchor, and do not replace the link with a `div` click handler. Keep the native link's keyboard, open-in-new-tab, and context-menu behavior. Hover feedback affects the whole surface.

```html
<li class="card">
  <h2><a class="card__link" href="/projects/atlas"><span class="card__selectable">Atlas project</span></a></h2>
  <p class="card__selectable">A summary users can select and copy.</p>
</li>
```

```css
.card {
  position: relative;
  isolation: isolate;
  border: var(--border-width-subtle) solid var(--color-border-subtle);
  border-radius: var(--radius-surface);
  background: var(--color-surface-default);
  box-shadow: var(--shadow-surface-rest);
}
.card__link::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
}
.card__link:focus-visible::after {
  outline: var(--border-width-focus) solid var(--color-border-focus);
  outline-offset: var(--space-focus-offset);
  border-radius: var(--radius-surface);
}
.card__selectable {
  position: relative;
  z-index: 1;
  user-select: text;
}
@media (forced-colors: active) {
  .card { border-color: CanvasText; }
  .card__link:focus-visible::after { outline-color: Highlight; }
}
@media (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference) {
  .card { transition: transform var(--duration-surface) var(--easing-decelerate); }
  .card:hover {
    transform: translateY(var(--offset-surface-hover));
    box-shadow: var(--shadow-surface-raised);
  }
}
```

The hover offset token is negative. Shadow changes immediately; only transform animates, consistent with [motion](motion.md). Do not clip the focus outline; verify its 3:1 contrast and visibility. Keep the native link focus fallback.

A stretched pseudo-element masks text selection. Raising selectable text above it, as here, leaves deliberate non-clickable summary regions; the title still belongs to the native link and the rest of the surface remains clickable. Keep the link itself unpositioned so its pseudo-element stretches relative to the card. Do not promise simultaneous click-anywhere and unrestricted selection, or disable selection to hide the tradeoff. Verify dragging to copy title and summary text, Tab/Enter, and clicking the remaining surface.

Two or more controls (for example a destination link and a favorite button) make a panel with separate explicit targets. Remove the stretched link; never nest controls inside it or add duplicate focus stops for the same destination. This single-action convention is this harness's default, not a claim that HTML or Material forbids all multi-action cards.

## Never nest cards
Flatten the inner container. Use spacing, a divider, or a section heading to express grouping. Nested borders, shadows, and radii make one entity look like several unrelated entities.

## Media in cards
Use one aspect-ratio token across a grid (fallback 16:9), `aspect-ratio: var(--aspect-media-card)` and `object-fit: cover`. Give the media box a constrained inline size so the ratio determines its height; never stretch the image. Preserve important subjects when cropping. Inset images use the nested-radius formula; edge-to-edge media follows the outer shape. Meaningful images need useful alt text; redundant or decorative images use empty alt text. See [wcag-22-aa](wcag-22-aa.md).

## Dark mode
Shadows barely distinguish dark surfaces. Bring the border back one tonal step lighter than the surface, and express elevation with lighter surface tint. Verify all text and meaningful boundaries on the final composited surface, including gradients. Reuse [product-palettes](../../color-science/references/product-palettes.md), [M3 tonal surfaces](material3.md), and [Apple elevated backgrounds](apple-hig.md). Do not invent a second dark palette.

## Platform notes
| Platform | Apply the same decisions with native components |
|---|---|
| Compose | `OutlinedCard` for a border on a base page; `ElevatedCard` for a raised surface on a tinted page; filled `Card` for a tonal treatment. Inside panels, use flat `Column`/`Row` groups. Theme shape, color, and elevation win. Use native clickable overloads and accessibility semantics for single-action cards. |
| SwiftUI | Reuse semantic grouped backgrounds for settings and form panels. Use `.background(.regularMaterial)` when translucency suits the hierarchy, honoring Reduce Transparency and contrast; it is not a universal card fill. Use native navigation/control semantics. |
| React Native | Reuse the project's shadow abstraction: iOS shadow props and Android `elevation` have different behavior. Where supported by the app's RN version/architecture, `boxShadow` is an alternative; verify platform support. Keep borders and tonal surfaces for dark mode and accessible native press semantics. |

## Sources
These sources support semantics, platform APIs, and accessibility behavior. The six-decision recipes, single-action convention, no-nesting heuristic, and numeric craft defaults above are harness guidance, not normative requirements from these sources.
- https://m3.material.io/components/cards/overview
- https://developer.android.com/develop/ui/compose/components/card
- https://developer.apple.com/design/human-interface-guidelines/layout
- https://developer.apple.com/design/human-interface-guidelines/materials
- https://developer.apple.com/documentation/swiftui/material
- https://reactnative.dev/docs/view-style-props
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/box-shadow
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/aspect-ratio
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/border-radius
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/forced-colors
- https://inclusive-components.design/cards/
- https://www.nngroup.com/articles/cards-component/
- https://www.w3.org/TR/WCAG22/
