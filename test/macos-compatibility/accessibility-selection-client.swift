import AppKit

let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
precondition(AXIsProcessTrusted(), "Existing Accessibility permission required; no prompt requested")
let pid = pid_t(CommandLine.arguments[1])!
let marker = CommandLine.arguments[2]
let root = AXUIElementCreateApplication(pid)

func attribute(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
    var value: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, key as CFString, &value) == .success ? value : nil
}

func find(_ element: AXUIElement, role: String, title: String? = nil, depth: Int = 0) -> AXUIElement? {
    if attribute(element, kAXRoleAttribute) as? String == role,
       title == nil || attribute(element, kAXTitleAttribute) as? String == title { return element }
    if depth < 15, let children = attribute(element, kAXChildrenAttribute) as? [AXUIElement] {
        for child in children {
            if let match = find(child, role: role, title: title, depth: depth + 1) { return match }
        }
    }
    return nil
}

_ = NSApplication.shared
guard let windows = attribute(root, kAXWindowsAttribute) as? [AXUIElement], windows.count == 1,
      let text = find(windows[0], role: kAXTextAreaRole),
      let menu = find(root, role: kAXMenuItemRole, title: "Select All"),
      let before = attribute(text, kAXValueAttribute) as? String,
      before.contains(marker) else {
    fatalError("Expected one isolated English-language app window, terminal marker and Select All menu")
}

var observer: AXObserver?
var notices = 0
precondition(AXObserverCreate(pid, { _, _, _, context in
    context!.assumingMemoryBound(to: Int.self).pointee += 1
}, &observer) == .success, "Cannot create AX observer")
let obs = observer!
withUnsafeMutablePointer(to: &notices) { pointer in
    precondition(AXObserverAddNotification(
        obs, text, kAXSelectedTextChangedNotification as CFString, pointer) == .success,
        "Cannot observe selection changes")
    CFRunLoopAddSource(CFRunLoopGetCurrent(), AXObserverGetRunLoopSource(obs), .defaultMode)
    defer {
        AXObserverRemoveNotification(obs, text, kAXSelectedTextChangedNotification as CFString)
        CFRunLoopRemoveSource(CFRunLoopGetCurrent(), AXObserverGetRunLoopSource(obs), .defaultMode)
    }
    // Only this app's Select All menu is invoked. The harness disables
    // copy-on-select and clipboard access; no global keyboard event is sent.
    precondition(AXUIElementPerformAction(menu, kAXPressAction as CFString) == .success,
                 "Select All action failed")
    let deadline = Date(timeIntervalSinceNow: 3)
    while pointer.pointee == 0 && Date() < deadline {
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.05))
    }
}
guard let selected = attribute(text, kAXSelectedTextAttribute) as? String,
      let value = attribute(text, kAXValueAttribute) as? String,
      let raw = attribute(text, kAXSelectedTextRangeAttribute),
      CFGetTypeID(raw) == AXValueGetTypeID() else { fatalError("Missing selected text/range") }
var range = CFRange()
// The Core Foundation type ID is checked before the required bridge cast.
// swiftlint:disable:next force_cast
precondition(AXValueGetValue(raw as! AXValue, .cfRange, &range), "Invalid selected range")
print("Selection notifications=\(notices); range=\(range); text UTF-16 length=\(value.utf16.count)")
fflush(stdout)
precondition(notices > 0, "Missing selection notification")
precondition(selected == value && selected.contains(marker), "Select All did not select the displayed marker text")
precondition(range.location == 0 && range.length == value.utf16.count,
             "Selected range must describe the selected text, not terminal cell offsets")
guard let ranges = attribute(text, kAXSelectedTextRangesAttribute) as? [AXValue], ranges.count == 1 else {
    fatalError("Select All must expose one selected range")
}
var multipleRange = CFRange()
precondition(AXValueGetValue(ranges[0], .cfRange, &multipleRange)
             && multipleRange.location == range.location && multipleRange.length == range.length,
             "Plural selected ranges must match the single selected range")
var substring: CFTypeRef?
let result = AXUIElementCopyParameterizedAttributeValue(
    text, kAXStringForRangeParameterizedAttribute as CFString, raw, &substring)
precondition(result == .success && substring as? String == selected,
             "Selected range does not reproduce selected text")
print("PASS: cross-process Select All action, selection notification and UTF-16 selected-text range")

if CommandLine.arguments.contains("--write-selection") {
    var writable = DarwinBoolean(false)
    precondition(AXUIElementIsAttributeSettable(text, kAXSelectedTextRangeAttribute as CFString, &writable) == .success
                 && writable.boolValue, "A real selection setter is required")
    let desired = (value as NSString).range(of: "SERVICE-PTY:")
    precondition(desired.location != NSNotFound)
    var target = CFRange(location: desired.location, length: desired.length)
    let encoded = AXValueCreate(.cfRange, &target)!
    precondition(AXUIElementSetAttributeValue(text, kAXSelectedTextRangeAttribute as CFString, encoded) == .success)
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.2))
    precondition(attribute(text, kAXSelectedTextAttribute) as? String == "SERVICE-PTY:",
                 "Setter must change the actual terminal selection")
    var invalid = CFRange(location: value.utf16.count + 100, length: 1)
    _ = AXUIElementSetAttributeValue(text, kAXSelectedTextRangeAttribute as CFString, AXValueCreate(.cfRange, &invalid)!)
    precondition(attribute(text, kAXSelectedTextAttribute) as? String == "SERVICE-PTY:",
                 "Invalid range must preserve selection")
    var clear = CFRange(location: 0, length: 0)
    precondition(AXUIElementSetAttributeValue(text, kAXSelectedTextRangeAttribute as CFString,
                                           AXValueCreate(.cfRange, &clear)!) == .success)
    precondition((attribute(text, kAXSelectedTextAttribute) as? String ?? "").isEmpty,
                 "Empty range must clear actual selection")
    print("PASS: writable AX selection changes, rejects invalid range and clears")
}

if CommandLine.arguments.contains("--rectangle") {
    precondition(CGPreflightPostEventAccess(), "Existing event-post permission required; never requests consent")
    let native = CommandLine.arguments.contains("--native-rectangle")
    let previousApp = NSWorkspace.shared.frontmostApplication
    let previousPointer = CGEvent(source: nil)?.location
    defer {
        if native {
            if let point = previousPointer { CGWarpMouseCursorPosition(point) }
            previousApp?.activate(options: [.activateIgnoringOtherApps])
        }
    }
    if native {
        guard let app = NSRunningApplication(processIdentifier: pid) else { fatalError("Fixture app exited") }
        app.unhide()
        app.activate(options: [.activateIgnoringOtherApps])
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.5))
        precondition(NSWorkspace.shared.frontmostApplication?.processIdentifier == pid)
    }
    let columns = Double(CommandLine.arguments[4])!
    let rows = Double(CommandLine.arguments[5])!
    guard let position = attribute(text, kAXPositionAttribute),
          let size = attribute(text, kAXSizeAttribute),
          CFGetTypeID(position) == AXValueGetTypeID(), CFGetTypeID(size) == AXValueGetTypeID() else {
        fatalError("Missing terminal AX frame")
    }
    var origin = CGPoint.zero
    var extent = CGSize.zero
    // swiftlint:disable force_cast
    precondition(AXValueGetValue(position as! AXValue, .cgPoint, &origin))
    precondition(AXValueGetValue(size as! AXValue, .cgSize, &extent))
    // swiftlint:enable force_cast
    let cell = CGSize(width: floor(extent.width / columns), height: floor(extent.height / rows))
    print("Rectangle frame=\(origin) \(extent), grid=\(columns)x\(rows), cell=\(cell)")
    precondition(cell.width > 0 && cell.height > 0)
    func send(_ type: CGEventType, column: Double, row: Double) {
        let point = CGPoint(x: origin.x + column * cell.width, y: origin.y + row * cell.height)
        let event = CGEvent(mouseEventSource: nil, mouseType: type, mouseCursorPosition: point,
                            mouseButton: .left)!
        event.flags = .maskAlternate
        event.setIntegerValueField(.mouseEventClickState, value: 1)
        if native {
            // Explicit opt-in for real WindowServer routing, never an implicit
            // fallback from PID posting. Check focus before every event.
            precondition(NSWorkspace.shared.frontmostApplication?.processIdentifier == pid)
            event.post(tap: .cghidEventTap)
        } else {
            // Monterey may deliver PID-posted events with windowNumber zero.
            event.postToPid(pid)
        }
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.08))
    }
    send(.mouseMoved, column: 2.2, row: 2.5)
    send(.leftMouseDown, column: 2.2, row: 2.5)
    send(.leftMouseDragged, column: 6.8, row: 4.5)
    send(.leftMouseUp, column: 6.8, row: 4.5)
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.2))
    let expected = ["23456", "CDEFG", "stuvw"]
    let selected = attribute(text, kAXSelectedTextAttribute) as? String
    print("Rectangle selected=\(String(describing: selected))")
    fflush(stdout)
    precondition(selected == expected.joined(separator: "\n"), "Option drag must select the fixture rectangle")
    guard let values = attribute(text, kAXSelectedTextRangesAttribute) as? [AXValue], values.count == 3,
          let fullText = attribute(text, kAXValueAttribute) as? String else {
        fatalError("Rectangle must expose three disjoint AX ranges")
    }
    var previousEnd = 0
    for (raw, expectedRow) in zip(values, expected) {
        var rowRange = CFRange()
        precondition(AXValueGetValue(raw, .cfRange, &rowRange))
        precondition(rowRange.location >= previousEnd && rowRange.length == expectedRow.utf16.count)
        precondition(rowRange.location + rowRange.length <= fullText.utf16.count)
        precondition((fullText as NSString).substring(with: NSRange(location: rowRange.location,
                                                                 length: rowRange.length)) == expectedRow)
        var part: CFTypeRef?
        precondition(AXUIElementCopyParameterizedAttributeValue(
            text, kAXStringForRangeParameterizedAttribute as CFString, raw, &part) == .success)
        precondition(part as? String == expectedRow, "Disjoint AX range must round-trip selected row")
        previousEnd = rowRange.location + rowRange.length
    }
    print("PASS: \(native ? "native" : "PID-targeted") Option drag and three exact disjoint AX UTF-16 ranges")
}
