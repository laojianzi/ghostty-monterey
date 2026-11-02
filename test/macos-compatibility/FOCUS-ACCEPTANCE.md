# Cross-window focus follow-up

Later artifact and input-source follow-up: INPUT-ACCEPTANCE.md. The identities
and focus results below remain evidence for this earlier build.

2026-11-01, Intel macOS 12.7.6. ReleaseLocal only; signing/notarization,
ARM, other machines and Japanese/Korean layouts remain outside acceptance.
This report supersedes earlier cross-window automatic-activation failures,
not the retained accessibility limitation or original fixed-width disagreement.

## Product change and artifact

BaseTerminalController.splitDidDrop now calls window.makeKeyAndOrderFront only
after successful cross-window insertion/removal. The shared moveFocus helper,
same-window branch, undo registration and invalid-drop paths are unchanged.
No activation is added to asynchronous generic focus callbacks.

This is a small fix for a reproduced interaction failure, not a claim that the
omission only affects Monterey. Before the fix, the cross-window controller
block and makeFirstResponder helper matched official 1.4. The independent
AppKit control distinguishes window activation from first-responder assignment.
It is unrelated to PR #3's legacy NSEvent translation.

ReleaseLocal executable:
583e90ea4f5c1779deef5c077dc451cf52f526922db2f5aa161b2840ad83e408

App: macos/build/ReleaseLocal/Ghostty.app, version 1.4.0, build 18457,
official HEAD 83fb95624b0439ee660c2679b43b38c8b63769cd with dirty adaptations.
Build succeeds using the unchanged system Swift 5.7/Xcode 14.1 configuration.
The existing universal build output is retained; ARM execution is not claimed.

## Red/green and regression evidence

| Scenario | Result |
| --- | --- |
| Previous ReleaseLocal, real handle drag | Fail: remaining child48830 receives `62`; moved48855 receives nothing |
| Candidate with only activation addition | Pass: moved49044 alone receives `62` |
| Rebuilt ReleaseLocal, same native probe | Pass: moved49716 alone receives `62` |
| Independent fresh ReleaseLocal launch | Pass: moved53692 alone receives `62` |
| Four directions, actual drag and Edit undo/redo | Pass: relative geometry and all three original children retained; fresh `a` goes only to moved pane without pointer refocus |
| Input after redo | Pass without a pointer-refocus click |
| Same-window move and cross-window Escape cancellation | Pass: expected geometry and fresh input retained |
| Move last source pane into another window | Pass: source window closes, all three live children remain, fresh `b` goes only to moved53678 |
| Production-tail AppKit seam, debug and optimized | Pass; removing activation fails both negative controls |
| Extended extracted-archive suite | Pass: resources, scripting policy/text, clipboard protocol, renderer/Kitty/compositor, Inspector, palette, lifecycle, quick terminal, undo/redo and refusal checks |
| Changed controller strict SwiftLint / git diff --check | Pass; existing linter configuration/deprecation warnings remain |
| Real XCTest UI candidate | 27 selected methods pass, zero failures, 169.866 seconds; xcresult independently checked |
| Fresh current-source Xcode unit candidate | 284 named passes, six documented skips with ABC input selected; reused pinned Testing objects and verified rebuilt core |

The seam test is repository-owned:
`python3 test/macos-compatibility/cross-window-focus-check.py`.
It extracts only the production cross-window success tail and uses real AppKit
windows; tree mutation is stubbed, so it complements rather than replaces the
native drag/PTY observations. It restores the previous front app.

The native scripts, compact results, screenshots and hashes are archived in
evidence/2026-11-01-focus. Those scripts document the exact disposable fixture
and use local helper paths; they are not an unattended portable GUI runner.
They require an isolated app and exclusive foreground control.

UI candidate and ReleaseLocal are different binaries. The candidate uses the
previously documented temporary Swift 5.10.1/SDK13 test adaptations plus this
same activation change. No original assertion was weakened. The fixed-width
tear-off assertion remains excluded with its original failed result preserved.
The first rerun was interrupted (exit75) after the appearance controller failed
to find a control while navigating from Accessibility to General. It is not a
passing run. Starting from verified General controls, the complete repeat passes;
no product/test assertion change was needed. Both logs are hashed in the evidence.

The fresh unit candidate initially reports 17 keyboard-layout issues with WeType
selected (the queried layout characters are nil). Repeating the same build and
unchanged assertions with ABC selected passes all 284 named tests and the same
six skips. This is explicitly an ABC-conditioned unit result, not a passing
WeType layout-translation result. Both logs are retained. It does not affect the
previous native WeType typing observations or establish an OS-specific cause.
The original aggregate entry's result.json retains its failed first invocation;
unit-results.json records the separately executed successful Xcode repeat.

The earlier thirty-minute soak belongs to the older cb71b89b binary. It is not
relabelled as a soak of this artifact. Current archive lifecycle measurements
exercise this artifact but are not an overnight or GPU frame-time benchmark.

## VoiceOver diagnostic progress, not a product fix

Real VO-F6 now distinguishes two otherwise identical terminal-like NSView
controls. A selected-range setter produces the actual caption `beta, selected`;
a selected-text setter without the range setter still produces no selection.
The controls retain correct ranges and plural ranges. Screenshots were captured
from VoiceOver and visually inspected. This narrows the earlier negative
metadata controls to selection writability as a relevant factor in this fixture.

The diagnostic setters deliberately do nothing. They must NOT be copied into
Ghostty: claiming writable selection without implementing it would break the AX
contract. This is not a verified Ghostty fix or proof that range mapping does
not matter. The current embedder API reads selection but does not expose an AX
UTF-16 selection setter. The user-approved separation of the broad snapshot
experiment remains intact. Actual Ghostty selected-text speech and inherited
cell-offset ranges retain their failed verdicts; ordinary text reading passed
earlier. No accessibility product source changed in this follow-up.

## Cleanup

Stopped private apps and children, VoiceOver controls, XCTest runners and
desktop controllers. Verified VoiceOver off and light appearance. Closed the
System Preferences instance opened for this run. Restored iTerm PID22191,
WeType and the complete enabled-input-source inventory. Reenabled the original
EmojiFunctionRowItem after XCTest removed it. Clipboard guard logged restoration
without recording contents. No install, commit, tag, upload or security-policy
change occurred.
