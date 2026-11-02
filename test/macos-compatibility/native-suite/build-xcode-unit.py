#!/usr/bin/env python3
"""Build, or explicitly run, the unit target with Xcode 14 in a candidate copy.

Does not modify the worktree/project/toolchain selection or run UI tests.
"""
import argparse
import json
from pathlib import Path
import plistlib
import runpy
import shlex
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
RUNNER = runpy.run_path(str(HERE / "run.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--testing-package", required=True, type=Path)
    parser.add_argument("--swiftc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hosted-test", action="store_true",
                        help="Run only the complete unit suite through Xcode's real app host")
    args = parser.parse_args()
    candidate = args.candidate.resolve(strict=True)
    package = args.testing_package.resolve(strict=True)
    swiftc = args.swiftc.absolute()
    candidate_inputs = json.loads((candidate / "build-inputs.json").read_text())
    core_root = Path(candidate_inputs["core_root"])
    verify_core = runpy.run_path(str(HERE / "core-inputs.py"))["verify"]
    core_provenance = verify_core(core_root, RUNNER["ROOT"])
    output = args.output.resolve()
    if output == RUNNER["ROOT"] or RUNNER["ROOT"] in output.parents:
        parser.error("Output must be outside the worktree")
    if "Swift version 5.10.1" not in subprocess.check_output([str(swiftc), "--version"], text=True):
        parser.error("Expected Swift 5.10.1")
    pins = json.loads((package / "Package.resolved").read_text())["pins"]
    if {p["identity"]: p["state"]["revision"] for p in pins} != RUNNER["PINS"]:
        parser.error("Testing dependency pins differ")
    for name, revision in RUNNER["PINS"].items():
        checkout = package / ".build/checkouts" / name
        head = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True)
        if head != revision or dirty:
            parser.error("Dependency checkout differs: " + name)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(candidate / "macos", output / "macos", symlinks=True)
    for name in ("include", "images", "zig-out"):
        (output / name).symlink_to((candidate / name).resolve(), target_is_directory=True)
    packages = output / "SourcePackages"
    shutil.copytree(candidate / "SourcePackages", packages, symlinks=True)
    state = packages / "workspace-state.json"
    state.write_text(state.read_text().replace(str(candidate / "SourcePackages"), str(packages)))
    subprocess.run(["git", "apply", str(HERE / "swift510-tests.patch")], cwd=output, check=True)
    if args.hosted_test:
        subprocess.run(["git", "apply", str(HERE / "xcode-hosted-tests.patch")], cwd=output, check=True)
    testing = package / ".build/debug"
    objects = sorted((testing / "Testing.build").glob("*.o"))
    objects += sorted((testing / "TestingInternals.build").glob("*.o"))
    if not objects:
        raise RuntimeError("Missing Testing objects")
    filelist = output / "Testing.LinkFileList"
    filelist.write_text("\n".join(str(p) for p in objects) + "\n")
    developer = Path(subprocess.check_output(["xcode-select", "-p"], text=True).strip())
    platform_dev = developer / "Platforms/MacOSX.platform/Developer"
    project = output / "macos/Ghostty.xcodeproj/project.pbxproj"
    data = json.loads(subprocess.check_output(["plutil", "-convert", "json", "-o", "-", str(project)]))
    entries = data["objects"]
    target = next(v for v in entries.values() if v.get("isa") == "PBXNativeTarget" and v["name"] == "GhosttyTests")
    phase = next(entries[k] for k in target["buildPhases"] if entries[k]["isa"] == "PBXSourcesBuildPhase")
    if len(phase["files"]) != 27:
        raise RuntimeError("Original unit target inventory changed")
    for index, name in enumerate(("NativeScaffolding.swift", "MontereySurfaceTransferTests.swift")):
        shutil.copy2(HERE / name, output / "macos/Tests" / name)
        reference, build_id = f"C012000000000000000000{index:02X}", f"C012000000000000000001{index:02X}"
        if reference in entries or build_id in entries:
            raise RuntimeError("Fixture identifier collision")
        entries[reference] = {"isa": "PBXFileReference", "lastKnownFileType": "sourcecode.swift",
                              "path": "Tests/" + name, "sourceTree": "SOURCE_ROOT"}
        entries[build_id] = {"isa": "PBXBuildFile", "fileRef": reference}
        phase["files"].append(build_id)
    for config in entries[target["buildConfigurationList"]]["buildConfigurations"]:
        settings = entries[config]["buildSettings"]
        settings["OTHER_SWIFT_FLAGS"] = ["$(inherited)", "-enable-bare-slash-regex",
                                         "-Xfrontend", "-load-plugin-executable", "-Xfrontend",
                                         str(testing / "TestingMacros") + "#TestingMacros"]
        settings["SWIFT_INCLUDE_PATHS"] = ["$(inherited)", str(testing), str(testing / "TestingInternals.build"),
                                           "$(BUILT_PRODUCTS_DIR)/include", "$(SRCROOT)/Sources/Helpers"]
        settings["LIBRARY_SEARCH_PATHS"] = ["$(inherited)", str(platform_dev / "usr/lib")]
        settings["OTHER_LDFLAGS"] = ["$(inherited)", "-Xlinker", "-filelist", "-Xlinker", str(filelist)]
    identity = "org.ghostty.xcode-unit." + str(uuid.uuid4())
    if args.hosted_test:
        app_target = next(v for v in entries.values() if v.get("isa") == "PBXNativeTarget" and v["name"] == "Ghostty")
        for config in entries[app_target["buildConfigurationList"]]["buildConfigurations"]:
            entries[config]["buildSettings"]["PRODUCT_BUNDLE_IDENTIFIER"] = identity
    project.write_bytes(plistlib.dumps(data))
    command = ["xcodebuild", "-project", str(project.parent), "-target", "GhosttyTests",
               "-configuration", "Debug", "-clonedSourcePackagesDirPath", str(packages),
               "-skipPackageUpdates", "-disableAutomaticPackageResolution",
               "SWIFT_EXEC=" + str(swiftc), "SYMROOT=" + str(output / "build"),
               "OBJROOT=" + str(output / "obj"), "ARCHS=x86_64", "ONLY_ACTIVE_ARCH=YES",
               "SWIFT_ACTIVE_COMPILATION_CONDITIONS=$(inherited) GHOSTTY_TEST_SDK13" +
               (" GHOSTTY_XCODE_HOSTED_TEST" if args.hosted_test else ""),
               "CLANG_COVERAGE_MAPPING=NO", "CLANG_COVERAGE_MAPPING_LINKER_ARGS=NO", "build"]
    if args.hosted_test:
        config = output / "host.config"
        config.write_text("initial-window = false\nwindow-save-state = never\n"
                          "command = /usr/bin/true\nshell-integration = none\n"
                          "clipboard-read = deny\nclipboard-write = deny\n"
                          "copy-on-select = none\ndesktop-notifications = false\n"
                          "auto-update = off\nconfirm-close-surface = false\n")
        scheme_path = project.parent / "xcshareddata/xcschemes/Ghostty.xcscheme"
        scheme = ET.parse(scheme_path)
        action = scheme.getroot().find("TestAction")
        action.set("shouldUseLaunchSchemeArgsEnv", "NO")
        plans = action.find("TestPlans")
        if plans is not None:
            action.remove(plans)
        testables = action.find("Testables")
        for testable in list(testables):
            if testable.find("BuildableReference").get("BlueprintName") != "GhosttyTests":
                testables.remove(testable)
            else:
                testable.set("parallelizable", "NO")
        environment = ET.SubElement(action, "EnvironmentVariables")
        for key, value in {
            "GHOSTTY_CONFIG_PATH": str(config), "GHOSTTY_USER_DEFAULTS_SUITE": identity + ".defaults",
            "GHOSTTY_CLEAR_USER_DEFAULTS": "YES", "XDG_CONFIG_HOME": str(output / "config"),
            "SWT_SF_SYMBOLS_ENABLED": "0", "NO_COLOR": "1",
            "XDG_CACHE_HOME": str(output / "cache"), "XDG_STATE_HOME": str(output / "state"),
            "GHOSTTY_RESOURCES_DIR": str(output / "build/Debug/Ghostty.app/Contents/Resources/ghostty"),
        }.items():
            ET.SubElement(environment, "EnvironmentVariable", key=key, value=value, isEnabled="YES")
        scheme.write(scheme_path, encoding="utf-8", xml_declaration=True)
        command[command.index("-target"):command.index("-target") + 2] = ["-scheme", "Ghostty"]
        command[-1:] = ["-destination", "platform=macOS,arch=x86_64", "-parallel-testing-enabled", "NO",
                        "-resultBundlePath", str(output / "Tests.xcresult"), "test"]
    sources = sorted((output / "macos/Sources").rglob("*.swift"))
    sources += sorted((output / "macos/Tests").rglob("*.swift"))
    inputs = sources + objects + [project, testing / "TestingMacros", testing / "Testing.swiftmodule"]
    if args.hosted_test:
        inputs += [scheme_path, config]
    hashes = {str(p): RUNNER["digest"](p) for p in inputs}
    (output / "inputs.json").write_text(json.dumps({"command": command, "sha256": hashes,
        "scope": "Xcode hosted unit test" if args.hosted_test else "Xcode unit target build only",
        "core_provenance": core_provenance,
        "bundle_identity": identity, "ui_tests": False}, indent=2) + "\n")
    print("Artifacts:", output, flush=True)
    with (output / "build.log").open("w") as log:
        result = subprocess.run(command, cwd=output, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
    if result.returncode:
        raise RuntimeError("Xcode unit target build failed; inspect build.log")
    if verify_core(core_root, RUNNER["ROOT"]) != core_provenance:
        raise RuntimeError("Core provenance changed during the Xcode action")
    for path in inputs:
        if RUNNER["digest"](path) != hashes[str(path)]:
            raise RuntimeError("Build input changed: " + str(path))
    bundles = list((output / "build/Debug").rglob("GhosttyTests.xctest/Contents/MacOS/GhosttyTests"))
    if len(bundles) != 1:
        raise RuntimeError("Expected exactly one unit-test bundle")
    compile_list = output / "obj/Ghostty.build/Debug/GhosttyTests.build/Objects-normal/x86_64/GhosttyTests.SwiftFileList"
    compiled = {Path(p).resolve() for p in shlex.split(compile_list.read_text())}
    expected = {p.resolve() for p in (output / "macos/Tests").rglob("*.swift")}
    if compiled != expected or len(expected) != 29:
        raise RuntimeError("Xcode did not compile the exact original-plus-fixture source inventory")
    report = {"exit": 0, "binary": str(bundles[0]),
        "sha256": RUNNER["digest"](bundles[0]), "unit_source_files": len(phase["files"]),
        "tests_executed": args.hosted_test}
    if args.hosted_test:
        report["tests"] = RUNNER["inspect_result"]((output / "build.log").read_text(), 0, "all")
        summary = json.loads(subprocess.check_output([
            "xcrun", "xcresulttool", "get", "--path", str(output / "Tests.xcresult"), "--format", "json"
        ], text=True))
        (output / "xcresult-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        metrics = summary.get("metrics", {})
        report["xctest_scaffold_count"] = int(metrics.get("testsCount", {}).get("_value", "0"))
        issues = summary.get("issues", {}).get("testFailureSummaries", {}).get("_values", [])
        if report["xctest_scaffold_count"] != 1 or issues:
            report["tests"]["accepted"] = False
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    if args.hosted_test and not report["tests"]["accepted"]:
        raise RuntimeError("Xcode exited 0 but exact test inventory was not confirmed")
    print("PASS: Xcode hosted unit suite" if args.hosted_test else
          "PASS: Xcode built 27 original unit sources and two native fixtures; no tests executed")


if __name__ == "__main__":
    main()
