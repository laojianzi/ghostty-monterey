import AppKit

// Independent AppKit diagnostic. Never post to a global event tap or inspect
// untagged user input. A zero-window result is a harness limitation, not a pass.
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
precondition(AXIsProcessTrusted() && CGPreflightPostEventAccess(), "Existing permissions required; no prompts")
let app = NSApplication.shared
if CommandLine.arguments.count == 1 {
    final class View: NSView {
        override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
        override func mouseDown(with event: NSEvent) { print("DOWN", event.locationInWindow, event.windowNumber); fflush(stdout) }
        override func mouseDragged(with event: NSEvent) { print("DRAG", event.locationInWindow, event.windowNumber); fflush(stdout) }
        override func mouseUp(with event: NSEvent) { print("UP", event.locationInWindow, event.windowNumber); fflush(stdout) }
    }
    let monitor = NSEvent.addLocalMonitorForEvents(matching: [.leftMouseDown, .leftMouseDragged, .leftMouseUp]) { e in
        if e.cgEvent?.getIntegerValueField(.eventSourceUserData) == 734812 {
            print("TARGETED", e.type.rawValue, e.windowNumber); fflush(stdout)
        }
        return e
    }
    _ = monitor
    app.setActivationPolicy(.regular)
    let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 300, height: 200), styleMask: [.titled, .closable], backing: .buffered, defer: false)
    window.contentView = View(frame: NSRect(x: 0, y: 0, width: 300, height: 200))
    app.finishLaunching()
    window.makeKeyAndOrderFront(nil)
    window.orderFrontRegardless()
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
        for type in [NSEvent.EventType.leftMouseDown, .leftMouseUp] {
            let event = NSEvent.mouseEvent(with: type, location: NSPoint(x: 150, y: 100), modifierFlags: [], timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber, context: nil, eventNumber: 1, clickCount: 1, pressure: 1)!
            window.sendEvent(event)
        }
    }
    print("WINDOW", window.windowNumber, "PID", getpid()); fflush(stdout)
    DispatchQueue.main.asyncAfter(deadline: .now() + 8) { app.terminate(nil) }
    app.run()
} else {
    let pid = pid_t(CommandLine.arguments[1])!
    guard let windows = CGWindowListCopyWindowInfo([.optionAll], kCGNullWindowID) as? [[String: Any]],
          let window = windows.first(where: {
              $0[kCGWindowOwnerPID as String] as? Int == Int(pid) && $0[kCGWindowLayer as String] as? Int == 0
          }), let number = window[kCGWindowNumber as String] as? NSNumber,
          let dictionary = window[kCGWindowBounds as String] as? [String: Any],
          let bounds = CGRect(dictionaryRepresentation: dictionary as CFDictionary) else {
        fatalError("Missing probe window")
    }
    let id = number.int64Value
    let pt = CGPoint(x: bounds.midX, y: bounds.midY)
    print("SEND", id, pt, "AX", AXIsProcessTrusted(), "POST", CGPreflightPostEventAccess())
    for t in [CGEventType.mouseMoved, .leftMouseDown, .leftMouseDragged, .leftMouseUp] {
        let e = CGEvent(mouseEventSource: nil, mouseType: t, mouseCursorPosition: pt, mouseButton: .left)!
        e.setIntegerValueField(.mouseEventWindowUnderMousePointer, value: id)
        e.setIntegerValueField(.mouseEventWindowUnderMousePointerThatCanHandleThisEvent, value: id)
        e.setIntegerValueField(.mouseEventClickState, value: 1)
        e.setIntegerValueField(.eventSourceUserData, value: 734812)
        e.postToPid(pid)
        Thread.sleep(forTimeInterval: 0.2)
    }
}
