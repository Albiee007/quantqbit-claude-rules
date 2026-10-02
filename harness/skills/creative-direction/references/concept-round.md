# Concept round

Sub-agents can't talk to each other, so the main session runs the round: it briefs each creator in concept mode, collects their concepts, asks the creative-director to critique them, and puts the result to the owner.

## Who takes part
Only the families the request needs, and only families the direction requests:

| Family | Creator | Skill |
|---|---|---|
| store (screenshots, panorama, feature graphic) | `store-creative` | store-mockups (mobile projects) |
| marketing (social, Open Graph, email header, banner), logo | `brand-asset-creator` | brand-assets |
| icon | `icon-creator` | app-icons (mobile projects) |
| illustration | `illustrator` | story-art |

A web-only project never needs `store-creative` or `icon-creator`. Independent families run in parallel.

## Reuse path (no new round)
If the family's approved concept is still current (`direction.py status` shows it approved) and the request changes no visual decision (new copy, a new size, a re-render, a new frame that uses approved layouts and backgrounds), skip the round and go to production.

## Brief for a creator (from the main session)
```
MODE: concept
Family: store | marketing | icon | illustration
Direction: brand/direction.json (status from `direction.py status`)
Scope: <frames / assets / placements this concerns>
Previews: on | off
Run: <run id> (one per round; `direction.py concept new` creates files under it)
```

## What a creator does in concept mode
- **Reads** the direction, the tokens, the family skill and ui-ux, typography and color-science. Reads project sources; edits none of them.
- **Writes only** its own concept files, `brand/concepts/<family>/<run>/<id>.json`, plus previews under a gitignored folder (`<kit>/.preview/`, `out/creative/`, or wherever the family's preview command writes). Never the direction, tokens, kit content, approvals or production outputs. No kit `init`, no production render.
- **Proposes 2–3 concepts** that differ in decisions that matter for this project (layout family, background treatment, type treatment, device or render style, how the motif is used, colour emphasis). At most one is a "safe evolution" of what exists. Numbers alone (a slightly different angle) are not a different concept.
- **Previews** when it can: `render_frames.py preview --concept <file>`, `export_svg.py --plan ... --preview <dir> --concept <file>`, `make_icon_set.py preview --from-direction . --concept <file>`. A concept without a preview says so in `preview.unavailable` and is never described as visually reviewed.
- **Checks** each concept: `direction.py concept check <file>` (schema, references, contrast pairs, signals).

## What a creator returns
```
## Concepts: <family> for <project> (direction revision <n>, run <run id>)
### <id>: <name>
Idea: <one sentence tied to the audience, mood and motif>
Levers: <the choices that make it different, with their reasons>
Kept from the existing identity: <what and why, or none>
Checks: <concept check summary: contrast pairs, signals>
Risks: <fidelity, legibility at 300 px, effort>
Preview: <path> | unavailable: <why>
File: brand/concepts/<family>/<run>/<id>.json
```

## After the round
1. The creative-director critiques ([critique-guide](critique-guide.md)) and recommends, with required changes.
2. The main session shows the owner the previews and the critique. **The owner picks.**
3. The main session records it: `direction.py approve --gate concept --family <f> --concept <file> --by <owner> --evidence <where>`.
4. Production runs with the family skill.
