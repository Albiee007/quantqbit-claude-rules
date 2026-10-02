# Color Heuristics

Everything in this file is a **heuristic**: contextual, culture-dependent, and weaker evidence than colorimetry or WCAG. Label it as a heuristic wherever you use it, and defer to the project's brand guidelines and user research.

## Color psychology and emotion
- Claims like "blue builds trust", "red increases urgency", "green means calm" are popular but weakly supported as general rules.
- Elliot & Maier's 2014 Annual Review of Psychology review concludes that color can affect affect, cognition and behavior, but that the field is still at an early stage: boundary conditions, moderators and real-world generalizability need much more work before firm recommendations are justified. Earlier work had notable methodological problems.
- Effects depend on context (the same red reads as danger, appetite, celebration or brand), on the person and on the culture.
- **Use:** as a starting hypothesis for exploration, never as the rationale for a final choice or as a claim in a report ("this red converts better") without project data.

## Cultural meaning
- Meanings vary by region and context. Apple's HIG gives an example: in the Stocks app, green indicates a positive trend in English while red indicates a positive trend in Chinese.
- White, red, yellow and other colors carry different associations (mourning, luck, royalty, warning) across cultures.
- **Use:** check the product's markets; localize status and financial colors where conventions differ; never rely on color alone (WCAG 1.4.1), so localized colors stay safe.

## 60/30/10
- A composition heuristic from interior and graphic design: roughly 60% dominant (usually neutral surfaces), 30% secondary, 10% accent.
- It is a starting proportion, not a rule or a measurement target. Dense data apps, media apps and marketing pages need different balances.
- **Use:** when a screen feels noisy, check whether the accent is overused; let the project's brand system decide proportions.

## Accent scarcity
- An accent stands out only when it is rare (the Von Restorff effect in ui-ux). Reserve the strongest accent for the primary action and key states.
- Too many accented elements flatten hierarchy. Prefer emphasis through weight, size, position and contrast, then color.
- Never make the accent the only cue for the primary action (1.4.1).

## Brand recognition
- Consistent use of a few distinctive brand colors helps recognition. Consistency across touchpoints matters more than any specific hue.
- Accessibility adjustments (darker text variants, lighter dark-theme variants) keep the hue family and are documented as part of the brand system, not as deviations.
- Evidence about brand color effects is mostly from marketing literature with mixed rigor; treat specific claims as heuristics.

## Harmony schemes
- Complementary, analogous, triadic and similar "color wheel" schemes are aesthetic heuristics. Which wheel (RGB, RYB, perceptual hue) changes the result; build them in a perceptual space (OKLCH) if used, and verify contrast and CVD anyway.

## How to validate
- **User research:** preference and comprehension tests with the product's real audience and markets; include people with CVD and low vision.
- **A/B or multivariate tests:** for conversion-related color claims; pre-register the metric, run to an adequate sample, and change only color. Report effect sizes and confidence, not just "won".
- **Comprehension checks:** can users identify status, errors and selected state with color removed (grayscale screenshot) and with CVD simulation?
- **Brand review:** confirm with the brand owner that accessibility-driven variants are acceptable.
- Record each heuristic used, what would validate it, and whether it was validated, in the decision record ([context-discovery](context-discovery.md)).

## Sources
- Elliot & Maier 2014, "Color psychology: effects of perceiving color on psychological functioning in humans" (abstract via Europe PMC; full text not accessed): [Research](sources.md#research).
- Apple HIG Color (cultural meaning, Stocks example): [Platforms](sources.md#platforms).
- 60/30/10, accent scarcity, harmony schemes: design-practice heuristics; no verified source.
