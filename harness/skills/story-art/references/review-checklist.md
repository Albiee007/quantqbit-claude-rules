# Review checklist

Open every image at full size and at the size it will be shown. Reject on any **Reject** item; regenerate with a corrected prompt (and a scene-specific negative), then review again.

## Reject
- **Wrong or invented glyphs:** currency symbols that aren't the ones asked for, ₿-like marks, mirrored or melted characters.
- **Any text:** letters, numbers, signage, labels, watermarks, even when blurry.
- **Logos and brands:** recognisable logos, trade dress, other apps' interfaces, real banknote designs, branded products.
- **People:** extra or fused fingers, broken hands, distorted faces or eyes, a likeness of a real or famous person, a cast that is less diverse than the storyboard asked for.
- **Untrue story:** the scene implies a feature, partner or result the product doesn't have (a bank card the app doesn't issue, a payment it doesn't make).
- **Off-brand:** colours outside the style bible, a different render style from the rest of the set, harsh lighting in a soft set.
- **Unsafe or insensitive content:** stereotypes, alcohol or gambling where the store rating forbids it, cultural or religious symbols used as decoration.

## Fit
- **Contrast with the page:** the subject reads against the page background; the image's edge doesn't vanish into a same-colour section, or it gets a card or border.
- **Crop:** the subject survives the 640 px crop and any overlapping element (a phone mockup over a corner).
- **Consistency:** side by side on the contact sheet, the set looks like one family.

## Accessibility
- Decorative art: `alt=""`, and no information that exists only in the image.
- Meaningful art: alt text describes the moment in one sentence ("Four friends checking a shared trip bill on a night street").
- Any text near or over the art meets 4.5:1 (3:1 for large text) on the art behind it.

## Performance budgets
| Width | Budget per file | Notes |
|---|---|---|
| 1200 px | ≤ 120 KB | AVIF under 80% of the WebP size |
| 640 px | ≤ 50 KB | For phones via `srcset` |
- Explicit `width` and `height` on every `<img>` (no layout shift).
- `loading="lazy"` below the fold. Art is never the LCP image unless it is the hero; a hero gets `fetchpriority="high"` and no lazy loading.
- `export_art.py export` enforces the budgets and exits non-zero when one can't be met.
