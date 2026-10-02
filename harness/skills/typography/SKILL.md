---
name: typography
description: Mandatory, context-aware typography companion to ui-ux for every UI change. Discovers the project's audience, brand, content density, platforms, supported languages and existing fonts and type tokens before deciding anything, then extends what exists instead of imposing a generic scale. Covers hierarchy, measure and line height, font selection and pairing, font metrics, variable fonts and OpenType features, multilingual and RTL text, web and native font loading performance, font licensing, and platform text scaling (browser zoom, Dynamic Type, Android font scale). Use when creating or changing any UI, choosing or loading fonts, defining or editing type tokens, picking a brand typeface or wordmark font, localizing UI into new scripts, or reviewing text rendering, truncation or layout shift.
---

# Typography

**Mandatory** with `ui-ux` for every change that touches text in a user interface: web, React Native, Android (Compose or XML), Apple platforms. Decide from project evidence, not from a universal recipe. Meet every required check, or report it as unverified.

## Precedence
1. **Accessibility minimums from `ui-ux` are never overridable** (text scaling to 200%, reflow, text spacing, contrast, platform minimum sizes). No brand rule, design file or token lowers them.
2. **Project type tokens and existing design documentation** are the source of truth: token files, theme objects, the design-system doc, brand guidelines, ADRs.
3. **Platform system:** Material 3 type scale on Android and Material web, Apple text styles with Dynamic Type on Apple platforms, browser defaults and `rem` on the web.
4. **This skill's defaults and heuristics,** used only to fill gaps the layers above leave open.

**Never create a parallel token set.** Extend or update the existing tokens. If two competing type systems already exist, flag it and converge on one in the same change or a follow-up; don't add a third.

**Existing `px` type tokens (web):** flag as debt and record it in the decision record. Migrate to `rem` only with the owner's agreement, preserving visual values at the default 16px (`14px` → `0.875rem`). New tokens use `rem`. React Native numeric font sizes are unitless dp already scaled by the user font scale: not debt.

## Workflow
1. **Discover context.** Gather evidence on audience, reading context, density, brand voice, platforms, languages and scripts, and constraints ([context-discovery](references/context-discovery.md)). Read before you decide.
2. **Inventory.** List the fonts in use and where they load, every type token and its consumers, the families and weights actually shipped, and 3–5 representative screens (densest, most editorial, most localized, smallest viewport). Note hard-coded sizes as debt.
   - **Greenfield (no type tokens exist):** create a minimal set (body, secondary, caption, 2–3 heading levels, line heights, families) via `ui-ux`'s [design-tokens-dtcg](../ui-ux/references/design-tokens-dtcg.md) reference and record it as the initial decision (step 6).
3. **Decide only what's missing,** adapting to the evidence. There is no universal scale, ratio, family count or body size. Write down the inputs each decision used ([hierarchy-and-measure](references/hierarchy-and-measure.md), [font-metrics-and-pairing](references/font-metrics-and-pairing.md)).
4. **Implement via tokens per platform:** CSS custom properties or the Tailwind theme in `rem`, DTCG tokens, Compose `Typography` in `sp`, Apple text styles or `relativeTo:` scaling, a shared React Native text component ([platforms](references/platforms.md)). Load fonts deliberately ([loading-and-licensing](references/loading-and-licensing.md)).
5. **Verify** every required check below on the representative screens and every supported script ([accessibility-checks](references/accessibility-checks.md), [multilingual-and-rtl](references/multilingual-and-rtl.md)).
6. **Record** significant decisions (new family, scale change, new script, licence) as a short decision record in the existing design docs: the design-system doc, tokens README, ADR folder or `brand/README.md`. Don't start a new doc tree when one exists; create a single file only when nothing exists.

## Tools
`python .claude/skills/typography/scripts/type_scale.py` (stdlib; DTCG 2025.10 is the interchange, platform forms go in `$extensions["org.quantqbit.platform"]`):
- `scale --base 16 --ratio 1.2 --steps caption,body,h3,h2,h1 --body body [--platform web,android,ios,rn] [--fluid 360:1440 --max-ratio 1.25]`: a scale with rem / `clamp()` (with a rem term) / sp / pt / React Native values. The ratio is your stated heuristic.
- `media --canvas-width 1080 --display-width 320 --min headline=22,sub=14`: canvas px for raster media (store frames, social images) that keep a minimum size at the smallest display.
- `font --name display --family X --source local --file path:700 --license ... --license-evidence ...` (or `--source system --availability ...`): the font record the media renderers read (files with sha256, weights, scripts, licence evidence).
- `check --tokens <file>`: every font record (files present and unchanged, licence evidence).
With `--out <tokens file>` they merge into the existing file without overwriting (a conflict writes nothing; `--replace` names a change; the old file is kept as `.bak`).

## Decision rules
- **Hierarchy uses size, weight, space and color together.** Size alone produces a scale with too many steps. Add a level only when content has a real level for it.
- **Scale ratio follows density and viewport range.** Dense dashboards and data tools need tight ratios and few levels; editorial and marketing pages can use wider ratios and larger display sizes. Fluid ranges for wide viewport spans. A modular scale is one option, not a mandate.
- **Measure:** prose around 45–75 characters per line as a heuristic; WCAG 1.4.8 (AAA) caps at 80, or 40 for CJK. UI labels and tables are not prose.
- **Line height depends on x-height, measure and script:** taller x-height and longer lines need more; headings need less; scripts with tall stacks or marks (Devanagari, Thai, Arabic) often need more. Unitless in CSS.
- **Families: minimal by default, justified by evidence.** Each extra family or weight must solve a named need (brand voice, data legibility, code, script coverage) and pay its loading cost. One family with good weights and widths often beats two.
- **Prefer system or platform fonts** when brand evidence doesn't demand a custom face: zero download, native rendering, built-in Dynamic Type and script coverage.
- **Data:** tabular lining numerals for columns, prices, timers and anything that updates in place; slashed zero where 0/O confusion matters (codes, IDs).
- **Script coverage first:** a font is only eligible if it, or a tested fallback, covers every supported language's characters and shaping.
- **Fallback stacks are metric-matched** (x-height and width) to keep the swap invisible and layout stable.
- **Avoid thin weights for body and UI text;** check weights at the smallest size they'll render.

## Required checks
- [ ] Text scales to **200%** on web (browser zoom and text-only zoom), at the **largest Dynamic Type size** including accessibility sizes on Apple, and at **Android font scale 200%**, with no clipping, overlap or truncation of essential content.
- [ ] WCAG **1.4.4** Resize Text, **1.4.10** Reflow (320 CSS px), **1.4.12** Text Spacing overrides all pass.
- [ ] No `px` font sizes or viewport-only (`vw`) sizes on web text; `clamp()` includes a `rem` term. Zoom is never disabled.
- [ ] Every supported language renders with the intended font or a tested fallback: no tofu, correct shaping, correct regional glyphs. Language tagged: web `lang` on root and inline changes; Android locale spans (`LocaleSpan`, Compose `LocaleList`/`textLocale`); iOS per-locale text (attributed-string language attribute, `accessibilityLanguage`); React Native: `accessibilityLanguage` (iOS) for pronunciation; check CJK regional glyphs on device (native API names not verified this pass).
- [ ] Layout shift from font swap is minimized: metric-matched fallback or overrides, only critical faces preloaded, `font-display` chosen deliberately.
- [ ] Licence permits the actual use: web embedding, app bundling, logo or wordmark, subsetting or modification. Licence recorded in the docs.
- [ ] RTL locales: direction set in markup, logical properties, mirrored directional icons, isolated user content, numbers checked.
- [ ] Numerals: tabular where values align or update; lining vs oldstyle chosen per context.
- [ ] Contrast for text is verified per `color-science` and `ui-ux`; this skill does not restate contrast thresholds.

## Reporting
- List each required check as passed, failed (with fix) or **not verified** with the reason: no device or simulator, no RTL locale configured, licence text unavailable, font files not in repo, CJK font not installed locally.
- Name the decisions taken and where they were recorded. Name any heuristic used as a heuristic.

## References
- [context-discovery](references/context-discovery.md): evidence checklist, token files to grep, resolving conflicting evidence, decision record format. Load when starting any type decision or inheriting an unfamiliar project.
- [hierarchy-and-measure](references/hierarchy-and-measure.md): deriving a scale, ratio heuristics, measure, line height, spacing, fluid type, container queries, M3 and Apple mappings. Load when adding or changing sizes, levels or text layout.
- [font-metrics-and-pairing](references/font-metrics-and-pairing.md): vertical metrics, x-height, pairing, variable fonts and axes, optical sizing, numerals, OpenType features. Load when choosing, pairing or configuring a typeface.
- [multilingual-and-rtl](references/multilingual-and-rtl.md): shaping, complex scripts, CJK, line breaking, bidi, `lang`, fallback coverage, text expansion, pseudo-localization. Load when supporting a new language or script, or any RTL locale.
- [loading-and-licensing](references/loading-and-licensing.md): `font-display`, preload, WOFF2, subsetting, metric overrides, native bundling, licence review. Load when adding, loading or licensing a font.
- [platforms](references/platforms.md): web, React Native, Android and Apple implementation details for scalable type. Load when implementing type tokens on a specific platform.
- [accessibility-checks](references/accessibility-checks.md): per-platform test procedures, truncation policy, dyslexia claims, reporting gaps. Load when verifying or reviewing text.
- [sources](references/sources.md): dated source index with access status. Load when citing or checking a rule's basis.
- Related: `ui-ux` (minimums, tokens, [material3](../ui-ux/references/material3.md), [apple-hig](../ui-ux/references/apple-hig.md)), [color-science](../color-science/SKILL.md) (text contrast), `brand-assets` (brand typeface and wordmark).
