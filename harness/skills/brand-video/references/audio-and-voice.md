# Audio and voice

## What this release does

- Videos render **silent** by default. Every run (and `voice`, `preview`) writes these from `video.json` and the video concept:

| File | Contents |
|---|---|
| `voice/script.md` | each scene's time, on-screen text, voice-over line, word count, and whether the line fits its scene |
| `voice/voice-prompt.md` | casting, register, accent, language, pace in words a minute, mood, music reference, pronunciations, and each line with its planned timing and recording notes |
| `voice/cues.json` | the planned voice-over windows and subtitle cues (`"timing": "planned"`) |
| `voice/captions.planned.srt`, `.vtt` | sidecar captions from the same cues |

- The voice prompt works with any voice tool or a voice actor. The owner chooses the tool; agents never call a paid or external voice service.
- Edit the lines in `video.json` (`scenes[].vo`, `voice`). The files are generated, so edits there are lost on the next run.

## Planned and synchronised captions

- **Planned:** the default, and the only kind in this release.
  - Each line starts once its scene has arrived and never over the previous line.
  - It lasts `words / voWpm × 60` seconds.
  - Lines split at the subtitle width (default 32 characters, two lines a cue).
  - These are estimates. Planned cues say so in the VTT header, in `cues.json` and in the run manifest (`piece.captions: "planned"`).
- **Segment-aligned:** re-timed to the measured length of each recorded line, once recordings are supplied. Planned for a later release.
- **Word-aligned:** needs speech alignment, an opt-in provider. Planned for a later release.
- Don't burn planned captions into a video that has a real voice-over: their timing is a guess.

## Recording specs (for when the recording comes back)

- **Files:** one file per scene, named after the scene id, or one file for the whole piece.
- **Format:** 48 kHz WAV, mono, peaks below −1 dBFS, half a second of room tone before and after.
- **Where:** `brand/video/<id>/media/vo/`. Media files are project-owned; consider Git LFS. They never go into `.claude/`.
- **Licence:** music and voice need licence evidence, recorded like a font's.

## Planned (not in this release)

These are planned for later releases:
- mixing a supplied voice-over and music, with the music ducked under the voice;
- two-pass loudness normalisation: −14 LUFS for social, −16 for podcast-style platforms, true peak at most −1 dBTP;
- TTS through an opt-in provider, with a casting sample the owner approves first;
- AI-generated b-roll under the HTML overlays.

Until then, a video that needs sound is finished in an editor from the silent master, the script and the captions.
