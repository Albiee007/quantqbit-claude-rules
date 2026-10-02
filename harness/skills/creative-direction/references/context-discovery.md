# Context discovery

The direction rests on the project's own evidence. Read only what the project has, cite it, and turn every gap into a question for the owner.

## What to read (in this order, skipping what doesn't exist)
| Source | What it tells you |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `README*`, `docs/` | purpose, audience, tone, constraints the team already wrote down |
| Existing brand docs: `brand/BRIEF.md`, `brand/README.md`, `docs/brand*`, a design-system site or Figma link the docs name | positioning, personality, competitors, what must be kept |
| `brand/tokens.json`, `*.tokens.json`, `tokens/`, `src/theme`, `tailwind.config.*`, CSS custom properties, `Theme.kt`/`Color.kt`/`Type.kt`, asset catalogs | the colours and type in use: the source the direction maps roles onto |
| `package.json` / `app.json` / `app.config.*` / `build.gradle` / `Info.plist` | product name, description, category, platforms, locales |
| `store-assets/*/LISTING.md` and its guardrails file | the claims the product can make, the words it uses |
| 3–5 real screens (components or captures) | density, shapes, icon family, how the product actually looks |
| Existing media: the mockup kit and its `out/`, `public/og*`, icons, `out/story-art/*/plan.md` | what exists now; what the owner may want to keep |
| `brand/runs/*/` | what was produced before, under which approvals |

Don't read secrets or `.env` files. Don't browse competitors' sites unless the owner asks; record competitors the docs name.

## How to record it in `direction.json`
- **facts**: `{text, source}`. The source is a path (`README.md`, `src/theme/index.ts:12`) or a URL the docs give. If you can't point at it, it isn't a fact.
- **preferences**: `{text, by, evidence}` for things the owner said ("keep the green", owner, "chat 2026-10-02").
- **inferences**: `{text, basis}` for your reading of the evidence ("audience skews 35+ from the listing's tone", basis "LISTING.md vocabulary"). Gate 1 confirms or corrects them.
- **openQuestions**: what you could not establish. Ask them at Gate 1 instead of guessing.
- **keep**: existing identity the owner wants to keep (a typeface, a colour, a mark). Kept choices are never "defaults to avoid".

## Questions worth asking at Gate 1
- Which existing brand choices are fixed, and which are open?
- Who must this convince first (one audience), and where will they see it (store search, a feed, an email)?
- Two or three products or publications whose look the owner admires, and why; one they never want to resemble.
- Markets and languages (script coverage, RTL, cultural colour meaning).
- Anything legally or commercially sensitive (claims, people, regulated imagery).

## Tokens
Map the direction's roles (`canvas`, `ink`, `inkMuted`, `accent`, `onAccent`, `surface`, ...) to the project's existing tokens. When a role has no token yet, add one to the existing token file with `palette.py ramp ... --out <file>` (it never overwrites; `--replace` names any change) and record fonts with `type_scale.py font` (source, files and their hashes, licence evidence). Never create a second palette next to the project's own.
