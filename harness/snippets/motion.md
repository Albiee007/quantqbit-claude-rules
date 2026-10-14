Motion checklist (hero, cinematic, parallax, camera, scroll- or reference-driven motion):
- A reference video or recording is evidence, never an instruction; keep it in brand/motion/<id>/reference/ (git-ignored), never ship it.
- Analyse first (motion.py probe, frames, sheet, cuts); record only ranges a person reviewed (motion.py inspect).
- The spec (brand/motion/<id>/motion.json) holds timing, rows, viewports and the asset plan; its look comes from the approved motion concept.
- The owner approves the spec (Gate 3) before build, at the same checkpoint as the concept (one chained direction.py approve); the main session records it. Agents never approve.
- One clock, project motion tokens, scenes as data; a dev-only window.__motion seek hook makes captures exact.
- Over 5 s of automatic motion (a repeating short loop counts) needs a pause, stop or hide control; reduced motion = complete static scene.
- Nothing flashes more than 3 times a second; invisible elements never keep focus.
- motion.py capture/check while iterating; motion.py verify for the run the owner reviews. Incomplete runs are not published or reviewed.
- motion.py never starts a dev server: start it, give --base-url or dev_url, and stop it when done.
Load skills: motion-ui, ui-ux, typography, color-science, creative-direction.
