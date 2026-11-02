# Building and packaging the Monterey adaptation

`STATUS.md` lists evidence and known limitations. The distribution target is
ReleaseLocal; the user excludes app signing and notarization from verification.
No Developer ID, notarization or Gatekeeper-approval gate is required for that
scope. Existing ad-hoc build mechanics and package integrity checks remain.
Only macOS 12 is the required runtime target. The baseline is official Ghostty
1.4, not the earlier fork's reduced feature set.

## Local toolchain

Verified build host: Intel macOS 12.7.6, Xcode 14.1, Swift 5.7.1, macOS SDK 13.0.
Use Zig **0.17.0** for this source revision, not the older fork's 0.15.2.
Nushell 0.102.0 runs on this host. Python checks/package tooling require 3.9+.
Check downloaded toolchains against their upstream checksums where published.

### Bounded throughput observations

After building, run sequentially with other GUI probes:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --throughput
```

The isolated app runs ASCII, ANSI-color and Unicode PTY output in three rounds.
Each workload reuses a roughly 4 MiB buffer for two seconds (at most 128 buffers),
with nonblocking writes and a 25-second write/response deadline. Cursor-position
responses before and after each workload fence parser consumption. Missing or
malformed responses fail, rather than counting successful writes as consumption.
The child restores its terminal settings in finally; no global input or clipboard
access is used. app-smoke owns app cleanup if the child/subprocess fails.

throughput-resources.json in the printed artifact directory records each rate,
sampled RSS/CPU, terminal size, OS/architecture, source label and copied executable
hash. These are observations, not speed thresholds. DSR does not wait for GPU
completion or display presentation; sampled RSS is not peak/GPU memory; process
CPU includes setup/scripting/sampling overhead. Repeated lines are a narrow
workload, not a representative whole-product benchmark. There is no official 1.4
same-host baseline, frame-pacing proof, thermal soak or arm64 claim.

### Build commands

```sh
zig version
xcodebuild -version
zig build -Demit-macos-app=false -Doptimize=ReleaseFast -Dxcframework-target=universal --summary all
nu macos/build.nu --configuration ReleaseLocal
python3 test/macos-compatibility/bundle-check.py macos/build/ReleaseLocal/Ghostty.app
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app
```

Use the current core, not a GhosttyKit.xcframework left by a previous source
version. The native build wrapper stamps version/build/source metadata before
Xcode signs the app. A modified/untracked worktree produces a `-dirty` revision.
Use full git history for the commit-count build number; release numbering must
remain monotonic. The wrapper rejects shallow clones before invoking Xcode;
fetch full history (`git fetch --unshallow`) first. This prevents undercounted
build numbers, but does not establish monotonicity across rebases or branches.
An exported tree without git metadata is not supported by
this wrapper.

`python3 test/macos-compatibility/build-metadata-check.py --nu /path/to/nu`
checks clean/dirty identities, shallow-history refusal and full-history recovery
using local disposable Git repositories. It runs the actual wrapper with only
the Xcode launch intercepted; it does not compile, sign or fetch from a network.

`ReleaseLocal` retains the upstream ad-hoc framework-loading entitlement. Do
not substitute a stricter ad-hoc `Release` bundle without proving embedded
framework loading on a standard machine. No Developer ID credentials or
notarization are provisioned here. The builder disables accidental profiling
and debug entitlement injection for non-Debug build/archive actions.

### Monterey unit tests

The repository entry point below runs the original unit suite through Xcode 14
on Intel Monterey, using explicit Swift 5.10.1 rather than replacing system Swift:

```sh
python3 macos/test-monterey.py \
  --swiftc /path/to/swift-5.10.1.xctoolchain/usr/bin/swiftc \
  --nu /path/to/nu \
  --core-root /path/to/current-core-source-tree \
  --source-packages /path/to/Xcode/SourcePackages \
  --skip-package-updates \
  --output /tmp/ghostty-unit-NEW
```

The core tree must contain current macos/GhosttyKit.xcframework and zig-out;
build-core.py can create it separately without replacing the active product.
An external core snapshot must have that builder's successful inputs/result
manifests. The workflow checks core-source inventory/current hashes and installed
artifact hashes before/after building, rejecting stale or altered inputs.
Using the current worktree as the core root records that its normal Zig build
has no verified source-to-artifact manifest; it is not mislabeled as a fresh
snapshot. External manifests provide local consistency, not publisher trust.
The package cache must contain the pinned Sparkle checkout and binary artifact.
Without --testing-package, the command rebuilds pinned Testing/Syntax objects;
--skip-package-updates uses cached source revisions where available, not previous
compiled objects. Alternatively --testing-package explicitly selects an existing
verified dependency build. Missing sources may still require network access.

The entry point prepares current Swift sources in an isolated copy, applies the
documented compiler/SDK/test adaptations there, and lets Xcode compile the app
and unit target once. It no longer needs a prebuilt experimental app or a manually
assembled test command. All 27 original unit source files and two native fixtures
are compiled; acceptance requires 284 named passes, the six exact skips, and a
successful XCTest scaffold in xcresult. Xcode 14 reports one scaffold method,
not individually selectable Testing cases. Logs/hashes/xcresult remain in output.

This is a candidate unit-test workflow, not a ReleaseLocal binary test or full
UI action. It requires an unlocked graphical session, launches a private real
app host, and may log notification authorization denial. It sends no global
input and changes no system appearance or compiler installation. Product files
are not patched in place. Do not ship its Debug app with the embedded test bundle.

The upstream Swift test invocation remains `nu macos/build.nu --action test`.
It is not currently green on Xcode 14: Swift Testing and newer UI-test APIs need
further work. The narrower compatibility scripts are supplementary evidence,
not permission to remove or silently skip upstream tests. A failed Xcode test
build may leave an unsigned `.xctest` inside its host app; the bundle checker
rejects it. Keep test/build outputs separate before preparing distribution.

See TEST-TOOLCHAIN.md before trying a newer compiler: Swift Testing's deployment
minimum, the toolchain's host requirement and Xcode's test runner are separate
constraints. The inspected Swift 6.0.3 compiler/SwiftPM binaries require macOS 13;
their installer accepting older systems does not establish Monterey support.
The temporary Swift 5.10.1 app-object experiment now runs all 27 candidate unit
sources with real macros/XCTestScaffold (283 named passes, five unavailable API
skips and one upstream-disabled benchmark). It is not yet a supported replacement
for the build wrapper's test action or coverage of native Monterey surface drops.
Adding the real SurfaceView native-transfer fixture gives 284 named passes and
the same six skips in a private application-bundle host. It covers transport and
teardown, not physical drops. See TEST-TOOLCHAIN.md for candidate-only changes and
the host/lifecycle limits; native-suite/README.md describes the additional fixture.
The repository-owned native-suite/run.py now repeats full/targeted candidate
unit runs from fresh test copies. It requires explicit prebuilt candidate and
Testing inputs and writes isolated logs/manifests; it does not replace the app
build or the original Xcode test action. See native-suite/README.md for commands.
native-suite/build-candidate.py now reproduces the Swift candidate app/object
library in an isolated source copy through build.nu, retaining existing core
and resource inputs. The fresh candidate builds and passes the same unit suite;
it does not promote its five compiler/SDK workarounds into the release product.
native-suite/build-testing.py separately rebuilds pinned Testing/Syntax sources
into fresh objects. The full candidate runner passes against both rebuilt app
and dependency inputs. --skip-update can use existing source-cache commits when
remote refresh is unavailable; it does not reuse compiled objects or guarantee
offline operation. Commands and provenance limits are in native-suite/README.md.

native-suite/build-core.py now reconstructs the universal ReleaseFast core and
resources from a current-source snapshot with empty compiled caches, sharing only
dependency source packages. The first successful run completes all 333 build
steps and records both architecture slices and 925 artifact hashes. Pass its
`source` directory via build-candidate.py --core-root to avoid using the active
worktree's prebuilt framework/resources. This is a dirty development snapshot,
not an immutable release identity or an automatically validated candidate app.

`python3 test/macos-compatibility/quit-app-check.py <Ghostty.app>` verifies real
confirmed quit in a private resigned copy, using existing Accessibility permission
and an unlocked session. It invokes only that process's Quit menu and native
Cancel/Terminate buttons, checks a live PTY heartbeat after cancellation, then
requires app exit 0 and child disappearance after acceptance. No app callback is
intercepted, global input sent, clipboard accessed or permission requested.
`--negative-cancel` deliberately omits the Cancel press and must fail with
"Quit sheet survived cancellation"; the runner still tears down its private app.
Logs/source binary hash remain in the printed temporary directory. This covers
one window/child and is not physical-input, multi-window or updater/logout QA.

Add `--multi review` to create two actual windows/PTYs, cancel the initial quit
dialog and the first reviewed sheet (checking fresh heartbeats from both), then
accept the two reviewed sheets sequentially and require final app/child exit.
`--multi direct` covers Cancel followed by Terminate Processes without review.
`--multi review --negative-review-cancel` omits the reviewed Cancel press and must
fail the sheet-disappearance assertion. These modes cover two-window shutdown,
not physical input, updater/logout or arbitrarily many windows/splits.

`python3 test/macos-compatibility/ui-wait-check.py` type-checks the existing
palette/mouse/tab/title/window UI test sources for both Monterey architectures
and runs their predicate-wait helpers with real XCTest in both optimization
modes. State transitions use a local fixture, not XCUI automation. Newer sleep
calls now use the equivalent cancellable nanosecond API, and wait assertions
retain their original deadlines. The remaining theme tests still require the
unavailable XCUIDevice appearance API; they are not removed or skipped to make
this check green. This is not a full test-target build or UI-test run, and does
not resolve the separate Swift Testing compiler dependency.

The Debug app can also exercise Swift runtime exclusivity checks that optimized
ReleaseLocal runs may not expose (the linked core still uses the previously
built configuration):

```sh
nu macos/build.nu --configuration Debug
python3 test/macos-compatibility/app-smoke.py macos/build/Debug/Ghostty.app --automation --clipboard-protocol --titlebar tabs --fullscreen true --fullscreen-tabs
```

Debug is not a distribution artifact; do not apply the release entitlement
audit or package it as a release. GUI probes share an isolated identifier and
must run sequentially regardless of configuration.

The smoke launcher strips inherited Ghostty resource paths, terminfo overrides,
shell startup overrides and DYLD injection/search paths before launching its
copy. Test XDG config/cache/state variables point under the printed artifact
directory. This prevents an installed parent terminal from supplying resources
that hide omissions in the copied bundle. HOME and the macOS login session are
not changed: Cocoa defaults, Metal caches, saved state and Sentry's native cache
path are not fully filesystem-isolated by XDG variables. Do not describe this
fixture as a clean-machine or sandbox test. The shell-integration mode checks
the actual child's resource and terminfo paths, not just launcher intentions.

The actual command palette also has a full-app AX check (existing Accessibility
permission required, without requesting consent or posting global events):

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --palette
```

It opens the real overlay through its binding action, checks automatic field
focus, changes queries through AX, checks no-match filtering, and presses New
Tab. Two cycles require exactly one new tab, dismissed overlay, terminal focus,
a working child PTY and recovery of the original surface after closing the tab.
On this host AXPress reports attributeUnsupported despite executing the action;
the fixture does not retry and uses the actual app outcome for acceptance.
This is not physical key/IME, all palette commands, or pixel-level validation.

For a compositor-output check using existing Screen Recording permission:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --pixels
```

This captures only the isolated app's single visible window, never the desktop
or other windows. A real PTY prints RGB background blocks and Unicode samples;
interior pixel counts must transition blank/color/blank. PNGs remain in the
smoke directory for visual inspection. The border is excluded to avoid counting
window chrome. The same probe uploads a red Kitty image, replaces its data with
green (which removes its old placement), explicitly places it again, and deletes
it. Captures must show red/blank/green/blank, proving actual texture presentation
rather than just protocol acknowledgements. No permission request or settings change is made. Counts prove
visible color output and clearing, not glyph shaping, exact color management,
all GPU paths, or visual acceptance of the Unicode samples. Run this standalone,
without renderer-stress backgrounds/shaders that would invalidate its blank
control.

The probe then reloads a solid-blue custom shader and separately a solid-blue
PNG background in stretch mode. Each must produce blue over more than half the
captured window and return to the blank control after removal. Temporary config
is restored in finally blocks; no restart, forced redraw or product test hook is
used. This verifies those live rendering paths, not animation, shader uniforms,
multi-pass sampling, transparency or every background fit/blend mode.

For bounded resource observations during real terminal lifecycle operations:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --lifecycle
```

Four batches each create a split, tab and window, close them, and require all
three child processes to exit within the existing ten-second deadline for the
five-second undo timeout. The original surface, process and PTY must survive.
The first batch warms lazy allocations. `lifecycle-resources.json` records RSS,
process CPU time, descriptor and thread counts before/open/settled/idle; companion
`lifecycle-*-fds.txt` files retain descriptor types and names. These measurements
are observations, not numerical performance acceptance thresholds or proof of
no leaks. No App Nap override/activity assertion is used. Run GUI tests serially.

System-zsh integration:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --shell-integration
zig build test -Dtest-filter=termio.shell_integration --summary all
```

This uses `/bin/zsh` with a temporary ZDOTDIR rather than personal startup files.
It checks installed integration hooks, OSC 7 directory propagation and live
split/tab/window directory inheritance before the ordinary smoke checks. The
expanded fixture passes on the current host (`shell-inheritance-current.log`);
earlier first-event automation timeouts are recorded in STATUS.md rather than
being treated as cwd failures. Disabled-integration negative control fails
on missing hooks. It does not verify every supported shell, physical prompt
navigation, or sudo/SSH wrappers. Existing smoke invocations retain `/bin/sh`
and disabled integration, so this does not replace their coverage.

Native configuration bridge checks (requires the freshly built universal core):

```sh
python3 test/macos-compatibility/config-check.py
python3 test/macos-compatibility/config-check.py --menu-shortcuts
```

This compiles the complete Swift config/input implementations against the actual
GhosttyKit archive, runs 43 upstream configuration test invocations through a
bounded adapter, and checks duration units, UInt32 limits, reload and clone
ownership. Both Swift optimization modes reject compiled wrong-unit and
optional-integer-storage mutants. The linked core retains its own build mode;
these are not two core optimization configurations. TemporaryConfig supplies
explicit temporary files; no personal config or Apple events are needed.
Additional checks exercise the actual child-exit message consumer at the
configured threshold, signed coordinate limits, quick-terminal tagged sizes
and axis mapping, floating-point animation duration, and resize duration units.
Only FullscreenMode's cases are extracted because fullscreen execution is
outside this fixture. This does not replace the full Xcode test suite.

The optional menu checks compile the unchanged MenuShortcutManager against
AppKit and the real config/input bridge. They adapt all 15 upstream shortcut
tests (serial main-actor calls instead of async actor hops, and a controller
selector spelling without linking that controller). Additional real NSMenu
actions check physical-over-Unicode precedence, disabled items, registration
replacement, detached/released items, reset and config unbinding. A compiled
mutant bypassing the enabled-item guard must fail. Events are created in-process;
this does not prove physical keyboard dispatch, IME or a different keyboard
layout, and it does not change the user's input source or application menu.

## Archive round-trip validation

For the remaining search-field bridge scope review:

```sh
python3 test/macos-compatibility/search-state-check.py --compare-upstream-fallback
```

This compares the real SearchState and native SwiftUI field with just the
selection background removed in a temporary source copy. It reports selection,
typing replacement and same-turn editor/model convergence instead of assuming
the upstream fallback is equivalent. All pasteboard operations use a unique
fixture board, not the user's find/general clipboard. Both optimization modes
run the nine adapted upstream state tests first. This is not full-app search,
physical IME, newer-OS or performance evidence; no product source is changed.

The optional AX snapshot has been separated by user decision. Its prior
cost probe and sources are archived under optional-ax/; snapshot-cost-check.py
now exits explicitly as inapplicable rather than reporting a passing skip.
The core/header files touched only by that experiment match official 1.4.
Small UTF-16 count/line fixes remain. The strict Services --selection diagnostic
still exposes inherited cell-offset defects and is not a release acceptance
pass. Earlier snapshot-era passing results below are historical evidence only.

Check resource retention and relocation independently of the build directory:

```sh
python3 test/macos-compatibility/resources-check.py macos/build/ReleaseLocal/Ghostty.app
```

This compares all ten generated resource-folder memberships with official 1.4,
then their complete file hashes with current zig-out/share inputs. Shell scripts
and the scripting dictionary also compare directly with current source. A signed
temporary copy outside the repository must discover all bundled themes without
GHOSTTY_RESOURCES_DIR, load sampled themes by name, reject a nonexistent theme,
and provide both terminfo names to Monterey's system infocmp. No GUI, clipboard,
preferences or installations are involved. This does not prove every theme's
visual appearance, every shell's runtime integration, or fresh generation of
all zig-out inputs; keep the normal core-build requirement.

Native Zig framework-wrapper and targeted renderer regression checks:

```sh
(cd pkg/macos && zig build test -Dtarget=x86_64-macos.12.0 --summary all)
(cd pkg/macos && zig build test -Dtarget=x86_64-macos.12.0 -Doptimize=ReleaseFast --summary all)
zig build test -Demit-macos-app=false '-Dtest-filter=kitty renderer' --summary all
zig build test -Demit-macos-app=false '-Dtest-filter=shadertoy to msl' '-Dtest-filter=custom shader selection' '-Dtest-filter=preedit range' '-Dtest-filter=renderCellMap' --summary all
```

The wrapper commands above are for this Intel host; use the native architecture
on Apple Silicon. Renderer tests exercise CPU state/translation, not live GPU
presentation. Reported aggregate counts include dependency tests and are not
counts of newly added assertions or distinct cases across separate runs.

To exercise packaging during development without pretending the worktree is a
release, choose a new directory outside the repository:

```sh
python3 macos/package-monterey.py --development \
  macos/build/ReleaseLocal/Ghostty.app /tmp/ghostty-package-trial
```

The ZIP is explicitly named `NOT-FOR-RELEASE`. Packaging:

- Audits every embedded universal Mach-O and the original strict signature.
- Rejects get-task-allow in either architecture of every embedded binary, not
  just the host slice of the main executable.
- Creates a ZIP with the app as its sole root, without modifying/re-signing it.
- Extracts and audits the ZIP, comparing every file hash, mode and symlink target.
- Refuses concurrent source changes or an existing output directory.
- Writes `manifest.json` and `SHA256SUMS.txt` beside the ZIP.

This is repeatable packaging with content-integrity checks, not a claim of
bit-for-bit reproducible compilation or timestamp-independent ZIP bytes.
The manifest records build identity and content, not an attestation that the
binary was compiled from every current source file.

`python3 test/macos-compatibility/bundle-entitlements-check.py <app>` verifies
the nested entitlement refusal using a disposable, correctly re-signed Dock
plugin with get-task-allow. The signature must remain valid so a failed resource
seal cannot masquerade as an entitlement-policy test. The original bundle is
not modified. This checks debug attachment policy, not every entitlement or
Developer ID/notarization trust.

```sh
cd /tmp/ghostty-package-trial
shasum -a 256 -c SHA256SUMS.txt
```

`package-check.py <app>` also tests refusal paths (including dirty release
metadata and tampered sealed resources) and runs automation, text-reader,
live scripting-policy, clipboard-protocol, renderer and Inspector checks on an
extracted archive. The standard smoke also checks the idempotent quick-terminal
command. Two earlier runs passed the then-current expanded check
without activity assertions or timeout changes (`package-current-check.log`,
`package-current-repeat.log`). Earlier background/occluded runs exposed delayed
closed-split expiration; see `STATUS.md` for the scheduling controls and remaining
qualification. Do not treat a static round trip alone as an archive-runtime pass
or these successful runs as proof that all lifecycle conditions are resolved.
The GUI smoke uses a re-signed test-only bundle identifier and requires
a logged-in GUI session/Automation permission. It does not test Gatekeeper,
notarization, physical keyboard dispatch, all UI operations, or arm64 runtime.

To include the newer acceptance checks against the same extracted artifact:

```sh
python3 test/macos-compatibility/package-check.py macos/build/ReleaseLocal/Ghostty.app --extended
```

After the original renderer/Inspector/automation/protocol smoke, this checks
resource retention and relocation, then runs palette, lifecycle and compositor
checks together in a second isolated app. Runs are sequential; the pixel blank
controls do not share renderer-stress's background configuration. Existing AX
and Screen Recording permissions are required in addition to Automation; no
permission prompts or settings changes are made. The archive remains a temporary
NOT-FOR-RELEASE artifact, and failure of any stage fails the overall command.

When expiry timing fails in a fully occluded/locked GUI session, run the native
scheduling control separately (about two to three minutes):

```sh
python3 test/macos-compatibility/scheduling-check.py
```

This builds a temporary AppKit-only app, then measures a five-second timer and
a worker's requested ten-millisecond sleep, without Ghostty code. It runs
ordinary/activity/ordinary controls and prints actual durations. The temporary
activity is limited to the middle control process; no global power setting or
product behavior changes. On this locked Monterey host, ordinary sleeps reached
8.85 and 9.82 seconds while the middle control took 15 ms. Treat this as evidence
of scheduling interference, not a passing Ghostty lifecycle test. The original
combined-smoke timeout remains unchanged; an unlocked-session comparison is
still required before deciding whether a product change is warranted.

Session restoration checks (run sequentially, not alongside the GUI smoke):

```sh
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar native
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --selected-tab beta --front-window tabbed
python3 test/macos-compatibility/restoration-order-check.py
```

The app test restarts an isolated copy three times and checks window/tab/split
structure, selected tab, focused split, ordering and window-save-state=never.
It does not imply fullscreen/Spaces or shell-process restoration coverage.
The native restoration-order fixture also exercises a minimized tab group:
selection must remain minimized, repeated selection must not expand it, and
the chosen tab must persist after deminiaturization. This is not across-launch
minimized-state decoding or a proof of animation/focus behavior when unlocked.

The optional Debug-only across-launch minimized check uses LLDB solely to
schedule AppKit miniaturization and read window state in the isolated test app:

```sh
python3 test/macos-compatibility/session-check.py macos/build/Debug/Ghostty.app --minimized-tabs
python3 test/macos-compatibility/session-check.py macos/build/Debug/Ghostty.app --titlebar tabs --selected-tab beta --minimized-tabs
```

It refuses an app without the debugger entitlement before copying or launching
it; release signing policy is unchanged. LLDB schedules operations on the main
operation queue, detaches, and the app writes test-only state snapshots. The
restoration and shell/PTY paths are production code. Physical Dock actions,
animation/focus and debugger-free Release behavior are not established by this
Debug probe. Run sequentially with all other GUI fixtures.

Optional live fullscreen checks:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --fullscreen true
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --fullscreen true --fullscreen-tabs
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --fullscreen false --fullscreen-tabs
python3 test/macos-compatibility/fullscreen-frame-check.py
```

The `--fullscreen` values match `macos-non-native-fullscreen`; `false` requests
native fullscreen and can switch Spaces. The check asserts geometry and live
PTY behavior, not pixels. Native fullscreen needs an unlocked GUI session; the
host was locked during the initial failing probes. Current runs pass two native
enter/exit cycles with tab groups for transparent/native/tabs titlebars, including
a tabs run with renderer stress and Inspector checks. The fixture waits for the
frame to change as well as approach display size; a maximized old frame must not
satisfy the entry predicate before the native animation starts. See `STATUS.md`
for logs and limitations. Multi-display Spaces/restoration and physical input
remain separate acceptance checks.

Search field selection checks:

```sh
python3 test/macos-compatibility/search-selection-check.py
python3 test/macos-compatibility/search-selection-check.py --same-turn-replacement
```

The second command checks the same-turn SwiftUI consistency workaround and an
unbridged control (the control must reproduce the failure). See `STATUS.md` for
its exact scope, remaining SwiftUI diagnostics and full-app validation gaps.

The real search-state/pasteboard integration has a separate bounded harness:

```sh
python3 test/macos-compatibility/search-state-check.py --ablate
python3 test/macos-compatibility/search-state-check.py --same-turn-replacement --ablate
```

The normal suite includes nine unchanged upstream SearchState tests and a real
SwiftUI field with the production nested needle bindings. The same-turn variant
now verifies recovery across 20 consecutive edit/external-write races and rejects
a compiled no-reconciliation mutant. All pasteboard writes use unique test boards.

Native MIME helper checks (no user clipboard writes):

```sh
python3 test/macos-compatibility/pasteboard-mime-check.py
```

This covers real lazy providers, metadata-only enumeration, text/binary/file
representations and production MIME mapping in both optimization modes. It
does not substitute for end-to-end OSC 5522 or clipboard-permission UI checks.

Safe OSC 5522 negative/error wire-path checks:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --clipboard-protocol
```

Standard clipboard operations are explicitly denied; allow-stage requests only
target the unsupported primary clipboard. The test checks EPERM, ENOSYS, EFBIG,
EINVAL, terminators, IDs and recovery via actual PTY replies without reading or
writing the user's standard clipboard. Success does not validate allowed
multipart clipboard transfers or ask/remember permission UI.

Native link cursor registration/lifecycle checks:

```sh
python3 test/macos-compatibility/pointer-check.py
```

The test observes real AppKit cursor rectangles without moving the mouse or
changing the global cursor. Physical hovering over the composed app UI still
requires an unlocked GUI session.

AppleScript configuration and real child-process automation checks:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --automation
```

See `AUTOMATION.md` for the Monterey Shortcuts bridge, distinct permission
policies and limits. This probe does not execute a Shortcut.

Host-system symbol resolution (run on macOS 12, report outside the repo):

```sh
python3 test/macos-compatibility/symbol-check.py macos/build/ReleaseLocal/Ghostty.app --report /tmp/ghostty-system-symbols.json
```

This checks the executing architecture's required system imports in all bundled
Mach-O files against installed system libraries, including the shared cache.
The report lists absent weak imports for guarded-call review. It does not load
bundled executables/plugins, check Objective-C selectors, validate other OS 12
patch releases, or substitute for native arm64 execution. Library-scoped dlsym
can search dependencies, so this is not a complete dyld two-level binding proof.

Command palette upstream assertions and native hosted UI checks:

```sh
python3 test/macos-compatibility/palette-check.py
```

This compiles the complete production palette view, real color helpers and
the production terminal-option sort function. It runs three upstream test
bodies with a bounded Swift Testing adapter, native field editing and explicit
hosting-view key equivalents in both optimization modes; no-submit/no-down
mutants must fail. Physical keys, IME, automatic focus and full-app event
routing still need an unlocked-session test.

Services provider and native pasteboard checks:

```sh
python3 test/macos-compatibility/services-check.py
```

See `AUTOMATION.md` for the recorded-construction boundary and the unresolved
selected-plain-text Services route; Finder file-list routing is not proof of
every advertised Services input representation.

Across-launch fullscreen session checks (standalone front window):

```sh
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --fullscreen true
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --fullscreen visible-menu
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar native --fullscreen padded-notch
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --fullscreen visible-menu --fixed-window-geometry
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --selected-tab beta --fullscreen false --launch-via launchservices
```

These assert restored geometry/order, exit back to the pre-fullscreen frame,
live restored PTY and the existing tab/split/never-restore assertions. They do
not test multiple displays, notch hardware or minimized restoration. The native
case (`false`) requires an unlocked session and switches Spaces. Native restoration
passes through LaunchServices with tabs and native titlebars. A locked session
fails preflight before app launch. `--launch-via launchservices` uses `open -W -n`
and resolves the unique isolated app PID for geometry/debugging. The default
direct-executable path also passes tabs/native-titlebar fullscreen restoration
after the CLI activation fix. Omit `--launch-via` to exercise it. Revealed native
titlebars can be separate WindowServer
windows; the fullscreen assertion compares their combined display extent while
regular/exit frames still require the original two-window geometry.
Use `--fixed-window-geometry` to require a non-maximized 80x24-cell window with
explicit offsets. This avoids masking lost exit geometry with the saved maximized
default. Non-native fullscreen saves its regular rectangle separately and seeds
the entry state after AppKit restoration, retaining the normal toolbar/content
geometry exit calculation.

The native case also accepts `--front-window tabbed`, exercising restoration of
the fullscreen tab group itself (not just an ordinary group beside a fullscreen
standalone window). The exact-exit-frame regression found by this case is fixed
by saving the pre-native-fullscreen rectangle and seeding it before AppKit
restores the group. The fixture also checks tab order/selection and frontmost
window after exit. Old archives without the additional optional rectangle retain
AppKit's previous behavior; their lost exit rectangle cannot be reconstructed.

```sh
python3 test/macos-compatibility/fullscreen-restoration-frame-check.py
```

This bounded native fixture extracts production capture/encode/decode/seed code
and runs it with real NSWindow tab groups and secure NSCoder. A window subclass
reports fullscreen membership without attempting a real Space transition; the
controller is a shell. It covers sibling-frame inheritance, absent/invalid frames,
non-native exclusion and omission of stale frames from ordinary state. Both
optimization modes reject compiled no-seed and negative-size-validation mutants.
The fixture also checks the non-native post-AppKit rectangle seed, invalid frames,
and a compiled no-non-native-seed mutant; shell controllers do not exercise the
full fullscreen lifecycle, which remains covered by the app session fixture.
Use the session fixture, not this unit boundary, for actual fullscreen acceptance.

To exercise a newly created tab inheriting a fullscreen group's regular frame:

```sh
python3 test/macos-compatibility/session-check.py macos/build/ReleaseLocal/Ghostty.app --titlebar tabs --selected-tab beta --front-window tabbed --fullscreen false --fixed-window-geometry --replace-fullscreen-tab
```

This replaces beta while fullscreen, then retains all grouping/selection/exit-frame
and PTY checks across restart. Its functional assertions pass, but the run exposes
an AppKit layout recursion warning that is not covered by those assertions.

Independent native accessory diagnostic (requires unlocked session):

```sh
python3 test/macos-compatibility/accessory-layout-check.py
```

The static/dynamic/static sequence uses no Ghostty implementation. Changing the
SwiftUI content of a titlebar accessory while native fullscreen reproduces the
warning; static controls do not. This demonstrates a native OS path, not a waiver
for product UI/performance validation. The probe checks real fullscreen entry,
tab joining and exit, but does not inspect pixels. No workaround is installed.
It also asserts that the accessory reaches its fitting size, collapses to zero
when hidden, and re-expands to the original size. These checks reject workarounds
that merely silence the warning by freezing the accessory's layout.

Historical session archive compatibility (no app launch or unlocked session needed):

```sh
python3 test/macos-compatibility/restoration-codec-check.py
```

Runs all three upstream restoration migration tests against their four embedded
archives (quick terminal v1, terminal v5/v7 and generic v7), the unchanged
CodableBridge and extracted production state schemas. It also checks current
protocol round-trip fields and rejection of pre-v5 versions. The upstream
MockView/dummy states replace real terminal surfaces/controllers; enum namespaces
retain extracted version constants. A test-only class-name mapping resolves the
private generic dummy bridge during the new round trip, as the historical tests
already do for their archives. No user saved state is read or written. Both Swift
optimization modes must reject a compiled schema mutant making the v7 title
field required. This does not validate actual window placement, live surfaces,
or the complete controller restoration path.

Asynchronous surface-drop lifecycle checks:

```sh
python3 test/macos-compatibility/drop-lifetime-check.py
```

The exact production data-loading callback runs through native NSItemProviders
and the production UUID codec/surface lookup extension. App/surface shells
record identity and registry access. Test-only completion markers make negative
assertions wait for callback completion rather than an arbitrary sleep. This
does not validate physical drag hit testing or actual split-tree mutations.

Upstream update state/view-model/release-note regression checks with bundled
Sparkle (requires the adjacent build-directory framework headers):

```sh
python3 test/macos-compatibility/update-state-check.py macos/build/ReleaseLocal/Ghostty.app
```

This is a no-network state-machine check, not an updater-installation test.
See `UPDATES.md` for exact coverage and outstanding update-cycle gates.

Without `--development`, packaging additionally requires clean source-revision
metadata. That is necessary but not sufficient for publishing. Do not publish
until the functional/performance/security/architecture gates in `STATUS.md` and
the update-cycle gates in `UPDATES.md` pass. Nothing in these commands installs
the app into Applications or uploads a release.

Native permission sheets and remembered-decision cache checks:

```sh
python3 test/macos-compatibility/permission-check.py
```

This compiles the complete production permission/defaults/duration helpers in
both optimization modes. It ends only fixture-owned NSAlert sheets and uses
a unique DEBUG defaults suite, cleaned even after failure or timeout. Allow,
deny, abort, remember policy, label boundaries and deterministic TTL expiry are
checked; response-mapping and expiry mutants must fail. It does not request
system permissions or access the user clipboard, and does not substitute for
physical interaction or full-app permission-flow validation.

Offscreen execution of production Metal shaders on every local GPU:

```sh
python3 test/macos-compatibility/metal-check.py
```

Requires Xcode's metal/metallib tools. Creates all five pipeline pairs in both
production pixel formats and checks IOSurface pixel readbacks for background,
cell background, alpha composition, padding, synthetic grayscale/color glyphs,
image sampling, centered background-image opacity/repetition, cursor/wide-cursor
recoloring and exemptions, minimum contrast, linear weight correction, and
color-space/blending variants. Metal API Validation is enabled.
Both optimization modes and eight compiled shader mutants are exercised, plus
the hardware-specific AMD byte-vector regression. Swift
native descriptors mirror (rather than execute) the Zig pipeline boundary;
real font shaping/rasterization and presentation remain untested here.
No screen capture or unlock is needed. This is not end-to-end
renderer or performance evidence; see `STATUS.md` for the precise remaining scope.

Run the full-app smoke under Metal API Validation as well (uses an isolated app
copy, not the installed Ghostty):

```sh
MTL_DEBUG_LAYER=1 python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --automation --clipboard-protocol
```

Full-app renderer configuration and Kitty graphics protocol checks:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --renderer-stress
```

This option enables Metal validation/core stderr logging itself. Generated PNG
backgrounds and two chained identity shaders accompany live blending-mode
reloads, raw/PNG Kitty image placement/replacement/deletion and Unicode PTY
output. Exact Kitty replies and app liveness are asserted, not visible pixels
or completed GPU presentation. The known display-link creation fallback is
explicitly allowed; other renderer/Metal/shadertoy warnings and errors fail.
It does not use screen capture, change installed-app configuration or exercise
sleep/wake. Artifacts and core logs remain in the printed temporary directory.

Built-in/custom icon decoding and native raster composition:

```sh
python3 test/macos-compatibility/icon-check.py macos/build/ReleaseLocal/Ghostty.app
```

Uses actual app/plugin asset catalogs and complete production image/composition
helpers. Runs ten upstream test bodies through a bounded adapter, compares
app/plugin pixel data, checks built-in/frame/color variation and rejects an
ignore-frame mutant in both optimization modes. Does not update Finder/Dock
icons, post notifications, load the Dock plugin, or modify user preferences.

Production CoreText shaping, face rasterization and atlas regressions:

```sh
zig build test -Dtest-filter=font.shaper.coretext -Dtest-filter=font.face.coretext -Dtest-filter=font.Atlas --summary all
zig build test -Dtest-filter='rasterized atlas coverage' --summary all
```

Use the documented Zig 0.17.0 toolchain. The upstream build fixes the main Zig
test root to Debug even with `-Doptimize=ReleaseFast`; do not describe such runs
as optimized-core validation. The raster test uses installed Menlo and Apple
Color Emoji and checks real atlas pixels without a window or screen capture.

Real-app Inspector layout and close/undo lifecycle:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --inspector
```

Automatically enables Metal validation and core stderr logging. The isolated
shell's PTY dimensions must shrink/recover through show/hide/toggle, and an
Inspector-visible window close/undo must preserve layout and process/PTY.
Does not assert MTKView presentation, physical input routing or memory usage.

Embedded native selection, remote accessibility and committed-input checks:

```sh
python3 test/macos-compatibility/embedded-selection-check.py --accessibility --committed-input
```

Requires the current universal GhosttyKit, ReleaseLocal resources and an unlocked
GUI session. `--accessibility` uses existing AX permission only, temporarily
activates a disposable probe, and restores prior focus on normal completion.
No global mouse/keyboard events, clipboard access or default user config are
used. The child runs a raw PTY with bracketed paste enabled; committed Unicode
must arrive byte-for-byte as typed input, while preedit/cancellation emits no
input. A compiled paste-instead-of-key mutant must fail that byte assertion.

These tests extract production button, AX, preedit, insertText and committed-text methods
against the real core. Motion/cache adapters remain bounded fixtures.
Window-local key events establish NSApplication.currentEvent before calling
insertText, covering attributed strings, split UTF-16 surrogate callbacks and
key-event accumulation without forwarding accumulated text early. Compiled
lost-surrogate and bypassed-accumulator mutants must also fail. Production
keyDown orchestration, modifier mapping and native Carbon identity lookup also
run against scripted interpretKeyEvents callbacks: start/commit/cancel, composing
control suppression and post-commit arrow replay have exact PTY assertions and
three further compiled negative controls. The fixture ignores physical pointer
input and accepts only timestamp-matched local key callbacks. It does not run
the complete SurfaceView or native interpretKeyEvents, select an OS input
method, exercise candidate windows, or establish VoiceOver acceptance. The
keyboard manual gates in `test/macos-keyboard/README.md` target macOS 12 only;
13/14 runtime testing is not a release requirement for this port.
