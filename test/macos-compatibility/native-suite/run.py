#!/usr/bin/env python3
"""Run real Testing against an explicitly supplied Swift 5.10 candidate build.

This does not build the app, install a toolchain, or run the Xcode UI action.
All generated files, patched test copies, and logs stay in a new output folder.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import uuid


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PINS = {
    "swift-testing": "8097dd8bcf7f2ed85f8aa8883635ce413012f53b",
    "swift-syntax": "2bc86522d115234d1f588efe2bcb4ce4be8f8b82",
}


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest()


def inspect_result(text, code, suite):
    passed = len(re.findall(r"^\u2714 Test (?!run with).* passed after", text, re.MULTILINE))
    skips = re.findall(r"^\u2718 Test .* skipped.*$", text, re.MULTILINE)
    summary = re.search(r"Test run with (\d+) tests? passed", text)
    expected_passes = 284 if suite == "all" else 1
    expected_skips = set()
    if suite == "all":
        expected_skips.add("\u2718 Test example() skipped.")
        for name in ("multipleTypesAreRegistered", "multipleTypesProvideCorrectData",
                     "pasteboardItemContainsExpectedType", "pasteboardItemIsCreated",
                     "pasteboardItemProvidesCorrectData"):
            expected_skips.add(f'\u2718 Test {name}() skipped: "Requires macOS 13"')
    valid = code == 0 and summary is not None and passed == expected_passes
    valid = valid and len(skips) == len(expected_skips) and set(skips) == expected_skips
    valid = valid and "Test actualSurfacePasteboardRoundTrip() passed after" in text
    valid = valid and "recorded an issue" not in text
    if summary:
        valid = valid and int(summary[1]) == passed + len(skips)
    return {"exit": code, "named_passes": passed, "skips": skips, "accepted": valid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swiftc", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path,
                        help="Temporary tree with macos/ and candidate-build/Debug/")
    parser.add_argument("--testing-package", required=True, type=Path,
                        help="Built SwiftPM package with the pinned Testing/Syntax dependencies")
    parser.add_argument("--output", required=True, type=Path, help="New, nonexistent artifact directory")
    parser.add_argument("--suite", choices=("all", "transfer"), default="all")
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "x86_64":
        parser.error("This candidate runner is currently validated only on Intel macOS")
    # swiftc is a symlink; resolving it changes the driver's argv[0] mode.
    swiftc = args.swiftc.absolute()
    if not swiftc.is_file():
        parser.error(f"Missing compiler: {swiftc}")
    candidate = args.candidate.resolve(strict=True)
    package = args.testing_package.resolve(strict=True)
    build = candidate / "candidate-build/Debug"
    testing = package / ".build/debug"
    developer = Path(subprocess.check_output(["xcode-select", "-p"], text=True).strip())
    platform_dev = developer / "Platforms/MacOSX.platform/Developer"
    sdk = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-path"], text=True).strip()
    version = subprocess.check_output([str(swiftc), "--version"], text=True)
    if "Swift version 5.10.1" not in version:
        parser.error("Expected the separately selected Swift 5.10.1 compiler")
    pins = json.loads((package / "Package.resolved").read_text())["pins"]
    if {p["identity"]: p["state"]["revision"] for p in pins} != PINS:
        parser.error("Testing/Syntax dependency revisions differ from the validated candidate")
    for name, revision in PINS.items():
        checkout = package / ".build/checkouts" / name
        actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip()
        if actual != revision or dirty:
            parser.error(f"Dependency checkout does not match its pin: {name}")
    required = [
        build / "libGhosttyProbe.dylib", build / "Ghostty.swiftmodule/x86_64-apple-macos.swiftmodule",
        build / "Ghostty.app/Contents/MacOS/ghostty", testing / "TestingMacros",
        testing / "Testing.swiftmodule", HERE / "swift510-tests.patch",
        platform_dev / "Library/Xcode/Agents/xctest",
    ]
    for path in required:
        if not path.is_file():
            parser.error(f"Missing prerequisite: {path}")
    objects = sorted((testing / "Testing.build").glob("*.o"))
    objects += sorted((testing / "TestingInternals.build").glob("*.o"))
    if not objects:
        parser.error("Missing compiled Testing objects")
    output = args.output.absolute()
    if ROOT == output.resolve() or ROOT in output.resolve().parents:
        parser.error("Use an output directory outside the worktree for isolated test patching")
    output.mkdir(parents=True, exist_ok=False)
    identity = "org.ghostty.native-suite." + str(uuid.uuid4())
    commands = []

    def run(command, name, timeout):
        command = [str(part) for part in command]
        commands.append(command)
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with (output / name).open("w") as log:
            return subprocess.run(command, cwd=output, env=env, stdout=log,
                                  stderr=subprocess.STDOUT, timeout=timeout).returncode

    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("DYLD_", "GHOSTTY_", "XCTest", "SWIFT_TESTING_"))
           and key not in ("TERMINFO", "TERMINFO_DIRS")}
    env.update({
        "GHOSTTY_RESOURCES_DIR": str(build / "Ghostty.app/Contents/Resources/ghostty"),
        "GHOSTTY_USER_DEFAULTS_SUITE": identity,
        "XDG_CONFIG_HOME": str(output / "config"), "XDG_CACHE_HOME": str(output / "cache"),
        "XDG_STATE_HOME": str(output / "state"),
    })
    sources = [HERE / "NativeScaffolding.swift", HERE / "MontereySurfaceTransferTests.swift"]
    originals = sorted((ROOT / "macos/Tests").rglob("*.swift"))
    if args.suite == "all":
        shutil.copytree(ROOT / "macos/Tests", output / "macos/Tests")
        patch = ["git", "apply", str(HERE / "swift510-tests.patch")]
        if run(patch, "patch.log", 30):
            raise RuntimeError("Candidate test patch no longer applies; inspect patch.log")
        sources += sorted((output / "macos/Tests").rglob("*.swift"))
        if len(sources) != len(originals) + 2:
            raise RuntimeError("Test-source inventory changed during preparation")
    bundle = output / "NativeTests.xctest/Contents"
    (bundle / "MacOS").mkdir(parents=True)
    (bundle / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": "NativeTests", "CFBundlePackageType": "BNDL",
        "CFBundleIdentifier": "org.ghostty.monterey-test-probe",
    }))
    host = output / "NativeTestHost.app"
    (host / "Contents/MacOS").mkdir(parents=True)
    executable = host / "Contents/MacOS/NativeTestHost"
    shutil.copy2(platform_dev / "Library/Xcode/Agents/xctest", executable)
    (host / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": "NativeTestHost", "CFBundlePackageType": "APPL",
        "CFBundleIdentifier": identity,
        "CFBundleName": "Ghostty Native Test Host", "CFBundleVersion": "1",
        "LSUIElement": True, "LSMinimumSystemVersion": "12.0",
    }))
    for name in ("Frameworks", "PrivateFrameworks"):
        (host / name).symlink_to(platform_dev / "Library" / name, target_is_directory=True)
    command = [swiftc, "-swift-version", "5", "-enable-bare-slash-regex", "-sdk", sdk,
               "-target", "x86_64-apple-macos12.0"]
    for path in (build, testing, build / "include", testing / "TestingInternals.build",
                 candidate / "macos/Sources/Helpers", platform_dev / "usr/lib"):
        command += ["-I", path]
    for path in (build, platform_dev / "Library/Frameworks"):
        command += ["-F", path]
    command += ["-load-plugin-executable", str(testing / "TestingMacros") + "#TestingMacros",
                "-emit-library", "-module-name", "GhosttyTests", *sources, *objects,
                "-o", bundle / "MacOS/NativeTests", "-L", build, "-lGhosttyProbe",
                "-framework", "Sparkle", "-framework", "XCTest", "-L", platform_dev / "usr/lib"]
    for path in (build, platform_dev / "Library/Frameworks", platform_dev / "usr/lib"):
        command += ["-Xlinker", "-rpath", "-Xlinker", path]
    app_sources = sorted((candidate / "macos/Sources").rglob("*.swift"))
    source_differences = []
    for path in app_sources:
        relative = path.relative_to(candidate)
        current = ROOT / relative
        if not current.is_file() or digest(path) != digest(current):
            source_differences.append(str(relative))
    manifest = {
        "suite": args.suite, "compiler": version, "candidate": str(candidate),
        "scope": "Candidate app objects; not ReleaseLocal, normal app startup or UI tests",
        "pins": PINS, "original_unit_source_count": len(originals),
        "candidate_source_differences": source_differences,
        "inputs_sha256": {str(p): digest(p) for p in required + originals + sources + objects + app_sources},
    }
    (output / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if run(command, "build.log", 600):
        raise RuntimeError("Test compilation failed; inspect build.log")
    code = run([executable, bundle.parent], "run.log", 240)
    text = (output / "run.log").read_text()
    result = inspect_result(text, code, args.suite)
    result["test_binary_sha256"] = digest(bundle / "MacOS/NativeTests")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if not result["accepted"]:
        raise RuntimeError("Runner failure or discovery/skip inventory changed; inspect run.log")


if __name__ == "__main__":
    main()
