#!/usr/bin/env python3
"""Check production scripting text accessors and their reader/policy boundaries.

Compiles exact accessor bodies with instrumented readers, not the full app.
Real C ownership and PTY/Apple-event text checks remain separate suites.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Features/AppleScript/ScriptTerminal.swift").read_text()


def accessor(name):
    start = source.index(f"    @objc({name})")
    end = source.index("\n    }", start) + len("\n    }")
    return source[start:end]


methods = "\n".join(accessor(name) for name in ("fullContents", "visibleText", "selectedText"))
harness = r'''
import AppKit
final class Policy {
    var isAppleScriptEnabled = true
}
let NSApp = Policy()
final class Cache {
    var calls = 0
    let value: String
    init(_ value: String = "viewport") { self.value = value }
    func get() -> String { calls += 1; return value }
}
final class View {
    let cachedScreenContents = Cache("scrollback")
    var fullCalls: Int { cachedScreenContents.calls }
    var snapshotCalls = 0
    var selectionCalls = 0
    var selection: String? = "\u{1f680}e\u{301}"
    let cachedVisibleContents = Cache()
    func accessibilityValue() -> Any? { snapshotCalls += 1; return "scrollback" }
    func accessibilitySelectedText() -> String? { snapshotCalls += 1; return selection }
    func selectedText() -> String? { selectionCalls += 1; return selection }
}
final class Script: NSObject {
    weak var surfaceView: View?
METHODS
}
func check(_ value: Bool, _ message: String) {
    if !value {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}
let script = Script()
var view: View? = View()
script.surfaceView = view
check(script.selectedText == view!.selection, "selection value")
check(view!.selectionCalls == 1 && view!.snapshotCalls == 0 && view!.fullCalls == 0,
      "selected-only read must not request full snapshot")
check(script.fullContents == "scrollback" && view!.fullCalls == 1, "full reader")
check(script.visibleText == "viewport" && view!.cachedVisibleContents.calls == 1, "visible reader")
NSApp.isAppleScriptEnabled = false
check(script.fullContents.isEmpty && script.visibleText.isEmpty && script.selectedText.isEmpty, "disabled values")
check(view!.selectionCalls == 1 && view!.snapshotCalls == 0 && view!.fullCalls == 1 &&
      view!.cachedVisibleContents.calls == 1, "disabled accessor must not call reader")
NSApp.isAppleScriptEnabled = true
view!.selection = nil
check(script.selectedText.isEmpty, "no selection")
view = nil
check(script.surfaceView == nil, "weak surface lifetime")
check(script.fullContents.isEmpty && script.visibleText.isEmpty && script.selectedText.isEmpty, "expired surface")
print("PASS: scripting text readers, disabled access and weak surface lifetime")
'''.replace("METHODS", methods)
with tempfile.TemporaryDirectory(prefix="ghostty-script-text-") as directory:
    work = pathlib.Path(directory)
    swift = work / "main.swift"
    binary = work / "check"
    for optimization in ("-Onone", "-O"):
        swift.write_text(harness)
        subprocess.run(["xcrun", "swiftc", optimization, str(swift), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
        mutant = harness.replace('guard NSApp.isAppleScriptEnabled else { return "" }', '')
        assert mutant != harness
        swift.write_text(mutant)
        subprocess.run(["xcrun", "swiftc", optimization, str(swift), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True)
        assert result.returncode != 0 and "disabled values" in result.stderr, result
        print(f"PASS: {optimization} accessor-policy bypass mutant rejected")
        mutant = harness.replace("surfaceView?.selectedText()", "surfaceView?.accessibilitySelectedText()")
        assert mutant != harness
        swift.write_text(mutant)
        subprocess.run(["xcrun", "swiftc", optimization, str(swift), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True, text=True)
        assert result.returncode != 0 and "selected-only read must not request full snapshot" in result.stderr, result
        print(f"PASS: {optimization} full-snapshot reader mutant rejected")
