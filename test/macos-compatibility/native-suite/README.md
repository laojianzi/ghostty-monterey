# Native runner integration fixtures

These are additional real Swift Testing tests, not replacements for the original
macos/Tests sources. They are not yet wired into the Xcode project. See
../TEST-TOOLCHAIN.md for the temporary Swift 5.10.1 experiment and its limits.

For the end-to-end unit workflow, use `python3 macos/test-monterey.py --help` and
the command in ../BUILDING.md. It rebuilds Testing dependencies by default,
prepares current candidate sources without compiling an intermediate app, then
runs the Xcode-hosted suite. --testing-package explicitly reuses a pinned build.
The individual scripts below remain useful for inspecting individual stages.

## Xcode unit-target compilation

```sh
python3 test/macos-compatibility/native-suite/build-xcode-unit.py \
  --candidate /tmp/ghostty-monterey/rebuilt-fresh-core-candidate-03 \
  --testing-package /tmp/ghostty-monterey/rebuilt-testing-02 \
  --swiftc /tmp/ghostty-monterey/swift5101.xctoolchain/usr/bin/swiftc \
  --output /tmp/ghostty-xcode-unit-NEW
```

This copies a candidate (including its verified SourcePackages cache), applies
the seven-file test compatibility patch to copies, and adds the two native
fixtures to the copied GhosttyTests target. Xcode builds the actual app dependency
and test bundle with new object paths. Only the test target imports/links Testing
and receives its macro plugin. Xcode 14's integrated driver needs the plugin
arguments forwarded with -Xfrontend, unlike the standalone swiftc invocation.
The generated SwiftFileList must contain exactly all 27 original sources and
the two fixtures; no original source or assertion is excluded.

This is **compilation only**: it does not launch the hosted unit suite or UI tests,
change system appearance, or establish Xcode test discovery/runtime success.
The copied project is serialized as an XML plist; the worktree project remains
untouched. Never distribute its Debug app containing GhosttyTests.xctest.
The standalone scaffold initializes the core itself. With --hosted-test, a
compile condition instead checks the actual AppDelegate/core initialized by main.

Add --hosted-test to execute all unit sources through Xcode's actual app host.
The copied scheme selects only GhosttyTests (UI tests remain untouched in the
worktree), disables parallel launches, and uses a unique app/defaults identity,
isolated config/state, no initial window and /usr/bin/true rather than a user
shell. No synthetic global input or appearance changes are used. The real app's
badge-authorization path still runs and logs notification denial for the private
host; this is not a permission-free mock of application startup.

The additional xcode-hosted-tests.patch marks SplitTreeTests @MainActor because
its MockView constructs NSView. Xcode's Main Thread Checker caught a background
construction and terminated the first hosted run; the checker stays enabled.
All assertions are retained. The successful run must show 284 named Testing
passes and exactly six skips, plus one XCTest scaffold in xcresult with no test
failures. Xcode 14 represents these nested tests as one XCTest method, not 284
individually selectable Xcode test cases. This is unit integration only, not full
UI test-action compatibility or an unchanged ReleaseLocal product test.

## Candidate runner

To reconstruct the universal core/resources without overwriting the active
worktree framework, use the source-snapshot builder:

```sh
python3 test/macos-compatibility/native-suite/build-core.py \
  --zig /tmp/ghostty-monterey/zig-x86_64-macos-0.17.0/zig \
  --dependency-cache ~/.cache/zig/p \
  --output /tmp/ghostty-core-NEW
```

It copies Git's tracked/nonignored untracked inventory, preserving current edits
and deletions, without .git or ignored build outputs. Both compiled-cache roots
are new; only the dependency source-package directory is reused. It builds a
universal ReleaseFast core and installs resources inside the snapshot, checks
source hashes after compilation, and records artifact hashes/architectures.
The version override is explicitly 1.4.0-dev.monterey-probe: this dirty snapshot
is not a tagged release or an immutable publisher identity. SDK/toolchain binaries
and cached external dependency sources remain prerequisites. See logs for actual
build outcome; creating a snapshot alone is not a successful core build.

Pass `<core-output>/source` as --core-root to build-candidate.py to consume that
framework/resource tree rather than the active worktree's artifacts. The Swift
candidate still takes its source/project copy from the active worktree. Its
manifest hashes all consumed core/resource files before/after the app build.
External core trees must now carry the successful build-core.py manifests.
The candidate and Xcode runners compare the recorded core-source inventory
(src/pkg/vendor/include/po/images/dist plus root build/version files) against
both the snapshot and current checkout, and verify every framework/resource
artifact against its recorded hash before/after compilation. Changed, added or
removed core sources require rebuilding. Swift/test/docs-only edits do not stale
the Zig snapshot. This is local consistency checking, not a signed attestation
or complete hermetic toolchain/dependency verification. Selecting the current
worktree as --core-root remains possible, but is explicitly recorded as lacking
source-to-artifact provenance; merely hashing an existing archive cannot prove
that it was built from current source.

The Testing/Syntax prerequisites can also be rebuilt from a repository-owned
minimal package (no app sources or previously compiled test objects):

```sh
python3 test/macos-compatibility/native-suite/build-testing.py \
  --swift /tmp/ghostty-monterey/swift5101.xctoolchain/usr/bin/swift \
  --output /tmp/ghostty-testing-NEW
```

Both dependencies are pinned by revision directly in testing-package/Package.swift.
SwiftPM may fetch their repositories or update its shared source cache. The output
directory must be new; all object files are built there with four jobs by default.
The builder verifies resolved pins and clean checkout HEADs and records hashes of
the Testing library/plugin/objects. A minimal macro expands during compilation;
that is not a runtime suite pass. Pass the resulting directory as --testing-package
to run.py for runtime validation. No toolchain installer or global compiler switch
is involved.
If both pinned commits already exist in SwiftPM's source cache, --skip-update
avoids refreshing remote refs. It still creates a new build directory and
recompiles dependencies; it does not copy any previous .o or .swiftmodule files.
This flag is not an offline guarantee when a required repository is absent.

An isolated candidate builder is available for the application-object prerequisite:

```sh
python3 test/macos-compatibility/native-suite/build-candidate.py \
  --swiftc /tmp/ghostty-monterey/swift5101.xctoolchain/usr/bin/swiftc \
  --nu /tmp/ghostty-monterey/nu-0.102.0-x86_64-apple-darwin/nu \
  --output /tmp/ghostty-candidate-NEW
```

It copies current macOS sources/project/assets, applies swift510-app.patch only
in that copy, invokes the copied build.nu with isolated object/output paths,
then derives the test library link from Xcode's actual app link command, excluding
only main.o. It requires an existing universal GhosttyKit.xcframework and zig-out
resources from the current core build, and Xcode may resolve the pinned Sparkle
package. It is not a clean core build or offline toolchain/bootstrap installer.
Build inputs and resulting app/library hashes are recorded separately.

If GitHub is unavailable, --source-packages /path/to/Xcode/SourcePackages copies
an existing package cache into the candidate, requiring a clean Sparkle checkout
at the repository's pinned revision. The copied workspace-state artifact paths
are relocated, remote updates/automatic version changes are disabled, and all
consumed binary artifact hashes are recorded. This reuses Sparkle's upstream
prebuilt binary distribution, not previous Ghostty Swift objects. It does not
promise offline success if the cache is incomplete. --skip-package-updates alone
only skips updates: a new project-specific cache may still require a clone.

The candidate patch makes two Task closures explicitly MainActor and adds an
explicit TimelineView closure return for Swift 5.10.1. Three SDK-14 expressions
use a test-only GHOSTTY_TEST_SDK13 compile condition, selected only after checking
that the actual SDK is 13.x. This supersedes the earlier arbitrary compiler-6
guard experiment: compiler version is not an SDK capability check. The builder
passes the condition through inherited OTHER_SWIFT_FLAGS, preserving DEBUG and
DockTilePlugin definitions. These are experimental source-copy changes, not
approved changes to the product's compiler/runtime support policy.

The repository runner replaces the previous hand-assembled temporary test
command. It requires the experimental application module/object library from
the builder (or earlier candidate) and pinned SwiftPM Testing build; it does
**not** yet reproduce all prerequisites from a clean checkout. The runner itself
downloads no dependency or toolchain.

```sh
python3 test/macos-compatibility/native-suite/run.py \
  --swiftc /tmp/ghostty-monterey/swift5101.xctoolchain/usr/bin/swiftc \
  --candidate /tmp/ghostty-swift510-app-x8fffd_v \
  --testing-package /tmp/ghostty-testing-native-twerewif \
  --output /tmp/ghostty-native-run-NEW
```

Use a new output directory outside the worktree on each invocation. Add
`--suite transfer` for only the native surface fixture. The default copies all
original unit sources, applies swift510-tests.patch **only to those copies**,
and adds the native fixture and XCTest scaffold. The seven-file patch contains
the verified compiler/syntax/API/trait workarounds, not changed assertions.
The original test files and product code are never edited by the runner.

The candidate must provide candidate-build/Debug/Ghostty.swiftmodule,
libGhosttyProbe.dylib (real app objects without main.o), Sparkle, GhosttyKit
headers and candidate app resources. It must be the compatible Swift 5.10.1
Debug build, not the Swift 5.7 ReleaseLocal app. The SwiftPM dependency revisions
are checked against Package.resolved; input hashes identify the actual objects,
sources and module artifacts consumed. They do not prove the object library was
built from the accompanying source. The manifest also records candidate source
differences from the active tree; clean build provenance remains future work.

Each output directory contains commands.json, inputs.json, patch/build/run logs,
the private XCTest host/bundle and result.json. Compilation and execution have
600/240-second deadlines. Success requires exit 0, a real Testing final summary,
the expected named pass count, and the explicit skip inventory (284 passes and
six skips for all; one pass/no skips for transfer). A discovery count change
fails for review instead of silently shrinking coverage. Inputs/results must
not be mistaken for a release certificate or the full Xcode test action.

## Surface fixture

MontereySurfaceTransferTests links the actual Ghostty application module and
libghostty, constructs a real App and SurfaceView, runs only /usr/bin/true with
explicit isolated configuration, and waits for that child to exit. It verifies
the exact 16 UUID bytes and pasteboard type, releases the surface, and reads the
payload from a unique native pasteboard after surface teardown. Native async
NSItemProvider transport exercises the UUID decoder with 0/15/16/17-byte payloads.
No user shell, general clipboard, global input, permission request or visible
window is needed. The host must have an unlocked graphical session.

The test must run in an application bundle. Bare Xcode xctest is not a sufficient
host: SurfaceView's existing deinitializer invokes UNUserNotificationCenter,
which asserts when the current process has no application bundle proxy. Do not
remove notification cleanup or leak the SurfaceView just to make a test pass.
The temporary host wraps a copy of Xcode's xctest in a private .app with a unique
bundle identifier and links its framework search locations back to Xcode. It
does not install an app or alter Xcode/system files.

The runner must isolate user defaults/XDG config and set the candidate resource
directory, initialize libghostty with only argv[0], and enforce a subprocess
timeout (currently 240 seconds). The callback continuation intentionally uses
the real provider result; a missing callback must fail by timeout, not pass.
The fixture checks the 5-second child-exit deadline and weak surface release.

The transport portion is not a physical drag, SwiftUI DropDelegate dispatch or
source lookup test. It does not validate the
five unavailable CoreTransferable-specific tests or claim generic multi-format
Transferable parity. The Monterey product uses a specific native surface format.

The fixture now additionally calls the actual BaseTerminalController split-action
entry point with real surfaces and two private, unordered NSWindows. It checks
all four drop directions through both cross-window and same-window branches,
exact leaf order/direction, source ownership migration and unchanged core-surface
identity. Invalid destinations must leave the original trees/ownership intact.
The moved source now runs a bounded /usr/bin/perl child directly, without a user
shell. Before/after moves, fresh UUID challenges sent through ghostty_surface_text
must be read on the same PID/tty and acknowledged in a private file. The child
exits on an explicit quit line and its disappearance is checked. Destination
fixtures run /usr/bin/true. This establishes live controller-move PTY continuity,
not undo/redo, SwiftUI DropInfo delivery or physical dragging.
The controller tests are a separate downstream seam, not proof that the provider
callback and controller dispatch are connected correctly during a real gesture.

In Xcode-hosted mode, the fixture also obtains the real AppDelegate's shared
ExpiringUndoManager from both controllers. All four cross-window moves are
undone/redone, checking exact restored trees and ownership. Same-window moves
reverse direction before undo so a no-op cannot satisfy the restoration check.
Every undo/redo checkpoint requires a fresh acknowledgment from the same live
PID/tty. Explicit groups avoid async run-loop grouping ambiguity; the fixture
restores the grouping policy and removes only its controllers' registrations.
The standalone host has no AppDelegate/undo manager, so this extra coverage is
deliberately compiled only in hosted mode. It does not validate menu routing,
focus restoration, undo expiry during a drag, or real gestures.

## Candidate termination dialogs

```sh
python3 test/macos-compatibility/native-suite/termination-check.py \
  --unit-output /tmp/ghostty-monterey/rebuilt-all-inputs-tests-01 \
  --output /tmp/ghostty-termination-NEW
```

This compiles TerminationProbe.swift against the same app-object library recorded
in an accepted unit-run output. It executes the actual candidate AppDelegate
termination/review methods and BaseTerminalController.confirmCloseAsync, drives
native alert buttons inside its own process, and checks deferred/synchronous
replies, sheet cleanup, sequential reviews and per-window close counts. It may
briefly display private alerts; it does not send global keyboard/mouse events.
An unlocked graphical session is required. A 30-second subprocess timeout handles
even a nested modal loop that prevents the main-queue watchdog from running.

Explicit test boundaries: the controller subclass supplies the confirmation
predicate with empty surface trees (no shell/PTY); the NSApplication subclass
records reply(toApplicationShouldTerminate:) instead of actually quitting. The
probe calls terminate() directly, not applicationShouldTerminate's update/logout
policy or the application's full launch/quit lifecycle. Thus it checks the two
candidate MainActor Task changes at their real native dialog seam, not process
kill, restoration, physical interaction or overall release readiness.

Add --negative with a different output directory to reverse one expected reply
only in the copied probe. Success for that negative control requires the exact
assertion failure and exit 1, not a compiler error, timeout or crash. Normal
success requires all six scenario labels and exit 0. Original/candidate product
sources and actual application termination behavior are never patched.

Add --real-child to run TerminationChildProbe.swift instead. This constructs an
actual BaseTerminalController/SurfaceView/PTY and a directly launched bounded
Python child (no user shell). With confirm-close-surface=always it verifies the
real surface, controller and app confirmation predicates, then calls the actual
applicationShouldTerminate method. Cancel preserves the running child; accept
returns true at the recorded NSApplication reply boundary. Explicit window and
controller teardown then releases the surface and reaps the owned child, and
the app's subsequent quit policy returns terminateNow. The outer runner also
checks child disappearance, including the negative-control exit path.

This stronger mode still intercepts the final application reply; it does not
claim an end-to-end NSApplication.terminate shutdown. It covers one real surface,
not the updater/logout bypasses, multi-surface process teardown or restoration.
The existing six-scenario mode remains the multi-window dialog-sequencing check.
