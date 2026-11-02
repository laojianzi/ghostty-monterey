# Authorized Intel Monterey interaction acceptance

Update: image input became available later on 2026-11-01. The visual follow-up
below supersedes the image-tool limitation for its explicitly inspected images.

Executed 2026-11-01 on Intel macOS 12.7.6 (21H1320). The user authorized
desktop control and explicitly excluded ARM from the required target. Official
1.4 remains the baseline; historical main is not a feature ceiling.

## Artifact and method

- Source: macos/build/ReleaseLocal/Ghostty.app, build 18457.
- Executable SHA256:
  767e290f7c578a9fa487cc33a6062bd78a07a564b0de5600e736782198227170.
- Disposable copied bundle, separate bundle ID/defaults/config, ad-hoc resigned.
  The executable is unchanged. No product source edits were needed in this run.
- Evidence: /tmp/ghostty-monterey/native-interaction-02. The Swift driver is
  /tmp/ghostty-monterey/native-ui.swift; session scripts are alongside it.
- Keyboard and pointer input used foreground CGEvents at the HID event tap,
  not AppleScript send-key commands or direct application callbacks. Input
  sources were selected using Carbon TIS. Native AppKit/IME and actual
  NSDraggingSession/drop routing execute. This is OS-injected interaction,
  **not a claim of physical hardware keystrokes**.
- Three real raw-PTY children logged exact bytes, PID and TTY. AX geometry,
  actual menu actions and scripting surface IDs supplied independent state
  observations. The children remained bounded to 30 minutes and were reaped
  when the disposable app exited.
- Window screenshots were saved, but the image-view tool refused image input.
  No visual-quality or candidate-popup appearance approval is claimed from
  those uninspected images. Text, layout and state verdicts use byte/AX evidence.

## Passing observations

| Scenario | Evidence / observation |
| --- | --- |
| ABC Ctrl A-Z, Shift-A, Ctrl-Shift-C and punctuation/Enter | keyboard-results.json; exact upstream protocol bytes, no swallowed key in this matrix |
| Kitty Ctrl-A press/release, flags 31 | keyboard-results.json; `ESC[97;5u` and `ESC[97;5:3u` |
| Option-E dead key followed by E | keyboard-results.json; one UTF-8 e-acute |
| false/true/left/right option-as-alt, both side flags | option-results.json; all eight cases, e-acute versus ESC-e followed by e; config reload between modes |
| Native simplified Pinyin nihao | ime-results.json; no PTY bytes during preedit, one UTF-8 nihao commit (Chinese characters), backspace/Escape cancels without bytes |
| Search Pinyin composition | search-ime-results.json; preedit, Chinese commit, backspace/cancel preserve committed text; no bytes leak to PTYs |
| Search replacement | search-ime-results.json; Command-A replaces composed text after restoring the select-all binding; actual Select All menu also tested |
| In-window left/right/top/bottom moves | direction-results.json and direction-*.json; actual handle drag, expected relative pane geometry, same live child accepts input, menu undo/redo restores geometry |
| Cross-window move and undo/redo | ax-cross-*.json; stable surface IDs/TTYs, source/destination geometry restored by actual Edit menu |
| Escape during cross-window drag | cancel-before.json / cancel-after.json; identical layout, moved child still accepts pointer-focused input |
| Move last source pane | last-pane-*.json; source window closes, all three surfaces remain, menu undo restores source window, redo closes it again |
| Native fullscreen drag | fullscreen-direction-results.json; 1440x900 fullscreen geometry, left move, live PTY and menu undo/redo |
| Cleanup | cleanup.json; original input source and front application restored, disposable app stopped, all three children reaped |

Assertions poll the settled native state where necessary. Newly restored
windows can appear in AX before their descendant text areas, and menu titles
can update after pane geometry. An early snapshot is not a lost-pane verdict.

## Failures investigated without product patches

1. Initial legacy expectations incorrectly assumed Ctrl A-Z were all C0 bytes.
   Official src/input/key_encode.zig explicitly tests Ctrl-I/M/[ CSI-u behavior
   and Ctrl-Shift-letter differentiation. Ctrl-Enter uses the unchanged
   src/input/function_keys.zig sequence `ESC[27;5;13~`. Expectations were
   corrected against official code, not simply copied from captured output.
2. Ctrl-Space is enabled as symbolic hotkey 60 on this host. Global injection
   invokes the input-source switcher rather than the PTY. Subsequent stale input
   source/preedit caused misleading empty or partial captures. The switcher was
   dismissed and ABC explicitly restored; no global shortcut setting changed.
   App-level Ctrl-Space is not certified by this session.
3. `keybind = clear` intentionally removed menu shortcuts for raw byte capture.
   Command-A therefore appended instead of selecting in Find. The actual Select
   All menu succeeded. Restoring only `super+a=select_all` in the private config
   made the complete search composition/replacement test pass. This follows
   the unchanged upstream MenuShortcutManager behavior, not PR #3.
4. Cross-window undo labels are `Close Terminal` / `Close Window`, not always
   `Move Split`. Official BaseTerminalController has the same nested undo
   naming calls. Real menu undo/redo restores the correct surfaces/windows;
   misleading naming is recorded, not expanded into a new port patch.
5. After the first cross-window drop, unclicked keyboard input remained in the
   surviving source pane. Clicking the moved pane restored input there. This
   run does not certify automatic destination-window activation. Determine the
   intended upstream behavior before calling it a Monterey regression.

## Remaining bounds

This session does not certify all layouts, physical repeat timing, Caps Lock,
Japanese/Korean composition, every cross-window insertion direction, rejected
or self drops, terminal-selection-to-Find reentry, candidate-popup appearance,
VoiceOver speech, system light/dark appearance, Shortcuts UI, or long-duration
performance. Existing lower-level evidence is not silently substituted for
these paths. Prioritize demonstrated port failures rather than treating all
possible upstream behavior as new work.

ARM, macOS 13/14 and a second 12.0 machine are not gates for the user's current
Intel-host acceptance. Runtime evidence is specifically 12.7.6; deployment 12.0
metadata is not evidence of an executed 12.0 run. Public distribution still
needs a fixed source/artifact identity and an explicit trust/install policy.
Temporary logs are not durable release evidence until archived with that build.

## Visual follow-up and search-focus fix (2026-11-01)

Evidence: /tmp/ghostty-monterey/native-visual-03 (old binary),
/tmp/ghostty-monterey/native-visual-fixed-04 (rebuilt binary), and
search-focus-*.log in the parent directory.

- Actually viewed terminal and search Pinyin screenshots: underlined preedit,
  highlighted first Chinese candidate, readable candidate rows positioned below
  the active input. The terminal screenshot crops a small left portion of the
  system candidate popup at the app-window capture boundary; that is not evidence
  of screen clipping. The search-region capture contains the complete popup.
- Viewed a held native drag: the lower half of the destination pane is blue,
  the source snapshot follows the pointer, and the post-drop overlay disappears.
  The resulting split and active cursor are visible. This is one visual direction,
  not a visual approval of every drag configuration.
- Found a real missing acceptance case: opening Find or refocusing it after a
  terminal selection left the terminal as first responder. A typed x went to
  the raw PTY rather than the search field. Prior tests explicitly called
  makeFirstResponder or clicked the field and therefore missed this regression.
- Minimized native SwiftUI comparison: direct TextField succeeds; the selection
  bridge with outer .focused fails; removing just the bridge succeeds; disabling
  its hit testing alone still fails. Binding focus to the actual TextField before
  its representable background succeeds. This is a demonstrated interaction of
  our added selection bridge on Monterey, not PR #3 or an established upstream
  defect. No broader AX, encoder or drag patch is justified by it.
- Small fix: BackportSelectionTextField accepts an optional FocusState binding;
  SurfaceSearchOverlay supplies its existing state at the actual input instead
  of focusing the outer background. The modern branch also receives the binding;
  that compiler-gated branch is not runtime-tested on this host. No replacement
  responder chain, focus timer, global observer or new core API was introduced.
- New search-focus-check.py exercises automatic SwiftUI focus, not direct field
  activation. Debug and optimized positives pass; moving the binding back outside
  fails by the intended focus assertion in both modes. Existing search-state and
  selection suites pass, including composition preservation and negative controls.
- ReleaseLocal rebuild succeeds with executable SHA256
  cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
  This supersedes the earlier executable identity. Build retains existing linker
  warnings; it is not a warning-free release build.
- Actual rebuilt-app foreground test passes: Command-F automatically focuses the
  input; typing stays out of the PTY; terminal beta selection -> Command-E ->
  Command-F -> x replaces the whole search term without a mouse click in Find.
  Pinyin commit/backspace/cancellation still passes with no leaked PTY bytes.
  search-results.json and AX snapshots record the exact outcomes.

At this stage, acceptance was not declared complete: cross-window activation policy,
VoiceOver, appearance transitions, Shortcuts UI and additional IME/layout paths
still have the previously documented bounds. An attempted System Events dark-mode
query did not return a usable result; no appearance setting was changed or passed.
The general clipboard was not accessed. Find operations use the system find
pasteboard by design; the initial observed find string was restored only while
the board still held this session's known marker.

## Subsequent desktop completion

See LOCAL-ACCEPTANCE.md for Shortcuts UI and ordinary-window appearance, and
COMPLETION-ACCEPTANCE.md for four cross-window directions with menu undo/redo,
quick-terminal light/dark, Caps/repeat PTY assertions, a ten-minute workload and
actual VoiceOver reading captions. Japanese/Korean layouts are excluded by user.
Automatic destination activation and VoiceOver selected-text speech are not
passed. Physical repeat timing is distinct from the now-tested repeat events.
Cleanup restored original session and temporary permission changes.
