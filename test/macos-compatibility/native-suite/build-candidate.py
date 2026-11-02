#!/usr/bin/env python3
"""Build isolated Swift 5.10 test app objects using current prebuilt Zig inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import runpy
import shlex
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def library_link(output):
    build = output / "candidate-build/Debug"
    app_binary = build / "Ghostty.app/Contents/MacOS/ghostty"
    link = None
    for line in (output / "app-build.log").read_text().splitlines():
        if "/usr/bin/clang " not in line or "-filelist" not in line:
            continue
        args = shlex.split(line.strip())
        if "-o" in args and Path(args[args.index("-o") + 1]).resolve() == app_binary.resolve():
            link = args
    if link is None:
        raise RuntimeError("Cannot find actual app link command in build log")
    filelist = Path(link[link.index("-filelist") + 1])
    objects = filelist.read_text().splitlines()
    excluded = [name for name in objects if Path(name).name == "main.o"]
    if len(excluded) != 1:
        raise RuntimeError("Expected exactly one main.o; inspect actual link file list")
    library_objects = [name for name in objects if name not in excluded]
    new_list = output / "Ghostty.TestLibrary.LinkFileList"
    new_list.write_text("\n".join(library_objects) + "\n")
    link[link.index("-filelist") + 1] = str(new_list)
    link[link.index("-o") + 1] = str(build / "libGhosttyProbe.dylib")
    link += ["-dynamiclib", "-Xlinker", "-install_name", "-Xlinker", "@rpath/libGhosttyProbe.dylib"]
    for index, value in enumerate(link):
        if value.endswith("Ghostty_dependency_info.dat"):
            link[index] = str(output / "test-library-dependency.dat")
        elif value.endswith("Ghostty_lto.o"):
            link[index] = str(output / "test-library-lto.o")
    return link, excluded, library_objects


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swiftc", type=Path, required=True)
    parser.add_argument("--nu", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory outside the worktree")
    parser.add_argument("--prepare-only", action="store_true",
                        help="Prepare source inputs for Xcode unit testing without compiling app objects")
    parser.add_argument("--core-root", type=Path,
                        help="Explicit rebuilt source tree containing macos/GhosttyKit.xcframework and zig-out")
    parser.add_argument("--skip-package-updates", action="store_true",
                        help="Skip remote refresh of pinned Xcode packages (requires cached sources/artifacts)")
    parser.add_argument("--source-packages", type=Path,
                        help="Copy an existing Xcode SourcePackages cache into the isolated candidate")
    args = parser.parse_args()
    swiftc, nu = args.swiftc.absolute(), args.nu.absolute()
    if platform.system() != "Darwin" or platform.machine() != "x86_64":
        parser.error("Only the Intel Monterey candidate has been validated")
    version = subprocess.check_output([str(swiftc), "--version"], text=True)
    sdk_version = subprocess.check_output(["xcrun", "--sdk", "macosx", "--show-sdk-version"], text=True).strip()
    if "Swift version 5.10.1" not in version or not sdk_version.startswith("13."):
        parser.error("This isolated candidate requires Swift 5.10.1 and SDK 13")
    core_root = args.core_root.resolve(strict=True) if args.core_root else ROOT
    verifier = runpy.run_path(str(HERE / "core-inputs.py"))["verify"]
    core_provenance = verifier(core_root, ROOT)
    output = args.output.resolve()
    if output.resolve() == ROOT or ROOT in output.resolve().parents:
        parser.error("Output must be outside the worktree")
    output.mkdir(parents=True, exist_ok=False)
    packages = None
    if args.source_packages:
        original_packages = args.source_packages.resolve(strict=True)
        checkout = original_packages / "checkouts/Sparkle"
        pin_file = ROOT / "macos/Ghostty.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        pin = next(p for p in json.loads(pin_file.read_text())["pins"] if p["identity"] == "sparkle")
        revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True)
        if revision != pin["state"]["revision"] or dirty:
            parser.error("SourcePackages must contain a clean checkout at the pinned Sparkle revision")
        packages = output / "SourcePackages"
        shutil.copytree(original_packages, packages, symlinks=True)
        state = packages / "workspace-state.json"
        state.write_text(state.read_text().replace(str(original_packages), str(packages)))
    if not (core_root / "macos/GhosttyKit.xcframework").is_dir() or not (core_root / "zig-out").is_dir():
        parser.error("Core input tree must contain the framework and installed resources")
    macos = output / "macos"
    macos.mkdir()
    for item in (ROOT / "macos").iterdir():
        if item.name in ("Sources", "Tests", "GhosttyUITests", "Assets.xcassets", "Ghostty.xcodeproj"):
            shutil.copytree(item, macos / item.name)
        elif item.is_file() and item.suffix in (".plist", ".entitlements", ".sdef", ".nu"):
            shutil.copy2(item, macos / item.name)
    for name in ("images", "include"):
        (output / name).symlink_to(ROOT / name, target_is_directory=True)
    (output / "zig-out").symlink_to(core_root / "zig-out", target_is_directory=True)
    (macos / "GhosttyKit.xcframework").symlink_to(core_root / "macos/GhosttyKit.xcframework", target_is_directory=True)
    commands = []

    def run(command, log_name, timeout):
        command = [str(value) for value in command]
        commands.append(command)
        (output / "build-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        with (output / log_name).open("w") as log:
            subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)

    run(["git", "apply", HERE / "swift510-app.patch"], "candidate-patch.log", 30)
    wrapper = (macos / "build.nu").read_text()
    replacements = {
        'let build_dir = ($env.FILE_PWD | path join "build")':
            'let build_dir = ($env.FILE_PWD | path dirname | path join "candidate-build")',
        'let root = ($env.FILE_PWD | path dirname)': 'let root = ' + json.dumps(str(ROOT)),
        '        ...$coverage': '\n'.join([
            '        ' + json.dumps('SWIFT_EXEC=' + str(swiftc)),
            '        ' + json.dumps('OBJROOT=' + str(output / 'candidate-obj')),
            '        "OTHER_SWIFT_FLAGS=$(inherited) -D GHOSTTY_TEST_SDK13"',
            *(['        -skipPackageUpdates', '        -disableAutomaticPackageResolution']
              if args.skip_package_updates or packages else []),
            *(['        -clonedSourcePackagesDirPath ' + json.dumps(str(packages))] if packages else []),
            '        ...$coverage',
        ]),
    }
    for before, after in replacements.items():
        if wrapper.count(before) != 1:
            raise RuntimeError("Build wrapper changed; review candidate adaptation: " + before)
        wrapper = wrapper.replace(before, after)
    (macos / "build.nu").write_text(wrapper)
    inputs = sorted((macos / "Sources").rglob("*.swift"))
    inputs += sorted(p for tree in (core_root / "macos/GhosttyKit.xcframework", core_root / "zig-out")
                     for p in tree.rglob("*") if p.is_file())
    inputs += [macos / "build.nu", macos / "Ghostty.xcodeproj/project.pbxproj", HERE / "swift510-app.patch"]
    if packages:
        inputs += sorted(p for p in (packages / "artifacts").rglob("*") if p.is_file())
    before = {str(path): digest(path) for path in inputs}
    manifest = {"compiler": version, "sdk": sdk_version, "source_root": str(ROOT),
                "core_root": str(core_root),
                "core_provenance": core_provenance,
                "skip_package_updates": args.skip_package_updates or packages is not None,
                "source_packages": str(args.source_packages) if packages else None,
                "scope": "Fresh candidate app objects; explicit core/resource inputs, not a clean release build",
                "inputs_sha256": before}
    (output / "build-inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.prepare_only:
        print("PREPARED: candidate sources only; no app compilation or tests")
        return
    run([nu, macos / "build.nu", "--configuration", "Debug"], "app-build.log", 1200)
    if verifier(core_root, ROOT) != core_provenance:
        raise RuntimeError("Core provenance changed during compilation")
    for path in inputs:
        if digest(path) != before[str(path)]:
            raise RuntimeError("Build input changed during compilation: " + str(path))
    build = output / "candidate-build/Debug"
    app_binary = build / "Ghostty.app/Contents/MacOS/ghostty"
    link, excluded, library_objects = library_link(output)
    run(link, "test-library-link.log", 180)
    run([app_binary, "+version"], "app-version.log", 30)
    result = {"app_sha256": digest(app_binary),
              "library_sha256": digest(build / "libGhosttyProbe.dylib"),
              "excluded_objects": excluded, "linked_objects": len(library_objects)}
    (output / "build-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
