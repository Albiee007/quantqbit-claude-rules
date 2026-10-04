# Formats and output profiles

## Formats in this release

| Format | Size | Length | Safe insets (standard / strict) | Profile |
|---|---|---|---|---|
| `social-9x16` | 1080 × 1920 | 3–90 s | top 220 / 260, right 120 / 140, bottom 400 / 480, left 90 / 120 px | `h264-web` |

- **Safe insets** keep text clear of the platforms' own buttons, captions and progress bars. They are a heuristic shared by Reels, Shorts and TikTok, measured from their 2026 UI. Platforms change their UI, so the check is a signal.
- The concept chooses `safeAreas: standard | strict`.
- The templates place text inside the insets. Text found outside them is a REVIEW REQUIRED item (kind `suitability`), not a failure: the video is still technically valid.
- Fps: 24, 25, 30 or 60, per piece. 30 suits social.

## Output profiles

A profile says how to encode **and** what the file must look like, so the checks match what was asked for.

| Profile | Encoding | Checked |
|---|---|---|
| `h264-web` | libx264 High, CRF 18, preset medium, yuv420p, explicit BT.709 matrix and tags, `+faststart` | codec h264, profile High, yuv420p, BT.709 colour space, primaries and transfer, moov before mdat, exact size, fps and frame count |
| `h264-draft` | the same at CRF 26, veryfast, half size, 15 fps | previews only |

- **Colour matrix.** Frames come from the browser as sRGB. Without an explicit matrix, ffmpeg converts with BT.601 and leaves the colour tags empty; colours shift slightly and players guess. `h264-web` sets BT.709 limited range explicitly.
- **Frame source.** Frames go into the encoder as JPEG at quality 92: indistinguishable from PNG after H.264, and faster. The still frames used for the checks and the sheet are PNG.

## Technical validity and platform suitability

They are reported separately:
- **technical** is PASS or FAIL against the profile;
- **suitability** for a platform is a REVIEW REQUIRED signal (safe areas today).

An owner can accept a suitability item for a use the heuristic doesn't know about.
