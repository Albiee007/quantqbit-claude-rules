# Direction files

All of these are project-owned and committed. The machine-readable schemas ship in `.claude/harness/lib/harnesslib/schemas/`; `direction.py validate` applies them and rejects unknown schema versions, unknown keys, bad enums, duplicate IDs, unsafe paths (absolute, `..`, backslashes) and non-finite numbers.

## `brand/direction.json` (schemaVersion 1)
```jsonc
{
  "schemaVersion": 1,
  "project": "Fernway",
  "revision": 3,                       // bump on every edit you want reviewed
  "summary": "Two or three sentences: how it should look and feel, and why.",
  "tokens": {
    "source": "brand/tokens.json",     // the project's existing DTCG file
    "roles": { "canvas": "{color.sand.50}", "ink": "{color.moss.950}", "inkMuted": "{color.moss.800}",
               "accent": "{color.clay.700}", "onAccent": "{color.sand.50}", "surface": "{color.sand.100}" },
    "fonts": { "display": "{font.display}", "text": "{font.text}" }
  },
  "context": { "facts": [{"text": "...", "source": "README.md"}], "preferences": [{"text": "...", "by": "...", "evidence": "..."}],
               "inferences": [{"text": "...", "basis": "..."}], "openQuestions": ["..."] },
  "mood": { "keywords": ["field notebook"], "axes": { "calm-energetic": -0.6, "warm-cool": -0.7 } },  // -1..1, see mood-levers
  "references": [{"what": "...", "why": "..."}], "antiReferences": [{"what": "...", "why": "..."}],
  "keep": ["the existing green (owner, 2026-10-02)"],
  "motif": { "idea": "pressed-leaf silhouettes", "asset": "brand/motif.svg" },
  "families": { "store": {"requested": true, "brief": "...", "selected": "brand/concepts/store/<run>/<id>.json"},
                "marketing": {"requested": true}, "icon": {"requested": false}, "illustration": {"requested": false} },
  "exceptions": [{"id": "dark-launch", "text": "..."}]
}
```
- Token-valued fields are token references (`{group.token}`); `{roles.x}` and `{fonts.x}` are shortcuts through this file. Everything else is a typed literal.
- `selected` is written by `direction.py approve --gate concept` and is not part of the direction's hash: choosing a concept does not change the direction.
- `brand/DIRECTION.md` is generated from this file (`direction.py summary`) and is never edited by hand.

## Font records (in the token file)
`type_scale.py font` writes a `fontFamily` token with `$extensions["org.quantqbit.font"]`:
`{source: "local", files: [{path, sha256, weight | [min, max], style}], license, licenseEvidence, scripts}` or `{source: "system", availability, provenance}`. Renders use local files only (no network). A changed file breaks the record until it is re-recorded, which in turn makes approvals that resolved it stale.

## Concepts: `brand/concepts/<family>/<run>/<id>.json`
`{schemaVersion, family, id, run, author, name, idea, levers[], risks[], spec, preview}` where `preview` is `{path, sha256}` or `{unavailable: "<why>"}`. `direction.py concept new` makes a valid skeleton. The `spec` per family:

| Family | spec keys |
|---|---|
| store | `backgrounds` {name: {recipe solid\|linear, color \| stops, angle, space oklab\|srgb, panel, text {head, sub, accent, onAccent}}}, `caption` {head, sub, kicker?: {font, weight, italic, tracking, lineHeight, case}, align start\|center, accent color\|underline\|highlight\|none, headScale, subRatio}, `device` {style frame\|frameless, bezel, radius, shadow none\|soft\|long\|crisp}, `layouts` [caption-top, caption-bottom, split-left, split-right, inset], `defaultLayout`, `defaultBackground`, `featureGraphic` {layout split-device-right\|split-device-left\|centered-type, background}, `motif` {use, opacity, placement, scale}, `displayWidth` |
| marketing | `backgrounds`, `caption`, `layouts` [type-start, type-center, split-image, logo-band], `defaultLayout`, `defaultBackground`, `logo`, `motif`, `displayWidth` |
| icon | `background` {recipe, color \| stops, angle, space}, `glyphScale`, `glyphOffset` [x, y], `qualityTarget` {markContrast} |
| illustration | `style`, `palette` [refs], `lighting`, `background`, `texture`, `shot`, `storyWorld` {setting, era, cast, register}, `negatives`, `ratio` |

`displayWidth` is the narrowest width, in CSS px, at which the asset is viewed (store frames default 320, marketing 500). Text sizes are judged at that width for WCAG large-text rules.

## `brand/approvals.json`
Records written only by `direction.py approve`: `{id, gate direction|concept|exception, family?, subject, scope?, hash, inputs, by, evidence, at, recordedBy}`. `hash` is the approved content; `inputs` the resolved values it depended on. `direction.py status` recomputes both and reports each record as approved, stale (and what changed) or missing.

## Run manifests: `brand/runs/<family>/<run>.json`
One immutable file per production run: tool, times, engine and browser, input hashes (config, direction, concept, slot assets with licences), approvals in force, fonts with hashes, every output with its sha256 and size, each check as PASS / FAIL / SKIPPED / REVIEW REQUIRED, and a status (`complete`, `review-required`, `failed`). Commit them: they are the audit record. Images and build folders stay out of git.
