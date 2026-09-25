# Logo principles

## A good mark
- **Simple:** it can be drawn from memory. It survives 16 px, a circle mask, one colour, and reversed on dark.
- **Distinct** from category clichés (a generic wallet, a coin or a chart arrow for finance). One idea per mark.
- **Built on a grid:** geometric construction, consistent stroke weights, optical (not mathematical) centring.
- **Useful as an app icon:** the mark must work as the glyph on a coloured tile, since `app-icons` builds from it.

## Directions: always present three
For each direction, show: the mark at 1024 and 32 px, on light and dark, as an app icon tile, and one sentence of rationale. Directions should differ in *idea*, not only in colour. Examples: a monogram, a symbol drawn from the core feature, and an abstract shape expressing the positioning.

## Wordmark
- Pick a typeface with a licence that allows logo use; record the licence in `brand/README.md`.
- Adjust spacing by hand between letter pairs, and convert the text to outlines in the final SVG.
- Keep the capitalisation consistent everywhere (store title, icon, website): e.g. "SplitExpenZ", never "Splitexpenz".

## Clear space and minimum size
- **Clear space:** at least the height of a defined element of the mark (e.g. its inner shape) on all sides.
- **Minimum size:** 16 px for the mark alone, and whatever size keeps the wordmark's x-height at 8 px or more on screen.

## Colour and contrast
- The primary on white and on the brand dark must each reach at least 3:1 (graphical objects, WCAG 1.4.11). Any text in brand assets must reach 4.5:1.
- Provide full colour, mono black, mono white, and the tints used in the UI.

## Don'ts
No gradients or shadows the mark depends on, no thin hairlines, no stock icons, no marks that resemble other brands. Check trademark databases before the owner commits to a name or mark. Say so explicitly: the agent can't clear trademarks.
