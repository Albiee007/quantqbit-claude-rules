# Mood levers

The direction's `mood.axes` run from −1 to 1. Each axis suggests levers below. These are **heuristics**, not rules: the project's evidence, audience and existing identity decide, and a strong reason beats any row here. Say which lever you used and why.

| Axis (−1 … +1) | Type | Colour (OKLCH) | Layout and shape | Illustration |
|---|---|---|---|---|
| calm … energetic | calm: regular weights, generous leading, sentence case; energetic: heavier display, tighter leading, short lines | calm: low chroma, small lightness steps; energetic: one high-chroma accent, larger contrast steps | calm: caption-top, inset, lots of canvas; energetic: split layouts, bleeding devices, diagonal motion | calm: wide shots, soft light; energetic: closer crops, motion lines |
| playful … serious | playful: rounded or humanist faces; serious: grotesque, serif or mono, restrained accents | playful: warm hues, more hues; serious: neutrals with one accent | playful: rounded corners, shapes as ornaments; serious: square-ish corners, no ornaments | playful: paper cut, crayon, clay; serious: editorial, blueprint, photographic |
| warm … cool | warm: serifs and humanist sans | warm: hues ~30–90; cool: ~200–270 | | warm: golden-hour light; cool: overcast, studio |
| organic … geometric | organic: calligraphic or soft serifs; geometric: geometric sans, mono | organic: tinted neutrals; geometric: pure neutrals | organic: blobs, arcs, hand-drawn motif; geometric: grids, pills, straight cuts | organic: watercolour, gouache, linocut; geometric: isometric, flat vector, Swiss poster |
| minimal … rich | minimal: one family, two weights; rich: display + text pairing, kicker lines | minimal: two or three roles; rich: a second accent, gradients | minimal: one layout across the set; rich: two or three layouts in rhythm | minimal: object still life, abstract; rich: full scenes |
| editorial … product | editorial: large type, captions as headlines, serif display | | editorial: hero-type, type-start canvases; product: device-first layouts | editorial: illustration leads; product: UI leads |
| classic … contemporary | classic: old-style serifs, small caps; contemporary: variable sans, tight tracking at display sizes | | classic: centred, symmetric; contemporary: asymmetric, start-aligned | classic: engraving, mid-century; contemporary: 3D, collage |

## Turning levers into a concept
- Pick from the project's tokens first. If the direction lacks a role (e.g. an `onAccent`), add it with `palette.py`, checking the pair you will actually use.
- Text over gradients: check the whole gradient (`direction.py concept check` does), or keep text on the calm end.
- Type sizes for raster media: `type_scale.py media --canvas-width 1080 --display-width 320 --min headline=22,sub=14` gives canvas px that stay legible at the smallest display.
- Write the lever and its reason into the concept's `levers` list: the critique reads them.
