# Authenticated Xcode UI acceptance

Current scope: the user chooses ReleaseLocal-only distribution and excludes app
signing/notarization from verification. Historical public-trust gates below are
not current acceptance blockers; functional failure verdicts are unchanged.

Latest follow-up: REMAINING-VERIFICATION.md records 27 selected methods passing
in one run, including cross-window tabs, with a bounded title readiness wait.
Only the original fixed-width tear-off expectation remains excluded. The 26-case
results below are historical; the exact candidate test delta is now archived.

2026-11-01, Intel macOS 12.7.6, Xcode 14.1. Authentication now permits real
XCTest UI execution. No credentials were collected, password controls inspected,
or security policy relaxed. ARM, newer systems and Japanese/Korean layouts are
not requirements. This report supersedes the earlier authentication blockage.

## Candidate and evidence

The isolated candidate is /tmp/ghostty-monterey/xcode-ui-07, application ID
org.ghostty.ui07.app, with the temporary Swift 5.10.1 toolchain and SDK13.
It retains the prior test-toolchain adaptations and embeds ReleaseFast libghostty.
Before the consolidated run, SurfaceDragSource.swift was refreshed from the
final repository source; the search-focus fixes are also present.
This is not the ReleaseLocal bundle and is not an unmodified upstream build.

Product sources were not edited in this follow-up. ReleaseLocal executable
SHA256 remains 3603418a1e5e42f75e1608db668dd0b9701b23237b1771f2d77ce74640cd86fc.

Evidence under the candidate directory:

- auth-174658.log/.xcresult: initial authenticated title test passes.
- auth-layout-01.log/.xcresult: 14 methods, 11 pass and three fail.
- auth-diagnostics-07.log/.xcresult: eight theme methods and corrected
  reset-zoom geometry pass; palette query and missing debug-banner failures.
- auth-titles-08.log/.xcresult: both palette cases and mouse-selection case pass
  after matching the actual button title rather than label/child label.
- auth-quick-09.log/.xcresult: quick-terminal background light/dark passes.
- auth-tabs-10.log/.xcresult: alternate window-position setup still fails before
  cross-window tab transfer; no false passing claim for that attempt.
- auth-consolidated-11.log/.xcresult: 26 selected methods, zero failures,
  148.788 seconds of test execution, xcodebuild exit 0.
- authenticated-results.json: all 26 Success records independently read back
  from xcresulttool, two explicit exclusions, artifact hash and cleanup checks.

Intermediate auth-interaction/queries/isolation/container/launch runs exposed
fixture failures and were not accepted as passing suites. Several were stopped
after runner crashes or startup stalls to fix the test harness; their exit
statuses and logs remain available. Zero-test suites during crash recovery do
not contribute to the reported 26 successes.

## Consolidated result

| Class | Selected methods | Result |
| --- | ---: | --- |
| GhosttyCommandPaletteTests | 2 | Pass: outside click, Escape, submit, keyboard and mouse selection |
| GhosttyMouseStateTests | 2 | Pass: search typing/click/Escape and focus-change/no accidental selection |
| GhosttyThemeTests | 9 | Pass with real system appearance changes; quick case uses background instead of absent debug banner |
| GhosttyTitleUITests | 1 | Pass |
| GhosttyTitlebarTabsUITests | 4 | Pass: reset-zoom alignment, normal, fullscreen, merge |
| GhosttyWindowPositionUITests | 8 | Pass: cascade, nonfixed tear-off, four style frame round-trips, two config/cache cases |

The four frame round-trips close and reopen a window within the application;
they do not prove cross-process session restoration. Theme pixel checks retain
the original luminance thresholds. No skip is counted as a pass here.

## Test-only adaptations and limits

All following edits are in the disposable candidate, not original repository
UI tests or product sources:

- Create default configuration if absent; launch explicitly rather than depend
  on a previously active app. Isolate config/defaults, terminate after each
  method, suppress updates/restoration/close confirmation and request bounded
  bash without profile files. Give default test windows 100 columns/30 rows;
  explicit per-test dimensions still override these. This fixture is not proof
  that every quick-terminal child honors the configured shell: a quick-terminal
  snapshot contained a login banner, and that discrepancy remains unclassified.
- ResetZoom is a direct window button on this host, not a button under an AX
  group. Query app.buttons instead of app.groups.buttons; keep the one-point
  vertical-alignment assertion unchanged.
- Palette buttons expose their combined text as title, not label. Captured
  XCTest debugDescription and independent native AX tree both show the button.
  Match title directly instead of searching descendants containing a label.
  Query-only changes initially failed; clearing cached state and enlarging the
  fixture also did not fix it. Matching the observed title fixed the failures.
- The SDK lacks XCUIDevice. A test-only bridge requests real System Preferences
  clicks from an external desktop controller through files in the runner's own
  container Documents directory. Every request verifies the selected checkbox
  value before acknowledgment. Earlier attempts to spawn an AX helper or write
  outside the sandbox failed; sandbox entitlements were not weakened.
  Disable redundant automatic UI-configuration iteration; each relevant method
  itself requests its required system appearance.
- The quick-terminal test expects a debug warning from a Debug/ReleaseSafe core.
  This candidate embeds ReleaseFast, so that warning correctly does not exist.
  Instead sample the quick window background at (5,5), retaining light/dark
  luminance assertions. This tests actual appearance but is not the original
  banner-element assertion.
- The mouse-selection test snapshots pasteboard item data only in memory,
  clears the clipboard for the original assertion, and restores only if its
  change count still matches the test's clear operation. All completed runs
  report restoration; contents are not logged or persisted. Concurrent clipboard
  changes are not overwritten. This preserves data, not clipboard ownership or
  change-count identity.

## Two unresolved original methods

1. testDragSplitWindowPositionWithFixedSize fails its unchanged width assertion:
   actual 165 points versus expected 328, tolerance five. Official
   newWindow(tree:) sizes from pane bounds, as previously documented. Nonfixed
   detachment and final-product native fixed/nonfixed pane-bound tests pass.
   Do not change product behavior or the original expected width merely to
   obtain a green count. Failure is recorded, not skipped as unsupported OS.
2. testTabsGeometryAfterMovingTabs cannot click the private _zoomLeft: menu item
   on Monterey: XCTest sees an infinite origin/zero-sized, nonhittable item.
   A temporary real titlebar-drag positioning variant also failed locating the
   second window's tabs before transfer. It is not accepted as equivalent
   coverage. Earlier tabs-ui-25 final-product native dragging changed groups
   4+2 to 3+3 with preserved geometry; that evidence remains separate from this
   unresolved original XCTest method.

## Cleanup and release disposition

The consolidated run terminates its private application after every method.
The appearance controller was stopped and System Preferences (opened for this
session) quit. Light appearance is verified selected. cleanup-session.json
matches the original foreground PID 22191 (iTerm), ABC input source and complete
enabled-source inventory. The clipboard restoration guard logged success.

This closes the authentication and broad unexecuted-UI gap, not public release.
VoiceOver selected-text speech remains a demonstrated failure, automatic
cross-window key activation remains unverified as correct, and ad-hoc signing
still fails Gatekeeper assessment. No signing credentials, notarization,
immutable release identity, commit, tag, issue, PR or publication was produced.
