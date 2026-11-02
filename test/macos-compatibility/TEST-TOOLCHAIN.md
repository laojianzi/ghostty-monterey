# Swift test toolchain investigation

Checked on 2026-10-31. This is an unresolved test-infrastructure requirement,
not a reason to drop product features or require macOS 13 as a product target.

## Distinguish host, target and runner

- Current host: Intel macOS 12.7.6, Xcode 14.1, Swift 5.7.1. The original unit
  target imports Testing; the installed compiler cannot import it. All 27 unit
  source memberships remain present. Supplementary source-body adapters do not
  provide the original macro expansion, discovery or runner semantics.
- Swift Testing at the official Swift 6.0 release revision
  `9aa8076dff01b66bcff9335cde02380d59acacc0` declares `swift-tools-version: 6.0`,
  a macro target and macOS 10.15 as its package deployment minimum. Therefore
  "Swift Testing inherently requires macOS 13 at runtime" is not a valid
  explanation of the current obstacle.
- Swift Testing 0.5.1 at `3ed2f90058afe4437369aee4880890e7fa65d1ec` declares
  tools version 5.9 and macOS 10.15, but its Getting Started document explicitly
  says Swift 5.9 and earlier are unsupported. The manifest alone is not proof
  of compiler compatibility. Swift 5.10 is documented with XCTestScaffold.
- The official Swift 6.0.3 macOS package's Distribution XML permits macOS 10.11
  and both architectures. However, the actual swift-frontend and swift-package
  binaries both have `LC_BUILD_VERSION minos 13.0` in **both** x86_64 and arm64
  slices (SDK 14.2). Do not infer host support from the installer or package
  deployment minima. This package is not a supported drop-in Monterey toolchain.

## Evidence and reproduction

Primary sources:

- [Swift Testing 6.0 manifest](https://github.com/swiftlang/swift-testing/blob/9aa8076dff01b66bcff9335cde02380d59acacc0/Package.swift)
- [Swift Testing 0.5.1 manifest](https://github.com/swiftlang/swift-testing/blob/3ed2f90058afe4437369aee4880890e7fa65d1ec/Package.swift)
- [Official Swift 6.0.3 package](https://download.swift.org/swift-6.0.3-release/xcode/swift-6.0.3-RELEASE/swift-6.0.3-RELEASE-osx.pkg)

The investigation reads the package as XAR metadata and its gzip/cpio payload,
without executing installer scripts. Extracted files are non-executable temporary
inspection copies. `otool -arch x86_64 -l <swift-frontend>` and the corresponding
arm64/SwiftPM commands produce the minimum-version evidence. The package's
Distribution member was checked against its XAR archived SHA-1
`f22913c8f206471403e425d0b7627651b46550d7`; that integrity check alone is not
signature authentication. Logs/metadata are under /tmp/ghostty-monterey:
swift603-distribution.xml, swift603-minimum.log and the two pinned Package.swift
copies. A partial download cannot pass pkgutil package validation.

The full 1,423,750,010-byte download subsequently passed
`pkgutil --check-signature`: Developer ID Installer "Swift Open Source"
(`V9AUD2URP3`), trusted timestamp 2024-12-11 and Apple notarization trust.
swift603-signature.log and swift603-sha256.txt record that check and the local
whole-package digest. The inspection was repeated against the completed package;
no toolchain executable or installer was run. Signature trust does not change
the binaries' macOS 13 host minimum.

## Next viable investigation, not a completed migration

1. Swift 5.10.1 now launches on the current host from a temporary extracted
   toolchain. Test the pinned Testing 0.6.0 runner before proposing project
   integration. This does not yet establish full app/test-target compatibility.
   Do not patch Mach-O minimum versions or replace system libraries.
2. Alternatively use a compatible external build/test host while keeping
   Monterey runtime validation separate. Newer-host tests alone cannot certify
   old AppKit/driver behavior. This adds no macOS 13/14 product-support promise.
3. A complete XCTest migration would need explicit coverage/discovery parity
   review and is substantially more patch surface than a toolchain solution.
   Do not replace all macros with assert or call only selected test bodies and
   report that as the original suite passing.

No dependency, Xcode project membership, system toolchain selection or runtime
minimum was changed by this investigation. XCUIDevice appearance support remains
a separate UI-test SDK issue. A newer compiler plus SDK 13 can also enable
compiler-gated source that references newer SDK APIs; do not assume a compiler
swap alone makes the app or full test target build successfully.

## Older toolchain follow-up

Both official packages below passed pkgutil signature validation as Swift Open
Source V9AUD2URP3 with Apple notarization trust. No installer scripts were run.

| Package | Intel frontend minimum | Intel SwiftPM minimum | arm64 frontend / SwiftPM minimum |
| --- | --- | --- | --- |
| Swift 5.9.2 | 10.13 | 10.15.4 | 11.0 / 11.0 |
| Swift 5.10.1 | 10.13 | 12.0 | 11.0 / 12.0 |

Swift 5.9.2 therefore has no declared host-minimum barrier here, but is not the
documented compiler for Testing 0.5.1. Swift 5.10.1 was extracted under
/tmp/ghostty-monterey/swift5101.xctoolchain and its absolute-path swift --version
successfully reports Swift 5.10.1 targeting x86_64-apple-macosx12.0. The default
xcrun compiler remains Swift 5.7.1 and xcode-select remains /Applications/Xcode.app.

Primary sources:

- [Official Swift 5.9.2 package](https://download.swift.org/swift-5.9.2-release/xcode/swift-5.9.2-RELEASE/swift-5.9.2-RELEASE-osx.pkg)
- [Official Swift 5.10.1 package](https://download.swift.org/swift-5.10.1-release/xcode/swift-5.10.1-RELEASE/swift-5.10.1-RELEASE-osx.pkg)
- [Testing 0.5.1 compiler/runner instructions](https://github.com/swiftlang/swift-testing/blob/3ed2f90058afe4437369aee4880890e7fa65d1ec/Sources/Testing/Testing.docc/TemporaryGettingStarted.md)
- [Testing 0.6.0 manifest](https://github.com/swiftlang/swift-testing/blob/8097dd8bcf7f2ed85f8aa8883635ce413012f53b/Package.swift)
- [Testing 0.6.0 XCTest scaffold](https://github.com/swiftlang/swift-testing/blob/8097dd8bcf7f2ed85f8aa8883635ce413012f53b/Sources/Testing/Testing.docc/TemporaryGettingStarted.md)

The probe uses a disposable Swift package containing unchanged copies of
CommandLineOpenFileFilter.swift and its original test source, plus the documented
XCTestScaffold entry point. This exercises real macros, discovery and reporting,
not textual replacement of assertions. A small-suite pass would prove that seam
only, not all 27 source files, the Ghostty host app or Xcode's full test action.

Result: the probe builds and runs on Intel Monterey with Swift 5.10.1, Testing
0.6.0 pinned as above and SwiftSyntax 510.0.3 at
`2bc86522d115234d1f588efe2bcb4ce4be8f8b82`. All five original tests are discovered
and pass. XCTest reports one scaffold test; Testing reports five actual tests.
This is a real runner result, not five hand-invoked bodies or an empty XCTest
success. The source/test copies were compared byte-for-byte with the worktree.
See testing-native-probe.log and /tmp/ghostty-monterey/testing-native-probe-path.
Negating one expectation in the temporary copy produces the expected file/line
failure, a failed XCTest and exit 1 (testing-native-red.log). The original file
was then restored; no repository test assertion was modified.

## Full app integration experiment

The next step used the actual Xcode app target, not a replacement library. A
temporary copy of macos/build.nu selected SWIFT_EXEC by absolute path and kept
SYMROOT/OBJROOT under /tmp. The first unmodified-source build failed inside
Swift 5.10.1 SIL generation at AppDelegate.terminate, asserting "local var should
not be actor isolated" (swift510-app-probe.log). This is a compiler failure, not
an observed Monterey application crash.

An isolated copy of the macOS sources then tested these candidate workarounds:

- Force the existing older-SDK paths for three compiler-gated macOS 14 APIs.
  Swift 5.10 with SDK 13 cannot see NSView.clipsToBounds,
  UnevenRoundedRectangle or onKeyPress, even inside availability checks. A
  standalone actual-SDK check confirms this (sdk13-new-compiler.log). Raising
  compiler guards in the temporary copy is experimental, not a proper general
  SDK-detection solution and not applied to the product.
- An explicit capture list alone did not avoid the termination compiler crash.
  Explicit MainActor closures for terminate and reviewWindows allowed their SIL
  generation to proceed. These changes require behavioral review before adoption.
- An explicit return inside PendingIndicator's TimelineView closure resolved
  the next generic Content inference error with this compiler/SDK combination.

With those five-file candidate edits, the actual Debug Xcode app builds and its
`+version` command runs on this machine (swift510-app-return.log and
swift510-app-version.log). This build is x86_64 only, not universal, and no GUI
acceptance or original test action was run on it. The candidate patch is kept
at /tmp/ghostty-monterey/swift510-app-candidate.patch; the active product and
ReleaseLocal artifact are unchanged. The temporary project is recorded in
/tmp/ghostty-monterey/swift510-app-probe-path.

Type-checking all 27 original unit-test sources against that real Ghostty module
with Testing 0.6.0's actual macro executable then fails with compiler signal 11
while expanding UpdateStateTests.testIsHidden's parameterized @Test arguments
containing closures (swift510-original-tests-typecheck.log). This rules out
calling the five-test experiment a turnkey full-suite solution. No test was
removed or converted to make that command pass. Next work is to minimize this
specific compiler/macro failure and evaluate a coverage-preserving workaround,
before adding any dependency or toolchain option to the real Xcode project.

### Parameterized macro failure minimized

The compiler crash reproduces without Ghostty, Sparkle or AppKit code:

```swift
import Testing
struct Probe {
    @Test(arguments: [{}])
    func sample(_ action: () -> Void) { action() }
}
```

Both a direct closure array and a tuple containing a closure crash Swift 5.10.1
in FragileFunctionKindRequest. Moving the same values into a named static
property makes type-checking succeed (macro-closure.log, macro-tuple.log,
macro-named.log). A computed property is preferable for the UpdateState fixture
so each argument-list evaluation still constructs fresh states.

The temporary UpdateStateTests copy now moves its two arrays, without changing
their seven rows or assertions, into named computed properties. A real SwiftPM
runner using unchanged production UpdateViewModel.swift and the actual Sparkle
framework passes the 16 UpdateState, 13 UpdateViewModel and 9 ReleaseNotes tests.
With five earlier command-line tests and one two-case closure diagnostic, the
runner reports 44 tests (swift510-update-native.log). It prints all seven update
argument rows. Reversing the idle expectation only in a temporary argument row
causes the named parameterized test and hosting XCTest to fail with exit 1;
restoring it passes again (swift510-update-red.log, swift510-update-restored.log).
These are real macros/runner results, not the earlier assertion adapter.

The complete test-target type-check then proceeds beyond that crash and exposes
other bounded compatibility work in the temporary copies: trailing argument
commas, URL path APIs introduced in macOS 13, main-actor access in the glass
test, and Testing 0.6.0's older trait-call signature. No source or test edits
from this investigation have been applied to the active worktree.

The five TransferablePasteboard tests specifically exercise CoreTransferable,
which is unavailable on macOS 12, rather than the retained native surface
pasteboard route. The initial temporary macOS-13 suite annotation permitted
type-checking but did not safely gate implicit test discovery at runtime. The
per-method availability experiment below supersedes that annotation. Before
integration, keep the original API tests for applicable hosts and provide
real-runner coverage for the production Monterey equivalent.
The existing transfer-check.sh is supplementary evidence, not a substitute for
that runner integration. Do not silently convert this annotation into permission
to drop five tests and declare the whole suite green.

Experiment hygiene: reusing OBJROOT across the original and copied projects
initially retained source file lists pointing to the original tree; that run
did not test candidate changes. A new candidate-obj/candidate-build pair and
inspection of compiler source lists corrected it. The copied project also
needed explicit links to the existing images, include, zig-out and GhosttyKit
resources. Missing fixture paths, XCTest search paths and an initially wrong
macro executable basename were corrected before interpreting compiler results.

## Real app-object unit bundle

All 27 temporary unit sources now compile against the actual candidate Ghostty
module. Seven files need compatibility edits: the two named UpdateState argument
arrays, older argument-comma syntax, older Foundation URL spellings, explicit
main-actor isolation in the glass test, the older Testing bug-trait signature,
and per-test availability for CoreTransferable. Assertions and parameter rows
are retained. The other 20 files are unchanged. These edits are not in the active
repository tests or the release product.

The actual candidate Xcode app objects, excluding only main.o, were relinked as
libGhosttyProbe.dylib. A native XCTest bundle links this library, real Sparkle,
Testing 0.6.0 and its real macro expansions. Its main-actor XCTestScaffold creates
NSApplication.shared and initializes libghostty. This is not a substitute
SurfaceView implementation, but neither is it the normal application's main,
delegate lifecycle or Xcode test action. It remains an x86_64 Debug experiment.

Two fixture problems were distinguished from product defects:

- Passing xctest's complete argument vector to ghostty_init caused ConfigTests
  to see the test bundle path as an invalid configuration argument. Initializing
  with argc 1 retains argv[0] but excludes harness arguments; ConfigTests then
  passes without changing its assertions or the configuration implementation.
- Availability on the enclosing implicit TransferablePasteboardTests suite
  type-checked, but execution ended at its first unavailable test without a
  final summary. Annotating the two helper types and each of the five test
  methods instead lets Testing generate safe runtime guards. An attempted
  explicit available @Suite was rejected by the macro. Neither unsuccessful
  attempt is passing runtime evidence.

The guarded bundle exits 0 and reports 289 tests. **This includes skips:** the
log contains 283 named test passes, five CoreTransferable skips with the reason
"Requires macOS 13", and one upstream-disabled benchmark test. Testing 0.6.0's
HumanReadableOutputRecorder increments its count for skipped tests as well as
started tests. Do not report this as 289 executed tests or complete native drag
coverage. The five skips do not validate the Monterey surface-pasteboard route.

Evidence under /tmp/ghostty-monterey:

- swift510-test-library-link.log and swift510-app-link-command.txt;
- swift510-native-bundle-command.txt (the complete compiler/linker argument list)
  and swift510-native-bundle-availability.log;
- run-native-test-bundle.py, with isolated defaults/XDG directories and explicit
  candidate resource paths; it does not change the general clipboard;
- initial successful log: /tmp/ghostty-native-suite-y0ctnlqf/run.log.

A whole-bundle negative control negates only requiresExecuteFlag's expectation
in the temporary test copy. Rebuilding and running reports that exact test and
line as a failure, propagates a failed XCTest, and exits 1. Restoring the source,
rebuilding, and rerunning exits 0 with the same 283 passes and six skips. Evidence:
swift510-native-suite-red.log, swift510-native-suite-restored.log and their
negative/restored-build logs. The candidate patch was regenerated after source
restoration; it contains seven compatibility files and no negated assertions.
This guards against an empty bundle or swallowed Testing failures, not against
the remaining lifecycle/coverage limitations.

The next integration requirement is real-runner coverage of the production
Monterey native transfer route and a reproducible build/test entry point, not a
general CoreTransferable reimplementation. Proper SDK capability gating and
review of the temporary compiler workarounds remain necessary before adopting
the candidate. Original UI tests, release-product validation, arm64 execution
and physical input/drag acceptance remain separate gates.

## Native Monterey surface transport fixture

native-suite/MontereySurfaceTransferTests.swift now exercises the real candidate
Ghostty.App, SurfaceView, pasteboard implementation and UUID codec with the real
Testing runner. Its isolated config disables clipboard access, notifications and
shell integration; the only child is /usr/bin/true. It requires child exit, checks
the exact 16 bytes/type on a unique pasteboard, releases the SurfaceView and
asserts its weak reference is nil, then reads the retained payload. Native async
NSItemProvider transport checks valid data and 0/15/17-byte invalid payloads.

The first run exposed a host limitation, not a drag implementation failure:
SurfaceView deinit calls UNUserNotificationCenter, whose currentNotificationCenter
asserts that bare Xcode xctest has no application bundle proxy. Leaving the view
alive or changing product notification cleanup would hide the problem. Instead,
a temporary NativeTestHost.app wraps a copy of the same xctest executable with a
private bundle identifier and framework links to Xcode. The exact same compiled
test bundle then passes, including surface teardown. No Xcode/system files or
notification permissions were changed. The host still does not execute Ghostty's
normal main/delegate lifecycle.

With the new fixture included, the full candidate bundle reports 290 tests:
284 named passes and the same six skips. A transfer-only negative control changes
one expected UUID byte; both the item and pasteboard comparisons fail, the XCTest
host fails and exits 1. Restoring the expectation and rebuilding the full bundle
returns exit 0. Logs under /tmp/ghostty-monterey:

- swift510-native-transfer-host-failure.log records the bare-host exception;
- swift510-native-transfer-pass.log and swift510-native-transfer-restored.log
  record full-bundle success;
- swift510-native-transfer-red.log records the exact failed comparisons;
- swift510-native-transfer-command.txt and run-native-apphost-bundle.py record
  compilation and the isolated application-bundle host.

After formatting the repository fixture, it was compiled directly from
native-suite/MontereySurfaceTransferTests.swift and rerun as a transfer-only
bundle (one test, exit 0; swift510-native-transfer-repo.log). The corresponding
swift510-native-transfer-repo-command.txt records that exact repository path.
The most recently compiled temporary NativeTests.xctest therefore contains this
single targeted test; the preceding full-bundle result is the restored log, not
a claim about that later binary's discovery count. SwiftLint 0.52.4 strict lint
passes for the fixture (the existing unsupported check_for_updates config-key
warning remains).

This narrows the missing Monterey coverage to actual DropDelegate dispatch,
surface lookup/split mutation and physical drag behavior. It does not replace
the five generic CoreTransferable tests with equivalent claims. Repository
integration still needs a reproducible toolchain/build entry point; the added
fixture is not yet a member of the Xcode test target. No candidate app/compiler
workarounds have been promoted to the release product.

## Repository candidate-runner entry point

native-suite/run.py now prepares and executes the candidate test bundle from
repository-owned fixtures rather than a saved Python argument list in /tmp.
It copies all current macos/Tests files, applies the archived seven-file
swift510-tests.patch to copies only, adds the native surface test/scaffold,
builds the bundle and private app host, and checks named pass/skip inventories.
It requires explicit paths to the existing candidate app-object library,
Swift 5.10.1 compiler and pinned Testing package. This is a repeatable test
invocation over existing build inputs, **not** a clean-checkout app/toolchain
bootstrap, normal Ghostty app-hosted test action or release validation.

The full repository-driven run passes with 284 named tests and exactly the six
documented skips (native-entry-all-03/{build.log,run.log,result.json} under
/tmp/ghostty-monterey). It compiles the current repository surface fixture and
all 27 patched test copies. The test output lives in its own directory, leaving
the previous temporary bundles and release app untouched. Commands, input hashes
and result JSON are retained. Later runner hardening checks exact skip names,
requires the surface test result, rejects recorded issues, records candidate
source differences and uses a fresh UUID for defaults/bundle isolation. Its
result parser also accepts the real full-run log after these changes.

Initial runner integration failures were confined to the fixture: absolute
git-apply output paths crossed macOS's /tmp symlink; applying relative to the
isolated output directory resolves that. Resolving the swiftc symlink changed
the multicall driver's argv[0] and rejected linker arguments; preserving the
explicit swiftc path resolves it. Neither requires a product change. Failed
attempts native-entry-all-01 and -02 are not passing evidence.

Nine fast test_runner.py checks verify result rejection for nonzero/empty,
incomplete, wrong-test, unexpected skip and incomplete-suite output, plus valid
targeted/full inventories. They test the verifier, not Swift runtime behavior.
The pre-existing full-bundle and surface-byte negative controls remain the
actual runner/expectation failure evidence. See native-suite/README.md for the
command, prerequisites and manifest provenance limits.

The hardened runner also builds/runs --suite transfer successfully (one pass,
no skips; native-entry-transfer-01). Its manifest lists exactly the five known
candidate app-source differences. All 27 original files and exactly seven
patched copies were checked in the full-run output; original tests remain
unchanged. The targeted and full runs have distinct output bundles.

## Fresh candidate application objects from the worktree

native-suite/build-candidate.py now copies current macOS sources/project/assets,
applies an archived five-file candidate patch, and invokes a temporary copy of
the actual build.nu with separate SYMROOT/OBJROOT. It requires the existing
universal core archive/resources and explicitly selected Swift 5.10.1/SDK 13;
it does not install a compiler or change the release app. Xcode resolves the
existing pinned Sparkle dependency in this new project location.

The three SDK-14 expressions no longer use the arbitrary compiler >=6.0 guard
from the first experiment. The candidate patch retains compiler >=5.9 and adds
!GHOSTTY_TEST_SDK13; the builder verifies SDK 13.x and supplies that test-only
condition through inherited OTHER_SWIFT_FLAGS. The actual compile log contains
DEBUG/GHOSTTY_TEST_SDK13 for Ghostty and additionally DOCK_TILE_PLUGIN for the
plugin. The two explicit MainActor Task closures and TimelineView return remain
candidate-only compiler workarounds, not reviewed release-product changes.

The fresh x86_64 Debug app build succeeds and +version runs in
/tmp/ghostty-monterey/rebuilt-candidate-01. Deriving the library link from the
actual Xcode invocation retains 162 object files and excludes exactly main.o;
libGhosttyProbe.dylib links successfully. Input hashes are checked before/after
the app build, and build-inputs.json/build-commands.json/build-result.json record
the candidate sources, core archive and app/library identities. The source
copy has the same five known differences from the active worktree, not a copy
of the earlier manually edited candidate. Re-extracting the link command with
the factored helper matches the executed command exactly.

Eleven fast verifier/link tests now cover result inventories, exclusion of only
main.o, preservation of the app link file list/diagnostics, and refusal when the
entry object is absent or duplicated. These tests are not GUI/runtime evidence.
Clean core/resource rebuilding, the Testing package bootstrap and complete
source-to-release provenance remain open; this step reconstructs the candidate
Swift app objects instead of depending on their previous temporary instance.

The repository runner subsequently compiles all test copies against these fresh
objects and passes: 284 named tests, six exact skips, exit 0. Evidence is in
rebuilt-candidate-tests-01/{inputs.json,build.log,run.log,result.json}. Both actual
Xcode SwiftFileList files point exclusively at the new copied source tree;
no old candidate source list was reused. This validates the revised SDK13
condition and rebuilt objects for this unit/transport scope, not GUI termination
dialog behavior, arm64 or the active ReleaseLocal binary.

## Fresh pinned Testing dependencies

native-suite/build-testing.py and testing-package/ now reconstruct the runner's
Testing/Syntax prerequisites without the earlier disposable Ghostty fixture.
Both repositories are pinned by exact revision in the package manifest. A small
compile-only probe imports Testing and expands @Test/#expect; runtime acceptance
still requires running the actual Ghostty test bundle afterward.

The initial remote-refresh attempt ended with exit 1 after GitHub HTTPS connection
timeouts (rebuilt-testing-01/build.log). After that process terminated, the
--skip-update variant used the already verified source-cache commits, created
new working copies and compiled all objects into rebuilt-testing-02. This is
source-cache reuse, not reuse of previous compiled objects or an offline-download
claim. The 244.53-second build succeeds; 75 library/plugin/object hashes are
recorded in build-result.json, with exact clean checkout HEADs. The package
sources still match their pre-build manifest and the repository template.

SwiftPM warns that the root's swift-syntax dependency is not used directly by a
target: it is explicitly pinned to constrain Testing's transitive macro compiler
dependency. Its actual sources compile as part of the build. This warning is not
hidden or counted as a test failure. The system Swift remains 5.7.1; no installer,
xcode-select or global dependency configuration was changed.

The builder refuses pre-existing output directories and invalid concurrency,
caps jobs at eight (default four), verifies resolved pins/checkouts and bounds
the build to 30 minutes. The consumer run.py now checks clean dependency checkout
HEADs as well as Package.resolved before compiling tests. Core/resources and the
compiler installation itself remain explicit external prerequisites.

Full runtime follow-through passes using both rebuilt-candidate-01 app objects
and rebuilt-testing-02 dependency objects, with fresh copied tests:
rebuilt-all-inputs-tests-01 reports 284 named passes, the six exact skips and exit
0. No object/module from the older ghostty-testing-native disposable package is
used by that recorded compiler command. This closes that temporary prerequisite
for the candidate unit runner, not clean core builds or normal app/UI acceptance.

## Native termination-dialog seam

termination-check.py links the actual rebuilt candidate app-object library into
a private application probe. The real AppDelegate.terminate/reviewWindows and
BaseTerminalController.confirmCloseAsync methods run with native NSAlert/sheets.
Only the confirmation predicate is supplied by a controller subclass with empty
surface trees; an NSApplication subclass records replies instead of terminating
the host. This specifically reaches both candidate MainActor closures without
reimplementing them or changing product code.

Verified paths: no confirming window returns terminateNow; single-window cancel
and accept defer then reply false/true and remove the sheet; multi-window cancel
and terminate return synchronously; review-cancel visits one sheet and closes
neither window; review-all visits two sheets and closes each window exactly once
before replying true. Buttons are invoked on private native views, not via global
events. Final source compiles without diagnostics and passes strict SwiftLint
(only the existing unsupported configuration-key warning from SwiftLint).

The first fixture mistakenly treated previously closed windows retained by
AppKit as still needing confirmation, entering an unexpected modal loop; a
process sample locates it in NSAlert.runModal. The fixture now clears its own
confirmation predicate after each scenario, and uses a main-run-loop selector
timer in modal/default modes rather than a Sendable closure. No product bug or
fix is inferred from that harness failure. Both timed-out/terminated probe
processes are terminal, not left running.

Final logs: /tmp/ghostty-monterey/termination-native-green-02 (all six scenarios,
exit 0) and termination-native-red-02 (one reversed expected reply, the exact
assertion failure, exit 1). This validates the bounded dialog orchestration,
not real child termination, applicationShouldTerminate update/logout policies,
normal app launch/quit, or physical UI acceptance. The release app is unchanged.

## Real child confirmation and teardown

The termination probe's --real-child mode now constructs the actual
BaseTerminalController/SurfaceView/PTY instead of supplying its confirmation
predicate. A directly launched Python process records its PID and sleeps for a
bounded 20 seconds; shell integration and clipboard/notification access remain
disabled. The isolated config requests confirm-close-surface=always. The probe
asserts the real surface/controller/app require confirmation and calls the actual
applicationShouldTerminate method, not just terminate().

Cancellation and acceptance both traverse the native sheet and reply with the
expected value. Cancellation leaves the child alive; accepting the intercepted
reply also leaves it alive until the host explicitly tears down the window and
controller. Weak controller/surface references then clear, kill(pid, 0) reports
ESRCH, the app no longer requests confirmation, and the next quit-policy call
returns terminateNow. This is actual surface ownership/child cleanup evidence,
not a claim that merely returning true terminates a child or the whole app.

termination-child-green-01 passes all assertions, exit 0, with an empty compiler
diagnostic log. termination-child-red-01 reverses only one expected sheet reply,
fails the exact assertion and exits 1. Both runs' child PIDs are absent afterward,
checked by the runner and independently. The earlier six-scenario mode also
passes after these runner changes (termination-native-regression-03). Strict
SwiftLint and the eleven verifier/link tests pass. No app-product source changed.

The final NSApplication reply remains intercepted; normal process shutdown,
multi-surface cleanup, update/logout bypasses and physical interaction are not
certified by this mode. It is evidence for the candidate's actual MainActor quit
path on Intel Monterey, not a blanket release gate closure.

Separately, the freshly rebuilt Debug candidate app (not the object-library
host) passes app-smoke.py --automation-text --automation-policy in a private
resigned copy. This reaches normal application startup, PTY/control/UTF-8,
split/tab/window close/undo/redo and TTL cleanup, quick-terminal idempotence,
scripted text/selection readers, live scripting opt-out/re-enable, and normal
quit with confirmation disabled by the fixture. Evidence:
rebuilt-candidate-app-smoke.log and /tmp/ghostty-monterey-smoke-totk7brr/launch.log
(empty). That success must not be combined with the intercepted-reply probe to
claim an end-to-end confirmed quit; the two executed scenarios differ.

The later quit-app-check.py closes that specific evidence gap separately: actual
ReleaseLocal and candidate apps, private resigned copies, no intercepted methods,
native Quit/Cancel followed by Quit/Terminate, child heartbeat preserved after
cancel, app exit 0 and absent child after accept. See STATUS.md's "Actual
application confirmed quit" entry for AX return-code caveats, the omitted-Cancel
negative control and logs. This is a new actual-app run, not a reinterpretation of
the earlier probe/smoke results or an expansion to all termination paths.

The subsequent two-window modes exercise real reviewWindows orchestration in
both application binaries: cancel the initial dialog, cancel the first reviewed
sheet with both independent children still producing heartbeats, then accept
both sheets sequentially and observe clean app exit/child disappearance. The
direct Terminate Processes branch also passes. No task/controller methods are
stubbed or invoked directly. A missing reviewed-Cancel action is rejected by the
sheet-disappearance assertion. See the later STATUS.md two-window entry for logs;
this is actual-app evidence for the candidate MainActor review closure, not
proof of update/logout handling or arbitrary split/window shutdown combinations.

## Fresh universal core prerequisite (2026-10-31)

native-suite/build-core.py now reconstructs the last previously prebuilt input:
the universal ReleaseFast core and installed resources. The successful
/tmp/ghostty-monterey/rebuilt-core-02 run copies 6068 tracked/nonignored source
files, uses new compiled-cache directories, and shares only dependency source
packages. All 333 build steps succeed, input hashes remain unchanged, and 925
artifact hashes are recorded. The archive contains x86_64 and arm64 slices.
The first attempt rejected an unsupported build CLI cache argument; the successful
attempt uses ZIG_GLOBAL_CACHE_DIR and a separate fresh output directory.

The Metal logical-op-parentheses warning is still present; the adjacent Zig
"failed command" diagnostic is not the overall outcome (exit 0, 333/333).
No shader edit is warranted by this warning alone. The source snapshot uses an
explicit development version and does not replace the active product archive.
build-candidate.py --core-root selects these rebuilt inputs and checks hashes of
all framework/resource files around the app build. Core compilation alone does
not establish app startup or unit success with the new inputs. External SDK,
compiler and package sources remain prerequisites; clean release identity and
normal Xcode test-action integration remain separate work.

The new core is now consumed by rebuilt-fresh-core-candidate-03 (2026-11-01).
Xcode's initial package refresh failed on GitHub HTTPS access (candidate-01).
Skipping updates alone still required a missing project-cache clone (candidate-02);
that owned fetch/build was explicitly terminated after repeated connection
failures, then confirmed terminal before starting another build. The successful
third candidate copies an existing SourcePackages cache, verifies the clean
Sparkle checkout at ac2def288cbff5cfc7df3ffef6abdf45b72bcb0a, relocates artifact
paths, and passes -skipPackageUpdates/-disableAutomaticPackageResolution.
The app's 1210 input hashes include 120 Sparkle artifact files. Sparkle remains
the pinned upstream binary distribution; it is not claimed to be rebuilt here.

The fresh Debug app builds and +version reports 1.4.0-dev.monterey-probe with
ReleaseFast core/CoreText/Metal/kqueue. Its SHA256 is
a2c506cf3d0c663173d5b0373a74bf5669c9695bbfea5ae0e0afc26b82d28566.
The library retains 162 actual app objects, excluding only main.o.
rebuilt-fresh-core-tests-01 then passes 284 named tests with the same six explicit
skips against rebuilt-testing-02. This removes the old worktree core/resource
reuse from that test chain. It does not promote candidate source-copy changes,
replace the release binary, or establish clean release provenance.
The successful run's input manifest records skip_package_updates=false because
it originally recorded only the explicit flag; build-commands/app-build logs
show the effective skip options implied by --source-packages. The builder now
records the effective boolean; the historical manifest is left intact.

## Xcode target graph compilation (2026-11-01)

build-xcode-unit.py now builds a copied GhosttyTests target and its actual app
dependency through Xcode 14. It retains all original source memberships, applies
only the existing candidate test patch to copies, and adds the native scaffold
and surface fixture. Testing's include paths, object list and macro plugin are
target-specific; no Swift package dependency is added to the product project.

The first attempt fails because Xcode 14's integrated driver misparses the newer
-load-plugin-executable operand. Passing both through -Xfrontend succeeds in
xcode-unit-build-02. The exact 29-file compile inventory and emitted XCTest class
are checked separately; this is compilation evidence, not executed tests or
successful Xcode discovery. Existing test actor-conformance warnings remain.
App-hosted execution still needs a scaffold that does not call ghostty_init after
the real main already initialized the core, plus isolated host configuration.
No UI test action, global input, appearance change or product edit was performed.

The subsequent --hosted-test path now closes the unit discovery/execution gap
for the candidate: a private copied scheme launches the real app, verifies its
already-initialized AppDelegate/core, and runs XCTestScaffold without repeated
ghostty_init. Xcode's Main Thread Checker exposed background NSView construction
in SplitTreeTests; xcode-hosted-tests.patch marks only that copied suite MainActor.
The checker is retained and no assertions are weakened. The original 27 test
files remain in the target, plus two fixtures. No UI tests run in this mode.

xcode-hosted-unit-03 passes 284 named tests/six skips and one XCTest method;
Tests.xcresult and console output both confirm success. Negating the surface-byte
expectation produces the exact recorded failure and Xcode exit 65 in Negative.xcresult.
Restored.xcresult/restored.log then pass the same full inventory. Input hashes
match after restoration. Xcode 14 aggregates the nested Testing tests under one
testAll method; per-case Xcode selection/reporting is not provided. Thirty-four
build warnings remain. Startup executes the real badge-authorization path and
logs denial for the private host; no user permission setting is changed.
The supported worktree scheme/build.nu is still untouched. Candidate-specific
compiler/SDK/test changes and external dependency provisioning still need a
deliberate supported workflow, and original UI-test API compatibility is open.

macos/test-monterey.py now provides that explicit repository unit entry point;
see BUILDING.md for prerequisites and invocation. It prepares source copies,
builds Testing/Syntax by default, then compiles/runs the app-hosted Xcode suite.
An explicit --testing-package can reuse verified dependency objects. The
--prepare-only candidate stage eliminates the previous redundant intermediate
app build/object-library link. Compiler/SDK/test source-copy differences remain
documented; they are not promoted to the release compiler policy.

Both entry-point modes were executed successfully: integrated-unit-01 reuses
Testing inputs explicitly; integrated-unit-02 rebuilds dependencies in 243.92s
from pinned cached source commits and then passes 284 named tests/six skips with
one successful Xcode scaffold. Stage/aggregate logs record which inputs were
reused. This removes reliance on manually assembled temporary candidate apps,
not the external toolchain/core/Sparkle prerequisites or remaining UI test gap.
