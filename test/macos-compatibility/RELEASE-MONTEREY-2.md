# Monterey revision 2 release

Published 2026-11-13:
[v1.4.0-monterey.2](https://github.com/laojianzi/ghostty-monterey/releases/tag/v1.4.0-monterey.2),
marked Latest at publication. Application version remains **1.4.0**.
The [revision-1 record](RELEASE-PUBLISHED.md) remains historical evidence.

## Artifact identity

| Field | Published value |
| --- | --- |
| App version / build | 1.4.0 / 18467 |
| Source and release tag target | `2d9823e797d444c05d9b8166ff6b672067ef45d4` |
| Official baseline | `83fb95624b0439ee660c2679b43b38c8b63769cd` |
| Profile / supported architecture | ReleaseLocal / x86_64 |
| Verified runtime | Intel macOS 12.7.6 |
| App ZIP | `Ghostty-macos12-1.4.0-monterey.2-18467-releaselocal-x86_64.zip` |
| ZIP SHA256 | `b347b1a5073ba0f2ab0cf97c1cda16b0873a198c6d36eb4f644206734ab885c5` |
| Executable SHA256 | `f33f3808dc9a03b4e4fe58f0d11039540c1f7a58ca1cab545cd46349e01ba518` |

Seven assets are published: application ZIP, matching symbols ZIP, `manifest.json`,
`build-provenance.json`, `SHA256SUMS.txt`, `RELEASE-NOTES.md` and `ACCEPTANCE.md`.
All seven uploaded assets matched GitHub's server-side SHA256 digests. Checksums
provide integrity, not independent publisher authentication.

## Change and delivery checks

The Metal target now releases its IOSurface reference without explicitly purging
pixels still owned by a presentation layer. This fixes issue #4 without disabling
hidden-surface swapchain, buffer or font-atlas reclamation. A presented last frame
can remain alive until its remaining owners release it; exact GPU memory overhead
was not measured. See [TAB-FLASH.md](TAB-FLASH.md) for root cause and the separate
build-18466 before/after diagnostic, not final-artifact results.

A clean full-history checkout produced fresh core and app outputs using Zig
0.17.0 and Xcode 14.1. Existing Zig global and dependency source/download caches
were reused; bit-for-bit reproducibility is not claimed. Source metadata,
Intel architecture, deployment/dependencies, coverage/debug-entitlement exclusion,
strict ad-hoc signatures, resources and ZIP file/mode/link round trip passed.
App and Dock plugin symbols match their binary UUIDs. Pinned Sparkle retains
untested ARM slices, not ARM support.

## Final-archive targeted verification

The extracted archive supplied isolated, privately identified and re-signed GUI
fixtures. The installed application was not replaced; personal configuration was
not edited. These results are not unmodified installed-app certification.

| Tab-switch variant | Round 1 bad / samples | Round 2 bad / samples |
| --- | --- | --- |
| Default | 0 / 913 | 0 / 940 |
| No vsync | 0 / 931 | 0 / 924 |
| Native titlebar | 0 / 930 | 0 / 935 |
| Continuous output | 0 / 883 | 0 / 883 |

Each variant completed 40 verified switches: 160 total, zero bad samples among
7,339 switch samples. Samples are not unique frames or a universal timing guarantee.
All baseline samples also passed.

Targeted AppleScript configuration/live-policy, Kitty raw/PNG rendering in three
color modes, lifecycle TTL/close/undo/redo, quick-terminal identity, transparent
PTY startup/quit, eight Services combinations and cross-process AX selection
read/write/notification checks passed. Resource checks covered 880 exact hashes,
819 relocated themes, named-theme controls and terminfo. Exact commands and
results are in the release's `ACCEPTANCE.md` asset.

## Retained boundaries

- Previous build-18465 expanded-test failures (single-visible-window pixel helper
  and terminal-text timeout) remain unresolved, not established as harness-only.
  New targeted passes do not retroactively erase those failures.
- Historical 284 unit passes/six skips and 27 of 28 UI passes were not rerun.
  The fixed-width UI expectation and incomplete unfiltered Zig suite remain
  excluded from the frozen release scope.
- No native AppIntents/Shortcuts parity, arbitrary AX sub-cell/multiple-range
  writes or atomic output snapshots are claimed. AX retains a 500 ms cache.
- ARM, other OS versions and Japanese/Korean layouts are not certified.
  ReleaseLocal is ad-hoc signed, without Developer ID or notarization; updates
  are manual, with no distributor feed.

This release record and download-link updates are post-build documentation.
They do not change the release tag, build identity or require rebuilding it.
