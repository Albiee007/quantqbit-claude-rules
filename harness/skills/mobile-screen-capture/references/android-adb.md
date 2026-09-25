# Android and ADB reference

Read this when capturing an Android device with ADB. The general process is in [../SKILL.md](../SKILL.md).

## 1. Select and inspect the device
```bash
adb devices -l
```
If several devices appear, identify the target from the requested device and the app state it is showing. Pass `-s <serial>` on **every** command. Never assume the first device is the intended phone.

Record the display size and density:
```bash
adb -s <serial> shell wm size
adb -s <serial> shell wm density
```
Check which activity is resumed (the output varies by Android version):
```bash
adb -s <serial> shell dumpsys activity activities | grep -i resumed
```
Confirm the intended app is in the foreground before capturing. Read the package name from the UI hierarchy or the activity output. Never guess it from a project folder name.

## 2. Capture a screenshot
Use the bundled helper, which keeps the PNG binary end to end:
```bash
python .claude/skills/mobile-screen-capture/scripts/capture_adb_screenshot.py \
  --serial "<serial>" --out "store-assets/2026-01-31/01-dashboard-top.png"
```
It refuses to overwrite an existing file unless you pass `--overwrite`. It requires `--serial` when more than one device is online, and it checks the PNG signature.

The same thing in plain Python:
```python
import subprocess
from pathlib import Path
png = subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"],
                     check=True, stdout=subprocess.PIPE).stdout
assert png.startswith(b"\x89PNG\r\n\x1a\n"), "ADB did not return a PNG"
Path(out).write_bytes(png)
```
Never capture `adb exec-out` into a PowerShell variable and write that string back out. Windows PowerShell decodes it as text and corrupts the image.

## 3. Inspect clickable bounds
```bash
python .claude/skills/mobile-screen-capture/scripts/ui_dump.py --serial "<serial>"
python .claude/skills/mobile-screen-capture/scripts/ui_dump.py --serial "<serial>" --all --xml-out uia.xml
```
The helper runs `uiautomator dump`, reads the XML back through `exec-out` (binary-safe), and prints each clickable node's label, bounds and centre.
- The app hierarchy often ends above the system navigation area. Some OEM builds print harmless warnings before the XML; the helper skips them.
- Prefer a named, accessible element or a connector action. When you must tap by coordinate, use the centre of a **current** clickable bound, then check the result immediately:
```bash
adb -s <serial> shell input tap <x> <y>
adb -s <serial> shell input swipe <x1> <y1> <x2> <y2> <duration-ms>
```
- Compare the hierarchy with the full-resolution screenshot before tapping near the system bars. Never reuse another device's coordinates.

## 4. Scroll and detect the end
- Capture the visible top first.
- Swipe inside the scroll container, not across a bottom tab bar or a fixed toolbar. A good starting swipe is from 70% to 35% of the container height over 400–600 ms.
- Keep overlaps moderate. After each swipe, capture again and check whether the content changed.
- On paginated lists, give the app time to load before the next capture.
- Stop at an end marker, the oldest or newest date, a stable item count, or a repeated unchanged scroll. Capture that final state.
- For horizontal tabs, filters and chart ranges: capture the default state, open each safe view and capture it, then restore the page with its visible close or back control.

## 5. Recovery and cleanup
If touch input seems to do nothing, inspect the hierarchy and capture again before retrying: the coordinates may be stale, or the app may still be animating. Prefer the visible close or back control.

Force-stopping and relaunching is a last resort, only when no draft or operation can be lost:
```bash
adb -s <serial> shell am force-stop <package>
adb -s <serial> shell monkey -p <package> -c android.intent.category.LAUNCHER 1
```
Deduplicate by exact file hash (`dedupe_index.py`), never by visual similarity. Keep one copy of every meaningful end state, even when neighbouring scroll frames overlap. Keep the original PNGs and `INDEX.md` together, and never clean up outside the output folder.

## Worked example
- **Device choice:** two Android devices were connected. The Xiaomi (1080 × 2400, 440 dpi) was chosen explicitly because it was already showing the requested app.
- **Coordinates:** the UI tree ended above the navigation area, so bounds were checked against the full screenshot before each tap.
- **Long feed:** a paginated Activity feed was captured through lazy loads to its "You're all caught up" state.
- **Stuck overlay:** one overlay stopped responding. With no form open, the app was restarted to clear it.
- **Result:** 183 PNGs and an index. Every form stayed unsubmitted and no preference value was changed.

This is an example, not a default device, count or output path.
