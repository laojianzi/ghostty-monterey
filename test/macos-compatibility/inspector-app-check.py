#!/usr/bin/env python3
"""Check real Inspector layout/lifecycle via the isolated app and its live PTY.

PTY geometry proves the inspector occupies/relinquishes layout space, not that
its Metal drawable presents correct pixels or physical input reaches ImGui.
"""

import pathlib
import plistlib
import shlex
import subprocess
import sys
import time

app, work = map(lambda arg: pathlib.Path(arg).resolve(), sys.argv[1:3])
with (app / "Contents/Info.plist").open("rb") as stream:
    assert plistlib.load(stream)["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.run(["osascript", "-"], input=f"tell application {literal(app)}\n{body}\nend tell",
                          text=True, capture_output=True, timeout=15, check=True).stdout.strip()


terminal = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(terminal)}"
pid = script(f"return pid of {target}")
tty = script(f"return tty of {target}")
assert pid != "0" and tty
sequence = 0


def size():
    global sequence
    sequence += 1
    output = work / f"inspector-size-{sequence}"
    script(f'''input text {literal('stty size > ' + shlex.quote(str(output)))} to {target}
send key "enter" to {target}''')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if output.exists() and len(output.read_text().split()) == 2:
            rows, cols = map(int, output.read_text().split())
            assert rows > 0 and cols > 0
            return rows, cols
        time.sleep(0.05)
    raise AssertionError("Inspector toggle lost live PTY")


def action(mode):
    assert script(f'perform action "inspector:{mode}" on {target}') == "true"
    time.sleep(0.4)


baseline = size()
try:
    for cycle in range(3):
        action("show")
        deadline = time.monotonic() + 5
        shown = size()
        while shown == baseline and time.monotonic() < deadline:
            time.sleep(0.1)
            shown = size()
        assert shown[0] < baseline[0] and shown[1] == baseline[1], (baseline, shown)
        action("show")
        assert size() == shown, "Repeated show changed Inspector layout"
        action("hide")
        assert size() == baseline, "Hiding Inspector did not recover PTY dimensions"
        action("toggle")
        assert size() == shown, "Toggle failed to reopen Inspector"
        action("toggle")
        assert size() == baseline, "Toggle failed to close Inspector"
        assert script(f"return pid of {target}") == pid and script(f"return tty of {target}") == tty
        assert script("return count of terminals") == "1", "Inspector created a terminal surface"
        print(f"PASS: Inspector cycle {cycle + 1}: {baseline} -> {shown} -> {baseline}; same surface/process/PTY", flush=True)
finally:
    action("hide")

# An Inspector-owned MTKView must not replace the terminal or its process when
# closing and undoing its window. Keep the original window as the undo target.
original = target
created = script('''set w to new window
return id of focused terminal of selected tab of w''')
target = f"terminal id {literal(created)}"
time.sleep(0.4)
created_pid = script(f"return pid of {target}")
created_tty = script(f"return tty of {target}")
created_size = size()
try:
    action("show")
    shown = size()
    assert shown[0] < created_size[0] and shown[1] == created_size[1]
    script(f'perform action "close_window" on {target}')
    time.sleep(0.3)
    assert script("return count of windows") == "1"
    assert script(f'perform action "undo" on {original}') == "true"
    time.sleep(0.5)
    assert script("return count of windows") == "2"
    assert script(f"return pid of {target}") == created_pid
    assert script(f"return tty of {target}") == created_tty
    assert size() == shown, "Undo lost visible Inspector layout or live PTY"
    action("hide")
    assert size() == created_size
    print("PASS: close/undo with visible Inspector retains layout, terminal/process/PTY; hide restores dimensions", flush=True)
finally:
    script(f"close ({target})")
