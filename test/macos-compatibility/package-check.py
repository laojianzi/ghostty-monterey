#!/usr/bin/env python3
"""Test package round trips/refusal paths against an existing local build."""

import hashlib
import argparse
import json
import pathlib
import plistlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=pathlib.Path)
parser.add_argument("--architecture", choices=("universal", "x86_64"), default="universal")
parser.add_argument("--extended", action="store_true",
                    help="Also check resources, palette, lifecycle and pixels; requires existing AX/Screen Recording permission")
args = parser.parse_args()
app = args.app.resolve()
with tempfile.TemporaryDirectory(prefix="ghostty-package-check-", dir="/tmp") as directory:
    tmp = pathlib.Path(directory)
    output = tmp / "package"
    command = [sys.executable, str(ROOT / "macos/package-monterey.py"),
               "--development", "--architecture", args.architecture, str(app), str(output)]
    subprocess.run(command, check=True)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["development"] is True
    assert "NOT-FOR-RELEASE" in manifest["archive"]
    archive = output / manifest["archive"]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == manifest["sha256"]
    for line in (output / "SHA256SUMS.txt").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected

    # Refuse overwriting a destination even if all existing bytes happen to match.
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode != 0 and "Output must not exist" in result.stderr
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest

    # Explicitly refuse optimized Python, which would disable static assertions.
    result = subprocess.run([sys.executable, "-O", *command[1:-1], str(tmp / "optimized")],
                            capture_output=True, text=True)
    assert result.returncode != 0 and "Do not use python -O" in result.stderr
    assert not (tmp / "optimized").exists()

    info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    if info.get("GhosttyCommit", "").endswith("-dirty"):
        release_output = tmp / "release"
        result = subprocess.run([sys.executable, str(ROOT / "macos/package-monterey.py"),
                                 "--architecture", args.architecture, str(app), str(release_output)], capture_output=True, text=True)
        assert result.returncode != 0 and any(message in result.stderr for message in ("clean source", "Source/bundle mismatch")), result.stdout + result.stderr
        assert not release_output.exists(), "Rejected development build left release output"
        print("PASS: dirty development metadata refused for release packaging", flush=True)

    extracted = tmp / "extracted"
    subprocess.run(["ditto", "-x", "-k", str(archive), str(extracted)], check=True)
    smoke = subprocess.run([sys.executable, str(ROOT / "test/macos-compatibility/app-smoke.py"),
                            str(extracted / app.name), "--automation", "--automation-text",
                            "--automation-policy", "--clipboard-protocol",
                            "--renderer-stress", "--inspector"])

    # Keep GUI runs sequential: they use the same isolated identifier. Pixel
    # blank controls must not inherit renderer-stress's background/shader config.
    extended_results = []
    if args.extended and smoke.returncode == 0:
        extended_results.append(subprocess.run([
            sys.executable, str(ROOT / "test/macos-compatibility/resources-check.py"), str(extracted / app.name),
        ]))
        if extended_results[-1].returncode == 0:
            extended_results.append(subprocess.run([
                sys.executable, str(ROOT / "test/macos-compatibility/app-smoke.py"),
                str(extracted / app.name), "--palette", "--lifecycle", "--pixels",
            ]))

    # Damage only a disposable extraction after the smoke subprocess exits. The
    # original signed app and archive must remain unchanged.
    restored = extracted / app.name
    resource = restored / "Contents/Resources/Assets.car"
    assert resource.is_file()
    with resource.open("ab") as stream:
        stream.write(b"ghostty-package-test-tamper")
    rejected = tmp / "tampered"
    result = subprocess.run([sys.executable, str(ROOT / "macos/package-monterey.py"),
                             "--development", "--architecture", args.architecture, str(restored), str(rejected)], capture_output=True, text=True)
    assert result.returncode != 0 and "codesign" in result.stderr, result.stdout + result.stderr
    signature = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(restored)],
                               capture_output=True, text=True)
    assert signature.returncode != 0 and "sealed resource is missing or invalid" in signature.stderr, signature.stderr
    assert not rejected.exists(), "Tampered app left package output"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
    print("PASS: modified resource rejected before package output creation", flush=True)
    smoke.check_returncode()
    for result in extended_results:
        result.check_returncode()
    if args.extended:
        assert len(extended_results) == 2, "Extended acceptance did not finish"
        print("PASS: extracted archive resources, command palette, lifecycle and compositor checks")
    print("PASS: package checksums, non-overwrite/optimized-Python/tampered-signature refusal, extracted-app extended smoke")
