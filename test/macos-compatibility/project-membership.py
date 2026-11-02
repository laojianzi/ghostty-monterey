#!/usr/bin/env python3
"""Verify explicit Xcode memberships against the upstream synchronized groups.

Run on macOS with plutil. This checks membership, not compilation or OS support.
Pass a different upstream revision when updating the fork's upstream baseline.
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECT = "macos/Ghostty.xcodeproj/project.pbxproj"
BASELINE = "83fb95624"


def objects(data):
    result = subprocess.check_output(
        ["plutil", "-convert", "json", "-o", "-", "--", "-"], input=data
    )
    return json.loads(result)["objects"]


def main():
    baseline = sys.argv[1] if len(sys.argv) > 1 else BASELINE
    before = objects(subprocess.check_output(
        ["git", "show", baseline + ":" + PROJECT], cwd=ROOT
    ))
    after = objects((ROOT / PROJECT).read_bytes())
    groups = {
        key: group for key, group in before.items()
        if group["isa"] == "PBXFileSystemSynchronizedRootGroup"
    }
    for target_id, target in before.items():
        if target["isa"] != "PBXNativeTarget":
            continue
        expected = set()
        for group_id, group in groups.items():
            default = group_id in target.get("fileSystemSynchronizedGroups", [])
            exceptions = set()
            for exception_id in group.get("exceptions", []):
                exception = before[exception_id]
                if exception["target"] == target_id:
                    exceptions.update(exception["membershipExceptions"])
            directory = ROOT / "macos" / group["path"]
            for file in directory.rglob("*"):
                if file.suffix not in (".swift", ".m", ".mm", ".xib"):
                    continue
                relative = file.relative_to(directory).as_posix()
                if default != (relative in exceptions):
                    expected.add((group["path"], relative))
        actual = set()
        for phase_id in after[target_id]["buildPhases"]:
            for build_id in after[phase_id].get("files", []):
                reference = after[build_id].get("fileRef")
                if reference is None:
                    continue
                for group_id, group in groups.items():
                    if reference in after[group_id]["children"]:
                        member = (group["path"], after[reference]["path"])
                        if member in actual:
                            raise ValueError("Duplicate membership: " + repr(member))
                        actual.add(member)
        if expected != actual:
            raise ValueError(
                target["name"] + ": missing=" + repr(sorted(expected - actual))
                + ", extra=" + repr(sorted(actual - expected))
            )
        print(target["name"] + ": " + str(len(actual)) + " memberships verified")


if __name__ == "__main__":
    main()
