# Motion techniques

Implementation patterns for scene-driven motion. They are stack-neutral: map them onto the project's framework and animation library.

## Scenes are data

Keep content, media, timing and layout in configuration, separate from the renderer, so new scenes and brands reuse the choreography:

```ts
type Scene = {
  id: string;
  durationMs: number;                          // from the motion spec, through tokens where they exist
  title: string[];                             // from the project's copy, never the reference's
  media: { type: 'video' | 'layers' | 'image'; sources: string[] };
  layout: Record<string, string>;              // per viewport: 'title-left', 'title-lower', ...
  camera?: Keyframe[];                         // project-specific keyframe type
  overlays?: Record<string, Keyframe[]>;
  transition: { kind: 'cut' | 'crossfade' | 'mask' | 'camera'; durationMs: number };
};
```

Validate indices, positive durations, media references and bounded camera travel. Add depth or geometry only where the spec needs it.

## One clock

- One clock drives camera, typography, panels, progress and scene changes. No independent timers or CSS animations for elements that must stay in sync.
- Evaluate a pure function of normalised time: `pose = motionAt(scene, t)`. It makes pause, replay, selection and capture exact, and it is what `window.__motion.seek` calls ([capture-contract](capture-contract.md)).
- Browsers: elapsed time, not frame counts. Clamp large frame deltas (a backgrounded tab), pause when hidden and resume without a jump, start once required media is ready behind a deliberate poster.
- Update per-frame transforms through refs or the animation engine; don't re-render a React tree every frame.
- Video-driven motion derives overlays from the media's own time, so seeking, buffering, looping and pausing stay aligned.
- Holds and transitions come from the measured spec, not equal slideshow durations.

## Dolly zoom

Projected size is proportional to focal length × object size / distance. With D the initial focus-plane distance, d the camera's forward travel and f0 the initial focal length:

```text
f(d) = f0 × (D − d) / D                         keeps the focus plane's size constant
nearScale(d) = ((D − d) / D) × N / (N − d)      a nearer layer at distance N
```

The near layer grows faster while far landmarks stay stable. Bound the denominators and use a near clipping plane; don't fly through a layer unless you mean to remove it.

- 3D engine: move the camera and change focal length (FOV) together. With a fixed sensor height, vertical FOV = 2 × atan(sensorHeight / (2 × focalLength)).
- Plane renderer: build a screen ray from the viewport aspect and focal length, intersect each plane, map the hit to texture UV. One camera for every layer; lateral travel then displaces nearer layers more on its own.
- This reproduces perspective across planes. It does not invent unseen geometry, moving light or real environmental motion.

## Layers and apertures

- Draw far layers first, mid layers next, transparent foreground last. Keep alpha blending consistent with texture premultiplication.
- An aperture (doorway, window, cut-out) belongs to its mid layer; the far scene lives behind it. Fit its centre and radii to the asset, feather the seam minimally, keep its edge believable, and let the layer grow out of view through projection. An expanding screen-space circle reads as a wipe, not camera travel.
- Prefer separate planes to displacing one photo that holds near objects and far landmarks: shared displacement bends straight edges.

## Coverage and continuity

- Before finalising assets, compute the largest camera offset and magnification and supply that much overscan. Clamp-to-edge avoids sampling errors but repeats border strips when exposed.
- Never smear detailed scenery to fill missing coverage: use a wider asset, more geometry or a deliberate plain extension.
- At shot boundaries align landmarks, horizon, focus-plane scale, grade and lateral offset at the same timestamp. If the reference cuts, cut: a misaligned crossfade doubles outlines.

## Perspective typography

Give title travel its own track; don't zoom the scene because the text becomes huge.

```css
.title {
  transform: perspective(var(--perspective)) translate3d(var(--title-x), var(--title-y), var(--title-z))
    scale(var(--title-scale));
  opacity: var(--title-opacity);
}
```

At perspective distance P and depth z the scale is P / (P − z); for a wanted scale s, z = P × (1 − 1/s), with z < P. Check sharpness at extreme scales: a permanently promoted layer can be rasterised small, so drop needless `will-change: transform` or use vector text. Text and controls stay in the DOM even when the backdrop is a canvas.

## Easing and choreography

- Normalise an interval: `t = clamp((time − start) / (end − start), 0, 1)`; apply the row's easing token (`cubic-bezier` from the concept). Quintic smootherstep, `t³ × (t × (6t − 15) + 10)`, is the `smootherstep` keyword.
- Match easing to the evidence row by row; don't apply one curve everywhere. Separate quiet holds from fast travel; evaluate camera and overlays together.
- Under reduced motion, resolve to a complete readable static frame (`reducedMotion.staticAt`) with working navigation.
- Freeze the shared time on pause; pause, stop and hide are the app's own controls, with real labels.

## Resilience

- Poster or fallback for media and WebGL failure; on context loss recover or keep the fallback deliberately.
- Clean up textures, listeners, observers and animation frames.
- Bound render resolution and device pixel ratio from measurements on representative hardware; resize the projection with the viewport.
- Invisible overlays must not take focus or intercept input: opacity alone does not disable interaction (use `inert` or remove them).
