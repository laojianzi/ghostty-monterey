# Input-source and remaining acceptance follow-up

2026-11-01, Intel macOS 12.7.6. ReleaseLocal executable:
c456ff946ec0242a7dd961170415844fbc40cf874d8c45ab77cb16228bb98ac7

The app remains macos/build/ReleaseLocal/Ghostty.app, version 1.4.0/build18457,
official HEAD 83fb95624b0439ee660c2679b43b38c8b63769cd with dirty adaptations.
Signing/notarization, ARM, other machines and Japanese/Korean layouts remain
excluded. No commit, installation, upload or security-policy change occurred.

## IME-selected script keys: real product failure fixed

The earlier 17 unit issues were not just an ABC-dependent test assumption.
On previous ReleaseLocal 583e90ea, an isolated raw PTY receives `aA` from
AppleScript send key under ABC, but receives no bytes under either WeType or
system Pinyin. The script calls return success. This provides a full-app red
signal separate from the unit tests and ordinary physical-event IME input.

An independent production-helper probe shows the synthetic NSEvent AppKit
translation returning nil while the existing Carbon underlying-layout helper
returns the expected letters/modifiers. The original character helper is
unchanged from official 1.4 before this fix. This is not a demonstrated
macOS-12-only failure and is not PR #3's mutation of a real input event.

KeyboardLayout.character now preserves the original AppKit result when present
and falls back to the existing stateless layout translator only on nil. It does
not switch input sources, feed a synthetic event through an IME, change real
NSEvent routing or add a new cache/API. Its existing single-character guard
still rejects invalid keys and multi-character results.

The first expanded helper test incorrectly required US punctuation from system
Pinyin. AppKit can legitimately supply full-width punctuation there. The final
test requires exact ASCII letters/Shift letters across these sources, exact
punctuation under ABC, nonnil other translations and preservation of available
AppKit results. This revised test still fails against the pre-fix source and
passes current production code in debug and optimized builds. No product change
was made to force Chinese punctuation into ASCII.

## Matched results

| Check | Result |
| --- | --- |
| New ReleaseLocal build | Pass with existing system Swift 5.7/Xcode14.1 |
| Actual send key under ABC, WeType, system Pinyin | All receive exactly `6141` (`aA`) |
| Control, Shift, Option and release under all three sources | Exact `01`, `41`, `c3a5`; release adds no bytes; input source unchanged |
| Actual native WeType and system Pinyin composition | `ni` preedit sends no bytes; Space commits exactly `e4bda0` (Chinese ni) to the PTY |
| Current-source Xcode unit candidate with WeType selected | 284 named passes, six existing skips, exit0; previously failed 17 issues no longer reproduce |
| Current UI candidate | 27 selected methods pass, zero failures, 164.444 seconds; independently parsed xcresult |
| Keyboard routing boundary / six mutants | 402 production checks pass; all six mutations rejected |
| Native SDK/header keyboard checks | 454 checks pass in each optimization mode on ABC |
| Extended extracted-archive suite | Pass, including resources, scripting policy/text, clipboard protocol, renderer/Kitty/compositor, Inspector, palette and lifecycle |
| Changed helper strict SwiftLint / diff whitespace | Pass; preexisting linter configuration/deprecation warnings remain |

The unit and UI candidates are separate binaries from ReleaseLocal. They
contain this helper change plus their previously documented compiler/test
adaptations; no test assertion was weakened to get the unit pass. The unit
candidate reuses the previously built current-source candidate, pinned Testing
objects and verified core. Source/hash evidence identifies the changed helper.

The initial UI rerun was interrupted after the external appearance controller
failed to navigate to a control (exit75). The repeat controller polls for the
actual appearance checkbox and verifies its selected state instead of assuming
fixed navigation delays. All 27 pass; the interrupted run is retained, not
counted. The fixed-width original test remains excluded as described below.

Repository regression command:
`python3 test/macos-compatibility/keyboard-layout-input-source-check.py`

This temporarily selects already-enabled ABC/WeType/system Pinyin and restores
the original source. It does not enable sources or type into personal apps.
The native full-app probes and compact results are preserved in
evidence/2026-11-01-input; scripts with temporary paths are audit artifacts,
not portable unattended runners. Full build/XCTest logs remain under
/tmp/ghostty-monterey with hashes in the evidence manifest.

## Fixed-width detachment disposition

Rechecked official source and the original test. The tree-size/setContentSize
block is byte-identical to official 1.4 and deliberately uses the moved pane's
bounds. The original test instead expects the parent window's configured width.
This is an inherited source/test disagreement, not an unexecuted manual check.

On the current ReleaseLocal, actual hidden-titlebar drags with and without fixed
size both create a 165x350 window at the requested 800,180 position, matching the
pane rather than the 328-wide parent. Live input, actual Edit undo/redo and Escape
cancellation pass. Preserve that official behavior under the minimum-port scope;
do not enlarge detached panes or edit the original assertion just for 28/28.
Compatibility behavior is verified; the original assertion remains failed.

## VoiceOver selected speech: narrower diagnosis, unresolved product result

The same NSView control binary now toggles only permission for
setAccessibilitySelectedTextRange through isAccessibilitySelectorAllowed.
Both runs retain exactly the same selected text/ranges and setter implementation.

- Read-only: VoiceOver queries writability=false and captions no selection.
- Writable: writability=true and VoiceOver captions beta/selected.
- Neither run logs a setter invocation for VO-F6 itself.

Both actual captions were captured and inspected. This isolates advertised AX
range writability as the speech gate in this control. Merely correcting getter
ranges or notifications cannot change this control's result. It does not prove
that a dishonest writable flag is safe or repair Ghostty's inherited range
mapping. The diagnostic setter remains a no-op and MUST NOT enter product code.

A correct product solution needs an actual selection-mutation contract and
consistent text/range mapping, or another documented read-only speech path.
The current embedder has no UTF-16 selection setter. No broad AX snapshot was
restored, no setter capability was fabricated, and Ghostty selected-text speech
is still not passed. Ordinary terminal text reading retains its prior pass.

## Cleanup

Private apps/children, UI controllers, test hosts and VoiceOver controls stopped.
VoiceOver is off, light appearance verified, test-opened System Preferences
closed. Foreground iTerm, WeType and complete enabled-source inventory match the
initial snapshot. The original EmojiFunctionRowItem was restored after XCTest.
Clipboard guards restore contents without logging them. Earlier performance
soaks and cross-window-specific evidence retain their original binary identities;
they are not relabelled as runs of this new build.
