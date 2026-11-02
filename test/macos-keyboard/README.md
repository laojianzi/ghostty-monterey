# macOS keyboard compatibility checks

These tests target the unshifted-codepoint and Command-modifier regressions
fixed in the 1.3.1 Monterey branch and carried forward to 1.4.
They add no test flags, caches, strategy objects, or new interfaces to the app.

## Linux and macOS: executable boundary tests and ablation

```sh
python3 test/macos-keyboard/check.py
python3 test/macos-keyboard/check.py --ablate
```

Requires Python 3 and a Swift compiler. The runner compiles the **production
Swift function bodies** with controlled AppKit/Carbon/GhosttyKit boundaries. It
only substitutes framework imports and the OS availability predicate in temporary
files, so both OS branches execute. This is NOT an AppKit, Carbon, IME, ABI, or
terminal-encoder runtime test. The fixtures model inputs and record forwarded
arguments; they are not evidence of Apple's runtime behavior.

Coverage: all 32 Shift/Control/Option/Command/Caps Lock combinations; key-down
and key-up; control-text recovery including a Command-dependent fixture; failed,
empty, BMP, non-BMP, and multi-scalar translations; original and consumed
modifiers; modifier-only events; committed text and function-key filtering;
per-query dead-key state; no-dead-keys mask; keyboard type and layout refresh;
modern/legacy routing.

Ablation recompiles each one-factor mutant and requires an assertion failure:
replace the unshifted lookup with `charactersIgnoringModifiers`; omit Command;
restore either lossy fallback; omit single-scalar validation; omit the no-dead-keys
mask. Compile errors and crashes are **not** accepted as killed mutants.

To test an older revision without changing the worktree, copy its two source
files from `git show <ref>:<path>` into a temporary directory retaining their
repository paths, then pass `--source-root <directory>` to this runner.

## macOS: actual SDK, C header, and native layout translation

```sh
bash test/macos-keyboard/native-check.sh
```

Requires Xcode command-line tools and a usable current keyboard layout. The
script type-checks unchanged sources against the actual Apple SDK and
`include/ghostty.h`, then runs debug and optimized native boundary executables.
No compiled Ghostty library is needed: only its data types are imported. The
standalone `Ghostty.ghosttyMods` adapter is not a test of that unchanged mapper.

Deployment target is 12.0 and Swift language mode is 5. This does **not** prove
compatibility with Swift 5.7/Xcode 14.1 unless that toolchain is actually selected.
The selected input source is printed; the script does not change system settings.
On macOS 14+, it compares forced-legacy output with independent native AppKit
queries. On 12/13 it never calls the affected API, checks mapping invariants, and
checks the explicit `a` identity when the current input source is ABC or US.
Repeat with ABC/US, Swiss German, Dvorak-QWERTY Command, and a dead-key layout.
Native-reference parity is explicitly reported as not run on pre-14 systems.

Running this suite on macOS 14+ cannot reproduce the macOS 12/13 OS defect
and is not a substitute for the gate below.

## Full-app gate: actual target system

Current scope (2026-11-01): Intel macOS 12 on this machine only, with agent
desktop control authorized. ARM and macOS 13/14 are not gates. Foreground
CGEvent/real-PTY/IME results for the current 1.4 artifact are recorded in
../macos-compatibility/NATIVE-INTERACTION.md; they do not certify every row below.

### Bounded manual byte capture

Inside a terminal of the built Ghostty app under test, run:

```sh
python3 /path/to/ghostty/test/macos-keyboard/capture.py /tmp/ghostty-keys-legacy.jsonl \
  --seconds 20 --protocol legacy --label 'revision; ABC; option-as-alt=false; Ctrl+A-Z'
python3 /path/to/ghostty/test/macos-keyboard/capture.py /tmp/ghostty-keys-kitty.jsonl \
  --seconds 20 --protocol kitty --label 'revision; ABC; option-as-alt=false; press/repeat/release'
```

Replace the paths/label with the actual checkout and tested binary identity.
Use a new output filename for each case. Type only the planned test keys after
the active message; capture stops automatically, so Ctrl+C remains capturable
input rather than the exit key. Kitty mode pushes flags 31 and pops them on
normal exit or handled TERM/INT/HUP. Terminal settings are restored in finally;
SIGKILL, terminal loss or interpreter failure cannot promise cleanup. Legacy
mode sends no protocol change: start it at an ordinary shell prompt without
an enclosing application that already enabled a keyboard protocol.

The JSONL file is created exclusively with mode 0600 and records environment,
timestamps and exact hexadecimal bytes. Treat it as sensitive; never type
passwords, paste secrets or record unrelated activity. It reads only its own
terminal, without hooks, global input, layout changes or permission requests.
Environment metadata is not proof of the binary revision. Read chunks may
split/combine key sequences; a nonempty capture is not a pass verdict. Compare
the reconstructed bytes with the protocol expectations for the labeled keys
and record IME candidate/commit observations separately.

`python3 test/macos-keyboard/capture-check.py` checks the recorder using private
PTYs: exact control/Unicode bytes, Kitty push/pop, timeout/SIGTERM cleanup,
mode restoration, private-file permissions, overwrite and non-TTY refusal.
This is recorder validation, **not** a physical input or PR #3 acceptance test.

Record OS, CPU architecture, Xcode/SDK, layout, tested commit, and raw key output.
Do not mark a row passed merely because a stub or native-boundary test passed.

- Build the complete 1.4 `ReleaseLocal` app with the Zig version pinned in
  `build.zig.zon`; validate Intel on the current test host 12.7.6. Deployment
  12.0 is not an execution claim for that OS version. macOS 13/14 validation
  is not a release requirement for this Monterey-only port.
- In a clean configuration without matching consumed keybindings, capture legacy
  and Kitty protocol output (including alternate keys, report events, and report
  all) using a key inspector, then test `nvim --clean` and the affected TUI.
- Verify Ctrl+A-Z, Shift+A, Ctrl+Shift+C, Ctrl+[, Ctrl+\\, Ctrl+], Ctrl+^,
  Ctrl+_, Ctrl+/, Ctrl+Enter, and Ctrl+Space. Verify repeat and release reports.
- Test ABC/US, Swiss German, Dvorak-QWERTY Command, and dead-key layouts. Include
  Shift+1, Caps Lock, Command-dependent shortcuts, and a live layout change.
- Verify all four option-as-alt settings and Chinese/Japanese/Korean composition,
  candidate confirmation, and cancellation/backspace. Verify no duplicated input.
- Existing macOS 14+ comparison paths are optional diagnostics, not additional
  support promises. Preserve the documented single-scalar identity contract;
  ordinary/committed text must remain unchanged on macOS 12.

Scope: the pre-existing `SurfaceView_AppKit` call used to construct a distinct
modifier-adjusted event is not rewritten by this PR. Its option-as-alt/IME path
is part of the full-app manual gate, not covered by the standalone boundary tests.
