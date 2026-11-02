# Final regression, package and resource verification

2026-11-02. Follow-up to the user's request to verify the first three remaining
items. Scope is this Intel macOS 12.7.6 host and ReleaseLocal; no publishing,
commits, Developer ID signing, notarization or security-policy bypass.

## Regression verdict

- Current-source app-hosted Xcode unit candidate: 284 named passes, six explicitly
  recorded skips, one successful XCTest scaffold. Fresh candidate app/test
  objects use the current core; pinned Testing dependency objects are reused
  explicitly. This is the documented Swift 5.10.1/SDK13 candidate, not the
  ReleaseLocal executable or unchanged upstream Xcode test action.
- Fresh UI candidate: all 28 methods were executed. The consolidated run had
  four failures: two foreground-event failures, one missing screenshot target,
  and the known fixed-width detach expectation (165 versus 328 pixels).
  A subsequent unchanged-code 27-method run passes every method in 166.611s,
  verified independently from xcresult. The fixed-width expectation remains
  excluded with its original failure retained; do not report 28/28.
- Earlier interrupted UI attempts are not passes. Actual system authentication
  allowed XCTest automation without enabling Developer mode. An input-method
  consent dialog interfered with focus and preferences navigation; the native
  controller now identifies that specific dialog and verifies actual appearance
  controls. No expectation was weakened to hide those failures.
- Additional unfiltered `zig build test` did not complete successfully. Despite
  `-Demit-macos-app=false`, its graph also invokes upstream Xcode testing, which
  fails on missing XCUIDevice under SDK13. The core test process was terminated
  after prolonged CPU activity; a sample locates it in the unchanged Screen
  cursorAbsolute capacity test. This is not a complete core-suite pass or proof
  of a product regression. Targeted AccessibilityText testing passes separately
  with `-Demit-xcframework=false` to avoid that unrelated Xcode route.

## Artifact and packaging

The audit found generated resource drift: the prior app's terminfo lacked Smol
and Rmol and used `Se=ESC[2 q`, while the current source generates `ESC[0 q`.
The broad Zig test also created a dummy man-directory placeholder. The latter
was moved to the temporary evidence directory (not removed from tracked source),
and ReleaseLocal was rebuilt against current generated resources. No product
source was changed and no old app resource was copied over the source to force
an assertion to pass.

New executable SHA256:
`8aa1ec74bb987e72cf2ecaa0a0723e2a5942d67614a14be6de779cd7fff195c2`.
The new complete extended extracted-archive suite passes, including exact
resource hashes, PTY/automation policy, Kitty/renderer, Inspector, compositor,
background images, palette, lifecycle and refusal controls. Strict full-app AX
read/write/clear and native rectangle checks also pass on this new artifact.

**A formal release archive is not yet accepted.** The normal packaging command
correctly rejects dirty source metadata: `Release requires a clean source
revision`. No metadata was falsified, no release gate removed, and no commit/tag
created. A development ZIP remains visibly NOT-FOR-RELEASE. To produce a formal
archive, first authorize and freeze a reviewed source revision, then build and
package that revision. Merely renaming the ZIP would not satisfy this gate.

## Resource verification

An initial 30-minute run on the preceding 32de3b76 executable passed: 69,609 DSR
cycles, 231,658,752 bytes, 358 cross-process AX polls, final-15-minute RSS growth
2,612 KiB, and all 30 additional window children reaped. Lifecycle growth from
cycle three to thirty was 3,916 KiB. These numbers are not assigned to the new
artifact. The matched new-artifact run also passes:

| Metric | New 8aa1ec74 artifact |
| --- | --- |
| Continuous workload | 1800.018 seconds, 69,446 cycles, 231,116,288 bytes |
| DSR latency | Median 0.278 ms, p95 1.391 ms, maximum 11.647 ms |
| Final 15-minute RSS | 57,432-60,328 KiB; net growth 2,712 KiB |
| AX reads | 358 successful polls, zero retries; max helper wall time 58.920 ms |
| Window lifecycle | 30/30 child processes reaped |
| Post-close RSS growth, cycle 3 to 30 | 4,740 KiB |

All declared resource criteria pass. Two matched identities are retained rather
than reassigning the first soak's numbers to the rebuilt app.

The declared criteria are unchanged: final-half RSS range below 8 MiB and net
change magnitude below 4 MiB; post-close growth from cycle three below 8 MiB;
exact DSR response within five seconds; every test child reaped. AX snapshots
are polled every five seconds with a two-second bounded retry for transient
cross-process tree discovery, recording retry counts. Initial single-attempt
AX tree failures are retained as failed harness runs, not hidden product passes.
Thirty minutes is a bounded soak, not an overnight/GPU frame-time test or an
indefinite leak-freedom claim. No executable official same-host baseline exists.

## Delivery and cleanup

App: `macos/build/ReleaseLocal/Ghostty.app`.
Development package (not published):
`/tmp/ghostty-monterey/verification-50/package-final/Ghostty-macos12-1.4.0-18457-universal-NOT-FOR-RELEASE.zip`.

Durable logs, parsed unit/UI results, source/artifact identities, package
manifest/checksums, both soak datasets and fixture sources:
`evidence/2026-11-02-final-verification/`. Failure logs remain alongside final
passes. Original source fingerprints are unchanged; only this acceptance report
and index updates are added. No product source fix is attributed to a harness
failure. Temporary native scripts are audit fixtures, not portable entry points.

All fixture apps/children and UI controllers exited. Foreground app, selected
input source, full enabled-source inventory and manual light appearance match
the original state. XCTest temporarily added US and disabled EmojiFunctionRowItem;
those inventory changes were reversed and the exact snapshot compared. Developer
mode remains disabled. No password is retained in files/evidence.
