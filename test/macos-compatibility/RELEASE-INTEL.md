# Intel ReleaseLocal release procedure

This supersedes the unimplemented-tooling statements in PACKAGING-PLAN.md.
The user explicitly excludes closing the fixed-width UI expectation and the
incomplete unfiltered Zig suite from this release task. Those results remain
limitations, not passes. No product behavior is changed by this packaging work.

Use a clean full-history checkout in a new directory and Zig 0.17.0, Xcode 14.1,
Nushell 0.102.0, Python 3.9+ and pandoc on the Intel macOS 12 host:

```sh
zig build -Demit-macos-app=false -Doptimize=ReleaseFast -Dxcframework-target=native -Dversion-string=1.4.0 -Demit-docs=true --summary all
nu macos/build.nu --configuration ReleaseLocal --architecture x86_64 --release
python3 macos/package-monterey.py macos/build/ReleaseLocal/Ghostty.app /external/new-output --architecture x86_64 --release-tag v1.4.0-monterey.1
python3 test/macos-compatibility/package-check.py macos/build/ReleaseLocal/Ghostty.app --architecture x86_64 --extended
```

Record clean source identity before/after both builds. Do not reuse compiled
core/app outputs, alter a signed bundle's metadata, or run generating tests in
the release staging tree. Dependency download/source caches may be reused.
The packager verifies clean full history, version/SHA/count/build identity,
ReleaseLocal entitlements and current generated/source resource inventories
before and after round-trip extraction. This is local consistency verification,
not a cryptographic build attestation or bit-for-bit reproducibility claim.

App and Dock plugin must be Intel-only. Each bundled Mach-O must include Intel;
pinned Sparkle components may also contain an untested ARM slice. The supported
runtime remains Intel macOS 12, not all architectures embedded in dependencies.

Run resources, PTY/renderer/automation and AX checks against the extracted final
archive; private-ID fixture copies are explicitly distinguished from an unchanged
installed-app launch. Keep final hashes, toolchain versions, test reports and
matching app/plugin dSYM UUIDs. Keep symbols separately from the user app ZIP.

Back up /Applications/Ghostty.app before installing the verified extracted app.
Do not alter user configuration or disable Gatekeeper/SIP. This ad-hoc release
has no Developer ID/notarization or automatic update service. Publish explicit
assets through gh, not the inherited upstream release workflows. The release
notes must retain known test/platform limitations and manual update guidance.
