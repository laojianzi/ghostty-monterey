#!/usr/bin/env python3
"""Audit a universal Monterey bundle without launching or modifying it.

Checks static deployment/dependency properties, not symbol availability or runtime
correctness. --release additionally rejects placeholder release metadata.
"""

import argparse
import pathlib
import plistlib
import re
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def version(value):
    numbers = tuple(int(n) for n in value.split("."))
    return numbers + (0,) * (3 - len(numbers))


def load_commands(binary, arch):
    return re.split(r"\nLoad command \d+\n", run("otool", "-arch", arch, "-l", str(binary)))[1:]


def field(command, name):
    found = re.search(rf"^\s*{name}\s+(.+)$", command, re.MULTILINE)
    assert found, f"Missing {name} in {command}"
    return found[1].split(" (offset ")[0].strip()


def expand(path, loader, executable):
    return pathlib.Path(path.replace("@loader_path", str(loader)).replace(
        "@executable_path", str(executable)))


def audit(app, release=False):
    app = app.resolve()
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    assert version(info["LSMinimumSystemVersion"]) == (12, 0, 0), "Bundle minimum must be 12.0"
    assert info.get("NSAppleScriptEnabled") is True, "AppleScript support missing"
    assert (app / "Contents/Resources/Ghostty.sdef").is_file(), "Scripting dictionary missing"
    assert not list(app.rglob("*.xctest")), "Test bundles must not ship inside the app"
    assert not list(app.rglob("*.profraw")), "Profiling output must not ship"

    if release:
        assert re.fullmatch(r"\d+\.\d+\.\d+", info["CFBundleShortVersionString"]), "Placeholder version"
        assert re.fullmatch(r"[1-9]\d*", info["CFBundleVersion"]), "Invalid build number"
        assert info["CFBundleVersion"] != "1", "Placeholder build number"
        assert re.fullmatch(r"[0-9a-f]{40}", info.get("GhosttyCommit", "")), "Release requires a clean source revision"
        assert info.get("GhosttyBuild"), "Missing build identity"

    main = app / "Contents/MacOS" / info["CFBundleExecutable"]
    dock = app / "Contents/PlugIns/DockTilePlugin.plugin/Contents/MacOS/DockTilePlugin"
    assert main.is_file() and dock.is_file(), "Main executable or Dock plugin missing"
    magic = {bytes.fromhex(x) for x in (
        "cafebabe", "bebafeca", "cafebabf", "bfbafeca", "cffaedfe", "feedfacf", "cefaedfe", "feedface")}
    binaries = []
    for path in sorted(app.rglob("*")):
        if path.is_symlink():
            assert path.resolve().is_relative_to(app), f"Symlink escapes bundle: {path}"
            assert path.exists(), f"Broken symlink: {path}"
        elif path.is_file():
            with path.open("rb") as stream:
                if stream.read(4) in magic:
                    binaries.append(path)

    main_rpaths = {}
    for arch in ("x86_64", "arm64"):
        main_rpaths[arch] = [field(c, "path") for c in load_commands(main, arch)
                             if field(c, "cmd") == "LC_RPATH"]

    for binary in binaries:
        relative = binary.relative_to(app)
        assert set(run("lipo", "-archs", str(binary)).split()) == {"x86_64", "arm64"}, relative
        # Embedded XPC/Updater executables resolve @executable_path themselves,
        # whereas plugins/framework libraries are loaded by their host process.
        executable = binary.parent if binary.parent.name == "MacOS" and binary != dock else main.parent
        for arch in ("x86_64", "arm64"):
            entitlements = subprocess.check_output(
                ["codesign", "-d", "--arch", arch, "--entitlements", ":-", str(binary)],
                stderr=subprocess.DEVNULL,
            ).rstrip(b"\x00")
            entitlements = plistlib.loads(entitlements) if entitlements.strip() else {}
            assert entitlements.get("com.apple.security.get-task-allow") is not True, (
                relative, arch, "Debug entitlement in release binary")
            commands = load_commands(binary, arch)
            minima = []
            rpaths = [field(c, "path") for c in commands if field(c, "cmd") == "LC_RPATH"]
            for command in commands:
                kind = field(command, "cmd")
                if kind == "LC_BUILD_VERSION":
                    assert field(command, "platform") in ("1", "macos"), relative
                    minima.append(field(command, "minos"))
                elif kind == "LC_VERSION_MIN_MACOSX":
                    minima.append(field(command, "version"))
                elif kind in ("LC_LOAD_DYLIB", "LC_LOAD_WEAK_DYLIB", "LC_REEXPORT_DYLIB", "LC_LOAD_UPWARD_DYLIB"):
                    dependency = field(command, "name")
                    if dependency.startswith(("/usr/lib/", "/System/Library/")):
                        # System frameworks may live exclusively in the dyld
                        # shared cache; filesystem existence is not a valid test.
                        continue
                    assert dependency.startswith("@"), f"Non-system absolute dependency: {dependency}"
                    if dependency.startswith("@rpath/"):
                        suffix = dependency[len("@rpath/"):]
                        candidates = [expand(p, binary.parent, executable) / suffix for p in rpaths]
                        candidates += [expand(p, main.parent, main.parent) / suffix for p in main_rpaths[arch]]
                    else:
                        candidates = [expand(dependency, binary.parent, executable)]
                    assert any(p.is_file() and p.resolve().is_relative_to(app) for p in candidates), (
                        relative, arch, "Unresolved bundled dependency", dependency)
                elif kind in ("LC_SEGMENT", "LC_SEGMENT_64"):
                    assert not re.search(r"sectname __llvm_(?:prf|cov)", command), (
                        relative, arch, "Coverage instrumentation in release binary")
            assert len(minima) == 1 and version(minima[0]) <= (12, 0, 0), (relative, arch, minima)
        print(f"PASS: {relative} (universal, deployment <= 12.0, dependencies, no coverage)")

    assert main in binaries and dock in binaries
    run("codesign", "--verify", "--deep", "--strict", str(app))
    print(f"PASS: {len(binaries)} Mach-O files and strict bundle signature; not a runtime/notarization proof")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()
    audit(args.app, args.release)
