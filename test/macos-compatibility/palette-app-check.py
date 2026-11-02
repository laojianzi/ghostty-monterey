#!/usr/bin/env python3
"""Exercise the built app's command palette with AX, AppleScript and a real PTY.

Only for app-smoke.py's isolated app. Requires existing AX permission; does not
prompt, post keyboard/mouse events, or read/write any clipboard. AX interaction
is not physical keyboard or IME acceptance.
"""

import pathlib
import plistlib
import shlex
import subprocess
import sys
import time

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
pid = int(sys.argv[3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
with (app / "Contents/Info.plist").open("rb") as stream:
    assert plistlib.load(stream)["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.check_output(
        ["osascript", "-"], input=f"tell application {literal(app)}\n{body}\nend tell",
        text=True, timeout=15,
    ).strip()


swift = work / "palette-client.swift"
swift.write_text(r'''
import AppKit

precondition(AXIsProcessTrusted(), "Existing AX permission required; no prompt requested")
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
let pid = pid_t(CommandLine.arguments[1])!
let root = AXUIElementCreateApplication(pid)
func attribute(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
    var value: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, key as CFString, &value) == .success ? value : nil
}
func descendants(_ element: AXUIElement, depth: Int = 0) -> [AXUIElement] {
    if depth >= 16 { return [element] }
    let children = attribute(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
    return [element] + children.flatMap { descendants($0, depth: depth + 1) }
}
func elements() -> [AXUIElement] {
    (attribute(root, kAXWindowsAttribute) as? [AXUIElement] ?? []).flatMap { descendants($0) }
}
func role(_ element: AXUIElement) -> String { attribute(element, kAXRoleAttribute) as? String ?? "" }
func text(_ element: AXUIElement) -> String {
    [kAXTitleAttribute, kAXValueAttribute, kAXDescriptionAttribute].compactMap {
        attribute(element, $0) as? String
    }.joined(separator: " ")
}
func wait(_ message: String, until predicate: () -> Bool) {
    let deadline = Date(timeIntervalSinceNow: 5)
    while Date() < deadline {
        if predicate() { return }
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.05))
    }
    for element in elements() { print("\(role(element)): \(text(element))") }
    fatalError(message)
}
if CommandLine.arguments[2] == "--preflight" { exit(0) }
if CommandLine.arguments[2] == "--closed" {
    wait("Palette field survived dismissal") {
        !elements().contains { role($0) == kAXTextFieldRole }
    }
    wait("Terminal did not regain focus") {
        guard let focused = attribute(root, kAXFocusedUIElementAttribute) else { return false }
        // AXUIElement has no conditional bridge cast; verify the CF type first.
        guard CFGetTypeID(focused) == AXUIElementGetTypeID() else { return false }
        return role(focused as! AXUIElement) == kAXTextAreaRole
    }
    print("PASS: palette dismissed and terminal focus restored")
    exit(0)
}
var query: AXUIElement?
wait("Expected one automatically focused palette query") {
    let fields = elements().filter { role($0) == kAXTextFieldRole }
    guard fields.count == 1,
          (attribute(fields[0], kAXFocusedAttribute) as? NSNumber)?.boolValue == true else { return false }
    query = fields[0]
    return true
}
let field = query!
precondition(attribute(field, kAXValueAttribute) as? String == "", "Reopened palette retained its query")
func setQuery(_ value: String) {
    precondition(AXUIElementSetAttributeValue(field, kAXValueAttribute as CFString, value as CFString) == .success,
                 "Query is not AX editable")
}
setQuery("monterey-no-matching-command-72491")
wait("Unmatched query did not filter the live command model") {
    elements().contains { role($0) == kAXStaticTextRole && text($0).contains("No matches") }
}
setQuery("New Tab")
var row: AXUIElement?
wait("New Tab command not found after changing the query") {
    guard !elements().contains(where: { text($0).contains("No matches") }) else { return false }
    row = elements().first {
        role($0) == kAXButtonRole && descendants($0).contains { text($0).contains("New Tab") }
    }
    return row != nil
}
var actions: CFArray?
let actionResult = AXUIElementCopyActionNames(row!, &actions)
precondition(actionResult == .success && (actions as? [String])?.contains(kAXPressAction) == true,
             "Command row does not advertise AXPress")
let pressResult = AXUIElementPerformAction(row!, kAXPressAction as CFString)
print("Palette press result=\(pressResult.rawValue)")
fflush(stdout)
// Monterey returns attributeUnsupported even when this self-dismissing SwiftUI
// action executes. Never retry: the caller checks exactly one new tab, focus and
// its live PTY. An error code alone proves neither execution nor non-execution.
precondition(pressResult == .success || pressResult == .attributeUnsupported,
             "Unexpected AX action failure")
print("PASS: actual palette autofocus, no-match filtering and query replacement; action outcome checked by caller")
''')
client = work / "palette-client"
subprocess.run(["xcrun", "swiftc", str(swift), "-o", str(client)], check=True)


def check(mode):
    subprocess.run([str(client), str(pid), mode], check=True, timeout=18)


check("--preflight")
original = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(original)}"
assert script("return count of windows") == "1"
assert script("return count of tabs of front window") == "1"
for cycle in range(2):
    assert script(f'perform action "toggle_command_palette" on {target}') == "true"
    check("--select")
    deadline = time.monotonic() + 5
    while script("return count of tabs of front window") != "2" and time.monotonic() < deadline:
        time.sleep(0.05)
    assert script("return count of tabs of front window") == "2", "Palette did not create a real tab"
    created = script("return id of focused terminal of selected tab of front window")
    assert created != original
    try:
        check("--closed")
        output = work / f"palette-pty-{cycle}"
        command = "printf palette-tab-alive > " + shlex.quote(str(output))
        script(f'''set t to terminal id {literal(created)}
input text {literal(command)} to t
send key "enter" to t''')
        deadline = time.monotonic() + 5
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert output.read_text() == "palette-tab-alive", "Palette-created tab lost its PTY"
    finally:
        script(f"close (terminal id {literal(created)})")
    assert script("return count of tabs of front window") == "1"
    assert script("return id of focused terminal of selected tab of front window") == original
    print(f"PASS: palette cycle {cycle + 1}, real tab/PTY creation and original surface recovery", flush=True)
