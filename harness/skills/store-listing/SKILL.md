---
name: store-listing
description: App-store listing copy for Google Play and the Apple App Store — title, short/full description, subtitle, promotional text, keywords, What's New and screenshot captions — written from a code-verified feature inventory and claims truth table, then checked against store limits and project guardrails by script. Use when writing or refreshing store listing text, repositioning an app, localising metadata, preparing release notes, or checking listing copy before submission.
---

# Store Listing Copy

Write copy that **ranks, converts and is true**. Every claim traces back to code; every field fits its limit; platform-gated and Premium features are marked, or left out where they don't exist.

## Workflow
1. **Brief.** Get the positioning in one sentence (who it's for, the job it does, why it's different), the target stores and locales, the brand voice, and the features to lead with. If the owner hasn't given a positioning, propose two and ask.
2. **Feature inventory and truth table.** Follow [claims-guardrails](references/claims-guardrails.md) §1–2:
   - Read the navigator, the screens, the entitlement tiers, the platform gates and the server flags.
   - Quote in-app labels exactly.
   - Record where each count applies.
   - Write down what the app does **not** do.
3. **Guardrails file.** Turn every ❌ and every "Premium only" into a `listing-guardrails.txt` rule, and save it next to the listing (§3 of the same file).
4. **Keywords.** Follow [aso-keywords](references/aso-keywords.md): seed the list, look at the competition, place terms by weight.
5. **Write** into a copy of [templates/LISTING.template.txt](templates/LISTING.template.txt) saved as `LISTING.md`. Use one `<!-- field: … | max N -->` block per field, and follow [field-limits](references/field-limits.md) for what each field is for.
   - **Lead with the differentiators.** The first two lines of the full description and the first two screenshots carry most of the conversion.
   - **Benefit first, then the mechanism:** "Changed cash before you flew? Record it once…".
   - **Plain, global English.** Short sentences. Name regional features as regional.
   - **iOS copy leaves out Android-only features.** It mentions Premium only if iOS in-app purchase ships.
   - **No prices, no superlatives, no competitor names.**
6. **Screenshot captions.** For each frame, a headline of at most 6 words and a sub-caption of at most 12 words, in the same order as the `store-mockups` storyboard. Hand them to `store-creative`, or take them from there.
7. **Check.** Run `python .claude/skills/store-listing/scripts/check_listing.py LISTING.md`, and fix everything until it passes. The checker enforces limits, iOS keyword hygiene, common banned claims, and the project guardrails.
8. **"Check before you publish."** End LISTING.md with every promise that can't be verified from the repo: server flags, IAP availability, sign-in methods in the submitted build, console forms. The `store-precheck-auditor` picks these up.

## Rules
- **Never invent a feature, number, rating or testimonial.** If the evidence column is empty, the claim goes.
- **Screenshot captions and copy use the same words** as the app's UI.
- **Name changes:** on iOS the name and subtitle go live only with a new version; on Play a title change is reviewed. Tell the owner.
- **Localisation:** translate the intent and redo keyword research for each locale. Don't machine-translate keyword fields.
- **Personal data:** keep real user names, emails and balances out of the copy and examples.

## Output
- `LISTING.md` (all fields plus captions plus "Check before you publish"), `listing-guardrails.txt`, and the checker's output pasted into your report.
- A short report: the positioning chosen, the fields and their character counts, the claims removed and why, and the open items.

## References
- [field-limits](references/field-limits.md): every field's limit, whether it's indexed, and how to write it.
- [claims-guardrails](references/claims-guardrails.md): inventory → truth table → guardrails; common traps.
- [aso-keywords](references/aso-keywords.md): the keyword method.
- [store-specs](../store-submission-precheck/references/store-specs.md): the single source of truth for store numbers.
- Checker: [check_listing.py](scripts/check_listing.py). Template: [LISTING.template.txt](templates/LISTING.template.txt).
