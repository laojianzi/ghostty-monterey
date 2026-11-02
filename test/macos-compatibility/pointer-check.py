#!/usr/bin/env python3
"""Observe production cursor-rectangle registration in a real SwiftUI host.

The addCursorRect interceptor is test-only and forwards to the real method.
No mouse warping/global cursor mutation; physical hover remains a separate test.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Helpers/Backport.swift").read_text()
harness = r"""
import Cocoa
import SwiftUI
import ObjectiveC
var cursorRects: [(NSRect, NSCursor)] = []
var cursorViews: [NSView] = []
extension NSView {
    @objc func testAddCursorRect(_ rect: NSRect, cursor: NSCursor) {
        cursorRects.append((rect, cursor))
        cursorViews.append(self)
        testAddCursorRect(rect, cursor: cursor)
    }
}
let original = class_getInstanceMethod(NSView.self, #selector(NSView.addCursorRect(_:cursor:)))!
let replacement = class_getInstanceMethod(NSView.self, #selector(NSView.testAddCursorRect(_:cursor:)))!
method_exchangeImplementations(original, replacement)
let app = NSApplication.shared
final class Model: ObservableObject {
    @Published var style: BackportPointerStyle? = .link
    @Published var width: CGFloat = 100
    @Published var shown = true
}
struct Root: View {
    @ObservedObject var model: Model
    var body: some View {
        if model.shown {
            Color.clear.frame(width: model.width, height: 40).backport.pointerStyle(model.style)
        }
    }
}
let model = Model()
let host = NSHostingView(rootView: Root(model: model))
let window = NSWindow(contentRect: NSRect(x: 50, y: 50, width: 250, height: 100), styleMask: [.titled], backing: .buffered, defer: false)
window.contentView = host
window.orderFront(nil)
func spin() { RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.15)) }
func checkRects(_ count: Int, width: CGFloat = 0) {
    spin()
    cursorRects.removeAll()
    cursorViews.removeAll()
    window.resetCursorRects()
    let links = cursorRects.filter { $0.1 === NSCursor.pointingHand }
    if links.count != count {
        FileHandle.standardError.write(Data("FAIL: expected \(count) link cursor rectangles, got \(links.count)\n".utf8))
        exit(1)
    }
    if count > 0 { precondition(links[0].0.size == NSSize(width: width, height: 40)) }
}
checkRects(1, width: 100)
let linkView = cursorViews.first { $0 is LinkCursorRegion.CursorView }!
precondition(linkView.hitTest(NSPoint(x: 5, y: 5)) == nil, "Cursor view intercepted a click")
model.width = 180
checkRects(1, width: 180)
model.style = nil
checkRects(0)
model.style = .resizeLeftRight
checkRects(0) // Existing split-divider onHover is still the sole cursor owner.
model.style = .link
checkRects(1, width: 180)
model.shown = false
checkRects(0)
print("PASS: cursor registration, resize, nil/link transitions, removal and click passthrough")
method_exchangeImplementations(original, replacement)
"""
with tempfile.TemporaryDirectory(prefix="ghostty-pointer-") as directory:
    directory = pathlib.Path(directory)
    marker = "content.background(LinkCursorRegion())"
    assert source.count(marker) == 1, "Update the no-pointer mutation"
    for optimize in ("-Onone", "-O"):
        for name, body in (("production", source), ("no-pointer-mutant", source.replace(marker, "content"))):
            swift = directory / "main.swift"
            swift.write_text(body + harness)
            binary = directory / name
            subprocess.run(["swiftc", optimize, str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if name == "production":
                assert result.returncode == 0, result.stderr
                print(f"{optimize}: {result.stdout.strip()}")
            else:
                assert result.returncode != 0 and "link cursor rectangles" in result.stderr, result.stderr
                print(f"{optimize}: PASS: compiled no-pointer mutant rejected")
