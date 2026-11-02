#!/usr/bin/env python3
"""Exercise the production AppKit restoration batch, without terminal/core mocks.

Requires a logged-in GUI session. Does not test persisted decoding or fullscreen;
use session-check.py for across-launch integration.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Features/Terminal/TerminalRestorable.swift").read_text()
start = source.index("    private struct RestoredWindow")
end = source.index("    static func restoreWindow(", start)
batch = source[start:end].replace("private ", "")
controller = (root / "macos/Sources/Features/Terminal/TerminalController.swift").read_text()
selection_start = controller.index("        state.encode(", controller.index("func window(_ window: NSWindow, willEncodeRestorableState"))
selection_end = controller.index(",\n", selection_start)
selection = controller[selection_start + len("        state.encode("):selection_end]
harness = r"""
import Cocoa
let app = NSApplication.shared
func window(_ title: String) -> NSWindow {
    let result = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 600, height: 400),
                          styleMask: [.titled, .closable, .resizable, .miniaturizable], backing: .buffered, defer: false)
    result.title = title
    result.isReleasedWhenClosed = false
    result.tabbingMode = .disallowed
    return result
}
let alpha = window("alpha")
let beta = window("beta")
let gamma = window("gamma")
let delta = window("delta")
let hidden = window("hidden")
precondition(TerminalWindowRestoration.takeRestoredFullscreenWindow() == nil)
TerminalWindowRestoration.restoredFrontWindow = gamma
precondition(TerminalWindowRestoration.takeRestoredFullscreenWindow() == nil,
             "Ordinary restored window should not override CLI activation")
precondition(TerminalWindowRestoration.restoredFrontWindow == nil,
             "Restored activation candidate must be consumed")
weak var released: NSWindow?
autoreleasepool {
    let transient = window("transient")
    released = transient
    TerminalWindowRestoration.restoredFrontWindow = transient
}
precondition(released == nil && TerminalWindowRestoration.restoredFrontWindow == nil,
             "Restoration activation must not retain a window")
func selectedForRestoration(_ window: NSWindow) -> Bool { SELECTION }
if !selectedForRestoration(hidden) {
    FileHandle.standardError.write(Data("Standalone window omitted from restoration order\n".utf8))
    exit(1)
}
hidden.styleMask.remove(.titled)
precondition(selectedForRestoration(hidden), "Untitled standalone window omitted from restoration order")
alpha.orderFront(nil)
alpha.addTabbedWindow(beta, ordered: .above)
beta.makeKeyAndOrderFront(nil)
precondition(!selectedForRestoration(alpha) && selectedForRestoration(beta), "Tab selection encoding")
delta.orderFront(nil)
gamma.orderFront(nil)
let key = app.keyWindow
TerminalWindowRestoration.restoreSelection(alpha, order: 2)
TerminalWindowRestoration.restoreSelection(gamma, order: 1)
TerminalWindowRestoration.restoreSelection(delta, order: 0)
TerminalWindowRestoration.restoreSelection(hidden, order: 3)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
let names = app.orderedWindows.filter { $0.isVisible && ($0.tabGroup?.selectedWindow == nil || $0.tabGroup?.selectedWindow === $0) }.map { $0.title }
if names != ["delta", "gamma", "alpha"] {
    FileHandle.standardError.write(Data("Wrong order: \(names)\n".utf8))
    exit(1)
}
precondition(alpha.tabGroup?.selectedWindow === alpha)
precondition(!hidden.isVisible, "Hidden window unexpectedly shown")
precondition(app.keyWindow === key, "Restoration changed the key window")
precondition(TerminalWindowRestoration.pendingWindows.isEmpty)
// A later batch must schedule independently and retain no windows after draining.
TerminalWindowRestoration.restoreSelection(alpha, order: 0)
TerminalWindowRestoration.restoreSelection(gamma, order: 1)
TerminalWindowRestoration.restoreSelection(delta, order: 2)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
precondition(app.orderedWindows.filter { $0.isVisible && ($0.tabGroup?.selectedWindow == nil || $0.tabGroup?.selectedWindow === $0) }.map { $0.title } == ["alpha", "gamma", "delta"])
print("PASS: production selection/order batch, hidden state, key window and cleanup")
// Selecting a tab through AppKit deminiaturizes its whole group on Monterey.
let miniAlpha = window("mini-alpha")
let miniBeta = window("mini-beta")
miniAlpha.orderFront(nil)
miniAlpha.addTabbedWindow(miniBeta, ordered: .above)
miniBeta.makeKeyAndOrderFront(nil)
miniBeta.miniaturize(nil)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.5))
precondition(miniAlpha.isMiniaturized && miniBeta.isMiniaturized, "Invalid minimized fixture")
let keyBeforeMinimizedSelection = app.keyWindow
TerminalWindowRestoration.restoreSelection(miniAlpha, order: 0)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.5))
if !miniAlpha.isMiniaturized || !miniBeta.isMiniaturized || miniAlpha.isVisible || miniBeta.isVisible {
    FileHandle.standardError.write(Data("Minimized group unexpectedly shown\n".utf8))
    exit(1)
}
precondition(miniAlpha.tabGroup?.selectedWindow === miniAlpha, "Minimized selection not restored")
precondition(app.keyWindow === keyBeforeMinimizedSelection, "Minimized selection changed key window")
TerminalWindowRestoration.restoreSelection(miniAlpha, order: 0)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
precondition(miniAlpha.isMiniaturized && miniBeta.isMiniaturized, "Repeated selection expanded minimized group")
miniAlpha.deminiaturize(nil)
RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.5))
precondition(miniAlpha.tabGroup?.selectedWindow === miniAlpha && miniAlpha.isVisible)
miniAlpha.close()
miniBeta.close()
print("PASS: minimized tab selection remains minimized and survives deminiaturization")
"""

with tempfile.TemporaryDirectory(prefix="ghostty-restoration-order-") as tmp:
    tmp = pathlib.Path(tmp)
    for optimize in ("-Onone", "-O"):
        for name, body, expression in (("production", batch, selection),
                           ("no-order-mutant", batch.replace(
                               "below.order(.below, relativeTo: above.windowNumber)", "_ = below; _ = above"), selection),
                           ("nil-group-mutant", batch, "window.tabGroup?.selectedWindow === window"),
                           ("unminimize-mutant", batch.replace("if minimized { window.miniaturize(nil) }", "_ = minimized"), selection)):
            swift = tmp / "main.swift"
            swift.write_text("import Cocoa\nclass TerminalWindowRestoration {\n" + body + "}\n" + harness.replace("SELECTION", expression))
            binary = tmp / name
            subprocess.run(["swiftc", optimize, str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True)
            if name == "production":
                assert result.returncode == 0, result.stderr
                print(f"{optimize}: {result.stdout.strip()}")
            else:
                diagnostic = {"nil-group-mutant": "Standalone window omitted",
                              "unminimize-mutant": "Minimized group unexpectedly shown"}.get(name, "Wrong order")
                assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
                print(f"{optimize}: PASS: compiled {name} rejected")
