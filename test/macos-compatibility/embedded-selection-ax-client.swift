import AppKit

precondition(AXIsProcessTrusted(), "Existing Accessibility permission required; no prompt")
let root = AXUIElementCreateApplication(pid_t(CommandLine.arguments[1])!)
let rectangle = CommandLine.arguments[2] == "rectangle"
let expected = rectangle ? ["23456", "CDEFG", "stuvw"] : ["23456789abcdef\nABCDEFGHIJKLMNOP\nqrstuvw"]
func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var value: CFTypeRef?
    precondition(AXUIElementCopyAttributeValue(element, name as CFString, &value) == .success,
                 "Missing AX attribute \(name)")
    return value
}
func find(_ element: AXUIElement, depth: Int = 0) -> AXUIElement? {
    if attribute(element, kAXRoleAttribute) as? String == kAXTextAreaRole { return element }
    guard depth < 12 else { return nil }
    var children: CFTypeRef?
    if AXUIElementCopyAttributeValue(element, kAXChildrenAttribute as CFString, &children) == .success,
       let children = children as? [AXUIElement] {
        for child in children {
            if let text = find(child, depth: depth + 1) { return text }
        }
    }
    return nil
}
let windowValue = attribute(root, kAXWindowsAttribute)
guard let windows = windowValue as? [AXUIElement], windows.count == 1 else {
    fatalError("Expected one remote window")
}
guard let text = find(windows[0]) else { fatalError("Missing remote text area") }
guard
      let whole = attribute(text, kAXValueAttribute) as? String,
      let selected = attribute(text, kAXSelectedTextAttribute) as? String,
      let count = attribute(text, kAXNumberOfCharactersAttribute) as? NSNumber else {
    fatalError("Missing terminal AX tree/text/ranges")
}
precondition(selected == expected.joined(separator: "\n"), "Remote selected text mismatch")
precondition(count.intValue == whole.utf16.count)
print("PASS: remote AX selected text and UTF-16 count; upstream selected-range limitation not claimed fixed")
