# Critique and review

The creative-director critiques concepts before the owner picks, and reviews production after it. Both are read-only: the director recommends; the owner decides.

## Priorities, in order
1. **Audience fit.** Does it speak to the audience and situation in the direction (where they meet it, at what size)?
2. **Fidelity and claims.** Store frames show the app as it ships; captions and images claim nothing the product can't back.
3. **Legibility.** Captions at about 300 px wide; computed contrast for every text/backdrop pair; REVIEW REQUIRED items listed for a person to check.
4. **Coherent identity.** The same roles, type and motif across families; consistent with approved earlier work unless the direction changes it on purpose.
5. **Distinctness, last.** Does it look like this project, or like a template? Use the [default signals](default-look.md) and category clichés from the brief as prompts. A signal is a question ("is Inter 800 here a choice?"), never a defect when the direction keeps it.

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
- Open every output (contact sheets, strips, canvases, icon preview sheet).
- Check coherence across families and drift from the direction.
- `direction.py compare <a.png> <b.png>` against earlier work or another family, if useful. It reports structure and palette distance as diagnostics; look at the images side by side before saying anything.
- Report: what is ready, what needs a person's eye (each REVIEW REQUIRED), and what should change.
