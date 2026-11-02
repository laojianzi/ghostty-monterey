#!/usr/bin/env python3
"""Measure terminal churn in app-smoke's actual isolated ReleaseLocal app.

Child exit and original-surface identity are assertions. RSS, CPU time, descriptor
and thread counts are observations, not an upstream performance comparison or
proof of absence of leaks. No activity assertions or global power changes.
"""

import json
import os
import pathlib
import plistlib
import subprocess
import sys
import time

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
pid = int(sys.argv[3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
with (app / "Contents/Info.plist").open("rb") as stream:
    assert plistlib.load(stream)["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.check_output(["osascript", "-"],
        input=f"tell application {literal(app)}\n{body}\nend tell", text=True, timeout=15).strip()


def alive(child):
    try:
        os.kill(child, 0)
        return True
    except ProcessLookupError:
        return False


def measure(stage):
    output = subprocess.check_output(["ps", "-p", str(pid), "-o", "rss=,time="], text=True).split()
    assert len(output) == 2, ("App exited during measurement", output)
    # macOS ps reports [[days-]hours:]minutes:seconds.centiseconds.
    days, separator, clock = output[1].rpartition("-")
    cpu = float(days) * 86400 if separator else 0.0
    for index, part in enumerate(reversed(clock.split(":"))):
        cpu += float(part) * 60 ** index
    descriptor_output = subprocess.check_output(
        ["/usr/sbin/lsof", "-a", "-p", str(pid), "-F", "ftn"], text=True, timeout=10)
    (work / f"lifecycle-{stage}-fds.txt").write_text(descriptor_output)
    descriptors = descriptor_output.splitlines()
    descriptors = sorted(int(line[1:]) for line in descriptors if line.startswith("f") and line[1:].isdigit())
    # Darwin -M selects a fixed thread layout; -o appends rather than replaces
    # that layout, and continuation rows omit the user/PID columns.
    threads = subprocess.check_output(["ps", "-M", "-p", str(pid)], text=True).splitlines()
    assert len(threads) > 1 and threads[0].split()[:2] == ["USER", "PID"], threads
    assert threads[1].split()[1] == str(pid), threads
    value = {"stage": stage, "monotonic": time.monotonic(), "rss_kib": int(output[0]),
             "cpu_seconds": cpu, "descriptors": len(descriptors), "threads": len(threads) - 1}
    print(json.dumps(value), flush=True)
    return value


original = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(original)}"
original_pid = script(f"return pid of {target}")
original_tty = script(f"return tty of {target}")
assert script("return count of terminals") == "1"
assert "undo-timeout = 5s" in (work / "config").read_text()
report = {"pid": pid, "app": str(app), "samples": [], "batches": [],
          "limits": "Host observations only; no upstream comparison, GPU memory or leak proof."}
try:
    for batch in range(4):
        # Batch zero warms lazy AppKit, renderer and scripting allocations before
        # comparing later settled states. Keep upstream undo retention enabled.
        before = measure(f"batch-{batch}-before")
        report["samples"].append(before)
        created = []
        children = []
        try:
            for kind in ("split", "tab", "window"):
                creation = {
                    "split": f"set t to split ({target}) direction right",
                    "tab": "set tabbed to new tab in front window\nset t to focused terminal of tabbed",
                    "window": "set w to new window\nset t to focused terminal of selected tab of w",
                }[kind]
                identifier = script(creation + "\nreturn id of t")
                created.append(identifier)
                time.sleep(0.2)
                child = int(script(f"return pid of terminal id {literal(identifier)}"))
                assert child > 1 and child != int(original_pid) and alive(child)
                children.append(child)
            assert script("return count of terminals") == "4"
            assert len(set(children)) == 3
            report["samples"].append(measure(f"batch-{batch}-open"))
        finally:
            for identifier in reversed(created):
                script(f"close (terminal id {literal(identifier)})")
        closed_at = time.monotonic()
        assert script("return count of terminals") == "1"
        while any(alive(child) for child in children) and time.monotonic() - closed_at < 10:
            time.sleep(0.1)
        remaining = [child for child in children if alive(child)]
        report["batches"].append({"index": batch, "children": children,
                                  "expiry_seconds": time.monotonic() - closed_at, "remaining": remaining})
        assert not remaining, f"Closed terminal children survived original expiry deadline: {remaining}"
        assert script(f"return pid of {target}") == original_pid
        assert script(f"return tty of {target}") == original_tty
        assert script("return id of focused terminal of selected tab of front window") == original
        time.sleep(0.5)
        settled = measure(f"batch-{batch}-settled")
        report["samples"].append(settled)
        time.sleep(3)
        idle = measure(f"batch-{batch}-idle")
        report["samples"].append(idle)
        # CPU seconds are process-wide; 100% represents one busy logical core.
        utilization = 100 * (idle["cpu_seconds"] - settled["cpu_seconds"]) / (idle["monotonic"] - settled["monotonic"])
        report["batches"][-1]["idle_cpu_percent_one_core"] = utilization
        print(f"PASS: batch {batch}, three PTY children expired, original surface/process retained; "
              f"observed idle CPU {utilization:.2f}% of one core", flush=True)
finally:
    (work / "lifecycle-resources.json").write_text(json.dumps(report, indent=2) + "\n")
