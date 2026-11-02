#!/usr/bin/env python3
"""Package an already-built universal Monterey app without changing its signature.

Requires Python 3.9+ and macOS command-line tools. Does not build, sign, notarize,
upload, or certify release readiness. --development permits dirty local metadata
and visibly labels the artifact NOT-FOR-RELEASE.
"""

import argparse
import hashlib
import json
import os
import pathlib
import plistlib
import re
import stat
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
AUDIT = ROOT / "test/macos-compatibility/bundle-check.py"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(app):
    """Include modes and link targets, not just data (executables must stay executable)."""
    entries = {}
    for path in sorted(app.rglob("*")):
        mode = stat.S_IMODE(path.lstat().st_mode)
        name = path.relative_to(app).as_posix()
        if path.is_symlink():
            entries[name] = ["link", mode, os.readlink(path)]
        elif path.is_dir():
            entries[name] = ["directory", mode]
        elif path.is_file():
            entries[name] = ["file", mode, sha256(path)]
        else:
            raise ValueError(f"Unsupported filesystem object: {path}")
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path, help="New, non-existing directory")
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    if sys.flags.optimize:
        parser.error("Do not use python -O: bundle auditing requires assertions")
    app = args.app.resolve()
    output = args.output.resolve()
    if output.exists() or not output.parent.is_dir():
        parser.error("Output must not exist and its parent must be a directory")
    if output.is_relative_to(app):
        parser.error("Output must not be inside the app")
    audit = [sys.executable, str(AUDIT)]
    if not args.development:
        audit.append("--release")
    subprocess.run([*audit, str(app)], check=True)
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    version = info["CFBundleShortVersionString"]
    build = info["CFBundleVersion"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or not re.fullmatch(r"\d+", build):
        parser.error("Build version metadata is not suitable for packaging")
    label = "-NOT-FOR-RELEASE" if args.development else ""
    name = f"Ghostty-macos12-{version}-{build}-universal{label}.zip"
    before = inventory(app)
    # Keep incomplete outputs out of the requested directory. Publish only after
    # extraction and signature/content checks; never overwrite an existing output.
    with tempfile.TemporaryDirectory(prefix=".ghostty-package-", dir=output.parent) as temporary:
        stage = pathlib.Path(temporary)
        archive = stage / name
        subprocess.run(["ditto", "-c", "-k", "--keepParent", "--norsrc", "--noextattr",
                        str(app), str(archive)], check=True)
        extracted = stage / "extracted"
        extracted.mkdir()
        subprocess.run(["ditto", "-x", "-k", str(archive), str(extracted)], check=True)
        restored = extracted / app.name
        if sorted(p.name for p in extracted.iterdir()) != [app.name]:
            raise ValueError("Unexpected archive root entries")
        subprocess.run([*audit, str(restored)], check=True)
        if inventory(restored) != before or inventory(app) != before:
            raise ValueError("Archive round trip changed data/modes/links, or source changed during packaging")
        manifest = {
            "format": 1,
            "development": args.development,
            "version": version,
            "build": build,
            "commit": info.get("GhosttyCommit"),
            "buildIdentity": info.get("GhosttyBuild"),
            "archive": name,
            "sha256": sha256(archive),
            "files": before,
            "limitations": "Static archive checks only; no notarization, update-cycle or runtime certification.",
        }
        manifest_path = stage / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        checksums = stage / "SHA256SUMS.txt"
        checksums.write_text(f"{sha256(archive)}  {name}\n{sha256(manifest_path)}  manifest.json\n")
        # mkdir is exclusive: a concurrent publisher cannot have its work replaced.
        output.mkdir()
        for path in (archive, manifest_path, checksums):
            path.rename(output / path.name)
    print(f"Packaged and round-trip verified: {output / name}")
    print("No release was published. Static validation is not production-readiness approval.")


if __name__ == "__main__":
    main()
