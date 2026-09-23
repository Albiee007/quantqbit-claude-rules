# Image SEO

Images rank in Google Images and appear in web results, Discover, and rich results. They also dominate LCP and CLS, so image handling is both an SEO and performance concern.

## Discovery

- Use `<img src>` (or `<picture>` with an `<img>` fallback) for meaningful images. **Google doesn't index CSS background images.**
- Keep images crawlable: don't block image paths in robots.txt unless intended; CDN hosts must allow Googlebot-Image.
- Image sitemaps (or `<image:image>` entries) help discovery for JS-inserted or CDN-hosted images.
- Supported formats: BMP, GIF, JPEG, PNG, WebP, SVG, AVIF. File extension should match the real type.
- Stable URLs: re-using the same image URL across pages helps caching and indexing; changing URLs on every deploy forces re-discovery.

## Alt text

- Describe what the image shows in context, concisely; include relevant terms naturally. It's also an accessibility requirement (WCAG).
- Decorative images: `alt=""` (empty, not missing). Don't describe purely decorative flourishes.
- Don't stuff keywords or repeat the filename; avoid "image of".
- Functional images (icon buttons, linked logos) describe the action/destination ("Acme home").
- Heuristic: ~10–125 characters; complex charts need a text explanation near the image, not a 500-char alt.

Good: `alt="Technician replacing a kitchen sink cartridge valve"`. Bad: `alt="plumber plumbing plumber austin"`, `alt="IMG_2291.jpg"`.

## Filenames, context, and captions

- Descriptive, hyphenated filenames: `black-leather-chelsea-boot-side.webp`, not `DSC0001.jpg`.
- Place images near relevant text; page title, headings, and captions give Google context. Captions are read more than body copy.
- Preferred page image: `og:image` or `primaryImageOfPage` / structured data `image`. Pick a representative image, not a logo, with a reasonable aspect ratio.
- For large preview images in Search/Discover, allow `max-image-preview:large` and use images ≥1200 px wide.

## Performance markup

```html
<!-- LCP / hero: eager, high priority, responsive -->
<img src="/img/hero-1200.avif"
     srcset="/img/hero-600.avif 600w, /img/hero-1200.avif 1200w, /img/hero-2000.avif 2000w"
     sizes="100vw" width="1200" height="630"
     fetchpriority="high" alt="Dashboard showing weekly revenue by channel">

<!-- Below the fold: lazy + async decode, format fallback -->
<picture>
  <source type="image/avif" srcset="/img/team-800.avif 800w, /img/team-1600.avif 1600w" sizes="(min-width: 800px) 50vw, 100vw">
  <source type="image/webp" srcset="/img/team-800.webp 800w, /img/team-1600.webp 1600w" sizes="(min-width: 800px) 50vw, 100vw">
  <img src="/img/team-800.jpg" width="800" height="533" loading="lazy" decoding="async" alt="Support team at the Pune office">
</picture>
```

Rules:
- `width` and `height` (or CSS `aspect-ratio`) on every image → prevents CLS.
- `loading="lazy"` only below the fold; never on the LCP image. JS lazy-loaders using `data-src` hide images from non-JS crawlers — prefer native lazy loading.
- `fetchpriority="high"` on the single LCP image.
- `srcset` + accurate `sizes` so mobile doesn't download desktop assets. Always keep a fallback `src`.
- Modern formats (AVIF, WebP) with fallback; SVG for logos/icons.
- Size targets (heuristics from claude-seo): thumbnails < 50 KB, content images < 100 KB, hero < 200 KB; flag > 200 KB (content) / > 300 KB (hero), critical above ~500–700 KB.
- Serve via an image CDN or build-time pipeline (Next.js `next/image`, Nuxt Image, Astro `<Image>`, Angular `NgOptimizedImage`) that handles resizing, formats, and dimensions.
- Long cache lifetimes with hashed filenames.

## Metadata and licensing

- IPTC/XMP photo metadata (Creator, Credit Line, Copyright Notice) can be shown in Google Images; licence info via Image metadata structured data (`license`, `acquireLicensePage`). Display only — not a ranking factor. WebP carries XMP rather than IPTC.
- AI-generated product images for merchants must carry IPTC `DigitalSourceType` `TrainedAlgorithmicMedia`.
- Don't strip metadata you need for attribution; do strip GPS/EXIF privacy data from user uploads.

## Video (brief)

Put each video on its own watch page or a page where it's the main content, with `VideoObject` markup, a crawlable thumbnail, and a visible title/description; let Googlebot fetch the video file or embed.

## Audit checklist

| Check | Severity |
|---|---|
| Key content images as CSS backgrounds | Medium |
| Missing `alt` on meaningful images | Medium (High if widespread on product pages) |
| LCP image lazy-loaded or JS-inserted | High |
| No dimensions → CLS | High if CLS failing, else Medium |
| Oversized/legacy formats | Medium |
| Image paths blocked by robots.txt | High |
| Generic filenames | Low |
| Missing `og:image` | Low–Medium |

## Sources
- https://developers.google.com/search/docs/appearance/google-images
- https://developers.google.com/search/docs/fundamentals/using-gen-ai-content
- https://web.dev/articles/optimize-lcp
- https://web.dev/articles/optimize-cls
- claude-seo v1.9.9 `seo-images` skill (AgriciDaniel, MIT) — size thresholds, `<picture>` pattern
