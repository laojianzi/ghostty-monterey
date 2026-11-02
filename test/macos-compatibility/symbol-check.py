#!/usr/bin/env python3
"""Resolve bundled binaries' system imports against this Monterey host.

Does not load Ghostty, Sparkle, plugins or helper executables. This is a native
host-architecture check, not arm64 emulation, Objective-C selector validation,
or proof that availability guards protect every missing weak symbol.
"""

import argparse
import ctypes
import json
import pathlib
import platform
import re
import subprocess


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def symbol_available(library, symbol):
    # dlsym accepts C names, not the Mach-O ABI underscore.
    assert symbol.startswith("_"), symbol
    name = symbol[1:]
    try:
        # Subscription also resolves dunder names that CDLL.__getattr__ rejects.
        library[name]
        return True
    except AttributeError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert platform.system() == "Darwin" and platform.mac_ver()[0].split(".")[0] == "12", (
        "Run on Monterey: resolving newer-system symbols is not Monterey evidence")
    arch = platform.machine()
    assert arch in ("x86_64", "arm64"), arch
    app = args.app.resolve()
    assert (app / "Contents/MacOS/ghostty").is_file(), "Expected built app"
    libraries = {}
    report = {"os": platform.mac_ver()[0], "arch": arch, "app": str(app), "binaries": []}
    failures = []
    magic = {bytes.fromhex(x) for x in (
        "cafebabe", "bebafeca", "cafebabf", "bfbafeca", "cffaedfe", "feedfacf", "cefaedfe", "feedface")}

    # Positive and negative native resolution controls, not a mocked resolver.
    system = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    assert symbol_available(system, "_malloc")
    assert symbol_available(ctypes.CDLL(
        "/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation"), "___NSArray0__")
    assert not symbol_available(system, "_ghostty_monterey_missing_symbol_control_8a2789")
    # The assembler-named lazy binder is not exposed through C-name dlsym.
    # Check its actual shared-cache export and libSystem re-export instead.
    binder_export = bool(re.search(
        r"^\s+0x[0-9A-Fa-f]+\s+dyld_stub_binder\s*$",
        run("dyld_info", "-exports", "/usr/lib/system/libdyld.dylib"), re.MULTILINE))
    binder_reexport = bool(re.search(
        r"^\s+re-export\s+/usr/lib/system/libdyld.dylib\s*$",
        run("dyld_info", "-dependents", "/usr/lib/libSystem.B.dylib"), re.MULTILINE))
    assert binder_export and binder_reexport, "Missing native lazy binder export/re-export"

    for binary in sorted(app.rglob("*")):
        if binary.is_symlink() or not binary.is_file():
            continue
        with binary.open("rb") as stream:
            if stream.read(4) not in magic:
                continue
        assert arch in run("lipo", "-archs", str(binary)).split(), binary
        entry = {"path": str(binary.relative_to(app)), "required_resolved": 0,
                 "weak_resolved": 0, "missing_weak": [], "missing_required": [],
                 "unresolved_libraries": [], "bundled_imports_not_checked": []}
        dependencies = {}
        # otool's dependency names correspond to nm's two-level namespace
        # library labels. Reject collisions rather than searching a global scope.
        for line in run("otool", "-arch", arch, "-L", str(binary)).splitlines()[1:]:
            match = re.fullmatch(r"\s+(.+?) \(compatibility version .+\)", line)
            assert match, line
            path = match[1]
            label = pathlib.PurePosixPath(path).name.split(".")[0]
            assert label not in dependencies or dependencies[label] == path, (label, dependencies)
            dependencies[label] = path
            if not path.startswith(("/usr/lib/", "/System/Library/")):
                continue
            if path not in libraries:
                try:
                    libraries[path] = ctypes.CDLL(path)
                except OSError as error:
                    libraries[path] = str(error)
            if isinstance(libraries[path], str):
                weak = line.endswith(", weak)")
                entry["unresolved_libraries"].append({"path": path, "weak": weak, "error": libraries[path]})
                if not weak:
                    failures.append((entry["path"], "required library", path))

        for line in run("nm", "-arch", arch, "-m", "-u", str(binary)).splitlines():
            match = re.fullmatch(r"\s*\(undefined\) (weak )?external (\S+) \(from (\S+)\)", line)
            assert match, f"Unparsed import: {line}"
            weak, symbol, label = match.groups()
            assert label in dependencies, (binary, label)
            path = dependencies[label]
            item = {"library": path, "symbol": symbol}
            if not path.startswith(("/usr/lib/", "/System/Library/")):
                entry["bundled_imports_not_checked"].append(item)
                continue
            library = libraries[path]
            if symbol == "dyld_stub_binder":
                assert path == "/usr/lib/libSystem.B.dylib", path
                available = binder_export and binder_reexport
            else:
                available = not isinstance(library, str) and symbol_available(library, symbol)
            if available:
                entry["weak_resolved" if weak else "required_resolved"] += 1
            else:
                entry["missing_weak" if weak else "missing_required"].append(item)
                if not weak:
                    failures.append((entry["path"], "required symbol", item))
        report["binaries"].append(entry)
        print(f"{entry['path']}: {entry['required_resolved']} required / "
              f"{entry['weak_resolved']} weak resolved; {len(entry['missing_weak'])} weak absent; "
              f"{len(entry['bundled_imports_not_checked'])} bundled imports not checked")

    assert report["binaries"], "No Mach-O files found"
    report["failures"] = failures
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    assert not failures, failures
    print(f"PASS: required system imports resolve on {arch} macOS {report['os']}; "
          "missing weak symbols still require guarded-call review")


if __name__ == "__main__":
    main()
