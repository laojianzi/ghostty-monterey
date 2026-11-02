#!/usr/bin/env python3
"""Run the original unit suite on Intel Monterey through an isolated Xcode host.

Requires Xcode 14 / SDK 13, explicit Swift 5.10.1 and current Zig core/resources.
Does not run UI tests, install tools, or change the product build configuration.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT / "test/macos-compatibility/native-suite"


def commands(args, output):
    dependency = args.testing_package.resolve() if args.testing_package else output / "testing"
    result = []
    if not args.testing_package:
        command = [sys.executable, str(SUITE / "build-testing.py"),
                   "--swift", str(args.swiftc.absolute().with_name("swift")), "--output", str(dependency)]
        if args.skip_package_updates:
            command.append("--skip-update")
        result.append(("dependencies", command))
    prepare = [sys.executable, str(SUITE / "build-candidate.py"),
               "--swiftc", str(args.swiftc.absolute()), "--nu", str(args.nu.absolute()),
               "--core-root", str(args.core_root.resolve()), "--prepare-only",
               "--source-packages", str(args.source_packages.resolve()),
               "--output", str(output / "candidate")]
    result.append(("prepare", prepare))
    result.append(("xcode-unit", [sys.executable, str(SUITE / "build-xcode-unit.py"),
        "--candidate", str(output / "candidate"), "--testing-package", str(dependency),
        "--swiftc", str(args.swiftc.absolute()), "--output", str(output / "xcode"), "--hosted-test"]))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swiftc", required=True, type=Path, help="Explicit Swift 5.10.1 compiler")
    parser.add_argument("--nu", required=True, type=Path, help="Nushell used by the candidate build wrapper")
    parser.add_argument("--core-root", required=True, type=Path,
                        help="Current source tree with macos/GhosttyKit.xcframework and zig-out")
    parser.add_argument("--source-packages", required=True, type=Path,
                        help="Xcode SourcePackages cache with pinned Sparkle source/binary artifact")
    parser.add_argument("--testing-package", type=Path,
                        help="Reuse explicitly supplied pinned Testing objects; otherwise rebuild them")
    parser.add_argument("--skip-package-updates", action="store_true",
                        help="Skip remote refresh when rebuilding cached Testing sources")
    parser.add_argument("--output", required=True, type=Path, help="New directory outside the worktree")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Output must be outside the worktree")
    if output.exists():
        parser.error("Output already exists; use a fresh directory")
    for path in (args.swiftc, args.nu, args.core_root, args.source_packages):
        if not path.exists():
            parser.error("Missing prerequisite: " + str(path))
    if args.testing_package and not args.testing_package.is_dir():
        parser.error("Missing Testing package")
    output.mkdir(parents=True)
    pipeline = commands(args, output)
    report = {"scope": "Intel Monterey Xcode unit suite; no UI tests or release certification",
              "core_root": str(args.core_root.resolve()), "reused_testing": bool(args.testing_package),
              "commands": pipeline, "completed": [], "accepted": False}
    manifest = output / "result.json"
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    print("Artifacts:", output, flush=True)
    for stage, command in pipeline:
        print("Running:", stage, flush=True)
        # The child owns its bounded compiler/test invocation; do not time out
        # this parent independently and leave an unobserved Xcode build behind.
        with (output / (stage + ".log")).open("w") as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            report["failed_stage"] = stage
            report["exit"] = result.returncode
            manifest.write_text(json.dumps(report, indent=2) + "\n")
            raise RuntimeError(f"{stage} failed; inspect {output / (stage + '.log')}")
        report["completed"].append(stage)
        manifest.write_text(json.dumps(report, indent=2) + "\n")
    tests = json.loads((output / "xcode/result.json").read_text())
    report["accepted"] = (tests["tests_executed"] and tests["tests"]["accepted"]
                          and tests["xctest_scaffold_count"] == 1)
    report["unit_result"] = tests
    manifest.write_text(json.dumps(report, indent=2) + "\n")
    if not report["accepted"]:
        raise RuntimeError("Unit result was not accepted")
    print("PASS: 284 named unit tests, six explicit skips, one Xcode-hosted scaffold; UI tests not run")


if __name__ == "__main__":
    main()
