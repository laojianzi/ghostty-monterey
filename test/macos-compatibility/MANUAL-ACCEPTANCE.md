# Monterey release acceptance handoff

Historical scenario inventory: use RELEASE-READINESS.md for current scope and
artifact identity. NONAX-ACCEPTANCE.md and RESOURCE-ACCEPTANCE.md supersede the
remaining non-selection follow-ups. AX selection is excluded by the user, not
fixed. No human-only acceptance step is implied by the older rows below.

Latest disposition: INPUT-ACCEPTANCE.md fixes IME-selected synthetic keys,
records current ReleaseLocal/UI/unit results, and classifies fixed-width sizing
as an inherited source/test disagreement. VoiceOver selected speech is still a
product limitation; no human action or signing credential is being requested.

Current disposition: FOCUS-ACCEPTANCE.md, REMAINING-VERIFICATION.md and XCODE-UI-ACCEPTANCE.md
supersede the historical missing-access/compiler statements below. The agent
executes real XCTest UI tests: 27 selected methods pass with documented
test-only adaptations; one original fixed-width expectation disagrees with
official pane sizing. Automatic drop activation is now fixed and native-tested;
VoiceOver selection remains a demonstrated failure, not a task awaiting a human
operator. The current artifact identity is in INPUT-ACCEPTANCE.md. The user chooses
ReleaseLocal-only distribution and excludes app signing/notarization. Public
trust is not an acceptance gate; artifact/evidence matching remains necessary.

Status: **partially executed by the agent with authorized desktop control**.
See NATIVE-INTERACTION.md for the exact passing scenarios and limitations.
The rows below are the original checklist, not a blanket passing test report.
Only macOS 12 is required. Do not add macOS 13/14 runs as release gates.
Only Intel on the current machine is required; ARM is explicitly out of scope.
Japanese/Korean layouts are excluded by the user's latest clarification.
See COMPLETION-ACCEPTANCE.md for additional agent-executed checks and remaining
evidence boundaries; this filename does not imply a required human handoff.
Use official 1.4 behavior as the feature baseline, not the older fork's main.

## Identify the artifact first

The later automatic-search-focus rebuild supersedes the identity below:
executable SHA256 cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
See NATIVE-INTERACTION.md's visual follow-up and search-focus-package.log for
matched new-artifact evidence; the original identity remains historical.

Current local artifact inspected on 2026-11-01:

- macos/build/ReleaseLocal/Ghostty.app
- Version 1.4.0, build 18457, revision
  83fb95624b0439ee660c2679b43b38c8b63769cd-dirty
- Main executable SHA256:
  767e290f7c578a9fa487cc33a6062bd78a07a564b0de5600e736782198227170
- Universal x86_64/arm64, deployment 12.0; ad-hoc signature, no TeamIdentifier.
- Existing execution evidence is Intel macOS 12.7.6 only.

This is a development artifact, not a public release candidate. Recalculate the
hash after rebuilding; a report for a different binary cannot close these rows.
Record the test date, OS/build, architecture, executable hash, config, input
source, expected result, actual result, and evidence path for every session.
Do not record secrets or unrelated terminal content.

The temporary evidence directory is /tmp/ghostty-monterey. Latest current-app
archive acceptance is current-release-package-20261101.log/.json; candidate
unit evidence is core-provenance-hosted-01/result.json. These describe different
binaries and are not interchangeable. Preserve logs with an eventual fixed
release identity before publishing; /tmp is not durable release storage.

## First local session: physical input and drag

Use a disposable config and test terminals with no valuable running jobs. The
agent may launch/activate the isolated app and temporarily change input sources,
restoring the original session afterward. Do
not overwrite normal config, change permissions, or disable Gatekeeper as part
of an automated test. Consult NATIVE-INTERACTION.md for rows now partly or fully
executed; do not infer completion of an entire matrix from a single scenario.

| Test | Action | Required observation |
| --- | --- | --- |
| Ctrl path / PR #3 | Use capture.py inside the tested app, ABC/US, legacy and Kitty modes; follow ../macos-keyboard/README.md | Exact planned control bytes / Kitty events, no swallowed keys; record repeats/releases separately |
| Native composition | Compose and commit Chinese, Japanese and Korean text; cancel composition and backspace through preedit | Correct candidate UI, no premature committed bytes, no duplicate commit, cancelled text absent |
| Option/layout semantics | Repeat the keyboard matrix for false/true/left/right option-as-alt, dead keys and Command-sensitive layout | Expected character/shortcut behavior and unchanged ordinary text; no inferred pass from the Carbon boundary tests |
| Search composition | Open Find, enter composed text, select a different terminal word and invoke Find again, replace selection | Search text and caret/selection agree; replacement does not append accidentally; composition is not cancelled or overwritten |
| In-window move | Create two splits; drag the actual top grab handle toward each edge of the other pane | Correct overlay and insertion direction, one copy of each surface, no lost child or input; terminal receives typing afterward |
| Cross-window move | Move a split between windows, including moving the final pane out of its source window | Correct destination tree and source-window lifecycle; no orphan/duplicate pane; process remains responsive |
| Cancel/self drop | Cancel an active drag with Escape; return to the source pane; test a rejected drop | No lost/duplicated surface, overlay clears, normal focus/input resumes |
| Drag undo/redo | Use the actual Edit menu after same/cross-window moves | Correct pane placement and window restoration, correct focused terminal, same running job, redo reverses undo |
| Fullscreen drag | Repeat one split move in native fullscreen and check grab-handle reveal | Handle remains usable, overlay coordinates match panes, no stuck drag state |

For a persistent disposable job, run the following in each pane and note its
PID/TTY before moving it. It reads only that terminal and creates no files:

```sh
/usr/bin/perl -MPOSIX=ttyname -e '$|=1; print "pid=$$ tty=",ttyname(0),"\n"; while (<STDIN>) { print "pid=$$ echo=$_"; last if /^quit$/ }'
```

Type a unique marker after each move/undo/redo and compare the returned PID.
Use `quit` to finish. This is a manual continuity aid, not a replacement for
physical gesture observations or byte-level keyboard capture.

Do not call controller-level tests a drag acceptance pass. They verify actual
tree mutations and a live PTY, but bypass NSDraggingSession/SwiftUI DropInfo,
pointer hit testing and menu/focus routing. Tests currently pass at that lower
level. The new foreground-event runs exercise actual drag routing; they are
not physical-device tests or visual approval of every overlay state.

## Remaining local acceptance

- VoiceOver: reviewer-controlled navigation through terminal/window/split UI,
  reading and selection announcements, and return of keyboard focus. Record
  inherited AX range defects separately (PATCH-SCOPE.md); this port does not
  claim to repair the upstream cell-offset range mapping.
- Themes: system light/dark transition, explicit window-theme overrides, config
  reload, and quick-terminal appearance. The original Xcode UI suite cannot
  currently compile its XCUIDevice.Appearance calls with SDK 13. A manually
  observed transition is useful evidence, not a claim that the suite passed.
- Shortcuts: reviewer executes a disposable Run AppleScript shortcut against
  the tested app with macos-applescript enabled, then disabled. Follow
  AUTOMATION.md's operation/policy limits; do not imply App Intents UI parity.
- Soak/performance: agree on a representative workload and duration, record
  terminal size/config and idle/active CPU, memory and visible frame pacing.
  Existing bounded PTY throughput and lifecycle checks do not establish a
  long-duration baseline. A historical 1.3.1 run is not official 1.4 equivalence.

## Distribution gates and evidence limits

| Gate | Needed evidence | Current state |
| --- | --- | --- |
| Apple Silicon macOS 12 | Not required by the user's updated scope | Extra slice is not a tested-support claim or release gate |
| Earliest deployment 12.0 | Not a second-machine gate for current-host acceptance | No 12.0 execution claim; validated host is 12.7.6 |
| Developer ID / notarization / Gatekeeper trust | Outside the user's ReleaseLocal verification scope | Not a blocker; no notarization, trusted-download or security-bypass claim |
| Source/artifact identity | Record source state, final build/hash, packaged output and durable matched reports | Worktree remains dirty; a commit/tag/upload is separate from acceptance |
| Updates | Owner chooses manual-only distribution or supplies owned feed/key and tests UPDATES.md's signed cycle | Safe manual-only default; automatic update service is not configured |

Do not lower the declared target, remove product features, generate publisher
keys or publish artifacts merely to clear these gates. Those are owner decisions,
not implicit consequences of missing access. A manually signed-off development
build still needs matching final-artifact evidence after a release rebuild.

## Report format

Use one entry per scenario, with **pass**, **fail** or **not run** (never infer
pass from lack of a crash):

```text
Date / reviewer:
OS build / architecture:
App executable SHA256:
Scenario / config / input source:
Steps and expected outcome:
Observed outcome:
Verdict:
Evidence files (redacted if needed):
```

No row in this document is certified by creating the checklist. Failures should
be reproduced narrowly and classified as port regressions, inherited defects,
tooling limitations or environment problems before adding product patches.
