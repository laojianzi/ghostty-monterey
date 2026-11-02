#!/usr/bin/env python3
"""Reject debug entitlements in embedded binaries, not just the main app.

Re-signs only a disposable copy's Dock plugin and enclosing bundle. No installed
app, signing identities, keychain, permissions or original signature are changed.
"""

import argparse
import pathlib
import plistlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=pathlib.Path)
args = parser.parse_args()
original = args.app.resolve()
audit = [sys.executable, str(ROOT / "test/macos-compatibility/bundle-check.py")]
subprocess.run([*audit, str(original)], check=True)
with tempfile.TemporaryDirectory(prefix="ghostty-entitlements-check-", dir="/tmp") as directory:
    work = pathlib.Path(directory)
    app = work / original.name
    subprocess.run(["ditto", "--norsrc", str(original), str(app)], check=True)
    plugin = app / "Contents/PlugIns/DockTilePlugin.plugin"
    entitlements = work / "debug.plist"
    entitlements.write_bytes(plistlib.dumps({"com.apple.security.get-task-allow": True}))
    subprocess.run(["codesign", "--force", "--sign", "-", "--entitlements", str(entitlements),
                    str(plugin)], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)], check=True)
    # Require a valid signature: a rejection for a broken resource seal would
    # not prove the entitlement policy actually covers embedded code.
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    result = subprocess.run([*audit, str(app)], text=True, capture_output=True)
    assert result.returncode != 0 and "Debug entitlement in release binary" in result.stderr, (
        result.stdout, result.stderr)
    assert "DockTilePlugin" in result.stderr, result.stderr
    print("PASS: validly signed nested debug-entitlement mutant rejected")
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(original)], check=True)
