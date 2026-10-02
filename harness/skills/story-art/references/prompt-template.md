# Prompt template

A prompt is the **style bible** (identical for every image in the set) followed by **one scene**. Lock the style bible before the first generation and copy it verbatim into every prompt; small wording changes drift the style.

## Style bible
The approved illustration concept supplies it: `python .claude/skills/creative-direction/scripts/direction.py resolve illustration` prints the style, palette (token references with their hexes), lighting, background, texture, shot, story world, negatives and ratio.
```
<Render style>, <scene>. Colour palette <name> (<hex>), <name> (<hex>), <name> (<hex>) with <accent name> (<hex>)
as the accent, <lighting>. <Texture>. <Background>. <Negative list>.
```
- **Render style:** from the concept (see [style-vocabulary](style-vocabulary.md)). There is no default style.
- **Palette:** the concept's token references, named and with their hexes. The accent is the one colour that pops. Generated pixels won't match the tokens exactly; that's expected.
- **Lighting and background:** from the concept, chosen for where the art sits on the page (text overlaid on it needs a calm area).

## Scene
```
<who: count, fictional, inclusive casting, or no people> <doing what> <where, in the story world>,
<the key objects, named exactly>, <the register>.
```
- Name exact symbols and objects: "a paper map with three red pins", not "travel items".
- Describe a device's screen as shapes ("a simple bar chart"), never as an app.

## Negative list (append to every prompt)
```
No text, no letters, no numbers, no logos, no brand names, no real people or celebrity likenesses,
no real banknote designs, no app interfaces.
```
Add the concept's `negatives` and any scene-specific negative a review catches, and keep them for the rest of the set (e.g. "no cryptocurrency symbols" for a product that doesn't deal in them).

## Two worked style bibles (fictional, deliberately different; neither is a default)
**Garden journal, risograph:**
```
Risograph print illustration, two-colour overlap with slight misregistration, <scene>. Colour palette moss
(#1c3827), clay (#9a4a26), sand (#fbf4ea) with clay as the accent, soft overcast morning light. Visible paper
grain. Plain sand ground with generous empty space at the top. No text, no letters, no logos, no brand names.
```
**Fleet dispatch, isometric:**
```
Isometric illustration, 30-degree axes, tidy detail, <scene>. Colour palette slate (#1b2330), steel (#5d6b7e),
fog (#e7ebf0) with signal orange (#e8590c) as the accent, sodium street light at dusk. Smooth flat shading.
Dark slate ground. No text, no letters, no logos, no brand names, no app interfaces.
```

What reviews catch: a vague noun gets a guessed glyph (asking for "baht ฿" once produced a ₿-like mark). Name only the symbols wanted and add a negative for the look-alike.
