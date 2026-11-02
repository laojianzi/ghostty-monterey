# Historical fork main packaging

## Scope and evidence

Research date: 2026-11-02. Historical baseline: `e975b2187a2c68465d0c660ca29bde935f885c99` (2026-09-10), referred to below as **M**. Findings concern this fork, not upstream Ghostty's current packaging. Source files were read from Git objects, not from modified working-tree product files. No builds, artifact downloads, signature checks, ref updates, commits, uploads, or issue/PR creation were performed. No other reports were read or changed.

Evidence classes used below:

- **Tracked recipe/configuration:** commands or settings actually committed at M. This establishes an inspectable, manually repeatable procedure, not a successful rerun or byte-for-byte reproducibility.
- **Maintainer claim:** verification or distribution statements in the README or release body. These are primary-source statements, not independently validated binary properties.
- **API observation:** GitHub release/tag metadata observed on the research date. Asset presence establishes publication, not how an asset was built or what is inside it.

The local origin URL is `https://github.com/laojianzi/ghostty.git`; its release API redirects to `laojianzi/ghostty-monterey`. Immutable source links below use the latter repository name.

## Main finding: a tracked manual recipe, not a release pipeline

M contains a substantial README recipe: build a universal ReleaseFast Zig framework, run six explicit Xcode builds, verify a bundle, create six ZIPs with `ditto`, and generate SHA-256 checksums. Thus it would be incorrect to say historical packaging is known **only** from published assets. It would also be incorrect to call this an automated, hermetic, or proven reproducible six-artifact pipeline. [S1]

At M, `.github/workflows/` contains only `macos-keyboard-compatibility.yml`, which runs native keyboard checks on `macos-15` and `macos-15-intel`; it does not build or publish the ZIP matrix. Commit `a28510594b15d31d3551d322bd4fcdea31dd5e3b` deleted the inherited release/publish workflows. Their presence in older ancestry is not evidence of an active fork packaging workflow at M. [S8, H6]

`macos/build.nu` is a general clean-environment Xcode wrapper (default configuration `Debug`), not the six-artifact packaging driver. The Zig Xcode integration maps non-Debug optimization modes to `ReleaseLocal`, handles universal/native architecture selection, and copies the app to the install path; it does not implement the README ZIP/checksum/release-metadata matrix. Plain `zig build -Doptimize=ReleaseFast` is therefore not equivalent to executing the documented distribution recipe. [S6, S7]

## Tracked architecture and output conventions

The README reports a verified host of macOS 12.7.6 with Xcode 14.1, Apple Swift 5.7.1, macOS 13 SDK, and Zig 0.15.2. These are maintainer verification claims; this research did not reproduce them. The project and Zig configuration both set the macOS minimum to 12.0. [S1 lines 5-12; S2; S9 lines 569-579]

The common prerequisite is exactly:

```sh
GHOSTTY_VERSION=1.3.1
GHOSTTY_BUILD=$(git rev-list --count HEAD)
GHOSTTY_COMMIT=$(git rev-parse --short HEAD)
zig build -Demit-macos-app=false -Doptimize=ReleaseFast -Dxcframework-target=universal
```

All six Xcode invocations use `-project macos/Ghostty.xcodeproj -target Ghostty`, `ONLY_ACTIVE_ARCH=NO`, the three metadata overrides, `CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO`, and `-quiet clean build`. The universal commands use an arm64 destination but do **not** set `ARCHS`; the intended universal result relies on Xcode's architecture defaults, rather than an explicit `ARCHS="arm64 x86_64"` argument. Single-architecture commands explicitly set `ARCHS=arm64` or `ARCHS=x86_64`, with matching destinations. [S1 lines 68-174]

Every path in the following table is relative to the repository root. Every archive is under `dist/`; each bundle path is `SYMROOT/configuration/Ghostty.app`. [S1 lines 78-174, 204-215]

| Configuration | Intended architecture | SYMROOT | ZIP basename |
| --- | --- | --- | --- |
| ReleaseLocal | universal: x86_64 + arm64 | `macos/build` | `Ghostty-macos12-releaselocal-universal.zip` |
| ReleaseLocal | arm64 | `macos/build-arm64-only-release` | `Ghostty-macos12-releaselocal-arm64.zip` |
| ReleaseLocal | x86_64 | `macos/build-x86_64-only-release` | `Ghostty-macos12-releaselocal-x86_64.zip` |
| Release | universal: x86_64 + arm64 | `macos/build-release` | `Ghostty-macos12-release-universal.zip` |
| Release | arm64 | `macos/build-release-arm64-only` | `Ghostty-macos12-release-arm64.zip` |
| Release | x86_64 | `macos/build-release-x86_64-only` | `Ghostty-macos12-release-x86_64.zip` |

This is a two-profile by three-architecture **documented build matrix**, not just a naming pattern inferred from assets. However, the supplied `lipo`/`vtool` verification commands target the main `Contents/MacOS/ghostty` executable in the universal ReleaseLocal bundle. They do not establish that every embedded framework/helper is thin in a single-architecture ZIP, nor provide an automated recursive six-bundle verification loop. [S1 lines 176-202]

## Version and signing conventions

- App marketing version: explicitly `1.3.1`, passed as `MARKETING_VERSION`; build number: `git rev-list --count HEAD`, passed as `CURRENT_PROJECT_VERSION`; commit: `git rev-parse --short HEAD`, passed as `GHOSTTY_COMMIT`. The README expects `CFBundleShortVersionString`, `CFBundleVersion`, and `GhosttyCommit` to expose those values. The committed plist also expands `GhosttyBuild` from `$(CURRENT_PROJECT_VERSION)`. This is build-time injection, not a documented post-signing plist rewrite. [S1 lines 71-74, 88-90, 192-202, 232; S3 lines 49-52]
- Git object checks independently give build counts **15220** at M and **15217** at `065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9`; the repository reports `--is-shallow-repository=false`. These counts match the corresponding release-body claims, but are not binary inspection. Short-hash length is not explicitly fixed by the README command. [G1, A1, A2]
- Both app configurations use ad-hoc identity `"-"`, an empty development team, automatic signing, and Hardened Runtime. Both are optimized: project Swift settings use whole-module compilation and `-O`; app target GCC optimization is `fast`. `ReleaseLocal` is not a Debug or unsigned profile. [S2 lines 1326-1434, 1724-1777, 1834-1886]
- `ReleaseLocal` selects `GhosttyReleaseLocal.entitlements`, including `com.apple.security.cs.disable-library-validation=true`. `Release` selects `Ghostty.entitlements`, which lacks that entitlement. The README recommends ReleaseLocal for ad-hoc distribution because bundled ad-hoc frameworks such as Sparkle lack a Team ID; it warns that the stricter Release profile may fail to launch on some standard macOS 12 systems. [S2; S4; S5; S1 lines 24-25, 43-46]
- Both profiles are described as ad-hoc signed and **not notarized**. Neither the name `Release` nor release prose about suitability for Developer ID workflows proves the distributed ZIPs are Developer ID-signed or notarized. The tracked recipe supplies no Developer ID identity, notarization submission, or stapling operation. README `codesign --verify --deep --strict` is a signature-integrity check in the recipe, not proof of notarization or a successful Gatekeeper assessment. [S1 lines 12, 56, 78-189; A1, A2 bodies]

### Important repeatability limitation: tag-sensitive Zig version detection

App plist version injection is separate from Zig's version detection. The README framework command does not pass `-Dversion-string`. At M, `GitVersion.detect` calls `git describe --exact-match --tags`; `Config.zig` rejects a detected non-`tip` tag unless it equals `v1.3.1`. The published `v1.3.1-monterey.1` tag resolves to M. Consequently, with that tag present and selected by Git, the literal documented framework command reaches the tagged-version panic. The tracked `-Dversion-string=1.3.1` option bypasses automatic detection, but is **not part of the historical README command** and is not evidence that the release producer used it. This is a source-level limitation identified without running a build; it prevents treating the recipe as unconditionally repeatable in today's tag state. [S9 lines 209-273; S10 lines 53-61; A4]

## ZIP and checksum conventions

The recipe uses `ditto -c -k --keepParent <bundle> dist/<name>.zip`, retaining the `Ghostty.app` parent directory. Filenames encode macOS compatibility target, lower-case configuration, and architecture, but **not** app version, build, or commit. Version differentiation resides in the release/tag and expected bundle metadata. The convention is ZIP, not a documented DMG or installer package. [S1 lines 204-215]

The checksum commands are exactly:

```sh
shasum -a 256 dist/Ghostty-macos12-*.zip > dist/SHA256SUMS.txt
shasum -a 256 -c dist/SHA256SUMS.txt
```

This records `dist/`-prefixed paths and covers any matching stale ZIPs as well as the intended six. The separate download instructions say `shasum -a 256 -c SHA256SUMS.txt`; that requires filenames/layout matching the manifest. The recipe does not document normalizing paths for flat release downloads or cleaning obsolete archives. No checksum asset contents were downloaded here, so actual published manifest paths remain unverified. Generated archives/checksums are explicitly release attachments rather than committed build outputs; ignore rules cover them and the relevant build directories. [S1 lines 31-52, 204-215; S11]

## Historical evolution in the fork

These changes are established by the named commits and their README/config diffs, not inferred from asset filenames:

| Commit | Packaging-relevant change |
| --- | --- |
| `05955ba08deb358f16c281dc8576b678a5427a60` | Initial compatibility README documents three Release ZIPs named `Ghostty-macos12-{universal,arm64,x86_64}.zip`, with no profile component. [H1] |
| `fc1dce7e81a9313b26495d98739303660a2d2f2b` | Adds explicit version/build/commit build settings to the recipe and build-setting expansion to `GhosttyBuild`/`GhosttyCommit`. [H2] |
| `95de1468158f86c37c3960b2ca1c9a52d56aa958` | Changes the documented ad-hoc builds to ReleaseLocal, initially retaining the old profile-less ZIP names. [H3] |
| `097bfdaee4a80f813a11d03dd6f8630322d9b29b` | Removes embedded checksum literals from the README; checksum authority moves to release artifacts. [H4] |
| `065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9` | Documents both profiles and all six explicitly profile-named ZIPs. This is the fork's `v1.3.1` tag target, not the earlier upstream `1.3.1` commit `332b2aefc6e72d363aa93ab6ecfc86eeeeb5ed28`. [H5, A3, G2] |
| `a28510594b15d31d3551d322bd4fcdea31dd5e3b` | Deletes inherited workflows including `publish-tag.yml`, `release-tag.yml`, and `release-tip.yml`. [H6] |
| `43073526547fede186a0a0d080b8a4684735242d` | Adds `macos/build-release*` to ignore rules. [H7] |

The README's final packaging revision is H5 and remains unchanged at M; M adds the keyboard-check workflow, not a new packaging workflow. [G3, S8]

## What published releases establish, and what they do not

The read-only release list API returned two releases. Both have the six ZIP basenames in the architecture table plus `SHA256SUMS.txt`. Both are non-draft, non-prerelease, and list `target_commitish="main"`. Tag-ref APIs independently resolve their exact commit targets; `target_commitish` alone would not do so. [A1-A4]

| Release | Release ID | Published UTC | Tag target | Release-body metadata claim |
| --- | --- | --- | --- | --- |
| `v1.3.1` | `320472301` | 2026-05-11 13:15:43 | `065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9` | version `1.3.1`, build `15217`, commit `065a421e5`, minimum macOS `12.0` |
| `v1.3.1-monterey.1` | `386363553` | 2026-09-10 14:36:33 | M | version `1.3.1`, build `15220`, commit `e975b2187`, minimum macOS `12.0` |

The later release body explicitly defines `v1.3.1-monterey.N` as upstream version + compatibility identifier + patch iteration. That is a **release-body naming convention**, not an implemented Zig tag parser or an instruction to set `MARKETING_VERSION=1.3.1-monterey.1`. Both bodies recommend ReleaseLocal and describe ad-hoc, non-notarized distribution. [A1, A2 bodies]

For an exact publication inventory at M's release, the API asset IDs and sizes are:

| Asset basename | Asset ID | Bytes |
| --- | --- | --- |
| `Ghostty-macos12-releaselocal-universal.zip` | `555231293` | 32462154 |
| `Ghostty-macos12-releaselocal-arm64.zip` | `555236792` | 24144668 |
| `Ghostty-macos12-releaselocal-x86_64.zip` | `555241478` | 24562730 |
| `Ghostty-macos12-release-universal.zip` | `555245734` | 32462294 |
| `Ghostty-macos12-release-arm64.zip` | `555250086` | 24144635 |
| `Ghostty-macos12-release-x86_64.zip` | `555253917` | 24562645 |
| `SHA256SUMS.txt` | `555231015` | 625 |

These are API observations from A2, not inspected binaries. Names and relative sizes are consistent with the documented matrix but do not prove Mach-O slices, metadata, nested signatures/entitlements, dependency versions, or minimum OS values. No build logs or provenance attestations tying those bytes to the recipe were examined. The release metadata was retrieved after publication and is mutable; A2 reports its release-body update time as `2026-09-11T00:30:58Z`, after M. Do not silently attribute all current release prose to the source snapshot at M.

## Exact primary-source references

All S references are immutable blobs at M; line numbers refer to those blobs, not the working tree.

- **S1:** [README.md](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/README.md), especially lines 5-56, 66-215, 232-237.
- **S2:** [macos/Ghostty.xcodeproj/project.pbxproj](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/Ghostty.xcodeproj/project.pbxproj), lines 1326-1434 (ReleaseLocal), 1724-1777 and 1834-1886 (Release).
- **S3:** [macos/Ghostty-Info.plist](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/Ghostty-Info.plist#L49), lines 49-52.
- **S4:** [macos/GhosttyReleaseLocal.entitlements](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/GhosttyReleaseLocal.entitlements), lines 1-22.
- **S5:** [macos/Ghostty.entitlements](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/Ghostty.entitlements), lines 1-20.
- **S6:** [macos/build.nu](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/build.nu), lines 1-32.
- **S7:** [src/build/GhosttyXcodebuild.zig](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/src/build/GhosttyXcodebuild.zig), lines 29-91, 168-178.
- **S8:** [workflow tree at M](https://github.com/laojianzi/ghostty-monterey/tree/e975b2187a2c68465d0c660ca29bde935f885c99/.github/workflows) and [macos-keyboard-compatibility.yml](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/.github/workflows/macos-keyboard-compatibility.yml), lines 1-30; also checked with `git ls-tree -r --name-only e975b2187 .github`.
- **S9:** [src/build/Config.zig](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/src/build/Config.zig), lines 209-273 and 569-579; [build.zig.zon](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/build.zig.zon), lines 1-6 (version 1.3.1 and minimum Zig 0.15.2).
- **S10:** [src/build/GitVersion.zig](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/src/build/GitVersion.zig), lines 53-61.
- **S11:** [.gitignore](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/.gitignore), lines 28-31; [macos/.gitignore](https://github.com/laojianzi/ghostty-monterey/blob/e975b2187a2c68465d0c660ca29bde935f885c99/macos/.gitignore), lines 1-5.
- **H1:** `05955ba08deb358f16c281dc8576b678a5427a60:README.md`, lines 26-40, 61-133; [commit](https://github.com/laojianzi/ghostty-monterey/commit/05955ba08deb358f16c281dc8576b678a5427a60).
- **H2:** [fc1dce7e81a9313b26495d98739303660a2d2f2b](https://github.com/laojianzi/ghostty-monterey/commit/fc1dce7e81a9313b26495d98739303660a2d2f2b), README and `macos/Ghostty-Info.plist` diffs.
- **H3:** [95de1468158f86c37c3960b2ca1c9a52d56aa958](https://github.com/laojianzi/ghostty-monterey/commit/95de1468158f86c37c3960b2ca1c9a52d56aa958), README diff.
- **H4:** [097bfdaee4a80f813a11d03dd6f8630322d9b29b](https://github.com/laojianzi/ghostty-monterey/commit/097bfdaee4a80f813a11d03dd6f8630322d9b29b), README diff.
- **H5:** [065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9](https://github.com/laojianzi/ghostty-monterey/commit/065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9), README diff.
- **H6:** [a28510594b15d31d3551d322bd4fcdea31dd5e3b](https://github.com/laojianzi/ghostty-monterey/commit/a28510594b15d31d3551d322bd4fcdea31dd5e3b), `.github/workflows/` deletions, verified with `git show --name-status a28510594 -- .github/workflows`.
- **H7:** [43073526547fede186a0a0d080b8a4684735242d](https://github.com/laojianzi/ghostty-monterey/commit/43073526547fede186a0a0d080b8a4684735242d), `.gitignore` diff.
- **G1:** Local object queries: `git rev-list --count e975b2187` -> `15220`; `git rev-list --count 065a421e5` -> `15217`; `git rev-parse --is-shallow-repository` -> `false`.
- **G2:** `git log e975b2187 --first-parent -20 --format='%H %s'` shows upstream `332b2aefc6e72d363aa93ab6ecfc86eeeeb5ed28` preceding H1; `git show-ref --tags` agrees with A3/A4 for the two published tags.
- **G3:** `git log e975b2187 --format='%H %s' -- README.md` identifies H5 as its latest change; `git log e975b2187 -- .github/workflows` identifies M as the keyboard-workflow addition after H6.
- **A1:** [release 320472301](https://api.github.com/repos/laojianzi/ghostty-monterey/releases/320472301), [release page](https://github.com/laojianzi/ghostty-monterey/releases/tag/v1.3.1).
- **A2:** [release 386363553](https://api.github.com/repos/laojianzi/ghostty-monterey/releases/386363553), [release page](https://github.com/laojianzi/ghostty-monterey/releases/tag/v1.3.1-monterey.1). A1/A2 were observed together through `curl -fsSL 'https://api.github.com/repos/laojianzi/ghostty/releases?per_page=100'`, following the repository redirect; relevant fields: `id`, `tag_name`, `target_commitish`, `published_at`, `updated_at`, `draft`, `prerelease`, `body`, and `assets[].{id,name,size}`.
- **A3:** [tag ref v1.3.1](https://api.github.com/repos/laojianzi/ghostty-monterey/git/ref/tags/v1.3.1), `object.type=commit`, `object.sha=065a421e5438cc8e6ee7fb8b71a3be3ebcbe88c9`.
- **A4:** [tag ref v1.3.1-monterey.1](https://api.github.com/repos/laojianzi/ghostty-monterey/git/ref/tags/v1.3.1-monterey.1), `object.type=commit`, `object.sha=e975b2187a2c68465d0c660ca29bde935f885c99`.
