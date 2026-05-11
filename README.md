# Ghostty macOS 12 Compatibility Build

This branch provides a macOS 12-compatible Ghostty build for machines that cannot run newer macOS releases. The goal is to keep the macOS app buildable and usable on macOS 12 with all product behavior that macOS 12 can support.

## Compatibility Target

- Minimum supported macOS version: `12.0`
- Verified host: macOS 12.7.6
- Verified toolchain: Xcode 14.1, Apple Swift 5.7.1, macOS 13 SDK, Zig 0.15.2
- Verified app binaries: universal `x86_64 arm64`, arm64-only, and x86_64-only
- Build configuration: `ReleaseLocal` for ad-hoc GitHub/GitLab distribution
- Signing mode: ad-hoc signed, not notarized, with library validation disabled for bundled frameworks

## Current Status

The macOS 12 compatibility work is complete for the macOS app target.

- Zig ReleaseFast macOS framework build passes.
- Xcode `Release` app build passes.
- Xcode scheme test build passes under Xcode 14.1.
- `Ghostty.app` declares `LSMinimumSystemVersion = 12.0`.
- Mach-O load commands report `minos 12.0`.
- Codesign verification passes.
- Release bundles carry `com.apple.security.cs.disable-library-validation` so the bundled ad-hoc signed `Sparkle.framework` loads on macOS 12 Intel.
- App icon resources are present in Release builds.
- Release bundles include official-style version, build, and commit metadata.
- The About window identifies this build as a `ghostty-monterey` macOS 12 compatibility build.
- Manual product testing passed, including split drag-and-drop.

## Release Attachments

Generated release artifacts are not committed to git. Upload these files as GitHub/GitLab Release attachments:

- `dist/Ghostty-macos12-universal.zip`
- `dist/Ghostty-macos12-arm64.zip`
- `dist/Ghostty-macos12-x86_64.zip`
- `dist/SHA256SUMS.txt`

Verify downloaded artifacts with:

```sh
shasum -a 256 -c SHA256SUMS.txt
```

## User Install Note

These builds are ad-hoc signed and not notarized. macOS may block the first launch with an unidentified developer warning.

To open the app:

1. Right-click `Ghostty.app`.
2. Choose `Open`.
3. Confirm `Open` in the macOS dialog.

Alternatively, launch once, then allow the app in System Settings, Privacy & Security.

## Build And Verify

Regenerate the macOS framework:

```sh
GHOSTTY_VERSION=1.3.1
GHOSTTY_BUILD=$(git rev-list --count HEAD)
GHOSTTY_COMMIT=$(git rev-parse --short HEAD)

zig build -Demit-macos-app=false -Doptimize=ReleaseFast -Dxcframework-target=universal
```

Build the universal ad-hoc Release app:

```sh
xcodebuild \
  -project macos/Ghostty.xcodeproj \
  -target Ghostty \
  -configuration ReleaseLocal \
  -destination 'platform=macOS,arch=arm64' \
  SYMROOT="$PWD/macos/build" \
  ONLY_ACTIVE_ARCH=NO \
  MARKETING_VERSION="$GHOSTTY_VERSION" \
  CURRENT_PROJECT_VERSION="$GHOSTTY_BUILD" \
  GHOSTTY_COMMIT="$GHOSTTY_COMMIT" \
  CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO \
  -quiet clean build
```

Build single-architecture ad-hoc Release apps:

```sh
xcodebuild \
  -project macos/Ghostty.xcodeproj \
  -target Ghostty \
  -configuration ReleaseLocal \
  -destination 'platform=macOS,arch=arm64' \
  SYMROOT="$PWD/macos/build-arm64-only-release" \
  ARCHS=arm64 \
  ONLY_ACTIVE_ARCH=NO \
  MARKETING_VERSION="$GHOSTTY_VERSION" \
  CURRENT_PROJECT_VERSION="$GHOSTTY_BUILD" \
  GHOSTTY_COMMIT="$GHOSTTY_COMMIT" \
  CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO \
  -quiet clean build

xcodebuild \
  -project macos/Ghostty.xcodeproj \
  -target Ghostty \
  -configuration ReleaseLocal \
  -destination 'platform=macOS,arch=x86_64' \
  SYMROOT="$PWD/macos/build-x86_64-only-release" \
  ARCHS=x86_64 \
  ONLY_ACTIVE_ARCH=NO \
  MARKETING_VERSION="$GHOSTTY_VERSION" \
  CURRENT_PROJECT_VERSION="$GHOSTTY_BUILD" \
  GHOSTTY_COMMIT="$GHOSTTY_COMMIT" \
  CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO \
  -quiet clean build
```

Verify the universal app bundle:

```sh
APP=macos/build/ReleaseLocal/Ghostty.app

lipo -info "$APP/Contents/MacOS/ghostty"
plutil -extract LSMinimumSystemVersion raw "$APP/Contents/Info.plist"
plutil -extract CFBundleShortVersionString raw "$APP/Contents/Info.plist"
plutil -extract CFBundleVersion raw "$APP/Contents/Info.plist"
plutil -extract GhosttyCommit raw "$APP/Contents/Info.plist"
xcrun vtool -show-build -arch x86_64 "$APP/Contents/MacOS/ghostty"
xcrun vtool -show-build -arch arm64 "$APP/Contents/MacOS/ghostty"
codesign --verify --deep --strict "$APP"
codesign -d --entitlements :- "$APP"
```

Expected verification highlights:

- `lipo` reports `x86_64 arm64`.
- `LSMinimumSystemVersion` reports `12.0`.
- `CFBundleShortVersionString` reports the release version.
- `CFBundleVersion` reports the git commit count build number.
- `GhosttyCommit` reports the short git commit.
- The app entitlements include `com.apple.security.cs.disable-library-validation`.
- Both `vtool` checks report `minos 12.0`.
- Codesign verification exits successfully.

Package release attachments:

```sh
ditto -c -k --keepParent macos/build/ReleaseLocal/Ghostty.app dist/Ghostty-macos12-universal.zip
ditto -c -k --keepParent macos/build-arm64-only-release/ReleaseLocal/Ghostty.app dist/Ghostty-macos12-arm64.zip
ditto -c -k --keepParent macos/build-x86_64-only-release/ReleaseLocal/Ghostty.app dist/Ghostty-macos12-x86_64.zip
shasum -a 256 dist/Ghostty-macos12-universal.zip dist/Ghostty-macos12-arm64.zip dist/Ghostty-macos12-x86_64.zip > dist/SHA256SUMS.txt
shasum -a 256 -c dist/SHA256SUMS.txt
```

## Compatibility Work Completed

- Downgraded the Xcode project structure so Xcode 14 can open and build it.
- Lowered macOS deployment targets to `12.0` across Xcode and Zig build configuration.
- Added SDK 13 fallbacks for newer CoreVideo pixel format constants.
- Avoided Objective-C headers that Zig's Xcode 14 `translate-c` path cannot parse.
- Added a libc++ compatibility shim for the missing `__libcpp_verbose_abort` symbol.
- Backported or compiler-gated Swift 6 and newer macOS SDK usage.
- Marked AppIntents declarations with macOS availability gates while keeping them out of the Xcode 14 path.
- Replaced `CoreTransferable` split drag payload handling with an AppKit pasteboard path compatible with macOS 12.
- Kept AppKit-only pasteboard APIs out of non-AppKit targets.
- Restored macOS 12 focus metadata propagation for window title, represented directory, command palette targeting, and resize increments.
- Aligned shared surface focus timing on `Date` for AppKit and UIKit surface implementations.
- Added an AppKit fallback for search `Return` and `Shift+Return` navigation on macOS 12.
- Added a traditional `Ghostty.appiconset` so Xcode 14 generates Release app icons correctly.
- Added build setting expansion for `GhosttyBuild` and `GhosttyCommit` so Release bundles carry version metadata without post-signing plist mutation.
- Switched public ad-hoc artifacts to `ReleaseLocal`, preserving Release optimization while allowing bundled ad-hoc frameworks such as Sparkle to load on macOS 12 Intel.
- Updated the About window source links and text so this fork is clearly identified as `ghostty-monterey`, not the official upstream release channel.
- Adjusted the About metadata layout so version, build, commit, and source rows fit within the macOS 12 About window.
- Compiler-gated Swift Testing and UI test files so Xcode 14 can build the test scheme.
- Ignored generated Release artifacts and Xcode build directories so they remain Release attachments, not source files.

## Product Coverage

Manual testing passed for the P0 compatibility risks:

- Terminal app launch
- Window and surface focus behavior
- Search navigation, including keyboard return handling
- Command palette targeting
- Split drag-and-drop
- Universal and single-architecture Release app generation
- About window version/build/commit/source display

No macOS 12-supported product feature is currently known to be intentionally removed.

## Known Limitation

AppIntents and Shortcuts are not supported on macOS 12 because the underlying Apple system APIs start at macOS 13 or newer. Those implementations remain gated for newer macOS and newer Xcode toolchains, but are outside the macOS 12 compatibility target.

## Maintenance Notes

When syncing future upstream changes, check for:

- Xcode project format changes requiring Xcode 15 or 16.
- New Swift 6-only syntax or standard library APIs.
- New SwiftUI, AppKit, or AppIntents APIs with macOS 13+ availability.
- New SDK constants absent from the macOS 13 SDK.
- New `CoreTransferable` or Swift Testing dependencies in macOS 12 build paths.

After each upstream sync, rerun the build and verification commands above and repeat manual testing for focus, search, command palette, and split drag-and-drop.
