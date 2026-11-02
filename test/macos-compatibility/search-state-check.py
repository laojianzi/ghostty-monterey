#!/usr/bin/env python3
"""Run unchanged upstream SearchState assertions plus its real SwiftUI field path.

Xcode 14 lacks Swift Testing. This bounded adapter only rewrites @Test/#expect;
the production state, C action wrapper, pasteboard extension and field compile
unchanged. Empty containing types avoid linking the unrelated terminal renderer.
All pasteboard operations use a unique test pasteboard, never the user's find board.
"""

import argparse
import json
import pathlib
import re
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--same-turn-replacement", action="store_true")
parser.add_argument("--ablate", action="store_true", help="reject a compiled select-all regression")
parser.add_argument("--compare-upstream-fallback", action="store_true",
                    help="compare native field behavior with the bridge removed in a temporary source copy")
args = parser.parse_args()
if args.compare_upstream_fallback and (args.ablate or args.same_turn_replacement):
    parser.error("The fallback comparison is a standalone experiment")

surface = (root / "macos/Sources/Ghostty/Surface View/OSSurfaceView.swift").read_text()
start = surface.index("    @MainActor class SearchState:")
end = surface.index("    func navigateSearchToNext()", start)
state = surface[start:end]
action_source = (root / "macos/Sources/Ghostty/Ghostty.Action.swift").read_text()
start = action_source.index("    struct StartSearch {")
end = action_source.index("    enum PromptTitle", start)
action = action_source[start:end]
tests = (root / "macos/Tests/Ghostty/Surface View/SurfaceView+SearchStateTests.swift").read_text()
names = re.findall(r"@Test func (\w+)\(\)", tests)
assert len(names) == tests.count("@Test") == 9
tests = tests.replace("import Testing", "").replace("@testable import Ghostty", "")
tests = tests.replace("@Test ", "").replace("#expect(", "expect(")
assert not re.search(r"@Test|#expect|#require", tests)
prefix = """
import AppKit
import SwiftUI
import GhosttyKit
enum Ghostty {
    class OSSurfaceView {}
    enum Action {}
}
func expect(_ value: @autoclosure () -> Bool, file: StaticString = #file, line: UInt = #line) {
    precondition(value(), "Upstream assertion failed", file: file, line: line)
}
"""
production = (prefix + "extension Ghostty.OSSurfaceView {\n" + state + "}\n" +
              "extension Ghostty.Action {\n" + action + "}\n" +
              (root / "macos/Sources/Helpers/Extensions/OSPasteboard+Extension.swift").read_text() +
              (root / "macos/Sources/Helpers/Backport.swift").read_text())

harness = r'''
@MainActor struct SearchRoot: View {
    @ObservedObject var state: Ghostty.OSSurfaceView.SearchState
    var body: some View {
        BackportSelectionTextField("Search", text: $state.needle.text, selection: $state.needle.selection)
            .textFieldStyle(.plain)
            .onChange(of: state.needle.text) { _ in state.writePasteboardNeedle() }
            .frame(width: 200, height: 35)
    }
}
@MainActor func checkField(sameTurn: Bool) {
    let app = NSApplication.shared
    _ = app
    let pasteboard = NSPasteboard.withUniqueName()
    defer { pasteboard.releaseGlobally() }
    pasteboard.string = "initial"
    let state = Ghostty.OSSurfaceView.SearchState(from: .init(c: .init(needle: nil)), pasteboard: pasteboard)
    let host = NSHostingView(rootView: SearchRoot(state: state))
    let window = NSWindow(contentRect: NSRect(x: 50, y: 50, width: 240, height: 60),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
    window.isReleasedWhenClosed = false
    defer { window.contentView = nil; window.close() }
    window.contentView = host
    window.orderFront(nil)
    func spin() { RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.15)) }
    func find(_ view: NSView) -> NSTextField? {
        if let field = view as? NSTextField { return field }
        return view.subviews.compactMap { find($0) }.first
    }
    spin()
    let field = find(host)!
    window.makeFirstResponder(field)
    spin()
    let editor = field.currentEditor() as! NSTextView
    precondition(editor.selectedRange() == NSRange(location: 0, length: 7))
    editor.insertText("typed", replacementRange: editor.selectedRange())
    if !sameTurn {
        spin()
        precondition(state.needle.text == "typed" && pasteboard.string == "typed")
        precondition(editor.selectedRange() == NSRange(location: 5, length: 0))
    }
    pasteboard.string = "external \u{1F600}"
    state.readPasteboardNeedle()
    spin()
    if editor.string != state.needle.text || pasteboard.string != state.needle.text {
        FileHandle.standardError.write(Data("FAIL: real state/editor/pasteboard diverged: editor=\(editor.string), state=\(state.needle.text), pasteboard=\(pasteboard.string ?? "nil")\n".utf8))
        exit(1)
    }
    precondition(editor.selectedRange() == NSRange(location: 0, length: state.needle.text.utf16.count))
    editor.insertText("new", replacementRange: editor.selectedRange())
    spin()
    precondition(state.needle.text == "new" && pasteboard.string == "new")
    precondition(editor.selectedRange() == NSRange(location: 3, length: 0))
    editor.deleteBackward(nil)
    spin()
    precondition(state.needle.text == "ne" && pasteboard.string == "ne")
    editor.insertText("abc", replacementRange: editor.selectedRange())
    editor.insertText("def", replacementRange: editor.selectedRange())
    spin()
    precondition(state.needle.text == "neabcdef" && pasteboard.string == "neabcdef")
    print("PASS: subsequent typing/deletion and consecutive inserts")
    if sameTurn {
        for index in 0..<20 {
            editor.insertText("local", replacementRange: editor.selectedRange())
            let external = "external-\(index)-\u{1F600}"
            pasteboard.string = external
            state.readPasteboardNeedle()
            spin()
            precondition(state.needle.text == external && editor.string == external && pasteboard.string == external)
            precondition(editor.selectedRange() == NSRange(location: 0, length: external.utf16.count))
        }
        print("PASS: 20 consecutive same-turn edit/external-pasteboard races")
    }
    editor.setSelectedRange(NSRange(location: 2, length: 0))
    spin()
    state.readPasteboardNeedle()
    spin()
    precondition(editor.selectedRange() == NSRange(location: 2, length: 0), "Unchanged pasteboard reset caret")
    state.setNeedle("start-search", selectAll: false)
    spin()
    precondition(editor.string == "start-search" && pasteboard.string == "start-search")
    window.makeFirstResponder(nil)
    pasteboard.string = "background replacement"
    state.readPasteboardNeedle()
    spin()
    window.makeFirstResponder(field)
    spin()
    let resumedEditor = field.currentEditor() as! NSTextView
    precondition(resumedEditor.string == state.needle.text)
    precondition(resumedEditor.selectedRange() == NSRange(location: 0, length: state.needle.text.utf16.count))
    print("PASS: production SearchState, field editor and isolated find-pasteboard flow")
}
'''
with tempfile.TemporaryDirectory(prefix="ghostty-search-state-") as directory:
    directory = pathlib.Path(directory)
    swift = directory / "main.swift"
    calls = "\n".join(f"SurfaceView_SearchStateTests().{name}()" for name in names)
    runner = ("\n@main struct Runner { @MainActor static func main() {\n" + calls +
              '\nprint("PASS: 9 unchanged upstream SearchState tests (macro adapter)")\n' +
              f"checkField(sameTurn: {str(args.same_turn_replacement).lower()})\n}}}}\n")
    if args.compare_upstream_fallback:
        # Keep the actual SearchState, unique pasteboard and native SwiftUI field.
        # The one changed variable is the background selection bridge.
        probe = harness[:harness.index('    precondition(editor.selectedRange()')]
        probe += r'''
    editor.setSelectedRange(NSRange(location: 7, length: 0))
    spin()
    pasteboard.string = "external \u{1F600}"
    state.readPasteboardNeedle()
    spin()
    let before = editor.selectedRange()
    let externalText = state.needle.text
    let textSynced = editor.string == externalText && pasteboard.string == externalText
    editor.insertText("new", replacementRange: editor.selectedRange())
    spin()
    let editedText = state.needle.text
    let settledSync = editor.string == editedText && pasteboard.string == editedText
    editor.insertText("local", replacementRange: editor.selectedRange())
    pasteboard.string = "same-turn-external"
    state.readPasteboardNeedle()
    spin()
    let report: [String: Any] = [
        "externalTextSynced": textSynced,
        "selectedLocation": before.location, "selectedLength": before.length,
        "expectedSelectedLength": externalText.utf16.count,
        "typedText": editedText, "settledTextSynced": settledSync,
        "sameTurnEditor": editor.string, "sameTurnModel": state.needle.text,
        "sameTurnPasteboard": pasteboard.string ?? ""
    ]
    let bytes = try! JSONSerialization.data(withJSONObject: report, options: [.sortedKeys])
    print("COMPARISON:" + String(data: bytes, encoding: .utf8)!)
}
'''
        bridge = ".background(TextFieldSelectionBridge(text: text, selection: $textSelection))"
        assert production.count(bridge) == 1
        for optimize in ("-Onone", "-O"):
            for label, implementation in (("current", production),
                                          ("upstream-fallback", production.replace(bridge, ""))):
                swift.write_text(implementation + tests + probe + runner)
                binary = directory / "compare"
                subprocess.run(["swiftc", "-parse-as-library", optimize,
                                "-I", str(root / "macos/GhosttyKit.xcframework/macos-arm64_x86_64/Headers"),
                                str(swift), "-o", str(binary)], check=True)
                result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
                assert result.returncode == 0, result.stdout + result.stderr
                line = next(line for line in result.stdout.splitlines() if line.startswith("COMPARISON:"))
                report = json.loads(line.removeprefix("COMPARISON:"))
                assert report["externalTextSynced"] and report["settledTextSynced"], report
                if label == "current":
                    assert report["selectedLocation"] == 0, report
                    assert report["selectedLength"] == report["expectedSelectedLength"], report
                    assert report["typedText"] == "new", report
                    assert report["sameTurnEditor"] == report["sameTurnModel"] == report["sameTurnPasteboard"] == "same-turn-external", report
                # Report fallback behavior, rather than requiring it to be broken.
                print(f"{optimize} {label}: {json.dumps(report, sort_keys=True)}", flush=True)
        raise SystemExit(0)
    swift.write_text(production + tests + harness + runner)
    failures = []
    for optimize in ("-Onone", "-O"):
        binary = directory / "check"
        subprocess.run(["swiftc", "-parse-as-library", optimize,
                        "-I", str(root / "macos/GhosttyKit.xcframework/macos-arm64_x86_64/Headers"),
                        str(swift), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
        print(f"{optimize}: {result.stdout.strip()}", flush=True)
        if result.returncode != 0:
            print(result.stderr, flush=True)
            failures.append(optimize)
    if args.ablate:
        statement = ("editor.string != self.text" if args.same_turn_replacement else
                     "setNeedle(pasteboardNeedle, selectAll: true)")
        replacement = ("false" if args.same_turn_replacement else
                       "setNeedle(pasteboardNeedle, selectAll: false)")
        assert production.count(statement) == 1, "Update the search-state mutation"
        swift.write_text(production.replace(statement, replacement) +
                         tests + harness + runner)
        subprocess.run(["swiftc", "-parse-as-library", "-Onone",
                        "-I", str(root / "macos/GhosttyKit.xcframework/macos-arm64_x86_64/Headers"),
                        str(swift), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
        diagnostic = "real state/editor/pasteboard diverged" if args.same_turn_replacement else "Upstream assertion failed"
        assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
        print("PASS: compiled search-state regression mutant rejected")
    assert not failures, f"Production search-state integration failed: {failures}"
