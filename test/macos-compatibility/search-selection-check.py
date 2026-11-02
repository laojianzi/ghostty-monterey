#!/usr/bin/env python3
"""Exercise the production SwiftUI text field and AppKit selection bridge.

Uses real field-editor operations, including UTF-16 and marked text, but is not
an end-to-end physical-keyboard/IME test. Requires a WindowServer session.
"""

import argparse
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Helpers/Backport.swift").read_text()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--same-turn-replacement", action="store_true",
                    help="probe the SwiftUI edit/external-write race, also without the bridge")
args = parser.parse_args()
harness = r"""
import Cocoa
import SwiftUI

final class Model: ObservableObject {
    @Published var text = "alpha beta"
    @Published var selection: Range<String.Index>?
}
let model = Model()
let other = Model()
var submissions = 0
var exits = 0
struct Root: View {
    @ObservedObject var model: Model
    var body: some View {
        VStack {
            BackportSelectionTextField("Other", text: Binding(get: { other.text }, set: { other.text = $0 }),
                                       selection: Binding(get: { other.selection }, set: { other.selection = $0 }))
                .frame(width: 200, height: 35)
            BackportSelectionTextField("Search", text: $model.text, selection: $model.selection)
                .textFieldStyle(.plain)
                .frame(width: 200, height: 35)
                .onSubmit { submissions += 1 }
                .onExitCommand { exits += 1 }
        }
    }
}
let app = NSApplication.shared
let host = NSHostingView(rootView: Root(model: model))
let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 250, height: 80),
                      styleMask: [.titled, .closable], backing: .buffered, defer: false)
window.contentView = host
window.orderFront(nil)
func spin() { RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.15)) }
func field(_ view: NSView) -> NSTextField? {
    if let field = view as? NSTextField { return field }
    return view.subviews.compactMap { field($0) }.last
}
spin()
guard let field = field(host) else { fatalError("No SwiftUI text field") }
window.makeFirstResponder(field)
spin()
guard let editor = field.currentEditor() as? NSTextView else { fatalError("No editor") }
editor.setSelectedRange(NSRange(location: 10, length: 0))
model.selection = model.text.startIndex..<model.text.index(model.text.startIndex, offsetBy: 5)
spin()
if editor.selectedRange() != NSRange(location: 0, length: 5) {
    FileHandle.standardError.write(Data("FAIL: programmatic selection ignored\n".utf8))
    exit(1)
}
print("PASS: programmatic selection")

editor.setSelectedRange(NSRange(location: 6, length: 4))
spin()
precondition(model.selection.map { NSRange($0, in: model.text) } == NSRange(location: 6, length: 4), "User selection not reflected")
model.text = "a\u{1F600}e\u{301}z"
model.selection = model.text.index(after: model.text.startIndex)..<model.text.index(before: model.text.endIndex)
spin()
precondition(editor.string == model.text)
precondition(editor.selectedRange() == NSRange(location: 1, length: 4), "UTF16 selection incorrect")
model.selection = nil
spin()
editor.setSelectedRange(NSRange(location: 5, length: 0))
spin()
precondition(model.selection.map { NSRange($0, in: model.text) } == NSRange(location: 5, length: 0))
window.makeFirstResponder(nil)
model.selection = model.text.startIndex..<model.text.endIndex
spin()
window.makeFirstResponder(field)
spin()
precondition((field.currentEditor() as? NSTextView)?.selectedRange() == NSRange(location: 0, length: 6), "Deferred selection not applied")
print("PASS: two-way selection, UTF16 and focus re-entry")

let current = field.currentEditor() as! NSTextView
current.insertText("x", replacementRange: current.selectedRange())
spin()
precondition(model.text == "x", "Editing did not update model")
if current.selectedRange() != NSRange(location: 1, length: 0) {
    FileHandle.standardError.write(Data("FAIL: editing moved caret\n".utf8))
    exit(1)
}
current.deleteBackward(nil)
spin()
precondition(model.text.isEmpty, "Deletion did not update model")
precondition(current.selectedRange() == NSRange(location: 0, length: 0), "Deletion moved caret")
model.text = "quick update"
model.selection = model.text.startIndex..<model.text.endIndex
model.text = "last"
model.selection = model.text.startIndex..<model.text.endIndex
spin()
precondition(current.string == "last" && current.selectedRange() == NSRange(location: 0, length: 4),
             "Queued selection did not use latest text/range")
model.text = "abcdef"
model.selection = model.text.startIndex..<model.text.endIndex
spin()
current.setMarkedText("composing", selectedRange: NSRange(location: 2, length: 0), replacementRange: current.selectedRange())
spin()
let markedSelection = current.selectedRange()
model.selection = model.text.startIndex..<model.text.endIndex
spin()
precondition(current.hasMarkedText(), "Bridge ended marked-text composition")
precondition(current.selectedRange() == markedSelection, "Bridge moved marked-text selection")
current.unmarkText()
spin()
precondition(other.selection == nil, "Bridge wrote another field's selection")
print("PASS: unrelated field isolation and marked-text preservation")
current.doCommand(by: #selector(NSResponder.insertNewline(_:)))
spin()
precondition(submissions == 1, "SwiftUI submit handler lost")
current.doCommand(by: #selector(NSResponder.cancelOperation(_:)))
spin()
precondition(exits == 1, "SwiftUI exit handler lost")
print("PASS: SwiftUI submit and exit handlers preserved")
func allFields(_ view: NSView) -> [NSTextField] {
    if let field = view as? NSTextField { return [field] }
    return view.subviews.flatMap { allFields($0) }
}
let sibling = allFields(host).first!
precondition(sibling !== field)
window.makeFirstResponder(sibling)
spin()
let siblingEditor = sibling.currentEditor() as! NSTextView
siblingEditor.setSelectedRange(NSRange(location: 2, length: 3))
spin()
precondition(other.selection.map { NSRange($0, in: other.text) } == NSRange(location: 2, length: 3),
             "Selection was attributed to the wrong field")
let siblingRange = siblingEditor.selectedRange()
model.selection = model.text.startIndex..<model.text.endIndex
spin()
precondition(siblingEditor.selectedRange() == siblingRange, "Inactive field moved active sibling's selection")
window.makeFirstResponder(field)
spin()
precondition((field.currentEditor() as! NSTextView).selectedRange() == NSRange(location: 0, length: model.text.utf16.count))
print("PASS: shared field editor switches between independent bindings")
let activeEditor = field.currentEditor() as! NSTextView
activeEditor.insertText("typed", replacementRange: activeEditor.selectedRange())
spin()
model.text = "external replacement"
model.selection = model.text.startIndex..<model.text.endIndex
spin()
precondition(activeEditor.string == model.text)
if activeEditor.selectedRange() != NSRange(location: 0, length: model.text.utf16.count) {
    FileHandle.standardError.write(Data("FAIL: external selection lost after native edit\n".utf8))
    exit(1)
}
print("PASS: external replacement after settled native edit")
weak var releasedHost: NSView?
weak var releasedModel: Model?
autoreleasepool {
    let transient = Model()
    let view = NSHostingView(rootView: Root(model: transient))
    let temporaryWindow = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 250, height: 80),
                                   styleMask: [.titled], backing: .buffered, defer: false)
    temporaryWindow.isReleasedWhenClosed = false
    temporaryWindow.contentView = view
    temporaryWindow.orderFront(nil)
    spin()
    transient.selection = transient.text.startIndex..<transient.text.endIndex
    releasedHost = view
    releasedModel = transient
    temporaryWindow.contentView = nil
    temporaryWindow.close()
}
spin()
precondition(releasedHost == nil && releasedModel == nil, "Selection bridge retained a dismissed view/model")
print("PASS: dismissed hosting view and model released with queued selection work")
"""

with tempfile.TemporaryDirectory(prefix="ghostty-search-selection-") as directory:
    directory = pathlib.Path(directory)
    bridge = ".background(TextFieldSelectionBridge(text: text, selection: $textSelection))"
    assert source.count(bridge) == 1, "Update the mutation for the current selection bridge"
    if args.same_turn_replacement:
        start = harness.index('editor.setSelectedRange(NSRange(location: 10')
        harness = harness[:start] + r'''
editor.setSelectedRange(NSRange(location: 0, length: 10))
editor.insertText("typed", replacementRange: editor.selectedRange())
model.text = "external replacement"
spin()
print("editor=\(editor.string), model=\(model.text)")
exit(editor.string == model.text ? 0 : 1)
'''
    failures = []
    mutations = [("production", source, None),
                 ("no-selection-mutant", source.replace(bridge, ""), "programmatic selection ignored")]
    if not args.same_turn_replacement:
        statement = "if self.edited {"
        assert source.count(statement) == 1, "Update the edit-preservation mutation"
        mutations.append(("stale-selection-mutant", source.replace(statement, "if false {"), "editing moved caret"))
    for optimize in ("-Onone", "-O"):
        for name, implementation, diagnostic in mutations:
            swift = directory / "main.swift"
            swift.write_text(implementation + "\n" + harness)
            binary = directory / name
            subprocess.run(["swiftc", optimize, str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if args.same_turn_replacement:
                print(f"{optimize} {name}: {'PASS' if result.returncode == 0 else 'FAIL'}: {result.stdout.strip()}")
                if name == "production" and result.returncode != 0:
                    failures.append((optimize, name))
                if name != "production":
                    assert result.returncode != 0, "Unbridged control unexpectedly passed; reassess workaround"
                continue
            if name == "production":
                assert result.returncode == 0, result.stderr
                assert "Modifying state during view update" not in result.stderr, result.stderr
                print(f"{optimize}: {result.stdout.strip()}")
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, result.stderr
                print(f"{optimize}: PASS: compiled {name} rejected")
    assert not failures, f"Same-turn replacement failed: {failures}"
