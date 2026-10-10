# Harness media library

Shared code for the media skills: colour maths, design tokens, type scales, schemas, creative
direction and approvals, contrast findings, browser rendering, the art-direction runtime and the
video renderer's parts (DevTools session, seek runtime, ffmpeg).
It ships with the web and mobile profiles to `.claude/harness/lib/` and is managed by the harness,
so edit nothing here; projects change behaviour through `brand/` files instead.

## Interface

| Module | What it provides |
|---|---|
| `harnesslib.color` | sRGB transfer, OKLab/OKLCH, CSS Color 4 gamut mapping, WCAG luminance and full-precision contrast, compositing, gradient sampling, `display_ratio()` (truncates) |
| `harnesslib.dtcg` | DTCG 2025.10 subset (including `duration` and `cubicBezier` for motion): load, resolve aliases, validate types, non-destructive merge, atomic write with a `.bak` recovery copy |
| `harnesslib.typescale` | modular scales, rem and `clamp()` (with a rem term), sp/pt/RN adapters, raster media sizes |
| `harnesslib.schema` + `schemas/` | strict JSON Schema subset; direction, concept, approvals, canvas, kit, video and run-manifest schemas |
| `harnesslib.fsutil` | strict JSON (no duplicate keys, no NaN), safe relative paths, atomic writes, locks, staged publishing |
| `harnesslib.direction` | `brand/direction.json`, concepts, scoped hashes (version 2, with the 1.7 adapter), approval records, gates, family resolution, run manifests |
| `harnesslib.contrast` | contrast findings: computed PASS/FAIL, sampled FAIL/REVIEW REQUIRED |
| `harnesslib.fingerprint` | signals that an asset repeats the 1.6 defaults (diagnostic, never a gate) |
| `harnesslib.browser` | headless Chrome/Edge: locate, version, bounded screenshot and DOM dump |
| `harnesslib.cdp` | a persistent headless browser over the DevTools protocol (stdlib WebSocket): init scripts, blocked network, evaluate, screenshots |
| `harnesslib.video` | video pieces: whole-frame plan, storyboard and review approvals, voice-over script, voice prompt, planned captions, composition build |
| `harnesslib.ffmpeg` | ffmpeg/ffprobe: locate (with install advice), output profiles, encoder, probe and profile checks |
| `harnesslib.framecheck` | signals from decoded frames (flashing heuristic) and pixel hashes |
| `harnesslib.imaging` | Pillow only: backdrop sampling, similarity diagnostics, sheets |
| `media/artdir.js` | browser runtime shared by the store frame and the marketing canvas |
| `media/canvas.html` | the marketing canvas page (social, Open Graph, email header, banners) |
| `media/timeline.js` | the seek runtime (`window.__hf.seek`, HyperFrames protocol) injected into video compositions |
| `media/motion.js`, `media/video.html` | video scene templates and transitions (paused Web Animations), the composition page |

Everything is stdlib Python 3.9+ except `harnesslib.imaging` (Pillow), rendering (a browser) and
video encoding (ffmpeg, found on PATH, never bundled).
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
