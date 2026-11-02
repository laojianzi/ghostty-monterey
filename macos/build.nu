#!/usr/bin/env nu

# Build the macOS Ghostty app using xcodebuild with a clean environment
# to avoid Nix shell interference (NIX_LDFLAGS, NIX_CFLAGS_COMPILE, etc.).

def main [
    --scheme: string = "Ghostty"       # Xcode scheme (Ghostty, DockTilePlugin)
    --configuration: string = "Debug"  # Build configuration (Debug, Release, ReleaseLocal)
    --action: string = "build"         # xcodebuild action (build, test, clean, etc.)
    --architecture: string = "universal" # universal or x86_64
    --release                         # Require a clean ReleaseLocal build
    --source-packages: string = ""     # Pinned Xcode dependency cache (not app objects)
    --update-key: string = ""          # Distributor's Sparkle Ed25519 public key
    --update-stable-url: string = ""   # HTTPS Monterey-only stable appcast
    --update-tip-url: string = ""      # HTTPS Monterey-only tip appcast
] {
    let project = ($env.FILE_PWD | path join "Ghostty.xcodeproj")
    let build_dir = ($env.FILE_PWD | path join "build")
    let root = ($env.FILE_PWD | path dirname)
    let package_flags = if $source_packages != "" {
        let pin = (open ($root | path join "macos/Ghostty.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")
            | get pins | where identity == "sparkle" | first | get state.revision)
        let checkout = ($source_packages | path join "checkouts/Sparkle")
        if (^git -C $checkout rev-parse HEAD | str trim) != $pin or ((^git -C $checkout status --porcelain | str trim) != "") {
            error make {msg: "Dependency cache must contain clean Sparkle at the locked revision."}
        }
        [-clonedSourcePackagesDirPath $source_packages -skipPackageUpdates -disableAutomaticPackageResolution]
    } else { [] }
    let arch_flags = if $architecture == "x86_64" {
        if (^uname -m | str trim) != "x86_64" {
            error make {msg: "The Monterey Intel build requires an x86_64 host."}
        }
        [ARCHS=x86_64 ONLY_ACTIVE_ARCH=NO]
    } else if $architecture == "universal" {
        ["ARCHS=x86_64 arm64" ONLY_ACTIVE_ARCH=NO]
    } else {
        error make {msg: "Architecture must be universal or x86_64."}
    }

    # A shallow clone silently undercounts CFBundleVersion and can break Sparkle
    # upgrade ordering. Require the same full history as upstream release jobs.
    if (^git -C $root rev-parse --is-shallow-repository | str trim) == "true" {
        error make {msg: "Build numbering requires full Git history; fetch --unshallow before building."}
    }

    # Stamp before Xcode signs the bundle. Match upstream's commit-count build
    # numbering, but identify uncommitted local builds honestly.
    let version = (open --raw ($root | path join "build.zig.zon")
        | parse --regex '\.version = "(?<version>[^"]+)"'
        | first | get version)
    let revision = (^git -C $root rev-parse HEAD | str trim)
    let build_number = (^git -C $root rev-list --count HEAD | str trim)
    let dirty = ((^git -C $root status --porcelain | str trim) != "")
    if $release and ($dirty or $configuration != "ReleaseLocal" or $action != "build") {
        error make {msg: "Release requires a clean checkout, ReleaseLocal configuration and build action."}
    }
    let commit = if $dirty { $"($revision)-dirty" } else { $revision }
    let build_identity = $"Monterey ($configuration) ($commit)"

    # Skip UI tests for CLI-based invocations because it requires
    # special permissions.
    let skip_testing = if $action == "test" {
        [-skip-testing GhosttyUITests]
    } else {
        []
    }

    # Keep coverage instrumentation out of shipped binaries. Test actions retain
    # their configured coverage settings.
    let coverage = if $action == "build" or $action == "archive" {
        [CLANG_COVERAGE_MAPPING=NO CLANG_COVERAGE_MAPPING_LINKER_ARGS=NO]
    } else {
        []
    }

    # Xcode 14 injects get-task-allow into ad-hoc ReleaseLocal builds unless
    # disabled explicitly. Preserve the checked-in entitlements for release
    # artifacts; Debug and test actions still support debugger attachment.
    let signing = if $configuration != "Debug" and ($action == "build" or $action == "archive") {
        [CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO]
    } else {
        []
    }

    (^env -i
        $"HOME=($env.HOME)"
        "PATH=/usr/bin:/bin:/usr/sbin:/sbin"
        xcodebuild
        -project $project
        -scheme $scheme
        -configuration $configuration
        $"SYMROOT=($build_dir)"
        $"MARKETING_VERSION=($version)"
        $"CURRENT_PROJECT_VERSION=($build_number)"
        $"GHOSTTY_COMMIT=($commit)"
        $"GHOSTTY_BUILD=($build_identity)"
        $"GHOSTTY_MONTEREY_UPDATE_KEY=($update_key)"
        $"GHOSTTY_MONTEREY_UPDATE_STABLE_URL=($update_stable_url)"
        $"GHOSTTY_MONTEREY_UPDATE_TIP_URL=($update_tip_url)"
        ...$coverage
        ...$package_flags
        ...$arch_flags
        ...$signing
        ...$skip_testing
        $action)
}
