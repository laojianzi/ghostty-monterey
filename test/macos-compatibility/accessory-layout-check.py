#!/usr/bin/env python3
"""Diagnose Monterey's native fullscreen accessory layout recursion.

Independent AppKit/SwiftUI control, not a Ghostty product acceptance test.
Requires an unlocked GUI session and temporarily switches Spaces. Does not
change preferences, capture pixels, or use private API. Dynamic mode currently
reproduces an OS layout warning; that warning is NOT an application pass waiver.
The regular-window control posts mouse events only within the probe process.
"""

import pathlib
import platform
import subprocess
import tempfile

source = pathlib.Path(__file__).with_name("accessory-layout-probe.swift")
warning = "It's not legal to call -layoutSubtreeIfNeeded"
with tempfile.TemporaryDirectory(prefix="ghostty-accessory-layout-") as directory:
    binary = pathlib.Path(directory) / "probe"
    subprocess.run(["xcrun", "swiftc", "-O", "-target", f"{platform.machine()}-apple-macosx12.0",
                    str(source), "-o", str(binary)], check=True)
    for label, arguments in (("static", ["--static"]), ("dynamic", []),
                             ("regular-interaction", ["--regular-interaction"]),
                             ("static-repeat", ["--static"])):
        result = subprocess.run([str(binary), *arguments], capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "PASS: hidden accessory releases titlebar space" in result.stdout, result.stdout
        assert "PASS: accessory re-expands to its original size" in result.stdout, result.stdout
        if label == "regular-interaction":
            for count in (1, 2):
                assert f"PASS: regular accessory button action {count}" in result.stdout, result.stdout
        observed = warning in result.stderr
        assert observed == (label == "dynamic"), result.stdout + result.stderr
        print(f"{label}: layout recursion warning={observed}; {result.stdout.strip()}", flush=True)
    # A working event-delivery control must fail if the real SwiftUI action is lost.
    mutant = pathlib.Path(directory) / "NoAction.swift"
    original = source.read_text()
    changed = original.replace("model.actions += 1", "_ = model.actions")
    assert changed != original
    mutant.write_text(changed)
    subprocess.run(["xcrun", "swiftc", "-O", "-target", f"{platform.machine()}-apple-macosx12.0",
                    str(mutant), "-o", str(binary)], check=True)
    result = subprocess.run([str(binary), "--regular-interaction"],
                            capture_output=True, text=True, timeout=20)
    # Optimized Swift need not print the precondition message; absence of the
    # first action marker plus a failing exit distinguishes this from a pass.
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Accessory visible/static size:" in result.stdout, result.stdout + result.stderr
    assert "PASS: regular accessory button action" not in result.stdout, result.stdout
    print("PASS: compiled no-action mutant rejected by regular interaction control", flush=True)
    print("REPRODUCED: dynamic native accessory layout recursion; not a product readiness pass")
