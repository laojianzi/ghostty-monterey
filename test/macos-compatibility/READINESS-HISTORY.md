# Historical readiness notes

Archived on 2026-11-01. This preserves earlier observations and decisions
verbatim; references to current artifacts or remaining gates are historical.
Use RELEASE-READINESS.md for the current verdict and evidence priority.

## Artifact history

The current artifact and matched evidence are in INPUT-ACCEPTANCE.md. The older
hashes below are retained as historical evidence, not current-build claims.

- Latest follow-up: search-focus-app-build.log succeeds after the minimal search
  focus-binding fix; executable SHA256 is now
  cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
  Automatic Find focus, selection-to-Find replacement and native Chinese IME
  pass on this new binary. See NATIVE-INTERACTION.md's visual follow-up.
  The older hash and archive evidence below describe the preceding artifact,
  not this rebuilt executable.
- search-focus-package.log now passes the extended archive check on the new
  executable: round-trip resources/signatures/refusals, extracted-app automation,
  PTY/window lifecycle, command palette, renderer and compositor checks. No
  release was published. Full original Xcode UI and remaining acceptance rows
  are not implied by this passing bounded archive suite.
- Branch: macos12-v1.4.0; HEAD is official 1.4 baseline
  83fb95624b0439ee660c2679b43b38c8b63769cd with uncommitted adaptations.
- Current app: macos/build/ReleaseLocal/Ghostty.app, universal, build 18457,
  GhosttyCommit ends in -dirty. Ad-hoc signature; no TeamIdentifier.
- Host: Intel macOS 12.7.6 (21H1320), Xcode 14.1 (14B47b).
- Preceding product build after removing the unused snapshot-only cache method:
  cache-scope-app-build.log. Cache and scripting-reader checks, actual app smoke
  with text/live-policy probes and seven-Mach-O bundle audit pass (cache-scope-*
  logs). Core code is unchanged from the approved AX separation build.
  The earlier embedded input/selection-text run passes;
  strict selected-range diagnostic fails at 109 cell units versus 66 UTF-16
  units, as expected from upstream (ax-separated-known-range.log).
- Preceding archive acceptance covers the app after the unused-method
  cleanup: current-release-package-20261101.log, exit 0, with matching identity
  in current-release-package-20261101.json. Main executable SHA256 remains
  767e290f7c578a9fa487cc33a6062bd78a07a564b0de5600e736782198227170.
  Both sequential extracted-app suites and resource/refusal checks pass. The
  NOT-FOR-RELEASE archive was temporary and has been removed. No public artifact
  has been produced. Logs are under /tmp/ghostty-monterey, not durable release
  evidence until copied with the eventual immutable source/artifact identity.

## Requirement-to-evidence matrix

| Requirement | Current evidence | Verdict / remaining work |
| --- | --- | --- |
| Build official 1.4 functionality on this machine | Universal core and ReleaseLocal builds; upstream project-membership comparison; relocated resources and actual app tests | Proven for this build/host, not every runtime path |
| Preserve native terminal/window/rendering behavior | Existing probes plus foreground input/Chinese IME, native drag/menu/fullscreen and FOCUS-ACCEPTANCE.md | Automatic destination activation now passes; actual VoiceOver text reading passes, but selected-text speech remains a failure |
| Preserve performance/resource efficiency | ReleaseFast core; lifecycle observations; bounded real-PTY throughput and sampled app resources (throughput-sustained.log); focused shader tests | Ten-minute workload passes (COMPLETION-ACCEPTANCE.md); no official same-host, frame-time or overnight baseline; parser acknowledgments are not GPU presentation |
| Retain upstream design and minimum patch cost | PATCH-SCOPE.md identifies required port work and inherited/general fixes | AX snapshot separated by user decision; bounded native comparison supports retaining search bridge for now, with IME/maintenance risk still open; neither is automatically an OS requirement |
| Preserve meaningful tests | All 27 unit-test and 8 UI-test memberships retained; isolated candidate has 284 named unit passes and 6 documented skips; 27 selected UI methods pass through real XCTest; separate ReleaseLocal native evidence | Unit scaffold lacks per-case Xcode reporting; UI adaptations and retained fixed-width expectation disagreement are detailed in REMAINING-VERIFICATION.md |
| Support required Intel Monterey host | Intel 12.7.6 execution, including native interaction | ARM not required; do not claim an executed 12.0 run from deployment metadata |
| Safe updates | Fork-only policy, no default feed/key, native state-machine tests | Default manual-update mode is safe but not an enabled update service; distributor key/feed and signed update cycle remain unverified |
| ReleaseLocal artifact quality | Round-trip content/modes/links, existing bundle integrity, entitlements, checksums, refusal tests, extracted-app acceptance | Match evidence to the exact artifact and disclose known limitations; Developer ID, notarization and Gatekeeper approval are outside acceptance |

## Concrete next decisions

For the remaining interaction checks, use
[MANUAL-ACCEPTANCE.md](MANUAL-ACCEPTANCE.md). It pins the current development
artifact and gives concrete pass/fail observations. NATIVE-INTERACTION.md records
newly completed scenarios; core/controller/unit tests alone do not close them.

1. AX snapshot separation was approved (option 1) and implemented. See
   optional-ax/README.md for the recoverable experiment and known inherited
   range limitations. Current-build validation is recorded in STATUS.md;
   earlier archive runs do not validate this changed binary.
2. Review the search-selection bridge separately: it exceeds upstream's older-OS
   fallback but adds maintenance/IME risk. The native one-variable comparison
   supports retaining it for now: removing it loses programmatic select-all and
   same-turn editor/model convergence on this host. Stress assertions pass but
   SwiftUI reports multiple updates per frame; physical IME and performance are
   not established. Do not remove search or treat this optional enhancement as
   a prerequisite for correcting every upstream defect before finishing the port.
3. Use the verified macos/test-monterey.py workflow for unit execution; full UI
   acceptance remains open. The following records how that choice was validated.
   The default compiler in current Xcode 14.1
   cannot import Testing (testing-import-current.log); replacing attributes in
   bounded fixtures is not the original runner. Obtain a compatible test
   environment/toolchain, or explicitly design and review a coverage-preserving
   test migration. Do not hide files or label a zero-test run as success.
   TEST-TOOLCHAIN.md separates library deployment support from compiler-host
   requirements: official Swift 6.0.3 compiler/SwiftPM binaries require macOS 13,
   despite the package installer allowing older systems. A temporary Swift
   5.10.1 + Testing 0.6.0 package now discovers and passes the five unchanged
   CommandLineOpenFileFilter tests using real macros/XCTestScaffold. A temporary
   five-file candidate builds the actual x86_64 Debug app with that compiler,
   and the parameterized UpdateStateTests macro crash has a verified named-
   argument workaround in temporary tests. Seven test-source compatibility
   edits now allow all 27 sources to compile and run against the actual app
   objects through XCTestScaffold: 283 named tests pass. The reported total of
   289 includes five unavailable CoreTransferable tests and one upstream-disabled
   benchmark; those skips are not native Monterey transfer coverage. This is a
   standalone XCTest host, not normal app startup or the full Xcode test action.
   An additional real SurfaceView/native pasteboard/provider lifetime test now
   passes in a private application-bundle XCTest host: 284 named passes including
   this fixture, six skips, reported total 290. Bare xctest lacks the bundle proxy
   needed by existing notification cleanup; the private host fixes that without
   product changes. DropDelegate/physical drag coverage and reproducible project
   integration remain; see native-suite/README.md for the fixture's exact scope.
   A repository-owned candidate runner now repeats the complete unit invocation
   from fresh test copies and records commands/hashes/results (284 passes, six
   skips); the hardened targeted entry also passes. It still requires prebuilt
   experimental app objects and Testing dependencies. A separate candidate
   builder now regenerates the Swift app objects from source copies through
   build.nu, using explicit SDK13 test guards instead of compiler-version
   guesses. The fresh app builds/+version runs and the full runner again passes
   284 tests with six skips. Testing/Syntax now also rebuild from a repository-
   owned pinned minimal package; rerunning against both rebuilt sets passes the
   same inventory (rebuilt-all-inputs-tests-01). Existing Zig core/resources
   remain inputs; clean-checkout provenance and production/project integration
   are not solved by this candidate-only path. The initial dependency refresh
   failed on network access; the successful build reused source-cache commits,
   not previously compiled objects.
   The later rebuilt-core-02 source snapshot now reconstructs the universal core
   with empty compiled caches (333/333 steps). rebuilt-fresh-core-candidate-03
   consumes it, and rebuilt-fresh-core-tests-01 again passes 284 named tests and
   six skips. The candidate copies a verified pinned Sparkle source/binary cache
   after remote connection failures; no prior Ghostty core/app objects are reused.
   This closes that prerequisite-reuse gap, not dirty-source release provenance,
   external-toolchain provisioning or normal Xcode test-action integration.
   A later isolated Xcode target build also succeeds with all 27 original unit
   sources plus two fixtures (xcode-unit-build-02). This establishes real target
   compilation, not Xcode discovery or hosted test execution; the complete test
   action and UI API limitations remain open.
   The subsequent --hosted-test candidate also passes real Xcode discovery and
   app-hosted execution (xcode-hosted-unit-03): 284 named Testing passes, six
   skips, one XCTest scaffold. A negated assertion yields exit 65; restored
   inputs pass again. A candidate-only MainActor annotation fixes the split
   test fixture's background NSView construction without disabling the checker.
   This closes unit execution in the isolated Xcode candidate, not normal
   worktree integration, per-case Xcode reporting or the original UI suite.
   macos/test-monterey.py now supplies a documented single-command unit workflow
   without changing the release toolchain: prepare current candidate sources,
   rebuild pinned test dependencies (or explicitly reuse), and execute Xcode.
   Both modes pass in integrated-unit-01/02. The source-copy differences remain
   explicit; UI tests and per-case Xcode reporting are not solved by this entry.
   Native candidate quit probes now cover real dialog orchestration and one
   actual surface/PTY's confirmation/cancel/release/reap path, with final app
   replies intercepted. Subsequent quit-app-check.py runs the actual ReleaseLocal
   and candidate apps without intercepted callbacks: native cancel preserves a
   live PTY, then confirmed quit exits 0 and reaps the child. The no-Cancel-action
   negative control fails the sheet-state assertion. This establishes one-child
   confirmed quit on Intel 12.7.6. Later two-window review/direct modes also pass
   on both binaries, including initial/review cancellation, live child checks,
   sequential sheet acceptance and final cleanup; an omitted-reviewed-Cancel
   negative control fails. Update/logout and arbitrary split/window combinations
   remain untested here; candidate workarounds are still not promoted into the
   ReleaseLocal product.
   No candidate edits/dependencies are applied to the product;
   system toolchain selection is unchanged. See TEST-TOOLCHAIN.md.
4. Continue authorized local acceptance where meaningful, especially remaining
   focus/selection paths and accessibility. Native foreground input and drag
   evidence now exists (NATIVE-INTERACTION.md). No ARM or second-machine gate;
   never reuse 1.3.1 PR validation as proof for the current 1.4 binary.
5. Distribution target is ReleaseLocal, as explicitly chosen by the user.
   Do not request Developer ID/notarization credentials or require Gatekeeper
   approval to complete this acceptance. Preserve existing build/package
   integrity checks and the safe manual-update default. Do not disable security
   controls or generate publisher keys. An enabled automatic update service
   would require its own validation; it is not part of this scope clarification.
