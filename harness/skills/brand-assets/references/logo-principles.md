# Logo principles

## A good mark
- **Simple:** it can be drawn from memory. It survives 16 px, a circle mask, one colour, and reversed on dark.
- **Distinct** from category clichés (a generic wallet, a coin or a chart arrow for finance). One idea per mark.
- **Built on a grid:** geometric construction, consistent stroke weights, optical (not mathematical) centring.
- **Useful as an app icon:** the mark must work as the glyph on a coloured tile, since `app-icons` builds from it.

## Directions: always present three
For each direction, show: the mark at 1024 and 32 px, on light and dark, as an app icon tile, and one sentence of rationale. Directions should differ in *idea*, not only in colour. Kinds of idea: a monogram, a symbol drawn from the core feature, an abstract shape expressing the positioning, a mark from the direction's motif, a wordmark-only solution. Draw each from the construction guide in `templates/logo-master.svg.template`; it holds no starting shape on purpose.

## Wordmark
- Pick a typeface with a licence that allows logo use; record the licence in `brand/README.md`. Choose it with [typography](../../typography/SKILL.md) (context, script coverage, licence terms).
- Adjust spacing by hand between letter pairs, and convert the text to outlines in the final SVG.
- Keep the capitalisation consistent everywhere (store title, icon, website): e.g. "SplitExpenZ", never "Splitexpenz".

## Clear space and minimum size
- **Clear space:** at least the height of a defined element of the mark (e.g. its inner shape) on all sides.
- **Minimum size:** 16 px for the mark alone, and whatever size keeps the wordmark's x-height at 8 px or more on screen.

## Colour and contrast
- A logo is branding: WCAG exempts logos and logotypes from its text-contrast rule, and non-text contrast (1.4.11) covers graphics needed to understand content or operate UI. So no WCAG threshold applies to the mark itself unless it acts as UI (e.g. the only label of a home link). Still report the mark's ratio on each background it is used on, and meet any target the project set; low-contrast marks vanish at small sizes.
- Any text in brand images (canvases, banners) meets WCAG at the size it is shown.
- Provide full colour, mono black, mono white, and the tints used in the UI.

## Don'ts
No gradients or shadows the mark depends on, no thin hairlines, no stock icons, no marks that resemble other brands. Check trademark databases before the owner commits to a name or mark. Say so explicitly: the agent can't clear trademarks.
