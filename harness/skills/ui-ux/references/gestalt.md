# Gestalt Principles for UI

People perceive a layout as groups and wholes before they read its details. Use these principles to make structure obvious without extra chrome. Proximity is among the strongest grouping cues and can override the others.

| Principle | Perception | Apply in UI | Common violation |
|---|---|---|---|
| **Proximity** | Items close together are seen as a group | Label tight to its field. More space between groups than within them. Spacing tokens encode this (for example 4-8 inside, 16-24 between, 32+ between sections) | A label equidistant from two fields. Uniform spacing everywhere |
| **Similarity** | Items that look alike (color, shape, size) are seen as related | One style per function: all links alike, all destructive actions alike | Two identical-looking buttons with different behavior. A link that looks like body text |
| **Common region** | Items inside a shared boundary are grouped | Cards, panels, table rows, grouped form sections (`fieldset`) | A control rendered inside one card that acts on another |
| **Uniform connectedness** | Visually connected items are more related | Steppers joined by a line, tabs attached to their panel, connectors in diagrams | Decorative lines that connect unrelated items |
| **Closure** | The eye completes incomplete shapes | Minimal icons. Partially visible next card signals horizontal scroll | Cropping content so it looks complete and users miss that it scrolls |
| **Continuity (continuation)** | Elements on a line or curve are seen as related and followed | Align to a grid. Consistent left edges. Horizontal carousels hint at continuation | Ragged alignment that breaks scanning |
| **Figure/ground** | We separate foreground objects from background | Scrims behind modals, elevation or tonal surfaces for overlays, sufficient contrast | A low-contrast dialog that blends into the page |
| **Prägnanz (simplicity)** | Ambiguous shapes are read in their simplest form | Simple geometric icons and layouts | Over-detailed icons at small sizes |
| **Symmetry and order** | Symmetric arrangements read as organized wholes | Balanced layouts for static content. Consistent grid | Accidental near-symmetry that looks like a mistake |
| **Common fate** | Items moving together are grouped | Animate related items together (list reorder, expanding group) | Unrelated items animating in sync, implying a relation |
| **Focal point (emphasis)** | The item that differs draws attention (see Von Restorff in [laws-of-ux](laws-of-ux.md)) | One primary action per view | Many competing accents |

## Review checks
- Squint test: blur the screen. Groups and the primary action must still be identifiable.
- Spacing within a group is strictly smaller than spacing between groups.
- Every visual grouping matches the functional grouping (and the programmatic grouping: `fieldset`, lists, landmarks).
- Grouping survives every breakpoint. Stacking on narrow screens must not separate labels from their controls.

## Sources
- https://www.nngroup.com/articles/gestalt-proximity/
- https://ixdf.org/literature/topics/gestalt-principles
- https://lawsofux.com/
