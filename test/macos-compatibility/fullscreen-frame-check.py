#!/usr/bin/env python3
"""Check production fullscreen exit geometry ordering on a native toolbar window.

Runs the style/frame/toolbar assignments in their production order. The focused
fixture does not emulate Ghostty tab-bar accessories; fullscreen-check.py covers
the complete application path.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Helpers/Fullscreen.swift").read_text()
start = source.index("        // Restore our saved state")
end = source.index("        // If the window was previously in a tab group", start)
assignments = [line.strip() for line in source[start:end].splitlines()
               if line.strip().startswith(("window.styleMask =", "window.setFrame(",
                                           "window.toolbar =", "window.toolbarStyle ="))]
assert len(assignments) == 4, "Update the test extraction for the current fullscreen exit"
body = "\n".join(assignments)
entry_start = source.index("        // Being untitled")
entry_end = source.index("        // Focus window", entry_start)
entry = "\n".join(line.strip() for line in source[entry_start:entry_end].splitlines()
                  if line.strip().startswith(("window.toolbar =", "window.styleMask.remove(")))
assert "window.toolbar = nil" in entry
frame_line = next(line for line in assignments if line.startswith("window.setFrame("))
mutant = "\n".join([assignments[0], frame_line] +
                   [line for line in assignments[1:] if line != frame_line])
assert mutant != body, "Frame restoration must follow toolbar restoration"

harness = r'''
import Cocoa
let app = NSApplication.shared
let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 800, height: 600),
                      styleMask: [.titled, .resizable, .closable], backing: .buffered, defer: false)
window.toolbar = NSToolbar(identifier: "test")
window.toolbarStyle = .unifiedCompact
window.orderFront(nil)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
let original = window.frame
let savedState = (contentFrame: window.convertToScreen(window.contentView!.frame),
                  styleMask: window.styleMask, toolbar: window.toolbar, toolbarStyle: window.toolbarStyle)
for _ in 0..<3 {
    ENTER
    window.setFrame(NSScreen.main!.frame, display: true)
    RESTORE
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
    if window.frame != original {
        FileHandle.standardError.write(Data("Wrong frame: \(window.frame), expected \(original)\n".utf8))
        exit(1)
    }
}
print("PASS: toolbar window frame restored over three cycles")
'''

with tempfile.TemporaryDirectory(prefix="ghostty-fullscreen-frame-") as directory:
    directory = pathlib.Path(directory)
    for optimize in ("-Onone", "-O"):
        for name, statements, entering in (("production", body, entry), ("old-order-mutant", mutant, entry),
                                          ("attached-toolbar-mutant", body, entry.replace("window.toolbar = nil", ""))):
            swift = directory / "main.swift"
            swift.write_text(harness.replace("RESTORE", statements).replace("ENTER", entering))
            binary = directory / name
            subprocess.run(["swiftc", optimize, str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            if name == "production":
                assert result.returncode == 0, result.stderr
                assert "Can't have a toolbar" not in result.stderr, result.stderr
                print(f"{optimize}: {result.stdout.strip()}")
            elif name == "attached-toolbar-mutant":
                assert result.returncode == 0 and "Can't have a toolbar" in result.stderr, result.stderr
                print(f"{optimize}: PASS: attached toolbar mutant emits expected AppKit error")
            else:
                assert result.returncode != 0 and "Wrong frame:" in result.stderr, result.stderr
                print(f"{optimize}: PASS: compiled old-order mutant rejected")
