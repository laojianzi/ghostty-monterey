# Recommended Monterey 1.4 packaging

Historical design snapshot. Intel tooling is now implemented in
[RELEASE-INTEL.md](RELEASE-INTEL.md) and the release is recorded in
[RELEASE-PUBLISHED.md](RELEASE-PUBLISHED.md). References to main, unimplemented
options and pending publication below describe the research-time state only.

2026-11-02. Design/research only: no source freeze, commit, tag, packaging-tool
change, app build or upload is performed by this investigation.

## Pinned primary sources

- Official v1.4.0 annotated tag resolves to
  `83fb95624b0439ee660c2679b43b38c8b63769cd` (tag object is not the source commit).
  Inspect `.github/workflows/release-tag.yml`, `publish-tag.yml`,
  `src/build/Config.zig` and the macOS Xcode project at that commit.
- Local fork main and origin/main both resolve to
  `e975b2187a2c68465d0c660ca29bde935f885c99`. Inspect `README.md`,
  `macos/build.nu`, `macos/GhosttyReleaseLocal.entitlements` and `.github/workflows/`.
- Published main release metadata:
  https://github.com/laojianzi/ghostty-monterey/releases/tag/v1.3.1-monterey.1
  API inspected: `/repos/laojianzi/ghostty-monterey/releases/tags/v1.3.1-monterey.1`.
  Assets confirm six ZIP variants and SHA256SUMS.txt; no asset binary was
  downloaded/re-audited in this investigation. target_commitish alone is not
  immutable build provenance. The release body identifies e975b2187/build15220.
- Current implementation: `macos/build.nu`, `macos/package-monterey.py`,
  `test/macos-compatibility/bundle-check.py`, `package-check.py`, `UPDATES.md`.

## Comparison

| Area | Official v1.4.0 | Fork main | Recommendation |
| --- | --- | --- | --- |
| Core/app | ReleaseFast Zig core; native Xcode Release | ReleaseFast; ReleaseLocal and Release | ReleaseFast core plus ReleaseLocal only |
| Architectures | Universal macOS app | Universal, arm64, x86_64 for both configurations | One x86_64 user package; do not promise ARM support |
| Bundle identity | Full-history commit count; version from tag; commit metadata | Same numbering model, metadata passed to Xcode | Preserve app 1.4.0, full source SHA and commit-count build; fork tag v1.4.0-monterey.1 |
| Container | DMG, app ZIP, separate dSYM ZIP | ditto ZIPs and checksums | ditto app ZIP, manifest, checksums; retain matching symbols separately |
| Signing | Developer ID nested signing; notarization and stapling | Ad-hoc; stricter Release has framework-loading warning | Existing ReleaseLocal ad-hoc mechanics, no Developer ID/notarization work |
| Updates | Signed Sparkle appcast, staged publication to R2 | Release attachments; not evidence of a working fork update service | Manual updates by default; preserve Sparkle code but no upstream feed |
| Publication | Build/upload and appcast promotion are separate workflows | README commands plus published release attachments | Local verified packaging first, separately authorized upload |

Official references: release-tag.yml setup lines 59-73, build-macos lines
173-291, appcast/upload jobs; publish-tag.yml checks staged assets before moving
the appcast to the live location. Official metadata is edited after the first
build and then the app is signed again. Our wrapper deliberately stamps metadata
before Xcode signing, avoiding any need to mutate the final bundle.

The main README documents the full six-variant command matrix and recommends
ReleaseLocal. Its build.nu is only an environment-clean Xcode wrapper; it does
not itself stamp versions, package ZIPs, run archive verification or publish.
The checked-in keyboard workflow is not a release-build workflow. Do not infer
a reproducible six-asset CI pipeline merely from the attached release files.

## Selected architecture and minimal tooling changes

Choose x86_64 because the user explicitly requires only this Intel host. The
current universal artifact is valid as a fallback distribution choice, but its
ARM slice is not runtime-tested. Keeping it just to avoid a small tooling change
would add bytes and imply a support matrix the user does not want.

Reuse the existing build/package/audit tools, with narrow changes before freeze:

1. Add an explicit architecture option to build.nu; for x86_64 pass ARCHS=x86_64
   and ONLY_ACTIVE_ARCH=NO consistently to app and plugin. Keep current defaults
   available for existing universal checks. Use Zig `-Dxcframework-target=native`
   only after asserting the build host is x86_64; native is host-relative.
2. Parameterize bundle-check.py's architecture contract. Require the executable
   and Dock plugin to match the selected architecture, and every bundled Mach-O
   to contain the supported slice. Pinned Sparkle binaries may retain universal
   slices; do not thin/re-sign them merely for cosmetic purity. Preserve minimum
   OS, dependency, entitlements, coverage, test-bundle and signature checks.
3. Make package naming/manifest reflect the inspected architecture and
   ReleaseLocal profile instead of hardcoding universal. Propagate the option
   through package-check.py and test wrong/missing architecture rejection.
4. Add source-bound release preflight: match bundle version, full SHA and build
   count against the selected clean checkout before/after build; check the
   ReleaseLocal identity/entitlement and current resource inventory. Today's
   --release checks a 40-hex metadata shape, not that it matches that checkout.
   Keep static bundle auditing distinct from source-provenance verification.

These are packaging/test changes, not a new application architecture or a
second release framework. None of the proposed options is implemented yet.
An Intel-only build is a new artifact and needs its own archive/runtime pass;
the current universal checksum and soak cannot simply be renamed to Intel.

## Frozen build and artifact contract

- Review and commit only intended product/tooling/docs changes. Do not blindly
  stage temporary evidence containing absolute machine paths. Logs are ignored
  by existing rules: explicitly decide which sanitized evidence to retain.
- Make a full-history clean checkout at the immutable selected revision in a
  fresh directory. Do not reuse the interactive worktree's zig-out, framework,
  Xcode products or test build directory. Dependency source/download caches may
  be reused with pinned versions; do not claim bit-for-bit reproducibility.
- Assert toolchain versions (Zig 0.17.0, Xcode14.1/Swift5.7.1/SDK13, compatible
  Nushell), host architecture, source SHA, version and full-history build number.
- Build core/resources, then the ReleaseLocal app through build.nu. Do not run
  tests that write generated outputs into this release staging tree. This avoids
  the terminfo/dummy-man drift found in FINAL-VERIFICATION.md.
- Pass `-Dversion-string=1.4.0` explicitly to Zig. Config.zig's automatic tag
  validation expects exactly v1.4.0, so the fork's v1.4.0-monterey.1 tag otherwise
  conflicts with detection. Keep fork revision in Git/plist/manifest, not by
  weakening upstream version validation. This also keeps core and app versions
  aligned; a shell GHOSTTY_VERSION assignment alone does not select this option.
- Audit the app and resource hashes; package to an external new directory,
  extract, compare contents/modes/symlinks and validate the extracted app.
  Never package all of macos/build/ReleaseLocal, which may contain test runners.
- Run representative extracted-artifact PTY/renderer/automation/AX tests on
  this host. Any rebuild invalidates the artifact identity and requires the
  corresponding gate again. Preserve full final bundle and ZIP hashes.
- Retain app and Dock plugin dSYMs separately, verifying UUIDs against shipped
  binaries with dwarfdump. Do not require Sentry or embed symbols/tests in app.
- Use release tag `v1.4.0-monterey.1`; keep CFBundleShortVersionString=1.4.0 and
  CFBundleVersion=full-history commit count. Review monotonicity before later
  releases, particularly after rebases. Tag creation/upload need authorization.

Proposed artifacts (names are a plan, not current script output):

```
Ghostty-macos12-1.4.0-monterey.1-<build>-releaselocal-x86_64.zip
manifest.json
SHA256SUMS.txt
RELEASE-NOTES.md
Ghostty-macos12-1.4.0-monterey.1-<build>-symbols.zip  # retained separately
```

The manifest should include upstream/fork revisions, release tag, app version,
build, configuration, supported/embedded architectures, toolchain versions,
bundle inventory, ZIP digest and artifact-matched acceptance references.
Checksums provide integrity comparison, not publisher authentication. Native
right-click Open guidance can be documented for Monterey; do not disable SIP,
Gatekeeper, or claim ad-hoc bundles are notarized/trusted automatically.

## Freeze versus public release

A release-candidate freeze is reasonable, but is not proof that all tests pass.
The fixed-width UI test change requested earlier was interrupted before editing;
it remains open. The unfiltered core test did not complete. Close those results
or explicitly document and approve their disposition before calling the release
fully accepted. The packaging design itself requires neither a commit nor
publication now. Do not remove NOT-FOR-RELEASE or rewrite dirty metadata on the
previously tested app to manufacture a clean release.

No need for six variants, a DMG/PKG installer, a new update backend, a cloud macOS
matrix or paid signing to meet the agreed ReleaseLocal distribution scope.

Further historical source/asset analysis: MAIN-PACKAGING-RESEARCH.md. Inherited
upstream release workflows are not the fork's new publishing entry point; do
not trigger them accidentally. The proposed suffixed tag does not match the
official release-tag push pattern, but any future automation should still use
explicit fork repository/tag guards and a separate publish approval.
