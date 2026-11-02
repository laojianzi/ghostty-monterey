# Continued local acceptance

Historical report: RELEASE-READINESS.md is the current index. The later
INPUT-ACCEPTANCE.md supersedes this artifact identity; NONAX-ACCEPTANCE.md and
RESOURCE-ACCEPTANCE.md record subsequent non-selection acceptance. AX selection
is now explicitly excluded, not repaired. Intermediate open gates below must
not be treated as a current request for human action.

Current scope: the user chooses ReleaseLocal-only distribution and excludes app
signing/notarization from verification. Historical public-trust gates below are
not current acceptance blockers; functional failure verdicts are unchanged.

Latest continuation: REMAINING-VERIFICATION.md records 27 selected XCTest UI
passes, cross-window tab coverage, verified quick-command inheritance, and the
remaining demonstrated focus/VoiceOver limitations. Authentication is resolved.

2026-11-01, Intel macOS 12.7.6. Japanese/Korean layouts, ARM and newer systems
are not required. This is not public-release approval. It records actual new
results, including failures, rather than converting every outstanding item to
a pass. Temporary evidence is under /tmp/ghostty-monterey.

Authentication follow-up: XCODE-UI-ACCEPTANCE.md supersedes the authentication
block below. Real XCTest UI execution now works. The consolidated isolated
candidate run passes 26 selected methods with zero failures; two methods remain
explicitly excluded after recorded failures. Test-only query/fixture adaptations
and the ReleaseFast quick-terminal pixel substitution are documented there.
This is not an unchanged 28/28 suite or a new ReleaseLocal product build.

## New product fix and artifact

Original UI-case audit found a real missing path: dragging a split handle in a
hidden-titlebar window moved the entire window instead of the split. Repeated
at handle offsets 3/6/9/11; native hit testing confirms SurfaceDragSourceView
is under the pointer. Swapping its mouseDownCanMoveWindow alone does not fix it.
Disabling window movement only during mouseDown is too late. Disabling it before
the gesture permits the same drag to detach the original live surface.

SurfaceDragSourceView now temporarily suppresses movement only while hovering
a hidden-window handle on Monterey, retaining the previous movable state in a
weak window reference. It restores on exit, detach, drag completion and release.
Normal window dragging outside the handle is verified afterward. No general
event monitor, window subclass, permanent non-movable window or core change.

Actual outside-window Escape then exposed another missed path: native dragging
can consume Escape before the local monitor, incorrectly creating a detached
window on cancellation. Monterey drag callbacks additionally sample the Escape
key state. The same cancel gesture now preserves the original two panes and
single window. Previous cancel evidence over another app window did not expose
this because endsInWindow already prevented tear-off.

Both changes are in SurfaceDragSource.swift. These are native window/drag issues,
not PR #3's Ctrl event translation and not the search focus or AX reader issues.
Official drag source has the same mouseDown-only protection and local Escape
monitor; newer-OS failure is not claimed without runtime evidence.

Final ReleaseLocal build succeeds: hidden-drag-escape-release-build.log.
Executable SHA256:
3603418a1e5e42f75e1608db668dd0b9701b23237b1771f2d77ce74640cd86fc.
The earlier hover-only build was 13d018f9; do not mistake it for the final build.

- hidden-release-24: actual tear-off coordinates, original-child input, menu
  undo/redo, outside Escape cancellation, and subsequent ordinary window drag.
- hidden-drag-state-check.py: debug/optimized native AppKit checks for hidden-only
  suppression, idempotence, preexisting false state, detach and release.
- hidden-drag-lint.log: zero violations (old linter warns about config/version).
- hidden-drag-package.log: complete extended extracted-archive suite passes:
  scripting policy, resources, renderer/Kitty/compositor, Inspector, command
  palette, lifecycle, undo/redo, quick terminal, cleanup and refusal tests.
- hidden-drag-search-focus.log: debug/optimized automatic focus positives and
  outer-focus regression negative controls pass.

## VoiceOver selection: now a demonstrated failure, not missing access

Recovered the actual command mapping from the installed ScreenReader config:
Global.selectionContent is VO-F6. The input helper must deliver real modifier
flagsChanged events; flags attached only to an F6 event can reach the PTY instead.

With the corrected chord, a disposable native NSTextView reads `beta, selected`
in VoiceOver's actual caption. Ghostty, with AXSelectedText=beta, instead reports
no selection. Both captions were captured and inspected:
native-completion-07/vo-control-10915.png and vo-selected-10915.png.
Thus the agent can operate this check; it is not a generic human-only task.

Ghostty's selectedRange implementation is byte-identical to official HEAD.
Observed beta range location 22/length 3 is inconsistent with the selected text.
The known cell/UTF16 mapping remains inherited. However, correcting a range and
adding AXSelectedTextRanges in a minimal terminal-like NSView still did not
produce the NSTextView result, so neither is asserted as the sole speech cause.
No broad accessibility redesign or archived snapshot was silently reintroduced.
Ordinary terminal text/focus reading remains verified; selected-text speech fails
on this host and must remain an explicit limitation.

## Cross-window activation classification

upstream-differential.json verifies exact official equality for cross-window
tree insertion and the moveFocus dispatch body. An independent two-window AppKit
probe reproduces the distinction: makeFirstResponder changes the destination
responder but leaves the source key; makeKeyAndOrderFront activates it. This
supports an inherited activation omission rather than this port's drop transport.
It is not an official newer-OS executable comparison. Pointer-focused destination
input and all insertion directions/undo/redo already pass.

## Original UI suite and additional case coverage

Inventory: 28 test methods in eight original UI source files. An isolated Xcode
candidate now compiles all eight files, including a test-only XCUIDevice bridge
for unavailable SDK13 appearance controls (real System Preferences controls).
Current search-focus deltas were copied into the candidate. Product toolchain
and project were not changed for this experiment.

The earlier test-without-building attempt reached Apple's UI automation startup,
which requires local password authentication. The system dialog was cancelled;
no password collection, guessing, automation-mode bypass or security-policy
change. xcode-ui-07/Title.xcresult and title.log record failed initialization,
not a passing or zero-test suite. That authentication boundary is now resolved;
see XCODE-UI-ACCEPTANCE.md for actual executions and per-case results.

Additional foreground native checks, not claimed as XCTest execution:

- native-ui-09: title config and four successive window cascade positions pass.
  An initial external frame mutation invalidated the cascade-anchor expectation;
  the correct test leaves the anchor under app control.
- hidden-release-24: native split tear-off, placement, live PTY, undo/redo/cancel.
  The original fixed-size UI assertion expects full configured width, but official
  newWindow(tree:) explicitly sets current pane bounds. Both fixed/nonfixed runs
  preserve pane size. This source/test disagreement is not hidden as a pass of
  the original full-width assertion.
- theme-ui-23: native light titlebar with dark terminal, dual light theme,
  reload to default dark, forced dark, return to system light, and issue8282
  dark-mode split/reload/new-window scenario. Eight titlebar pixel observations
  pass; key screenshots inspected. Original light setting restored.
- tabs-ui-25: normal/split/zoom/fullscreen/exit/merge tab title, close-button and
  shortcut vertical alignment within one point; equal tab heights. Actual native
  cross-window tab drag changes groups 4+2 to 3+3 with geometry preserved.
- final-ui-26: title/reset-zoom alignment, actual Find autofocus/typing/Escape,
  command palette Escape and keyboard selection/submission pass on final product.

The older restoration/session, quit, IME, keyboard, Shortcuts, quick appearance
and four-direction split tests retain their recorded scopes. The mouse-selection
clipboard test was initially withheld because it clears the user's general
clipboard. It now passes with an in-memory snapshot/restore guard and corrected
Monterey element queries; no claim that all 28 original assertions have passed.

## Distribution trust

Final bundle codesign strict verification and extended archive checks pass.
Read-only spctl assessment rejects this ad-hoc development app on the host
(hidden-drag-trust.log). No quarantine removal, Gatekeeper disable or trust bypass.
This is a real remaining public-distribution gate, not a packaging success.
Clean-machine launch, distributor signing/notarization and immutable source
release identity are not established. The safe manual-update default remains.

## Thirty-minute stability and cleanup

native-completion-08 completes 1,800.07 seconds, 17,489 ANSI/Unicode/DSR cycles,
29,101,696 output bytes, with no five-second acknowledgment deadline failure.
Final ten-minute sampled RSS range is 117,468-119,452 KiB. Desktop tests and builds
ran concurrently. This checks bounded responsiveness/resource stability, not
GPU frame timing or an overnight leak claim. It runs the preceding cb71b89b
artifact; the final drag-only build receives the extended lifecycle/package
checks above, not a falsely relabeled thirty-minute run.

cleanup.json in native-completion-07 verifies original WeType input source,
enabled-source inventory and foreground Magpie PID 57485 restored. Original
light appearance and disabled VoiceOver restored; all disposable apps and
control fixtures exited. Authentication prompts cancelled without credentials.
No user config or clipboard alteration, system toolchain switch, security-policy
relaxation, commit, tag, issue, PR or publishing operation.
