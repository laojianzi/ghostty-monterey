#!/usr/bin/env python3
"""Check the cross-window drop activation seam with real AppKit windows.

This complements, not replaces, native drag/PTY tests. Extract the production
cross-window success tail so removing activation makes this check fail. A
negative control also verifies that first-responder assignment is insufficient.
Requires an unlocked, authorized foreground GUI session; restores the front app.
"""
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "macos/Sources/Features/Terminal/BaseTerminalController.swift").read_text()
start = source.index("        // Add in the surface to our tree", source.index("private func splitDidDrop("))
end = source.index("\n    }", start)
tail = source[start:end]
prefix = '''import AppKit
class Input: NSView {
    override var acceptsFirstResponder: Bool { true }
}
class Destination {
    let window: NSWindow?
    let focusedSurface = Input()
    init(_ window: NSWindow) { self.window = window }
    func replaceSurfaceTree(_ tree: Int, moveFocusTo view: Input, moveFocusFrom old: Input) {
        window?.contentView = view
        window?.makeFirstResponder(view)
    }
    func completeDrop(_ source: Input) {
        let newTree = 0
'''
suffix = '''
    }
}
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false))
let app = NSApplication.shared
let previous = NSWorkspace.shared.frontmostApplication
app.setActivationPolicy(.regular)
let source = NSWindow(contentRect: NSRect(x: 20, y: 100, width: 200, height: 100),
                      styleMask: [.titled], backing: .buffered, defer: false)
let target = NSWindow(contentRect: NSRect(x: 300, y: 100, width: 200, height: 100),
                      styleMask: [.titled], backing: .buffered, defer: false)
source.title = "Disposable focus regression source"
target.title = "Disposable focus regression destination"
source.isReleasedWhenClosed = false
target.isReleasedWhenClosed = false
let moved = Input()
source.contentView = moved
target.orderFront(nil)
source.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)
DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
    let initialKey = source.isKeyWindow
    Destination(target).completeDrop(moved)
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
        let passed = initialKey && target.isKeyWindow && target.firstResponder === moved
        source.close()
        target.close()
        previous?.activate(options: [.activateIgnoringOtherApps])
        print(passed ? "PASS: cross-window drop activates destination" : "FAIL: destination not key")
        exit(passed ? 0 : 1)
    }
}
app.run()
'''
activation = "window?.makeKeyAndOrderFront(nil)"
for optimization in ("-Onone", "-O"):
    for negative in (False, True):
        body = tail.replace(activation, "") if negative else tail
        with tempfile.TemporaryDirectory(prefix="ghostty-cross-focus-") as directory:
            work = Path(directory)
            swift, executable = work / "main.swift", work / "check"
            swift.write_text(prefix + body + suffix)
            subprocess.run(["xcrun", "swiftc", optimization, str(swift), "-o", str(executable)], check=True)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
            print(optimization, "negative" if negative else "production", result.stdout.strip())
            expected = 1 if negative else 0
            if result.returncode != expected:
                raise RuntimeError(f"Expected exit {expected}, got {result.returncode}: {result.stderr}")
