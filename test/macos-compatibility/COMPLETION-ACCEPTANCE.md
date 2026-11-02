# Additional local acceptance

Date: 2026-11-01. Host: Intel macOS 12.7.6. Product executable SHA256:
cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
No product changes during this run. ARM, newer macOS and Japanese/Korean layouts
are explicitly outside the user's current scope. This report supersedes the
corresponding outstanding rows in earlier reports, not unrelated release gates.
Raw evidence: /tmp/ghostty-monterey/native-completion-06 (temporary local files,
not immutable release evidence). Private app PID 40881; isolated config/defaults.

## Results

| Scenario | Result | Evidence / limit |
| --- | --- | --- |
| Cross-window left/right/top/bottom drop | Pass | Actual handle drags between non-overlapping windows; relative pane geometry checked; moved child 50273 accepts fresh input after pointer focus |
| Cross-window undo/redo, all four directions | Pass | Actual Edit menu restores original and moved geometry with same child PID; direction-results.json and direction-*.json |
| Quick terminal system light/dark | Pass | Same surface C6BE5BFC-21ED-4A4D-9B9F-39A6951F2388 and child 48426; actual system controls; inspected quick-actual-light-10783.png and quick-actual-dark-10783.png |
| Caps Lock modifier and repeat events | Pass for injected native events | Real app to raw PTY, exact legacy and Kitty bytes checked; not physical keyboard/firmware or OS repeat-timer coverage |
| Ten-minute ANSI/Unicode workload | Pass in bounded scope | 600.10 seconds, 5,811 DSR round trips, 9,669,504 output bytes; no acknowledgment deadline failure or app exit |
| VoiceOver text reading | Pass in bounded scope | Enabled screen reader's caption contains UI TEST 40889 - alpha beta search target; vo-terminal-reading.png inspected; window and keyboard-focus announcements also inspected |
| VoiceOver selected-text reading | Not certified | AX exposes selected beta, but attempts did not obtain a reliable selected-text speech caption; ordinary text reading is not sufficient |

## Harness corrections

- Layer-zero-only screenshot helper initially captured an ordinary window, not
  quick terminal. Correct captures select CGWindowID 10783, layer 3, bounds
  x0/y25/1440x400. Earlier quick-light.png / quick-dark.png are not this evidence.
- Test-created VoiceOver HelpViewer covered the right drop region. Those drops
  were correctly rejected. Closing it enables all four cross-window directions
  and undo/redo. Source handle coordinates also corrected from the screenshot.
- A process started by open is not proof VoiceOver is enabled. Used Accessibility
  checkbox and welcome UI; captured localized owner windows. No synthetic speech.
- First keyboard probes after stopping VoiceOver delivered no bytes despite AX
  focus. Switching foreground away and back restored delivery. Both modes rerun
  with exact byte assertions; the empty first run is not a pass.

## Exact keyboard evidence

CGEvent down/up with Caps Lock flags, then a normal key down, five key-down
events with keyboardEventAutorepeat=1, and key up. No global Caps setting changed.

- Legacy: exactly `Aaaaaaa`.
- Kitty: Caps press `ESC[97;65;65u`, release `ESC[97;65:3u`; ordinary press
  `ESC[97;;97u`; exactly five `ESC[97;1:2;97u` repeats; `ESC[97;1:3u` release.

repeat-caps.json records payloads. This adds repeat/action/modifier coverage,
without claiming physical hardware repeat timing was exercised.

## Workload boundary

Child emits 32 ANSI-colored lines containing Chinese, a combining character and
emoji per cycle, requests cursor position, checks response within five seconds,
then sleeps 0.1 seconds. Stops after ten minutes; no unbounded output file or
allocation stress. Progress files are small; app scrollback remains bounded.

121 samples cover 601.19 seconds. App cumulative CPU increases 32.53 seconds
(about 5.4% of one core averaged). RSS ends at 148,676 KiB; final 120 seconds
range 148,676-151,000 KiB. Appearance, quick-terminal and accessibility checks
ran concurrently: not an isolated benchmark or attribution of all RSS to
scrollback. DSR proves parser responsiveness, not GPU presentation. Not an
overnight leak test or official same-host performance comparison.

## Cleanup verified

- Original ABC source, enabled inventory and foreground PID 22191 restored and
  compared with acceptance06-original.json; cleanup.json records verification.
- Original light appearance restored; private config restored, including removal
  of duplicate temporary theme/autohide overrides. No user config/clipboard edit.
- VoiceOver disabled, preference checkbox verified off. Test-created HelpViewer
  and VoiceOver Utility exited; caption-panel setting restored to original on.
- Temporary invoking-client to VoiceOver Automation checkbox restored off and
  verified in automation-restored.json. VoiceOver AppleScript control was never
  enabled: authentication cancelled without credentials or bypass. Other
  Automation permissions unchanged.
- Isolated app and all five tested children exited, verified by process absence.
  No system compiler replacement, security-policy relaxation, signing identity
  modification, public upload or release operation.

## Remaining distinctions

Automatic destination activation immediately after cross-window drop remains
the previously reproduced limitation. Official controller/helper also lacks an
explicit activation call: source evidence, not a newer-OS runtime comparison.
Retain this known limitation rather than silently broadening the minimal port
into a general upstream focus redesign.

VoiceOver selected-text speech remains unverified. The inherited cell-to-UTF16
selected-range defect is not repaired; archived optional AX snapshot stays out.
Physical repeat timing, audio quality, full original XCTest UI-suite execution
and clean-machine public-distribution trust are not established by these checks.
