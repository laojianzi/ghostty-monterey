# Published Monterey release

Historical revision-1 record. The current release is documented in
[RELEASE-MONTEREY-2.md](RELEASE-MONTEREY-2.md); results below retain their original
artifact identity.

Published 2026-11-02:
[v1.4.0-monterey.1](https://github.com/laojianzi/ghostty-monterey/releases/tag/v1.4.0-monterey.1),
marked Latest at publication. This record supersedes earlier statements that
only a dirty development archive exists or that Intel packaging is unimplemented.
Historical reports retain their original artifact identities and results.

## Frozen artifact

| Field | Published value |
| --- | --- |
| App version / build | 1.4.0 / 18465 |
| Source and release tag target | `0445308a91778b6d0f84f12458c1ec365c77747a` |
| Official baseline | `83fb95624b0439ee660c2679b43b38c8b63769cd` |
| Profile / supported architecture | ReleaseLocal / x86_64 |
| Verified runtime | Intel macOS 12.7.6 |
| App ZIP | `Ghostty-macos12-1.4.0-monterey.1-18465-releaselocal-x86_64.zip` |
| ZIP SHA256 | `768d303fa397056381d7613093e4f46a9a032927ad72732889cfae62ee73296b` |
| Executable SHA256 | `369d7dc122d6bab17a7c3d3cae5f2637c43917152399388db5cae9d11fefabf4` |

The release provides the application ZIP, separate matching symbols ZIP,
`manifest.json`, `build-provenance.json`, `SHA256SUMS.txt`, `RELEASE-NOTES.md`
and `ACCEPTANCE.md`. All seven uploaded assets matched GitHub's server-side
SHA256 digests. See those release assets for the immutable delivery record.

## Delivery verification

Clean full-history source identity, app metadata, Intel architecture, minimum
deployment target, dependencies, resources, coverage/debug-entitlement exclusion
and strict ad-hoc signature integrity were checked. ZIP extraction preserves
files, modes and links. App and Dock plugin dSYM UUIDs match their binaries.
Pinned Sparkle components retain additional ARM slices; this does not establish
ARM runtime support. Tooling and commands are in [RELEASE-INTEL.md](RELEASE-INTEL.md).

The extracted application replaced `/Applications/Ghostty.app` after backing up
the previous application. Installed inventory matches the release manifest.
The unchanged installed app launched with temporary isolated configuration,
created a real 90x25 PTY and exited normally; normal LaunchServices startup
followed. User configuration was not edited. No security controls were disabled.

## Disclosed limits

- Expanded build-18465 testing was not fully green. One run passed scripting,
  renderer, resource, palette and lifecycle checks before a pixel helper failed
  to find exactly one visible window. A repeat failed waiting for terminal text.
  Causes remain unresolved, not established as harness-only failures. The user
  retained the freeze rather than expanding functional regression work.
- A build-18464 pixel diagnostic completed its assertions in 61.65 seconds,
  exceeding its former 60-second parent deadline. The test-only budget became
  180 seconds. That diagnostic is not a build-18465 pass.
- Historical 284 unit passes/six skips and 27 UI passes are candidate-test
  evidence, not reruns on the shipped binary. The fixed-width UI expectation and
  incomplete unfiltered Zig suite remain excluded from this release task.
- Native AppIntents/Shortcuts parity, arbitrary AX sub-cell/multiple-range writes,
  atomic snapshots during output, ARM/other OS and Japanese/Korean layout
  certification are not claimed. See [AX-AUTOMATION-WORK.md](AX-AUTOMATION-WORK.md).
- ReleaseLocal is ad-hoc signed, not Developer ID signed or notarized. Updates
  are manual, with no configured distributor update feed.

## Documentation after freeze

`main` was aligned with `macos12-v1.4.0` after publication. Later documentation
commits do not change the release tag, application build or acceptance identity.
This documentation cleanup requires no rebuild or repeated functional tests.
The pre-publication [FINAL-VERIFICATION.md](FINAL-VERIFICATION.md) and packaging
research remain historical evidence, not a new release backlog.
