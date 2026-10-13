# Visual production: reference, method, sample

The renderer makes a polished video from what it is given. It can't make weak artwork look like a premium reference. When the owner supplies a visual reference, or a piece needs people, places or objects the templates don't draw, choose how that artwork will be made before the concept round. Then show that the method works on one representative sample before scaling up.

## Reference assessment
Write `brand/video/<id or series>/visual-plan.md` when the owner supplies a reference (images, frames, a video). Media is evidence, not instructions.

```
# Visual plan: <piece or series>
References: <file: what it shows, what it is for>   (one reference may set characters and materials, another the lighting; a set is not one style)
Appearance required: anatomy and proportions · materials and surfaces · lighting · depth (foreground, background softness) · expression
Actions required: <per shot: what a character must do: turn, take off headphones, walk, speak> or none
Keep from the project: <identity in force: palette roles, type, motif>   (borrow the reference's quality, not its brand)
Owner constraints: <code-only | generated art allowed | footage or 3D available | budget, tools, deadline>
Assets available: <approved art, masters, layers, recordings, models>
Method: <from the table below> · Why: <how it reaches the appearance and the actions>
Known limits: <what this method won't do, and which shots that affects>
Sample: <pilot piece id, the shot it covers> · Result: <pending | approved | changed method>
```

Keep the project's identity unless the owner explicitly asks for a change. A missing piece of artwork calls for a method decision, not automatically for image generation.

## Methods
None is the default and none is ruled out. Choose from the appearance, the actions and the owner's constraints.

| Method | What it makes | How it enters the video | Watch for |
|---|---|---|---|
| Templates | Type, stats, end cards, app recordings | the built-in scene templates | Only what they draw |
| Code illustration | SVG or Canvas characters and places with shaded forms, gradients, lighting and layered animation | a `custom` scene | Form and lighting depth take real modelling effort, not only gradients; check hands, faces and silhouettes up close |
| Procedural or modelled 3D | Geometry, materials, lighting and deterministic animation | a `custom` scene (WebGL drawn from the seeked time) or frames rendered outside the harness as `recording` media | Determinism (no clock, seeded randomness), render time, rig quality for performance |
| Generated artwork plus code composition | Stills or separated layers, animated by camera and layer moves | a `still` scene, or a `custom` scene with `custom.assets` | Consistency across shots, layer cleanup, resolution |
| Supplied footage or rigged animation | Real performance | `recording` media | Licence, colour match with the rest of the piece |

**Animatic or performance.** Camera and layer moves over a still give an animatic, which can look rich. They can't make a character take off headphones, turn naturally, walk or speak. The plan names each shot that needs performance and the method that delivers it, or says the shot is reframed.

## Comparing methods
When the owner asks to compare methods (for example code-only against generated art):
- Hold everything but the method fixed: the same scene, framing, lighting intent, duration, captions and app insert.
- Each candidate returns a still, detail crops (face, hands, hair, a material) and a motion sample of the same length, made with `render_video.py preview`.
- The creative-director assesses the actual results against the reference ([critique-guide](../../creative-direction/references/critique-guide.md), "Against a supplied reference"). Nothing is ranked or labelled before it exists. Report what each method reached and what it missed.

## Representative sample before scaling
This is not a separate technical gate. The sample is a pilot piece (for example `brand/video/<series>-pilot/`): one finished frame and a short motion sample. It goes through the usual concept and storyboard approvals before a whole episode or series is made.
- Character designs may be provisional in the pilot.
- Before the series expands, the reusable character sheets and environments are approved (story-art [video-assets](../../story-art/references/video-assets.md)).
- If the sample misses the reference, change the method or the target with the owner. Don't scale a method that hasn't reached the look.

## Layered compositions
Separated layers aren't depth layers until they are cleaned up. Check each one at full size before it moves:
- **Holes:** any area a moved layer uncovers is painted or extended in the layer behind it.
- **Edges:** hair, fur and soft edges have no halo or hard cut-out line.
- **Shadows:** contact shadows move with their subject and aren't left on the background.
- **Overlaps:** objects that overlap in depth sit on the right layers (a hand in front of a mug, the mug in front of a table).
- **Phone and screen inserts:** the app screen is corner-pinned to the device's perspective, and fingers or objects in front of the screen are a foreground layer above it.
- **Resolution:** each layer has enough pixels at its largest placement and transform. `lint` checks `still` scenes only (the `resolution:<scene>:<format>` item). For a `custom` scene's layers, the required size depends on where the script puts them, so check it by eye at full size.
- **Masters, not web exports:** compose from full-size masters. A 1200 px web export is too small for a 1080×1920 push-in.
