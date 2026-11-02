import AppKit

precondition(AXIsProcessTrusted(), "Existing Accessibility permission required; no prompt requested")
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
if CommandLine.arguments[1] == "--preflight" { exit(0) }
let pid = pid_t(CommandLine.arguments[1])!
let action = CommandLine.arguments[2]
let root = AXUIElementCreateApplication(pid)

func attribute(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
    var value: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, key as CFString, &value) == .success ? value : nil
}
func descendants(_ element: AXUIElement, depth: Int = 0) -> [AXUIElement] {
    guard depth < 16 else { return [element] }
    let children = attribute(element, kAXChildrenAttribute) as? [AXUIElement] ?? []
    return [element] + children.flatMap { descendants($0, depth: depth + 1) }
}
func find(role: String, title: String) -> AXUIElement? {
    descendants(root).first {
        attribute($0, kAXRoleAttribute) as? String == role &&
            attribute($0, kAXTitleAttribute) as? String == title
    }
}
func wait(_ message: String, _ predicate: () -> Bool) {
    let deadline = Date().addingTimeInterval(5)
    while Date() < deadline {
        if predicate() { return }
        RunLoop.main.run(until: Date().addingTimeInterval(0.05))
    }
    fatalError(message)
}
func press(_ element: AXUIElement) -> AXError {
    let result = AXUIElementPerformAction(element, kAXPressAction as CFString)
    print("AXPress result: \(result.rawValue)")
    return result
}
if action == "new-window" {
    guard let menu = find(role: kAXMenuItemRole, title: "New Window") else { fatalError("Missing New Window menu") }
    precondition(press(menu) == .success, "New Window action failed")
    wait("Second window did not appear") { (attribute(root, kAXWindowsAttribute) as? [AXUIElement])?.count == 2 }
} else if action == "one-window" {
    wait("Reviewed window did not close") { (attribute(root, kAXWindowsAttribute) as? [AXUIElement])?.count == 1 }
} else if action == "quit" || action == "quit-multi" {
    wait("Missing Quit Ghostty menu") { find(role: kAXMenuItemRole, title: "Quit Ghostty") != nil }
    precondition(press(find(role: kAXMenuItemRole, title: "Quit Ghostty")!) == .success, "Quit menu press failed")
    let title = action == "quit-multi" ? "Review Windows..." : "Terminate"
    wait("Quit confirmation did not appear") { find(role: kAXButtonRole, title: title) != nil }
} else if action == "cancel" {
    guard let button = find(role: kAXButtonRole, title: "Cancel") else { fatalError("Missing Cancel button") }
    let result: AXError = CommandLine.arguments.contains("--skip-cancel") ? .success : press(button)
    // Monterey can report an AX error after the sheet has already been dismissed.
    // Require the state transition here and a fresh live child heartbeat outside.
    precondition(result == .success || result == .attributeUnsupported, "Cancel AX error: \(result.rawValue)")
    wait("Quit sheet survived cancellation") {
        find(role: kAXButtonRole, title: "Terminate") == nil &&
            find(role: kAXButtonRole, title: "Review Windows...") == nil
    }
} else if action == "review" {
    guard let button = find(role: kAXButtonRole, title: "Review Windows...") else { fatalError("Missing Review button") }
    let result = press(button)
    precondition(result == .success || result == .attributeUnsupported, "Review AX error: \(result.rawValue)")
    wait("Review did not present a sheet") { find(role: kAXButtonRole, title: "Terminate") != nil }
} else if action == "accept" || action == "accept-all" {
    let title = action == "accept-all" ? "Terminate Processes" : "Terminate"
    wait("Missing \(title) button") { find(role: kAXButtonRole, title: title) != nil }
    let button = find(role: kAXButtonRole, title: title)!
    let result = press(button)
    precondition(result == .success || result == .attributeUnsupported || result == .cannotComplete,
                 "Accept AX error: \(result.rawValue)")
    // The parent runner must observe clean app exit and child disappearance.
} else {
    fatalError("Unknown action")
}
print("PASS: native quit action \(action)")
