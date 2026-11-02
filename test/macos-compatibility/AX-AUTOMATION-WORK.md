# AX and automation acceptance

The user reopened AX selection and requested the recommended feature-preserving
AX/automation work on 2026-11-01. This scoped follow-up is complete on this Intel
macOS 12.7.6 host with the new ReleaseLocal below. Earlier AX exclusions are
historical, not the current disposition. ARM, other hosts, Japanese/Korean input,
Developer ID signing and notarization remain outside scope.

## Implementation boundaries

- AccessibilityText.zig owns on-demand text/range mapping, separate from Screen
  and StringMap. Reuses previously tested read-side algorithms and the formatter
  row continuation primitive, not the archived patch wholesale. There are no
  per-frame mapping updates. The current core tests include Unicode, repeated
  text, wide cells, rectangles, scrollback, allocation failure and scaling.
- The C setter accepts expected text plus a UTF-16 range. It holds the terminal
  lock, rejects changed text and ranges not representable as terminal cells,
  and uses the actual selection mutation/notification path. Empty ranges clear
  selection. It never types, moves the shell cursor, or copies to the clipboard.
  A text comparison guards stale content, not a claimed universal generation ID.
- Swift AX uses a separate lazy 500ms cached view, invalidated on selection
  changes. Full/visible scripting reads retain the existing inexpensive readers.
  Input-method selectedRange is unchanged. No no-op setter or fake capability.
- Automation examples use explicit app paths, existing controller commands,
  bounded readiness and the existing AppleScript/TCC policy. No parallel
  terminal controller, legacy Intents extension or screenshot API is added.

## Acceptance coverage

New core/app build; strict full-app AX read/write/invalid-range checks; actual
VoiceOver selection speech; ordinary/rectangular selection and Unicode; scripting
examples and live opt-out; input/IME regression; mapping cost and bounded resource
checks; final source/artifact identities and restored session. Native Shortcut
picker/entity presentation is still not claimed on Monterey.

Initial baseline fails the real cross-process range assertion (109 versus 66
UTF-16 units), with a delivered selection notification. New core module tests
pass 86/86 in the broad filtered run and 78/78 in the setter-filtered run; counts
include the build's additional tests, not 86 distinct AX scenarios. Both debug
and optimized extracted Swift text/caching tests pass. The completed full-app
checks are listed below. Working logs: /tmp/ghostty-monterey/automation-ax48/.

## Verified on new ReleaseLocal

Executable 32de3b76a7cb9a7f986efb100085d9aa992094d145e9e2a30886e33b57c5f62c.
Core universal build 333/333, ReleaseLocal app build succeeds. Strict real
cross-process Select All now reports 66/66 UTF-16 units rather than 109/66.
Real AX setter changes selection, rejects out-of-bounds range without replacing
it, and clears selection. All eight Services scenarios pass with cleanup.
Embedded normal/reversed rectangle gestures reconstruct selected text from AX
ranges; committed-text/composition/control/arrow PTY checks pass. Fifteen
AppleScript recipe assertions pass, including actual child directory, quick
idempotence, policy denial and restore. Initial cwd assertion compared /tmp
with /private/tmp; canonicalizing the fixture comparison fixes it, not product.

12,000-line same-core read-cost probe: no-selection snapshot 4.35ms versus
plain 4.04ms; select-all 15.87ms versus plain 3.84ms; small-selection snapshot
7.86ms versus plain 3.85ms. A small selection-only read remains 0.0033ms and
menus/scripts retain that path. The additional AX mapping cost is explicit,
not a claim of zero overhead. Actual VoiceOver now captions "beta, selected" on the rebuilt real app after
setting a real terminal selection. Screenshot inspected; no synthetic speech.
The complete extended archive suite passes.

Further final checks:

- Full-app native Option-drag selects exactly `23456\nCDEFG\nstuvw`. All three
  disjoint AX ranges reconstruct their expected row through AXValue and
  AXStringForRange. Select All, actual setter/invalid/clear and all eight Services
  checks pass in the same run. This uses explicitly opted-in foreground
  WindowServer routing, not the previously failing PID-posted pointer fixture.
- ABC, WeType and system Pinyin scripting produces exact `aA` bytes. Nine
  modifier cases pass, with no extra release bytes. Actual native WeType and
  Pinyin composition sends no preedit bytes and commits the Chinese character.
- Both Shortcuts-style handlers are compiled and executed with their actual
  `{input, parameters}` contract through osascript. Text returns actual PTY
  output; a quoted/metacharacter directory reaches the child unchanged;
  relative directories are rejected. This is not a rerun of Shortcuts editor
  UI on this artifact. Earlier editor evidence remains identified separately.
- Original foreground app and enabled/selected input sources are restored.
  VoiceOver's native settings checkbox is off and no fixture app remains.
  `voiceOverOnOffKey` is not treated as a reliable enabled-state indicator.

## Reproduce and inspect

Durable evidence: `evidence/2026-11-01-ax-automation/`, including executable and
source identities, build/test logs, the inspected VoiceOver caption image,
session restoration and a checksum manifest. Session-specific scripts retained
there are audit fixtures with recorded paths/PIDs, not portable unattended tools.

```sh
python3 test/macos-compatibility/services-standalone-check.py macos/build/ReleaseLocal/Ghostty.app --accessibility --selection --write-selection
python3 test/macos-compatibility/services-standalone-check.py macos/build/ReleaseLocal/Ghostty.app --accessibility --selection --rectangle --native-rectangle --write-selection
python3 test/macos-compatibility/embedded-selection-check.py --committed-input
python3 test/macos-compatibility/accessibility-text-check.py
python3 test/macos-compatibility/cache-check.py
python3 test/macos-compatibility/script-text-reader-check.py
```

The native rectangle command explicitly requires an unlocked session and existing
AX/event permissions; it activates only its isolated fixture and checks focus
before every pointer event. It restores the pointer/previous foreground app on
normal completion. Do not interact with other windows during that command.

## Deliberate limits

- Monterey cannot load AppIntents or offer native Ghostty AppEntity pickers,
  thumbnails or Intent permission dialogs. AppleScript preserves underlying
  operations, not those APIs. No screenshot automation API or legacy Intent
  extension is added. See AUTOMATION.md for operation coverage and policy.
- AX writes support representable contiguous terminal-cell selections and
  clearing, not partial combining cells, split surrogate pairs, arbitrary
  caret movement or plural-range rectangle writes. Read-side rectangles are
  supported. Invalid/stale requests leave the actual selection unchanged.
- The 500ms lazy AX cache is not an atomic transaction across arbitrary calls
  during terminal output. Exact-text validation guards writes but is not a
  universal screen-generation identity. Visible-range policy still exposes
  full content as upstream does; this does not add viewport geometry mapping.
- Core Screen/StringMap files and the input-method selectedRange implementation
  are unchanged. The new narrow C ABI and formatter continuation are intentional
  AX work, not requirements for compiling on Monterey. The inherited selected
  range defect is not a macOS-12-only bug.
- Earlier 284 unit/27 UI results were not rerun wholesale and are not relabeled
  as tests of this executable. New build, targeted core/Swift tests, live AX/IME,
  automation and the complete extended archive suite cover this follow-up.
