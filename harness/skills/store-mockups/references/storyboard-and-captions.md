# Storyboard and captions

The first 2–3 screenshots do most of the converting: many users never scroll the gallery. Plan the set as one story, not as a tour of the tabs.

## Order (8 frames is a good default; both stores allow up to 8 on Play and 10 on iOS)
1. **The promise.** The one screen that shows what the app is for, with a headline that states the positioning.
2. **The differentiator.** The feature competitors don't have (e.g. bills in any currency on a trip).
3. **Its payoff.** The screen that proves the differentiator works (e.g. "what's left, who holds it").
4. **The core action.** Adding the main item, showing the choices users care about.
5. **The resolution.** The outcome users want (settled up, goal reached, report ready).
6–7. **Supporting pillars:** insights, recurring items, reminders.
8. **Breadth or social proof:** all the use cases, or a no-sign-up sharing path.

Use the same order on both stores, dropping frames of platform-gated features on the other platform.

## Captions
- **Headline: at most 6 words,** benefit first, in the user's language. Mark 1–3 words with `<em>` for the accent colour. Good: "Travel abroad. Split in <em>any currency.</em>" Bad: "Multi-currency ledger engine".
- **Sub-caption: at most 12 words.** It says how, using the app's own label ("Trip money tracks every yen…").
- **No claims the frame doesn't show.** Captions are metadata, so the `store-listing` truth table applies to them too.
- **Readable at thumbnail size.** The headline must be legible at about 300 px wide. Keep it to 2 lines on phones and 3 at most.
- Keep captions in `frames.json`, and mirror them in the LISTING.md caption table, which doubles as alt text.

## Composition rules learned the hard way
- **Nothing on top of the figures a frame is about.** Drop the floating action button, snackbars and badges from a frame when they would cover an amount or a list value. Keep them where they cover nothing, because they show the app is real.
- **End the scroll on something meaningful.** A clipped half-row at the bottom reads as "there's more". A clipped headline or amount reads as a bug.
- **One focal point per frame.** If a frame needs two captions, it's two frames.
- **Tablets reuse the phone screens** on a wider canvas; the kit does this automatically. Make real tablet layouts only if the app has them.
