---
name: creative-direction
description: Project-specific creative direction for every media asset — store screenshots and panoramas, the Play feature graphic, social/Open Graph/email/banner images, logos, app icons, story art and videos. Derives a direction from the project's own evidence (code, listing, brand docs, tokens) with the ui-ux, typography and color-science skills, records it as brand/direction.json, runs a concept round where the creator agents propose genuinely different options, and binds owner approvals to the exact inputs they approved, so production renders follow the project instead of harness defaults. Use when starting or refreshing any media asset, when outputs look generic or alike across projects, when an asset family needs concepts for the owner to choose from, or when checking whether media may be produced (approvals, stale approvals, migrating 1.6 kits).
---

# Creative Direction

Every media asset looks like **this project**, chosen by **its owner**. The harness supplies methods, renderers and checks; it supplies no look of its own. Existing identity and visual fidelity come before novelty: a project that already uses Inter, indigo or clay keeps them when that is the choice.

## The flow
1. **Discover** (creative-director). Read the project's evidence with [context-discovery](references/context-discovery.md). Reuse existing brand and design-system docs; write `brand/BRIEF.md` from [brief-template](references/brief-template.md) only when no strategy document exists.
2. **Direct** (creative-director). Write `brand/direction.json` ([direction-schema](references/direction-schema.md)) and generate `brand/DIRECTION.md` from it (`direction.py summary`). Colours and type come from the project's tokens, built or extended with `palette.py` and `type_scale.py` (color-science, typography). Never start a second palette.
3. **Gate 1: the owner approves the direction.** The main session shows the summary and open questions, then records the decision: `direction.py approve --gate direction --by <owner> --evidence <where they said it>`.
4. **Concept round.** Only the creators the request needs ([concept-round](references/concept-round.md)): `store-creative` (store), `brand-asset-creator` (marketing, logo), `icon-creator` (icon), `illustrator` (illustration), `video-creative` (video). Each proposes 2–3 alternatives that differ in decisions that matter, with previews when it can render them. An unchanged approved family takes the reuse path instead.
5. **Critique** (creative-director): [critique-guide](references/critique-guide.md). Audience fit, fidelity, legibility and a coherent identity first; [default signals](references/default-look.md) are prompts for discussion, never verdicts.
6. **Gate 2: the owner picks one concept per requested family.** The main session records it: `direction.py approve --gate concept --family <f> --concept <file> ...`.
7. **Production** with the family skill: `render_frames.py render`, `export_svg.py --plan`, `make_icon_set.py generate --from-direction`, the story-art style bible from `direction.py resolve illustration`, or `render_video.py render` (video also needs Gate 3, the owner's approval of each piece's storyboard). Production commands enforce the gates; each run writes `brand/runs/<family>/<run>.json`.
8. **Review** (creative-director): coherence across families, drift from the direction, every REVIEW REQUIRED item looked at. The family skills' own final gates still apply (contact sheet sign-off, per-image approval for story art, store pre-check).

## Approvals
- An approval binds the gate to the **content hash and the resolved-input hash** (token values, font files, motif, logo) it approved. Change either and the gate reports the approval as stale, naming what changed; only the affected scope is invalidated (a store concept edit leaves the icon approval alone; a direction change invalidates every concept chosen under it; requesting or briefing a family, including video, leaves the other families' approvals current; a role colour invalidates the concepts that use it).
- Approvals recorded by 1.7 (no `hashVersion`) keep working: they are checked the way 1.7 hashed them, so they stay current until something they depend on changes, but any family's brief still makes them stale. `direction.py status` notes them; re-approving switches them to scoped hashes.
- Video adds two records: `--gate storyboard --piece <id>` (the owner approves a piece's visuals, timing and script) and `--gate review --run <run> --items <ids|all>` (the owner has looked at a render's REVIEW REQUIRED items; bound to that run's output hashes).
- **Only the owner approves.** Agents never run `direction.py approve`, never invent evidence and never treat their own recommendation as a decision. The main session records what the owner said and where.
- Approval of a direction or concept is not approval of images nobody has seen, and never permission to publish or upload.
- Reuse what is approved: a copy fix, a new size or a re-render of unchanged work needs no new concept round.
- An override outside the approved concept (a frame layout, a canvas background) is refused until the owner approves that exception: `direction.py approve --gate exception --scope "<the scope the error names>"`.
- These records stop accidental drift. They are not tamper-proof.

## Rules
- **Evidence over invention.** Every fact in the direction cites a source; owner preferences cite who and where; agent inferences are labelled as inferences and confirmed at Gate 1. A missing source is an open question, never an invented citation.
- **Tokens for authored roles.** Colours and type in the direction and concepts are token references. Photos, screenshots, generated images and legacy kits are exempt; palette tokens guide generation but don't constrain its pixels.
- **Contrast where text meets a real backdrop.** Computed PASS/FAIL where the backdrop colour is known; sampled estimates are REVIEW REQUIRED (or FAIL when low), never a normative pass. Ratios are compared at full precision and only truncated for display.
- **Logos and launcher icons are branding.** No WCAG threshold applies to them unless they act as UI; a project may set a target (`qualityTarget`), and an override never waives a requirement that does apply.
- **No fixed number of concepts by quota**, no "N default signals = fail", no image-distance pass mark. Consistency with an approved earlier campaign is often right.
- **No mandatory remote service.** Fonts are local files (with licence evidence) or stated system fonts; renders never fetch from the network. Paid or unavailable generators are named as such.
- **One owner per file.** The director edits `brand/direction.json` and tokens; creators write only their own concept folders (unique run IDs); the main session records approvals.

## Tools
`python .claude/skills/creative-direction/scripts/direction.py <command> [--project .]`

| Command | Use |
|---|---|
| `init --name X` | Draft `brand/direction.json` and `DIRECTION.md` |
| `validate` | Schema, token references, font records and licences, every concept, declared contrast pairs |
| `status` | Which gates are met, and why not |
| `approve --gate direction\|concept\|exception\|storyboard\|review ...` | Record an owner decision (main session only) |
| `summary` | Regenerate `brand/DIRECTION.md` |
| `concept new --family F --id ID --name N [--run R]` / `concept check FILE` | Start / check a concept |
| `resolve FAMILY [--concept FILE]` | The resolved values (style bible inputs for illustration) |
| `signals FILE` / `compare A.png B.png` | Diagnostics only |
| `migrate` | Report 1.6 kits, copied 1.6 templates and plan entries to migrate (changes nothing) |
| `runs [--family F]` | Production run manifests |

Exit codes: 0 done, 1 invalid data or an unmet gate, 2 bad arguments or a missing dependency.

## References
- [context-discovery](references/context-discovery.md): what to read, how to cite it, what to ask.
- [direction-schema](references/direction-schema.md): `direction.json`, concepts, approvals and run manifests.
- [brief-template](references/brief-template.md): `brand/BRIEF.md` when no strategy document exists.
- [mood-levers](references/mood-levers.md): turning mood axes into type, colour, layout and illustration choices (heuristics).
- [concept-round](references/concept-round.md): the contract every creator follows in concept mode.
- [critique-guide](references/critique-guide.md): how the director critiques and reviews.
- [default-look](references/default-look.md): the harness 1.6 defaults, as discussion signals.
- [modes-and-migration](references/modes-and-migration.md): legacy, draft and production modes per command; migrating 1.6 kits and templates.
- Related skills: `ui-ux`, `typography`, `color-science` (always), and the family skills `store-mockups`, `brand-assets`, `app-icons`, `story-art`, `brand-video`.
