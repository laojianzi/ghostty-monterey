#!/usr/bin/env python3
"""Check live fullscreen transitions and PTY retention in an isolated test app.

Uses WindowServer geometry, not just action acceptance. Requires a GUI session;
native fullscreen temporarily switches Spaces. Does not validate rendered pixels.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import time

app = str(pathlib.Path(sys.argv[1]).resolve()).replace('"', '\\"')
pid = int(sys.argv[2])
mode = sys.argv[3]
tabbed = "--tabs" in sys.argv[4:]


def script(body):
    result = subprocess.run(["osascript", "-"], input=f'tell application "{app}"\n{body}\nend tell',
                            text=True, capture_output=True, timeout=15, check=True)
    return result.stdout.strip()


with tempfile.TemporaryDirectory(prefix="ghostty-fullscreen-") as directory:
    directory = pathlib.Path(directory)
    source = directory / "geometry.swift"
    source.write_text('''
import Cocoa
let pid = Int(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                       kCGNullWindowID) as! [[String: Any]]
let bounds = windows.filter {
    $0[kCGWindowOwnerPID as String] as? Int == pid &&
    $0[kCGWindowLayer as String] as? Int == 0
}.compactMap { $0[kCGWindowBounds as String] as? [String: Any] }
let screens = NSScreen.screens.map { ["Width": $0.frame.width, "Height": $0.frame.height] }
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
let locked = session?["CGSSessionScreenIsLocked"] as? Bool ?? false
let data = try JSONSerialization.data(withJSONObject: ["windows": bounds, "screens": screens,
                                                      "locked": locked])
print(String(data: data, encoding: .utf8)!)
''')
    binary = directory / "geometry"
    subprocess.run(["swiftc", str(source), "-o", str(binary)], check=True)

    def geometry():
        return json.loads(subprocess.check_output([str(binary), str(pid)], text=True))

    if mode == "false":
        assert not geometry()["locked"], "Native fullscreen requires an unlocked GUI session; unlock and rerun"

    saved = script('''
activate window front window
delay 0.5
set t to focused terminal of selected tab of front window
return {id of t, pid of t, tty of t}
''')
    terminal_id = saved.split(", ")[0]
    if tabbed:
        sibling = script(f'''
set originalTab to selected tab of front window
set newTab to new tab in front window
set t to focused terminal of newTab
set identity to {{id of t, pid of t, tty of t}}
select tab originalTab
delay 0.5
return identity
''')
        sibling_id = sibling.split(", ")[0]
        original_order = script("return id of every tab of front window")
    initial = geometry()
    assert len(initial["windows"]) == 1, initial
    before = initial["windows"][0]
    print(f"Initial window bounds: {before}", flush=True)

    def toggle():
        assert script(f'perform action "toggle_fullscreen" on terminal id "{terminal_id}"') == "true"

    def wait_geometry(predicate, count=1):
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            value = geometry()
            if len(value["windows"]) == count and predicate(value["windows"][0], value["screens"]):
                return value["windows"][0]
            time.sleep(0.2)
        raise AssertionError(f"Fullscreen geometry timeout: {value}")

    for cycle in range(2):
        toggle()
        full = wait_geometry(lambda window, screens: any(
            abs(window["Width"] - screen["Width"]) <= 2 and
            screen["Height"] - 100 <= window["Height"] <= screen["Height"] + 2
            for screen in screens) and any(
                abs(window[key] - before[key]) > 2 for key in ("X", "Y", "Width", "Height")),
            count=2 if tabbed and mode != "false" else 1)
        # A restored/maximized window can already span the display width.
        # Wait for a changed frame too, or the old frame can satisfy the screen
        # predicate before the asynchronous native transition has even started.
        assert any(abs(full[key] - before[key]) > 2 for key in ("X", "Y", "Width", "Height")), (before, full)
        print(f"Fullscreen cycle {cycle + 1} bounds: {full}", flush=True)
        # Wait until the native animation/state machine has finished before exit.
        time.sleep(1)
        assert script(f'set t to terminal id "{terminal_id}"\nreturn {{id of t, pid of t, tty of t}}') == saved
        if tabbed:
            assert script(f'set t to terminal id "{sibling_id}"\nreturn {{id of t, pid of t, tty of t}}') == sibling
            assert script("return count of windows") == ("1" if mode == "false" else "2")
        output = directory / f"fullscreen-{cycle}"
        script(f'''
set t to terminal id "{terminal_id}"
input text "printf fullscreen-ok > '{output}'" to t
send key "enter" to t
''')
        deadline = time.monotonic() + 5
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert output.read_text() == "fullscreen-ok"
        toggle()
        wait_geometry(lambda window, _: all(abs(window[key] - before[key]) <= 2
                                           for key in ("X", "Y", "Width", "Height")))
        time.sleep(1)
        if tabbed:
            assert script("return count of windows") == "1", "Fullscreen tab did not rejoin its group"
            assert script("return id of every tab of front window") == original_order, "Fullscreen changed tab order"
            assert script("return id of focused terminal of selected tab of front window") == terminal_id
    if tabbed:
        script(f'close terminal id "{sibling_id}"')
    print(f"PASS: fullscreen={mode}, two enter/exit cycles, frame restoration and live PTY")
