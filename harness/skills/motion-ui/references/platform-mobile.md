# Mobile and native motion

Implementation guidance for React Native, Expo, Jetpack Compose and SwiftUI, and what each capture driver can prove. In this release native motion is **evidence-only**: there is no native seek adapter, so a device or simulator run can't be complete.

## What each driver can establish

| Driver | Visual lane | Behaviour lane | Reduced motion | Semantic checks | Best possible run |
|---|---|---|---|---|---|
| `web` (browser) | yes (app-seek, or the virtual clock) | yes | emulated | DOM selectors | complete |
| `expo-web` | yes | yes | emulated | DOM | complete for the web build only; adds the review item `native-runtime-unverified` |
| `adb` (Android device) | no | recording only | by hand (changing device settings needs the owner) | no | incomplete: missing visual, semantic |
| `frames` (Compose test frames) | the project's own deterministic frames, `verify --frames DIR` | no | from the project's test | no | complete only with `--recording` too; semantics and reduced motion become manual review items |
| `file` (iOS, any recording) | no | recording only | by hand | no | incomplete |

`lint` and `SPEC.md` print the best possible result for the piece's driver, so nobody reads "verified" into a native run.

## React Native and Expo

- One clock: a Reanimated shared value (`useSharedValue`) holds progress; derived values (`useDerivedValue`) compute every track from it; worklets keep it off the JS thread. `withTiming` durations and `Easing.bezier(...)` come from the motion tokens (the concept's `motion.durations` and `motion.easing`).
- Layers and cameras: Skia (`@shopify/react-native-skia`) for planes, masks and perspective; Lottie or Rive when the motion is authored as a file (its licence is an asset licence).
- Reduced motion: `useReducedMotion()` (Reanimated) or `AccessibilityInfo.isReduceMotionEnabled()`; show the complete static scene.
- Pause, stop or hide: a real `Pressable` with `accessibilityRole="button"` and a label; pausing cancels the animation (`cancelAnimation`) and keeps progress.
- App state: pause on `AppState` `background`, resume without a jump.
- Expo web (`capture.driver: expo-web`, `npx expo start --web` started by you) gives the browser lanes for the web build. Record the device too: `motion.py record <id> --adb` (Android) or a simulator recording with `--file`.
- Deterministic values without pixels: Jest with Reanimated's test utilities and fake timers (`jest.advanceTimersByTime`) can assert the shared values at spec times. Keep those tests in the project; they don't feed `verify`.

## Jetpack Compose

- One clock: an `Animatable` or `updateTransition` drives progress; `graphicsLayer` applies scale, translation and alpha per layer; `Canvas` or `drawWithContent` for planes and masks.
- Tokens: durations and `CubicBezierEasing` from the motion tokens (export them to `Motion.kt` from the token file).
- Reduced motion: honour the system animator duration scale (`Settings.Global.ANIMATOR_DURATION_SCALE` of 0) and show the static scene.
- Deterministic frames: in a Compose UI test, `composeTestRule.mainClock.autoAdvance = false`, then for each spec time `mainClock.advanceTimeBy(ms)` and `onRoot().captureToImage()` (or Roborazzi). Save them as `t<ms>.png` and pass the folder: `motion.py verify <id> --frames <dir> --recording <device.mp4>`.
- Device recording: `motion.py record <id> --adb [--serial S]` (`adb shell screenrecord`, 180 s at most; secure windows record black). The `mobile-screen-capture` skill (mobile profile) has the device checks and safety rules.

## SwiftUI

- One clock: `TimelineView(.animation)` or a `withAnimation` driven state; `phaseAnimator` / `keyframeAnimator` for multi-step tracks; `.scaleEffect`, `.offset`, `.opacity`, `.rotation3DEffect` per layer.
- Tokens: durations and `.timingCurve(...)` from the motion tokens.
- Reduced motion: `@Environment(\.accessibilityReduceMotion)`; show the static scene.
- Pause: a real `Button` with an accessibility label; `TimelineView(.animation(paused:))`.
- Recording: `xcrun simctl io booted recordVideo out.mp4`, then `motion.py verify <id> --recording out.mp4` (driver `file`). Snapshot tests (for example swift-snapshot-testing) can produce `t<ms>.png` frames for `--frames`.

## Common rules

- Native text and controls stay accessible: labels, focus order, Dynamic Type and font scale, nothing invisible keeps focus.
- Bound frame cost on a mid-range device; no per-frame allocations; stop the clock when off screen.
- A device recording is pacing evidence. Look at it; the run can't measure it.
