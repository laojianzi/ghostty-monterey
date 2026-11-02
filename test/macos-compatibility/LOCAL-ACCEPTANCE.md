# Latest local acceptance disposition

Current scope: the user chooses ReleaseLocal-only distribution and excludes app
signing/notarization from verification. Historical public-trust gates below are
not current acceptance blockers; functional failure verdicts are unchanged.

Newest: REMAINING-VERIFICATION.md raises actual selected XCTest coverage to
27 passing methods and resolves the quick-command concern. It retains explicit
source/test disagreement, inherited interaction failures and distribution gates.

Authenticated follow-up: XCODE-UI-ACCEPTANCE.md records actual XCTest UI
execution: 26 selected methods pass, two remain explicitly unresolved, and
test-only SDK/query/fixture differences are listed. Authentication is no longer
a pending human-only gate. The original desktop state was restored afterward.

Newest follow-up: FINAL-LOCAL-AUDIT.md supersedes the remaining-unknown labels
for VoiceOver selection, hidden-titlebar split drag, original UI compilation and
local trust assessment. It records failures as failures, plus a new drag fix and
matched final-build archive/native evidence.

Follow-up: COMPLETION-ACCEPTANCE.md records subsequent four-direction
cross-window drag/undo/redo, quick-terminal light/dark, Caps/repeat native-event,
ten-minute workload and actual VoiceOver text-caption checks on the same binary.
Japanese/Korean layouts are now excluded by the user, not a pending manual
requirement. Earlier rows below describe the native-final-05 session.

Date: 2026-11-01. Target: Intel macOS 12.7.6 only. No ARM or macOS 13/14 gate.
Artifact: ReleaseLocal build 18457, executable SHA256
cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
Evidence: /tmp/ghostty-monterey/native-final-05. Earlier keyboard, drag and
search-focus reports are in NATIVE-INTERACTION.md. This is not release approval.

## Executed in this session

| Area | Outcome | Evidence and boundary |
| --- | --- | --- |
| System light/dark transition | Pass | Real System Preferences controls changed light -> dark -> original light; configured GitHub Light/Dark themes visibly switch terminal background, foreground, cursor and titlebar; appearance-light.png / appearance-dark.png inspected |
| Configuration reload | Pass in tested scope | Dual-theme config loaded live, original config restored; appearance-result.json |
| Explicit window-theme with transparent titlebar | Expected documented behavior | Light/dark overrides do not force the transparent terminal titlebar away from terminal background luminosity; Config.zig documents this exception. Not a general override failure |
| Real Shortcuts Run AppleScript | Pass | Created one disposable shortcut through the actual UI; returned the private app's visible terminal text; shortcut-run.png inspected |
| Shortcuts scripting initially disabled | Pass | UI refuses Run AppleScript with explanatory setting link; shortcut-added.png inspected |
| Ghostty scripting disabled after reload | Pass | Same shortcut fails to resolve terminal 1; shortcut-denied.png inspected. It cannot read terminal contents; no App Intents policy parity claimed |
| Self/rejected native drops | Pass | Actual drag back onto its source and onto desktop gap leave pane geometry unchanged; child accepts fresh input afterward; drop-rejection.json |
| Cross-window automatic activation | Reproduced limitation | Moved child 32102 remains alive, but immediate z reaches surviving source child 32601. cross-before.json / cross-after.json and PTY logs. Not certified as automatic destination focus |
| VoiceOver | Partial, not signed off | Started actual VoiceOver via welcome UI; VO navigation produced a visible terminal focus outline. No reliable speech/caption transcript was obtained. A running process or visible outline is not complete accessibility acceptance |
| Japanese/Korean input modes | Not completed | Enumerated installed modes; enabling the Japanese mode did not make it selectable through the existing TIS helper. Harness stops before keyboard delivery; no Ghostty defect or IME pass inferred. Korean case did not execute |

The Shortcuts runner is not merely an osascript substitute: the action was added,
edited and run in the real Shortcuts editor, with visible returned text and an
actual failure alert after Ghostty's scripting opt-out. The shortcut's temporary
display title did not persist as its library name; it was deleted as the sole
new `Run AppleScript` item. The six original shortcuts remain. Their actions
were not executed or edited. iCloud sync was already enabled, so the temporary
shortcut may have synchronized while present; its deletion UI applies to all
synced devices. No remaining test shortcut was observed locally.

## Why no new product patch

The cross-window controller explicitly calls moveFocus to the moved surface,
but the upstream helper only makes it first responder in its window; it does
not call makeKeyAndOrderFront or otherwise activate that window. These calls
are unchanged apart from the previously documented Swift syntax conversion.
This supports separating within-window responder focus from window activation,
but is not an upstream newer-OS runtime comparison. The observed activation
limitation remains visible rather than being declared fixed or silently patched.

The explicit window-theme result also follows the upstream documented transparent
titlebar exception. No theme feature was removed or backported solely to force
an incorrect test expectation.

VoiceOver scripting caused a macOS Automation consent prompt for the invoking
client (`vp`). It was declined rather than granting broad new access. VoiceOver
keyboard navigation was attempted independently afterward. No synthetic speech
was substituted for actual VoiceOver output. Additional user permission was not
treated as necessary for the already-authorized desktop tests, but this run does
not claim to have verified the inaccessible speech channel.

## Cleanup and current limits

cleanup.json verifies original foreground app/input source and enabled-source
inventory, original light appearance, original Shortcuts scripting-disabled
setting, deletion of the disposable shortcut, stopped VoiceOver, and termination
of the private app plus all three PTY children. The original user configuration
and general clipboard were not changed. System Preferences and Shortcuts were
opened for testing; they may remain open. No credentials, signing, Gatekeeper,
system compiler or public release settings were changed.

Remaining local work is specific, not a blanket manual handoff:

- Resolve the input-source harness failure before claiming Japanese/Korean or
  additional layout coverage; physical repeat/Caps Lock remain unverified.
- Obtain actual VoiceOver reading/selection evidence, not just AX text or cursor.
- Decide whether to retain the upstream cross-window activation behavior or
  require a narrowly scoped change after a differential test.
- Quick-terminal appearance under both system themes, all cross-window drop
  directions and a defined long-duration workload are not covered by this run.

Public distribution separately needs immutable source/artifact identity and a
verified install/trust policy. Existing bounded performance/extended archive
tests remain valid in their recorded scopes; none is a full clean-machine or
long-duration performance certification.
