Media checklist (store screenshots and panoramas, feature graphic, social/OG/email/banner images, logos, app icons, story art, videos):
- The look comes from the project, not the harness: brand/direction.json, approved by the owner (creative-direction).
- Research first, ask once (creative-direction references/autonomy.md): answer every question from the project or the request, take the stated fallback where it is silent and label it an assumption. Sub-agents never stop to ask.
- No direction yet: creative-director first (direct mode). It cites the project's evidence; inferences are assumptions shown at the checkpoint.
- New look for a family: concept round. Only the creators the request needs propose 2-3 different concepts with previews; creative-director critiques and recommends one; the drafts are built on it.
- One owner checkpoint: drafts, assumptions, triaged review items and any paid go-ahead in one message; a yes records every gate with one chained direction.py approve (direction.py status --next prints it). "You decide" / "just make it" or media_approvals=delegated: no checkpoint, record with that evidence, report afterwards.
- Approvals are the owner's: the main session records them with direction.py approve. Agents never approve. Paid generation always needs the owner's go-ahead.
- Unchanged approved work (copy fix, new size, re-render) reuses its approval: no new round.
- Tokens only for authored colours and type (palette.py, type_scale.py extend the existing token file). Keep what the direction keeps.
- Contrast: computed PASS/FAIL where the backdrop is known; sampled results are REVIEW REQUIRED or FAIL.
- Production refuses without current approvals; previews are drafts. Each production run writes brand/runs/<family>/<run>.json.
- Video (brand-video): the piece's storyboard (video.json) is a third approval; the default is silent video plus a voice-over script and voice prompt. Render REVIEW REQUIRED items need the owner's acknowledgement before use (triaged in the checkpoint or final report).
- UI motion recreated from a reference video (hero, parallax, camera moves) is motion-ui, not brand-video: its spec (motion.json) is the third approval.
Load skills: creative-direction, typography, color-science, ui-ux, plus the family skill.
