#!/usr/bin/env python3
"""Invoke uniquely named Services in the isolated, already-running smoke app.

Registers only the temporary test app and unregisters it in finally. Uses a
unique pasteboard, never the user's general clipboard or installed Ghostty.
Experimental: duplicate historical smoke bundle IDs can prevent discovery;
the inventory preflight fails closed rather than invoking another bundle.
"""

import pathlib
import plistlib
import shlex
import subprocess
import sys
import time

app = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(sys.argv[2]).resolve()
with (app / "Contents/Info.plist").open("rb") as stream:
    info = plistlib.load(stream)
assert info["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"
services = {s["NSMessage"]: s["NSMenuItem"]["default"] for s in info["NSServices"]}
assert all(work.name in name for name in services.values()), "Non-isolated Services names"
register = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"


def apple_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    result = subprocess.run(["osascript", "-"],
                            input=f"tell application {apple_string(app)}\n{body}\nend tell\n",
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


client = work / "service-client.swift"
client.write_text(r'''
import AppKit
_ = NSApplication.shared
NSUpdateDynamicServices()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 1))
let board = NSPasteboard.withUniqueName()
defer { board.releaseGlobally() }
let path = CommandLine.arguments[2]
board.setPropertyList([path], forType: NSPasteboard.PasteboardType("NSFilenamesPboardType"))
let success = NSPerformService(CommandLine.arguments[1], board)
print("NSPerformService=\(success)")
exit(success ? 0 : 1)
''')
binary = work / "service-client"
subprocess.run(["xcrun", "swiftc", str(client), "-o", str(binary)], check=True)
directory = work / "services directory 'quoted'"
directory.mkdir()
original = script("return id of focused terminal of selected tab of front window")
try:
    subprocess.run([register, "-f", str(app)], check=True, timeout=15)
    subprocess.run(["/System/Library/CoreServices/pbs", "-update"], check=True, timeout=15)
    inventory = subprocess.check_output(["/System/Library/CoreServices/pbs", "-dump"],
                                        text=True, stderr=subprocess.STDOUT, timeout=15)
    (work / "services-inventory.txt").write_text(inventory)
    assert all(name in inventory for name in services.values()), (
        "Services inventory does not select this temporary bundle's unique names; "
        "see services-inventory.txt. No service was invoked.")
    for message in ("openWindow", "openTab"):
        result = subprocess.run([str(binary), services[message], str(directory)],
                                text=True, capture_output=True, timeout=20)
        (work / f"service-{message}.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        created = script("return id of focused terminal of selected tab of front window")
        assert created != original, "Service did not create a new terminal"
        try:
            marker = work / f"service-{message}-cwd"
            script(f'''
set t to terminal id {apple_string(created)}
input text {apple_string("pwd -P > " + shlex.quote(str(marker)))} to t
send key "enter" to t
''')
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            assert marker.exists() and marker.read_text().strip() == str(directory.resolve()), "Wrong service PTY cwd"
        finally:
            script(f"close (terminal id {apple_string(created)})")
        assert script("return count of windows") == "1"
        assert script("return count of tabs of front window") == "1"
    print("PASS: cross-process NSPerformService window/tab creation and live PTY working directories")
finally:
    subprocess.run([register, "-u", str(app)], check=True, timeout=15)
    subprocess.run(["/System/Library/CoreServices/pbs", "-update"], check=True, timeout=15)
