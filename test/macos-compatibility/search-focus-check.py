#!/usr/bin/env python3
"""Check automatic SwiftUI focus through the production selection bridge.

Requires a logged-in macOS GUI. Temporarily activates small test windows and
restores the foreground application after each completed probe.
The negative control moves focus back to the outer representable background,
reproducing the Monterey failure without bypassing SwiftUI focus dispatch.
"""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = r'''
import AppKit
import SwiftUI
class ProbeState: ObservableObject {
    @Published var shown = false
    @Published var request = false
}
struct Probe: View {
    @ObservedObject var state: ProbeState
    @State var text = "needle"
    @State var selection: Range<String.Index>?
    @FocusState var focused: Bool
    var body: some View {
        VStack {
            if state.shown {
                BackportSelectionTextField(
                    "Search", text: $text, selection: $selection, focus: $focused
                )
                .textFieldStyle(.plain)
                .padding(8)
                .background(Color.gray)
            }
        }.onChange(of: state.request) { _ in focused = true }
    }
}
@main struct Main {
    static func main() {
        let previous = NSWorkspace.shared.frontmostApplication
        let app = NSApplication.shared
        app.setActivationPolicy(.regular)
        let window = NSWindow(
            contentRect: NSRect(x: 600, y: 200, width: 300, height: 100),
            styleMask: [.titled, .closable], backing: .buffered, defer: false)
        let state = ProbeState()
        window.contentView = NSHostingView(rootView: Probe(state: state))
        window.makeKeyAndOrderFront(nil)
        app.activate(ignoringOtherApps: true)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) { state.shown = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            window.makeFirstResponder(window)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.9) { state.request = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            let ok = window.firstResponder is NSTextView
            print("Automatic search focus: \(ok)")
            window.orderOut(nil)
            previous?.activate(options: [.activateIgnoringOtherApps])
            exit(ok ? 0 : 1)
        }
        app.run()
    }
}
'''


def main():
    production = ROOT / "macos/Sources/Helpers/Backport.swift"
    for optimize in ("-Onone", "-O"):
        with tempfile.TemporaryDirectory(prefix="ghostty-search-focus-") as folder:
            work = pathlib.Path(folder)
            for mutant in (False, True):
                code = HARNESS
                if mutant:
                    code = code.replace(", focus: $focused", "")
                    code = code.replace(".background(Color.gray)", ".background(Color.gray).focused($focused)")
                swift = work / "main.swift"
                swift.write_text(code)
                executable = work / "probe"
                subprocess.run(["xcrun", "swiftc", "-parse-as-library", optimize,
                                str(swift), str(production), "-o", str(executable)], check=True)
                result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
                expected = 1 if mutant else 0
                assert result.returncode == expected, (mutant, result.returncode, result.stdout, result.stderr)
                assert f"Automatic search focus: {str(not mutant).lower()}" in result.stdout
                print(f"{optimize}: {'outer-focus regression rejected' if mutant else 'automatic field focus passed'}")


if __name__ == "__main__":
    main()
