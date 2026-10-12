# Formats and output profiles

## Formats in this release

| Format | Size | Length | Safe insets, standard (strict) | Use |
|---|---|---|---|---|
| `social-9x16` | 1080 × 1920 | 3–90 s | top 220 (260), right 120 (140), bottom 400 (480), left 90 (120) px | Reels, Shorts, TikTok, Stories |
| `social-4x5` | 1080 × 1350 | 3–60 s | top 80 (110), right 80 (100), bottom 140 (190), left 80 (100) px | portrait feed posts (Instagram, Facebook, LinkedIn) |
| `social-1x1` | 1080 × 1080 | 3–60 s | top 80 (100), right 80 (100), bottom 120 (160), left 80 (100) px | square feed posts |
| `wide-16x9` | 1920 × 1080 | 3–600 s | top 96 (108), right 160 (192), bottom 150 (200), left 160 (192) px | YouTube, the web, presentations |
| `og-card` | 1200 × 630 | 1–15 s | top 48 (64), right 64 (80), bottom 48 (64), left 64 (80) px | animated link cards, email and chat loops |
| `app-preview-iphone` | 886 × 1920 | 15–30 s | top 120 (160), right 60 (80), bottom 160 (220), left 60 (80) px | App Store preview, iPhone 6.9" and 6.5" |
| `app-preview-ipad` | 1200 × 1600 | 15–30 s | top 100 (130), right 80 (100), bottom 140 (180), left 80 (100) px | App Store preview, iPad 13" |

- The social, wide and link-card formats are encoded with `h264-web`; the App Store preview formats with `app-preview`; a transparent piece with an alpha profile. A piece lists its formats; they all share one timeline.
- **Safe insets** keep text clear of the platforms' own buttons, captions and progress bars. They are heuristics measured from the platforms' 2026 UI. Platforms change their UI, so the check is a signal.
- The concept chooses `safeAreas: standard | strict`.
- The templates place text inside the insets. Text found outside them is a REVIEW REQUIRED item (kind `suitability`), not a failure: the video is still technically valid.
- **Per-format changes.** A scene's `byFormat` entry changes its `layout`, replaces `copy` fields or `hide`s some (`kicker`, `head`, `sub`, `points`, `label`, `url`) for one format: shorter copy for a square post, a lower layout for a link card. Timing never changes per format.
- **Type size** follows the format's short side, so the same piece reads alike in every format. `og-card` sets its type 1.3 times larger, because a link card is seen small.
- Fps: 24, 25, 30 or 60, per piece. 30 suits social.

## A format of the piece's own

When a platform wants a size the table lacks, declare it in the piece. Never edit the harness, and never resize an exported file by hand.

```json
"formats": ["social-9x16", "li-card"],
"customFormats": {
  "li-card": {"size": "1200x628", "like": "og-card", "label": "LinkedIn link card"}
}
```
- **`size`:** `WxH`, both sides even (H.264 4:2:0) and 128–3840 px.
- **`like`:** names the built-in format it inherits from: length range, encoding profile, type scale and safe insets.
  - The insets are scaled to the new size: left and right by width, top and bottom by height.
  - `min`, `max`, `typeScale`, `label` and `safe` (`{"standard": {"bottom": 300}}`, in pixels at the new size, merged over the scaled insets) override what was inherited.
  - A custom id may reuse a built-in id (`og-card` at 800 × 420); `like` still reads the built-in.
- **`byFormat`:** a scene may use the custom id like any other format.
- **Approval:** a format that is neither built in nor declared is refused when the piece loads. `customFormats` is part of the storyboard's on-screen content, so changing a size or an inset needs a new storyboard approval.
- **Layouts:** they scale to any aspect, but a shape far from its `like` can crowd. Preview it and look at the sheet.

## Loops and posters

- `loop: { "outputs": ["gif", "webp"], "width": 600, "fps": 15, "maxBytes": 5000000 }` adds animated images per format, made from the format's master video. Every value is optional.
  - Pieces up to 15 s only.
  - `fps` must divide the piece's fps (30 → 15 or 10; 24 → 12 or 8).
  - `width` is never wider than the format.
  - A loop over `maxBytes` is a REVIEW REQUIRED item: email and chat apps refuse or don't animate large files.
- `kind: "loop"` marks a piece made to repeat. It gets a GIF by default, and its seam is checked: the jump from the last frame back to the first. End on the opening picture, or accept the cut.
- `poster: { "scene": "<id>" }` writes a PNG still per format: that scene's still frame, for players that show a picture before playing.
- **GIF** uses one 256-colour palette for the file, so gradients band. Prefer WebP where the platform takes it, and keep GIFs short and narrow.

## App Store previews and the Play promo

- **App Store previews** follow App Store Connect's rules (2026): H.264, 30 fps, 15 to 30 seconds, at most 500 MB, a stereo AAC track. The `app-preview` profile checks each of them; a piece without audio gets a silent track.
- **Footage:** previews should show the app itself. Build them from `recording` scenes (screen recordings made with `mobile-screen-capture`). Text overlays and a voice-over are allowed. Any scene that is not a recording becomes a `suitability:app-store:<format>` review item with the share of the preview that is recorded; the owner checks it against the App Store Review Guidelines (2.3.4).
- **Other device sizes:** declare them in `customFormats` with `"like": "app-preview-iphone"` (or `-ipad`) and the size App Store Connect asks for.
- **Google Play promo video:** Play takes a YouTube link, not a file. Render `wide-16x9` and upload it to YouTube.

## Transparent overlays

- `"transparent": true` renders without the canvas, scene backgrounds or motif: lower thirds, name titles, stingers for an editor.
- `"alpha": "webm"` (default) encodes VP9 with alpha (`yuva420p`) in WebM; `"prores"` encodes ProRes 4444 (`yuva444p10le`) in QuickTime for editing software.
- Checks: the codec, the alpha flag or pixel format, and a decoded frame that actually has transparent pixels.
- Contrast can't be measured without the footage underneath, so it is a review item. Overlays have no loops and no sound.

## Output profiles

A profile says how to encode **and** what the file must look like, so the checks match what was asked for.

| Profile | Encoding | Checked |
|---|---|---|
| `h264-web` | libx264 High, CRF 18, preset medium, yuv420p, explicit BT.709 matrix and tags, `+faststart` | codec h264, profile High, yuv420p, BT.709 colour space, primaries and transfer, moov before mdat, exact size, fps and frame count |
| `h264-draft` | the same at CRF 26, veryfast, half size (padded to even sides), 15 fps | previews only |
| `app-preview` | `h264-web` capped at 12 Mb/s, with an AAC stereo track (256 kb/s) | as `h264-web`, plus 30 fps, 15–30 s, at most 500 MB, one stereo AAC track at 44.1 or 48 kHz |
| `alpha-webm` | libvpx-vp9, `yuva420p`, CRF 24, frames in as PNG | codec vp9, `alpha_mode=1`, transparent pixels present, size, fps, frame count |
| `alpha-prores` | prores_ks 4444, `yuva444p10le`, frames in as PNG | codec prores, a `yuva444` pixel format, transparent pixels present, size, fps, frame count |
| `gif` | ffmpeg palettegen and paletteuse (sierra dither), loops forever | GIF, size, loop forever, play length, at most the master's frames |
| `webp-anim` | lossy WebP, quality 80, loops forever (Pillow) | WebP, size, loop forever, play length, at most the master's frames (identical frames may be merged) |
| `poster` | the browser's PNG of the scene's still frame | PNG, the format's size |

- **Colour matrix.** Frames come from the browser as sRGB. Without an explicit matrix, ffmpeg converts with BT.601 and leaves the colour tags empty; colours shift slightly and players guess. `h264-web` sets BT.709 limited range explicitly.
- **Frame source.** Frames go into the encoder as JPEG at quality 92: indistinguishable from PNG after H.264, and faster. The still frames used for the checks, sheets and posters are PNG.

## Technical validity and platform suitability

They are reported separately:
- **technical** is PASS or FAIL against the profile;
- **suitability** for a platform is a REVIEW REQUIRED signal (safe areas, file size, picture provenance, App Store footage, overlay contrast).

An owner can accept a suitability item for a use the heuristic doesn't know about.
