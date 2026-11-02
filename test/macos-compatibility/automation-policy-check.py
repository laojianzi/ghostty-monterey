#!/usr/bin/env python3
"""Verify the real app's scripting opt-out without changing system permissions.

Only for app-smoke's disposable bundle/config. SIGUSR2 is Ghostty's existing
public config reload path, allowing recovery while scripting itself is denied.
"""

import os
import pathlib
import plistlib
import shlex
import signal
import subprocess
import sys
import time

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
pid = int(sys.argv[3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
assert plistlib.loads((app / "Contents/Info.plist").read_bytes())["CFBundleIdentifier"] == (
    "com.mitchellh.ghostty.monterey-smoke")


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.run(["osascript", "-"],
        input=f"tell application {literal(app)}\n{body}\nend tell", text=True,
        capture_output=True, timeout=10)


def value(body):
    result = script(body)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def wait_count(expected):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if value("return count of terminals") == str(expected):
            return
        time.sleep(0.1)
    raise AssertionError(f"Scripting visibility did not become {expected}")


config = work / "config"
original = config.read_text()
assert original.count("macos-applescript = true") == 1
terminal = value("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(terminal)}"
child_pid = value(f"return pid of {target}")
tty = value(f"return tty of {target}")
assert value("return count of terminals") == "1"
assert value("return count of windows") == "1"
try:
    config.write_text(original.replace("macos-applescript = true", "macos-applescript = false"))
    os.kill(pid, signal.SIGUSR2)
    wait_count(0)
    assert value("return count of windows") == "0", "Disabled scripting still exposes windows"
    for command in ("new window", "new surface configuration", "open quick terminal"):
        result = script(command)
        assert result.returncode != 0 and "AppleScript is disabled" in result.stderr, result
        assert "-1743" in result.stderr, result.stderr
    # Object lookup may reject these before dispatch reaches the command guard.
    # Accept either route, but never successful mutation of the retained surface.
    for command in (f'input text "DENIED-INPUT" to {target}',
                    f'perform action "new_tab" on {target}', f"close ({target})"):
        result = script(command)
        assert result.returncode != 0, (command, result.stdout)
    for prop in ("full contents", "visible text", "selected text"):
        result = script(f"return {prop} of {target}")
        assert result.returncode != 0, (prop, result.stdout)
    os.kill(int(child_pid), 0)
    print("PASS: live opt-out hides objects and denies creation/input/action/close", flush=True)
finally:
    config.write_text(original)
    os.kill(pid, signal.SIGUSR2)
    wait_count(1)

assert value("return count of windows") == "1"
assert value("return count of tabs of front window") == "1"
assert value(f"return pid of {target}") == child_pid
assert value(f"return tty of {target}") == tty
marker = work / "automation-policy-restored"
command = "printf policy-restored > " + shlex.quote(str(marker))
value(f'input text {literal(command)} to {target}\nsend key "enter" to {target}')
deadline = time.monotonic() + 5
while not marker.exists() and time.monotonic() < deadline:
    time.sleep(0.05)
assert marker.read_text() == "policy-restored", "Denied input leaked or original PTY did not recover"
print("PASS: re-enable restores the same terminal/process/PTY and accepts fresh commands", flush=True)
