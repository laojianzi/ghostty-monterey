#!/usr/bin/env python3
"""Run upstream palette assertions and real SwiftUI/AppKit editor interactions.

Uses the complete production palette view, with no terminal/core stand-ins.
Uses native responder commands and synthesized hosting-view key equivalents,
not physical keyboard events or proof of full-app event dispatch.
"""

import pathlib
import platform
import re
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
palette = root / "macos/Sources/Features/Command Palette/CommandPalette.swift"
terminal = (root / "macos/Sources/Features/Command Palette/TerminalCommandPalette.swift").read_text()
sorter = terminal[terminal.index("func sortedTerminalPaletteOptions("):terminal.index("struct TerminalCommandPaletteView:")]
tests = (root / "macos/Tests/CommandPaletteTests.swift").read_text()
methods = re.findall(r"@Test func (\w+)\(\)", tests)
assert len(methods) == tests.count("@Test") == 3, "Update the bounded upstream adapter"
tests = tests.replace("import Testing", "").replace("@testable import Ghostty", "")
tests = tests.replace("@Test ", "").replace("#expect(", "check(")
assert not re.search(r"#(?:expect|require)|@(?:Test|Suite)", tests)

harness = r'''
import SwiftUI

func check(_ condition: @autoclosure () -> Bool, _ message: String = "Upstream assertion failed",
           file: StaticString = #file, line: UInt = #line) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message) (\(file):\(line))\n".utf8))
        exit(1)
    }
}

final class Model: ObservableObject {
    @Published var presented = true
    var actions: [String] = []
    lazy var options = ["New Window", "New Tab", "Quit"].map { title in
        CommandOption(title: title) { [weak self] in self?.actions.append(title) }
    }
}

struct Root: View {
    @ObservedObject var model: Model
    var body: some View {
        if model.presented {
            CommandPaletteView(isPresented: $model.presented, options: model.options)
        } else {
            Text("Dismissed")
        }
    }
}

func spin() { RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.15)) }
func findField(_ view: NSView) -> NSTextField? {
    if let field = view as? NSTextField, field.isEditable { return field }
    return view.subviews.compactMap { findField($0) }.first
}

@main struct Runner {
    @MainActor static func main() {
        UPSTREAM_CALLS
        print("PASS: three unchanged upstream palette test bodies")
        check("New Window".matchedIndices(for: "nw")?.count == 2, "Initials matching")
        check("New Window".matchedIndices(for: "WINDOW")?.count == 6, "Case-insensitive substring")
        check("New Window".matchedIndices(for: "wz") == nil, "Nonmatch accepted")
        // Use the OS color list rather than assuming localization or RGB values.
        check(!NSColor.colorNames.isEmpty, "Missing native color list")
        for name in NSColor.colorNames {
            guard let native = NSColor(named: name) else { continue }
            let color = CommandOption(title: "No text match", leadingColor: Color(nsColor: native)) {}
            let text = CommandOption(title: name) {}
            check(CommandOptionMatch.colorMatchScore(for: color.leadingColor, query: name) == 1,
                  "Exact color not recognized")
            check([text, color].filteredAndSorted(query: name).first == color, "Color ranking")
        }

        _ = NSApplication.shared
        let model = Model()
        let host = NSHostingView(rootView: Root(model: model))
        let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 540, height: 320),
                              styleMask: [.titled], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = host
        window.orderFront(nil)
        func editor() -> NSTextView {
            spin()
            guard let field = findField(host) else { fatalError("No palette query field") }
            // Locked sessions cannot prove physical activation/autofocus. Set
            // first responder explicitly to exercise native editor/delegate flow.
            window.makeFirstResponder(field)
            spin()
            guard let editor = field.currentEditor() as? NSTextView else { fatalError("No editor") }
            return editor
        }
        func reopen() -> NSTextView {
            model.presented = true
            let result = editor()
            check(result.string.isEmpty, "Query survives reopen")
            return result
        }
        func type(_ value: String, into editor: NSTextView) {
            editor.setSelectedRange(NSRange(location: 0, length: editor.string.utf16.count))
            editor.insertText(value, replacementRange: editor.selectedRange())
            spin()
        }
        func submit(_ editor: NSTextView) {
            editor.doCommand(by: #selector(NSResponder.insertNewline(_:)))
            spin()
            check(!model.presented, "Submit did not dismiss")
        }
        func move(down: Bool) {
            let character = String(UnicodeScalar(down ? NSDownArrowFunctionKey : NSUpArrowFunctionKey)!)
            let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [],
                                        timestamp: 0, windowNumber: window.windowNumber, context: nil,
                                        characters: character, charactersIgnoringModifiers: character,
                                        isARepeat: false, keyCode: down ? 125 : 126)!
            check(host.performKeyEquivalent(with: event), "Palette shortcut not handled")
            spin()
        }
        func controlMove(down: Bool) {
            let character = down ? "n" : "p"
            let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [.control],
                                        timestamp: 0, windowNumber: window.windowNumber, context: nil,
                                        characters: character, charactersIgnoringModifiers: character,
                                        isARepeat: false, keyCode: down ? 45 : 35)!
            check(host.performKeyEquivalent(with: event), "Palette control shortcut not handled")
            spin()
        }

        submit(editor())
        check(model.actions.isEmpty, "Empty initial query unexpectedly executed")
        var input = reopen()
        type("nw", into: input)
        submit(input)
        check(model.actions == ["New Window"], "Typed query did not select first match")

        input = reopen()
        type("new", into: input)
        move(down: true)
        submit(input)
        check(model.actions.last == "New Tab" && model.actions.count == 2, "Down selection")

        input = reopen()
        type("new", into: input)
        move(down: false)
        submit(input)
        check(model.actions.last == "New Tab" && model.actions.count == 3, "Up wraparound")

        input = reopen()
        type("new", into: input)
        move(down: true)
        type("window", into: input)
        submit(input)
        check(model.actions.last == "New Window" && model.actions.count == 4, "Selection after filtering")

        input = reopen()
        type("no such command", into: input)
        move(down: true)
        submit(input)
        check(model.actions.count == 4, "No-match query executed a command")

        input = reopen()
        type("quit", into: input)
        input.doCommand(by: #selector(NSResponder.cancelOperation(_:)))
        spin()
        check(!model.presented && model.actions.count == 4, "Escape executed or failed to dismiss")
        input = reopen()
        type("quit", into: input)
        type("", into: input)
        submit(input)
        check(model.actions.count == 4, "Cleared query retained initial selection")

        input = reopen()
        type("new", into: input)
        controlMove(down: true)
        submit(input)
        check(model.actions.last == "New Tab" && model.actions.count == 5, "Control-N selection")
        input = reopen()
        type("new", into: input)
        controlMove(down: false)
        submit(input)
        check(model.actions.last == "New Tab" && model.actions.count == 6, "Control-P wraparound")
        window.contentView = nil
        window.close()
        spin()
        print("PASS: native query, selection, arrow/control shortcuts, refilter, submit, empty/no-match, Escape and reopen")
    }
}
'''.replace("UPSTREAM_CALLS", "\n".join(f"CommandPaletteFilterTests().{name}()" for name in methods))

with tempfile.TemporaryDirectory(prefix="ghostty-palette-") as directory:
    tmp = pathlib.Path(directory)
    runner = tmp / "Runner.swift"
    runner.write_text(tests + "\n" + sorter + "\n" + harness)
    sources = [str(root / "macos/Sources/Helpers/Extensions" / name)
               for name in ("NSColor+Extension.swift", "OSColor+Extension.swift")]
    production = palette.read_text()
    mutation = "selectedOption?.action()"
    assert production.count(mutation) == 1
    down = "case .move(.down):"
    assert production.count(down) == 1
    for optimization in ("-Onone", "-O"):
        for label, source, diagnostic in (
            ("production", production, None),
            ("no-submit-mutant", production.replace(mutation, "// no action"),
             "Typed query did not select first match"),
            ("no-down-mutant", production.replace(down, down + "\n                    if true { break }"),
             "Down selection"),
        ):
            implementation = tmp / "Palette.swift"
            implementation.write_text(source)
            binary = tmp / "check"
            subprocess.run(["xcrun", "swiftc", optimization, "-D", "DOCK_TILE_PLUGIN",
                            "-target", f"{platform.machine()}-apple-macosx12.0",
                            *sources, str(implementation), str(runner), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=35)
            if label == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimization + ": " + result.stdout.strip())
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, (
                    result.stdout + result.stderr)
                print(optimization + f": PASS: compiled {label} rejected")
