# Image providers

The skill doesn't depend on one generator. Every provider has to cover the same four steps: **generate → get a media or job ID → get the native-resolution file → export a PNG**. Tool names and limits below were right when written, but they vary by account and change without notice. Read the tool list the session actually has, and match on the capability, not only the name.

## Detecting what's available
1. Look at the session's tools for an image-generation capability: Canva (`generate-image`), Figma Weave (`weave_*`), or a provider SDK the project already uses.
2. If you are a sub-agent and none is visible, the tools may not be granted to you. Return the storyboard and the prompts to the parent; the parent (which has the session's MCP tools) runs the generation and hands the images back for review and export.
3. If the session has no generator at all, stop and ask the parent which provider to use. Don't install SDKs or sign up for services.

## Canva MCP (default)

### Generate
1. `generate-image` with the prompt and an aspect ratio (e.g. `LANDSCAPE_4_3`). It returns a job ID.
   - **`quota_cooldown`:** roughly one generation per cooldown window. Generate one image at a time; on this error, record the scene as pending, wait, and retry later. Never retry in a tight loop.
2. Poll `get-generate-image-job` until the status is `SUCCESS`. The result is a **media ID** and a thumbnail of about 200 px. Record the media ID in the plan at once.
3. `get-assets` with the media ID gives the native size (e.g. 1456 × 1088). Its thumbnail URL is **signed**: changing the width or height parameters returns 403. It can't be used to fetch full resolution.

### Full resolution, via a scratch design
`create-design` with the images is the direct route, but it can fail with `quota_exceeded`. The fallback that works:
1. `search-designs` (owned designs) and pick any one. `copy-design` it, **one page only**. Never edit the owner's original.
2. `read-design` on the copy with `open_transaction`.
3. `edit-design`, keeping the transaction open:
   - `update_title`, e.g. "`<Product>` illustrations (export scratch)";
   - `add_page` per image, at the image's native width and height, with a dark background.
4. `read-design` with `page_indices` to get the new page IDs.
5. `edit-design`: `insert_fill` each media ID onto its page, full bleed (top 0, left 0, native width and height).
6. `edit-design` finalize, committing the transaction. Commit **only** this scratch copy. Tell the owner it exists and can be deleted.
7. `export-design` as PNG, `export_quality: "pro"`, with the page list.
8. **Download the signed export URLs immediately;** they expire. Save them as `<scene>.png` in the source folder.

### Replacing one image after review
Open a transaction on the scratch design, `update_fill` the page's image element (its locator from `read-design`) with the new media ID, commit, and export just that page.

## Figma Weave (outline)
- Use the session's `weave_*` tools to generate, then place the result in a scratch Figma file and export the frame as PNG at 1×–2× of the native size.
- Same rules: a scratch file only, never the owner's design files; record the node or asset ID as the media ID.
- Load the Figma plugin's skills before calling its write tools, if the session provides them.

## API-key providers (outline)
- Only when the project already uses the provider, or the owner names one.
- Read the key from the environment (e.g. `IMAGE_API_KEY`). Never write it to a file, the plan, a log or a command line that gets echoed. Never touch `.env` files.
- Request the largest native size the provider offers at the placement's aspect ratio; record the provider's request or image ID as the media ID.
- Check the provider's terms for commercial use, and note them in the plan.

## Whatever the provider
- One image at a time; 4–8 per set; ask before more than one regeneration round.
- Nothing is published, shared or uploaded outside the generator without the owner's approval.
- Every image's provider, media ID, prompt and date go in the plan's provenance table.
