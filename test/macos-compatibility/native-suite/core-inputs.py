"""Validate build-core snapshot evidence before consuming its framework/resources."""
import hashlib
import json
import os
from pathlib import Path
import subprocess


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def core_source(name):
    path = safe_relative(name)
    return (path.parts[0] in {"src", "pkg", "vendor", "include", "po", "images", "dist"}
            or name in {"build.zig", "build.zig.zon", "VERSION"})


def safe_relative(name):
    path = Path(name)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("Unsafe core manifest path: " + name)
    return path


def metadata(path):
    if path.is_symlink():
        return {"symlink": os.readlink(path)}
    return {"sha256": digest(path)}


def verify(core, current, names=None):
    core, current = core.resolve(), current.resolve()
    evidence = core.parent
    inputs, result = evidence / "inputs.json", evidence / "result.json"
    # A normal zig build does not emit the snapshot builder's provenance files.
    if core == current:
        return {"verified_snapshot": False, "reason": "Worktree build has no source-to-artifact manifest"}
    if not inputs.is_file() or not result.is_file():
        raise ValueError("External core requires build-core.py inputs.json and successful result.json")
    source = json.loads(inputs.read_text())
    built = json.loads(result.read_text())
    if built.get("exit") != 0 or set(built.get("architectures", [])) != {"x86_64", "arm64"}:
        raise ValueError("Core manifest does not report a successful universal build")
    if names is None:
        inventory = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=current)
        names = [os.fsdecode(p) for p in inventory.split(b"\0") if p]
    expected = {name: value for name, value in source["files"].items() if core_source(name)}
    present = {name for name in names if core_source(name)
               and ((current / name).exists() or (current / name).is_symlink())}
    if present != set(expected):
        raise ValueError("Core source inventory changed; rebuild the core snapshot")
    for name, value in expected.items():
        relative = safe_relative(name)
        if metadata(core / relative) != value or metadata(current / relative) != value:
            raise ValueError("Core source differs from build snapshot: " + name)
    artifacts = built["artifact_sha256"]
    actual = {str(p.relative_to(core)) for tree in (core / "macos/GhosttyKit.xcframework", core / "zig-out")
              for p in tree.rglob("*") if p.is_file()}
    if not actual or actual != set(artifacts):
        raise ValueError("Core artifact inventory differs from successful build")
    for name, expected_hash in artifacts.items():
        path = core / safe_relative(name)
        if not path.resolve().is_relative_to(core) or digest(path) != expected_hash:
            raise ValueError("Core artifact differs from successful build: " + name)
    return {"verified_snapshot": True, "source_files": len(expected), "artifact_files": len(artifacts),
            "inputs_sha256": digest(inputs), "result_sha256": digest(result),
            "scope": "Local manifest consistency, not trusted publisher or hermetic build attestation"}
