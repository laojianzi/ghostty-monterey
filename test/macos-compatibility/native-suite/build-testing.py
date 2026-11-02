#!/usr/bin/env python3
"""Build pinned Testing dependencies in a fresh directory, without installing Swift."""
import argparse
import json
import os
from pathlib import Path
import platform
import runpy
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
RUNNER = runpy.run_path(str(HERE / "run.py"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swift", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory outside the worktree")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--skip-update", action="store_true",
                        help="Use cached source revisions without refreshing remote refs; not an offline guarantee")
    args = parser.parse_args()
    swift = args.swift.absolute()
    if args.jobs < 1 or args.jobs > 8:
        parser.error("Use 1-8 jobs to bound local resource use")
    if platform.system() != "Darwin" or platform.machine() != "x86_64":
        parser.error("This dependency build is validated only on Intel macOS")
    version = subprocess.check_output([str(swift), "--version"], text=True)
    if "Swift version 5.10.1" not in version:
        parser.error("Expected explicitly selected Swift 5.10.1")
    output = args.output.resolve()
    if output == RUNNER["ROOT"] or RUNNER["ROOT"] in output.parents:
        parser.error("Output must be outside the worktree")
    if output.exists():
        parser.error("Output must not exist; never reuse previous build objects")
    shutil.copytree(HERE / "testing-package", output)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("DYLD_", "SWIFT_", "NIX_"))
           and key not in ("SDKROOT", "TOOLCHAINS", "DEVELOPER_DIR")}
    command = [str(swift), "build", "--package-path", str(output), "--jobs", str(args.jobs)]
    if args.skip_update:
        command.append("--skip-update")
    manifest = {"compiler": version, "command": command, "pins": RUNNER["PINS"],
                "scope": "Fresh Testing/Syntax objects; no app or core build",
                "source_sha256": {str(p.relative_to(output)): RUNNER["digest"](p)
                                  for p in output.rglob("*.swift")}}
    (output / "build-inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with (output / "build.log").open("w") as log:
        result = subprocess.run(command, env=env, cwd=output, stdout=log,
                                stderr=subprocess.STDOUT, timeout=1800)
    if result.returncode:
        raise RuntimeError("Dependency build failed; inspect build.log")
    for name, expected in manifest["source_sha256"].items():
        if RUNNER["digest"](output / name) != expected:
            raise RuntimeError("Package source changed during compilation: " + name)
    pins = json.loads((output / "Package.resolved").read_text())["pins"]
    if {p["identity"]: p["state"]["revision"] for p in pins} != RUNNER["PINS"]:
        raise RuntimeError("Resolved dependency revisions differ from the pinned manifest")
    checkouts = {}
    for name, revision in RUNNER["PINS"].items():
        checkout = output / ".build/checkouts" / name
        actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain"], text=True).strip()
        if actual != revision or dirty:
            raise RuntimeError(f"Unexpected dependency checkout state: {name}")
        checkouts[name] = actual
    build = output / ".build/debug"
    artifacts = [build / "Testing.swiftmodule", build / "TestingMacros"]
    for target in ("Testing", "TestingInternals"):
        objects = sorted((build / (target + ".build")).glob("*.o"))
        if not objects:
            raise RuntimeError("Missing objects: " + target)
        artifacts += objects
    result = {"exit": 0, "checkouts": checkouts,
              "artifacts_sha256": {str(p.relative_to(output)): RUNNER["digest"](p) for p in artifacts}}
    (output / "build-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"PASS: {len(artifacts)} library/plugin/object artifacts built in {output}")


if __name__ == "__main__":
    main()
