#!/usr/bin/env python3
"""Measure native AppKit timer/worker scheduling, not Ghostty correctness.

Runs ordinary/activity/ordinary controls sequentially in a temporary app with
its own bundle identifier. Does not change Ghostty, global energy settings,
permissions, or installed preferences. Run separately from GUI smoke tests.
Large delays are reported, not converted to a product pass or a root-cause claim.
"""

import os
import pathlib
import plistlib
import re
import subprocess
import tempfile


source = pathlib.Path(__file__).with_name("scheduling-probe.m")
with tempfile.TemporaryDirectory(prefix="ghostty-scheduling-", dir="/tmp") as directory:
    app = pathlib.Path(directory) / "SchedulingProbe.app"
    executable = app / "Contents/MacOS/probe"
    executable.parent.mkdir(parents=True)
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "com.mitchellh.ghostty.monterey-scheduling-probe",
        "CFBundleExecutable": "probe",
        "CFBundlePackageType": "APPL",
        "LSMinimumSystemVersion": "12.0",
    }))
    subprocess.run(["xcrun", "clang", "-fobjc-arc", "-O2", "-mmacosx-version-min=12.0",
                    "-framework", "AppKit", str(source), "-o", str(executable)], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", str(app)], check=True)
    for activity in (False, True, False):
        env = dict(os.environ)
        env.pop("GHOSTTY_SCHEDULING_PROBE_ACTIVITY", None)
        # Do not accidentally inherit the earlier diagnostic interposers.
        env.pop("DYLD_INSERT_LIBRARIES", None)
        if activity:
            env["GHOSTTY_SCHEDULING_PROBE_ACTIVITY"] = "1"
        print(f"RUN: activity={activity}", flush=True)
        try:
            result = subprocess.run([str(executable)], env=env, text=True,
                                    capture_output=True, timeout=120, check=True)
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b""
            print(output.decode() if isinstance(output, bytes) else output, end="")
            print("INCONCLUSIVE: native control exceeded 120 seconds", flush=True)
            raise
        print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", flush=True)
        measured = re.search(r"worker_sleep_ms=([0-9.]+) result=0 errno=0", result.stdout)
        if not measured:
            raise RuntimeError("Native control did not complete its requested sleep")
        delay = float(measured[1])
        print(f"OBSERVED: 10 ms sleep took {delay:.3f} ms; "
              "not a Ghostty pass/fail result", flush=True)
