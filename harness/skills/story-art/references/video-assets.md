# Art for video and episodic sets

Web story art is a handful of separate images. Video art is a cast and a set of places that have to stay the same across many shots, at a resolution that survives cropping and camera moves. This reference covers the differences. `brand-video`'s [visual-production](../../brand-video/references/visual-production.md) decides whether generated art is the method at all. Use this file when it is, or when generated plates feed another method.

## Start with a pilot
Make one representative shot first: one finished frame and a short motion sample, in a pilot piece. Do this before generating an episode or a series.
- Character designs may be provisional in the pilot.
- Once the owner approves the pilot, lock the character sheets and environments below. Expanding the series follows from that approval.

## Character sheets
One sheet per recurring character, approved before the series expands:
- front, three-quarter and profile views, at the same scale;
- three or four expressions the story needs;
- the wardrobe for each episode, with variants named ("hoodie, headphones on" and "hoodie, headphones round neck");
- proportions: head-to-body ratio, height relative to the others;
- palette swatches for skin, hair and clothing.

## Environment plates
One plate per recurring place (a hostel room, a café), wide enough to reframe. Shots crop or push into the plate rather than regenerating the room each time. A plate that will sit behind moving layers is painted complete, with no character in it.

## Shot list and continuity
Add a shot list to `plan.md`: shot id, plate, characters and their wardrobe variant, props, time of day and light direction, screen direction (who is on the left), framing, and what moves. Check each new shot against the previous one for continuity.

## Keeping characters consistent
- A provider's **reference-image input** (a character or style reference) improves consistency across shots. It doesn't guarantee it.
- Repeated prompt wording alone is a weak hold on identity.
- With or without references, review every shot against the character sheet: face shape, hair, proportions, wardrobe, skin tone. Reject drift as you would a broken hand ([review-checklist](review-checklist.md)).
- Record in `plan.md` which references each generation used. If the provider has no reference input, say so; the owner decides whether the consistency risk is acceptable.

## Masters at video resolution
- **Size:** at least the format's size × the camera zoom × a crop margin. A 1080×1920 shot with a 108 % push-in and 10 % reframing room needs about 1280×2280 or more. Request the provider's largest native size. An upscaler, if used, is a provider step and goes in provenance.
- **Where:** keep masters durably under `brand/art/<set>/masters/<shot>.png` and layers under `brand/art/<set>/layers/<shot>/<layer>.png`. These, not `out/` or web exports, are what `brand-video` uses. Large binaries can go in Git LFS or external asset storage instead of ordinary Git. Record which one in `plan.md`, and make sure the render machine has the files.
- **Never** feed `export_art.py`'s web files (640 or 1200 px, compressed) to a video.

## Layers
- Separate a master into plate, characters and foreground, either by generating the parts separately or with the provider's layer separation (for example Canva `separate-image-layers`).
- Separated layers need cleanup before they move: holes behind moved subjects, hair edges, contact shadows, overlaps, and phone inserts with occluding fingers. See the checklist in visual-production.
- Name layers by depth (`plate`, `mid`, `hero`, `fore`); these become the `custom.assets` names in the video.

## Approval and provenance
- The owner approves the character sheets, the plates and each shot's master on the contact sheet, as for web art.
- Each master and layer gets a provenance row: file, sha256, shot, prompt, references used, provider, media ID, date, approval.
- The 4–8 image quota is for a web set. For an episode, the owner sets the count, and generation stays one image at a time.
