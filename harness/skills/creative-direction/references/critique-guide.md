# Critique and review

The creative-director critiques concepts before the owner picks, and reviews production after it. Both are read-only: the director recommends; the owner decides.

## Priorities, in order
1. **Audience fit.** Does it speak to the audience and situation in the direction (where they meet it, at what size)?
2. **Fidelity and claims.** Store frames show the app as it ships; captions and images claim nothing the product can't back.
3. **Legibility.** Captions at about 300 px wide; computed contrast for every text/backdrop pair; REVIEW REQUIRED items listed for a person to check.
4. **Coherent identity.** The same roles, type and motif across families; consistent with approved earlier work unless the direction changes it on purpose.
5. **Distinctness, last.** Does it look like this project, or like a template? Use the [default signals](default-look.md) and category clichés from the brief as prompts. A signal is a question ("is Inter 800 here a choice?"), never a defect when the direction keeps it.

## Motion (video concepts and storyboards)
- **Pace against reading.** Does every scene hold long enough to read its words? `render_video.py lint` reports estimates; watch the draft before agreeing.
- **Restraint and consistency.** One default transition and one text entrance carry most videos; each extra one needs a reason. Motion should feel like the stills it animates.
- **Identity continuity.** Same backgrounds, type, accents and motif as the approved stills unless the direction changes them on purpose.
- **Comfort and safety.** Nothing flashing more than three times a second, no large parallax or spins, text inside the safe insets. Treat the flashing and safe-area results as signals to look at.
- **Voice.** Does the casting and pace in the voice prompt fit the audience and the mood? Do the lines say only what the product can back?

## Critique output
```
## Critique: <family>, run <run id>
| Concept | Audience fit | Fidelity | Legibility | Identity | Distinct | Notes |
|---|---|---|---|---|---|---|
| a | strong / fair / weak | ... | ... | ... | ... | ... |
Recommendation: <id>, because <reason>.
Required before production: <changes, or none>
Signals discussed: <signal: kept on purpose / should change, why>
Not verified: <what could not be checked (no preview, no device)>
```
Never rank by a count of signals and never set a similarity threshold. When two concepts differ only by numbers, say so and ask the creator for a real alternative.

## Review after production
- `direction.py runs` and the run manifests: statuses, REVIEW REQUIRED checks, approvals in force.
- Open every output (contact sheets, strips, canvases, icon preview sheet, video sheets and the videos themselves).
- Videos: `render_video.py status` lists review items still open; an output with open items is published but not ready to use.
- Check coherence across families and drift from the direction.
- `direction.py compare <a.png> <b.png>` against earlier work or another family, if useful. It reports structure and palette distance as diagnostics; look at the images side by side before saying anything.
- Report: what is ready, what needs a person's eye (each REVIEW REQUIRED), and what should change.
