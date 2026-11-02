# Monterey automation

Keep the upstream AppleScript dictionary and Services implementation. Do not
introduce a parallel terminal controller or a legacy Intents extension merely
to reproduce operations already exposed through AppleScript.

## Ready-to-adapt recipes

`automation-examples/` contains a CLI operation dispatcher and two Shortcuts
Run AppleScript handlers. They use the existing dictionary and explicit bundle
paths, not a new terminal manager. The dispatcher covers list/readiness,
window/tab/split creation, exact-ID focus/close, text reads, binding actions and
idempotent quick terminal. The readiness loop is bounded; directory arguments
remain structured data. See its README for compilation, permission and parent
selection semantics. No screenshot/entity-picker parity is claimed.

## Available route and limits

The built-in App Intents actions are not available on macOS 12. The current
upstream implementation requires macOS 15; Monterey also lacks the AppIntents
framework itself. Compiler guards preserve that source without trying to load
it on this target. They do not restore discoverable Ghostty actions in Shortcuts.

Monterey's Shortcuts has a Run AppleScript action that can call Ghostty's
dictionary. This is an alternative automation route, not an App Intents API
replacement: existing shortcuts using those actions need to be rewritten.
The 2026-11-01 unlocked-session test now executes a disposable Run AppleScript
action in the actual Shortcuts editor: visible text returns with scripting on,
and access fails after Ghostty scripting is disabled. Initial Shortcuts script
execution refusal and temporary enable/restore are also verified. See
LOCAL-ACCEPTANCE.md. No pre-existing user shortcuts were executed or edited.
This does not establish every first-run Automation-consent combination.

AppleScript uses `macos-applescript` and macOS Automation permissions, **not**
the App Intents `macos-shortcuts` ask/allow/deny setting. Setting
`macos-shortcuts = deny` does not disable AppleScript. Set
`macos-applescript = false` to disable the dictionary. Do not describe the
bridge as preserving the App Intents permission dialog or policy.

### Operation coverage, not API parity

| Official operation | Monterey scripting route | Remaining difference |
| --- | --- | --- |
| New window/tab/split | Configuration record and creation commands | Caller supplies parent, directory handling, environment and initial input; no entity picker |
| Focus/close terminal | `focus` / `close` | No App Intents entity discovery |
| Text/key/mouse input | Existing input and mouse commands | AppleScript/TCC policy, not Shortcuts permission policy |
| Perform binding / chosen palette action | `perform action` | No dynamic command entity chooser; opening the palette is a different operation |
| Title/working directory | Terminal properties | Text values, not App Intents entities |
| Full contents/visible text/selected text | Read-only terminal properties | Added below; no formatting and no automatic rewrite of existing shortcuts |
| Open quick terminal | `open quick terminal` | Idempotently shows the existing controller and returns live terminal references; no entity screenshot or wait for initial metadata |

Monterey lacks the framework, not the ability to read terminal text. The three
text properties reuse the existing in-process readers used by terminal details
and accessibility. They do not add a cache, controller, C API or AX permission
requirement. Empty/no-selection or unavailable surfaces return empty text;
full/visible reads have the existing cache's refresh semantics rather than an atomic snapshot
across separate Apple events. All accessors check `macos-applescript`.

```applescript
tell application "Ghostty"
    set t to focused terminal of selected tab of front window
    return visible text of t
end tell
```

For scrollback or selection, use `full contents of t` or `selected text of t`.
Terminal output can contain credentials or untrusted instructions; callers must
handle it as data. These additions do not claim to restore Shortcuts UI actions
or their permission prompts. The separately requested AX implementation is
accepted in AX-AUTOMATION-WORK.md; scripting does not depend on its mapping cache.

Selected-text automation calls the existing selection-only reader, not the AX
snapshot cache. Reading a small selection therefore does not also serialize
scrollback solely for that request. The full/visible text properties retain
their existing cache behavior; separate reads are not an atomic snapshot.
`script-text-reader-check.py` compiles the exact property bodies with reader
counters, checking routing, disabled access and weak-reference expiry in both
Swift optimization modes. Compiled policy-bypass and snapshot-reader mutants
must fail; actual C/PTY behavior is covered by the full-app probe below.

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --automation-text --automation-policy
```

The text probe emits 300 lines from a real child PTY and distinguishes scrollback
from the current viewport, checks Unicode in a full selection, then clears it.
It uses no AX calls, clipboard access or global input. The policy probe also
requires text-property queries against the original ID to fail after disabling
scripting; object lookup can reject them before accessor dispatch.

`open quick terminal` reuses QuickTerminalIntent's `animateIn()` operation,
not the toggle binding. Repeated calls leave an already-open quick terminal
visible and return all its split surfaces. The original toggle binding remains
unchanged. As with existing AppleScript creation commands, returned references
are live: initial title/cwd/child metadata may still be initializing. Unlike the
Intent's first-open entity construction, the command does not await metadata
or create screenshots. Callers needing those properties should retry reads
with a bounded deadline.

```applescript
tell application "Ghostty"
    set quickTerminals to open quick terminal
    return id of item 1 of quickTerminals
end tell
```

The standard app smoke checks first/repeated open, split reference enumeration,
hide/reopen identity and the unchanged toggle binding. The scripting opt-out
probe requires this command to return the explicit disabled-policy error before
creating a quick terminal.

For a Run AppleScript action, this example opens a terminal in the home
directory and runs a fixed command through the configured shell:

```applescript
on run {input, parameters}
    tell application "Ghostty"
        set settings to new surface configuration
        set initial working directory of settings to POSIX path of (path to home folder)
        set environment variables of settings to {"MONTEREY_AUTOMATION=1"}
        set initial input of settings to "pwd" & linefeed
        new window with configuration settings
    end tell
    return input
end run
```

Use `initial input` for commands that should run inside the configured shell;
`command` instead overrides the process being launched. Upstream New Terminal
Intent appends `; exit` and a newline to its command input. The example above
deliberately leaves the shell open. Do not concatenate untrusted Shortcut input
as shell code; shell arguments need appropriate quoting.

## Live scripting opt-out

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --automation-policy
```

The isolated app starts with one live terminal. The probe changes only its test
config to macos-applescript=false and invokes Ghostty's existing SIGUSR2 reload
handler. Window/terminal enumeration must become empty; new window and new
surface configuration must report the explicit disabled-policy error (-1743).
Input, action and close attempts against the previous terminal ID must also
fail (object lookup can deny them before handler dispatch).

The probe restores the config in finally and reloads without relying on scripting
while it is disabled. The same terminal PID and PTY must return, with no extra
tab/window, and must execute a fresh shell command. This passes on the current
host (`automation-policy.log`). No TCC or macos-shortcuts permission is changed;
this tests Ghostty's runtime policy, not macOS consent prompts or Shortcuts UI.

## Verified scope

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --automation
```

The optional probe uses the smoke harness's isolated bundle, preferences and
configuration. It copies a surface configuration record, changes the copy,
and checks that the original is unchanged. Window, tab and split creation
each launch a real child that checks its working directory, environment values
(including spaces, quotes, equals signs, backslashes and an empty value) and
PTY. A second command proves that the shell remains usable after initial input.
Closing each test surface must preserve the original terminal identity and
restore the window/tab/split counts.

This verifies Apple events and actual child-process behavior on Intel Monterey,
not Shortcuts UI execution, login-shell startup files, Services invocation,
all scripting commands, or Apple Silicon runtime. The fixture explicitly uses
`/bin/sh` without shell integration for deterministic isolation.

## Services provider checks

```sh
python3 test/macos-compatibility/services-check.py
```

This compiles the unchanged upstream Services provider and production URL
helper against native AppKit pasteboards and real temporary files. Only app
and terminal construction are replaced with call recorders. It checks legacy
Finder filename lists, modern file URLs, files versus directories, directory
deduplication, slashless directory URIs, root, parent routing and error paths.
The no-resource-lookup mutant must fail. The source Info.plist declarations and
runtime Objective-C service selectors are also checked.

This is not Finder menu discovery or a cross-process NSPerformService test.
In particular, Monterey AppKit does not turn a bare text path or file URI in a
string-only pasteboard into NSURL objects for this provider. The current
provider rejects both, despite the upstream Services declaration advertising
plain text with FilePath context. The cross-process check described below now
confirms that native Services mediation handles plain-text file/directory paths
on this host; the direct-provider result alone would have incorrectly suggested
a need for new parsing logic in the product.

Experimental cross-process probe (currently fails its discovery precondition
on this host):

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --services
```

The isolated copy has unique service menu names. The probe registers that copy,
refreshes the Services inventory and refuses to invoke anything unless both
names appear. It unregisters the copy in `finally`. It does not enable disabled
user services, flush registration databases, or invoke installed Ghostty.
The current Services inventory selects an older temporary copy with the same
smoke bundle identifier, even after registering the new path. A unique bundle
identifier instead encountered an AppleScript consent/startup timeout in the
locked session; it is not enabled by this harness. Cross-process service/PTY
assertions in that shared-ID fixture therefore remain unverified. The emitted inventory is authoritative
discovery evidence, not a failure inside ServiceProvider.

An unlocked-session rerun on 2026-10-30 reproduces the same discovery failure
(`services-unlocked-current.log`). Giving only the disposable test copy a higher
build number also fails (`services-version-probe.log`). Session lock alone does
not explain the inventory choice. Neither run invokes an unintended service;
do not fix this fixture by resetting user registration or permission databases.

## Isolated cross-process Services

```sh
python3 test/macos-compatibility/services-standalone-check.py macos/build/ReleaseLocal/Ghostty.app
python3 test/macos-compatibility/services-standalone-check.py macos/build/ReleaseLocal/Ghostty.app --accessibility
```

This fixture uses a unique temporary bundle identifier and unique service names,
so older smoke copies cannot win discovery. It disables AppleScript in the test
configuration and uses actual terminal child processes to report cwd and PTY
state, avoiding an unrelated Automation consent dependency. No product source
or Services declarations are changed, except test-only menu names and bundle
identity. The signed source bundle is not modified.

Eight cases cover both openTab/openWindow selectors, filename-list/plain-text
pasteboards, and directory/file inputs (including spaces and quotes). Each must
create exactly one new real terminal child in the expected directory; file
inputs must use their parent. Named pasteboards are released, the app is
terminated and unregistered in cleanup, and reporting children must have exited.
No general clipboard writes, consent changes or service-enablement changes are
performed. Artifact logs are retained in the printed temporary directory.

The current Intel Monterey run passes all eight cases
(`services-standalone-final.log`). WindowServer checks now additionally require
tab calls to retain one visible app window and window calls to increment that
count (`services-window-count.log`). A disposable plist mutant routing the tab
service to openWindow fails this check (`services-wrong-selector.log`).

The optional accessibility mode requires existing permission and never prompts
or changes it. It queries AXWindows explicitly, then checks window counts, the
single tab group's growing tab count, one selected tab, and the expected marker
from the focused terminal's AXTextArea value. The marker is printed by each real
child and contains its working directory. This passes all eight service cases
(`services-accessibility-check.log`), establishing read-only cross-process AX
tree/text access as well as service grouping/focus on this host. It does not
verify AX actions, notifications, VoiceOver navigation or selected-text ranges.

The marker now includes emoji and a combining mark. Accessibility mode also
requires AXNumberOfCharacters and AXVisibleCharacterRange to use UTF-16 units
and AXStringForRange to reproduce the complete displayed text. This exposed an
inherited String.count mismatch; the two production count/range expressions now
use utf16.count. The rebuilt app passes (`accessibility-unicode-green.log`).
`python3 test/macos-compatibility/accessibility-text-check.py` supplies focused
native-reference and compiled-mutant regression checks for the same methods.
The marker also includes a second line. AXLineForIndex is checked on both sides
of that newline using UTF-16 offsets; the production prefix operation now uses
UTF-16 rather than grapheme counts (`ax-line-app-red.log`,
`ax-line-app-green.log`). These line queries do not validate selection offsets
or screen-reader navigation.

These checks do not establish Finder menu presentation, every text path syntax,
physical interaction, or arm64 execution. The older `--services`
smoke option still fails its shared-ID discovery gate and is not silently waived.

### Current AX acceptance

AX-AUTOMATION-WORK.md records the reopened work and new artifact. Strict Select
All, real range writes/invalid/clear, native Option-drag rectangles, and actual
VoiceOver selected-text captions now pass. Use `--write-selection` for setter
checks and `--rectangle --native-rectangle` for the explicitly opted-in foreground
pointer route. The old PID-posted rectangle routing failure is not silently
relabeled as a pass. Text reading, Services and input/IME regressions also pass.

### Historical selection diagnostic (superseded)

```sh
python3 test/macos-compatibility/services-standalone-check.py macos/build/ReleaseLocal/Ghostty.app --accessibility --selection
```

This additionally invokes the isolated app's English-language Select All menu
through AX and observes its selected-text-change notification. Copy-on-select
and clipboard access are disabled explicitly. The original run delivered the
action/notification and correct selected text, but failed because the reported
selection range uses terminal cell offsets, not offsets into AXValue
(`ax-selection-repro.log`). The ASCII-only diagnostic also fails. Do not treat
the read-only suite's pass as selection correctness, or "repair" the location by
matching the first occurrence of selected text. Full mapping and regression
coverage were required at that point. The optional snapshot experiment passed
those assertions, but the user chose to separate it from the minimum Monterey
port. Its implementation and original tests are archived under optional-ax/.
The current product again inherits the upstream selected-range defect; that
strict diagnostic is not an acceptance pass. Text reading, UTF-16 counts and
input/gesture checks remain active. This defect is not macOS-12-specific.
Physical rectangular selection, VoiceOver operation and all AX semantics are
not proven by Select All. The experimental --rectangle PID-posted pointer test
still fails at native window routing and must not be reported as passing.
The test does not prompt for or alter AX permission.
