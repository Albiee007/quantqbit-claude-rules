# Audio and voice

## Silent by default

Videos render **silent** unless the piece has an `audio` section. Every run (and `voice`, `preview`) writes these from `video.json` and the video concept:

| File | Contents |
|---|---|
| `voice/script.md` | each scene's time, on-screen text, voice-over line, word count, and whether the line fits its scene |
| `voice/voice-prompt.md` | casting, register, accent, language, pace in words a minute, mood, music reference, pronunciations, and each line with its timing and recording notes |
| `voice/cues.json` | the voice-over windows and subtitle cues, with their timing (`planned` or `segment-aligned`) |
| `voice/captions.planned.srt`, `.vtt` | sidecar captions estimated from the script (no recorded takes) |
| `voice/captions.srt`, `.vtt` | sidecar captions following the recorded takes (every line has a take) |

- The voice prompt works with any voice tool or a voice actor. The owner chooses the tool; agents never call a paid or external voice service.
- Edit the lines in `video.json` (`scenes[].vo`, `voice`). The files are generated, so edits there are lost on the next run.

## Mixing recorded voice and music

```json
"audio": {
  "voice": true,
  "music": { "file": "brand/video/<id>/media/music.m4a", "license": "Track, library, licence id", "gainDb": -18, "duck": true },
  "loudness": "web"
}
```

- **Voice takes:** with `voice: true`, every scene with a `vo` line needs one take, `brand/video/<id>/media/vo/<scene>.wav` (or `.flac`, `.m4a`, `.aac`, `.mp3`, `.ogg`). A missing take fails production; a draft mixes the takes that exist.
- **Where a take goes:** ffmpeg's silence detection finds where the speech starts and ends in each take, so the room tone before and after is not counted. The speech is placed where the line starts (once its scene has arrived, never over the previous line).
- **Music** needs `license`. It is looped or cut to the video's length, faded out over the last second, set to `gainDb` (default −18 dB) and, with `duck` (the default), lowered while someone speaks.
- **Loudness:** the mix is normalised in two passes (EBU R128 `loudnorm`, linear) to `web` −16 LUFS (default) or `broadcast` −23 LUFS, with true peak at most −2 dBTP, leaving headroom for the AAC encode. The render then measures the file (`ebur128`) and reports `audio:<format>`: PASS within 1 LU of the target with true peak at most −1 dBTP.
- **The track:** AAC stereo, 48 kHz (192 kb/s; 256 kb/s for App Store previews), muxed into each format's video. App Store previews always get a track: silent when the piece has no audio.
- Transparent overlays carry no sound; the editor mixes it.

## The mix approval

- The storyboard approval never covers audio. A piece with audio also needs the owner to have listened: `direction.py approve --gate mix --piece <id>` (main session only, after the storyboard).
- The record binds to the audio settings and the bytes of every take and the music, and to the piece's script and timing.
  - A new take, music file or setting makes only the mix stale.
  - A new voice-over line makes the storyboard and the mix stale. So does anything that moves a take: a scene's timing, or a concept whose transitions are longer or shorter.
  - A changed picture or on-screen copy leaves the mix current.
- `render` refuses without a current mix approval, and copies the takes and music into the build, checked against the approved bytes, before it mixes.

## Planned and synchronised captions

- **Planned:** without takes.
  - Each line starts once its scene has arrived and never over the previous line.
  - It lasts `words / voWpm × 60` seconds.
  - Lines split at the subtitle width (default 32 characters, two lines a cue).
  - These are estimates. Planned cues say so in the VTT header, in `cues.json` and in the run manifest (`piece.captions: "planned"`).
- **Segment-aligned:** with takes. Each line spans its take's measured speech, and its cues are spread over that span: right per line, approximate inside a line. The VTT note, `cues.json` and the manifest say `segment-aligned`. A draft with takes for some lines only says `mixed`.
- **Word-aligned:** with an alignment of each take (`render_video.py generate --what align`, the project's own aligner; see [providers](providers.md)). Each caption starts at its first word and ends at its last. Sidecars `voice/captions.srt|vtt`, labelled `word-aligned`.
- Don't burn planned captions into a video that has a real voice-over: their timing is a guess.

## Recording specs

- **Files:** one take per scene, named after the scene id.
- **Format:** 48 kHz WAV, mono, peaks below −1 dBFS, half a second of room tone before and after.
- **Where:** `brand/video/<id>/media/vo/`. Media files are project-owned; consider Git LFS. They never go into `.claude/`.
- **Licence:** music needs `license`; a voice that isn't the owner's or the team's needs the same kind of evidence, kept with the project's records.

## Generated voice

- A take can come from the project's own TTS command (`render_video.py generate --what tts`, run by the main session when the owner asks; see [providers](providers.md)). It is mixed, approved and checked like a recorded take.
- Generated takes are an AI-disclosure review item on every render that uses them.
