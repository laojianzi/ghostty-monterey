#!/usr/bin/env python3
"""Check quick-terminal hide/reopen identity in a running isolated test app."""

import pathlib
import plistlib
import shlex
import subprocess
import sys

app = str(pathlib.Path(sys.argv[1]).resolve()).replace("\\", "\\\\").replace('"', '\\"')
pid = int(sys.argv[2])
work = pathlib.Path(sys.argv[1]).resolve().parent
assert work.name.startswith("ghostty-monterey-smoke-")
assert plistlib.loads((pathlib.Path(sys.argv[1]) / "Contents/Info.plist").read_bytes())["CFBundleIdentifier"] == (
    "com.mitchellh.ghostty.monterey-smoke")
source = work / "quick-visible.swift"
binary = work / "quick-visible"
source.write_text('''import Cocoa
let pid = Int(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                       kCGNullWindowID) as! [[String: Any]]
let visible = windows.filter {
    guard $0[kCGWindowOwnerPID as String] as? Int == pid,
          let bounds = $0[kCGWindowBounds as String] as? [String: Any],
          let width = bounds["Width"] as? Double,
          let height = bounds["Height"] as? Double else { return false }
    return width > 100 && height > 100
}
print(visible.count)
''')
subprocess.run(["swiftc", str(source), "-o", str(binary)], check=True)
geometry = shlex.quote(str(binary)) + " " + str(pid)
geometry = geometry.replace("\\", "\\\\").replace('"', '\\"')
subprocess.run(["osascript", "-"], input=f'''
tell application "{app}"
    if (count of windows) is not 1 then error "Expected one regular test window"
    set original to focused terminal of selected tab of front window
    set originalID to id of original
    set visibleBefore to (do shell script "{geometry}") as integer
    set opened to open quick terminal
    if (count of opened) is not 1 then error "Expected one returned quick terminal"
    set returnedID to id of item 1 of opened
    delay 0.6
    set candidates to every terminal whose id is not originalID
    if (count of candidates) is not 1 then error "Expected one quick terminal, got " & (count of candidates)
    set quick to item 1 of candidates
    set quickID to id of quick
    if quickID is not returnedID then error "Open returned the wrong surface"
    set quickPID to pid of quick
    set quickTTY to tty of quick
    if quickID is originalID or quickPID is 0 or quickTTY is "" then error "Quick terminal not created: " & quickID & ", pid=" & quickPID & ", tty=" & quickTTY
    repeat 3 times
        set opened to open quick terminal
        if (count of opened) is not 1 or (id of item 1 of opened) is not quickID then error "Repeated open replaced quick terminal"
    end repeat
    delay 0.6
    if ((do shell script "{geometry}") as integer) is not (visibleBefore + 1) then error "Repeated open hid quick terminal or created a window"
    if pid of quick is not quickPID or tty of quick is not quickTTY then error "Repeated open restarted child/PTY"
    set other to split quick direction right
    set otherID to id of other
    set opened to open quick terminal
    if (count of opened) is not 2 then error "Open omitted quick-terminal splits"
    set returnedIDs to {{id of item 1 of opened, id of item 2 of opened}}
    if returnedIDs does not contain quickID or returnedIDs does not contain otherID then error "Wrong split references returned"
    close other
    delay 0.2
    if not (perform action "toggle_quick_terminal" on quick) then error "Quick terminal hide rejected"
    delay 0.6
    if (count of windows) is not 1 then error "Quick terminal did not hide"
    if ((do shell script "{geometry}") as integer) is not visibleBefore then error "Quick terminal still on screen after hide"
    set opened to open quick terminal
    if (id of item 1 of opened) is not quickID then error "Reopen returned the wrong surface"
    delay 0.6
    set quick to terminal id quickID
    if id of quick is not quickID then error "Quick terminal lost surface identity"
    if pid of quick is not quickPID or tty of quick is not quickTTY then error "Quick terminal restarted child/PTY"
    if not (perform action "toggle_quick_terminal" on quick) then error "Quick terminal final hide rejected"
    delay 0.6
    if not (perform action "toggle_quick_terminal" on original) then error "Original toggle show rejected"
    delay 0.6
    if ((do shell script "{geometry}") as integer) is not (visibleBefore + 1) then error "Original toggle did not show quick terminal"
    if not (perform action "toggle_quick_terminal" on quick) then error "Original toggle hide rejected"
    delay 0.6
    if ((do shell script "{geometry}") as integer) is not visibleBefore then error "Final hide left quick terminal on screen"
    return "PASS: quick-terminal idempotent open/return/hide/reopen preserves surface, process and PTY"
end tell
''', text=True, check=True, timeout=20)
