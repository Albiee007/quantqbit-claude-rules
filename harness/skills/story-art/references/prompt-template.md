# Prompt template

A prompt is the **style bible** (identical for every image in the set) followed by **one scene**. Lock the style bible before the first generation and copy it verbatim into every prompt; small wording changes drift the style.

## Style bible
```
<Render style>, <scene>. Color palette <primary name> (<hex>), <secondary name> (<hex>),
<light tint name> (<hex>) with <accent name> (<hex>) accents, <lighting>.
<Background>. <Negative list>.
```
- **Render style:** one phrase, e.g. "Stylized modern 3D illustration, soft clay render style" or "Flat vector illustration, soft grain".
- **Palette:** 3–4 hexes from the brand tokens, named. The accent is the one colour that pops. If the tokens don't settle the palette, decide it with [color-science](../../color-science/SKILL.md).
- **Lighting:** one phrase, e.g. "warm soft lighting".
- **Background:** the page the art sits on decides it, e.g. "Dark indigo/navy backdrop" for a dark site.

## Scene
```
<who: count, fictional, inclusive casting> <doing what> <where>, <the key objects, named exactly>,
<the emotion>.
```
- Name exact symbols and objects: "floating ¥ € $ £ ₹ symbols", not "currency symbols".
- Describe the phone's screen as shapes ("a donut chart"), never as an app.

## Negative list (append to every prompt)
```
No text, no letters, no numbers, no logos, no brand names, no real people or celebrity likenesses,
no real banknote designs, no cryptocurrency or bitcoin symbols, no app interfaces.
```
Add a scene-specific negative when a review catches a defect, and keep it for the rest of the set.

## Worked example (fictional expense-splitting app)
Style bible, used for all four images:
```
Stylized modern 3D illustration, soft clay render style, <scene>. Color palette deep indigo
(#1d0f8a), violet (#5b4ff0), lavender (#c3c0ff) with mint green (#9ff3cf) accents, warm soft
lighting. Dark indigo/navy backdrop. No text, no letters, no logos, no brand names.
```

| Scene | Feature pillar | Scene text |
|---|---|---|
| `trip` | Group trip expenses | A diverse group of four friends abroad on a lantern-lit night street, a temple silhouette behind them, one holding a phone, all smiling |
| `currency` | Trip money in foreign currency | A traveller at an airport currency-exchange counter, floating ¥ € $ £ ₹ symbols above, no cryptocurrency or bitcoin symbols |
| `roommates` | Household bill splitting | Three flatmates unpacking groceries together in a shared kitchen, relaxed and chatting |
| `personal` | Personal expense tracking | A person relaxing on a sofa looking at a phone showing a donut chart, floating coffee cup, shopping bag, bus and house icons |

What the review caught: the first `currency` prompt listed "baht ฿", and the image showed a ₿-like glyph. The fix was to name only the symbols wanted and add "no cryptocurrency or bitcoin symbols". Regenerated once, approved.

Exported as `art-trip-1200.webp` etc. at 640 and 1200 px; the largest (the busy night street) was 94 KB WebP and 72 KB AVIF at 1200 px, inside the 120 KB budget.
