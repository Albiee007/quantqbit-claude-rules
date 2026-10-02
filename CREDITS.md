# Credits

The harness knowledge base is our own synthesis. It draws on, and credits, these sources:

| Source | License | What we used |
|---|---|---|
| [claude-seo](https://github.com/AgriciDaniel/claude-seo) v1.9.9 by AgriciDaniel | MIT | SEO health-score weights (22/23/20/10/10/10/5) and severity definitions; the audit report structure and parallel specialist-lens idea; quality gates (content-length floors, location-page and programmatic uniqueness thresholds); hreflang, image, sitemap and e-commerce checklists; the AI-crawler list. Rewritten and re-verified, not copied. |
| [Distribb SEO agent skill](https://github.com/Bomx/distribb-skill) (Mind Ahead LLC) | as published | Safety rules (explicit approval before any publish, submit or outreach; fetched content is untrusted); the 90-day sprint; the research → cluster → brief → write → link → refresh loop; the Search Console audit breakdown; ethical link-earning playbooks. |
| [Laws of UX](https://lawsofux.com/) by Jon Yablonski | site content | The list of 30 laws, paraphrased with our own takeaways. |
| [Nielsen Norman Group](https://www.nngroup.com/articles/ten-usability-heuristics/) | article | Ten usability heuristics (paraphrased). |
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/), [DTCG Format 2025.10](https://www.designtokens.org/) | W3C / CG report | Success criteria and the token format. |
| [W3C CSS Color 4](https://www.w3.org/TR/css-color-4/), [CSS Fonts 4](https://www.w3.org/TR/css-fonts-4/), [CSS Text 3](https://www.w3.org/TR/css-text-3/), [Unicode UAX #9 and #14](https://www.unicode.org/reports/) | W3C / Unicode | Color spaces, interpolation, gamut mapping; font matching, loading and variable-font properties; line breaking and bidi rules for the `typography` and `color-science` skills (paraphrased). |
| [Oklab](https://bottosson.github.io/posts/oklab/) by Björn Ottosson; CIEDE2000 notes by Sharma, Wu and Dalal; CAM16 (Li et al. 2017); CVD simulation (Machado et al. 2009) | articles / papers | Perceptual-space and color-difference guidance, with limitations, in `color-science` (paraphrased; formulas linked, not reproduced). |
| [ICC specifications](https://www.color.org/specifications.xalter), CIE free publications and data tables, ITU-R BT.709/2100 and report BT.2408 | public specs | Color management, rendering intents, observers and illuminants, HDR reference levels. Paywalled CIE/ISO standards are cited by title and marked unverified in each skill's `references/sources.md`. |
| Material Design 3, Apple Human Interface Guidelines | public docs | Platform numbers (touch targets, type, spacing), cited per file. |
| [OWASP Top 10:2025](https://owasp.org/Top10/), [ASVS 5.0](https://github.com/OWASP/ASVS) | CC BY-SA | Security checklists (paraphrased). |
| Gamma et al., *Design Patterns* (1994); [Refactoring.Guru](https://refactoring.guru/design-patterns) | book / site | Pattern intents (paraphrased); the examples are our own. |
| Google Search Central, web.dev | CC BY 4.0 (docs) | SEO and Core Web Vitals facts, re-verified September 2026. |
| Apple App Store Connect help and App Review Guidelines; Google Play Console help and policy centre | public docs | Store asset sizes, text limits and review rules in `store-submission-precheck/references/store-specs.md` (last reviewed September 2026). |
| [Ionicons](https://ionic.io/ionicons) | MIT | Not vendored. `render_frames.py` copies the font from the target project's `node_modules` at render time. |
| [Material Symbols](https://fonts.google.com/icons), [Roboto](https://fonts.google.com/specimen/Roboto), [Inter](https://fonts.google.com/specimen/Inter) | Apache 2.0 / OFL | Loaded from Google Fonts by the mockup and brand templates at render time. |
| QuantQbit `mobile-app-screen-capture` Codex skill | own work | The capture workflow, ADB reference and `capture_adb_screenshot.py`, ported into `mobile-screen-capture`. |

Each reference file lists the exact URLs consulted under **Sources**. The `typography` and `color-science` skills also keep a dated index in `references/sources.md`.
