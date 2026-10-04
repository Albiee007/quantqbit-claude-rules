# Motion vocabulary

A video concept sets how the project moves: its durations, easing curves, transitions, text entrances, pace and voice. These are heuristics for the concept round. The owner's direction and the project's existing motion always win.

## From mood to motion (starting points)

| Mood axis | Toward the left | Toward the right |
|---|---|---|
| calm–energetic | longer base durations (about 450–550 ms), `fade` and `dip`, gentle `fade-up` text, 2–3 s holds | shorter durations (about 250–300 ms), `push`, `slide`, `wipe`, `mask-up` or `word-stagger`, quicker cuts |
| playful–serious | an overshooting emphasis curve, `scale-in`, `scale` transitions | standard curves only, no overshoot, `cut` and `fade` |
| minimal–rich | one transition and one text entrance for the whole piece | two or three transitions, with a reason for each |
| organic–geometric | soft fades and drifting motifs | wipes, pushes and hard cuts on the beat |

`render_video.py motion-tokens` turns calm–energetic and playful–serious into `motion.duration.{fast,base,slow}` and `motion.easing.{standard,enter,exit,emphasis}` tokens. Its easing curves follow Material 3:
- `standard` (0.2, 0, 0, 1);
- `enter` (0.05, 0.7, 0.1, 1);
- `exit` (0.3, 0, 0.8, 0.15).

Durations follow ui-ux [motion](../../ui-ux/references/motion.md), stretched for video, where nothing is waiting on a tap. Treat them as a draft: the creative-director adjusts them in the concept.

## Transitions

| Transition | What it does | Use for |
|---|---|---|
| `cut` | nothing; the next scene is just there | rhythm, energy, the first scene |
| `fade` | the incoming scene fades in over the outgoing one | calm, continuous stories |
| `dip` | out to the canvas colour, then in | a change of topic |
| `slide` | the incoming scene slides in from the right | a sequence of steps |
| `push` | the incoming scene pushes the outgoing one out | lists, "next" |
| `scale` | the incoming scene settles from 106 % with a fade | arrivals, reveals |
| `wipe` | a hard edge uncovers the incoming scene | geometric, product-led looks |

Pick two or three per concept, with one default. A piece may use only those; anything else is an owner exception per scene.

## Text entrances

| Entrance | What it does |
|---|---|
| `fade-up` | parts rise and fade in, staggered |
| `mask-up` | parts are uncovered from below |
| `word-stagger` | the headline arrives word by word |
| `scale-in` | parts settle from 94 % |
| `fade` | opacity only |
| `none` | no entrance |

Stagger is per part: kicker, head, sub, then each point. It stops growing after `maxItems`. `textOut` (optional) runs the reverse just before the next scene.

## Pace and reading

- `pace.readingWpm` is the on-screen reading speed the concept assumes; about 180–220 for short social copy.
- `lint` flags a scene whose still part is shorter than its words need (`words / wpm × 60 + 0.5 s`). This is a signal for the owner, not a failure.
- `pace.minHold` is enforced: a scene whose still part is shorter fails `lint`. Lengthen the scene, or shorten its transitions.
- `pace.voWpm` is the voice-over pace: 130–170 is conversational, faster reads as an ad. It times the planned voice-over and captions.

## Reduced motion and flashing

- A rendered video can't follow a viewer's reduced-motion setting. Prefer short, small movements: no large parallax and no full-screen spins. Keep any loop calm.
- Never flash more than three times in a second. The render checks for it (a heuristic) and lists anything it finds for review.
