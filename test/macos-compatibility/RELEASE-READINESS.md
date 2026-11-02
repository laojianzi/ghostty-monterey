# Monterey release readiness

The reopened AX selection/automation follow-up is complete. AX-AUTOMATION-WORK.md
records the new artifact-matched acceptance and its explicit limits. Older
feature/unit/UI evidence below retains its original identity, not a blanket rerun.

Updated 2026-11-02. This is the current acceptance index, not a chronological
backlog. READINESS-HISTORY.md preserves the superseded wording and intermediate
results. STATUS.md remains the chronological record.

## Scope and artifact

- Required runtime: this Intel macOS 12.7.6 host. Distribution: ReleaseLocal.
- Excluded by the user: ARM, Japanese/Korean layouts,
  other hosts/OS versions, Developer ID signing and notarization.
- App: `macos/build/ReleaseLocal/Ghostty.app`, 1.4.0/build18457.
- Executable SHA256:
  `8aa1ec74bb987e72cf2ecaa0a0723e2a5942d67614a14be6de779cd7fff195c2`.
- Official baseline: `83fb95624b0439ee660c2679b43b38c8b63769cd`, with dirty
  adaptations. No commit/tag/upload is implied by local acceptance.

The agreed representative local acceptance and follow-up resource/dispatch
checks are complete within the boundaries below. No demonstrated unresolved
in-scope functional blocker is recorded. This does not certify every upstream
feature combination or transform excluded/limited behavior into a pass.

## Latest verification

FINAL-VERIFICATION.md records fresh current-source unit/UI runs, corrected
resource packaging and the rebuilt artifact's 30-minute AX/PTY load plus 30
teardown cycles. Formal release packaging still refuses dirty revision metadata;
only a visibly labeled development archive exists. No commit or publication is
implied. Unfiltered upstream test execution is not green; the compatibility
unit workflow passes and 27/28 UI methods pass with the documented fixed-width
expectation retained. Do not call this an unchanged full-suite pass.

## Current evidence

| Requirement | Latest evidence | Verdict and boundary |
| --- | --- | --- |
| AX selection and automation | AX-AUTOMATION-WORK.md | New full-app UTF-16 read/write/clear, native rectangle, real VoiceOver caption, 15 dispatcher assertions and two recipe handlers pass. Native AppIntents UI is not restored. |
| Build and package | AX-AUTOMATION-WORK.md; new matching build/package logs | ReleaseLocal build and extended extracted-archive suite pass. No trusted/notarized-download claim. |
| Keyboard and IME | AX-AUTOMATION-WORK.md; INPUT-ACCEPTANCE.md | ABC/WeType/Pinyin exact script bytes and native Chinese preedit/commit pass. Keyboard boundary/native regressions pass. |
| Focus, search, drag | FOCUS-ACCEPTANCE.md, INPUT-ACCEPTANCE.md, native interaction reports | Destination keyboard focus, undo/redo, cancel, hidden-titlebar drag and search native IME paths pass. Earlier wrong-window/Find failures are superseded, not current blockers. |
| Unit and UI tests | FINAL-VERIFICATION.md | Fresh current-source candidate: 284 named unit passes, six documented skips; 27 selected UI methods pass in the isolated Xcode candidate. Not unchanged 28/28, not every test running on the ReleaseLocal binary. |
| Secure Input, progress, visual Bell | NONAX-ACCEPTANCE.md | Real PTY state, menu/lifetime, progress states/expiry/disable and visual Bell pass. |
| Native notifications | NONAX-ACCEPTANCE.md | Original unmodified ReleaseLocal delivers desktop/success/failure notifications, click-to-focus and cleanup pass. Private bundle authorization rejection is retained as a fixture limitation. |
| SSH | NONAX-ACCEPTANCE.md | Eight boundary and five actual loopback transport cases pass, including terminfo compilation/cache/fallback. Not a remote-server compatibility matrix. |
| Resource and remaining Bell checks | RESOURCE-ACCEPTANCE.md | Eight-minute bounded-history workload and ten teardown cycles pass their declared RSS/response criteria; five instrumented Bell dispatch/config controls pass. Not acoustic/Dock-animation or official performance parity proof. |
| Minimum patch cost | PATCH-SCOPE.md | Archived broad AX patch remains separate; new isolated on-demand AX module added by explicit request, without changing Screen/StringMap. Narrow compatibility/focus/input changes retained. Search bridge retained with native comparison and full-app input evidence, not claimed as a compilation requirement. |
| Updates | UPDATES.md and package checks | Safe manual-update default; no configured distributor update service. Enabling one is a separate validation task, not an outstanding local acceptance gate. |

## Known limitations, not disguised passes

- AX now has mapped UTF-16 selection ranges and a real setter. It retains a
  500ms lazy snapshot, full-content visible-range policy, and terminal-cell
  representability limits. It does not promise arbitrary caret/sub-cell writes,
  plural-range writes or atomicity across concurrent output. See AX-AUTOMATION-WORK.md.
- Fixed-width detached-pane behavior matches official implementation. One
  original UI expectation conflicts with that behavior and remains failed.
- AppIntents is unavailable on Monterey; AppleScript alternatives do not supply
  full Shortcuts entity/UI/policy parity. See AUTOMATION.md.
- Six unit skips and candidate-only toolchain adaptations remain explicit.
  The XCTest scaffold does not provide per-case Xcode reporting for every
  Swift Testing case; do not confuse that with tests not executing.
- No executable official v1.4 same-host performance baseline exists here.
  Bounded resource/response observations cannot prove GPU frame-time parity,
  every configuration combination, indefinite uptime or absence of all leaks.
- SSH remote system tic 5.7 rejects upstream's stdin syntax; fallback works.
  Explicit remote-command installation is not covered as a successful path.
- Ad-hoc Gatekeeper rejection remains a distribution characteristic. Do not
  disable security controls or request signing credentials to close this scope.

## Evidence precedence and repeatability

Use AX-AUTOMATION-WORK.md for the current artifact and changed paths.
INPUT-ACCEPTANCE.md, NONAX-ACCEPTANCE.md and RESOURCE-ACCEPTANCE.md retain earlier
artifact-specific coverage; they are not silently relabeled as current reruns. Older failures only close when
later evidence covers that same behavior. MANUAL-ACCEPTANCE.md is a historical
scenario inventory, not a demand that the user repeat already completed checks.

BUILDING.md documents the build; TEST-TOOLCHAIN.md and macos/test-monterey.py
provide the unit workflow. Native session scripts and coordinates are audit
fixtures, not unattended portable entry points. EVIDENCE-INDEX.md identifies
retained build/test logs, checksums, reproduction boundaries and negative controls.

The complete archive suite was rerun after the AX product change and passes.
The artifact was rebuilt on 2026-11-02 to resolve generated-resource drift;
FINAL-VERIFICATION.md records the new matched tests. Committing, packaging for publication and uploading are separate
operations, not implicit requirements to finish local acceptance.
