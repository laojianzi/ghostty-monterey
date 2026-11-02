#!/usr/bin/env python3
"""Exercise TerminalView's maximum frame in Monterey's native hosting layout."""

import pathlib
import re
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Features/Terminal/TerminalView.swift").read_text()
frames = re.findall(r"\.frame\(maxWidth: ([^,]+), maxHeight: ([^)]+)\)", source)
assert len(frames) == 1, "Update the harness for the current terminal frame"
width, height = frames[0]

swift = """
import AppKit
import SwiftUI

let app = NSApplication.shared
let view = Color.black.frame(maxWidth: WIDTH, maxHeight: HEIGHT)
let host = NSHostingView(rootView: view)
let container = NSView()
container.addSubview(host)
host.translatesAutoresizingMaskIntoConstraints = false
NSLayoutConstraint.activate([
    host.topAnchor.constraint(equalTo: container.topAnchor),
    host.bottomAnchor.constraint(equalTo: container.bottomAnchor),
    host.leadingAnchor.constraint(equalTo: container.leadingAnchor),
    host.trailingAnchor.constraint(equalTo: container.trailingAnchor),
])
let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 640, height: 480),
                      styleMask: [.titled, .resizable], backing: .buffered, defer: false)
window.contentView = container
window.orderFront(nil)
for size in [NSSize(width: 640, height: 480), NSSize(width: 1200, height: 800),
             NSSize(width: 320, height: 240)] {
    window.setContentSize(size)
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.05))
    container.layoutSubtreeIfNeeded()
    precondition(host.frame.size == container.bounds.size, "Terminal must fill resized content")
}
"""

with tempfile.TemporaryDirectory(prefix="ghostty-layout-") as tmp:
    tmp = pathlib.Path(tmp)
    for name, w, h in [("production", width, height),
                       ("finite-mutant", ".greatestFiniteMagnitude", ".greatestFiniteMagnitude")]:
        path = tmp / f"{name}.swift"
        path.write_text(swift.replace("WIDTH", w).replace("HEIGHT", h))
        binary = tmp / name
        subprocess.run(["swiftc", "-O", str(path), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], text=True, capture_output=True, check=True)
        warning = "constant that exceeds internal limits" in result.stderr
        if name == "production":
            assert not warning, result.stderr
        else:
            assert warning, "Expected Monterey to reject the finite-magnitude mutant"
        print(f"PASS: {name}, resize checks and expected warning behavior")
