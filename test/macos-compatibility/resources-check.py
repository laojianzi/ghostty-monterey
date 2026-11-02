#!/usr/bin/env python3
"""Check upstream resource retention and relocated bundle resource discovery.

Uses the current zig-out/share as build-input evidence, not as proof that those
inputs were freshly generated. Runs CLI subcommands only, with isolated config
and no GHOSTTY_RESOURCES_DIR override. Does not launch the GUI or install files.
"""

import argparse
import hashlib
import json
import pathlib
import plistlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROJECT = "macos/Ghostty.xcodeproj/project.pbxproj"
BASELINE = "83fb95624b0439ee660c2679b43b38c8b63769cd"


def resource_folders(data):
    objects = json.loads(subprocess.check_output(
        ["plutil", "-convert", "json", "-o", "-", "--", "-"], input=data
    ))["objects"]
    target = next(value for value in objects.values()
                  if value["isa"] == "PBXNativeTarget" and value["name"] == "Ghostty")
    folders = {}
    for phase in target["buildPhases"]:
        if objects[phase]["isa"] != "PBXResourcesBuildPhase":
            continue
        for item in objects[phase].get("files", []):
            reference = objects[objects[item]["fileRef"]]
            path = reference.get("path", "")
            if path.startswith("../zig-out/share/"):
                folders[reference["name"]] = path
    assert folders, "No generated resources in Xcode project"
    return folders


def inventory(directory):
    assert directory.is_dir(), f"Missing resource directory: {directory}"
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            assert path.resolve().is_relative_to(directory.resolve()), f"External resource link: {path}"
            result[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert result, f"Empty resource directory: {directory}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    args = parser.parse_args()
    app = args.app.resolve()
    baseline = resource_folders(subprocess.check_output(["git", "show", f"{BASELINE}:{PROJECT}"], cwd=ROOT))
    current = resource_folders((ROOT / PROJECT).read_bytes())
    assert current == baseline, ("Generated resource membership differs from official 1.4", baseline, current)
    resources = app / "Contents/Resources"
    total = 0
    for name, source in current.items():
        expected = inventory((ROOT / "macos" / source).resolve())
        actual = inventory(resources / name)
        assert actual == expected, (
            name, "missing", sorted(expected.keys() - actual.keys()),
            "extra", sorted(actual.keys() - expected.keys()),
            "different", [key for key in expected.keys() & actual.keys() if expected[key] != actual[key]])
        total += len(actual)
    print(f"PASS: {len(current)} official resource folders, {total} exact build-input file hashes", flush=True)

    scripts = inventory(ROOT / "src/shell-integration")
    scripts.pop("README.md")
    assert inventory(resources / "ghostty/shell-integration") == scripts, (
        "Bundled integration scripts differ from the current source (possibly stale zig-out)")
    assert (resources / "Ghostty.sdef").read_bytes() == (ROOT / "macos/Ghostty.sdef").read_bytes()
    print(f"PASS: {len(scripts)} integration scripts and scripting dictionary match current source", flush=True)

    with tempfile.TemporaryDirectory(prefix="ghostty-resource-check-", dir="/tmp") as directory:
        work = pathlib.Path(directory).resolve()
        relocated = work / "Relocated Ghostty.app"
        subprocess.run(["ditto", "--norsrc", str(app), str(relocated)], check=True)
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(relocated)], check=True)
        home = work / "home"
        home.mkdir()
        environment = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / "config"),
                       "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8"}
        info = plistlib.loads((relocated / "Contents/Info.plist").read_bytes())
        binary = relocated / "Contents/MacOS" / info["CFBundleExecutable"]

        def cli(*arguments):
            return subprocess.run([str(binary), *arguments], cwd=work, env=environment,
                                  text=True, capture_output=True, timeout=15)

        themes = relocated / "Contents/Resources/ghostty/themes"
        names = sorted(path.name for path in themes.iterdir() if path.is_file())
        result = cli("+list-themes", "--plain", "--path")
        assert result.returncode == 0, result.stdout + result.stderr
        assert set(result.stdout.splitlines()) == {
            f"{name} (resources) {themes / name}" for name in names
        }, "Theme listing did not resolve exclusively to the relocated bundle"
        print(f"PASS: relocated CLI discovers all {len(names)} bundled themes without resource override", flush=True)

        # Theme validation must exercise name lookup, not direct file loading.
        config = work / "theme-config"
        samples = names[::max(1, len(names) // 5)]
        for name in samples:
            config.write_text(f"theme = {name}\n")
            result = cli("+validate-config", f"--config-file={config}")
            assert result.returncode == 0, (name, result.stdout, result.stderr)
        config.write_text("theme = ghostty-resource-missing-control-5d229\n")
        result = cli("+validate-config", f"--config-file={config}")
        assert result.returncode != 0 and "ghostty-resource-missing-control-5d229" in result.stdout, result
        print(f"PASS: {len(samples)} named themes load; missing-theme negative control rejected", flush=True)

        for term in ("ghostty", "xterm-ghostty"):
            result = subprocess.run(
                ["/usr/bin/infocmp", "-A", str(relocated / "Contents/Resources/terminfo"), term],
                cwd=work, env=environment, text=True, capture_output=True, timeout=10,
            )
            assert result.returncode == 0 and "colors#256" in result.stdout, result
            assert str(relocated) in result.stdout, "infocmp used a system entry instead of the bundle"
        print("PASS: Monterey ncurses reads both relocated terminfo names; original signature unchanged")


if __name__ == "__main__":
    main()
