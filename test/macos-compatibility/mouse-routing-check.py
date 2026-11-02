#!/usr/bin/env python3
"""Reproduce PID-targeted mouse routing independently of Ghostty on Monterey.

Uses only the probe's disposable window, internal positive-control events, and
PID-targeted events. No global input, preference edits, or permission prompts.
Successful reproduction is NOT acceptance of Ghostty's mouse input behavior.
"""

import pathlib
import platform
import subprocess
import tempfile
import time

source = pathlib.Path(__file__).with_name("mouse-routing-probe.swift")
with tempfile.TemporaryDirectory(prefix="ghostty-mouse-routing-") as directory:
    directory = pathlib.Path(directory)
    binary = directory / "probe"
    subprocess.run(["xcrun", "swiftc", "-target", f"{platform.machine()}-apple-macosx12.0",
                    str(source), "-o", str(binary)], check=True)
    output = directory / "target.log"
    with output.open("w") as stream:
        target = subprocess.Popen([str(binary)], stdout=stream, stderr=stream)
        try:
            deadline = time.monotonic() + 5
            while "WINDOW " not in output.read_text():
                assert target.poll() is None, output.read_text()
                assert time.monotonic() < deadline, "Probe did not create its window"
                time.sleep(0.05)
            sender = subprocess.run([str(binary), str(target.pid)], capture_output=True, text=True, timeout=5)
            assert sender.returncode == 0, sender.stdout + sender.stderr
            target.wait(timeout=10)
            assert target.returncode == 0, output.read_text()
        finally:
            if target.poll() is None:
                target.terminate()
                target.wait(timeout=5)
    result = output.read_text()
    assert "DOWN (150.0, 100.0)" in result and "UP (150.0, 100.0)" in result, result
    for kind in (1, 6, 2):
        assert f"TARGETED {kind} 0\n" in result, result
    print(result.strip())
    print(sender.stdout.strip())
    print("REPRODUCED: local control reaches NSView; PID-targeted mouse events have windowNumber zero")
