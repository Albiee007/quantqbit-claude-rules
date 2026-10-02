# Harness media library

Shared code for the media skills: colour maths, design tokens, type scales, schemas, creative
direction and approvals, contrast findings, browser rendering and the art-direction runtime.
It ships with the web and mobile profiles to `.claude/harness/lib/` and is managed by the harness,
so edit nothing here; projects change behaviour through `brand/` files instead.

## Interface

| Module | What it provides |
|---|---|
| `harnesslib.color` | sRGB transfer, OKLab/OKLCH, CSS Color 4 gamut mapping, WCAG luminance and full-precision contrast, compositing, gradient sampling, `display_ratio()` (truncates) |
| `harnesslib.dtcg` | DTCG 2025.10 subset: load, resolve aliases, validate types, non-destructive merge, atomic write with a `.bak` recovery copy |
| `harnesslib.typescale` | modular scales, rem and `clamp()` (with a rem term), sp/pt/RN adapters, raster media sizes |
| `harnesslib.schema` + `schemas/` | strict JSON Schema subset; direction, concept, approvals, canvas, kit and run-manifest schemas |
| `harnesslib.fsutil` | strict JSON (no duplicate keys, no NaN), safe relative paths, atomic writes, locks, staged publishing |
| `harnesslib.direction` | `brand/direction.json`, concepts, hashes, approval records, gates, family resolution, run manifests |
| `harnesslib.contrast` | contrast findings: computed PASS/FAIL, sampled FAIL/REVIEW REQUIRED |
| `harnesslib.fingerprint` | signals that an asset repeats the 1.6 defaults (diagnostic, never a gate) |
| `harnesslib.browser` | headless Chrome/Edge: locate, version, bounded screenshot and DOM dump |
| `harnesslib.imaging` | Pillow only: backdrop sampling, similarity diagnostics, sheets |
| `media/artdir.js` | browser runtime shared by the store frame and the marketing canvas |
| `media/canvas.html` | the marketing canvas page (social, Open Graph, email header, banners) |

Everything is stdlib Python 3.9+ except `harnesslib.imaging` (Pillow) and rendering (a browser).
A command that needs a missing dependency exits 2 and names it.

## Importing it

A skill script imports the library with exactly this bootstrap and nothing else (a test checks
every consumer):

```python
# harness lib bootstrap (see .claude/harness/lib/README.md)
sys.dont_write_bytecode = True
_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(d) for d in (_root / "harness" / "lib", _root / "lib") if (d / "harnesslib").is_dir()][:1]
```

It finds `.claude/harness/lib` in an installed project (`.claude/skills/<skill>/scripts/x.py`)
and `harness/lib` in the harness source.

## Exit codes (every media command)

| Code | Meaning |
|---|---|
| 0 | Completed. The report may still say REVIEW REQUIRED or SKIPPED for individual checks |
| 1 | Validation failed, or a production gate is not met |
| 2 | Invalid invocation, missing dependency, or an operational failure (lock held, browser failed) |

## Result labels

PASS and FAIL are numerical results of a check that ran. SKIPPED means it did not run, and why.
REVIEW REQUIRED means only an estimate exists (for example, contrast sampled from rendered pixels)
and a person must confirm it. A run with a FAIL is not published; a run with REVIEW REQUIRED is
published and says so, and its manifest status is `review-required`.
