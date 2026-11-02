# Remaining verification follow-up

Historical follow-up: use RELEASE-READINESS.md for the current scope and latest
artifact. INPUT-ACCEPTANCE.md, NONAX-ACCEPTANCE.md and RESOURCE-ACCEPTANCE.md
supersede this intermediate backlog. AX selection is excluded by the user.

Later follow-up: FOCUS-ACCEPTANCE.md fixes and verifies cross-window automatic
activation on rebuilt ReleaseLocal 583e90ea4f5c1779deef5c077dc451cf52f526922db2f5aa161b2840ad83e408.
It also repeats the 27 selected UI passes and records a new VoiceOver diagnostic
control. The old focus failure and artifact identity below are historical;
VoiceOver selected-text speech is not fixed by that follow-up.

Scope correction from the user: distribute ReleaseLocal only; app signing and
notarization are outside verification. Missing signing identities and Gatekeeper
rejection below are informational, not remaining goal blockers. The earlier
request for a distribution-signing decision is superseded. Functional results
and their limitations are unchanged.

2026-11-01, Intel macOS 12.7.6 only. This continues XCODE-UI-ACCEPTANCE.md.
No product source changes, feature removal, commit or publication in this run.
ReleaseLocal executable remains
3603418a1e5e42f75e1608db668dd0b9701b23237b1771f2d77ce74640cd86fc.

## Cross-window tab case now executes and passes

The previously unresolved cross-window tab method passes twice individually
(remaining-tabs-15 and remaining-tabs-repeat-16), then in both consolidated runs.
The UI candidate is still distinct from ReleaseLocal.

The private _zoomLeft:/_zoomRight: setup is replaced only in the disposable test
with native AX window positioning, verified at x20/x740, width650. XCTest's
snapshot contains both tab groups, but indexed inactive-window descendant
queries fail on this host. The revised test enumerates app.tabs, selects by
observed frame on the test side, and uses XCTest's real press-and-drag gesture.
It asserts the group counts change from 3+2 to 2+3, total five, before running
the original close-button/shortcut/title alignment and tab-height assertions
against both focused windows. No controller move action replaces the drag.

A failed intermediate attempt used frame predicates inside XCUI queries;
that attempt reported application-not-running and is not counted as a pass.
Client-side enumeration avoids that unsupported query path. Initial titlebar
drag positioning was also not accepted as equivalent coverage.

## Consolidated UI result and one retained disagreement

remaining-consolidated-17: 27 selected methods, 26 pass, one title assertion
fails because it observes an empty title immediately after launch. The same
unchanged title case passes separately in remaining-title-repeat-18. A bounded
five-second wait for the expected title is added to the disposable test before
its unchanged equality assertion; this does not relax the expected title.

remaining-consolidated-19: **27 methods, zero failures**, 170.685 seconds,
xcodebuild exit 0. xcresulttool independently verifies all 27 Success records.
This includes all nine theme cases and all five tab cases. It is not an
unchanged official 28/28 run: the earlier documented SDK/query/quick-background
adaptations still apply.

The only excluded original method remains fixed-size tear-off's full-width
assertion (165 actual vs 328 expected). Official newWindow(tree:) explicitly
uses pane bounds; final-product native tests preserve that behavior. Its failed
original assertion is retained, not rewritten to manufacture a pass.

Durable compact evidence is in evidence/2026-11-01-ui/results.json. The exact
disposable UI source delta is archived as candidate-tests.patch, not applied to
the original test files. It references temporary helper paths and is an audit
artifact, not a portable standalone UI runner. Full logs/xcresults remain under
/tmp/ghostty-monterey/xcode-ui-07; log hashes accompany the compact report.

## Quick-terminal command concern resolved

On a private copy of the final ReleaseLocal app, ordinary and quick terminals
each start the configured isolated Python raw-PTY child. The quick child receives
the exact `a` byte after native input. Its executable and parent are recorded in
remaining-native-27/quick-command-result.json. It does not ignore the configured
command in this scenario.

The previously observed `Last login` banner is not evidence of a user shell:
official src/termio/Exec.zig deliberately wraps both direct and shell commands
with /usr/bin/login on macOS. The relevant wrapper is byte-identical to official
HEAD. No shell-command product patch is justified by that banner.

## Cross-window split focus is a reproduced failure

A final-product native handle drag moves live child46159 from the left window
to the right window; all three child processes and panes remain present.
Without a pointer-refocus click, injected `b` is received by the remaining source
child46106, not moved child46159. The geometry and byte log make this a concrete
failure, not merely missing human acceptance. A preliminary drag missed the
small handle and is not used as evidence of successful transfer.

The cross-window tree mutation/focus scheduling block is byte-identical to
official HEAD. Together with the earlier native makeFirstResponder probe this
supports an inherited key-window omission, not a transport regression introduced
by the port. It does not prove behavior on a newer official executable. Retain
the limitation under the user's minimum-port requirement; do not silently add
a general focus/undo redesign to obtain a passing checkbox.

## VoiceOver: further narrow controls do not fix selected speech

The terminal-like native NSView control now additionally supplies top-level
window, shared text elements/range, correct selected range and plural ranges.
Actual VO-F6 still captions no selection (model28-14260.png). Explicit enabled
and focused accessors also leave no-selection speech (model29-14260.png).
The same session's NSTextView control captions `beta, selected`
(control28-14260.png). All three captions were captured and visually inspected.

These negative controls rule out those simple metadata additions as sufficient
solutions in that fixture. They are not new Ghostty fixes or a claim that the
full speech cause is understood. The previously demonstrated Ghostty failure
remains. The user-approved separation of the broad AX snapshot experiment is
preserved, including the documented inherited selected-range defect.

## Distribution and cleanup

Read-only `security find-identity -v -p codesigning` reports zero valid signing
identities. Password authorization for XCTest does not create a Developer ID
identity or notarization account. The earlier normal Gatekeeper rejection of
the ad-hoc artifact remains. No credentials were extracted, identities created,
quarantine removed or security policy relaxed.

The user subsequently chose ReleaseLocal-only distribution and excluded app
signing/notarization from verification. No owner signing credentials or
Gatekeeper approval are required to close that scope. Preserve exact artifact
identity and known functional limitations; do not describe the build as
notarized or system-trusted. A commit/tag/upload is separate from verification.

VoiceOver is disabled through its original checkbox, verified off; control
fixtures, private terminal apps/children, XCTest runners and desktop controllers
are stopped. System appearance is restored light. Foreground iTerm PID22191,
WeType input source and full enabled-source inventory match the pre-run snapshot.
XCTest changed the source inventory (US added, EmojiFunctionRowItem absent);
the added source was disabled and the original item reenabled, then the full
inventory was compared successfully. A testmanagerd third-party-input-method
consent sheet was declined rather than granting an additional permission.
Clipboard restoration guards report success, without recording contents.
