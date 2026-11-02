"""Source-bound ReleaseLocal preflight; does not modify or sign the app."""

import importlib.util
import pathlib
import plistlib
import re
import subprocess


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def source_identity(root):
    if git(root, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("Release requires full Git history")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Release requires a clean source checkout")
    version = re.search(r'\.version = "([^"]+)"', (root / "build.zig.zon").read_text())[1]
    return {"version": version, "commit": git(root, "rev-parse", "HEAD"),
            "build": git(root, "rev-list", "--count", "HEAD")}


def validate_metadata(info, identity):
    expected = {"CFBundleShortVersionString": identity["version"],
                "CFBundleVersion": identity["build"], "GhosttyCommit": identity["commit"],
                "GhosttyBuild": f'Monterey ReleaseLocal {identity["commit"]}'}
    for key, value in expected.items():
        if info.get(key) != value:
            raise ValueError(f"Source/bundle mismatch for {key}: {info.get(key)!r} != {value!r}")


def verify(root, app):
    identity = source_identity(root)
    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    validate_metadata(info, identity)
    raw = subprocess.check_output(
        ["codesign", "-d", "--entitlements", ":-", str(app)], stderr=subprocess.DEVNULL)
    entitlements = plistlib.loads(raw.rstrip(b"\0"))
    expected = plistlib.loads((root / "macos/GhosttyReleaseLocal.entitlements").read_bytes())
    if entitlements != expected:
        raise ValueError("ReleaseLocal entitlement profile differs from source")
    spec = importlib.util.spec_from_file_location(
        "release_resources", root / "test/macos-compatibility/resources-check.py")
    resources = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(resources)
    project = "macos/Ghostty.xcodeproj/project.pbxproj"
    folders = resources.resource_folders((root / project).read_bytes())
    baseline = subprocess.check_output(
        ["git", "-C", str(root), "show", f"{resources.BASELINE}:{project}"])
    if folders != resources.resource_folders(baseline):
        raise ValueError("Resource membership differs from official v1.4.0")
    for name, source in folders.items():
        if resources.inventory((root / "macos" / source).resolve()) != resources.inventory(app / "Contents/Resources" / name):
            raise ValueError(f"Bundled resource differs from build input: {name}")
    scripts = resources.inventory(root / "src/shell-integration")
    scripts.pop("README.md")
    if scripts != resources.inventory(app / "Contents/Resources/ghostty/shell-integration"):
        raise ValueError("Bundled shell integration differs from source")
    if (root / "macos/Ghostty.sdef").read_bytes() != (app / "Contents/Resources/Ghostty.sdef").read_bytes():
        raise ValueError("Bundled scripting dictionary differs from source")
    return identity
