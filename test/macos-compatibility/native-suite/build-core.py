#!/usr/bin/env python3
"""Rebuild universal Monterey core/resources in an isolated source snapshot.

Only dependency source packages are reused; local/global compiled-object caches
start empty. Does not replace the worktree's xcframework or release app.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", required=True, type=Path)
    parser.add_argument("--dependency-cache", required=True, type=Path,
                        help="Existing Zig package source directory (usually ~/.cache/zig/p)")
    parser.add_argument("--output", required=True, type=Path, help="New directory outside the worktree")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1 or args.jobs > 8:
        parser.error("Use 1-8 jobs")
    zig = args.zig.resolve(strict=True)
    dependency_cache = args.dependency_cache.resolve(strict=True)
    if not dependency_cache.is_dir():
        parser.error("Dependency cache must be a directory of source packages")
    version = subprocess.check_output([str(zig), "version"], text=True).strip()
    if version != "0.17.0":
        parser.error("Expected the project's pinned Zig 0.17.0")
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Output must be outside the worktree")
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    source.mkdir()
    paths = subprocess.check_output(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT)
    inputs = {}
    for name in sorted(set(os.fsdecode(value) for value in paths.split(b"\0") if value)):
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("Unsafe source inventory entry: " + name)
        original = ROOT / relative
        if not original.exists() and not original.is_symlink():
            continue  # Preserve deliberate tracked deletions in the snapshot.
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if original.is_symlink():
            target = os.readlink(original)
            if not original.resolve().is_relative_to(ROOT):
                raise RuntimeError("Source symlink leaves repository: " + name)
            destination.symlink_to(target)
            inputs[name] = {"symlink": target}
        elif original.is_file():
            shutil.copy2(original, destination)
            inputs[name] = {"sha256": digest(original)}
            if digest(destination) != inputs[name]["sha256"]:
                raise RuntimeError("Source changed during copy: " + name)
        else:
            raise RuntimeError("Unsupported source inventory entry: " + name)
    global_cache = output / "global-cache"
    global_cache.mkdir()
    (global_cache / "p").symlink_to(dependency_cache, target_is_directory=True)
    command = [str(zig), "build", "-Demit-macos-app=false", "-Doptimize=ReleaseFast",
               "-Dxcframework-target=universal", "-Dversion-string=1.4.0-dev.monterey-probe",
               "--cache-dir", str(output / "local-cache"),
               f"-j{args.jobs}", "--summary", "all"]
    manifest = {"command": command, "version": version, "source_root": str(ROOT),
                "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "scope": "Dirty source snapshot; fresh compiled caches; reused dependency source packages",
                "dependency_source_cache": str(dependency_cache), "global_cache": str(global_cache), "files": inputs}
    (output / "inputs.json").write_text(json.dumps(manifest, indent=2) + "\n")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("ZIG_", "NIX_", "DYLD_", "GHOSTTY_"))}
    env["ZIG_GLOBAL_CACHE_DIR"] = str(global_cache)
    print("Artifacts:", output, flush=True)
    with (output / "build.log").open("w") as log:
        result = subprocess.run(command, cwd=source, env=env, stdout=log,
                                stderr=subprocess.STDOUT, timeout=3600)
    if result.returncode:
        raise RuntimeError("Core rebuild failed; inspect build.log")
    for name, metadata in inputs.items():
        path = source / name
        if "sha256" in metadata and digest(path) != metadata["sha256"]:
            raise RuntimeError("Source snapshot changed during build: " + name)
    framework = source / "macos/GhosttyKit.xcframework"
    archives = sorted(framework.rglob("*.a"))
    if len(archives) != 1:
        raise RuntimeError("Expected one universal core archive")
    arches = subprocess.check_output(["lipo", "-archs", str(archives[0])], text=True).split()
    if set(arches) != {"x86_64", "arm64"}:
        raise RuntimeError("Core archive is not universal")
    artifacts = [p for tree in (framework, source / "zig-out") for p in tree.rglob("*") if p.is_file()]
    report = {"exit": 0, "architectures": arches,
              "artifact_sha256": {str(p.relative_to(source)): digest(p) for p in artifacts}}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: universal core and {len(artifacts)} artifact files rebuilt", flush=True)


if __name__ == "__main__":
    main()
