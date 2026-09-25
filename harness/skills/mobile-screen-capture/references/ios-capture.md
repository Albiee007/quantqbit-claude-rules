# iOS capture reference

Read this when capturing an iOS app. The general process is in [../SKILL.md](../SKILL.md). **ADB does not work for iOS. Don't try it.**

## Choosing a control path
1. **A connected mobile or computer-use connector.** Prefer this when one is available. Use its element labels, and take a fresh screenshot after each navigation.
2. **Xcode Simulator (macOS only).** Good for store-size captures from a release-candidate build:
   ```bash
   xcrun simctl list devices booted
   xcrun simctl io booted screenshot "store-assets/2026-01-31/01-home-top.png"
   xcrun simctl status_bar booted override --time "9:41" --batteryState charged --batteryLevel 100 --cellularBars 4 --wifiBars 3
   ```
   Pick the simulator model for the store slot you need. A 6.9″ iPhone gives 1290 × 2796 or 1320 × 2868, and a 6.5″ gives 1242 × 2688. Reset the status bar afterwards with `xcrun simctl status_bar booted clear`.
3. **A physical iPhone.** Use the connector, or have the user take the captures (Side + Volume Up) and AirDrop them. Don't invent a workaround that installs profiles or grants the device access to anything.

## Rules that differ from Android
- **Platform-gated features:** some features exist only on Android (e.g. SMS import). Record their absence on iOS, and never show them in iOS captures or mockups.
- **Sign in with Apple:** capture it only on a test account. The private-relay email shown in captures is personal data.
- **Sheets:** iOS dismisses sheets by swiping down. Use the visible close button, because a swipe can trigger "discard changes?" prompts.
- **App Review:** screenshots must match the build you submit (Guideline 2.3.3). If a capture is for the App Store, take it from the exact TestFlight or release-candidate build.

## Output
Same as Android: a dated folder, `NN-area-position.png` names, `dedupe_index.py` for exact duplicates, and an `INDEX.md` with no personal data.
