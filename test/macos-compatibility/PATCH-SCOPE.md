# Patch necessity audit

Baseline: official 1.4 commit `83fb95624b0439ee660c2679b43b38c8b63769cd`.
Required runtime: macOS 12 only. Historical main is not the feature ceiling.
This is a partial audit of the current diff, not release approval.

## Latest AX decision (2026-11-01)

The user subsequently reopened AX work. AX-AUTOMATION-WORK.md supersedes the
historical AX exclusion below: a new isolated mapping module, small C read/write
interface and formatter continuation are now active. Screen/StringMap and the
input-method selectedRange remain unchanged. The separate lazy AX cache is not
used by ordinary scripting text readers. This is an explicitly requested general
correctness/feature restoration, not a Monterey compilation requirement. The
archived broad patch is not applied wholesale. New full-app native rectangle,
setter and VoiceOver evidence is retained with measured mapping cost.

## Retain as port or distribution work

- Xcode 14 explicit source memberships, Swift 5.7 syntax, SDK/compiler guards,
  deployment 12.0, and icon assets address the actual build environment. Keep
  upstream algorithms and source memberships rather than removing features.
- Duration/continuous-clock equivalents and native item-provider surface drops
  replace APIs unavailable on Monterey. Preserve precision, cancellation,
  asynchronous delivery and surface identity; these are not optional UI cuts.
- PR #3's native event translation fix is already retained. The current
  `NSEvent+Extension.swift` matches its final commit
  `f0763f6f771d9eb0cf51753a1a17905dfa7e56c9`. `KeyboardLayout.swift` also retains
  official 1.4's separate menu translation helper. Do not replace either file
  wholesale with historical main or duplicate the Ctrl-event workaround.
- Native window restoration/fullscreen changes address demonstrated Monterey
  feature failures. They require actual window/session evidence, not just
  source availability annotations. See the restoration sections in STATUS.md.
- Three read-only AppleScript terminal-text properties retain operations from
  GetTerminalDetailsIntent on Monterey, which lacks AppIntents. They reuse the
  existing readers and scripting policy without new C ABI/cache/controller.
  This is a small explicit scripting dictionary extension, not exact Shortcuts
  parity or a reason to retain the optional AX snapshot work below. See the
  operation-by-operation coverage and remaining gaps in AUTOMATION.md.
- `open quick terminal` also retains the Intent's idempotent open operation
  through the existing controller and returns its live scripting terminals.
  It does not introduce another lifecycle/state machine or change toggle
  semantics. AppleScript creation returns references rather than the Intent's
  awaited metadata/screenshot entities; that difference is explicit.
- Metal texture storage and the AMD background-color expression address native
  GPU failures observed on this host. They are hardware/driver compatibility
  work, not proof that the upstream logic fails exclusively on macOS 12. Keep
  the rendering features and upstream optimization level.
- Fork-only update metadata and archive validation are distribution safety,
  not missing OS capabilities. Keep Sparkle 2.9.6 and its verification. A local
  build without a distributor-owned feed/key must not install official builds.
  Commit-count numbering requires full Git history, as upstream release jobs do.

## Separate optional upstream fixes from port requirements

### Historical AX text and cache disposition (superseded)

The user approved retaining the four narrow differences on 2026-11-01. This is
a decision to keep the existing implementation, not to resume excluded AX
selection work or restore the archived snapshot experiment.

| Difference from official 1.4 | Classification | Retained behavior and reason |
| --- | --- | --- |
| AX character count | General correctness fix, not a Monterey requirement | Count UTF-16 units rather than Swift grapheme clusters, matching AppKit text offsets. |
| AX visible-range length | General correctness fix, not a Monterey requirement | Use the same UTF-16 unit as substring ranges. The upstream full-content-as-visible policy is unchanged; this is not viewport mapping. |
| AX line lookup | General correctness fix, not a Monterey requirement | Interpret the supplied offset in UTF-16 units and reject negative indices, instead of crossing newlines early after multi-unit characters. |
| Text-cache clock and expiration | Monterey compatibility with lifecycle protection | Replace unavailable clock APIs; check expiry on reads, reject stale-generation eviction, and retain asynchronous payload release when idle. |

Keep the three text-unit corrections together. Reverting them merely to match
upstream would reintroduce demonstrable unit mismatches without reducing the
selection-mapping limitation. Keep the existing cache interface/locking model;
do not replace it with a new snapshot architecture or remove idle eviction.
The cache behavior is a compatibility safeguard, not proof of an observed
upstream sleep/wake failure on newer macOS.

The actual selection range still delegates to upstream selectedRange and its
terminal-cell offsets. No UTF-16 selection setter, fabricated writable AX
capability, disjoint-range mapping or new core/header API is added. Selected-text
speech and range defects remain recorded and excluded. Search-field selection
bridging is separate from this terminal AX decision.

Verification entry points: accessibility-text-check.py exercises extracted
production text methods against native text controls in debug/optimized modes,
and rejects three regressions per mode. cache-check.py exercises the production
cache for reuse, expiry, concurrent reads and object/payload lifetime. These
checks do not claim full-app AX selection or physical sleep/wake coverage.
Decision evidence: evidence/2026-11-01-ax-retention/.

### Other retained fixes and separated experiments

- Synthetic key/menu translation now falls back to the existing underlying
  layout helper when AppKit returns nil. Actual AppleScript send key previously
  dropped letters under WeType and system Pinyin; new ReleaseLocal exact bytes
  and native IME composition pass. Successful AppKit translations, including
  Chinese punctuation, remain unchanged. INPUT-ACCEPTANCE.md records red/green,
  WeType-selected original unit results and the distinction from PR #3.
- Successful cross-window drops now explicitly activate the destination window.
  This is one call in the success branch, not a generic focus/undo redesign.
  Actual pre-fix input goes to the remaining source; the rebuilt app passes
  fresh-key routing, four directions, redo/cancel and last-pane window closure.
  See FOCUS-ACCEPTANCE.md. The omitted activation is inherited in source;
  no newer-OS runtime comparison or macOS-12-exclusive cause is claimed.
- User selected separation of the large AX snapshot group (option 1). The
  optional C API, Screen/StringMap/formatter changes are removed from active
  product code and preserved in optional-ax/snapshot.patch with original test
  sources. All five affected core/header files now match official 1.4 exactly.
  Swift retains the upstream full-text cache and selection-only reader. Small
  UTF-16 count/visible-range/line fixes remain independently reviewable.
  The unused snapshot-only cache invalidation method is also archived with the
  experiment; time-based cache expiry and Monterey clock handling remain active.
  Upstream cell-based selected-range defects are knowingly inherited, not fixed
  or silently marked passing. Strict services --selection remains a diagnostic.
  Earlier snapshot cost/correctness results describe the archived experiment,
  not this reduced product. Search-field bridging is outside this decision.
- The search-field selection bridge implements behavior that upstream's
  pre-macOS-26 fallback deliberately omits. It preserves more functionality but
  adds native hierarchy matching, notifications and state reconciliation. This
  is not required merely to compile on 12. Judge its feature value and maintenance
  cost separately; its tests do not establish physical IME acceptance.
  A one-variable native comparison now records the actual fallback cost:
  `search-state-check.py --compare-upstream-fallback` compiles the production
  SearchState and SwiftUI field with/without only the selection background.
  Both modes synchronize a settled external needle, but the upstream fallback
  leaves the caret at the end (typing appends instead of replacing); a same-turn
  native edit/external replacement leaves editor and model text divergent.
  The current bridge preserves select-all and convergence in both optimization
  modes. This is bounded native evidence, not physical IME/full-app evidence or
  proof of a macOS-12-exclusive bug. Retain the bridge for now rather than extend
  the user's AX-only separation decision to an unrelated feature. No additional
  generic backport architecture is warranted by this comparison.
  The separate same-turn stress run emits SwiftUI multiple-updates-per-frame
  warnings despite passing convergence assertions; do not describe it as a
  warning-free run or evidence of acceptable frame pacing.
- Upstream's pre-14 onKeyPress and pre-15 pointerVisibility helpers are no-ops.
  Neither has a remaining production call site in this worktree. Do not build
  general-purpose backports for unused helpers. Search Shift-Return is handled
  by the existing field's onSubmit; split dividers retain their onHover cursors.

## Observations that do not justify product changes

- `TerminalWindow.swift` is unchanged from official 1.4. The native-fullscreen
  accessory recursion warning also occurs in an independent AppKit/SwiftUI
  reproduction, while the tested geometry and lifecycle assertions pass. There
  is no demonstrated visible/performance defect and no newer-OS comparison.
  Neither a macOS-12-only defect nor upstream runtime reproduction is proven.
- The experimental synthetic Option-E case is a harness failure, not evidence
  of a physical keyboard regression or a rediscovery of PR #3. Keep it outside
  release blockers unless a genuine app failure is reproduced.
- Broad ABI/Unicode edge-case exploration must not silently become a condition
  for finishing an OS port. Prioritize build failures, demonstrated macOS 12
  feature failures, and regressions caused by this adaptation.

## Current evidence and limits

The 2026-10-30 host symbol rerun resolves all required system imports in seven
Mach-O files on x86_64 macOS 12.7.6 (`scope-symbol-audit.json` in the temporary
evidence directory). There are still 45 missing weak imports in the main app;
availability guards/runtime path coverage matter, not eliminating those entries.
This does not prove arm64 execution, macOS 12.0, Objective-C selector availability,
clean-machine launch, or signed update installation. Current scope and acceptance
are in RELEASE-READINESS.md; STATUS.md preserves historical intermediate gates
rather than defining a new backlog. No feature removals are authorized by this
classification.
