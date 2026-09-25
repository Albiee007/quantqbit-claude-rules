---
name: mobile-screen-capture
description: Read-only walkthrough of a mobile app on a connected real device (Android over ADB, iOS via a connector or the macOS simulator) that produces a dated folder of screenshots at every scroll depth and opened state, plus an INDEX.md. Use when asked to capture, tour or document an app's current UI, to gather reference screens for store mockups or design review, or before a redesign. Not for code-only design review or for writing automated screenshot tests.
---

# Mobile Screen Capture

Capture a reviewable, locally stored tour of the app on the user's connected device. Cover each reachable top-level area, meaningful scroll depth, and safe detail/component views. Keep the user informed on long captures, and make the final index clear enough to navigate without opening every image.

## Safety rules (not overridable)
- **Read-only.** Never submit, save, create, invite, settle, pay, delete, leave, log out, import data, change settings or grant permissions unless the user authorised that specific action. Blank forms may be opened to inspect their fields and then closed.
- **Personal data stays local.** Real-account captures contain names, photos, balances and contacts. Write them to a folder that is gitignored, or ask where to put them. Never upload or send them anywhere unless asked. Never copy on-screen personal details into `INDEX.md`.
- **One device, chosen deliberately.** With several devices connected, pass an explicit serial on every command. If the target is ambiguous, ask before touching anything.
- **No guessed coordinates.** Coordinates don't transfer between devices, resolutions or app versions. Take them from a fresh UI dump or the current screenshot.

## Workflow
1. **Choose the control path and device.**
   - Prefer a mobile or computer-use connector if one is available.
   - For Android over ADB, see [references/android-adb.md](references/android-adb.md).
   - For iOS, see [references/ios-capture.md](references/ios-capture.md). **Never use ADB for iOS.**
   - Identify the intended device from its model and the app state it is showing.
2. **Establish a baseline.**
   - Confirm the app is in the foreground.
   - Record the device model, display size and orientation, and the app package or bundle id if available.
   - Capture the first screen.
   - Create a dated output folder, e.g. `store-assets/<YYYY-MM-DD>/` or `artifacts/mobile-screenshots/<YYYY-MM-DD>/`, unless the user chose another place.
3. **Map the reachable screens.**
   - Walk the visible tabs, menus, cards and detail links.
   - Use the accessibility or UI hierarchy and its element bounds (`scripts/ui_dump.py` on Android).
   - Take a fresh screenshot after every navigation to confirm where you are.
4. **Capture full screen depth.**
   - For each scrollable area, capture the top, useful middle regions and the bottom, with overlapping swipes so nothing is skipped.
   - When a list lazy-loads, keep scrolling and capturing while it changes.
   - Stop at an explicit end marker (e.g. "You're all caught up"), or when repeated scrolls show nothing new. Keep that terminal screenshot.
5. **Drill into components safely.**
   - Open cards, menus, dialogs, pickers and detail pages, capture them, then close or go back to restore the previous screen.
   - Don't change a preference value while inspecting a picker.
6. **Recover carefully.**
   - If a control stops responding, check the current screen and try the visible close or back control **once**. Don't keep tapping guessed coordinates.
   - Force-stop and relaunch only when no unsaved input or in-progress operation can be lost. Otherwise stop and report the blocked screen.
7. **Organise and verify.**
   - Use stable descriptive names: `NN-area-position.png`, e.g. `10-groups-top.png`, `11-groups-middle.png`, `12-groups-bottom.png`.
   - Run `python .claude/skills/mobile-screen-capture/scripts/dedupe_index.py <folder> --device "<model> <W>x<H>" --write-index`. It removes byte-identical duplicates only, keeps the terminal and end-marker captures, and writes an `INDEX.md` skeleton grouped by area.
   - Finish the index by hand. Include the device and date, the screen families, the filename sequences, the scroll endpoints, and which forms were left unsubmitted.

## Scripts
| Script | What it does |
|---|---|
| [scripts/capture_adb_screenshot.py](scripts/capture_adb_screenshot.py) | One binary-safe PNG from `adb exec-out screencap -p`. Refuses to overwrite without `--overwrite`, and needs `--serial` when several devices are online |
| [scripts/ui_dump.py](scripts/ui_dump.py) | Dumps the UI hierarchy and lists the clickable labels with their bounds and tap centres |
| [scripts/dedupe_index.py](scripts/dedupe_index.py) | Removes exact duplicates and writes the INDEX.md skeleton |

Run the scripts with `python <path>`; they need Python 3.9+ and `adb` on PATH. Never pipe `adb exec-out` through a PowerShell text variable, because Windows PowerShell corrupts binary output.

## Report back
- The screenshot count, output folder and index path.
- Coverage: which areas were captured to their end, and which were partial.
- Screens you couldn't reach, and why (a permission, a paywall, needing data, a stuck overlay).
- Confirmation that no create, submit, settings or permission action was taken, or which authorised actions were.

## References
- [android-adb](references/android-adb.md): device selection, UI hierarchy, coordinate checks, scrolling to the end, recovery. Includes a worked example.
- [ios-capture](references/ios-capture.md): connectors, the Simulator, and what not to do.
- Downstream skills that use these captures: `store-mockups` (which rebuilds screens from them) and `store-listing` (which builds the feature inventory).
