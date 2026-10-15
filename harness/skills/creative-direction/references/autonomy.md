# Autonomy: research first, one owner checkpoint

The owner wants output, not a questionnaire. Every media request (stills, logos, icons, store art, story art, video, motion) follows the same rhythm: **research, decide by default, draft everything, then stop once.** The owner sees finished drafts with the recommended choices already made and answers once. Approvals are still the owner's and still bound to hashes; what changes is that they are collected together instead of one gate at a time.

## The rhythm
1. **Research.** Answer every question you can from the project ([context-discovery](context-discovery.md)) and from the request. Read before you ask.
2. **Decide by default.** Where the evidence is silent, take the fallback below, label it as an assumption (`context.inferences`, or the agent's "Assumptions made" line) and keep going.
3. **Draft everything.** Direction, the creators' concepts with previews, the director's critique with **one recommended concept**, and the piece built on the recommended concept: storyboard and draft render (`render_video.py preview`), spec and draft captures (`motion.py capture --draft`), preview frames (`render_frames.py preview`), the contact sheet, the icon before/after preview. Drafts need no approval.
4. **One checkpoint** (below), unless the owner delegated.
5. **Production** with the chained approvals in place, then the family skill's own checks.
6. **Final report**: what was made, every assumption, every REVIEW REQUIRED item and what was done about it, and the options not taken (alternative concepts, paid methods).

Sub-agents never stop to ask. They return their work with "Assumptions made" and "For the checkpoint" lines; the main session gathers those into the single checkpoint.

## Answer it from the project
| Question | Where the answer comes from | When the evidence is silent |
|---|---|---|
| What must be kept | Existing tokens, fonts, logo, icon (`keep`) | Keep everything that exists |
| Audience, message, positioning | README, `CLAUDE.md`, `LISTING.md` and its claims table, store copy, `package.json`/`app.json` description | The listing's first claim; say it is assumed |
| Markets and languages | i18n folders, `app.json` locales, `Info.plist`, listing locales | The source language only |
| Video platform, length, call to action | The request, then `families.video.brief`, then the listing | 9:16, 15 s, the listing's call to action |
| Voice-over | The request, `providers.json` | Silent video plus `voice/script.md` and a voice prompt |
| Visual method (video, story art) | An existing `visual-plan.md`, masters under `brand/art/`, the generators the session or `providers.json` offers | Templates and code illustration (no paid generation) |
| Story-art placements | Site pages and components, the manifest's `art-*` entries, OG meta tags | The hero of the home page |
| Store lead features, classic or continuous | `LISTING.md`, an existing kit's `frames.json` `style` and captions | Classic, the listing's top three claims |
| Sizes and slots | `store-assets.json`, `frames.json` `sizes`, `store-slots.json`, the request | What the project declares; never a harness list |
| Replace or audit an icon | The request's wording | Audit and preview only |
| Admired products, anti-references | `references`/`antiReferences`, docs that name them | None; the direction says so and the checkpoint invites them |

Never invent a citation: an assumption is an inference with its basis, never a fact.

## What may still stop the work before drafts
Only two things, each asked once, in one message, with your proposed answer:
- a legal or regulated sensitivity with no evidence either way (people's likenesses, health or finance claims, minors);
- a destructive change the request does not cover (overwriting a shipped icon, replacing the logo).

## Paid generation
TTS voices, AI b-roll, image generators and any regeneration round beyond the first always need the owner's go-ahead, in every mode. Don't stop for it: draft the free path, and put the paid option (what, which provider, roughly how many calls) in the checkpoint. In delegated mode, produce the free path and list the paid option in the final report. A provider the project already configured (`providers.json`) still needs the go-ahead for a new run.

## The checkpoint
One message. In order:
1. **What I made**: the draft previews (paths or the images), the script, the contact sheet.
2. **Choices made for you**: the recommended concept and why (the alternatives as one-line thumbnails), and every assumption, each with its basis.
3. **Checked, and what needs your eye**: REVIEW REQUIRED items triaged. What you verified, and the few that genuinely need a human look.
4. **Needs a yes**: paid generation, a second regeneration round, a destructive change. Only if any.
5. **What a "yes" records**: the chained command from `direction.py status --next`.

A "yes" records every gate in one chained command (all or nothing) and goes to production:
`direction.py approve --gate direction,concept,storyboard,mix --family video --concept <file> --piece <id> --by <owner> --evidence "<where they said it>"`

A correction ("use concept B", "shorter", "change the CTA") is applied, and the revised drafts come back in **one** re-check, not another round of questions. A review acknowledgement after production (`--gate review --run <run> --items ...`) can ride the same reply when the owner has seen the items.

## Delegated mode
The owner delegated when:
- the request says so ("you decide", "just make it", "no questions", "use your judgement"); or
- `.agents/harness.config` sets `media_approvals=delegated` (`direction.py status` shows the mode).

Then the main session records the chained approvals itself, with the evidence quoting the request (`"chat 2026-10-14: 'just make it, you decide'"`) or `"harness.config media_approvals=delegated"`. It goes straight to production and acknowledges review items it has looked at, naming them in the final report. Delegation never covers paid generation, a destructive change, publishing or uploading. Agents still never run `direction.py approve`; delegation is the owner's word, recorded by the main session.

## Reuse
A current approval skips its gate in every mode: a copy fix, a new size or a re-render needs no checkpoint at all, only the final report.
