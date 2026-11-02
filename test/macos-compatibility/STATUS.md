# Monterey 1.4 compatibility work

## Status

The reopened AX/automation follow-up is complete on the current Intel Monterey
ReleaseLocal artifact. See AX-AUTOMATION-WORK.md and RELEASE-READINESS.md for
current evidence and limits. Earlier entries below are chronological history,
not current pending gates or blanket production certification.

Latest scope and interactive evidence (2026-11-01): only Intel on this machine
is required; ARM and second-machine 12.0 checks are not gates. The user authorized
desktop control. See NATIVE-INTERACTION.md for foreground keyboard/IME and actual
native drag/menu/fullscreen results. Historical pending/manual statements below
describe their original dates, not a continuing need for user-operated testing.

Current requirement-by-requirement audit and next decisions:
[RELEASE-READINESS.md](RELEASE-READINESS.md). This separates the current artifact
from historical test runs and external/manual evidence still required.

## Final verification (2026-11-02)

See FINAL-VERIFICATION.md: fresh 284-pass/six-skip candidate unit execution,
27-method UI pass with the original fixed-width discrepancy still explicit,
rebuilt current resources and complete archive pass, and matched 30-minute load
plus 30 teardown cycles. Formal packaging remains blocked by dirty revision
metadata, not by notarization. Unfiltered upstream testing is not claimed green.
Current artifact: 8aa1ec74bb987e72cf2ecaa0a0723e2a5942d67614a14be6de779cd7fff195c2.

## Current AX scope (2026-11-01)

The user reopened selection work. The active implementation now isolates
on-demand UTF-16 mapping in AccessibilityText.zig, with a real validated setter
and separate lazy Swift AX cache. Screen/StringMap and input-method selectedRange
remain unchanged. Native rectangle/read/write and real VoiceOver selected-text
caption pass on the rebuilt app. The previous exclusion and archived patch are
historical. See AX-AUTOMATION-WORK.md for costs, limits and evidence.

## Scope clarification (2026-10-29)

Follow-up necessity audit: [PATCH-SCOPE.md](PATCH-SCOPE.md). Inherited AX defects,
optional search-selection improvements and unproven framework/harness warnings
are not automatically macOS 12 port blockers. Preserve existing work pending
separate review rather than expanding or deleting these groups implicitly.

The user clarified that **macOS 12 is the only required runtime target**.
macOS 13/14 and later are not release-validation requirements. Keep upstream
code where practical, but do not add compatibility layers or testing obligations
solely to support those systems.

Official 1.4 is the feature, architecture, and performance baseline. The old
fork's main branch is historical evidence about building and distributing on
Monterey, not the implementation template or the acceptable feature ceiling.
Reassess already ported changes against official 1.4 and actual Monterey tests.
Do not inherit feature removals or no-op fallbacks merely because main used them.

Minimize functional loss, runtime/resource overhead, patch surface, and ongoing
maintenance cost. A newer unavailable API does not by itself justify removing
the feature: first investigate a Monterey-native equivalent. Document genuinely
unavailable OS capabilities separately from features that can be reimplemented.

Baseline: upstream `83fb95624` (version bump to 1.4.0).
Historical comparison: fork `main` at `e975b2187`, based on `332b2aefc` (1.3.1).
Host inspected on 2026-10-29: macOS 12.7.6, x86_64, Xcode 14.1, Swift 5.7.1.
Installed default Zig is 0.15.2; this branch requires **0.17.0**. Do not lower
the Zig requirement or build 1.4 against leftover 1.3.1 GhosttyKit artifacts.

## Historical release findings

- The 1.3.1 fork built the Zig core with ReleaseFast and universal or separate
  architecture targets, then built Xcode ReleaseLocal and Release bundles.
- ReleaseLocal permits loading ad-hoc bundled frameworks through
  `com.apple.security.cs.disable-library-validation`. Release preserves stricter
  upstream entitlements and is not generally suitable for ad-hoc distribution.
- Historical releases were ad-hoc signed, not notarized. They included icon
  assets, version/build/commit metadata, ZIP artifacts, and SHA256SUMS.
- The previous fork removed most upstream workflows. That is not necessary for
  runtime compatibility; this work has not copied those removals.
- Runtime gates, old-SDK compilation gates, Swift syntax changes, AppKit
  transfer fallbacks, and a libc++ abort shim were part of the old patch.
  Each needs reevaluation against 1.4 rather than wholesale source replacement.
- The old patch replaced Swift Duration globally with a narrower custom type.
  This has not been copied: preserve supported-platform behavior and audit
  precision, range, clock semantics, and cancellation before choosing a backport.

## Changes and evidence so far

- Converted synchronized Xcode groups to explicit Xcode 14-compatible groups
  and build memberships, retaining current upstream sources and targets.
  `python3 test/macos-compatibility/project-membership.py` verifies 173 app,
  10 Dock plugin, 27 unit-test, and 8 UI-test members against the upstream rules.
  Run this again whenever adding files. It does not test compilation.
- Lowered project deployment settings and the shared Zig macOS minimum to 12.0.
- Converted Package.resolved schema 3 to schema 2 without changing Sparkle's
  upstream 2.9.6 version/revision. Xcode package resolution and `-list` completed
  successfully, listing all four targets and both schemes.
- Completed Swift 5.7 syntax/API adaptations needed by the app build, keeping
  official 1.4 logic rather than replacing files with historical fork versions.
  A successful build is not proof of equivalent runtime behavior.
- Ported the historical input-event translation fix while retaining 1.4's
  separate menu-equivalent translation helper.
  `bash test/macos-keyboard/native-check.sh`: 454 checks, zero failures in each
  of debug and optimized builds on this Monterey host with ABC layout.
  Native-reference comparison on macOS 14+ was not run. These tests do not
  reproduce the interactive AppKit Ctrl-event dispatch defect on their own.
- `python3 test/macos-keyboard/check.py`: 402 checks, zero failures.
  `python3 test/macos-keyboard/check.py --ablate --optimize`: production passes;
  all six single-factor mutants fail assertions (not compilation).
  Running the boundary suite against upstream NSEvent code with the Carbon
  helper present produces 214 assertion failures, confirming a red-capable test.

## Remaining release gates

1. Audit deployment requirements and linker/runtime symbols in both architecture
   slices. Zig 0.17.0 was checksum-verified; the universal core build passed
   333/333 build steps and the universal ReleaseLocal app built successfully.
2. Validate Monterey equivalents for transfer/drag-and-drop, clocks, focus,
   input, command palette, windowing, and automation. App Intents themselves
   require newer macOS; retain AppleScript/services and assess Shortcuts bridges.
3. Use `macos/build.nu` to build the app and run unit tests. Preserve meaningful
   coverage despite Swift Testing not being included in Xcode 14; merely hiding
   unsupported test sources is not equivalent coverage.
4. Run targeted Zig regression tests and native tests. Exercise the actual app:
   IME/Ctrl/Option/layout changes, shell/PTY behavior, rendering, clipboard and
   drag-and-drop, splits/tabs, quick terminal, restoration, fullscreen, services,
   AppleScript, config reload, command palette, and accessibility.
5. Compare functionality and resource behavior against official 1.4; use 1.3.1
   only as supplementary historical evidence. Validate macOS 12 on the advertised
   architectures; this Intel host alone cannot prove Apple Silicon runtime
   correctness. Newer macOS runtime validation is outside the required scope.
6. Define safe fork update behavior so Sparkle cannot replace the Monterey app
   with an incompatible official build. Preserve signing/update validation.
7. Make release packaging reproducible. Verify all embedded Mach-O slices and
   minimum OS versions, dynamic dependencies, metadata, icons/resources,
   signatures/entitlements, clean-machine launch, ZIPs, and checksums. Clearly
   document ad-hoc versus Developer ID/notarized distribution limitations.

## Temporary local work

Downloads and logs are outside the repository in `/tmp/ghostty-monterey`.
Zig 0.17.0 downloaded and runs on this host. Its archive SHA256 matches the
official download index:
`4f9a1c5269aa17ebda5e6d3c2b89d6cbf36f7d2b22a0306e9ab98f25f95529c6`.
The executable is `/tmp/ghostty-monterey/zig-x86_64-macos-0.17.0/zig`.

Old SDK issues were resolved without disabling rendering: omit Objective-C
CALayer.h from C translation (keep QuartzCore/objc access), and supply missing
CoreVideo FourCC constants. `/tmp/ghostty-monterey/core-verify.log` records
333/333 successful steps for the universal ReleaseFast core.

Nushell 0.102.0 runs from `/tmp/ghostty-monterey/nu-0.102.0-x86_64-apple-darwin/nu`.
`app-build-4.log` records a successful universal ReleaseLocal app build. Deep
strict codesign verification passed; the executable reports Ghostty 1.4.0,
CoreText/Metal/kqueue, with x86_64 and arm64 slices and minimum OS 12.0.
No app was installed, no release uploaded, and no commit created by this work.

## Additional local compatibility evidence

- Expanded Swift 5.7 syntax adaptations without replacing current 1.4 logic
  with old fork files. Native type-checking now reaches runtime API availability
  errors, including ContinuousClock and Task sleep. The diagnostic-only command
  in `/tmp/ghostty-monterey/typecheck.py` uses the current C header but an old
  local Sparkle framework for imports; it is not release build evidence.
- Replaced the 16-byte surface drag payload bridge with native NSPasteboardItem
  and asynchronous NSItemProvider loading. Kept format and main-thread surface
  lookup; malformed UUID data is rejected without an unaligned memory load.
  Interactive split drag/drop is still unverified.
- Added an explicit GhosttyDuration value for configuration/ABI intervals,
  rather than shadowing Swift.Duration globally. Exact comparisons support the
  full UInt64 millisecond/nanosecond inputs without narrowing them to signed
  nanoseconds. Foundation supplies localized Monterey duration descriptions.
  GhosttyInstant uses CLOCK_MONOTONIC_RAW to include sleep without wall-clock
  adjustments. Cache reads enforce TTL; generation checks prevent stale timers
  from evicting replacement values. Actual sleep/wake remains untested.
- `bash test/macos-compatibility/value-check.sh` passes debug and optimized
  native runs: duration boundaries, narrow integer inputs, negative intervals,
  2,001 precision/comparison cases, fixed UUID byte order, malformed lengths,
  sliced data, and 1,000 UUID round trips. This does not prove drag UI behavior.
- `bash test/macos-compatibility/security-check.sh` passes 115 checks in each of
  debug and optimized native runs. Covers URL policy, executable/symlink denial,
  preview normalization, control-character rejection, decoded URL paths, and
  actual `/bin/sh` argument round trips including Unicode and metacharacters.
  Fixed a real Foundation-version difference: Monterey rejects raw bidi URL
  scalars rather than percent-encoding them, so preview must retain a rejected
  scheme-bearing target instead of turning it into a cwd-relative file path.
- Search Shift+Return now uses the native submit event's modifier flags rather
  than relying on a no-op pre-14 onKeyPress helper. Full-app interaction testing
  is still required. URL hover banner uses a one-corner rounded Shape on Monterey
  instead of removing its background when UnevenRoundedRectangle is unavailable.
- `python3 test/macos-compatibility/cache-check.py` passes debug and optimized
  native runs of the actual cache implementation, including expiry, reuse,
  concurrent fetch coalescing, eager payload release, and deinitialization.
- Xcode project membership verification and `git diff --check` pass. SwiftLint
  is not installed; lint remains a release gate.

## Runtime and test findings (2026-10-29)

- Launched an ad-hoc re-signed copy under a separate test bundle identifier in
  `/tmp/ghostty-monterey/runtime/Ghostty.app`. AppleScript reached the actual GUI
  and terminal, and input text plus Enter executed a shell command that wrote
  `isolated-pty-ok` to a test file. This is not visual/Metal correctness proof.
- Important isolation correction: `GHOSTTY_CONFIG_PATH` is debug-only. Early
  ReleaseLocal smoke runs ignored it and read default configuration. Subsequent
  runs use `--config-default-files=false --config-file=<test config>` with
  updates disabled and window-save-state never. No installed app was launched.
- First-tab AppleScript references can retain the pre-tab-group window ID and
  fail with -1728 after AppKit lazily creates the group. `tab-reference.py`
  reproduces this with an isolated initial window and a split (red before fix).
  Lookup now resolves earlier standalone-window IDs through live native windows.
  The same test passes after rebuilding, including closing the returned tab and
  split. This preserves AppleScript instead of removing the feature.
- `zig build test -Demit-macos-app=false -Dtest-filter=ctrlOrSuper --summary all`
  passed 104/104 steps and 78/78 tests (includes imported module tests).
  Log: `/tmp/ghostty-monterey/zig-input-test.log`.
- `macos/build.nu --configuration ReleaseLocal --action test` failed to compile
  UI tests despite skip-testing: Xcode 14 lacks waitForNonExistence/XCUIDevice,
  and UI tests use newer sleep APIs. Swift Testing unit-test compatibility also
  remains open. No official Swift test success is claimed. The failed test
  action left an unsigned GhosttyTests.xctest in the app; that generated bundle
  was moved to `/tmp/ghostty-monterey/failed-GhosttyTests.xctest` before rebuilding.
- ReleaseLocal compile commands included coverage instrumentation. The build
  wrapper now explicitly disables coverage mapping/link flags for build/archive
  only, preserving test settings. `app-build-tab-fix.log` records a successful
  universal build without Swift profiling flags. The final main executable has
  no __llvm_prf/__llvm_cov sections, and deep strict codesign verification passes.
- App metadata still reports CFBundleShortVersionString 0.1/build 1 and empty
  GhosttyBuild/GhosttyCommit. Core +version is correct but is insufficient to
  validate distributable metadata. Sparkle's official feeds remain a release
  risk; fork update behavior has not yet been resolved.
- Fixed the startup NSLayoutConstraint warning. LLDB stopped at
  `_NSLayoutConstraintNumberExceedsLimit` and identified TerminalView's hosting
  maxWidth constraint. Monterey turns greatestFiniteMagnitude into a finite
  Auto Layout limit rather than unbounded sizing. Changing that one frame to
  infinity preserves expansion while avoiding the out-of-range constraint.
- `layout-check.py` exercises the production frame expression in a pinned native
  hosting view, checking resize fill behavior. It fails before the fix, passes
  after it, and rejects the greatestFiniteMagnitude mutant on this host.
- `app-smoke.py` now provides repeatable isolated GUI/PTY/tab/split/quit checks.
  It copies and re-signs the bundle under a test-only identifier, uses CLI config
  isolation (including updates off), preserves logs, checks clean shutdown and
  rejects the layout warning/profiling output. The old app fails specifically
  on the warning; the rebuilt app passes. No visual-rendering claim is made.
  Use a stable test-only bundle ID: a fresh random ID triggers a new macOS
  Automation permission prompt and cannot be tested unattended.
- Native keyboard recheck passes 390 checks in each optimization mode with the
  active WeType Pinyin input source; it is still not interactive IME coverage.
  Value, security (115 checks each), and cache suites pass again in both modes.
- Replaced implicit actor-isolated initializer/method conversions in AppleScript
  with closures that retain lexical main-actor context. `app-build-actor.log`
  records a successful universal build with those actor warnings eliminated;
  the app-smoke harness and deep strict signature check pass again. Sparkle
  callback sendability and ImGui dSYM warnings remain to be evaluated.
- SwiftLint 0.52.4 download attempts stopped: the first timed out partway, the
  resume could not connect to github.com. The partial archive and logs remain
  outside the repo; no download is running. Lint is not yet passed.

## Bundle and input audit (2026-10-29)

- Added `bundle-check.py`: audits every non-symlink Mach-O file, both architecture
  slices, deployment load commands, bundled dependency resolution, absence of
  coverage sections/test artifacts, strict signatures, and debug entitlement.
  All seven binaries pass: main app, Dock plugin, Sparkle, Autoupdate, Updater,
  Downloader and Installer. This does not prove weak-symbol safety, runtime
  compatibility of every code path, or notarization. Negative probes reject
  a 13.0 bundle minimum, an embedded test bundle, and an x86-only Dock plugin.
- The audit caught an actual signing issue: Xcode 14 injected get-task-allow
  into the ad-hoc ReleaseLocal app despite its absence from the checked-in
  entitlement file. `macos/build.nu` disables base-entitlement injection for
  non-Debug build/archive actions, preserving debugger support for Debug/tests.
  `app-build-signing.log` records successful rebuild; bundle and app smoke tests
  pass with the debug entitlement absent. Do not strip the library-validation
  exception required to load ad-hoc bundled frameworks in ReleaseLocal.
- `bundle-check.py --release` correctly rejects current placeholder metadata.
  Its success would only cover metadata/static properties, not release readiness.
  Version stamping, fork updates, signing/distribution policy remain open gates.
- Expanded `app-smoke.py` to read actual PTY bytes with termios raw mode. The
  AppleScript synthesis -> core encoder -> PTY path delivers Ctrl+A/C/D/S/Q/Z
  as 01/03/04/13/11/1a and Unicode pasted text as exact UTF-8. This passed after
  signing changes. It does NOT exercise interpretKeyEvents/IME event dispatch.
- `bash test/macos-compatibility/transfer-check.sh` passes debug and optimized
  runs against the real production surface pasteboard method and UUID codec,
  native named NSPasteboard and asynchronous NSItemProvider. Tests valid and
  malformed payload transport without using the user's clipboard. Terminal/app
  shells are stand-ins; interactive drag destination behavior remains unverified.

## Build metadata and upstream assertions (2026-10-29)

- The Debug Swift application target builds with `macos/build.nu`, using the
  existing ReleaseFast core. This is not a Debug core build or a Swift test run.
  Log: `/tmp/ghostty-monterey/app-build-debug.log`.
- `macos/build.nu` now stamps version from build.zig.zon and build number from
  git commit count, matching upstream's numbering approach. GhosttyBuild and
  GhosttyCommit are expanded by Xcode before signing, not patched into a signed
  artifact. Local changes append `-dirty`; no uncommitted build is represented
  as a clean published revision. About avoids a broken dirty-commit hyperlink.
  The built Info.plist reads 1.4.0 / 18457 and the actual HEAD plus -dirty.
  `bundle-check.py --release` intentionally rejects this dirty source revision.
- Added a bounded adapter in `upstream-check.py` for four unchanged upstream
  test files: command-line open filtering, URL paths, split drop zones, and split
  trees (including parameterized resize/spatial cases). It compiles actual
  production sources and replaces only the selected Swift Testing attributes/
  boolean assertions in temporary files. All 93 invocations pass in each of
  -Onone/-O; a successfully compiled broken-filter mutant is rejected by the
  assertions. No unsupported macro is silently ignored. This is partial semantic
  coverage, NOT an official Swift Testing/Xcode suite pass or a concurrency test.
- Full Swift unit/UI test compatibility is still an open gate. No test targets
  were removed or hidden to obtain these results.
- The version-stamped universal app passed the seven-binary bundle audit and
  isolated PTY/split/tab smoke checks again (`app-build-about.log`).
- Targeted Zig `clipboard write limit` run passes 104/104 build steps and 78/78
  tests. Log: `/tmp/ghostty-monterey/zig-clipboard-test.log`.
- Resumed SwiftLint download completed; portable 0.52.4 runs on this host.
  Archive SHA256: 39ea5cd9ab338c120885b764029d40a538fd8a083f69e955795d9061d02f9505
  (locally recorded, not compared against a separately published checksum).
  Ran strict --fix on all 84 modified Swift files, then strict lint. Fixed drop
  closure formatting and made the extracted delegate protocol class-only.
  Verification reports zero violations, but this old SwiftLint warns about the
  newer check_for_updates config key and its correction parser skips two files
  containing compiler-gated nonisolated(unsafe) syntax. Treat this as partial
  lint evidence, not complete modern-toolchain lint coverage. Rebuild after
  these final lint changes passed (app-build-lint.log), followed by the bundle
  audit and isolated app smoke. Value, transfer and cache tests pass again in
  both optimization modes. No build/download/test processes remain active.

## Fork update isolation (2026-10-29)

- Removed hard-coded official appcast selection and the upstream Ed25519 key
  from the fork's default bundle metadata. The update code and Sparkle remain;
  no auto-update implementation was removed as an alleged macOS 12 limitation.
- A distributor can supply `--update-key`, `--update-stable-url`, and
  `--update-tip-url` to macos/build.nu. Values enter Info.plist before signing.
  Runtime policy requires a 32-byte base64 key and a valid HTTPS URL for the
  selected channel; rejects official domains/key and credential/fragment URLs;
  never falls back to another channel or user-default feed URL. A Sparkle
  mayPerformUpdateCheck delegate guard is defense in depth.
- Without that metadata, Sparkle does not start/resume background schedules.
  Manual checks report the distribution prerequisite through the existing update
  error driver (including its no-terminal-window fallback). Removed the blanket
  SUEnableAutomaticChecks=false from source metadata so properly configured fork
  builds retain upstream config/preferences behavior instead of disabling updates
  permanently. Tests still explicitly disable automatic checks in isolated copies.
- `update-check.py` validates 22 source/key cases against the production policy
  in debug and optimized runs. No network requests or signing keys are generated.
  This is not a full update-cycle test. `UPDATES.md` records distributor setup,
  signing, monotonically increasing versions, and remaining update-cycle gates.
- The default universal bundle built successfully and passed bundle/PTY/tab
  smoke checks after feed isolation. Smoke also dispatches manual check_for_updates
  and verifies it is handled, but does not inspect rendered error text or prove
  network silence. The final existing-driver error presentation change rebuilt
  successfully (app-build-update-driver.log); bundle and app smoke pass again.
  A compiled upstream-key acceptance mutant fails the policy assertions, and
  both changed updater Swift files pass strict lint with the local tool version.
- A trusted fork appcast, distributor-controlled signing key and end-to-end
  update installation validation are still absent. Safe unconfigured behavior
  is progress, not completion of the public-release update requirement.

## Packaging and undo lifetime (2026-10-29)

- Added `macos/package-monterey.py` to archive a previously built universal app
  without changing its signature. It audits before/after ZIP extraction and
  compares every data hash, permission mode and symlink target; rejects changed
  inputs, existing outputs, optimized Python, and invalid release metadata.
  Produces a manifest and SHA256SUMS. This is repeatable packaging, not a claim
  of bit-identical compilation/ZIP output or source-to-binary attestation.
- `package-check.py` passed archive/checksum/refusal checks and executed the GUI/
  PTY/tab/split smoke against an extracted artifact. Production-mode packaging
  rejected the current dirty revision before creating output. The retained
  trial ZIP in /tmp/ghostty-monterey/package-roundtrip is marked NOT-FOR-RELEASE.
  No app was installed and nothing was uploaded. `BUILDING.md` records commands,
  signing/toolchain constraints, verification scope and release caveats.
- New native `undo-check.sh` exposed a real Swift exclusivity abort in
  ExpiringUndoManager.removeAllActions: releasing expiringTargets calls each
  proxy's deinit, which used to call back into the same Set mutation via expire.
  The deinit now only invalidates its timer; explicit expiry still removes undo
  entries. This preserves native UndoManager semantics without recursive mutation.
  Tests run actual production code and cover execution, TTL, zero/negative TTL,
  disabled registration, selective removal, redo and weak target/manager lifetime
  in -Onone/-O. Before fix the -Onone harness aborted; the old-deinit mutant
  reproduces that abort, but does not abort under -O on this host. After fix both
  modes pass. The universal app rebuild succeeds (app-build-undo.log), followed
  by strict bundle audit and isolated GUI/PTY/tab/split smoke tests. The fix's
  modified Swift file passes strict lint. No release readiness is inferred from
  the standalone undo tests; window restoration/interactive reopen remain gates.

## Live reopen and titlebar matrix (2026-10-29)

- Extended the isolated GUI smoke with `reopen-check.py`: close/undo/redo of
  splits, tabs and windows must preserve the surface UUID, child PID and PTY.
  It also verifies a closed split's child is retained briefly but exits after
  the configured five-second undo window (bounded resource retention).
- This exposed a second actual undo defect in native/tabs titlebar styles:
  restoring a standalone window produced one window/two tabs, not two windows.
  Reproduced twice with native and once with tabs before the fix. Nib loading
  temporarily sets tabbingMode=preferred for session restoration; synchronous
  undo presentation was letting AppKit group the window automatically. Undo
  now temporarily disallows automatic tabbing during safe window presentation,
  then restores the saved explicit tab group/index as before. Native, tabs and
  transparent close/undo/redo checks pass after the change.
- Hidden titlebar intentionally opens a new window for a new-tab action (upstream
  behavior). The AppleScript new-tab return failed with -1708: its temporary
  ScriptWindow wrapper was weakly held and could die before objectSpecifier was
  serialized. ScriptTab now retains that lightweight wrapper; ScriptWindow does
  not retain tabs and its underlying controller stays weak, so no cycle/terminal
  ownership is introduced. Hidden-style tab references/reopen checks now pass.
- `quick-terminal-check.py` verifies showing/hiding/reopening preserves terminal,
  PID and PTY. Isolation sets autohide=false to avoid automation focus changes
  hiding the panel. The test looks up the quick surface independently of ordered
  regular windows; assuming frontWindow is the panel caused an initial false
  failure. Physical global-shortcut dispatch/autohide behavior remains untested.
- Universal rebuild after both fixes succeeds (app-build-hidden-tab.log), strict
  lint passes for the changed Swift files, and hidden-style full smoke passes.
  The final native/tabs/transparent matrix and bundle audit also pass. These
  are live object/process checks, not pixel/IME/fullscreen
  or across-launch session-restoration validation.

## Across-launch restoration probe (2026-10-29)

- Added `session-check.py`, using an isolated, re-signed app copy and the same
  dedicated automation test bundle ID as the GUI smoke (run sequentially).
  On native, transparent and tabs titlebar styles, two windows, alpha/beta tab
  grouping, the alpha split and all three title overrides survive an app restart.
  A third launch with window-save-state=never produces one window/one terminal.
- Initially red on all three styles: selecting alpha before quitting restored
  beta instead. Enabling saving before fixture creation did not change this.
  A minimal pure-AppKit application reproduces it without Ghostty/SwiftUI/core
  (/tmp/ghostty-monterey/native-session). LLDB also shows AppKit restoring and
  ordering the windows, not a later Ghostty makeKeyAndOrderFront call.
- Added a namespaced Boolean to the native window coder, not the split-tree
  Codable schema. After AppKit groups the windows, restore selectedWindow on the
  next main-queue turn using a weak window reference. Missing keys preserve old
  session decoding. When a tab becomes key, invalidate siblings' cached state
  so deselection is saved too. No polling or persistent observer is added.
- Universal ReleaseLocal rebuild passes (app-build-session.log); strict lint of
  both changed Swift files and the seven-Mach-O bundle audit pass. All three
  titlebar styles now preserve selected alpha and selected beta (six runs), tab
  order and the focused split UUID. Native-style full GUI/PTY/reopen/expiry/quick
  terminal smoke also passes with this build.
- The stronger harness was also **red on frontmost-window restoration** in all
  six cases: gamma is frontmost before quit but not after restart. Reproduced
  with a pre-fix app copy as well, so this is not evidence that the selection
  change introduced it. A WindowServer on-screen list confirms the tabbed window
  is in front. The harness completes its never-restore cleanup before reporting
  selection/window-order failures.
- Reproduce: `python3 test/macos-compatibility/session-check.py
  macos/build/ReleaseLocal/Ghostty.app --titlebar native`.
  Add `--selected-tab beta` to exercise selection changes after fixture creation.
  This does not verify shell-process survival, working-directory restoration or
  fullscreen state. Across-launch shell-process survival is not expected.

## Restored window order (2026-10-29)

- The pure-AppKit probe reproduces window-order loss as well: gamma/alpha/beta
  saves and beta/gamma/alpha restores. Changing the restoration tabbingMode from
  preferred to automatic does not fix it. This does not implicate the SwiftUI
  focus repair loop; no speculative changes to that loop were made.
- Save native window order alongside selected-tab metadata. A single queued
  batch applies selected tabs, then orders the visible non-native-fullscreen
  restored windows relative to each other. No app activation, key-window change,
  timers or strong window retention. Key-window changes invalidate terminal
  window state so both ordering and deselection can be re-encoded.
- Universal build succeeds (app-build-session-order.log), two-file strict lint
  and bundle audit pass. The six standalone-frontmost combinations now pass;
  three additional beta-selected/tabbed-frontmost cases pass. Transparent GUI/
  PTY/undo/expiry/quick-terminal smoke passes against the rebuilt app.
- `restoration-order-check.py` compiles the actual batch body and tests three
  logical windows, tab selection, a hidden window, unchanged key window, drained
  weak-reference queue and a second independent batch. Both -Onone/-O pass; a
  compiled no-ordering mutant fails the explicit order assertion in each mode.
  This does not prove native fullscreen/Spaces/minimized-window restoration or
  every interaction with other apps. Those remain separate runtime gates.

## Fullscreen transition probes (2026-10-29)

- Added opt-in `app-smoke.py --fullscreen false|true|visible-menu|padded-notch`
  and `fullscreen-check.py`. The latter checks actual WindowServer dimensions,
  two enter/exit cycles, frame restoration, stable surface/PID/PTY and execution
  of shell commands while fullscreen. Action acceptance alone is not a pass.
- Found a reproducible 28-point height increase on each non-native fullscreen
  exit with titlebar-tabs, including a fresh app without preceding undo/quick
  terminal operations. A minimal AppKit toolbar window reproduced the increase:
  restoring the frame before the toolbar produces height 708 instead of 680;
  restoring it after the toolbar produces 680. Moved the existing setFrame call
  after restoration of toolbar/accessories, retaining upstream saved-state logic.
- Universal rebuild (app-build-fullscreen.log), strict lint and bundle audit
  pass. Titlebar-tabs passes all three non-native modes; native, transparent and
  hidden titlebars pass non-native=true. Each run includes the full existing
  GUI/PTY/undo/expiry/quick-terminal smoke. The current Intel screen has no notch;
  padded-notch geometry on a notched display is not validated.
- Native fullscreen (`--fullscreen false`) remains **red/unverified**: the
  action is accepted but window geometry never changes. Activating the window
  first and removing preceding smoke operations did not fix it. A standalone
  pure-AppKit NSWindow with fullScreenPrimary also remains non-fullscreen after
  toggleFullScreen, both as a bare executable and a signed app bundle. This
  suggests an environment/AppKit prerequisite, not proof of a Ghostty defect or
  proof the feature works. No native fullscreen fallback/removal was made.
- Probes retained under /tmp/ghostty-monterey/native-fullscreen.swift and
  fullscreen-frame.swift. No system preferences, Dock process, installed app,
  or user restoration state were changed to force a result. Native fullscreen,
  Spaces, multi-display and grouped-tab fullscreen remain open runtime gates.

## Fullscreen follow-up (2026-10-29)

- `--fullscreen-tabs` now exercises a real two-tab group. On non-native entry
  the selected tab becomes a separate fullscreen window; on exit it rejoins
  with original tab order and selection. Both terminals retain their UUID,
  child PID and PTY. All nine combinations of native/transparent/tabs titlebar
  and true/visible-menu/padded-notch mode pass, each with two cycles and the
  existing full GUI smoke. This closes the tested non-native grouped-tab gate,
  not the native-fullscreen grouped-tab/Spaces gate.
- Added `fullscreen-frame-check.py`: runs the production style/toolbar/frame
  assignments in their actual order on an AppKit toolbar window. Three cycles
  pass in -Onone and -O; moving frame restoration back before toolbar restoration
  compiles but fails the geometry assertion in each build. Accessory views are
  deliberately not mocked into this focused test; full-app checks cover them.
- Identified an actual native-fullscreen prerequisite failure: the current
  `CGSessionCopyCurrentDictionary` reports CGSSessionScreenIsLocked=1 and
  NSWorkspace.frontmostApplication is com.apple.loginwindow. The pure-AppKit
  app is visible but never active/key, even when launched with `open`. LLDB
  confirms canEnterFullScreenMode=YES and entry into Apple's transition code.
  Private selectors were inspected only in LLDB, not added to production code.
  The native-fullscreen harness now rejects a locked session with an actionable
  message instead of waiting for a geometry timeout. Native fullscreen remains
  unverified until an unlocked-session rerun; no unlock was attempted.

## Search-field selection on Monterey (2026-10-29)

- Audited the upstream pre-26 BackportSelectionTextField: its selection binding
  is intentionally ignored. A real NSHostingView/SwiftUI TextField harness on
  Monterey confirms setting range 0..<5 leaves the editor caret at {10, 0}.
  This is an upstream fallback limitation, not a reason to drop the feature.
- Added a small AppKit field-editor selection bridge while keeping SwiftUI's
  TextField, delegate, styling, focus and submit/exit handling. No replacement
  NSTextField implementation, private class names, swizzling or polling. SwiftUI
  flattens native controls under its hosting view on Monterey, so the bridge
  matches the field within its own background bounds rather than assuming a
  fixed private view hierarchy. Observers exist only with the field's view;
  queued work holds the view weakly and coalesces updates.
- Initial bridge tests caught a real editing regression: a stale selection was
  reapplied after typing. Text-change notifications now preserve the native
  editor's new caret instead. Marked text is not interrupted. This code still
  needs unlocked full-app interaction and real IME validation; the bounded
  field-editor fixture is not a substitute for those tests.
- `search-selection-check.py` compiles the actual Backport.swift and checks
  programmatic/two-way selection, UTF-16 emoji/combining-mark ranges, focus
  re-entry, typing/deletion, coalesced replacements, unrelated-field isolation
  and marked-text preservation in -Onone/-O. A compiled no-bridge mutant fails
  the selection assertion in both modes. No state-during-view-update warnings.
- Universal rebuild succeeds (app-build-search-selection.log), Backport.swift
  passes strict lint, bundle audit and transparent full GUI/PTY smoke pass.
  No files were added to app build membership; full-app search navigation,
  pasteboard activation/focus behavior and pointer backports remain open.

## Search selection follow-up (2026-10-29)

- Extended the real SwiftUI/editor harness to cover submit and Escape handlers,
  switching the window's shared field editor between two independent bindings,
  inactive-field selection isolation, and releasing a dismissed hosting view
  and model while selection work is queued. Both -Onone/-O pass. A second
  compiled mutant disables preservation of the edited caret and is rejected by
  an explicit typing/caret assertion in both modes.
- A stronger same-runloop scenario is **red**: insert text through AppKit then
  immediately replace the model externally, before SwiftUI settles. The model
  becomes "external replacement" but the field/editor still shows "typed";
  SwiftUI reports "Binding<String> action tried to update multiple times per
  frame." Reproduced in -Onone/-O both with and without the selection bridge.
  This is not evidence of a bridge-introduced regression, but remains an open
  Monterey SwiftUI consistency risk. Reproduce with
  `python3 test/macos-compatibility/search-selection-check.py --same-turn-replacement`;
  it deliberately fails, reporting all four results. Settled edit followed by
  external replacement passes the regular suite. No direct editor-text overwrite
  was added speculatively; real search/pasteboard event sequencing needs checking.
- Rechecked session state: still locked, loginwindow frontmost. Physical input,
  activation-driven find-pasteboard updates and native fullscreen still require
  an unlocked-session test. No production code changed in this follow-up.

## Production search-state integration (2026-10-29)

- Added `search-state-check.py`: compiles the unchanged production SearchState,
  StartSearch C wrapper, pasteboard extension and Backport.swift, with only empty
  containing types to avoid unrelated renderer linkage. Runs all nine unchanged
  upstream SearchState tests through a bounded @Test/#expect adapter. This is
  additional coverage, not a claim the complete Swift Testing suite runs on
  Xcode 14. A compiled select-all regression fails an upstream assertion.
- The integration fixture uses the actual nested needle text/selection bindings
  and onChange pasteboard write path. It verifies typing -> model -> pasteboard,
  external pasteboard -> model -> selected editor text, unchanged-pasteboard
  caret preservation, new search text, and pasteboard changes while unfocused
  followed by refocus. All use unique pasteboards, never the user's find board.
  Both -Onone and -O pass, including emoji in the external needle.
- The same-turn failure also reproduces with the real SearchState/pasteboard
  flow, not just the earlier simplified model, in both optimization modes:
  `search-state-check.py --same-turn-replacement`. The editor displays "typed"
  while the actual model and pasteboard contain the external needle. The bounded
  fixture does not establish how often real activation/input events interleave
  this way in the app. This remains an open consistency issue.
- Tested deferring the pasteboard read by one main-queue turn in a temporary
  harness. That is not a valid fix: the pending onChange write overwrites the
  external pasteboard before it is read, leaving all three values at "typed".
  No delayed read or direct text override was added to production. Next work
  must preserve external-update ordering, not merely make editor/model equal.
- Pointer audit: the split divider already has an upstream Monterey onHover
  resize-cursor fallback. A blanket pointerStyle backport would double-handle
  that path; link-cursor call sites need separate assessment. No blanket
  replacement was made in this turn.

## Native MIME clipboard checks (2026-10-29)

- Added `pasteboard-mime-check.py`, compiling the complete production
  NSPasteboard extension and shell helper against GhosttyKit headers, without
  mocks for the clipboard or MIME mapping. All writes use a unique pasteboard.
  Both -Onone and -O pass on Monterey.
- Real lazy text, image and file-URL providers remain unread during MIME
  enumeration; explicit data requests fetch their bytes. A compiled mutant
  that eagerly reads text during enumeration fails the provider-counter
  assertion in both modes. This directly covers the metadata-only requirement
  of the helper used for mode 5522, not the entire wire protocol.
- Covered UTF-8 and embedded binary bytes, MIME normalization/deduplication,
  file URL precedence over Finder labels, multi-file shell escaping, percent-
  encoded CRLF URI lists, multi-item text ordering, unsupported MIME reads,
  non-file URL rejection/fallback, custom MIME round trips and clipboard routing.
- Two initial fixture assumptions were corrected from native evidence, without
  production changes: AppKit advertises synthesized TIFF/legacy representations
  for PNG, and unknown MIME types can map to dynamic UTTypes rather than raw
  MIME identifiers. The final tests follow the actual production write mapping
  and do not require an artificially restricted list of image representations.
- End-to-end OSC 5522 negotiation, permissions/confirmation UI, physical paste
  and cross-application lazy providers remain separate validation gates. This
  turn adds evidence for preserving the upstream clipboard implementation on
  Monterey, not grounds to claim full clipboard release readiness.

## OSC 5522 wire-path checks (2026-10-29)

- Added opt-in `app-smoke.py --clipboard-protocol` with a PTY child that sends
  real OSC 5522 packets through the running app and parses the terminal replies.
  This tests core parsing/dispatch, the macOS runtime boundary where reached,
  response encoding and PTY transport, not a simulated protocol endpoint.
- Eleven exact wire replies pass: standard reads/writes under deny policy
  return EPERM with the original ID and ST/BEL terminator; allow-policy requests
  for macOS's unsupported primary clipboard return ENOSYS; a 17-byte write with
  a 16-byte configured limit returns EFBIG; malformed base64 returns EINVAL;
  the next valid primary transaction returns ENOSYS (failure-state recovery).
  The reader also rejects extra/trailing bytes that would leak into the shell.
- No standard clipboard content is read or replaced: standard operations run
  under explicit deny, and all allow-stage requests name loc=primary. The
  harness reloads test-only configuration and restores it in finally. Captured
  packets remain in the isolated smoke directory for inspection.
- Transparent and native full GUI/PTY/reopen/expiry/quick-terminal smoke pass
  with the protocol probe. The stricter exact-response/trailing-byte version
  passed the native run. No production/core changes were required.
- Successful standard multipart writes/reads, unsolicited mode-5522 paste
  events, ask/remember confirmation UI and physical cross-app paste still need
  validation. These negative/error-path successes do not prove those paths.

## Search consistency recovery (2026-10-29)

- Fixed the demonstrated same-turn external-replacement divergence in the
  existing field bridge. After SwiftUI's update, reconcile the native field and
  editor only if they differ from the latest model, never during marked text.
  Do not re-read/rewrite the pasteboard, change the model text, or replace the
  SwiftUI field/delegate. Programmatic changes suppress selection notifications
  while applied so a transient caret cannot overwrite the requested selection.
- A 20-cycle stress test exposed a second ordering case: SwiftUI sometimes did
  apply external text, but the bridge treated it as the earlier local edit and
  replaced select-all with the native caret. Record the text of the native edit
  and preserve its caret only when that text still matches the current model.
  This is event-driven work on the existing coalesced queue, not polling.
- Both optimization modes now pass the simplified and actual SearchState/
  pasteboard same-turn probes, including 20 consecutive races, subsequent typing,
  deletion and consecutive native inserts. The unbridged control still fails;
  a compiled reconciliation-disabled mutant fails the exact divergence check.
  Regular selection, shared-editor, lifetime, marked-text and nine upstream
  SearchState tests remain green. Earlier known-red entries describe the
  pre-fix evidence, not the current test verdict.
- SwiftUI still emits its multiple-updates-per-frame diagnostics in the
  deliberately same-turn fixture; the workaround restores observable state,
  not SwiftUI internals. Real keyboard/IME/activation sequencing remains a gate.
- Final universal rebuild succeeds (app-build-search-reconcile-final.log),
  Backport.swift strict lint passes, and rebuilt-app GUI/PTY/OSC5522 smoke plus
  seven-Mach-O bundle audit pass. No new source membership or dependencies.

## Monterey link cursor fallback (2026-10-29)

- Confirmed `.backport.pointerStyle(.link)` registered no link cursor on
  Monterey using a real SwiftUI host and a test-only forwarding interceptor for
  AppKit's addCursorRect. Added a small native cursor-rectangle background for
  the actual link call sites (search controls, overlays and secure-input UI).
  The view passes clicks through, uses its visibleRect and has no observers,
  timers, global cursor push/pop or polling. AppKit handles cursor lifetime.
- The fallback deliberately leaves resize styles alone: the split divider's
  existing upstream onHover owns those cursors on Monterey. It does not claim
  to implement unused pointerVisibility or every newer pointer style.
- `pointer-check.py` verifies native registration, resizing, link/nil changes,
  view removal, click passthrough and no duplicate resize-cursor registration.
  Both -Onone/-O pass; the compiled no-pointer mutant fails. Method interception
  exists only in the disposable test process and forwards to AppKit, never in
  production. Physical hover/compositing precedence remains an unlocked-GUI gate.
- Universal build passes (app-build-pointer.log), Backport.swift strict lint,
  selection bridge regressions, tabs GUI/PTY/grouped non-native fullscreen smoke
  and bundle audit pass. No new dependencies or Xcode source memberships.

## Monterey automation without another implementation (2026-10-29)

- Added opt-in `app-smoke.py --automation`: real AppleScript configuration
  record copying and window/tab/split creation, with child-process assertions
  for working directory, environment and initial input. Paths contain spaces
  and quotes; values contain quotes, equals signs and backslashes, plus an
  explicit empty variable. A subsequent command proves each shell stays live.
  Closing created surfaces preserves the original terminal identity/counts.
- Transparent-titlebar automation and the complete existing GUI/PTY/undo/TTL/
  quick-terminal smoke pass on the current universal ReleaseLocal app. No
  product code changes, core changes, dependencies or rebuild were needed.
- `AUTOMATION.md` describes the existing dictionary as the low-maintenance
  Monterey route, with an example for Shortcuts' Run AppleScript. This does
  not restore native discoverable App Intents actions. AppleScript uses its
  own configuration switch and system Automation permissions, not the App
  Intents `macos-shortcuts` policy. Shortcuts UI/consent, login-shell behavior,
  Services invocation and arm64 runtime remain unverified by this probe.

## Native system-symbol audit (2026-10-29)

- Added `symbol-check.py` to complement the deployment/dependency bundle
  audit. It enumerates undefined symbols in all seven bundled Mach-O files
  and resolves system imports against actual Monterey libraries/shared cache,
  without loading the bundled app, plugins, Sparkle or helper executables.
  The JSON report retains missing weak imports and skipped bundled imports.
- Current x86_64 macOS 12.7.6 result: 3,383 required system imports resolve;
  61 weak imports resolve; 45 weak imports are absent, all in the main app.
  Three Sparkle imports are explicitly outside this system-only audit.
  Evidence: `/tmp/ghostty-monterey/system-symbols.json`. Native positive and
  absent-symbol controls exercise the resolver on each run.
- Corrected two test-tool assumptions rather than changing production:
  ctypes attribute lookup rejects double-underscore names such as NSArray's
  empty singleton, whereas indexed lookup resolves them; the assembler-named
  dyld_stub_binder needs a shared-cache export and libSystem re-export check,
  not C-name dlsym. These were fixture errors, not missing runtime symbols.
- Demangled absent weak imports group into Duration formatting, URL's newer
  path API, CoreTransferable, Swift Regex, and compiler-generated SwiftUI
  protocol defaults/descriptors. Explicit source operations in the first four
  groups retain macOS 13 availability guards and Monterey alternatives; do
  not remove upstream code simply to eliminate weak import entries. Compiler
  protocol defaults still require runtime path coverage, not just an inventory.
- This closes only a bounded host-symbol check: library-scoped dlsym searches
  dependencies and is not a complete dyld two-level namespace proof. It does
  not prove guarded weak calls, Objective-C selector availability, arm64,
  macOS 12.0 versus 12.7.6, or updater installation. No production changes or
  rebuild were needed, and these broader release gates remain open.

## Command palette preservation checks (2026-10-29)

- Added `palette-check.py`, compiling the complete production CommandPalette
  view and native color helpers, plus the exact terminal-option sorting
  function. Three upstream palette test bodies run unchanged apart from the
  bounded Swift Testing attribute/assertion adapter. They cover text ranking,
  stable ties and terminal sort keys; extra assertions cover initials,
  case-insensitive matching and native color-list ranking.
- A real NSHostingView/NSTextField editor verifies initial no-selection,
  typed-query selection, arrow and Control-N/P shortcut actions, wraparound,
  narrowing results with an out-of-range selection, empty/no-match queries,
  submission, Escape, clearing and reopen/reset. Both -Onone and -O pass.
  Compiled mutants disabling submission or downward selection each fail at
  the corresponding assertion in both modes. Evidence is retained in
  `/tmp/ghostty-monterey/palette-check.log`.
- Initial harness calls to the editor's moveDown selector did not exercise
  SwiftUI's keyboard-shortcut buttons. Direct hosting-view key equivalents
  with an extra function modifier were also unhandled; explicit declared
  arrow/control equivalents pass. No product fix was inferred from these
  fixture-level results. Physical arrow event normalization and full-app
  responder routing remain gates, not demonstrated regressions or successes.
- The fixture explicitly assigns first responder because the host session is
  locked. It does not prove automatic focus, IME, physical keys, mouse/hover,
  terminal palette data assembly, or core action dispatch. No product changes,
  new compatibility layers, dependencies or app rebuild were needed.

## Native Services provider checks (2026-10-30)

- Added `services-check.py`: complete unchanged production ServiceProvider
  and production URL helper, native unique pasteboards and temporary files.
  App/controller construction is recorded rather than creating terminals.
  Source service declarations and Objective-C runtime selectors are checked.
- Both optimization modes pass legacy Finder filename-list and modern NSURL
  representations, file-to-parent conversion, multiple-file deduplication,
  existing directories without trailing URI slashes, root preservation,
  window/tab routing with/without a preferred parent, and rejected empty,
  non-path and remote-URL input. A compiled resource-lookup-disabled mutant
  fails directory resolution in both modes. No user clipboard or Services
  registrations were modified. Log: `/tmp/ghostty-monterey/services-check.log`.
- A further native probe found that string-only absolute paths and file URIs
  are not converted to NSURL by Monterey's file-URL pasteboard reader. The
  unchanged provider rejects them even though the upstream Info.plist
  advertises plain text with FilePath context. The test records this behavior
  explicitly; it is not evidence that selected-text Services works. Actual
  Services mediation/representation conversion needs investigation before
  deciding whether a Monterey adaptation is necessary. Do not silently add
  shell parsing or broaden accepted input to make this probe green.
- Finder menu discovery, cross-process service invocation and real terminal
  construction via Services remain open. No production code or compatibility
  layers were added, and no app/core rebuild was needed.

## Cross-process Services discovery investigation (2026-10-30)

- Added opt-in experimental `app-smoke.py --services` and
  `services-app-check.py`. Only the copied app's service names change; the
  production service definitions and code remain untouched. The client uses
  NSPerformService and a unique filename pasteboard, with planned assertions
  for created terminal identity, actual PTY cwd and cleanup.
- Initial NSPerformService calls returned false. Inventory inspection narrows
  this to discovery: pbs selects an older temporary app with the same stable
  smoke bundle ID (`/private/tmp/ghostty-session-q22cy347/Ghostty.app`), not the
  current copy's unique service names. Explicit path registration and Services
  refresh did not change that selection. Reading the bundle directly confirms
  its entries parse, but does not establish discovery. This is not evidence
  of a provider or terminal-creation bug.
- A unique test bundle ID avoided that collision in principle but timed out
  on the first AppleScript query in the locked session, before any Services
  invocation; that variant was removed and its temporary registration removed.
  Do not bypass system consent or unregister unrelated historical/user apps.
- Current probe fails closed on inventory mismatch, saves the inventory and
  unregisters its own temporary copy in finally. Latest diagnostic artifacts:
  `/tmp/ghostty-monterey-smoke-fowzw4vy`; no smoke app is left running. It is
  explicitly documented as experimental/failing, not a new green release gate.
  True cross-process and selected-text Services validation remains open.

## Fullscreen session ordering correction (2026-10-30)

- Extended `session-check.py` with opt-in non-native fullscreen across a full
  quit/relaunch, using WindowServer bounds, persisted tab/split identities,
  front-window ordering, exit-frame comparison and a command through the
  restored PTY. Before the fix, repeated runs restored fullscreen geometry
  but put the previously frontmost fullscreen window behind the tabbed window.
  The original test remains red on its front-order assertion; merely finding
  fullscreen-sized geometry somewhere in the window list is not success.
- A native AppKit probe reproduced the relevant distinction: automatic or
  disallowed tabbing can leave a standalone window without any tab group,
  including after removing the titlebar. The added restoration encoder had
  marked such a window as unselected, excluding it from our order batch.
  Corrected that one expression: no tab group means a standalone selected
  window, while grouped windows still encode their actual selection. No new
  timers, observer, schema version, focus activation or controller architecture.
- The production-expression/batch fixture passes in both optimization modes;
  a compiled old nil-group expression and the no-order mutant are rejected.
  Universal ReleaseLocal rebuild succeeds (`app-build-nil-group.log`) and
  TerminalController strict lint reports zero violations (old-tool config
  warning remains). The rebuilt transparent/true across-launch test passes
  front order, fullscreen geometry, exit frame, live PTY, tabs/splits and
  window-save-state=never (`session-fullscreen-fixed.log`).
- Tabs/visible-menu and native-titlebar/padded-notch session combinations also
  pass, as does a non-fullscreen regression with beta selected and the tabbed
  window frontmost. The seven-Mach-O deployment/dependency/signature bundle
  audit passes on the rebuilt app (`bundle-nil-group.log`).
- Native fullscreen, minimized windows, multiple displays/Spaces and physical
  notch hardware remain unverified. The new check currently covers a separate
  fullscreen front window alongside a tabbed window, not arbitrary combinations
  of fullscreen tab groups. A later source-only explanatory comment does not
  change the tested binary's behavior.

## Asynchronous surface-drop lifecycle checks (2026-10-30)

- Added `drop-lifetime-check.py` for the compatibility callback in
  TerminalSplitTreeView. It extracts the actual provider-loading closure and
  compiles it with the production UUID codec and SurfaceView transfer/lookup
  extension, native NSItemProviders, and minimal app/surface registry shells.
  Test-only completion markers run after queued action work so error-path
  assertions do not merely assume a sleep was long enough.
- Both optimization modes pass delayed delivery, exact source/destination/zone,
  main-thread registry lookup and dispatch, malformed 0/15/17-byte payloads,
  provider errors, self-drop rejection, source removal before delivery,
  destination deallocation while pending, and 20 valid transfers following
  failed transfers. The pending native provider does not retain the destination.
- Compiled strong-destination, allowed-self-drop and background-lookup mutants
  each fail their specific assertions in both modes. The deliberately broken
  background mutant also emits Swift 5.7 actor warnings; production fixture
  compilation does not. Log: `/tmp/ghostty-monterey/drop-lifetime.log`.
- No product changes or rebuild were needed. This strengthens evidence for
  the small native transport replacement, not physical drag/drop equivalence:
  hit testing, drop overlays, actual split-tree move/rollback, cross-window drag
  and released core surfaces still require end-to-end validation.

## Current Debug build and fullscreen toolbar correction (2026-10-30)

- Rebuilt the previously stale universal Debug app through build.nu. Current
  Swift -Onone/runtime exclusivity checks now cover the undo, session, search
  and pointer adaptations; the linked core is still the earlier ReleaseFast
  build, not a claim of full-core Debug testing. Combined automation/OSC5522/
  tabs/undo/TTL/quick-terminal/grouped-fullscreen smoke and tabs/visible-menu
  session restoration passed before the additional toolbar fix below.
- That run exposed a fixture assumption: an initial restored window can
  already span display width. Fullscreen entry now requires screen-sized
  geometry and a changed frame component, not strictly increased width.
  Exact exit-frame restoration and two-cycle identity/PTY assertions remain.
- It also exposed an AppKit error in otherwise passing fullscreen transitions:
  `Can't have a toolbar in a window with <NSNextStepFrame ...>`. A standalone
  native toolbar window reproduced it exactly when removing the titled style;
  detaching the toolbar first eliminated it. SavedState already retains and
  restores the toolbar, so the production fix is one assignment before the
  style change, with no new state or fallback UI.
- Extended the production-entry/exit fixture: both optimization modes pass
  three exact frame-restore cycles without the error. The old exit-order
  mutant still fails geometry; an attached-toolbar mutant reproduces the
  AppKit error. App smoke now explicitly rejects that diagnostic. Fullscreen
  strict lint passes and universal ReleaseLocal/Debug rebuilds both succeed
  (`app-build-toolbar-release.log`, `app-build-toolbar-debug.log`). Known
  Sparkle sendability and ImGui dSYM build warnings remain separate issues.
- Rebuilt Debug combined smoke and ReleaseLocal grouped visible-menu smoke
  pass with the stricter no-toolbar-error assertion. ReleaseLocal tabs/
  visible-menu session restoration and seven-Mach-O bundle audit also pass
  (`toolbar-debug-smoke.log`, `toolbar-release-smoke.log`, `toolbar-session.log`,
  `toolbar-bundle.log`). This does not prove visual toolbar appearance or
  physical fullscreen interaction in the locked session.

## Upstream update-state coverage with embedded Sparkle (2026-10-30)

- Added `update-state-check.py`: complete production UpdateViewModel/UpdateState
  plus 43 upstream test invocations from UpdateStateTests, UpdateViewModelTests
  and ReleaseNotesTests. The bounded adapter changes only Swift Testing
  attributes/assertions/imports, retains async/throws and checks every test is
  invoked. Parameterized visibility and termination cases are all executed.
- Compiles against matching Sparkle 2.9.6 build headers and explicitly checks
  the runtime Bundle path belongs to the supplied app's embedded framework.
  A shipped app intentionally lacks development module headers; the first
  compile-only attempt exposed that fixture assumption, not a missing runtime.
- Both -Onone/-O pass all upstream cases and additional callback checks:
  cancel/dismiss routing, uncancellable states, install confirmation, retry
  termination, hiding and warning suppression. Compiled cancel-installs and
  confirm-retains-item mutants fail their specific assertions in each mode.
  The latter mutant's unused-variable warning is expected; production compiles
  without that warning. Evidence: `/tmp/ghostty-monterey/update-state.log`.
- No updater, network requests, preference writes or installation are used.
  Real SPUUserDriver callbacks, sendability import warnings, signature rejection,
  download/install/relaunch and distributor infrastructure remain separate
  gates. This does not justify enabling an unverified feed or dropping Sparkle.
  No production edits or rebuild were necessary.

## Preserve minimized groups during restoration selection (2026-10-30)

- A native AppKit probe found that changing NSWindowTabGroup.selectedWindow
  deminiaturizes the whole group on Monterey. Running the actual production
  restoration batch against two minimized native tabs reproduced the bug:
  `Minimized group unexpectedly shown`. This was introduced by the selected-
  tab restoration adaptation, not evidence for removing tab restoration.
- The batch now skips already-selected tabs and remembers isMiniaturized
  before changing selection, then re-minimizes that window if needed. No new
  saved schema, observer, polling or alternate window controller. A native
  probe confirms the group's minimized/visibility state is preserved by this
  ordering; actual animation behavior still requires an unlocked session.
- Extended `restoration-order-check.py` to cover minimized selection, repeated
  selection, key-window preservation and subsequent deminiaturization. Both
  -Onone/-O pass; a compiled no-reminimize mutant fails the specific assertion,
  alongside the existing order and nil-group mutants. Source:
  `macos/Sources/Features/Terminal/TerminalRestorable.swift`.
- Universal ReleaseLocal and Debug builds pass (`app-build-mini-release.log`,
  `app-build-mini-debug.log`); changed-source strict lint reports no violations.
  This bounded native fixture does not prove AppKit's persisted minimized-state
  decode ordering or a complete app quit/relaunch with minimized windows.
- Rebuilt ReleaseLocal tabs/visible-menu fullscreen session regression and
  Debug native-titlebar/beta-selected/tabbed-front session regression pass,
  as does the seven-Mach-O release bundle audit (`mini-session-fullscreen.log`,
  `mini-session-debug.log`, `mini-bundle.log`).

## Across-launch minimized-session evidence (2026-10-30)

- Added `session-check.py --minimized-tabs`, restricted to a Debug app that
  already carries get-task-allow. It refuses ReleaseLocal before copying or
  launching; no signing policy or product API was widened. LLDB attaches only
  to the isolated test PID, schedules native miniaturize/state inspection on
  the main NSOperationQueue, then detaches before that work runs. JSON state
  snapshots and debugger transcripts remain in the printed artifact directory.
- Transparent/alpha-selected, tabs/beta-selected and native/beta-selected
  configurations pass actual app quit/relaunch. Both tab windows remain
  minimized/invisible while the standalone window remains visible; scripting
  enumeration does not expand them. Deminiaturization keeps the saved selected
  tab and a real command reaches its restored PTY. Existing tab order, focused
  split, titles, frontmost window and window-save-state=never assertions pass.
  Logs: `session-minimized-app.log`, `session-minimized-tabs.log`,
  `session-minimized-native.log` under `/tmp/ghostty-monterey`.
- Initial debugger probes failed on Objective-C expression import/capture and
  a Swift-only controller property. The final probe uses public NSWindow title
  and AppKit APIs, not a new production selector. Those setup failures were
  not interpreted as app restoration defects. Release entitlement refusal was
  separately exercised (`session-minimized-refusal.log`).
- This adds persisted-decoding evidence missing from the previous standalone
  fixture; it does not prove physical Dock interaction, animation/focus while
  unlocked, a debugger-free Release run, or arm64. No production edits or new
  build were necessary this turn.

## Native Zig wrapper ABI and renderer regressions (2026-10-30)

- Ran targeted core tests on the Monterey host with Zig 0.17.0: kitty renderer
  tests pass (104/104 build steps, 86/86 aggregate tests), as do combined MSL
  translation, shader-selection layout, preedit range and renderCellMap filters
  (104/104 steps, 85/85 aggregate tests). These include dependency tests and
  overlap; they are not GPU presentation or performance-baseline evidence.
- Running pkg/macos's own complete native wrapper suite exposed a compile
  failure that the main app build did not instantiate: String.compare feeds
  CFStringCompare's c_long result into a c_int-backed ComparisonResult enum.
  The SDK declares CFComparisonResult as CFIndex; a native C probe confirms
  eight-byte result versus four-byte int, with -1/+1 comparison values. The
  enum also participates in the CFArray comparator callback ABI, so narrowing
  only the string return would not correct the shared type contract.
- Changed ComparisonResult's backing type to the translated
  c.CFComparisonResult, retaining cases/call sites and adding SDK-size/alignment/
  value assertions plus less/greater native string comparisons. Native package
  Debug and ReleaseFast runs both pass 53/53 tests, including array sorting and
  CoreText/CoreGraphics/Foundation wrappers. Zig formatting passes. Logs:
  `macos-package-tests.log` (original failure),
  `macos-package-tests-fixed.log`, `macos-package-tests-release.log`.
- This is a small SDK ABI correction, not a Monterey-only runtime branch or
  broader feature rewrite. Core universal ReleaseFast rebuild precedes the
  dependent app rebuild; their outcome is recorded after completion below.
- Universal core rebuild completes 333/333 steps (`core-build-cfabi.log`),
  followed by a successful ReleaseLocal app build (`app-build-cfabi.log`).
  Rebuilt-app automation/OSC5522/GUI/PTY/undo/TTL/quick-terminal smoke and the
  seven-Mach-O deployment/dependency/signature audit pass (`cfabi-smoke.log`,
  `cfabi-bundle.log`). Debug app has not been relinked to this newest core;
  earlier Debug session results remain scoped to the preceding core build.

## Native permission-sheet regression evidence (2026-10-30)

- `permission-check.py` compiles the complete production PermissionRequest,
  duration helper and defaults helper on Monterey in both optimization modes.
  Native fixture-owned NSAlert sheets exercise allow/deny/abort, checkbox
  labels, one-time decisions, remembered allow/deny, automatic timed/forever
  allow, expiry removal, remember-duration precedence and independent keys.
  Negative TTLs exercise expiry without sleeping or changing the system clock.
- Both modes pass; compiled denial-becomes-allow and never-expires mutants
  fail the intended assertions. Log: `/tmp/ghostty-monterey/permission-check.log`.
  Defaults use a unique DEBUG-only suite, removed in Python's finally block
  even when the fixture fails or times out. No production changes were needed;
  the permission implementation still differs only in its duration type.
- This is programmatic native-sheet and cache evidence, not physical button
  interaction, system permission consent, or clipboard/Shortcuts end-to-end
  evidence. No user clipboard or installed-app preferences were touched.

## Offscreen Metal execution evidence (2026-10-30)

- `metal-check.py` compiles the unchanged production shaders.metal using the
  same metal/metallib flags as MetallibStep (macOS minimum 12.0), then runs a
  native Swift Metal fixture on both local devices: Intel Iris Pro Graphics
  (shared storage) and AMD Radeon R9 M370X (managed storage). No screen capture,
  unlock, installed-app launch or system privacy permission is involved.
- Each device creates all five production shader pipeline pairs for both BGRA
  pixel formats. For each optimization mode, each GPU completes 24 offscreen
  IOSurface-backed renders and synchronized pixel readbacks: whole background,
  cell backgrounds and their composition, transparent/translucent/opaque colors,
  padding extension enabled/disabled, gamma/linear blending, and sRGB/P3 input.
  CPU Double color conversion/compositing references check every pixel/channel
  with a two-byte quantization tolerance. No-device and GPU command failures
  fail rather than silently skip.
- Both optimization modes pass. Compiled shader mutants that erase the
  background or disable padding extension fail pixel assertions. Log:
  `/tmp/ghostty-monterey/metal-check.log`. The existing shader logical-operator
  parentheses warning remains; no production shader change was necessary.
- Scope: native descriptors mirror the Zig pipeline/attribute boundary, while
  uniform offsets come from Metal reflection. This executes production shader
  code but does not execute the Zig renderer's resource binding, text/image
  draws, custom shaders, compositor presentation, sleep/wake or display changes.
  It is not a performance comparison, glyph correctness, arm64, or full-app
  visual acceptance result. Those release gates remain open.

## Metal texture storage validation (2026-10-30)

- Extended the offscreen fixture with synthetic grayscale/color glyph atlas
  draws and image sampling, then enabled `MTL_DEBUG_LAYER=1`. This invalidated
  the previous storage-safety assumption: Intel Iris Pro reports unified memory
  but shared textures fail native validation. The prior successful readbacks
  without validation did not establish that the resource configuration was legal.
- Reproduced in the existing ReleaseLocal app, not just the fixture:
  `MTL_DEBUG_LAYER=1 ... app-smoke.py` exits at startup with
  `MTLStorageModeShared not allowed for textures`.
  Log: `/tmp/ghostty-monterey/metal-validation-app-before.log`, with native
  diagnostic in its printed artifact directory. A separate 12-case native
  probe (`metal-storage.log`) confirms shared buffers are allowed on both local
  GPUs, shared ordinary/IOSurface textures fail, and managed textures pass.
- Device now caches a separate texture storage mode, using shared for Apple
  GPU family hardware and managed otherwise. All four texture construction
  routes (target, custom-shader texture, image, font atlas) use it. Existing
  buffer storage/coherency policy is unchanged; there is no per-frame query,
  blanket managed-buffer conversion or GPU-feature removal.
- With the corrected texture policy and validation enabled, both local GPUs
  pass 48 draws/readbacks in both optimization modes. Four compiled shader
  mutants fail pixel assertions: zero background, disabled padding extension,
  ignored glyph alpha mask and omitted image premultiplication. Log:
  `/tmp/ghostty-monterey/metal-texture-check.log`. The native fixture still
  mirrors the Zig boundary; synthetic atlas sampling does not test real font
  shaping/rasterization, contrast correction, cursor coloring or presentation.
- Universal core rebuild passes 333/333 steps, followed by a successful
  ReleaseLocal app rebuild (`core-build-metal-storage.log`,
  `app-build-metal-storage.log`). The previously failing full-app smoke now
  passes with Metal API Validation enabled, including live PTYs, undo/redo,
  quick terminal, AppleScript automation and OSC5522 negative wire checks.
  `metal-validation-app-after.log` records the isolated artifact directory;
  its launch log confirms validation was enabled and has no assertion/error.
  The seven-Mach-O bundle/deployment/signature audit passes too
  (`metal-storage-bundle.log`). Debug has not been relinked with this fix.

## Full-app renderer configuration and Kitty traffic (2026-10-30)

- Added `app-smoke.py --renderer-stress`, using the existing isolated app
  copy. It enables Metal API Validation and core stderr logging, supplies a
  generated RGBA PNG background and two chained identity GLSL shaders, and
  reloads native/linear/linear-corrected blending configurations while the app
  stays alive. Both shader-source load messages must be present. Renderer,
  Metal and shadertoy warnings/errors fail, except the explicit upstream
  display-link fallback described below; validation assertions fail as well.
- `renderer-app-check.py` runs a real raw-mode PTY child in each configuration.
  It sends raw RGBA and PNG Kitty transmit-and-display commands, replaces an
  existing image, verifies three exact OK replies per configuration and deletes
  the fixture images. Unicode/combining/emoji output also enters the real PTY.
  The ordinary split/tab/window undo, quick-terminal and subsequent PTY checks
  remain enabled. Final run passes: `/tmp/ghostty-monterey/renderer-app-check.log`.
- This closes a configuration/protocol/liveness gap left by the standalone
  Metal fixture, but does not assert that the compositor presents those images
  or that every render command executes while the screen is locked. Kitty OK
  acknowledges terminal protocol handling, not completed GPU presentation;
  shader-source load is not proof of a visible postprocessing effect.
- Core logs reveal `error creating display link; using fallback rendering
  err=error.CreationFailed` on this session. The test explicitly permits that
  upstream fallback rather than claiming display-link timing is validated.
  Unlocked display-link behavior, visual correctness, rendering performance
  and sleep/wake remain release gates. No production edit or rebuild was
  necessary for this additional check.

## AMD background-image color regression (2026-10-30)

- A native CoreVideo/CG probe reports zero active displays, return -6661 from
  CVDisplayLinkCreateWithActiveCGDisplays, and a locked session. Thus the
  display-link creation failure reproduces outside Ghostty; it is not evidence
  that its callback wrapper needs changing. Log: `display-link-probe.log`.
- Expanded offscreen Metal checks to actually draw the background-image
  pipeline, centered at original size with repetition on/off and half opacity,
  for both input color spaces and blending modes. This exposed a repeatable
  AMD Radeon R9 M370X pixel failure: background RGB is zero while alpha is
  correct. Intel passes the same inputs. Two original runs and a pixel dump
  reproduce the failure (`metal-background-check.log`,
  `metal-background-repeat.log`, `background-dump.log`).
- Isolated to the vertex-stage construction of an opaque uchar4 from a
  uchar3 uniform plus constant alpha. Managed uniforms, varying renaming/order,
  removing flat interpolation, noinline and disabling fast math do not fix it.
  Moving color conversion to the fragment stage passes, but would add per-pixel
  work. Constructing via float3/float4 and converting back to uchar4 also passes,
  preserving exact byte values and the existing vertex-stage work. The product
  patch uses that one-expression workaround with a comment; no rendering
  feature, optimization level or GPU is disabled. Some alternative expressions
  trigger driver compiler internal errors, not a production runtime result.
- Both GPUs now pass 56 IOSurface draws/readbacks per optimization mode with
  Metal validation enabled. Five deliberately broken shader variants fail;
  reverting just the byte-vector workaround also fails on this AMD host in
  both modes (`metal-background-fixed.log`). That last hardware-specific check
  may report non-reproduction on other GPUs rather than invent a failure.
- Background-image scaling/position combinations beyond this bounded fixture,
  real compositor output and performance still require validation. Additional
  optimized native runs with background alpha 0 and 255 also pass on both GPUs
  (`metal-bg-alpha-0.log`, `metal-bg-alpha-255.log`).
- Universal core rebuild passes 333/333 steps and the dependent ReleaseLocal
  app rebuild succeeds (`core-build-amd-background.log`,
  `app-build-amd-background.log`). Rebuilt full-app renderer-stress/PTY smoke
  and the seven-Mach-O bundle audit pass (`amd-background-app-smoke.log`,
  `amd-background-bundle.log`). The app uses its normal preferred GPU; the
  dedicated offscreen fixture, not that app smoke, proves the AMD pixel fix.
  Debug is not current. Existing shader-parentheses/libtool member-name build
  warnings remain; they did not make the build fail.

## Current Debug relink and native icon coverage (2026-10-30)

- Rebuilt the Debug app against the current universal ReleaseFast core,
  including the CF ABI, texture-storage and AMD shader fixes
  (`app-build-current-debug.log`). This is a Debug Swift app with the optimized
  core, not a claim that the core was rebuilt in Debug mode. Earlier notes
  saying Debug was stale describe the state before this relink.
- Current Debug passes `session-check.py --titlebar tabs --selected-tab beta
  --minimized-tabs` under Metal API Validation: minimized state survives
  restart/enumeration, deminiaturization retains selected tab/live PTY, split
  focus/order/front-window and never-restore assertions pass. All three launch
  logs confirm validation is enabled with no validation assertion/error.
  Evidence: `current-debug-minimized.log` and its isolated artifact directory.
- Added `icon-check.py`: compiles the complete production AppIcon image branch,
  ColorizedGhosttyIcon, NSImage/OSColor helpers and config types with
  DOCK_TILE_PLUGIN, against the built app and actual Dock plugin asset catalogs.
  A bounded adapter runs all ten upstream ColorizedGhosttyIcon test bodies;
  this supplements rather than replaces the unavailable Swift Testing suite.
- Both optimization modes pass decoding/rasterization of eight distinct
  built-in icons, all four frames with two color schemes (eight distinct
  custom styles), app/plugin pixel parity, custom image data and persistence.
  An ignore-frame compiled mutant fails the raster-variation assertion in both
  modes. Log: `icon-check.log`. No production change was needed.
- This does not call AppIconUpdater, set a Finder/Dock icon, load a plugin into
  Dock, post distributed notifications or touch user defaults. Asset/composition
  evidence is not proof of the actual Dock update lifecycle or visual acceptance.

## Glyph contrast/cursor/correction GPU evidence (2026-10-30)

- Extended the existing native Metal fixture to cover the production text
  shader's cursor recoloring, wide-cursor second cell, cursor-glyph exemption,
  minimum-contrast adjustment and exemption, and linear blending weight
  correction. Synthetic atlas masks include zero, partial and full coverage.
  CPU Double references check each pixel's RGB/alpha, including untouched
  surroundings, under both color spaces and both render-target formats.
- Intel and AMD each pass 104 draws/readbacks per optimization mode with Metal
  API Validation enabled. The three new compiled mutants (disable wide cursor,
  minimum contrast, or linear correction) each fail pixel assertions. Existing
  five feature mutants and the hardware-specific AMD regression also fail as
  expected. Log: `/tmp/ghostty-monterey/metal-glyph-features.log`.
- No product code change or rebuild was needed. This confirms those upstream
  shader features remain operational in the tested GPU paths rather than
  simply compiling, but synthetic masks do not prove real font rasterization,
  terminal-to-vertex data, interactive selection/IME or compositor presentation.
  Performance and Apple Silicon runtime gates remain open.

## Native CoreText shaping and atlas rasterization (2026-10-30)

- Ran the actual Zig CoreText shaper/face and Atlas test groups on Monterey.
  Existing coverage includes ligatures, combining characters, multiple complex
  scripts, emoji variation selectors/width, selection/cursor boundaries, native
  and embedded font rasterization, variable fonts and atlas growth/error paths.
  Initial run passes 123 aggregate tests (`coretext-font-tests.log`). These
  counts include dependency tests, not 123 distinct CoreText-specific cases.
- Added `rasterized atlas coverage` to the existing CoreText face tests, rather
  than a second rasterizer implementation: render Menlo A and Apple Color Emoji
  rocket through production Face.renderGlyph into the actual grayscale/BGRA
  atlases. Assert nonempty dimensions, in-atlas bounds, nonzero/partial coverage,
  chromatic emoji pixels and premultiplied BGRA channels; also check rejected
  mismatched atlas formats and the zero-size whitespace glyph.
- Targeted new-test run passes (78 aggregate tests, `coretext-raster-tests.log`)
  and the complete filtered group then passes 124/124 tests, 104/104 steps
  (`coretext-font-release-tests.log`). Despite that log's filename and the
  invocation's ReleaseFast option, build.zig explicitly fixes ghostty-test's
  root module to Debug; the build output confirms Debug. This is NOT optimized
  core test evidence. Zig formatting and changed-file whitespace checks pass.
- Only a test block changed; no runtime implementation or app build changed.
  This adds real native rasterization evidence beyond synthetic GPU masks, but
  does not connect those pixels through the complete app/compositor or compare
  performance and visual output with upstream 1.4. Apple Silicon remains untested.

## Full-app Inspector lifecycle evidence (2026-10-30)

- Added `app-smoke.py --inspector`, which enables Metal API Validation and core
  stderr logging on the existing isolated app copy. A real shell's `stty size`
  observes Inspector show/hide/toggle through the actual SwiftUI split layout:
  three cycles change 46x179 to 22x179 and back, repeated show is idempotent,
  and surface ID/process/PTY remain unchanged. This is stronger than merely
  checking that the action returns true.
- Closing a second window while its Inspector is visible, then undoing from
  the original window, preserves the live process/PTY and Inspector layout;
  hiding it restores the original dimensions. Ordinary undo/redo, quick-terminal
  and PTY smoke checks subsequently pass. Final log: `inspector-app-check.log`.
  Validation-enable/core-log markers are required, and validation assertions or
  logged Inspector render errors fail. No runtime source change was needed.
- This does not force an occluded MTKView to draw, assert ImGui pixels, measure
  resource use, or test physical mouse/keyboard routing. The locked-session
  display-link constraint remains. Real Inspector interaction/presentation and
  lifecycle resource measurements still require acceptance testing.

## Extended archive validation exposes a lifetime failure (2026-10-30)

- Expanded `package-check.py` to run automation, OSC5522, renderer-stress and
  Inspector checks together from a ZIP extraction, and to reject dirty metadata
  in release mode and an intentionally modified sealed asset in a disposable
  extraction. Static round-trip/hash/mode/link checks pass. Dirty release
  refusal and tampered-resource refusal both pass without creating output;
  no original app, installed app or archive is modified by the tamper test.
- The combined extracted-app smoke is currently RED: on three runs a closed
  split's shell survives the ten-second observation window despite the configured
  five-second undo timeout. The latest probes capture a live `S+` /bin/sh,
  not merely a zombie. Earlier automation/graphics/Inspector assertions pass.
  Logs: `package-extended-check.log`, `package-extended-repeat.log`,
  `package-extended-third.log`; their printed smoke directories retain launch
  logs/configuration and the newer `undo-expiry-process.txt` snapshots.
- Controls: direct built-app renderer+Inspector passes; adding clipboard checks
  also passes; a direct built-app run with all four options passes too
  (`combined-lifetime-check.log`, `lifetime-no-automation.log`,
  `lifetime-direct-all.log`). This narrows the next investigation to the
  extracted/packaging-run context and timing/lifetime interactions; it does not
  establish an archive corruption or UndoManager root cause. The inventory
  comparison passes, so do not assume changed binary bytes.
- Do not widen the timeout or drop combined coverage to manufacture a pass.
  The packaging test now still runs its independent tampered-signature check
  after a smoke failure, then propagates that failure. The first standalone
  tamper probe expected different codesign wording; corrected to Monterey's
  actual `a sealed resource is missing or invalid` diagnostic and verified.
  No product fix has been made for the lifetime failure; it is an open release
  blocker, not a claimed successful archive-runtime validation.

## Lifetime failure narrowed to teardown (2026-10-30)

- The built app also fails when the combined smoke is invoked through a Python
  parent, without ZIP packaging (`lifetime-nested-built.log`,
  `lifetime-nested-diagnostic.log`). Archive extraction is not necessary.
  Another combined run passes (`lifetime-process-observation.log`), while the
  following run fails (`lifetime-login-observation.log`): this is timing-sensitive,
  not yet a deterministic nested-process versus direct-launch distinction.
- Failure samples in smoke directories `qykf61ce` and `w250io69` show the main
  thread inside the expiration timer, removing undo actions, releasing surface
  trees and calling ghostty_surface_free, then waiting in pthread_join. IO
  threads are sampled in nanosleep. The timer has fired; an idle run loop or
  retained surface that never starts destruction is not the sampled failure.
  The optimized Zig frames lack useful source symbols, so the precise wait
  site still needs confirmation rather than being inferred from these stacks.
- A process-tree observation (`lifetime-login-tree.txt`) captures a zombie
  login process while other closed terminals' login/shell pairs remain alive.
  The shell and its login parent have separate process groups. This warrants
  investigating subprocess shutdown and serial teardown before changing
  UndoManager or renderer ownership. The failed split's shell is still live,
  not a zombie; a later diagnostic Apple event succeeds after the sampled wait.
- Smaller controls pass: nested automation-only, eight/sixteen simple split
  closes, and renderer-config plus close/undo/redo followed by one split close.
  These do not yet reproduce the combined scenario. Temporary probes and logs
  remain under `/tmp/ghostty-monterey`; no product code changed.
- Setting NSAppSleepDisabled only in a disposable test copy does not fix the
  combined failure (`lifetime-no-nap-all.log`). Do not adopt a global App Nap
  opt-out, which would add resource cost without resolving this test.
- The original ten-second assertion and full combined coverage remain intact.
  Python syntax checks and tracked diff whitespace checks pass. The extended
  archive runtime gate remains red; neither a root-cause fix nor release
  readiness is claimed.

## Shutdown timing probes (2026-10-30)

- Temporary, subsequently removed `killPid` instrumentation localizes the long
  wait: killpg and nonblocking waitpid take microseconds, but a requested 10 ms
  sleep takes 10,062 ms in a failing combined run
  (`lifetime-instrumented2-all.log`). There are only two wait-loop iterations,
  not thousands of unsuccessful signals. A passing combined run still contains
  a 7.5-second sleep, so pass/fail alone misses the teardown stall.
- A disposable DYLD interposer confirms the libc nanosleep input is exactly
  0 seconds / 10,000,000 nanoseconds, with a measured 8.3-second elapsed time
  and default QoS 21 (`lifetime-libc-probe.log`). This is not a Zig duration
  conversion error. The interposer is loaded only by isolated smoke app copies.
- Mach absolute waiting and raising the sleeping thread's QoS do not resolve
  the combined assertion. A temporary activity held only during each sleep
  removes the sampled long sleeps, but the failure sample then shows an idle
  main run loop. A NOTE_EXIT kqueue probe similarly reduces shutdown waits to
  roughly 1-2 ms without making the combined expiry assertion pass. Neither
  probe is a production fix; both change only disposable diagnostic runs.
- Holding a process activity (user-initiated plus latency-critical) for the
  entire isolated run passes three consecutive combined runs, with all measured
  shutdown loops at 10-12 ms (`lifetime-whole-activity*.log`). This strongly
  points to background timer/scheduling policy affecting both expiration and
  shutdown in the locked, fully occluded session. It does not establish that a
  permanent process activity is appropriate for Ghostty: that would undermine
  the resource-efficiency goal and is NOT added to the product or test defaults.
- A smaller no-renderer probe after 35 seconds idle exits its single closed
  shell after 9.886 seconds instead of the usual approximately 5 seconds. A
  subsequent four-close probe fails earlier on an AppleScript missing-value
  reference, so it is not valid evidence of the expiry failure. Minimization
  still needs a reliable fixture and unlocked-session comparison remains open.
- All `[DEBUG-ttl]` source instrumentation was removed; Exec.zig again has no
  diff. Universal core and ReleaseLocal app rebuild successfully without it
  (`lifetime-clean-core.log`, `lifetime-clean-app.log`). Production runtime
  behavior remains unchanged by this investigation. The clean rebuilt app also
  passes the whole-run activity diagnostic (`lifetime-clean-activity.log`), so
  that result does not depend on the temporary logging instrumentation.
  The unmodified combined
  packaging gate is not yet green and no release-readiness claim is made.

## Independent native scheduling control (2026-10-30)

- Added `scheduling-check.py` / `scheduling-probe.m`: a temporary, separately
  identified AppKit app with one ordinary window, 35 seconds idle, a five-second
  timer, and a pthread doing a ten-millisecond libc nanosleep. It imports no
  Ghostty source, Zig runtime, Metal renderer, or undo implementation. The
  runner executes ordinary/activity/ordinary controls and reports measurements
  without relabeling slow results as a product pass. No global power setting,
  installed app, permission, or existing preference is changed.
- The checked-in fixture reports 8,853.289 ms / 15.049 ms / 9,824.541 ms for the
  three worker sleeps. All return success with errno zero, and their preceding
  five-second timers fire in approximately five seconds. Log:
  `/tmp/ghostty-monterey/scheduling-repo-check.log`. A preliminary native control
  without an ordinary window did NOT reproduce (10-14 ms); adding the ordinary
  window did. The window and background-session context matter to this probe.
- This independently reproduces the multi-second worker sleep without any
  Ghostty port code. It supports investigating native background scheduling
  before modifying subprocess teardown. It does not independently reproduce
  every delayed expiration in the full app, prove upstream-app equivalence,
  establish unlocked-session behavior, or close the original packaging gate.
- This is diagnosis evidence, not a permanent activity assertion in Ghostty,
  not a widened timeout, and not an automatically waived release gate. The
  clean ReleaseLocal app remains unchanged. Python syntax and tracked diff
  whitespace checks pass; native compilation and all three controls complete.

## System shell integration and current session (2026-10-30)

- Added opt-in `app-smoke.py --shell-integration` and `shell-app-check.py`.
  This starts the actual ReleaseLocal app with system zsh 5.8.1 and automatic
  integration, using a temporary ZDOTDIR and disabling subsequent global rc
  loading in its .zshenv. Personal startup/history files are not used. The
  initial fixture passed: production precmd/preexec hooks are installed,
  ZDOTDIR is restored, TERM/TERM_PROGRAM are correct, changing to a directory
  containing spaces and a quote reaches the Swift surface via OSC 7, and a
  new split's actual shell inherits that directory. Ordinary PTY/control/UTF-8,
  undo/redo, expiry and quick-terminal checks then passed too
  (`shell-app-check.log`). No runtime source change was needed.
- A disposable script changing only integration detection to `none` fails on
  the expected missing hooks (`0 0` instead of `1 1`,
  `shell-disabled-control.log`). This confirms the fixture does not merely
  check that any interactive shell works. Targeted Zig shell-integration tests
  pass 98 aggregate tests / 104 steps (`shell-core-tests.log`, Debug test root).
- The fixture now also checks actual tab/window child cwd, but these new
  assertions are NOT yet verified: two later smoke attempts time out on the
  very first AppleScript window-count query, before the fixture runs
  (`shell-app-inheritance.log`, `shell-app-inheritance-repeat.log`). A sample
  shows the app main thread idle in its event loop, not a teardown wait.
  Do not infer a cwd regression from those startup/automation timeouts or
  silently waive the expanded test. Automation delivery/consent needs checking.
- Revalidation at 09:38 shows one active display and successful CVDisplayLink
  creation (`display-current.log`); the session dictionary no longer reports
  the locked key and Chrome is frontmost (`session-current.log`). Do not keep
  assuming the earlier zero-display locked state. No agent unlocked the session
  or changed permissions. Native scheduling control in this state still shows
  3,038.211 / 10.592 / 1,975.667 ms worker sleeps for ordinary/activity/ordinary
  runs (`scheduling-active-display.log`). Thus lock alone is not a sufficient
  explanation; background/occlusion remains relevant. The fixture does not
  activate its window, so this is not a foreground-active control.
- Current signed ReleaseLocal bundle passes all seven Mach-O/deployment,
  dependency/coverage and strict-signature checks (`current-bundle-recheck.log`).
  Python syntax and tracked diff whitespace checks pass. Original packaging,
  physical interaction, arm64 and release gates remain open.

## Real config ABI regression and fix (2026-10-30)

- Added `config-check.py`, compiling the full production Swift Config, Input and
  supporting implementations against the current universal GhosttyKit static
  archive. A bounded adapter runs all 38 upstream ConfigTests methods (43
  invocations including argument tables) without editing their assertions.
  TemporaryConfig's two URL.path() calls are adapted only in the temporary
  fixture for Monterey. FullscreenMode cases are extracted; no fullscreen
  behavior is claimed. Explicit temporary files avoid personal config loading.
- New boundary assertions exposed an actual C ABI bug: abnormalCommandExitRuntime
  passed `UInt32?` storage to ghostty_config_get, which writes a plain u32.
  Swift's Optional tag stayed nil, so the getter returned its 250 ms fallback
  instead of the configured value. The original native test failed on
  UInt32.max (`config-check.log`); this is independent of AppleScript/scheduling.
- Fixed only that getter's local storage to nonoptional UInt32 and removed the
  spurious nil check. No C/core change, additional allocation, polling or feature
  removal. Tests now cover zero, 250, 2500, UInt32.max and missing-config fallback.
  Other checks cover the C duration getter's millisecond truncation, notification
  threshold units, independent clone ownership and zero-timeout reload.
- Both -Onone and -O pass all 43 upstream invocations and new boundary assertions.
  Compiled mutants restoring Optional integer storage or changing undo units to
  nanoseconds fail at the exact expected assertions in both modes
  (`config-check-regression.log`). The linked core is ReleaseFast in both runs;
  this does not claim Debug-core coverage or the full Swift Testing suite.
- ReleaseLocal rebuild succeeds with the fix (`config-abi-app-build.log`), and
  strict signature/all-seven-Mach-O audit passes (`config-abi-bundle.log`). Python
  syntax and tracked whitespace checks pass. GUI/packaging gates remain open.
- Latest automation diagnostic still times out on the initial window-count
  event (`shell-automation-diagnostic.log`). System logs show an indirect TCC
  request from the test app identifying iTerm as responsible sender, with no
  completion shown in the captured interval (`automation-tcc-detail.log`).
  This is evidence to investigate consent/delivery, not proof of denial or an
  application deadlock. No TCC database, permissions, or system services changed.

## Config consumer and geometry ABI checks (2026-10-30)

- Extended the existing native configuration fixture through the real
  ChildExitedMessage consumer. A 2500 ms configured threshold classifies
  successful exits at 2499/2500 ms as errors, at 2501 ms as success, and a
  nonzero exit code at 2501 ms as error; explanatory text agrees. UInt64.max
  elapsed time does not overflow the duration comparison. This connects the
  preceding getter fix to its actual behavior rather than only testing a value.
- Added real core-to-Swift signed coordinate limits (Int16.min/max), quick
  terminal enum/bool/floating-point settings, tagged percentage/pixel sizes and
  their top/right axis mapping, plus resize-overlay millisecond units. All pass
  with both -Onone/-O Swift wrappers linked to the ReleaseFast core; no additional
  product changes were necessary (`config-consumer-check.log`). These are config
  and calculation assertions, not visible-window geometry acceptance.
- Negative-control process exits do not run Swift deinit, so the fixture now
  sets TMPDIR to its own Python-owned subdirectory. TemporaryConfig files from
  both successful and intentionally failing runs are removed with that fixture.
  The complete suite and both mutants pass again after this cleanup isolation
  (`config-consumer-cleanup-check.log`). Original upstream test files remain
  untouched. Full app automation and release gates remain outstanding.

## Automation resumes; extended archive smoke passes (2026-10-30)

- A no-prompt AEDeterminePermissionToAutomateTarget probe against the running
  isolated app returns noErr (`automation-preflight-check.log`), and a subsequent
  osascript window-count query returns 1 (`automation-sender-check.log`). No
  permission database, system service, entitlement or app policy was changed.
  This does not retroactively establish the cause of the earlier timeouts.
- The full expanded system-zsh fixture now passes actual split/tab/window cwd
  inheritance plus ordinary smoke/lifecycle checks
  (`shell-inheritance-current.log`). This supersedes the earlier missing
  execution evidence for tab/window assertions, not the historical diagnostics.
- The unchanged `package-check.py` passes twice consecutively against the
  current ReleaseLocal app (`package-current-check.log`,
  `package-current-repeat.log`). Both runs cover ZIP/hash/mode/link round trip,
  dirty-release refusal, non-overwrite and optimized-Python refusal, all four
  extracted-app options (automation, clipboard protocol, renderer stress,
  Inspector), original ten-second closed-child expiration, quit and modified
  sealed-resource refusal. Test archives are temporary; nothing was published.
- No sleep interposer, activity assertion, timeout widening, coverage removal
  or new subprocess-teardown implementation is used. Launch logs show Metal
  API Validation and successful display-link creation; the host has one active
  display (`display-package-current.log`). This adds genuine current archive
  runtime evidence, but does not prove the earlier background scheduling issue
  cannot recur or establish unlocked foreground performance equivalence.
- A further built-app run combines system-zsh integration with all four
  extended options and passes (`all-features-current.log`), including the
  original expiry assertion. Python syntax and tracked whitespace checks pass.
- The release objective remains incomplete: physical input/IME/pointer/drag,
  native fullscreen/Spaces, presentation and resource/performance comparison,
  Apple Silicon/earliest-supported Monterey, update installation and clean
  distribution verification remain separate gates. Do not label the temporary
  development ZIPs production-ready on the strength of these smoke runs.

## Native fullscreen execution on the active display (2026-10-30)

- Retried real native fullscreen (`macos-non-native-fullscreen=false`) with a
  tab group in the currently unlocked session. The first run exposed a fixture
  race: the preexisting 1440x818 maximized frame satisfied the loose display-size
  predicate immediately, before the asynchronous native transition started;
  the subsequent changed-frame assertion then failed (`native-fullscreen-current.log`).
- Moved the existing changed-frame condition into the same bounded wait predicate
  and retained the independent assertion, original timeout, exact exit-frame
  restoration check, live PTY checks and identity/tab-order assertions. No app
  implementation, fullscreen choice or animation timing was changed. Each
  observed fullscreen frame is now printed for diagnosis.
- The corrected fixture passes two native enter/exit cycles with tab groups
  for transparent, native and tabs titlebars (`native-fullscreen-wait-frame.log`,
  `native-titlebar-native-fullscreen.log`, `tabs-titlebar-native-fullscreen.log`).
  On the tabs run, WindowServer bounds change from 1440x818 at y=25 to 1440x900
  at y=0 in both cycles, then restore to the original frame. Both terminals keep
  ID/PID/TTY, shell commands execute while fullscreen, and tab order/selection
  are retained after exit.
- A further tabs/native-fullscreen run with renderer stress and Inspector
  lifecycle checks also passes under Metal API Validation
  (`native-fullscreen-renderer-inspector.log`). The Inspector checks precede
  fullscreen; this does not assert Inspector interaction while fullscreen.
  Ordinary smoke/undo/expiry/quit checks pass in all successful runs.
- This supersedes the earlier lack of native-transition execution evidence for
  this host, not all fullscreen/Spaces gates: multiple displays, across-launch
  native fullscreen restoration, physical interaction, actual pixel correctness
  and Apple Silicon are still unverified. Python syntax/whitespace checks pass.

## Native fullscreen restoration fixture (2026-10-30)

- Extended `session-check.py` to accept native fullscreen (`false`) without
  changing the production restoration implementation. The geometry wait expects
  one on-screen app window in the native fullscreen Space, retaining two for
  ordinary/non-native windows. It now waits for a changed frame as well as size,
  avoiding the same asynchronous-entry race found in the live transition test.
- The attempted native session run did not enter fullscreen
  (`native-fullscreen-session.log`). A subsequent public CoreGraphics session
  query reports `CGSSessionScreenIsLocked = 1`; the previously unlocked host is
  now locked. This is not evidence of a restoration defect: the run never
  reached quit/relaunch. Added a native-only locked-session preflight, verified
  to refuse before launching the test app
  (`native-fullscreen-session-preflight.log`). No session/security settings changed.
- Existing tabs/beta/visible-menu restoration passes with the updated geometry
  helper (`session-geometry-regression.log`): windows, split tree, tab selection
  and order, frontmost window, exact fullscreen and exit frames, live restored
  PTY and subsequent never-restore launch. Native across-launch restoration
  remains unverified until the session is unlocked.

## Native menu shortcut regression coverage (2026-10-30)

- The host remains locked; instead of retrying native fullscreen, extended
  `config-check.py --menu-shortcuts` through the unchanged production
  MenuShortcutManager, real GhosttyKit config parser/input bridge and AppKit
  NSMenu actions. No production change or additional runtime cost is needed.
- All 15 upstream MenuShortcutManager/NormalizedMenuShortcutKey tests run via a
  bounded adapter. The three manager tests execute serially on the main actor
  instead of awaiting actor hops; the split controller selector is spelled with
  NSSelectorFromString without linking the full controller. Original test files
  remain unchanged. This is not full Swift Testing concurrency coverage.
- Additional assertions cover actual target callbacks, physical-key precedence
  over Unicode matches, disabled physical bindings not falling through, modifier
  mismatch/empty keys, latest-registration replacement, detached menu items,
  reset, weak ownership/released entries and unbinding after config reload.
  The fixture clears default bindings before testing its own bindings; otherwise
  new_window legitimately retains its default Cmd+N after removing Cmd+A.
- Both -Onone and -O pass the menu checks and the existing 43 config invocations.
  Both reject compiled mutants for disabled-item dispatch, wrong duration units
  and Optional integer ABI storage (`menu-shortcut-check.log`). The linked Zig
  core remains ReleaseFast. Python syntax, tracked whitespace and Swift fixture
  lint pass (the existing lint config/deprecated CLI warnings remain).
- Events and menus are isolated in-process, not injected into the desktop; no
  input-source changes, personal settings, application menu replacement or
  AppleEvents are used. Physical keyboard/IME/layout switching and full app
  event dispatch remain separate acceptance gates.

## Historical restoration archive compatibility (2026-10-30)

- Added `restoration-codec-check.py` to run the three upstream
  TerminalRestorableTests with their original four embedded archives: quick
  terminal v1, terminal v5, terminal v7 and generic terminal v7. It compiles
  the production CodableBridge, SplitTree and complete extracted state schemas,
  protocol implementation and version constants on Monterey. Original test files
  and all product sources are unchanged.
- Added a current secure protocol round trip preserving focused view ID,
  ordered split IDs, fullscreen mode, tab color and title; versions 0 and 4
  are rejected by the production minimum-version guard. The fixture uses the
  upstream dummy states/MockView, not real surface/controller construction.
  Its private generic dummy bridge needs an explicit test class-name mapping
  for the new round trip, consistent with the historical archive test approach.
- Both -Onone and -O pass (`restoration-codec-check.log`). Both reject a compiled
  schema mutant making the v7 title required: decoding the real v5 archive
  returns nil through CodableBridge and fails the upstream require assertion.
  Errors are caught by the fixture runner instead of deliberately crashing.
- Swift 5.7 emits actor-conformance warnings for the upstream dummy test types;
  these are not production-source failures or full Swift Testing coverage.
  No saved user sessions, preferences or processes are used. Native fullscreen
  across-launch UI restoration remains a separate, still-open gate.

## Native restoration: launch-path distinction (2026-10-30)

- The session is unlocked again. The direct-executable tabs/beta/native-fullscreen
  run reaches quit/relaunch but selects the ordinary tabbed window/Space instead
  of the saved fullscreen standalone window (`native-fullscreen-session-unlocked.log`).
  A Debug entitlement-only LLDB probe confirms gamma actually has the fullScreen
  style bit; beta is key/main (`native-session-diagnostic.log`). This is a focus/
  Space result, not loss of fullscreen state or the split tree.
- Temporarily bypassing only the Monterey selection/order batch does not fix
  it and additionally loses beta selection (`native-session-no-batch.log`). The
  temporary source change was restored byte-for-byte, and ReleaseLocal rebuilt
  (`native-restore-clean-build.log`). All seven Mach-O/signature checks pass
  (`native-clean-bundle.log`). No diagnostic product change remains.
- Explicitly activating gamma switches to its fullscreen Space, exposing a
  separate AppKit titlebar window. With tabs style, its 54px titlebar overlays
  content at y=38/h=862; native style exposes a 44px titlebar over full-height
  content. These windows made the old exact-count geometry predicate fail.
  The fixture now combines a short titlebar and aligned content extent for
  native fullscreen only, preserving exact pre/post regular-window assertions.
- Added explicit `--launch-via launchservices`; direct launch remains the default
  and is not silently replaced. `open -W -n` owns the lifecycle handle, with the
  unique isolated executable PID used for geometry/LLDB and failure cleanup.
  LaunchServices tabs/beta and native/alpha runs pass across-launch native
  fullscreen geometry, frontmost window, tab selection/order, focused split,
  exit-frame restoration, live restored PTY and never-restore behavior
  (`native-session-ls-final.log`, `native-session-native-titlebar-ls.log`).
- The normal app launch path now has actual native fullscreen restoration
  evidence on this host. The direct CLI path still has an unresolved frontmost
  Space discrepancy; the upstream CLI activation/arrangeInFront path differs
  from LaunchServices, but causality is not yet established. Multi-display,
  physical interaction, pixel correctness and other hardware remain open.

## Direct CLI fullscreen restoration activation (2026-10-30)

- Reproduced the direct-launch failure with the corrected geometry fixture.
  Removing only `arrangeInFront` does not fix it (`cli-no-arrange-session.log`).
  Temporary targeted traces show gamma already restored fullscreen on another
  Space, with no key/main window before/after the synchronous activation calls;
  the ordinary beta window becomes key/main afterwards (`cli-trace-session.log`,
  `/tmp/ghostty-session-sxej_jv7/launch-2.log`). Thus it is not simply a synchronous
  arrangeInFront reorder, nor loss of native fullscreen state.
- Retain the saved frontmost window weakly during restoration, consume the
  reference at launch completion, and explicitly make it key/front after direct
  CLI activation only if it is native fullscreen. LaunchServices continues to
  handle its own activation; ordinary/minimized restoration does not receive
  a new activation. This reuses the already-encoded window order, adding no new
  persisted key, timer, event monitor or ongoing polling. No frontend/core
  architecture or fullscreen implementation replacement is needed.
- The previously failing direct tabs/beta run passes, as do direct native/alpha,
  LaunchServices tabs/beta, and ordinary tabbed-front restoration on the final
  rebuilt app (`cli-front-final-tabs.log`, `cli-front-final-native.log`,
  `cli-front-final-ls.log`, `cli-front-final-tabbed.log`). Assertions retain
  fullscreen/exit geometry, front window, selected tab/order/focused split,
  live PTY and never-restore checks. This supersedes the direct-launch failure
  gate above for the tested one-display cases, not multi-display/physical QA.
- The native restoration-batch fixture now checks nil/non-fullscreen candidates,
  one-shot consumption and weak ownership. Both optimization modes pass these
  plus existing selection/order, hidden/key/minimized lifecycle assertions and
  three compiled negative controls (`restoration-front-order-check.log`).
  Both changed Swift files pass strict lint with the existing config warning.
- All `[DEBUG-cli]` tracing and the temporary arrangeInFront removal are gone;
  final ReleaseLocal rebuild succeeds (`cli-front-final-build.log`).
- Final non-native fullscreen restoration, combined app smoke (AppleScript,
  denied clipboard protocol, renderer stress, Inspector, isolated system-zsh
  integration, original child-expiry limit), and all-seven-Mach-O/signature
  audit pass (`cli-front-final-nonnative.log`, `cli-front-final-smoke.log`,
  `cli-front-final-bundle.log`). Python syntax/whitespace checks pass.

## Fullscreen tab-group restoration expansion (2026-10-30)

- Extended `session-check.py --fullscreen false --front-window tabbed` to put
  the two-tab group itself in native fullscreen before quitting. Existing
  standalone coverage did not exercise this. Exit/PTY actions now address the
  configured front tab, and additional assertions retain tab order, selection
  and front window after fullscreen exit. Non-native tabbed mode remains
  rejected because that mode does not support tabs.
- This exposes an exact exit-frame discrepancy: native fullscreen, selection,
  grouping and front window restore, but tabs titlebar exit can add 38px height
  or shift y by 38px (`native-tabbed-session.log`, `tabbed-tabs-final.log`,
  `tabbed-tabs-repeat.log`). Transparent titlebar also showed a 38px mismatch
  (`tabbed-transparent-session.log`). These failures remain failures; no frame
  tolerance or accepted error was added.
- A pre-fullscreen activation wait and explicit front-tab assertion remove a
  fixture race when the tab group is activated just before capturing geometry.
  Native titlebar then passes once (`tabbed-activation-wait.log`), but the tabs
  discrepancy persists. A temporary no-relaunch control passes native titlebar;
  its generic PASS wording is not across-launch evidence (`tabbed-no-relaunch.log`).
- Temporarily bypassing only the restoration selection batch does not eliminate
  the mismatch (`tabbed-no-batch-session.log`). Restored the source byte-for-byte
  and rebuilt ReleaseLocal (`tabbed-clean-build.log`); no product diagnostic
  change remains. A Debug-only LLDB frame probe independently observes both
  alpha/beta changing from AppKit {{0,57},{800,628}} to {{0,19},{800,666}} after
  restoring and exiting fullscreen (`tabbed-frames-diagnostic.log`). Gamma is
  unchanged. This supports an actual tab-group frame discrepancy, not merely
  WindowServer choosing a titlebar as the terminal window.
- Root cause and minimal fix remain open. Do not claim all native fullscreen
  restoration is covered by the earlier standalone passes. The Debug diagnostic
  app predates the CLI activation fix and was deliberately launched through
  LaunchServices; its evidence is limited to frames, not current CLI activation.
- A native-titlebar repeat also fails its exact frame check
  (`tabbed-native-postexit.log`), so the one native pass is not a resolved gate.
  The existing standalone scenario still passes with the new post-exit tab/
  front-window assertions (`tabbed-standalone-regression.log`); the clean rebuilt
  bundle passes all seven Mach-O/signature checks (`tabbed-clean-bundle.log`).

## Native tab-group exit-frame preservation (2026-10-30)

- Targeted setFrame stack tracing shows Monterey restoring alpha/beta directly
  into fullscreen from their newly constructed default frame, without first
  applying the saved regular frame. AppKit's exit transition then returns that
  default frame (`tab-frame-trace-session.log`, `tab-frame-traces.log`). The
  apparent 38px issue is not a constant correction: position/size can be lost
  more broadly. Gamma's ordinary restore does apply its archived frame.
- A temporary diagnostic supplying the actual pre-fullscreen frame before
  completionHandler makes the formerly failing scenario pass
  (`tab-frame-seed-session.log`). Replaced that probe with capture at
  windowWillEnterFullScreen, sharing the rectangle across the tab group (or
  inheriting an already-fullscreen sibling's exit frame). Encode it only while
  native-fullscreen, under an optional NSCoder key; seed valid geometry before
  handing native restoration to AppKit. No private AppKit keys, frame offsets,
  post-animation resize timers or changes to the version-7 Codable schema.
- Tabs/beta, native/alpha, transparent/beta, LaunchServices tabs/alpha and
  standalone native restoration pass the exact frame assertions on the initial
  fix (`tab-frame-fix-session.log`, `tab-frame-fix-native.log`,
  `tab-frame-fix-transparent.log`, `tab-frame-fix-ls.log`,
  `tab-frame-fix-standalone.log`). No geometry tolerance was widened.
- Added a bounded native frame codec fixture with real AppKit tabs/NSCoder,
  extracted production paths and shell controllers. Fullscreen membership is
  simulated for this unit boundary only. Both optimization modes reject
  compiled no-seed and negative-size mutants (`native-frame-unit-final.log`).
  The boundary test caught CGRect.width normalizing a negative stored size;
  validation now checks frame.size.width/height directly. Missing-key archives
  retain AppKit behavior rather than inventing a rectangle; previously lost
  geometry in old archives is not retroactively recoverable.
- All temporary frame traces and the test environment hook are removed;
  ReleaseLocal rebuild succeeds (`tab-frame-validation-build.log`). Both changed
  Swift files pass strict lint with the existing config warning; Python syntax
  and tracked whitespace checks pass. Multi-display relocation/clamping, sleep/
  wake, physical input and other architecture release gates remain open.
- Final rebuilt tabs/beta and native/alpha tabbed sessions pass again
  (`tab-frame-final-tabs.log`, `tab-frame-final-native.log`). However the
  non-native visible-menu regression now starts from an 800x666 cascaded
  rectangle and exits restored fullscreen at 1440x818
  (`tab-frame-final-nonnative.log`). Earlier passes started maximized and thus
  did not discriminate this geometry loss. The native-only key is neither
  encoded nor consumed for non-native fullscreen; a causal before/after
  comparison and the non-native restore path still need investigation. Do not
  count this failed run as a passing regression or widen its frame assertion.
- The final boundary fixture (including absent-key and non-native exclusions),
  combined extended app smoke and all-seven-Mach-O/signature audit pass
  (`native-frame-unit-final.log`, `tab-frame-final-smoke.log`,
  `tab-frame-final-bundle.log`). No debug frame probe remains in product sources.

## Non-native fullscreen regular-frame preservation (2026-10-30)

- A repeat with saved maximized defaults passes, confirming why previous smoke
  geometry could miss the issue. Added `--fixed-window-geometry` to require an
  explicit 80x24-cell, offset, non-maximized window. The actual frame is checked
  to be smaller than the display before entering fullscreen. This reproduces
  648x454 at x=120/y=125 returning as 1440x818 after relaunch/exit
  (`nonnative-fixed-red.log`), without weakening the exact exit assertion.
- NonNativeFullscreen already retains live content/chrome state, but it was not
  persisted. Its AppKit archive contains the borderless fullscreen rectangle;
  restoration enters non-native fullscreen again and captures that rectangle
  as the new regular frame. Retain the original frame alongside existing saved
  content geometry, encode it under a separate optional NSCoder key only while
  this saved state exists, and apply valid geometry after AppKit restoration
  but before non-native enter(). Normal live exit still restores content/chrome
  in the existing order. Native capture/restore remains separate and unchanged.
- The same red fixture now passes (`nonnative-fixed-green.log`). Fixed-geometry
  hidden-menu/native-titlebar, padded-notch/transparent-titlebar, LaunchServices
  visible-menu/tabs, and native fullscreen tab-group regressions pass
  (`nonnative-hidden-menu-fixed.log`, `nonnative-padded-fixed.log`,
  `nonnative-ls-fixed.log`, `nonnative-native-regression.log`). This host has no
  notch; padded-notch is the mode path, not hardware-notch verification.
- Extended the native boundary fixture with production non-native decode/seed
  statements, invalid rectangle rejection and a no-non-native-seed mutant.
  Both optimization modes pass and reject all three compiled mutants
  (`fullscreen-frame-codec-all.log`). This is supplemental to actual session
  tests, not a mock replacement for app acceptance. Strict lint, Python syntax
  and tracked whitespace checks pass. ReleaseLocal rebuild succeeds
  (`nonnative-frame-build.log`). Old archives without the new key still rely
  on AppKit's prior behavior; no missing historical rectangle is fabricated.
- A further fixed-window session, combined extended smoke (automation, denied
  clipboard protocol, renderer, Inspector, system-zsh integration and original
  child-expiry limit), and seven-Mach-O/signature audit pass
  (`nonnative-fixed-repeat.log`, `nonnative-final-smoke.log`,
  `nonnative-final-bundle.log`). No release is published or certified by these
  tests; remaining physical/hardware/distribution gates are unchanged.

## Fullscreen tab replacement and native layout recursion (2026-10-30)

- Added `session-check.py --replace-fullscreen-tab`, restricted to native
  fullscreen with beta selected in the front tab group. It selects alpha,
  closes beta through the real close-tab action, creates/selects a replacement
  beta while fullscreen, then runs the full save/relaunch/exit fixture. This
  exercises inheritance by a new tab, not just preexisting-tab frame capture.
- Current ReleaseLocal passes with fixed non-maximized geometry, retained
  split focus, grouping/order/selection, front window, restored PTY and exact
  exit rectangle (`fullscreen-replacement-session.log`). However launch-1.log
  also reports native layout recursion. Functional PASS does not cover this
  warning or establish presentation/performance correctness.
- Debug-only LLDB breakpoint tracing (no production edits) at the AppKit
  diagnostic shows NSHostingView frame changes notifying
  NSTitlebarAccessoryViewController, whose fullscreen companion relayout calls
  displayIfNeeded/layoutIfNeeded during an active view-tree layout
  (`fullscreen-layout-trace.log`,
  `/tmp/ghostty-session-3v7ni8x1/layout-trace.log`). The Debug app is older;
  this trace identifies the layout path, not current build acceptance.
- A standalone AppKit/SwiftUI program with no Ghostty code reproduces the same
  warning when a titlebar accessory's content changes while fullscreen.
  Static empty-content controls do not. A container view, fixedSize and deferred
  viewDidLayout experiments do not remove it; none were added to product code.
- Promoted the minimal static/dynamic/static diagnostic to
  `accessory-layout-check.py` / `accessory-layout-probe.swift`. All native
  entry/tab/exit checks execute and the warning appears only in dynamic mode
  (`accessory-layout-control.log`). This is a reproduced OS path, not a reason
  to suppress the warning, remove zoom/update UI, or declare the release ready.
  The warning's product impact and a safe minimal mitigation remain open.
  Python syntax, Swift probe lint and tracked whitespace checks pass.

## Accessory mitigation rejects stale-layout workaround (2026-10-30)

- Rechecked current source/build state and unlocked session. Continued the
  minimal native diagnostic rather than changing the app speculatively.
  Deferring NSHostingView frame notifications at setFrameSize, layout, or the
  frame property does not remove the warning (`accessory-deferred-frame.log`,
  `accessory-layout-notify.log`, `accessory-frame-property.log`). A manually sized
  plain NSView accessory does not reproduce it (`accessory-appkit-only.log`),
  narrowing the observed path to hosting/autolayout interaction, not arbitrary
  titlebar size changes.
- A manually sized NSHostingView container with deferred size propagation
  initially removes the warning (`accessory-manual-container.log`), but fails a
  hide/show follow-up: the accessory retains its occupied titlebar width when
  content becomes empty (`accessory-manual-hidden-check.log`). Rejected this
  approach; no product wrapper, notifications override, or frozen layout added.
- The unchanged native hosting path does shrink to 0x0 and return to 30x37 on
  hide/show despite reporting recursion (`accessory-native-toggle.log`). Added
  fitting-size, zero-space-hidden and repeat-expansion assertions to the checked-in
  independent probe. Static/dynamic/static runs pass these geometry assertions,
  with the warning still confined to dynamic mode (`accessory-layout-sizing.log`).
  This is bounded geometry evidence, not pixel correctness, clickability,
  accessibility, or performance proof, and not a resolution of the warning.
- Product sources remain unchanged this turn. Swift probe lint, Python syntax
  and tracked whitespace checks pass. The stronger diagnostic prevents a
  warning-only green result from silently accepting lost accessory behavior.

## Accessory follow-up: rejected probes, no product change (2026-10-30)

- Two more temporary container experiments do not meet the existing geometry
  contract: intrinsic-size invalidation still fails hidden-space release, and
  GeometryReader/preference-based sizing fails the visible-size assertion
  (`accessory-intrinsic-container.log`, `accessory-measured-container.log`).
  Neither is adopted.
- An in-process accessibility lookup does not discover the SwiftUI button in
  the fullscreen fixture (`accessory-action-probe.log`). Synthetic in-process
  mouse delivery also leaves the action counter at zero; the final queued-event
  probe exits on its action assertion (`accessory-mouse-probe.log`). These probes
  have not established a working interaction control, so their failures are
  fixture limitations, not evidence of a Ghostty input/accessibility defect.
  No cross-process input, permission changes, or user clipboard writes are used.
- Product sources remain unchanged. The native layout warning remains open;
  passing geometry assertions is not an interaction or performance acceptance
  result. Do not add a wrapper that loses behavior merely to silence the warning.

## Post-fullscreen-fix archive validation (2026-10-30)

- Re-ran `package-check.py macos/build/ReleaseLocal/Ghostty.app` after the
  fullscreen frame fixes. Archive extraction, checksums, original/extracted
  seven-Mach-O audits, strict signatures, refusal of overwrite/optimized Python/
  dirty release metadata, and tampered-resource rejection all pass
  (`package-post-fullscreen.log`).
- The extracted-app extended smoke also passes automation, denied clipboard
  protocol, renderer modes, Inspector, tab references, split/tab/window undo,
  quick-terminal lifetime and the original child-expiry check. No scheduling
  assertion or timeout was changed. This invocation does not add fullscreen
  restoration coverage; that remains in the separate session fixture.
- This is a development archive marked NOT-FOR-RELEASE, removed with its
  temporary directory after the check. It is not Gatekeeper, notarization,
  signed-update, arm64-runtime or clean-machine acceptance.

## Accessory interaction control (2026-10-30)

- The temporary fullscreen click probe reports a zero visible rectangle even
  though its hosting view has a nonzero frame. Setting the public accessory
  `fullScreenMinHeight` alone does not expose the click target in that fixture
  (`accessory-reveal-probe.log`). A failed click there cannot establish that a
  visible fullscreen button is broken.
- Removing fullscreen transitions from the same probe delivers the action
  (`accessory-regular-click.log`). Added this regular-window control to the
  checked-in diagnostic: post mouse events only to the probe's own event queue,
  require the target point to be unclipped, and assert exactly one action both
  initially and after hide/reveal. A compiled no-action mutant fails, proving
  the fixture checks dispatch rather than only the existence of a button.
- All static/dynamic/regular/static-repeat cases and the negative control pass
  (`accessory-interaction-control.log`); recursion is still confined to dynamic
  fullscreen. Swift lint, Python syntax and tracked whitespace checks pass.
  This improves the independent control, not full-app or physical-input
  acceptance. Visible-fullscreen interaction and safe warning mitigation remain
  unverified. No product changes are made for this diagnostic.

## Further native controls and patch reduction (2026-10-30)

- Accessory probes reject two more shortcuts: enabling autoresizing-mask
  translation fails the existing fitting-size assertion; removing Spacer still
  emits layout recursion (`accessory-autoresize-probe.log`,
  `accessory-no-spacer.log`). Removing autoHideToolbar from the test app's
  presentation options still leaves the fullscreen click target clipped
  (`accessory-presentation-probe.log`). None changes product code.
- Retried cross-process Services with the session unlocked. Discovery still
  selects an older temporary bundle with the shared smoke identifier rather
  than this run's unique service names (`services-unlocked-current.log`). A
  disposable higher-build-number copy does not change that outcome
  (`services-version-probe.log`). Both stop before invoking a service and
  unregister their own copy; no database reset, consent bypass or installed-app
  change is performed. The discovery gate is not caused solely by session lock.
- Reduced duplicated compatibility code in FileHandle and KeyEquivalent:
  compiler conditions now select only conformance syntax, with one shared
  implementation of each protocol witness. No runtime branch or behavior is
  added. Expanded `value-check.sh` to compile both production files and verify
  generic equality, existential description and TextOutputStream pipe output;
  both optimization modes pass (`conformance-value-check.log`). Swift lint
  passes for the changed Swift files.
- Rebuilt the universal ReleaseLocal app successfully after deduplication;
  seven-Mach-O/signature audit and standard isolated GUI/PTY/undo/expiry smoke
  pass (`conformance-dedup-build.log`, `conformance-dedup-bundle.log`,
  `conformance-dedup-smoke.log`). This verifies the current app build rather
  than relying solely on the small protocol-witness fixture.

## Cross-process Services now exercised without Automation (2026-10-30)

- A unique test bundle identifier resolves the duplicate-registration problem.
  Instead of using AppleScript to observe terminals (which previously introduced
  a separate consent dependency), a disposable command reports its own cwd and
  PTY from each real terminal child. Temporary probes pass both filename-list
  and plain-text inputs (`services-isolated-probe.log`,
  `services-text-probe.log`), without product changes or permission changes.
- Added `services-standalone-check.py`: unique app/service names, unchanged
  production ServiceProvider, native NSPerformService client, unique pasteboards
  with scoped release, and AppleScript disabled in the test config. Eight cases
  cover openTab/openWindow, filename-list/plain-text, directory/file input, and
  spaces/quotes in paths. Each creates one real child with the expected cwd and
  PTY; cleanup unregisters only the test app and checks reporting children exit.
- All eight cases pass (`services-standalone-final.log`). Native Services
  mediation accepts plain-text paths even though directly invoking the provider
  with a string-only board does not. No additional path parser or compatibility
  branch is warranted by the earlier direct-provider result.
- The initial promoted fixture had a config quoting error and failed before
  creating its first child (`services-standalone-check.log`); corrected with
  explicit shell mode and shell-quoted arguments, not a product change.
- This proves cross-process service dispatch and real terminal cwd/PTY on this
  Intel Monterey host, not Finder menu presentation, UI grouping, all text path
  formats or arm64 runtime. The original shared-ID smoke `--services` discovery
  failure remains accurately documented rather than treated as passing.
- A second independent invocation passes all eight cases and cleanup checks
  (`services-standalone-repeat.log`); no test child/app processes remain. Python
  syntax and tracked whitespace checks pass.

## Services window routing and cross-process accessibility (2026-10-30)

- Extended the independent Services fixture with WindowServer counts: four tab
  calls retain one visible window, four window calls grow the count to five
  (`services-window-count.log`). A disposable signed-copy plist mutant routing
  the tab service to openWindow fails on the first call's extra window
  (`services-wrong-selector.log`). No production selector changes are made.
- Read-only permission preflight confirms existing Accessibility access; no
  permission prompt/settings change is used. Initial AXChildren-only traversal
  exposes an incomplete window node. Explicit AXWindows traversal exposes the
  actual terminal pane, scroll area, text area, native tabs and selection
  (`services-ax-probe.log`, `services-ax-attributes.log`). This fixture issue is
  not treated as a product accessibility defect.
- Added opt-in `--accessibility`: query native window/tab trees, assert counts
  and one selected tab, then verify the focused terminal's AXTextArea contains
  a marker printed by its real child, including cwd. All eight service cases
  pass (`services-accessibility-check.log`), without AppleScript or changing
  application code. This establishes bounded cross-process text/tree access;
  AX actions/notifications, selected-text ranges and VoiceOver navigation remain
  separate acceptance work.
- A wrong-terminal-marker control fails the initial AX text assertion while
  retaining correct child cwd/PTY reporting (`services-wrong-ax-marker.log`).
  Repeat and final runs pass all eight cases and cleanup
  (`services-accessibility-repeat.log`, `services-accessibility-final.log`).
  Generated Swift client lint, Python syntax and tracked whitespace checks pass.

## Unicode accessibility count/range correction (2026-10-30)

- Expanded the real AX probe with a supplementary-plane character and combining
  mark. The current app reports 52 characters for text whose NSString/UTF-16
  length is 54 (`accessibility-unicode-red.log`). A native NSTextView control
  reports UTF-16 units. This is an inherited upstream 1.4 defect (baseline has
  the same String.count expressions), not a regression introduced by lowering
  deployment target; it still breaks the tested Monterey accessibility contract.
- Corrected only accessibilityNumberOfCharacters and the visible range length
  to use content.utf16.count. No compatibility layer, cache policy change or
  terminal rendering change is added. The existing substring method already
  consumes UTF-16 NSRange, so reported count/range now agree with it.
- Added `accessibility-text-check.py`, extracting these exact methods against a
  fixed cache and native AppKit control. It fails before the fix
  (`accessibility-text-red.log`); ASCII, CJK, emoji, combining marks, ZWJ sequence,
  full-range and per-grapheme substring checks pass in both optimization modes.
  Separate compiled count and range mutants fail their assertions
  (`accessibility-text-final.log`). This small test does not replace AX transport.
- Rebuilt universal ReleaseLocal, then passed the actual app's eight Services/AX
  cases with Unicode markers, AXNumberOfCharacters, AXVisibleCharacterRange and
  AXStringForRange full-text round trips (`accessibility-unicode-build.log`,
  `accessibility-unicode-green.log`). Strict bundle/seven-Mach-O audit also passes
  (`accessibility-unicode-bundle.log`). Generated client and isolated changed
  method lint pass. Line-index mapping, selected-range offsets, notifications
  and VoiceOver interaction remain outside this bounded fix.
- Standard current-app GUI/PTY/undo/expiry smoke passes after rebuilding
  (`accessibility-unicode-smoke.log`); Python syntax and tracked whitespace
  checks pass. No production instrumentation remains.

## UTF-16 accessibility line indexing (2026-10-30)

- Extended the same production-method fixture to line queries. For text
  `rocket-emoji + newline + next`, querying UTF-16 offset 2 (the newline) returns
  line 1 rather than 0 because String.prefix counts graphemes
  (`ax-line-red.log`). Added a second line to the real child marker and queried
  AXLineForIndex across its newline; the current built app also fails
  (`ax-line-app-red.log`). This is another inherited upstream expression, not
  evidence of a newly introduced Monterey-only regression.
- Converted only the prefix operation to UTF-16 decoding, retaining existing
  newline counting and positive out-of-range clamping. Negative indices now
  return NSNotFound rather than trapping in prefix. No cache or core ABI change.
- The bounded fixture checks every UTF-16 offset, including surrogate interiors
  and combining/ZWJ sequences, before/at/after newlines. Production passes in
  both optimization modes; the compiled grapheme-line mutant fails, alongside
  existing count/range mutants (`ax-line-green.log`). Generated AX client and
  isolated changed-method Swift lint, Python syntax and whitespace checks pass.
- Universal ReleaseLocal rebuild, real-app AX line/count/range/text checks for
  all eight service cases, strict bundle audit and standard smoke pass
  (`ax-line-build.log`, `ax-line-app-green.log`, `ax-line-bundle.log`,
  `ax-line-smoke.log`). Selected-range coordinate conversion and notification
  semantics remain separate work; these successes do not certify all AX behavior.

## Actual AX selection action/notification exposes range defect (2026-10-30)

- Used the isolated app's AX Select All menu action and registered an AXObserver
  on its terminal text area. The action succeeds, one selected-text-change
  notification arrives, and selected text equals the displayed fixture text.
  However AXSelectedTextRange reports length 109 while that text has 66 UTF-16
  units; AXStringForRange fails for the reported range
  (`ax-selection-probe.log`, `ax-selection-repro.log`).
- Added opt-in `services-standalone-check.py --accessibility --selection` and
  `accessibility-selection-client.swift` as an explicit failing regression.
  The harness disables copy-on-select and clipboard reads/writes, requires
  existing AX permission, invokes only the target app's menu (no global input),
  and removes its observer on completion. It fails rather than masking the
  inconsistent range; the existing read-only suite remains separate.
- An ASCII-only control still reports 109 versus 65 units
  (`ax-selection-ascii.log`). This is not merely another Unicode-count bug.
  Source tracing shows selectedRange() directly uses the core's viewport cell
  offsets (`row * columns + column`, endpoint difference) as an NSRange, while
  AXValue is flattened screen text with unwrapped/trimmed rows. The same
  expression exists in upstream. Correct mapping must account for coordinate
  origin, padding, Unicode, wrap, scrollback and partial/rectangular selection;
  replacing only length or searching for the first selected-string occurrence
  would be incorrect for repeated text and is not adopted.
- No product changes in this investigation. Swift client lint, Python syntax
  and tracked whitespace checks pass. Selection range repair remains open;
  action/notification success is not a waiver of the failing range assertion.
- Read-only AX/Services suite still passes all eight cases with the explicit
  clipboard restrictions (`ax-selection-baseline.log`); no test child/app
  processes remain after successful and failing invocations.

## Selection mapping: existing formatter seam and counterexamples (2026-10-30)

- Added a test-only `StringMap selection range mapping feasibility` case using
  the real terminal parser, selection formatter and existing byte-to-pin map.
  Repeated identical text, backward selection, emoji/combining marks, hard and
  soft wraps, history-only selections, and selections spanning history/current
  viewport now have bounded mapping evidence. No new production helper, C ABI
  or Swift selection workaround is introduced.
- The first basic mapping run passes (`selection-map-feasibility.log`), but
  adding scrollback catches an important counterexample: formatter-inserted
  newline bytes can share the last selected text cell's pin. Filtering only
  by pin membership returns an extra newline not present in the selected text
  (`selection-map-scrollback.log`). The fixture records that boundary explicitly
  rather than accepting this algorithm as a correct selection-range repair.
- Rectangular selection provides another explicit counterexample: its text is
  not one contiguous substring of the full screen. A future AX implementation
  must consider selectedTextRanges rather than expand a single range over
  unselected cells. Pin-based origin plus exact serialization boundaries is the
  useful seam; first-occurrence string search and raw cell offsets remain invalid.
- The expanded targeted test passes (`selection-map-boundaries.log`, 78 total
  tests including dependencies). `-Doptimize=ReleaseFast` rerun reuses the build's
  Debug test artifact (`selection-map-release.log`); it is not independent
  optimized-test evidence. Zig formatting and tracked whitespace checks pass.
  The app's selected-range regression remains red and the release goal incomplete.

## Serialized selection origins, not raw cell membership (2026-10-30)

- Extended the real formatter fixture to locate the selection's serialized
  first-byte pin in the full-screen map, then validate the exact selected byte
  length/content. This avoids the extra-newline membership failure and correctly
  distinguishes repeated strings, including selections wholly in scrollback.
  Explicit UTF-16 prefix assertions cover Unicode before the selection.
- A selection starting on a wide glyph's spacer-tail cell is another raw-pin
  membership counterexample: the formatter includes the complete glyph from
  its leading cell, but no emitted byte belongs to the selected tail cell.
  The serialized origin resolves it (`selection-serialized-origin.log`).
- Blank leading rows and selected spaces also pass (`selection-origin-empty.log`).
  For the rectangular fixture, row-wise serialized origins map to disjoint
  full-text spans and each span reproduces its selected row; the encompassing
  single range is still explicitly rejected (`selection-origin-rectangle.log`).
- All expanded targeted runs pass (78 aggregate tests including dependencies).
  Changes are test-only and formatting/whitespace checks pass. This is bounded
  evidence for an implementation seam, not a shipped mapping API, performance
  proof or a fix for the still-failing app AX selection range. A production
  implementation must avoid a full per-byte map allocation on routine reads and
  preserve atomic text/range identity while the terminal changes.

## Selection mapping without allocating a full pin map (2026-10-30)

- Tested a lower-memory alternative against the existing map oracle: serialize
  the prefix from screen origin through the selection's inclusive endpoint,
  subtract the exact selected text byte length, and verify the resulting slice
  of the complete text. This passes the current repeat/backward/Unicode/wrap/
  history fixtures (`selection-prefix-length.log`). It does not search by text.
- A bounded 31-byte Discarding writer produces exactly the same prefix length
  through the real ScreenFormatter, without allocating prefix text or a
  per-byte pin map. Rectangle row prefix calculations also match their mapped
  origins (`selection-prefix-counter.log`). This proves byte-position arithmetic
  for these cases, not a completed UTF-16 streaming counter or production API.
- Added exhaustive endpoint-pair checks over four small real terminal screens:
  ASCII hard wraps, wide/combining characters, repeated text and soft wraps.
  Every contiguous selection's prefix-derived range reproduces its exact
  serialized text (`selection-prefix-exhaustive.log`, 79 aggregate tests passed
  including dependencies). Formatting and whitespace checks pass.
- All changes remain tests. The app selection diagnostic is still red. The
  useful next implementation constraint is to keep this on-demand path under
  one core state snapshot, reuse the existing formatter rather than duplicate
  terminal layout, and expose disjoint rectangle ranges without slowing normal
  rendering or text reads.

## Bounded-memory UTF-16 formatter counter (2026-10-30)

- Implemented `Screen.selectionUtf16Length`, reusing the production plain-text
  ScreenFormatter with the same unwrap/trim/selection options as selectionString.
  A 256-byte stack writer counts valid UTF-8 leading bytes as one or two UTF-16
  units; continuation bytes contribute zero, so split sequences need no carry
  allocation. It does not allocate serialized text or a per-byte pin map.
- Existing mapping fixtures and exhaustive endpoint pairs compare the helper
  against Foundation-independent Zig UTF-8-to-UTF-16 conversion of the actual
  serialized selection/prefix. Both trimmed and untrimmed fixtures are covered.
  Writer tests cover buffer capacities 0 through 32, bytewise split Unicode,
  flushes, multiple vectors and repeated final patterns.
- Targeted app tests pass (80 aggregate tests, `selection-utf16-boundaries.log`);
  preferred lib-vt tests pass (77 aggregate tests, including dependencies and
  C-test target runs, `selection-utf16-libvt.log`, `selection-utf16-trim.log`).
  Zig formatting and tracked whitespace checks pass.
- This is a tested internal primitive, not yet wired to the app/C API. It adds
  no calls to normal rendering or existing text reads. App-level selection still
  fails until snapshot/range transport and disjoint rectangle handling are
  implemented. No claim of end-to-end repair or measured performance is made.

## UTF-16 range primitive and reflow checks (2026-10-30)

- Added `Screen.selectionUtf16Range`: two bounded-memory formatter counts give
  the exact location/length of a contiguous selection in untrimmed screen text.
  The helper explicitly requires an unchanged screen across both passes and
  rejects multi-row rectangles in Debug; callers must supply rectangle rows
  separately. No existing read API or renderer path calls it yet.
- Existing map-oracle and exhaustive endpoint fixtures now exercise this real
  helper instead of only test arithmetic (`selection-utf16-range.log`). Added
  rectangle row tests for every horizontal bound on four screens with repeated
  text, blank rows, short rows, Unicode and scrollback. Each resulting UTF-16
  range reproduces its row from the full text, and ranges stay ordered/in bounds
  (`selection-rectangle-ranges.log`).
- A tracked selection of the second repeated word after an emoji survives
  widths 20/6/12/4/20; actual terminal reflow retains its text and exact UTF-16
  range (`selection-range-reflow-final.log`). An initial fixture typo used the
  wrong selection setter and was corrected before execution; no product failure
  is inferred from that compile error.
- Combined lib-vt run passes 81/87 aggregate tests, with six existing Oniguruma
  search tests skipped by the lib-vt build's disabled regex option
  (`selection-range-all.log`). The new range/counter tests execute, not skip.
  Formatting and whitespace checks pass. App selection remains uncorrected
  until lock-scoped snapshot transport and AX range integration are implemented.

## Owned text/range snapshot primitive (2026-10-30)

- Added `Screen.textSnapshot` with owned full text, selected text and UTF-16
  ranges. It preserves the existing formatter semantics and emits separate
  nonempty rectangle row ranges rather than including unselected columns.
  Construction requires the caller to hold terminal state stable; the Screen
  layer does not claim to acquire the surface mutex itself.
- Tests cover no selection, contiguous and rectangular selections, exact range
  values, and snapshots retaining their original strings after live terminal
  contents change. Allocation-failure injection runs at every allocation
  boundary for both selection kinds and no selection; the test allocator
  reports no leaks (`selection-owned-snapshot-final.log`,
  `selection-snapshot-all.log`). The initial compile used an obsolete allocator
  helper name, corrected to this toolchain's dupeSentinel before execution.
- Combined lib-vt run passes with the same existing regex-disabled skips;
  formatting/whitespace checks pass. This primitive is not connected to the
  C bridge or app, so the existing built app still has the selected-range bug.
  Rectangle range calculation currently recounts prefixes per selected row;
  its scaling must be addressed or measured before claiming a low-overhead
  production path. No normal rendering or existing read path calls it.

## Lock-scoped snapshot C bridge (2026-10-30)

- Added an additive C snapshot API without changing the existing ghostty_text_s
  layout or its cell-offset semantics. The new read operation holds the core
  renderer/terminal mutex across snapshot construction, then transfers owned
  text, selected text and UTF-16 range storage to the caller. Failure leaves a
  zeroed result; the free operation releases ownership and clears the fields,
  without needing a live surface. Global library initialization is still needed.
- Universal ReleaseFast core build passes all 333 steps
  (`selection-snapshot-core-build.log`); both architecture slices export the new
  read/free symbols. C11 header size/offset assertions compile for x86_64/arm64;
  a linked Intel C client initializes the actual library and exercises zero-result
  repeated free successfully. Swift 5.7 typechecking accepts the new structs and
  read signature. These are ABI/compile checks, not live snapshot acceptance.
- Added an embedded ownership test, but the normal app test root does not reach
  embedded.CAPI; its 78-test pass (`selection-snapshot-bridge.log`) is therefore
  not evidence that this particular new test ran. Existing core snapshot tests
  cover allocation/ownership; actual embedded live read/free still needs direct
  coverage when wiring the app. This limitation is explicit, not a silent skip.
- No Swift AX consumer is switched yet, so the application-level selected-range
  diagnostic remains red. The existing app bundle predates this rebuilt core;
  rebuild it before using it as evidence for the new bridge. Rectangle prefix
  scaling and snapshot cache invalidation remain required integration work.

## AX snapshot integration on Monterey (2026-10-30)

- The screen cache now holds Swift-owned text, selected text and UTF-16 ranges
  copied from the lock-scoped C snapshot. Core allocations are freed immediately
  after copying. AX value/count/line/substring/selection methods share this cache;
  NSTextInputClient.selectedRange and its existing cell-offset ABI are unchanged.
  Separate AX requests can still cross a cache expiry or selection change; this
  is a consistent captured state, not a transaction across remote AX requests.
- Selection changes invalidate the cache before the existing 100ms notification
  debounce. Added generation-safe invalidation and tests for immediate payload
  release, concurrent get/invalidate, expiry and lifetime in Onone/O builds
  (`cache-invalidate-red.log`, `cache-invalidate-green.log`). Menu validation and
  context menus retain the cheap selected-text read, avoiding full-screen
  snapshots when accessibility is not being queried. The existing App Intent
  screen-content caller is adapted to the cache's text field.
- Native extracted AX tests pass for Unicode counts/lines/substrings, no
  selection, repeated text origins and disjoint ranges, with the previous
  grapheme-offset mutants still rejected (`ax-snapshot-text.log`). Disjoint
  range tests here exercise the Swift adapter, not physical rectangular drag
  or VoiceOver behavior.
- Rebuilt universal ReleaseLocal with the new core (`ax-snapshot-app-build.log`).
  The previously failing real cross-process Select All probe now returns
  location 0, length 66 for 66 UTF-16 units (previously length 109), reproduces
  selected text via AXStringForRange, observes a selection notification, and
  verifies the plural AXSelectedTextRanges attribute. All eight standalone
  Services cases also pass (`ax-snapshot-app-selection.log`). This reaches the
  actual embedded read/free bridge, unlike the unreachable embedded unit test.
- Static universal bundle/signature checks pass (`ax-snapshot-bundle.log`);
  rebuilt-app smoke passes startup, PTY/UTF-8, split/tab/window undo/redo,
  quick-terminal lifetime, TTL cleanup and quit (`ax-snapshot-smoke.log`).
  Focused SurfaceView SwiftLint reports zero violations. Rectangle prefix
  scaling, live disjoint-selection behavior and VoiceOver remain open gates.
  No macOS 13/14 runtime acceptance is claimed or required by this port.

## Rectangle snapshot scaling and wide-wrap boundary (2026-10-30)

- Added a real Screen snapshot scaling fixture at 128/512/2048 rows. The
  original Debug path takes roughly 16/203/3404ms in one run, demonstrating
  repeated whole-screen prefix work rather than just allocation overhead
  (`snapshot-scaling-before.log`). This is a diagnostic, not a timing threshold
  or a renderer benchmark; tests assert each returned range exactly.
- Snapshot construction now counts completed pages once with the existing
  PageFormatter trailing-state mechanism, then recounts only the endpoint's
  current partial page. It adds no byte-to-pin map and no new heap allocation.
  Debug measurements fall to about 13/201/863ms (`snapshot-scaling-after.log`).
  The remaining within-page repeated work is still substantial: this is an
  intermediate optimization, not sufficient evidence of production latency.
- Expanded every-column rectangle tests to include a wide glyph wrapping at
  the right margin. This exposed a real pre-existing bug in the new range
  helper: a normal prefix includes the glyph following a spacer head, but a
  rectangular row excludes it. Both reference and snapshot endpoints now stop
  before that spacer; exact UTF-16 substring checks pass. The initial failing
  test is in `snapshot-page-ranges.log`, corrected focused run in
  `snapshot-page-ranges-wide.log`.
- Added multi-page scrollback cases with combining/wide glyphs, blank rows,
  explicit spaces and selections starting at the top/middle/end. They compare
  the optimized ranges with independent full-prefix ranges and each actual
  selected row's serialized text. Initial fixtures did not actually cross a
  page; their explicit page-count assertion caught this and the corrected
  80-column fixture passes (`snapshot-pages-boundaries.log`).
- ReleaseFast lib-vt StringMap tests pass 85/91 aggregate cases, with the same
  six Oniguruma-disabled skips (`snapshot-pages-release-all.log`). Unlike the
  app test target, this target actually uses the requested optimization mode,
  confirmed by its `compile test ... fast` build steps. A same-run 2048-row
  comparison gives roughly 272-295ms for the full snapshot versus 1045-1049ms
  for the old ranges-only prefix algorithm under concurrent build load. These
  are bounded measurements, not an idle-system latency guarantee.
- Debug StringMap aggregate also passes 85/91 with those same six skips
  (`snapshot-pages-debug-all.log`). Universal core rebuild passes 333/333 steps
  and ReleaseLocal app rebuild succeeds (`snapshot-pages-core-build.log`,
  `snapshot-pages-app-build.log`). Rebuilt-app cross-process AX Select All and
  all eight Services cases pass (`snapshot-pages-app-selection.log`); static
  bundle/signature audit passes (`snapshot-pages-bundle.log`). These live tests
  cover contiguous selection, not the newly optimized rectangle branch.

## Linear row-prefix snapshot counting (2026-10-30)

- Replaced repeated within-page prefix scans with a monotonic row cursor.
  Completed rows are counted once; only the current endpoint row is counted
  speculatively. The next iteration consumes that row in full. This preserves
  deferred blank rows/cells across hard wraps, soft wraps and page boundaries,
  with a 256-byte stack counter and no additional allocation or per-byte map.
- Added a narrow PageFormatter.continuePlain entry point to supply explicit
  prior row whitespace. Existing formatWithState keeps its original rule of
  ignoring trailing state at nonzero selection starts. Normal format dispatch
  remains specialized; the continuation path requires plain text, no point map,
  column-zero start and nonrectangular formatting. A native regression compares
  every row/column endpoint against a fresh full-prefix format, including both
  emitted bytes and deferred state. All formatter tests pass 335/335 in Debug
  (`snapshot-row-formatter.log`), including existing VT/HTML/map tests.
- StringMap tests pass 85/91 in Debug and ReleaseFast, with the six existing
  regex-disabled skips (`snapshot-row-debug.log`, `snapshot-row-release.log`).
  The 2048-row ReleaseFast snapshot now takes 2.2-2.9ms versus 698-757ms for
  the full-prefix reference ranges in the same run; 128/512-row snapshots take
  about 0.13/0.61-0.66ms. Debug 2048-row snapshots take 12.7-13.4ms. These
  fixtures include full text allocation and range correctness assertions, but
  do not measure AppKit copying, remote AX latency or arbitrary terminal data.
- ReleaseFast formatter tests also pass 335/335
  (`snapshot-row-formatter-release.log`). Universal core rebuild passes all
  333 steps, then ReleaseLocal app rebuild succeeds (`snapshot-row-core-build.log`,
  `snapshot-row-app-build.log`). Rebuilt-app AX selection and eight Services
  cases, bundle/signature audit, and basic startup/PTY/split/tab/window/quick-
  terminal/undo-redo smoke all pass (`snapshot-row-app-selection.log`,
  `snapshot-row-bundle.log`, `snapshot-row-smoke.log`). Physical rectangular drag
  and VoiceOver acceptance remain separate, unfinished gates.

## PID-targeted rectangle input diagnostic (2026-10-30)

- Added experimental `services-standalone-check.py --accessibility --selection
  --rectangle`: the isolated child prints three known rows and reports its PTY
  grid; the AX client sends Option-drag events only to the disposable app PID
  and asserts exact selected text plus three disjoint substring round trips.
  Clipboard and AppleScript remain disabled, and no global input is posted.
  This option is explicitly failing/experimental, not an acceptance pass.
- Existing AX Select All passes first, but targeted mouse events leave that
  selection unchanged (`ax-rectangle-probe.log`). Supplying public window-ID
  fields, activating the target, and using NSEvent-generated CGEvents do not
  change the outcome (`ax-rectangle-window.log`, `ax-rectangle-active.log`,
  `ax-rectangle-nsevent.log`). Activation/window-field experiments were removed
  from the retained app probe; no product workaround was added.
- Reduced this to a standalone AppKit window (`mouse-routing-check.py` and
  `mouse-routing-probe.swift`). Its local NSWindow.sendEvent positive control
  reaches mouseDown/mouseUp. The externally posted tagged down/drag/up events
  reach the process monitor but all have windowNumber zero and do not reach
  the view (`mouse-routing-check.log`). Existing AX and event-post permission
  checks both return true. Only tagged synthetic events are reported; untagged
  user input is ignored. This proves an event-routing limitation of this test
  method on the current system, not a Ghostty rectangle-selection regression.
- Ordinary rebuilt-app AX selection and all eight Services cases still pass
  with the expanded child evidence (`ax-rectangle-standard-control.log`).
  Actual AppKit-to-core rectangular drag and VoiceOver remain unverified; core
  rectangle range/ownership/scaling tests are not being substituted for them.

## Embedded native selection integration (2026-10-30)

- Added `embedded-selection-check.py`/`.swift`, linking the actual rebuilt
  universal core into a disposable NSWindow with a real child PTY. Local
  NSWindow.sendEvent button/drag events avoid the PID-routing limitation without
  global input, clipboard use, user config or permission changes. Production
  SurfaceView mouseDown/mouseUp implementations are extracted unchanged;
  modifier and mouse-position routing are explicitly bounded test adapters.
- Forward and reverse Option drags produce the exact three rectangular rows;
  ordinary drag produces a contiguous selection. Repeated words above the
  selection, preceded by emoji/combining characters, verify origin preservation
  and UTF-16 locations rather than first-occurrence string search. Both range
  forms round-trip the actual full text. Removing Option is a negative control
  that fails the expected rectangle assertion (`embedded-selection-unicode.log`,
  `embedded-selection-production-buttons.log`).
- The harness also compiles the real Swift AccessibilityTextSnapshot copying
  implementation and AX value/count/selected-text/single-range/multiple-range/
  substring methods against this live surface. Direct native method calls
  reproduce each selected row (`embedded-selection-ax-adapter.log`). Its cache
  adapter deliberately reads fresh fixed-content snapshots; it does not claim
  debounce/cache or remote AX transport coverage.
- Actual bridge tests cover no selection, repeated free clearing fields and an
  owned snapshot surviving surface destruction. The child exits after normal
  teardown and after the negative-control process exit; PID exit is checked,
  not assumed. Focused SwiftLint and whitespace checks pass. This closes a
  useful live C/Swift integration gap but does not replace full-app rectangular
  input routing, remote disjoint AX ranges, IME or VoiceOver acceptance.

## Cross-process disjoint AX range transport (2026-10-30)

- Extended the real embedded selection harness with `--accessibility` and a
  separate read-only AX client. Forward/reverse rectangles expose exactly three
  AXSelectedTextRanges; a normal drag exposes one. Each remote range preserves
  the UTF-16 origin after emoji/combining text and reproduces its exact selected
  substring through AXStringForRange. AXSelectedTextRange agrees with the first
  plural range, selected text matches, and number-of-characters matches AXValue.
- Initial probe windows were visible but absent from AXWindows, even locally.
  Running the probe as a disposable app with NSApplication's event loop alone
  did not change that. Explicitly activating it makes the native AX window tree
  available. The retained test activates only for remote acceptance and restores
  the prior front app on normal completion; no activation is used for the
  deliberately failing no-Option control. No private API, global event posting,
  preference or permission changes were introduced.
- `embedded-selection-check.py --accessibility` passes both rectangle directions,
  the contiguous case, ownership/child-exit checks and the no-Option negative
  control (`embedded-selection-remote-final.log`). Local-only mode remains a
  separate check. The production AX methods/copying code are extracted unchanged;
  the cache, motion and modifier adapters remain fixture-specific. This verifies
  actual AppKit cross-process disjoint-range transport, not the complete Ghostty
  view/runtime or VoiceOver behavior. Full-app input/IME/VoiceOver gates remain.

## Committed text and preedit against a raw PTY (2026-10-30)

- Added `--committed-input` to the embedded native harness. The real child
  disables terminal echo/canonical processing, enables bracketed paste, and
  atomically records received bytes. Production committedTextAction sends ASCII,
  Chinese, Japanese, Korean, decomposed combining text and emoji: all 32 UTF-8
  bytes arrive exactly once, unchanged, with no paste delimiters. This tests
  the actual key encoder and PTY, not just forwarded C arguments.
- Production setMarkedText/hasMarkedText/markedRange/unmarkText/syncPreedit are
  extracted unchanged apart from test visibility. Multiple preedit replacements
  and cancellation preserve native UTF-16 marked lengths and emit no child
  input. This does not assert rendered preedit pixels or input-method behavior.
- A compiled mutant replacing ghostty_surface_key with the paste API fails the
  exact PTY-byte assertion. The initial mutant run hit stale fixture output from
  the prior process; per-run cleanup fixed that harness error before accepting
  the intended mutation result. Child exit is verified after every run.
- Combined remote AX, preedit, committed input and both negative controls pass
  (`embedded-committed-preedit.log`). Focused SwiftLint and whitespace checks
  pass. No product changes were needed. Actual insertText/current-event gating,
  keyDown/interpretKeyEvents, CJK candidate handling and physical input remain
  separate open gates; injected commit payloads are not an IME acceptance claim.
- Removed obsolete 13.x/14+ release obligations from the keyboard manual gate.
  It now explicitly targets macOS 12 (including earliest supported 12.0 and
  the current 12.7.6 host) on Intel/Apple Silicon. Existing newer-OS comparison
  code remains optional diagnostic coverage, not part of this fork's promise.

## Native current-event insertText integration (2026-10-30)

- Extended the raw-PTY fixture to invoke unchanged production insertText through
  a window-local posted key event. The test keyDown callback asserts that
  NSApplication.currentEvent is a real keyDown before injecting commit payloads;
  the production current-event guard is not removed or stubbed. Production
  LeadSurrogate/TrailSurrogate implementations are compiled with it.
- Native NSString and attributed-string commits clear preedit and preserve
  exact child bytes. Separate leading/trailing UTF-16 callbacks produce one
  emoji; an orphan trailing surrogate produces no bytes, and intervening ordinary
  text clears a pending lead. During key-event accumulation, insertText appends
  both strings and clears preedit without sending either to the PTY early.
- Combined remote AX, selection, preedit/cancellation, insertText and ownership
  run passes (`embedded-insert-final.log`), with 44 exact committed UTF-8 bytes.
  Compiled paste-instead-of-key, lost-surrogate-pair and bypassed-accumulator
  mutants fail their specific byte/accumulator assertions, not compile errors.
  The unused-variable warning belongs only to the deliberate surrogate mutant.
  No-Option negative control still fails its rectangle assertion as expected;
  child exit is checked for each process. SwiftLint reports zero violations.
- This validates current-event presence and insertText's live downstream path,
  not full production keyDown, no-current-event rejection, interpretKeyEvents,
  OS input-method candidate selection, or pixel placement. Those remain open;
  no product behavior was changed to accommodate the fixture.

## Production keyDown orchestration to PTY (2026-10-30)

- Extended the embedded fixture to compile the actual keyDown body (renamed
  only at its test entry), keyAction, post-commit replay predicate and composing
  control filter. It uses production modifier conversion/key enumeration and
  unchanged KeyboardLayout/NSEvent sources against native Carbon and the real
  core. interpretKeyEvents is explicitly scripted at the callback boundary;
  no system input source is selected or changed by the test. The current host
  reports ABC, recorded in the test output rather than assumed.
- Exact PTY assertions cover ordinary accumulated text, entering composition,
  Enter committing text without leaking a newline, cancellation by Backspace,
  Ctrl+H cancellation with a control-text callback, Korean text followed by
  plain Left (no cursor replay), and committed text followed by Right (one CSI
  cursor sequence). Production keyDown must release its accumulator each time.
  Combined committed output is 57 bytes, not an OS IME acceptance claim.
- Compiled lost-Right-replay, leaked-composing-control and replayed-plain-Left
  mutants each fail the exact child-byte assertion. Previous paste/surrogate/
  accumulator and no-Option controls remain active. Combined remote AX and input
  run passes (`embedded-keydown-controls.log`, `embedded-keydown-final.log`). Deliberate mutant warnings are
  not production compile warnings.
- One mutation run stopped earlier at a pointer selection mismatch instead of
  its intended byte assertion; it was correctly rejected as inconclusive.
  The disposable window now ignores physical pointer events while retaining
  local synthetic dispatch; key callback delivery checks the posted fixture event's timestamp.
  A CGEvent user-data tag did not survive the NSEvent bridge; the final test
  uses the native event timestamp instead, with one-microsecond tolerance
  for AppKit timestamp quantization. The final combined run and all six
  compiled mutants pass their expected assertions; SwiftLint reports zero
  violations. This avoids treating unrelated user input as fixture input. A
  duplicate mutation substring was also tightened to its exact source line.
- Complete SurfaceView dispatch, native interpretKeyEvents, actual candidate
  UI/OS layout transitions and physical input remain unverified. No product
  changes were introduced for this test seam.

## Patch scope and build-history safety (2026-10-30)

- Rechecked PR #3 and official 1.4 sources. PATCH-SCOPE.md separates build/API
  adaptation, demonstrated native failures and distribution safety from optional
  upstream fixes and unproven warnings. No existing product changes were removed;
  the AX snapshot and search-selection bridge need separate necessity review.
- Found a concrete release-wrapper gap: a clean depth-two clone stamped build
  number 2 and reached Xcode even though its full history had three commits.
  A real local-Git/Nushell test reproduced this (`build-metadata-red.log`).
  `build.nu` now rejects shallow histories before Xcode rather than silently
  producing an undercounted Sparkle version. No network fetch is automatic.
- `build-metadata-check.py` passes clean revision/count, untracked dirty labeling,
  shallow refusal before Xcode and local full-history recovery
  (`build-metadata-green.log`). Only the external Xcode invocation is intercepted;
  the real Git and production Nushell metadata logic run unchanged.
- Actual ReleaseLocal invocation also succeeds (`scope-app-build.log`); all seven
  universal Mach-O deployment/dependency checks and strict signature validation
  pass (`scope-bundle-audit.log`). Native system-import resolution passes again
  (`scope-symbol-audit.json`), with 45 missing weak imports still requiring guards.
  These are build/static checks, not new physical input or release certification.

## Full-app command palette acceptance (2026-10-30)

- Added opt-in `app-smoke.py --palette`, using the existing isolated app and
  permission rather than extracted SwiftUI components. The actual overlay opens
  through toggle_command_palette. Cross-process AX verifies automatic focus,
  empty query on reopen, no-match filtering and replacement with New Tab.
  Pressing that row must create exactly one real tab, dismiss the palette and
  restore terminal focus. Its child must execute a PTY command; closing the tab
  must recover the original surface. Two cycles run before the ordinary smoke.
- The first two attempts failed the AXPress return-code assertion. The native
  call advertises AXPress but returns attributeUnsupported (-25205). Checking
  authoritative app state instead proves the action actually executed, creating
  the tab and its live PTY. This is not a product failure requiring a backport.
  The final harness records that code, rejects unrelated errors, never retries
  the action and requires the full resulting state instead of accepting the
  error alone. No production change or global event injection was made.
- Outcome-based run and final repeat both pass two palette cycles plus ordinary
  PTY/control/UTF-8, split/tab/window undo-redo, child expiry, quick-terminal and
  quit checks (`palette-app-outcome.log`, `palette-app-final.log`). Python syntax
  and diff whitespace checks pass. The production query, row callbacks, config
  entries and terminal creation remain unmodified. Physical keyboard submission,
  IME, other palette actions and visual correctness remain distinct gates.

## Resource retention and relocated CLI (2026-10-30)

- Added resources-check.py to audit a packaging/function-retention gate rather
  than add product workarounds. All ten generated resource-folder memberships
  match official 1.4, and all 882 bundled files match current zig-out inputs.
  This covers themes, shell integrations, completions, editor files, locale data,
  documentation and terminfo. Seven integration files (including hidden files)
  and Ghostty.sdef additionally match current source directly.
- A temporary unmodified signed bundle outside the repository, under a path
  containing spaces, discovers all 819 bundled themes through the real CLI.
  HOME/XDG_CONFIG_HOME are isolated, cwd is outside the repo, and there is no
  GHOSTTY_RESOURCES_DIR override. Six sampled themes load by name through
  validate-config; a nonexistent name fails with its diagnostic. The system's
  infocmp reads both ghostty and xterm-ghostty from that relocated bundle.
- Initial and final runs pass (`resources-check.log`,
  `resources-check-final.log`); no product/resource changes were necessary.
  This establishes current resource retention and native CLI discovery, not
  all-theme rendering, all-shell runtime integration, clean-machine trust or
  provenance/freshness of every generated input. The core must still be built
  from current source before packaging; matching stale inputs alone is not
  a production-readiness claim.

## Bounded full-app lifecycle resource measurements (2026-10-30)

- Added `app-smoke.py --lifecycle`: four batches create a real split, tab and
  standalone window, then close all three and wait for the existing five-second
  undo retention to expire. All twelve child processes exit within the unchanged
  ten-second deadline; the original terminal UUID, PID and PTY survive. No
  production changes, App Nap overrides or activity assertions were introduced.
- Two full runs pass the batch assertions and subsequent standard smoke
  (`lifecycle-app-final.log`, `lifecycle-app-repeat.log`). The repeat observes
  child expiry 5.03-5.07 seconds after the last close. The initial attempt stopped
  at a Darwin ps output-parser assumption before creating terminals; the parser
  now respects -M's fixed layout instead of assuming -o replaces its columns.
- In the first completed run, settled/idle RSS after warmup grows from 74,960 to
  79,348 KiB over the remaining three batches. Idle process CPU deltas are
  0.00-0.33% of one core over three-second intervals; settled thread counts are
  12-13. These are short host observations, not equivalence to upstream, a
  long-duration stability result or a proof of leak freedom.
- Descriptor counts rise from 21 to 24 after warmup and then stay at 24 for the
  last batch in both runs. The repeat retains lsof types/names: the three extra
  descriptors are AppKit savedState window_2.data, data.data and windows.plist
  under the existing smoke-only bundle identifier, not extra PTYs. The original
  terminal remains the only /dev/ptmx descriptor at the sampled settled points.
  The test does not clear macOS's saved-state or cache directories. JSON samples
  and per-stage descriptor inventories remain in the printed smoke directory.
- No numerical RSS/CPU limit was invented to make these measurements pass.
  They establish bounded child cleanup and provide a starting resource profile;
  sustained workload/GPU memory and an appropriate official-1.4 comparison are
  still missing for the broader performance requirement.

## Actual compositor color output (2026-10-30)

- Existing Screen Recording permission is available on the host. Added opt-in
  `app-smoke.py --pixels`: captures only the isolated process's single visible
  layer-zero window through CGWindowListCreateImage, never all windows/desktop.
  No permission request, global input or product rendering hook is used.
- The real PTY clears, prints red/green/blue background blocks plus text, then
  clears again. The first fixture counted window chrome as terminal content and
  rejected its blank screen (416 green pixels). The retained check excludes a
  symmetric ten-percent border rather than relaxing the color thresholds.
  This is a fixture correction, not evidence for a rendering workaround.
- The current run passes blank/color/blank at 1296x908: interior RGB counts are
  [0,0,0], [17873,34816,34816], [0,0,0]. Subsequent ordinary PTY, undo/redo,
  child-expiry, quick-terminal and quit smoke passes (`pixels-app-final.log`).
  It establishes compositor-visible color drawing and clearing beyond previous
  offscreen Metal/API checks. No product change was needed.
- PNGs are retained with ASCII/CJK/combining/emoji/style samples, but this agent's
  image-view tool refused image input; no visual glyph-quality acceptance is
  claimed. Numerical checks do not validate glyph shaping, exact color fidelity,
  background/custom-shader/Kitty presentation, frame pacing or other GPUs.

## Kitty image compositor transitions (2026-10-30)

- Extended --pixels to send a 16x16 RGBA Kitty image through the real PTY and
  scale its placement to 40 columns by eight rows. Captures now require red,
  blank after retransmission, green after explicit replacement placement, and
  blank after deletion. This directly exercises the app's image texture/render
  path, not only its wire response or the offscreen shader harness.
- The initial test incorrectly expected retransmission to preserve placement.
  Official 1.4 graphics_storage.zig explicitly removes all old placements on
  retransmission, and the current source matches that behavior. The blank result
  was correct; no product fix was warranted. Corrected the test sequence and
  the older wire fixture's misleading placement-retention comment.
- Final captured interior counts are [174080,0,0], [0,0,0], [0,174080,0],
  [0,0,0]. RGB text-background controls and subsequent complete standard smoke
  also pass (`pixels-kitty-final.log`). Individual captures retain indexed file
  names so the two blank states are not overwritten. No product code changed.
- Coverage remains bounded to opaque raw RGBA upload/replacement/placement/
  deletion on this host. PNG, alpha composition, animation, relative/Unicode
  placements, custom shaders, frame pacing and other GPUs are not established
  by this result. Earlier wire and offscreen evidence retains its own scope.

## Custom shader and background compositor output (2026-10-30)

- Extended the existing --pixels test rather than changing production code.
  Live config reload installs a constant-blue custom shader with animation off.
  Captured blue interior pixels must cover more than half the complete window;
  removal must restore the blank control. This tests actual shader output, not
  just successful compilation or log messages.
- A separate stage loads a generated opaque blue PNG as a stretched background,
  checks the same coverage threshold, removes it and checks blank restoration.
  Each config mutation is restored in finally; no user config, forced redraw,
  restart or test hook is used. Only the isolated window is captured.
- Shader-only and expanded shader/background runs pass (`pixels-shader.log`,
  `pixels-shader-background.log`). In the latter 1296x908 run, shader blue count
  is 753899 and background blue count is 632056; each removal returns [0,0,0].
  Existing RGB/Kitty transitions and subsequent standard smoke also pass.
- These observations close the tested static shader and opaque PNG background
  presentation gap on this host, not animation, multi-pass input sampling,
  uniform correctness, alpha blending, fit modes, frame pacing or other GPUs.
  Product code and upstream feature implementations remain unchanged.

## Combined extracted-archive acceptance (2026-10-30)

- Added `package-check.py --extended` to exercise the accumulated acceptance
  checks against one packaged/extracted artifact rather than only independent
  build-directory runs. It retains the original checksum, exact round-trip,
  dirty-release refusal, non-overwrite, optimized-Python refusal and tampered
  signature rejection checks.
- The extracted app first passes automation, OSC5522 policy, renderer wire/API
  and Inspector smoke. Resource retention/relocated CLI then passes. A second
  sequential isolated app runs palette, four-batch lifecycle and RGB/Kitty/
  shader/PNG compositor checks together, followed by standard smoke. Separate
  configs keep renderer-stress backgrounds out of the blank pixel controls.
- The complete command exits zero (`package-extended-current.log`). Original
  archive and signed source remain unchanged; test ZIP/extraction are temporary
  and explicitly NOT-FOR-RELEASE. This closes the combined artifact-runtime check
  on the current host, not Gatekeeper, notarization, physical input, arm64 or
  signed update installation. Re-signing the GUI test copy is still explicit.
- Reconciled AUTOMATION.md's stale 'currently failing' AX selection paragraph
  with the verified snapshot-era Select All log. The separate optional-patch
  classification remains: this upstream defect is not an OS-port prerequisite,
  and physical rectangular input/VoiceOver are not certified by that test.

## Launch-environment contamination control (2026-10-30)

- Auditing the combined fixture found that app-smoke inherited resource, terminfo
  and shell-startup overrides from its launching terminal. This host currently
  supplies iTerm's TERMINFO_DIRS. Even though the relocated CLI check already
  used a clean environment, the GUI fixture needed independent protection from
  accidentally consuming an installed app's resources.
- The GUI launcher now removes these overrides and DYLD injection/search paths,
  sets test-local XDG config/cache/state variables, and explicitly enables only
  the logging/Metal options required by the selected test. Its zsh probe checks
  the actual child's GHOSTTY_RESOURCES_DIR and TERMINFO point into this copied
  app, along with the requested XDG variables.
- A full system-zsh smoke run launched with deliberately nonexistent inherited
  GHOSTTY_RESOURCES_DIR, TERMINFO and BASH_ENV passes resource-path checks,
  automatic shell hooks, cwd inheritance, normal PTY/undo/child-expiry/quick
  terminal checks (`smoke-resource-isolation.log`). No product change was made.
- XDG variables are not complete filesystem isolation: Cocoa/Metal/saved state
  still use the login user's test bundle domain. Current upstream sentry.zig
  also chooses the native cache path when XDG_CACHE_HOME is nonempty; it is
  unchanged here. This general upstream behavior is recorded as a fixture
  limitation, not expanded into another OS-port bugfix. The test does not
  promise that all cache writes remain under its temporary directory.

## Embedded release-entitlement audit (2026-10-30)

- The packaging audit previously checked get-task-allow only on the main app's
  default architecture. It now examines the signed entitlements of each of the
  seven Mach-O binaries in both x86_64 and arm64, including Dock and Sparkle
  helpers. A nested or non-host debug attachment entitlement is rejected before
  packaging. Existing upstream entitlement files are unchanged.
- Current ReleaseLocal passes all fourteen entitlement inspections plus existing
  deployment/dependency and strict-signature checks. A disposable Dock plugin
  re-signed with get-task-allow is rejected specifically for that entitlement;
  its enclosing bundle first passes codesign --deep --strict, ruling out an
  unrelated broken resource seal as the cause. The original signature remains
  valid (`bundle-entitlements.log`). No installed bundle or credentials changed.
- This is a release-check coverage correction, not a discovered debug entitlement
  in the current product. It does not establish all entitlement policy, signed
  updates, Developer ID identity, notarization or clean-machine trust.

## Live AppleScript opt-out enforcement (2026-10-30)

- Added --automation-policy to exercise the upstream scripting restriction in
  the actual Monterey app, not only successful automation. Test-only config
  reload via the existing SIGUSR2 handler hides window/terminal enumeration and
  rejects new-window/new-configuration with the explicit disabled-policy -1743
  error. Input/action/close using the previous terminal ID also fail; lookup
  rejection and handler rejection are not conflated.
- Restoring the config through the same signal returns the original terminal,
  PID and PTY without extra tabs/windows. A fresh child command succeeds, proving
  the denied input did not corrupt the shell's subsequent command. The complete
  standard smoke then passes (`automation-policy.log`). No product changes,
  Shortcuts permission changes or system Automation consent changes were needed.
- This closes the tested live enable/disable policy path on this host. It does
  not prove all Apple events, stale in-process object wrappers, system consent
  behavior or Shortcuts execution, and does not alter the separate App Intents
  availability limitation on Monterey.

## Retaining terminal-detail automation without AppIntents (2026-10-30)

- Operation-level comparison found that the original AppleScript dictionary
  does not expose GetTerminalDetailsIntent's full/visible/selected text. Lack
  of AppIntents on 12 does not make these text operations impossible. Added
  three read-only terminal properties using existing in-process readers and
  the normal macos-applescript guard. No C API, cache, controller, clipboard
  access or additional system permission is introduced. The full-text reader
  uses the existing accessibility entry point rather than coupling this bridge
  to the optional snapshot representation.
- New --automation-text drives a real child PTY through 300 scrollback lines,
  distinguishes full text from visible text, reads selected Unicode including
  supplementary/combining/CJK characters, and checks selection clearing. The
  old bundle fails at dictionary parsing (`automation-text-red.log`); the
  rebuilt universal app passes (`automation-text-recovery.log`). Live policy
  checks also reject all three property reads after scripting is disabled and
  recover the same process/PTY afterwards. Standard smoke passes in that run.
- A second sequential run includes the original window/tab/split configuration
  tests as well as text/policy and standard smoke; all pass
  (`automation-text-repeat.log`).
- Initial combined testing left Escape in the shell line editor after clearing
  selection, preventing the following probe's command. The fixture now cancels
  that input with the existing send-key control modifier API; an initial wrong
  ctrl+c key-name spelling was rejected. Neither failure required a product
  input change. Earlier logs are retained rather than counted as passes.
- ReleaseLocal universal build, seven-Mach-O signature/deployment audit and
  targeted SwiftLint pass (`automation-text-build.log`,
  `automation-text-bundle.log`). The final Swift source also adds mapping-only
  documentation after that build. No arm64 runtime or Shortcuts UI claim is
  made. AUTOMATION.md now records operation-level gaps: entity selection,
  distinct permission policy and idempotent quick-terminal opening remain
  different from the upstream Intents API. The optional AX snapshot scope
  review remains independent and unresolved.

## Idempotent quick-terminal scripting operation (2026-10-30)

- Closed the next operation gap from the App Intents comparison: added `open
  quick terminal`, guarded before controller access by validateScript. It calls
  the existing QuickTerminalController.animateIn and maps its leaf surfaces to
  live ScriptTerminal references. Repeated open does not toggle visibility or
  create a second lifecycle/controller; the existing toggle binding is unchanged.
  This deliberately follows AppleScript creation semantics (live references),
  not the Intent's first-open awaited metadata/screenshot entity construction.
- The old app rejects the new command during script parsing
  (`quick-open-red.log`). After the universal ReleaseLocal build, the live probe
  verifies returned ID, three repeated opens, PID/PTY retention, enumeration of
  two quick-terminal splits, hidden-window reopening and original toggle behavior.
  Live opt-out rejects the command with the explicit -1743 policy error before
  quick-controller initialization. Full text/policy/standard smoke passes
  (`quick-open-geometry.log`).
- A separate sequential run also passes with the original configuration-record
  automation tests and live policy checks (`quick-open-repeat.log`).
- An initial test incorrectly assumed the scripting window collection includes
  the nonactivating quick panel. Replaced that assumption with WindowServer
  on-screen window counts filtered to the test PID and substantial bounds;
  show/hide must change this count by exactly one. This gathers geometry only,
  not screenshots, AX or global events. No product change was made to satisfy
  that incorrect fixture assumption (`quick-open-green.log`).
- Seven-Mach-O signature/deployment audit, dictionary command-code uniqueness,
  Python syntax, diff whitespace and targeted SwiftLint pass
  (`quick-open-bundle.log`, `quick-open-build.log`). The public-release gates
  remain open; this does not establish Shortcuts UI/entity/permission parity,
  physical keyboard acceptance or Apple Silicon runtime.

## Optional AX snapshot cost audit (2026-10-30)

- Rechecked official 1.4: accessibilitySelectedText reads only the selection
  through ghostty_surface_read_selection. The adaptation instead uses the
  full-screen snapshot cache, and that C entry point holds the renderer-state
  mutex while producing text, selected text and ranges. Thus correcting general
  AX range defects also changes the cost of selected-text-only reads. This is
  not a macOS 12 requirement or PR #3 issue.
- Added snapshot-cost-check.py to compare both C APIs in the same current
  optimized core, using a real native surface and child PTY. It retains first
  and last scrollback markers, checks identical full text, compares selected
  bytes and UTF-16 substring ranges, and verifies child exit after teardown.
  Two warmups precede eight measured reads per mode; ordering alternates.
  No product source, permissions, clipboard or global input changed this turn.
- At 12,000 lines/576,060 text bytes, initial select-all medians were 3.83 ms
  for selection-only versus 15.77 ms for snapshot (`snapshot-cost.log`). At
  30,000 lines/1,440,060 text bytes, the final two runs report:

  | Case | Existing read median | Snapshot median | Returned snapshot bytes |
  | --- | --- | --- | --- |
  | No selection, full text | 23.81 / 11.95 ms | 19.11 / 12.89 ms | 1,440,060 |
  | Select all, selection only | 11.51 / 12.29 ms | 58.05 / 47.55 ms | 2,880,136 |
  | Six-byte viewport selection | 0.0095 / 0.0088 ms | 31.20 / 22.92 ms | 1,440,082 |

  Logs: `snapshot-cost-short.log`, `snapshot-cost-repeat.log`. Raw timings and
  generated Swift sources remain in the artifact directories printed there.
  Variance is material; do not treat one timing as a stable latency guarantee.
- Returned bytes exclude allocator slack/temporary allocations and Swift copies.
  Timed calls include locking and core allocation/serialization, not result
  validation/freeing, app caching, rendering or AX transport. Snapshot supplies
  additional consistent ranges, so this is a cost-of-feature comparison, not
  equal-work optimization proof. It confirms that a short-selection cache miss
  now performs scrollback-sized work; it does not prove a visible stall or an
  upstream-binary performance regression.
- This evidence changes the patch decision: treat the large AX group as a
  separately justified improvement, not part of the minimum-cost Monterey port.
  Existing code/tests remain intact pending the scope decision; correctness
  passes alone no longer support retaining it without considering this cost.

## Selection-only automation reader correction (2026-10-30)

- Applied the preceding cost evidence at the automation boundary: made the
  existing selectedText helper available within the module and routed the
  AppleScript selected-text property and preserved App Intent call site to it.
  The helper already wraps ghostty_surface_read_selection for menus and keeps
  the original nil/empty and ownership behavior. No new cache/C API, AX range
  change or broad snapshot removal is involved. Full-text and viewport readers
  are unchanged. The App Intent path is compiler-excluded on this host; its
  modern SDK build/runtime is not claimed as tested.
- New script-text-reader-check.py compiles the exact three scripting property
  bodies against reader counters. Before this correction it fails because a
  selected-only read calls the full snapshot adapter (`script-text-reader-red.log`).
  Both optimization modes pass after correction, including disabled-policy
  no-reader access and weak-reference expiry. Compiled bypass-policy and
  full-snapshot-routing mutants fail their intended assertions
  (`script-text-reader-final.log`). This tests the accessor boundary, not a
  performance threshold or the complete Cocoa scripting runtime.
- Rebuilt the universal ReleaseLocal app and passed actual PTY Unicode
  selection/clearing, full/visible text, live opt-out/recovery and standard smoke
  including idempotent quick-terminal open (`script-text-direct-build.log`,
  `script-text-direct-app.log`). All seven Mach-O/signature checks pass
  (`script-text-direct-bundle.log`), as do targeted SwiftLint and diff whitespace.
  The large optional AX snapshot group still needs a separate scope decision;
  these changes only prevent automation from unnecessarily paying its cost.

## Current archive acceptance after automation additions (2026-10-30)

- Extended package-check.py's first extracted-app run to include the new
  terminal-text reader and live scripting-policy checks alongside existing
  configuration-record, clipboard-protocol, renderer and Inspector probes.
  Standard smoke includes the idempotent quick-terminal command. This verifies
  dictionary delivery and real dispatch after packaging, not just source lint.
- Ran package-check.py ReleaseLocal/Ghostty.app --extended against the latest
  built artifact; exit 0 (`package-automation-current.log`). Archive/extraction
  signatures, all seven Mach-O files, checksums, no-overwrite, optimized-Python
  refusal and dirty-release refusal pass. Original resources and dictionary
  match the current source; relocated CLI/theme/terminfo checks pass.
- Both sequential GUI runs pass: text/policy/renderer/Inspector/PTY checks in
  the first, palette/lifecycle/compositor checks in the second. Four lifecycle
  batches release their children; RGB/Kitty/custom-shader/PNG-background output
  and blank controls pass. Disposable sealed-resource tampering is rejected
  before package output creation. The NOT-FOR-RELEASE archive is automatically
  removed at completion; no install, publication or signing-policy change.
- Rechecked Xcode memberships: 173 app, 10 plugin, 27 unit-test and 8 UI-test
  members still match upstream rules. This is membership evidence, not a Swift
  Testing/Xcode test pass. Physical keyboard/IME/VoiceOver, arm64/macOS 12.0,
  clean-machine trust, full test-suite execution and performance/optional-patch
  decisions remain open. Archive success does not replace any of those gates.

## Preserving UI-test waits on the Monterey toolchain (2026-10-30)

- Reproduced the upstream UI-source compile failures with Xcode 14's actual
  XCTest framework and Swift overlay, without launching tests or overwriting
  the signed ReleaseLocal bundle (`ui-waits-red.log`). The first standalone
  invocation omitted XCTest's Swift-overlay include directory and was corrected
  before treating diagnostics as product/toolchain evidence.
- Replaced unsupported waitForNonExistence/key-path equality wait calls with
  two small XCTest predicate/waiter helpers in the existing shared test file.
  Assertions and original timeout values are preserved. Replaced 0.5-second
  Task.sleep(for:) calls with cancellable Task.sleep(nanoseconds: 500_000_000).
  No production code, test membership or test-skip policy changed.
- ui-wait-check.py type-checks the real palette/mouse/tab/title/window test
  sources for x86_64 and arm64 deployment 12.0. Its runtime fixture uses actual
  XCTest predicates/waiters with local element state: already satisfied,
  delayed transitions and unsatisfied deadlines. Initial testing showed the
  predicate wait may not evaluate within a 50 ms timeout even when already
  satisfied; helpers now check the immediate condition first. Both Swift
  optimization modes pass, and a compiled false-success mutant is rejected
  (`ui-wait-final.log`). This does not execute XCUIElement server interactions.
- Full UI-source type-check still fails at XCUIDevice.Appearance and system
  appearance mutation in GhosttyThemeTests (`ui-suite-remaining.log`). Tests
  remain intact; no fake success, no global theme changes or skipped tests were
  introduced. Swift Testing remains a separate blocker for the unit target.
  Membership audit, shared-helper SwiftLint and diff whitespace pass. The
  ReleaseLocal product is unchanged from the previous archive acceptance.

## Preparing physical keyboard acceptance evidence (2026-10-30)

- Added test/macos-keyboard/capture.py for a human to run inside the actual
  built terminal: bounded raw-byte recording, legacy or Kitty flags 31,
  exclusive 0600 JSONL output, timestamps/labels, protocol pop and termios
  restoration on normal exit and handled termination signals. It only opens
  its own stdin terminal; no hooks, injection, layout changes or permissions.
  Never type secrets during capture. SIGKILL/terminal loss cannot guarantee
  cleanup, and read chunks are not key-event boundaries or pass verdicts.
- capture-check.py passes private-PTY checks for control/Unicode bytes,
  timeout/SIGTERM cleanup, push/pop, private permissions, overwrite refusal and
  noninteractive refusal (`keyboard-capture-final.log`). The initial exact
  termios comparison encountered Darwin's kernel-set PENDIN after raw mode;
  the test now masks only that queued-input reprocessing flag, retaining all
  other field comparisons. No terminal settings workaround was added.
- README documents how to gather the still-missing manual evidence. No human
  key capture was run this turn and no PR #3/input correctness claim follows
  from recorder tests. The optional AX scope decision still awaits explicit
  user input; no existing implementation was removed while awaiting it.


## Approved AX separation and rebuild (2026-10-31)

- User explicitly selected option 1. Saved all tracked changes plus affected
  tests in /tmp/ghostty-ax-separation-1mf9v256 before editing. Separated only the
  optional AX experiment: include/ghostty.h, embedded.zig, Screen.zig,
  StringMap.zig and formatter.zig now match official 1.4 byte-for-byte.
  The upstream terminal-state snapshot subsystem is untouched.
- Restored the Swift String screen cache and upstream selectedRange behavior;
  selection-only helper remains shared by AX, menus and automation. Retained
  UTF-16 count/visible-range/line fixes, clock/cache compatibility, all PR #3
  input fixes and the unrelated search selection bridge.
- optional-ax/snapshot.patch and .snapshot test files preserve the experiment.
  Applied that patch only to a temporary tree and verified reconstruction of
  all seven prior product files byte-for-byte. No destructive Git reset,
  commit, installation or publication occurred. Current strict Services
  --selection diagnostic still asserts exact ranges and is expected to expose
  the inherited defect, not silently pass a weakened contract.
- Reworked embedded gesture/input checks to call the upstream text/selection
  APIs, preserving forward/reverse rectangle/contiguous selected text and all
  PTY/preedit/control/replay tests. Remote AX text/count checks and all six
  compiled input mutants pass (ax-separated-embedded.log). Correct disjoint
  selected-range assertions and snapshot ownership tests are archived, not
  claimed as current passes. Snapshot cost probe explicitly exits inapplicable.
- Universal ReleaseFast core rebuild passes 333/333; ReleaseLocal app rebuild
  succeeds (ax-separated-core.log, ax-separated-app-build.log). Targeted lib-vt
  formatter/StringMap run succeeds: aggregate 137/143 passed, six skipped,
  including dependency/feature variants (ax-separated-core-tests.log).
  Small UTF-16 checks and their three mutants pass in both optimization modes;
  cache and scripting-reader tests also pass. SwiftLint and membership audits
  pass. Full Swift Testing/physical input/other-hardware gates remain open.
- Actual app smoke passes text automation, live scripting policy, PTY/control/
  UTF-8, lifecycle and idempotent quick terminal (ax-separated-app-smoke.log).
  Seven-Mach-O signature/deployment audit passes (ax-separated-bundle.log).
  Ran the unchanged strict --selection diagnostic: it fails specifically at
  selected range length 109 versus UTF-16 text length 66, after one selection
  notification and correct selected text (ax-separated-known-range.log).
  This records the explicitly accepted upstream limitation, not a test pass
  or a new Monterey defect. Prior archive acceptance predates this binary.

## Separated-product archive acceptance (2026-10-31)

- Reran package-check.py --extended because the core and Swift reader changed,
  not merely to repeat prior passing checks. Exit 0 in ax-separated-package.log:
  round-trip signatures/content/checksums, release/overwrite/tamper refusal,
  current dictionary and resource retention, relocated themes/terminfo,
  automation/text/policy, renderer/Inspector, palette/lifecycle and compositor
  probes all pass on the newly rebuilt artifact. The temporary development
  archive was removed; nothing was installed or published.
- Inspected both app Mach-O symbol tables: the upstream text and selection
  exports exist, while both optional AX snapshot exports are absent. This
  excludes accidentally validating a stale snapshot-linked app. Source/header
  comparison and reversible archive-patch verification remain as recorded above.
- Updated release-readiness evidence to this binary. Inherited selected-range
  defects, physical input/VoiceOver, arm64/macOS 12.0 execution, full Swift
  Testing and clean-machine distribution gates are not closed by this run.

## Search fallback scope comparison (2026-10-31)

- search-state-check.py --compare-upstream-fallback passed in -Onone and -O
  (search-fallback-comparison.log). It compiles the production SearchState and
  real SwiftUI field; the only removed behavior is the selection background in
  a temporary source. All pasteboard operations use a private fixture board,
  not the user's find or general pasteboard. Product search code is unchanged.
- Both variants synchronize settled external text. The bridge selects all 11
  UTF-16 units and typing replaces them with "new"; the upstream fallback leaves
  a zero-length selection at offset 11 and appends instead. For a same-turn
  native edit/external replacement, the bridge converges editor/model/board to
  "same-turn-external"; the fallback editor retains the local edit while the
  model and board hold the external value. This is not a full-app or physical
  IME test, or proof of the same race on other OS versions.
- --same-turn-replacement --ablate also passed the nine adapted upstream test
  bodies, typing/deletion, 20 races and the rejected mutant in both optimization
  modes (search-current-race.log). It repeatedly emitted Binding<String> and
  onChange multiple-updates-per-frame warnings. Functional convergence is not
  evidence of warning-free behavior or acceptable frame pacing.
- Retain the search bridge for now for its demonstrated functionality; do not
  extend the approved AX-only separation to it or expand the port into general
  SwiftUI repairs. PR #3 addresses a distinct legacy NSEvent mutation problem.

## Remove snapshot-only cache residue (2026-10-31)

- Current-source search confirmed CachedValue.invalidate has no remaining
  production caller after AX separation. Removed that method from the active
  product and archived its tests as optional-ax/cache-check.swift.snapshot.
  Kept continuous-clock expiry, stale-task generation guards, concurrent reuse
  and idle/deallocation payload release; these serve the retained Monterey cache.
- Regenerated optional-ax/snapshot.patch against the smaller product. Applying
  it in a temporary tree reconstructs all seven prior experiment product files
  byte-for-byte, including the method and its caller. Backup path is recorded in
  /tmp/ghostty-monterey/cache-scope-backup-path. The five core/header files still
  match official 1.4 exactly. No additional AX feature was removed.
- Cache tests pass in -Onone/-O (cache-scope-check.log); scripting readers and
  their policy/routing mutants pass (cache-scope-readers.log). All project
  memberships, git diff --check and targeted strict SwiftLint pass; SwiftLint
  emits its existing deprecated-path/config-key warnings.
- Rebuilt the universal ReleaseLocal app through macos/build.nu successfully
  (cache-scope-app-build.log). Seven-Mach-O deployment/signature audit passes
  (cache-scope-bundle.log). Actual isolated-app PTY, lifecycle, quick terminal,
  Unicode selection/scrollback/viewport and live scripting opt-out/re-enable
  checks pass (cache-scope-smoke.log). The session was unlocked at preflight.
- No core rebuild was needed because only Swift product code changed. The
  broad archive suite was not repeated for this dead-method removal; its prior
  results do not certify the newest binary. No commit, install or publication.

## Bounded real-PTY throughput observations (2026-10-31)

- Added app-smoke --throughput and throughput-app-check.py; no product code or
  runtime configuration optimization changed. The unlocked-session fixture uses
  the current ReleaseLocal app, a private shell PTY and nonblocking bounded
  writes. Cursor-position replies fence parser consumption before/after each
  workload, not renderer/GPU completion. JSON records executable identity,
  terminal dimensions and sampled process resources with each run.
- Initial 4 MiB bursts completed in 30-130 ms, too short for useful resource
  sampling (throughput-current.log). Replaced single bursts with buffer reuse
  for two seconds per workload, capped at 128 buffers and a 25-second deadline.
  The final three rounds of ASCII/ANSI/Unicode sent 1,598,046,032 bytes in total;
  all nine parser fences and subsequent ordinary app-smoke checks passed
  (throughput-sustained.log). Geometry was 80x24 on Intel macOS 12.7.6.
- Observed MiB/s ranges and medians: ASCII 123.67-138.93 (126.92), ANSI
  86.81-92.94 (91.79), Unicode 30.23-30.74 (30.73). Maximum sampled app RSS
  was 151.85 MiB. These are host observations, not a passing performance budget,
  measured peak allocation, GPU memory usage or an official-1.4 comparison.
- The workloads exercise repeated text/attributes/scrollback under live PTY
  pressure. They do not establish frame pacing, rendered-content correctness,
  long-running resource stability, realistic workload coverage, other GPUs or
  arm64 runtime. No release gate is closed merely by these throughput numbers.
- A temporary private-PTY harness exercises the exact generated child source:
  absent and malformed DSR replies both fail before sending workload bytes and
  restore terminal settings (throughput-fence-refusal.log). The first harness
  attempt queried a Darwin PTY after its session leader exited and received
  ENOTTY; keeping the test session leader alive permits the restoration check.
  Only the kernel PENDIN bit is masked in that comparison. Python syntax and
  git diff --check pass. No product rebuild or new archive was necessary.

## Original Swift test runner investigation (2026-10-31)

- Investigated the remaining original-suite gap rather than adding another
  assertion adapter. Installed tools remain Xcode 14.1/Swift 5.7.1; no extra
  user/system toolchain is present. All 27 unit sources remain in the project.
- Pinned upstream Swift Testing manifests show macOS 10.15 deployment support
  with Swift tools 6.0 (Swift 6.0 release) or 5.9 (Testing 0.5.1). The framework
  is not inherently unavailable at Monterey runtime; compiler/macro/runner
  compatibility must be evaluated separately. Current Swift 5.7 is insufficient.
- Downloaded the official Swift 6.0.3 package to /tmp and inspected it without
  installing or executing scripts/binaries. Its installer XML permits 10.11,
  but swift-frontend and swift-package each declare minimum macOS 13.0 in both
  architectures. Thus this release is not a supported drop-in compiler upgrade
  for this host. Full-package signature validation passes for Swift Open Source
  V9AUD2URP3 with notarization trust (swift603-signature.log); metadata evidence
  is in swift603-minimum.log and TEST-TOOLCHAIN.md.
- An older macro-capable compiler/Testing pair is still unverified, not ruled
  out by the Swift 6.0.3 result. External test execution or a reviewed XCTest
  migration remain alternatives. No unsupported minimum-version patch, system
  library change, dependency addition, test skip or product feature removal was
  made. No full-suite pass is claimed; UI appearance APIs are a separate gap.

## Native Swift Testing runner on Monterey (2026-10-31)

- Followed up on older compilers with official signed packages. Swift 5.9.2
  compiler/SwiftPM minima permit Monterey, but Testing 0.5.1's own guide says
  Swift 5.9 and earlier are unsupported despite its manifest tools version.
  This corrects the manifest-only candidate assessment in the preceding entry.
- Swift 5.10.1's compiler and SwiftPM minima also permit Monterey. The package
  passed Swift Open Source signature/notarization checks and was extracted only
  into /tmp/ghostty-monterey/swift5101.xctoolchain, without installer scripts or
  changing xcode-select/default Swift. Its compiler launches successfully here.
- A disposable Swift package uses Testing 0.6.0's documented XCTestScaffold and
  unchanged copies of CommandLineOpenFileFilter and its original tests. Real
  macro expansion, discovery and runner execution succeed: five Testing tests,
  hosted by one XCTest, all pass (testing-native-probe.log). Testing and resolved
  SwiftSyntax revisions are pinned in TEST-TOOLCHAIN.md and Package.resolved.
- Negating one expectation only in the temporary test copy produces a source-
  located expectation failure, propagated XCTest failure and exit 1
  (testing-native-red.log). This rejects a discovery/zero-test false success.
  The original test source was restored afterward. No product/test source or
  project dependency was altered. Full app-linked test integration and UI SDK
  gaps remain; this result establishes a viable real-runner seam, not a complete
  suite pass or a reason to expand the macOS runtime support scope.

## Swift 5.10 full-app integration boundary (2026-10-31)

- Built through a temporary macos/build.nu copy with explicit SWIFT_EXEC and
  separate output directories. Unchanged app source triggers Swift 5.10.1's
  actor-isolation SIL assertion in AppDelegate.terminate. Existing Swift 5.7
  ReleaseLocal app is unaffected; this is not a product runtime regression.
- In an isolated source copy, tested SDK-13 fallback routing, explicit MainActor
  termination/review closures and an explicit TimelineView closure return. An
  explicit capture list alone does not resolve the compiler assertion. With
  the five-file candidate the actual x86_64 Debug app builds and +version runs
  (swift510-app-return.log, swift510-app-version.log). No candidate change was
  promoted to the active product and no full GUI acceptance is claimed.
- All 27 original unit sources were then submitted to the real compiler against
  that Ghostty module and Testing's macro plugin. The compiler crashes with
  signal 11 at UpdateStateTests.testIsHidden's closure-containing parameterized
  arguments (swift510-original-tests-typecheck.log). This is an integration
  obstacle beyond the earlier five-test success, not an empty passing suite.
- TEST-TOOLCHAIN.md records commands' evidence, temporary paths and corrected
  fixture mistakes (reused object-root source lists, missing resource links,
  XCTest search paths and macro executable name). No test exclusions, project
  dependency changes, global compiler selection or product rebuild occurred.
  The next meaningful step is a minimized compiler/macro reproducer, not more
  unrelated compatibility tests or a wholesale XCTest rewrite.

## Parameterized macro diagnosis and native update tests (2026-10-31)

- Reduced the signal-11 failure to a five-line Testing-only source with
  @Test(arguments: [{}]); no Ghostty, Sparkle or AppKit implementation is needed.
  A tuple containing a closure also crashes, while named static arguments
  type-check. Logs: macro-closure.log, macro-tuple.log, macro-named.log.
- In temporary UpdateStateTests, moved the original two arrays into computed
  properties, preserving all seven rows, fresh construction and assertions.
  The actual Testing 0.6.0 runner executes unchanged production UpdateViewModel
  with real Sparkle: 38 update/state/release-notes tests pass. Including the
  preceding command-line suite and one two-case closure diagnostic, the reported
  total is 44 tests (swift510-update-native.log). This is not 44 distinct update
  tests or an app-hosted full-suite result.
- Changed only one temporary argument row's expectation: the named test reports
  the exact failing idle case, XCTest fails and process exits 1. Restored source
  passes again (swift510-update-red.log, swift510-update-restored.log). No active
  repository assertion, test list or product file changed.
- All-source type-check advances past the compiler crash, then exposes older
  Swift syntax, URL API, main-actor and old Testing trait-signature constraints.
  Candidate fixes remain in /tmp/ghostty-swift510-app-x8fffd_v/unit-tests-candidate
  and swift510-tests-candidate.patch. An initial mechanical URL replacement
  retained an invalid directoryHint label; it was corrected to isDirectory in
  the fixture, not counted as a product bug.
- The five CoreTransferable-specific tests cannot run against that API on 12.
  A temporary availability annotation permits further compile inventory only;
  it is not accepted coverage. Integration must retain those tests for their
  applicable API and cover the production Monterey pasteboard equivalent with
  the real runner. No complete suite pass is claimed or release gate closed.

## Real app-object unit bundle on Monterey (2026-10-31)

- All 27 temporary unit sources compile with real Testing macros against the
  candidate Ghostty module. Seven files contain compatibility-only changes;
  the other 20 are unchanged. Actual compiled app objects (excluding main.o)
  are relinked into libGhosttyProbe.dylib, not replaced by stand-in app classes.
- A standalone XCTestScaffold host creates NSApplication.shared and calls
  ghostty_init. Passing the entire xctest argv initially polluted ConfigTests
  with the bundle path; argc 1 removes only harness arguments and fixes that
  failure without changing product config parsing or test assertions.
- Suite-level availability did not safely gate implicit CoreTransferable test
  discovery: execution ended without a final summary. Per-method availability
  plus annotations on the two helper types produces five explicit runtime skips.
  The suite-level approach is superseded, not accepted as a passing run.
- The corrected bundle exits 0: 283 named tests pass, five unavailable API tests
  are skipped, and one benchmark remains disabled by upstream. Testing's reported
  289 includes skips, confirmed in its HumanReadableOutputRecorder source.
  First success: /tmp/ghostty-native-suite-y0ctnlqf/run.log; compiler evidence:
  swift510-native-bundle-availability.log. TEST-TOOLCHAIN.md records the commands.
- This is an x86_64 Debug candidate with seven test/five app-file workarounds,
  not the active ReleaseLocal app, normal app startup, or full Xcode UI action.
  Native Monterey transfer coverage and reproducible integration remain open.
  No candidate source/dependency or global toolchain change was promoted.
- Negated one temporary requiresExecuteFlag expectation and rebuilt the complete
  bundle: its exact test/line fails, the host XCTest fails, and exit status is 1.
  Restoring the source and rebuilding returns to exit 0 with 283 named passes
  and six skips. Logs: swift510-native-suite-red.log and
  swift510-native-suite-restored.log. Regenerated the seven-file candidate patch
  after restoration; active repository tests and assertions remain unchanged.

## Real SurfaceView transport and lifetime test (2026-10-31)

- Added native-suite/MontereySurfaceTransferTests.swift as a real Testing fixture
  against the compiled application module, not a SurfaceView stand-in. It creates
  an isolated real App/surface, waits for /usr/bin/true to exit, checks the exact
  UUID bytes/type on a unique pasteboard, releases the view and checks weak
  teardown, then reads the payload. Async NSItemProvider round trips cover
  0/15/16/17-byte payloads and the actual UUID decoder.
- Bare Xcode xctest aborts at SurfaceView's existing notification cleanup because
  its main process lacks an application bundle proxy. A private .app wrapping
  the same xctest executable resolves the failure with the exact same compiled
  test bundle. No product cleanup was removed, view leaked or system file changed.
- Full candidate run now has 284 named passes and six skips (reported total 290).
  A negative control changing one expected UUID byte fails both byte comparisons
  and exits 1; restoring and rebuilding the full bundle exits 0. Logs:
  swift510-native-transfer-{host-failure,pass,red,restored}.log.
- This is native transport/lifetime coverage, not physical drag or SwiftUI
  DropDelegate/source-lookup/split-mutation acceptance. The test is not yet wired
  into the project, and the host does not run normal Ghostty startup. The current
  release app and original tests remain unchanged; no release gate is closed.
- After lint-only formatting, compiled the repository fixture directly and ran
  its targeted bundle: one test passes, exit 0 (swift510-native-transfer-repo.log).
  Strict SwiftLint passes with the existing config-key warning. The latest
  temporary bundle contains this single test; the earlier restored log records
  the full 284-pass/six-skip run, not the later targeted bundle.

## Repository-owned candidate test runner (2026-10-31)

- Added native-suite/run.py, NativeScaffolding.swift and the tested seven-file
  compatibility patch. The entry point copies all 27 original unit sources,
  patches copies only, includes the native surface fixture, and builds/runs a
  new private XCTest app host. It neither edits product/original test files nor
  changes system toolchains, permissions or the existing release app.
- Full entry-point run passes: 284 named tests and the six explicit skips;
  /tmp/ghostty-monterey/native-entry-all-03 contains compiler/run logs, commands,
  input hashes, test artifacts and result.json. It does not reuse a precompiled
  test bundle or the manually patched temporary test-source directory.
- Corrected two runner-only setup errors before the pass: absolute patch paths
  traversed /tmp's symlink, and resolving swiftc changed the multicall driver's
  argv[0]. Failed attempts are retained as -01/-02, not counted as successes.
- Result acceptance requires the expected count, exact unavailable-test names,
  surface-test discovery, no recorded issue, a final Testing summary and exit 0.
  Nine fast negative/positive parser checks pass, as does validation against the
  earlier real full/targeted logs. These checks do not replace runtime tests.
- Clean-checkout app-object/Testing bootstrap and project/UI integration remain
  open. The supplied app objects still contain the five temporary compiler/SDK
  workarounds; hashes identify consumed inputs but do not prove source-to-object
  provenance. No release-readiness claim follows from this runner integration.
- Hardened entry point also passes --suite transfer (one test, no skips), with
  five known candidate source differences recorded in inputs.json under
  native-entry-transfer-01. Full and targeted bundles have separate output
  paths. Checked the full output retains all 27 files with exactly seven patched
  copies, and the final parser accepts its actual 284-pass/six-skip log.

## Fresh Swift candidate app build (2026-10-31)

- Added native-suite/build-candidate.py and swift510-app.patch to reproduce the
  candidate application-object prerequisite from current source copies through
  macos/build.nu. Outputs/objects are isolated; the existing universal Zig archive
  and resource tree are inputs, not silently claimed as freshly rebuilt.
- Replaced the experimental compiler >=6 guard in the candidate's three SDK-14
  expressions with an explicit test-only SDK13 condition. Builder verifies SDK
  13.x first; compiler logs confirm DEBUG and DOCK_TILE_PLUGIN definitions are
  preserved. MainActor/TimelineView compiler workarounds remain candidate-only.
- Fresh x86_64 Debug build and +version pass in rebuilt-candidate-01 under
  /tmp/ghostty-monterey. The actual app link command produces the test library
  with 162 app objects, excluding exactly main.o. Input/output hashes and commands
  are captured; the actual source inventory has the expected five differences.
- Factored link extraction matches the successful command exactly; eleven fast
  verifier/link tests pass, including absent/duplicate main.o rejection. This is
  not a full GUI acceptance run or clean core/Testing dependency bootstrap, and
  no candidate product edits were promoted to the active source/release app.
- Full runner against the freshly rebuilt objects passes: 284 named tests,
  six exact skips, exit 0 (rebuilt-candidate-tests-01). Both Xcode SwiftFileList
  files reference only the new copied sources. This proves the revised test-only
  SDK13 guard builds and runs for the unit/native-transport scope, not normal
  quit dialogs, physical input/drag or ARM runtime acceptance.

## Rebuilt Testing/Syntax dependency chain (2026-10-31)

- Added native-suite/build-testing.py and a minimal package with exact Testing
  and SwiftSyntax revisions. It builds the library/plugin from source in a new
  output directory without the old disposable app fixture or compiled objects.
- Initial remote refresh failed with GitHub connection timeouts; after verified
  process termination, --skip-update used both existing pinned source commits.
  New checkout/object build completes in 244.53 seconds (rebuilt-testing-02),
  recording 75 artifact hashes and verified clean dependency checkout HEADs.
  The failed rebuilt-testing-01 log remains distinct from that success.
- SwiftPM emits an unused-direct-dependency warning for the explicit transitive
  SwiftSyntax pin. Its sources are compiled through Testing's macro dependency;
  no warning-free build is claimed. The compile-only macro probe is not a runtime
  test result. Package source hashes remain unchanged throughout the build.
- Existing-output/invalid-job refusal probes, eleven runner/link checks, Python
  parsing, SwiftLint and whitespace checks pass. run.py additionally verifies
  dependency checkout HEAD/cleanliness before consumption. No release product,
  original test source or system compiler selection changed.
- Recompiled and ran the complete unit/native-transport bundle against both the
  rebuilt app and rebuilt Testing objects: 284 named passes, six exact skips,
  exit 0 in rebuilt-all-inputs-tests-01. Commands/manifests contain no dependency
  on the earlier disposable package's compiled artifacts. The existing Zig
  core/resource inputs and physical/GUI release gates remain unverified here.

## Candidate MainActor termination dialogs (2026-10-31)

- Added TerminationProbe.swift and termination-check.py, linked against actual
  rebuilt candidate app objects. It runs real AppDelegate termination/review and
  BaseTerminalController async sheets, pressing only private native buttons.
- No-window, single cancel/accept, multi cancel/terminate, review-cancel and
  review-all assertions pass. Review cancellation preserves windows; accepting
  both sheets closes each exactly once. The reply boundary asserts main-thread
  execution and records the result without quitting the host.
- The first harness left confirmation predicates true on closed windows retained
  by AppKit, entering an unexpected modal loop. Sampling identified that state;
  clearing fixture predicates and using a main-run-loop modal/default timer fixes
  it without product changes. Final compilation has no diagnostics; strict lint
  passes with the existing configuration-key warning.
- termination-native-green-02 passes exit 0; termination-native-red-02 reverses
  one expected reply, fails that exact assertion and exits 1. Probe processes
  have exited. Native dialogs may briefly appear, but no global input, user shell,
  clipboard or permission change occurs. Configuration/defaults are isolated.
- This is a deliberate seam: empty trees and a supplied confirmation predicate,
  recorded NSApplication replies, direct terminate() invocation. It does not
  certify child termination, update/logout policy or full app launch/quit. The
  candidate patches remain separate from the active ReleaseLocal product.

## Real terminal child quit-policy seam (2026-10-31)

- Added TerminationChildProbe.swift and --real-child to termination-check.py.
  Uses actual AppDelegate.applicationShouldTerminate, BaseTerminalController,
  SurfaceView and PTY with a bounded directly launched child. Confirmation
  predicates now come from the real core/config, not an overridden controller.
- Native cancel/accept sheet responses pass; cancellation preserves the child.
  With the final app reply still intercepted, explicit window/controller release
  clears both weak references and reaps the child; afterward app confirmation
  clears and quit returns terminateNow. No user shell/global input is used.
- termination-child-green-01 exits 0 with no compiler diagnostics; a reversed
  reply expectation fails exactly and exits 1 in termination-child-red-01. Child
  disappearance is checked after both runs. The six-scenario native-dialog mode
  still passes in termination-native-regression-03. Lint and eleven fast checks
  pass; product sources and the active release app are unchanged.
- This narrows the previous empty-tree seam but still does not call the real
  final NSApplication quit reply, test updater/logout shortcuts or prove
  multi-surface/process-wide shutdown. Those limits remain explicit.
- Separately ran app-smoke.py --automation-text --automation-policy on a private
  copy of the actual fresh Debug app, not the library probe. Startup, PTY/input,
  native terminal/window operations and undo/redo/TTL, quick-terminal idempotence,
  text readers and live scripting policy all pass, then the process quits with
  exit 0. Log: rebuilt-candidate-app-smoke.log; launch.log is empty in
  /tmp/ghostty-monterey-smoke-totk7brr. This smoke config disables quit confirmation;
  it is normal lifecycle coverage but not end-to-end confirmed termination.

## Actual application confirmed quit (2026-10-31)

- Added quit-app-check.py and quit-app-client.swift. Unlike the preceding probes,
  these run the unmodified real app lifecycle in a private resigned bundle and
  do not override NSApplication replies or call internal methods. A bounded child
  runs directly in its PTY and writes atomic heartbeats; config/defaults are
  isolated, clipboard/notifications disabled, and existing AX permission is
  required without a prompt. Only app-local menu/button AX actions are sent.
- Both the current universal ReleaseLocal app and the rebuilt x86_64 Debug
  candidate pass: Quit shows confirmation while child/app remain alive, Cancel
  removes the sheet and the same child produces fresh heartbeats, then a second
  Quit/Terminate exits the application with status 0 and the child disappears.
  Logs: confirmed-quit-release-final.log and confirmed-quit-candidate-final.log.
  Their private output directories contain action logs and source-binary hashes.
- Initial release tests failed on the AX return code, not on observed cancellation:
  AXPress returned attributeUnsupported (-25205), despite exposing AXPress on an
  enabled button and dismissing the sheet. A diagnostic post-action query proved
  the dismissal. The client now records this code and requires actual post-state:
  sheet gone plus fresh child heartbeat for Cancel; exit 0 plus absent child for
  Terminate. Quit menu invocation still requires success. The Debug candidate
  returns AX success for all actions. No OS-exclusive/product-bug claim follows.
- Negative control omits the Cancel action while returning synthetic success;
  the exact "Quit sheet survived cancellation" assertion fails, not a compile
  error or timeout of the whole harness (confirmed-quit-negative-cancel.log).
  Cleanup completes and its child is absent too. Final positive runs repeat after
  this negative control; no source/product behavior is changed to make them pass.
- Strict client lint passes with the existing config-key warning; Python syntax
  and git whitespace checks pass. This closes the earlier single-child confirmed-
  quit evidence gap for these binaries on Intel 12.7.6. It does not cover physical
  button input, multiple windows/children, update/logout bypasses, arm64, or 12.0,
  and does not authorize publishing the dirty/ad-hoc artifact.

## Two-window confirmed quit in actual apps (2026-10-31)

- Extended quit-app-check.py with --multi review/direct and per-process atomic
  heartbeats. A target-local New Window menu action creates a second real window
  with an independent directly launched child/PTY; no product callbacks or
  confirmation predicates are replaced.
- Both current ReleaseLocal and rebuilt Debug candidate pass initial modal
  cancellation with both children alive, cancellation of the first reviewed
  sheet with both heartbeats advancing, and sequential acceptance of both
  reviewed sheets. After the first accepted sheet there is exactly one window
  and the app remains alive; final acceptance exits 0 and both children vanish.
  Both binaries also pass Cancel followed by direct Terminate Processes.
- Logs: confirmed-quit-{release,candidate}-multi-{review,direct}.log. The omitted
  reviewed-Cancel negative control fails exactly at "Quit sheet survived
  cancellation" in confirmed-quit-multi-review-red.log; cleanup reaps both children.
  The single-window regression and restored review run also pass afterward.
- This supplies actual multi-window behavior evidence for the candidate's
  reviewWindows MainActor closure, rather than inferring it from unit/source
  checks. The observed ReleaseLocal AX -25205 after successful sheet actions
  remains explicitly logged and validated through post-state/process assertions.
  No product edit or new system-support obligation is introduced.
- Tightened the sequential-review check to require a fresh live child heartbeat
  while the second confirmation is pending. Both binaries pass again in
  confirmed-quit-multi-review-live.log and confirmed-quit-candidate-review-live.log.
  Final logs are empty at the app side, child PIDs are absent afterward, and
  strict client lint/Python syntax/git whitespace checks pass.

## Fresh universal core reconstruction (2026-10-31)

- native-suite/build-core.py copies the current Git source inventory into an
  isolated snapshot and uses new local/global compiled caches. Only Zig package
  sources are reused. The active framework and ReleaseLocal app are not replaced.
- rebuilt-core-01 failed because Zig 0.17 rejects --global-cache-dir at the build
  command level. The builder now sets ZIG_GLOBAL_CACHE_DIR instead. A separate
  fresh rebuilt-core-02 succeeds: 333/333 build steps, 6068 unchanged snapshot
  files, and 925 hashed artifact files; lipo reports x86_64 and arm64.
- The new universal archive SHA256 is
  60fbfaba9418c1ee26fe41dbadd4e866442b30037139afde8b32d48f8213f98d.
  The existing worktree archive and app hashes remain c12dc891... and 767e290f...
  respectively. Inputs, command, full build log and results are recorded under
  /tmp/ghostty-monterey/rebuilt-core-02.
- Metal emits the inherited logical-op-parentheses warning and Zig prints a
  "failed command" line alongside it, but the overall build exits 0 and all steps
  succeed. Do not infer a product failure or change shader logic from that line.
- The snapshot uses explicit 1.4.0-dev.monterey-probe identity, not release
  metadata. This proves reconstruction without old compiled core objects, not
  a clean tagged release, arm64 execution, or test success against this new core.
  The candidate builder accepts --core-root for that next validation and hashes
  all consumed framework/resource files. Its twelve fast verifier tests pass.

## Rebuilt core through candidate tests and app startup (2026-11-01)

- rebuilt-fresh-core-candidate-03 consumes rebuilt-core-02, not the active
  framework/resources, and builds new Swift app objects. Initial remote Sparkle
  resolution failed; a second skip-updates attempt still needed a clone and was
  explicitly terminated. The successful build copies a clean pinned Sparkle
  SourcePackages cache, retaining its upstream binary artifact and hashing all
  120 artifact files. See TEST-TOOLCHAIN.md for provenance and the manifest flag
  reporting correction; neither failed attempt is counted as passing evidence.
- New Debug app SHA256:
  a2c506cf3d0c663173d5b0373a74bf5669c9695bbfea5ae0e0afc26b82d28566.
  +version reports the explicit development core identity. The real-app object
  library retains 162 objects excluding main.o. Full native runner output
  rebuilt-fresh-core-tests-01 passes 284 named tests and the same six skips.
- Actual app-smoke with automation-text/policy passes against a private copy of
  this new app: startup, PTY/control/UTF-8, split/tab/window undo/redo and expiry,
  quick terminal, scripted readers and live scripting opt-out/re-enable.
  rebuilt-fresh-core-smoke.log records artifacts in
  /tmp/ghostty-monterey-smoke-9f1a6706; its app launch log is empty.
- Sequential quit-app-check --multi review also passes with two real live PTYs,
  cancel/review sequencing and final app exit 0/child disappearance. Evidence:
  rebuilt-fresh-core-quit.log, /tmp/ghostty-confirmed-quit-y3y33azw.
- The active ReleaseLocal app and universal framework remain untouched. This
  closes old compiled-core reuse in the candidate validation chain, not immutable
  release provenance, full Xcode UI tests, physical input/IME, arm64 execution or
  publisher trust. No unrelated product fix or newer-OS obligation is added.

## Xcode unit-target build integration (2026-11-01)

- Added native-suite/build-xcode-unit.py: an isolated project copy consumes the
  rebuilt candidate/core and pinned Testing objects, retains all 27 original
  unit source memberships, and adds the two already-tested native fixtures.
  No product project/test source or system compiler selection changes.
- First build fails in Xcode 14's integrated Swift driver: it treats the macro
  plugin argument as an unexpected input. Forwarding the plugin option and its
  operand via -Xfrontend fixes this specific build failure. Standalone swiftc's
  existing runner remains unchanged.
- xcode-unit-build-02 builds the actual app dependency and GhosttyTests bundle
  successfully. Bundle SHA256:
  f241ce4226136e8e98e505a56a7f73b45ec60bed067ccd70f738c2f12077fce1.
  Xcode's generated SwiftFileList contains exactly 29 expected sources; the
  resulting binary contains the NativeTests XCTest scaffold class. Existing
  actor-conformance/unused-value warnings remain; this is not warning-free.
- This closes compilation through Xcode's real target graph, not test discovery
  or app-hosted execution. No tests ran in this new build, and the earlier 284
  passes belong to the separate app-object runner. The scaffold must avoid
  duplicate core initialization before hosted execution; UI appearance APIs
  and the full test action remain unresolved. Active project membership check
  still reports 173 app / 10 plugin / 27 unit / 8 UI sources.

## Xcode app-hosted unit execution (2026-11-01)

- build-xcode-unit.py --hosted-test now runs the complete unit target through
  Xcode's real Ghostty app host in a copied scheme/project. Main initializes the
  core; the scaffold checks AppDelegate/core availability instead of calling
  ghostty_init twice. Host config/defaults/state and bundle identity are private;
  no initial terminal or user shell is launched. UI tests are not executed.
- xcode-hosted-unit-01 exposed a preparation-script missing Release setting;
  no build ran. xcode-hosted-unit-02 built and discovered NativeTests.testAll,
  then Xcode's Main Thread Checker stopped SplitTreeTests when MockView created
  NSView on a background executor. This is a test-fixture scheduling defect,
  not PR #3 or demonstrated product regression. The candidate-only hosted patch
  marks that suite @MainActor; no assertions or checker are disabled.
- xcode-hosted-unit-03 succeeds: 284 named Testing passes, the same six skips,
  ** TEST SUCCEEDED ** and one successful XCTest scaffold in Tests.xcresult.
  Xcode 14 does not represent these as 284 independently selectable test cases.
  Compiler warnings remain (34 xcresult warnings); real startup also logs
  notification authorization denial for the private bundle and test fixtures
  log expected invalid-path/config diagnostics. This is not a warning-free run.
- An exact surface-byte assertion was negated only in the copied test source:
  negative.log / Negative.xcresult fail that assertion, exit 65. After restoration,
  restored.log / Restored.xcresult pass the full 284/six inventory again. All
  recorded source/object inputs match their original hashes after restoration;
  no private test host remains. The twelve verifier tests and whitespace check
  pass. Standalone and hosted scaffold modes remain explicitly distinct.
- This closes actual Xcode unit discovery/execution for the experimental
  candidate. It does not change the supported product build/test command, solve
  the UI appearance API gap, or prove physical input/IME/arm64/release trust.

## Single-command Monterey unit workflow (2026-11-01)

- Added macos/test-monterey.py as the documented entry point for the existing
  isolated Xcode unit path. It accepts explicit compiler/core/Sparkle inputs,
  rebuilds pinned Testing dependencies by default, prepares current app sources,
  then runs the Xcode-hosted suite with stage logs and an aggregate verdict.
  --testing-package makes reuse explicit instead of depending on scratch paths.
- build-candidate.py --prepare-only avoids compiling an intermediate app/object
  library: Xcode builds the app and unit target once. Candidate-only adaptations
  remain visible in the isolated inputs, not silently applied to product files.
- integrated-unit-01 passes with explicitly reused Testing objects. The default
  rebuild path integrated-unit-02 also passes: fresh dependency build completes
  in 243.92 seconds, then Xcode reports 284 named passes/six skips and one
  successful scaffold in xcresult. Both aggregate result.json files accept the
  actual nested test results. No intermediate candidate-build directory exists.
- Seventeen fast verifier/orchestration/refusal tests pass, including refusal of
  existing/worktree output and missing prerequisites. Active project membership
  remains 173 app / 10 plugin / 27 unit / 8 UI sources; whitespace checks pass.
- The default build.nu action and release toolchain are unchanged. This is a
  reproducible explicit unit workflow for Intel Monterey, not support for UI
  appearance APIs, per-case Xcode discovery, all architectures, or public release.

## Current ReleaseLocal archive acceptance (2026-11-01)

- Closed the explicitly outstanding archive-evidence gap after the unused AX
  cache-method cleanup. Ran package-check.py --extended against the actual
  current ReleaseLocal binary, not a Swift 5.10 Debug candidate. The app hash
  remains 767e290f7c578a9fa487cc33a6062bd78a07a564b0de5600e736782198227170.
- Packaging/extraction preserves files, executable modes and framework links;
  all seven universal Mach-O files and strict signatures pass. Existing-output,
  optimized-Python, dirty release-metadata and tampered-resource refusals pass.
- First sequential extracted-app suite passes scripting configuration/text/live
  policy, real PTYs, OSC 5522 protocol checks, renderer stress/inspector and the
  normal split/tab/window undo/expiry/quick-terminal checks. Second suite passes
  command-palette interactions, three lifecycle batches and compositor RGB,
  Kitty-image upload/replacement/deletion, custom shader and PNG background
  checks with blank controls. These remain bounded tests, not physical-input or
  long-duration performance certification.
- Resource checks confirm ten official resource folders / 882 exact file hashes,
  seven current shell-integration scripts and the scripting dictionary; relocated
  CLI discovery finds all 819 bundled themes without a resource override.
- Evidence: /tmp/ghostty-monterey/current-release-package-20261101.log and .json;
  smoke artifacts /tmp/ghostty-monterey-smoke-def7d3jg and -raf2ug09. The temporary
  NOT-FOR-RELEASE archive/extraction is removed after completion. The original
  app is unchanged; no public artifact, signing identity or release is created.
  Dirty source, clean-machine trust, physical input and arm64/12.0 runtime gates
  remain open. No unrelated product patch was added.

## Real controller split-move seam (2026-11-01)

- Extended the existing native surface fixture beyond transport bytes to actual
  BaseTerminalController.performSplitAction with real surfaces and two private
  unordered NSWindows. All four zones traverse both cross-window and same-window
  branches; assertions check exact leaf order/direction, empty original tree,
  ownership migration and unchanged core-surface pointer. Invalid destinations
  preserve the trees and source ownership on both branches.
- controller-drop-transfer-02 passes the targeted native run, and the complete
  Xcode-hosted controller-drop-hosted-01 entry passes 284 named tests/six skips.
  No new test name or skip is added: these checks extend the surface fixture.
  The initial attempt was only a compile error from comparing whole SplitTree
  values; assertions now compare their root/zoomed state instead.
- Reversing expected source/destination order exposed a failure-reporting crash
  when Testing reflected the actual NSView-backed tree values. This is not a
  valid negative-control pass. Computing comparison booleans before #expect
  avoids that reflection; the same reversed-order control now fails exact
  leftMatches/rightMatches assertions with exit 1 (controller-drop-negative-01,
  build-bool.log/run-bool.log). Original tree operations/assertions remain intact.
- Children run /usr/bin/true and exit before moves. This closes a controller
  mutation/rollback seam only: no live-PTY continuity, source UUID lookup,
  DropInfo dispatch, gesture hit-testing, undo/redo or physical drag claim.
  Product code is unchanged; strict fixture lint passes with the known old
  SwiftLint configuration-key warning.
- Final boolean-assertion source passes both controller-drop-transfer-final and
  the hosted rerun (controller-drop-hosted-01/xcode/final.log, Final.xcresult,
  final-result.json). The hosted rerun updates only its copied fixture; its
  original inputs/result manifest describes the earlier pre-boolean build.
  Seventeen fast runner checks and tracked whitespace validation pass.

## Live PTY continuity through controller moves (2026-11-01)

- The controller-move fixture now launches a bounded direct /usr/bin/perl child
  on the source surface. Fresh UUID input challenges before and after all four
  directions of cross-window/same-window moves must be acknowledged with the
  same child PID and tty path. The core surface pointer also remains unchanged.
  The final invalid-destination case preserves a responding source; explicit
  quit then requires process-exited plus ESRCH for the recorded PID.
- The child uses a private temporary reply file, no user shell or clipboard,
  and a 30-second alarm. Other surfaces still run /usr/bin/true. Fixture cleanup
  removes undo registrations, clears controller trees and closes private windows.
- Initial failures were fixture issues: Swift 5.10 crashed compiling nested
  async local helpers (moving helpers to methods compiled), and a command was
  incorrectly passed using direct: through the surface command override, which
  represents a shell command. The fixture now uses a separate explicit config
  with the core's direct command form. Its space-split arguments must not contain
  shell quotes; paths are checked to contain no spaces. No core parser change.
- live-drop-transfer-05 passes the native targeted run; live-drop-hosted-01
  passes the full Xcode suite (284 named passes/six skips). A wrong PID/tty
  acknowledgment negative control fails exactly at acknowledged with Xcode exit
  65, rather than passing on a live process alone (xcode/negative.log and
  Negative.xcresult). No physical input, provider-to-UI dispatch, gesture hit
  testing or undo/redo acceptance is inferred from controller-level calls.
- Strict fixture lint (known config warning), 17 Python verifier tests and
  whitespace checks pass. Product sources and release artifacts are untouched.
- After restoring the negative control, restored.log/Restored.xcresult again
  pass 284/six and the one XCTest scaffold; all original input hashes match.
  No direct Perl child remains after the successful and failing runs.

## Split-move undo/redo with live PTY (2026-11-01)

- Extended only the Xcode-hosted surface fixture to use the actual AppDelegate
  ExpiringUndoManager shared by two real BaseTerminalControllers. For all four
  zones, cross-window undo restores the original two trees and source owner;
  redo restores the moved tree/owner. Same-window moves reverse direction before
  undo/redo, making restoration distinguishable from a no-op.
- Fresh UUID acknowledgments require the same PID/tty after each undo and redo.
  Explicit native undo groups avoid event-loop grouping ambiguity in async test
  execution. Cleanup removes registrations only for the two fixture controllers
  and restores groupsByEvent; no replacement undo implementation is used.
- drop-undo-hosted-01 passes 284 named tests/six skips through the documented
  entry point. Omitting the cross-window undo in a copied source fails the exact
  sourceRestored assertion, Xcode exit 65 (negative.log / Negative.xcresult).
  The standalone targeted fixture also passes (drop-undo-standalone-01) but does
  not exercise undo because that host has no real AppDelegate.
- Strict fixture lint (known config-key warning), 17 Python verifier tests and
  whitespace checks pass. No product code changes. Gesture delivery, menu action
  routing, focus restoration and undo-expiration during dragging remain outside
  these controller/undo tests; physical drag acceptance is still open.
- After restoring the omitted call, restored.log/Restored.xcresult pass the full
  284/six inventory and one XCTest scaffold; all recorded input hashes match.
  No direct child remains. The restored run reports no Main Thread Checker issue.

## Reject stale core inputs in the unit workflow (2026-11-01)

- The unit entry point previously hashed an explicitly selected core archive but
  did not enforce that its recorded source still matched current core sources.
  Added native-suite/core-inputs.py and pre/post checks in both candidate and
  Xcode builders. External core roots require build-core.py's successful universal
  result, matching current/snapshot source inventory and matching artifact hashes.
- The selected rebuilt-core-02 verifies 1400 core/build/resource source files
  and 925 installed artifacts. Swift/test/docs-only changes do not force a core
  rebuild. Changed/added/deleted core input, modified snapshot, missing/failed
  evidence and altered/extra artifacts are rejected in executable fixture tests.
  Normal current-worktree core builds are explicitly labeled unverified, not
  falsely presented as source-linked snapshots. Local manifests are not signed
  attestations and do not prove hermetic external toolchains/dependencies.
- core-provenance-prepare-01 records the verified evidence without compiling an
  intermediate app. The complete core-provenance-hosted-01 workflow passes the
  new pre/post checks and 284 named tests/six skips with the real Xcode scaffold.
  Twenty-eight fast verifier tests and whitespace checks pass. No core rebuild,
  product-code edit or release-artifact replacement was needed.

## Remaining acceptance handoff (2026-11-01)

- Rechecked the current environment (Intel 12.7.6), branch/HEAD, product metadata,
  universal slices and strict signature. ReleaseLocal executable SHA256 remains
  767e290f7c578a9fa487cc33a6062bd78a07a564b0de5600e736782198227170;
  revision is dirty and signing is ad-hoc with no TeamIdentifier. Latest current
  archive and candidate-unit result files remain present and accepted in their
  respective scopes. These checks do not establish public-release readiness.
- Added MANUAL-ACCEPTANCE.md with that artifact identity and concrete remaining
  physical input/IME/search, gesture/move/undo/focus, VoiceOver, appearance and
  Shortcuts scenarios. It separately identifies arm64/12.0 hardware evidence,
  clean-machine trust, immutable source identity and update ownership decisions.
  Every manual row is explicitly pending; no synthetic test is substituted.
- The documented no-file Perl continuity helper was executed in a private PTY:
  it reports its own PID/tty, echoes a fresh marker with that PID, and exits on
  quit. This validates the helper only, not a manual app scenario. Document
  references and whitespace checks pass. No product changes, input injection,
  permission changes, signing setup or publishing was performed.
- Further physical/hardware release claims require reviewer action or another
  machine, not another rerun of the already-passing lower-level tests. Unit
  execution is now a documented path; UI API compatibility remains separately
  open. See RELEASE-READINESS.md for the requirement-level verdicts.

## Authorized Intel-only interaction verification (2026-11-01)

- User explicitly permits controlling the current machine and excludes ARM.
  Updated the active readiness, acceptance and keyboard scope accordingly;
  earlier arm64/12.0 second-machine requirements no longer apply to current-host
  acceptance. No architecture slice or product feature was removed.
- Ran native-ui.swift with foreground HID-tap CGEvents, real raw-PTY byte
  recorders, Carbon input-source changes, actual NSDraggingSession gestures,
  AX geometry and real Edit menu actions against an isolated copy of the same
  ReleaseLocal executable. NATIVE-INTERACTION.md enumerates results/limits.
  Evidence is /tmp/ghostty-monterey/native-interaction-02; no callback substitute
  or controller test is being presented as a native gesture.
- ABC Ctrl A-Z, shifted/control punctuation, Kitty Ctrl-A press/release, dead
  keys and all eight option-as-alt mode/side cases pass exact byte assertions.
  Chinese Pinyin preedit produces no premature terminal bytes, commits once,
  and cancels cleanly. Search composition/cancellation and replacement pass
  after restoring the select-all binding deliberately cleared by the test.
- Four in-window directions pass actual handle drag, live PTY input and menu
  undo/redo geometry. Cross-window movement, Escape cancellation, final-pane
  source-window closing/restoration and fullscreen drag also execute. Three
  surface identities/PTYs persist. Polling is required for restored AX children
  and menu-title convergence; early snapshots were harness failures.
- Official encoder expectations, a system Ctrl-Space shortcut, cleared test
  keybindings and upstream undo naming explain the initial apparent failures.
  No product patch was made. Cross-window automatic destination activation is
  not certified: first unclicked input remained in the source pane; clicking
  the destination works. Do not generalize that into a proven OS regression.
- Screenshots were saved but the image-view tool refused them; no visual
  candidate-popup/overlay quality approval is claimed. Hardware repeat, other
  IMEs/layouts, selection-to-Find reentry, VoiceOver, appearance and Shortcuts
  remain separately scoped. Full execution details are in the new report.
- Restored the original foreground application and input source. Stopped the
  disposable app and verified all three children were reaped. No normal config,
  global hotkey, permission, Gatekeeper or publishing settings were changed.
  Fast native-suite verifier tests remain 28/28 passing; git diff --check passes.

## Image-enabled acceptance and automatic Find focus (2026-11-01)

- Image viewing now works. Inspected actual terminal/search Pinyin candidate
  screenshots and the held native drag overlay/preview. Details and capture
  boundaries are recorded in NATIVE-INTERACTION.md, not inferred from AX alone.
- Actual keyboard acceptance exposed a missed port regression: Find appeared
  without taking focus, so subsequent typing reached the terminal. A native
  one-variable comparison identifies the selection-bridge background combined
  with outer .focused. Plain field and no-bridge controls pass; hit-testing-only
  change does not fix it. This is distinct from PR #3 and inherited AX ranges.
- Bound the existing SearchOverlay FocusState to the actual TextField through
  one optional parameter. Kept the selection bridge and normal SwiftUI focus,
  submit and IME behavior; no general focus framework or responder replacement.
- Added search-focus-check.py: real focus transition passes in debug/optimized
  builds and the compiled outer-focus regression fails by the exact assertion.
  Existing search-state and selection suites pass. ReleaseLocal rebuild passes
  (search-focus-app-build.log), with existing linker warnings.
- New executable SHA256:
  cb71b89bf6a9dbbde8b4372bc680b23da363ad86f8d787ec687e786ee5ebe3bd.
  native-visual-fixed-04 passes Command-F automatic focus, no PTY input leakage,
  beta selection -> Command-E -> Command-F -> replacement, and Chinese IME
  commit/cancel after the fix. Previous artifact reports remain historical.
- search-focus-package.log passes the complete extended archive command on the
  rebuilt product, including both extracted-app suites, compositor, palette,
  lifecycle, resource and refusal checks. Temporary NOT-FOR-RELEASE packaging
  does not imply release approval. Cleanup confirms both isolated app sessions
  and their children stopped, with original foreground app/input source restored.

## Remaining local desktop acceptance run (2026-11-01)

- Same cb71b89b executable; no product changes in this run. See
  LOCAL-ACCEPTANCE.md and /tmp/ghostty-monterey/native-final-05 for exact limits.
- Actual System Preferences controls switch dual light/dark themes, verified
  in screenshots; original light appearance and private config restored. The
  transparent titlebar's override behavior matches the upstream documented
  luminosity exception and was not treated as a new bug.
- Built and ran one disposable Run AppleScript action through Shortcuts UI.
  Terminal visible text returns when allowed; live Ghostty scripting opt-out
  causes an actual invalid-terminal error. Shortcuts' original disabled-script
  setting restored, test shortcut removed, six original shortcuts preserved.
- Real self and rejected/outside drops preserve geometry and live PTY input.
  Cross-window immediate input again remains in the surviving source window.
  Official controller/helper calls do not explicitly activate the destination;
  no newer-OS runtime equivalence or patch is claimed.
- Actual VoiceOver welcome/start/navigation exercised; terminal focus outline
  visible. Reliable reading/selection transcript was not available, so full
  VoiceOver is not marked passed. Invoking-client Automation consent was declined;
  no new broad permission was granted. VoiceOver stopped afterward.
- Japanese mode selection failed in the TIS helper before app input; Korean
  case did not run. Enabled source inventory restored. These are uncompleted
  cases, not evidence of a terminal IME regression.
- Cleanup confirms original source/front application, light mode, script setting,
  no disposable shortcut and no test app/PTY/VoiceOver processes left running.

## Additional authorized local acceptance (2026-11-01)

- Same cb71b89b product; no product edits. COMPLETION-ACCEPTANCE.md records
  evidence and limits; Japanese/Korean layouts now excluded by user.
- Four cross-window directions pass actual drags, relative geometry, moved-child
  input after pointer focus and menu undo/redo. Closed test-created HelpViewer
  that initially covered right-side drop targets; no product fix required.
- Quick terminal follows actual system light/dark controls on same live surface.
  Inspected correct layer-3 captures, not earlier ordinary-window screenshots.
- Caps modifier and five repeats pass exact legacy/Kitty PTY assertions. No
  claim of physical hardware/OS repeat-timer coverage.
- Ten-minute ANSI/Unicode load passes 5,811 DSR fences, 9,669,504 output bytes.
  Final two-minute RSS range 148,676-151,000 KiB; concurrent UI checks mean this
  is not an isolated renderer benchmark or official performance comparison.
- Enabled VoiceOver captions confirm terminal text and focus/window announcements.
  Selected-text speech still lacks reliable caption evidence.
- Restored light appearance, original ABC/inventory/foreground and private config.
  Verified temporary VoiceOver Automation off, VoiceOver disabled; script-control
  authentication cancelled without bypass. Test app/children, HelpViewer and
  VoiceOver Utility exited. No security-policy or user configuration changes.

## Continued verification and hidden-titlebar drag fixes (2026-11-01)

- See FINAL-LOCAL-AUDIT.md. Audited all 28 original UI methods; all eight source
  files compile in an isolated Xcode candidate with an actual-appearance-control
  test bridge. XCTest UI startup requires local password authentication; safely
  cancelled, no bypass, no zero-test success claim.
- Correct VO-F6 event delivery makes native NSTextView read selected beta, but
  actual Ghostty reports no selection. This converts an unverified item into a
  known failure; ordinary reading remains passed. Official selectedRange is
  identical, but no single-cause speech fix is claimed or AX snapshot restored.
- Cross-window insertion and moveFocus callback match official source exactly.
  Native two-window probe confirms responder focus alone does not activate the
  destination; no newer-OS runtime equivalence claimed.
- Original hidden-titlebar UI path exposed whole-window dragging instead of
  split dragging. Hover-time Monterey-only movable-state suppression fixes it;
  saved state restores on exit/detach/completion/release. Outside Escape needed
  a native key-state fallback because the local monitor can miss cancellation.
- Final ReleaseLocal SHA256:
  3603418a1e5e42f75e1608db668dd0b9701b23237b1771f2d77ce74640cd86fc.
  Native tear-off coordinates, original-child input, undo/redo, outside cancel,
  ordinary window drag, Find/palette, and tab geometry tests pass. State fixture
  debug/optimized passes; Swift lint zero violations; extended archive passes.
- More theme transitions, title/cascade, split/zoom/fullscreen/merge/tab-move
  geometry exercised. Original fixed-width tear-off expectation disagrees with
  official treeSize sizing; retain explicit source/test discrepancy.
- Thirty-minute previous-artifact load passes 17,489 fences and 29,101,696 bytes;
  final ten-minute RSS 117,468-119,452 KiB. Not mislabeled final-build soak.
- Strict signature validation passes but Gatekeeper assessment rejects the
  ad-hoc app. Public trust/identity gates remain open. Restored original WeType,
  source inventory, foreground app, light appearance and VoiceOver off; all
  disposable processes stopped. No user config, clipboard or security changes.

## Authenticated original UI execution (2026-11-01)

- XCODE-UI-ACCEPTANCE.md supersedes the preceding password-authentication gate.
  Real XCTest UI startup now succeeds without security-policy changes or
  credential collection. Initial title case passes; the first layout group
  executes 14 methods with 11 passes and three recorded failures.
- Corrected disposable SDK13 test fixtures and element queries, not production
  code: direct-window ResetZoom button, palette title rather than descendant
  label, explicit isolated launches/teardown, and actual system appearance via
  an external controller with verified replies inside the runner container.
  Quick appearance samples the background because ReleaseFast has no debug
  banner. Intermediate crashed/interrupted runs are not counted as success.
- auth-consolidated-11 executes 26 selected methods in 148.788 seconds with
  zero failures and xcodebuild exit 0. Independent xcresulttool traversal verifies
  all 26 Success records. Includes both palette methods, both mouse/focus methods,
  all nine theme scenarios, title, four tab/zoom methods and eight position cases.
  Evidence: /tmp/ghostty-monterey/xcode-ui-07/authenticated-results.json.
- Two original methods are explicitly excluded from the consolidated run after
  failures: fixed-size detach expects width 328 but official pane sizing gives
  165; cross-window tab test cannot hit the private _zoomLeft: menu, and alternate
  real-window positioning still fails before tab transfer. Native final-product
  tab-transfer evidence remains separate. This is not an unchanged 28/28 pass.
- The mouse-selection test now actually passes, with clipboard item data held
  only in memory and restored under a change-count guard. No clipboard contents
  are logged. Light appearance, original foreground iTerm PID 22191, ABC source
  and full input-source inventory are verified restored. Test apps/controller
  stopped and newly opened System Preferences quit.
- ReleaseLocal executable hash remains 3603418a1e5e42f75e1608db668dd0b9701b23237b1771f2d77ce74640cd86fc.
  This turn changes acceptance documentation only in the repository. Known
  VoiceOver selection, activation and public trust/immutable-identity limitations
  remain; no commit, issue/PR, publication or false goal-completion claim.

## Remaining UI verification and inherited-failure classification (2026-11-01)

- REMAINING-VERIFICATION.md records actual cross-window tab transfer through
  XCTest after native AX positioning and client-side enumeration of tab frames.
  Counts change 3+2 to 2+3, with original geometry assertions retained. Two
  individual runs and two consolidated runs pass that case.
- remaining-consolidated-17 reports 26/27 passes with an empty-title startup
  observation. Unchanged title rerun passes; a bounded expected-title wait
  precedes the unchanged assertion in the disposable candidate. Final
  remaining-consolidated-19 passes all 27 selected methods in 170.685 seconds,
  exit0, independently verified from xcresult. Fixed-width detachment's known
  official sizing/expectation disagreement remains the sole excluded method.
- Preserved compact results, log hashes and exact candidate UI source delta in
  evidence/2026-11-01-ui. No original UI assertions or product sources edited.
- Final-product quick terminal runs the configured isolated child and receives
  native input. Last-login output is explained by official-identical macOS
  login wrapping, not evidence that the command is ignored.
- Final-product native split drop preserves all panes/children but sends the
  next key to the remaining source, not the moved pane. Source mutation/focus
  scheduling is official-identical. Further small NSView AX metadata controls
  still fail VO-F6 selection speech; same-session NSTextView control passes.
  These are recorded failures, not missing permission or inferred newer-OS bugs.
- Read-only signing identity listing finds zero valid identities. Public trust
  and immutable release identity still need owner decisions/credentials; no
  Gatekeeper bypass, publisher-key generation or unauthorized release occurs.
- Stopped private app/PTYs, controllers and VoiceOver fixtures. Verified
  VoiceOver off and original light appearance. Restored foreground22191, WeType
  and exact enabled-source inventory, including undoing testmanagerd's source
  changes. Clipboard guards logged restoration without storing its contents.

## User scope correction: ReleaseLocal only (2026-11-01)

- User explicitly excludes app signing and notarization from verification and
  intends to distribute ReleaseLocal only. Earlier requests for signing identity
  or distribution-trust decisions are superseded; Developer ID, notarization
  and Gatekeeper approval are not goal blockers.
- Preserve existing ad-hoc build mechanics, package contents/integrity checks,
  exact artifact hashes and manual-update safety. This clarification does not
  authorize security-policy changes, commits, tags or publication.
- The 27 selected UI passes, fixed-width source/test disagreement and actual
  VoiceOver/cross-window-input failures retain their recorded verdicts. Scope
  correction alone does not mark functional failures passing or the goal done.
- Updated current readiness/build/acceptance documents; no product or packaging
  code changed and no signing operation was performed.

## Cross-window automatic focus repair (2026-11-01)

- Built a fresh red-capable native handle/PTY repro. Previous ReleaseLocal sends
  `b` to remaining48830, not moved48855. A one-call candidate activates the
  destination only after successful cross-window insertion; moved49044 receives
  the byte without a refocus click. Four directions and actual Edit undo/redo
  pass before promoting the same change to BaseTerminalController.
- Rebuilt ReleaseLocal SHA256
  583e90ea4f5c1779deef5c077dc451cf52f526922db2f5aa161b2840ad83e408.
  Two independent native launches pass. Four-direction moves, input after redo,
  same-window move, Escape cancellation and last-pane source-window closure pass
  with live child identity and exact byte checks. Shared moveFocus is unchanged.
- Added cross-window-focus-check.py: production success-tail extraction with
  real AppKit windows, debug/optimized positives and removed-activation negative
  controls. This seam stubs tree mutation; actual native tests provide full-path
  evidence. Strict changed-file SwiftLint and diff whitespace checks pass.
- Extended extracted-archive suite passes on this new binary. Corresponding
  candidate real XCTest repeat passes 27 methods, zero failures, 169.866 seconds,
  independently parsed from xcresult. First rerun was interrupted (exit75) after
  appearance-controller navigation failure; it is retained as failed evidence.
  Original fixed-width expectation disagreement remains unchanged.
- VoiceOver control comparison narrows selected-speech behavior: a range setter
  yields beta/selected; a text setter alone still yields no selection. Actual
  screenshots inspected. Empty diagnostic setters are not a legitimate product
  implementation and were not promoted. Existing selection range/speech failures
  and user-approved AX snapshot separation remain explicit.
- FOCUS-ACCEPTANCE.md and evidence/2026-11-01-focus pin results, probes and hashes.
  No broad AX change, system toolchain replacement, installation, commit or upload.
  All private jobs stopped; VoiceOver off/light appearance verified; restored
  iTerm/WeType/full source inventory, including original EmojiFunctionRowItem.
- Fresh current-source hosted unit candidate focus-unit-37 rebuilds the app/test
  targets with reused pinned Testing objects and verified rebuilt core. Initial
  WeType-selected run reports 17 nil keyboard-layout issues. The unchanged Xcode
  repeat with ABC selected passes 284 named tests and six documented skips;
  original failure is not overwritten. unit-results.json and both log hashes
  preserve that condition. Restored WeType/iTerm and exact source inventory again.

## IME-selected synthetic keys and remaining disposition (2026-11-01)

- Previous ReleaseLocal script send key delivers aA with ABC but no bytes with
  WeType/system Pinyin, confirming actual product impact beyond unit assumptions.
  Existing AppKit synthetic-event translation returns nil; the already-present
  Carbon layout helper supplies letters/modifiers. Preserve AppKit success and
  fall back only on nil in KeyboardLayout.character; real NSEvent routing stays
  unchanged. The pre-fix helper matches official source, not PR #3's event path.
- Added repository native input-source regression, red against pre-fix source
  and green in debug/optimized builds. Corrected an initial test-only assumption
  that system Pinyin punctuation must be ASCII; preserve native full-width output.
- Rebuilt ReleaseLocal c456ff946ec0242a7dd961170415844fbc40cf874d8c45ab77cb16228bb98ac7.
  Exact script letters/control/shift/option/release bytes pass in three sources;
  native WeType/Pinyin ni preedit is buffered and commits one Chinese character.
  Extended extracted archive suite passes. WeType-selected unit candidate now
  passes 284 named tests/six skips; UI repeat passes 27/0 in 164.444 seconds.
  First UI attempt was interrupted on appearance-controller navigation failure;
  bounded observed-state polling fixes the harness, not product assertions.
- Keyboard boundary 402 checks/six rejected mutants and native SDK/header
  454 checks per optimization mode pass. Changed helper strict lint/diff pass.
- Fixed-width actual native teardown/undo/redo/cancel rerun passes pane-size
  behavior on current release. Official implementation and conflicting assertion
  verified; retain behavior and failed original assertion, no resizing redesign.
- Same-binary VoiceOver control toggling only selection-range setter permission
  yields no-selection versus beta/selected. Setter is never invoked by VO-F6.
  This narrows the speech gate but is not a valid Ghostty fix; no empty setter,
  advertised false capability or broad AX snapshot promoted into the product.
- INPUT-ACCEPTANCE.md/evidence/2026-11-01-input record identities and raw results.
  Original foreground, WeType and full source inventory restored; VoiceOver off,
  light appearance, private jobs stopped. No install/commit/upload/security change.

## Non-selection acceptance on unchanged current release (2026-11-01)

- User excludes AX selection work; keep its known failure recorded but do not
  reintroduce it as the current follow-up gate. No product changes or rebuild.
- NONAX-ACCEPTANCE.md and evidence/2026-11-01-nonax record 22 private-copy GUI
  checks, a progress-disabled control, four original-release notification checks,
  five additional original-release checks, eight fake-SSH boundary cases and
  five actual OpenSSH-to-loopback-server cases.
- Secure Input canonical/noecho, global toggle, activation yield/reacquire and
  secure-surface close release pass. Progress state/value/removal/expiry passes.
  Visual Bell and command duration/focus policy pass. No passwords are entered.
- Private bundle notification validation fails; original unmodified ReleaseLocal
  is authorized and delivers real desktop/success/failure notifications. Native
  Notification Center click-to-focus and focus cleanup pass. No security setting
  or notification database is changed. Do not claim private copies passed.
- Real SSH uses generated keys, strict host-key checking, only 127.0.0.1 and
  an isolated server command handler, not system sshd or personal hosts. Existing
  ncurses 6.6 compiles transferred terminfo and infocmp reads it back. The remote
  system tic 5.7 limitation and explicit-command limitation remain documented.
  An initial test cache entry outside the intended state directory was removed
  by exact test key; repeated passing cases explicitly isolate XDG_STATE_HOME.
- Current-build workload passes 600.058 seconds, 5,780 DSR cycles, 9,617,920
  bytes. RSS 64,572 -> 112,428 KiB across 121 samples; no leak-free or performance
  parity claim. This supersedes relying only on the older artifact's soak.
- Test apps/PTY children and loopback listener are gone. Full session snapshot
  matches the start, Secure Input off, executable hash still c456ff946ec0242a7dd9
  (full hash in report). No commit/upload or unrelated product fix.

## Bounded-history resource and acceptance reconciliation (2026-11-01)

- Unmodified c456ff94 ReleaseLocal, explicit 1 MB/1,000-line history: eight
  minutes, 20,169 exact DSR cycles, 67,122,432 bytes pass. DSR median/p95/max
  0.225/1.199/9.647 ms is response latency, not GPU presentation latency.
- Final four minutes RSS 59,104-60,092 KiB, net +940 KiB. Ten extra windows
  load/close and all children exit. Post-close cycle-three-to-ten growth is
  1,216 KiB. Predeclared bounded criteria pass; residual growth/caching does
  not establish leak freedom or official performance parity.
- Five temporary copied-app Bell observer controls pass: disabled, custom sound
  accepted at volume 0.1, original NSBeep, informational attention request, then
  disabled again. All system calls forward to originals. No acoustic recording
  or measured Dock animation is claimed, and no instrumentation enters product.
- Corrected two harness assumptions: scripting pid was login wrapper rather
  than fixture child; Swift NSSound.beep uses overlay/NSBeep, not the observed
  Objective-C class method. Neither failure prompted a product change.
- RESOURCE-ACCEPTANCE.md and EVIDENCE-INDEX.md retain results/recipe. Four full
  matched build/archive/unit/UI logs are now durable. RELEASE-READINESS.md is
  reconciled to current scope; its old chronological wording is preserved in
  READINESS-HISTORY.md. Historical handoffs now point to the current index.
- Session restored, fixture processes exited, Secure Input off, original hash
  unchanged. AX selection remains excluded and unresolved. No rebuild, commit,
  upload, personal configuration or system security change.

## Approved retention of narrow AX text/cache differences (2026-11-01)

- User accepts retaining the three general UTF-16 count/range-length/line fixes
  and the Monterey cache/clock adaptation. PATCH-SCOPE.md now distinguishes
  general correctness from OS compatibility and records the minimal scope.
- Reran accessibility-text-check.py: production methods pass debug/optimized
  checks and all six compiled regression mutants are rejected. Reran
  cache-check.py: reuse, expiry, concurrency and lifetime pass in both modes.
  Logs and source/artifact hashes are in evidence/2026-11-01-ax-retention/.
- No product code change or rebuild. The current c456ff94 artifact is unchanged;
  no AX snapshot restored, writable selection advertised or selection repair
  claimed. Full-app selection and physical sleep/wake are not these tests.
