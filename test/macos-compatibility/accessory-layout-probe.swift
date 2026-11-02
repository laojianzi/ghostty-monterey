import Cocoa
import SwiftUI

final class Model: ObservableObject {
    @Published var visible = false
    var actions = 0
}

struct Accessory: View {
    @ObservedObject var model: Model

    var body: some View {
        if model.visible {
            VStack {
                Button("Zoom") { model.actions += 1 }.frame(width: 20, height: 20)
                Spacer()
            }
            .padding(.top, 9)
            .padding(.trailing, 10)
        }
    }
}

let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
let model = Model()
let regularInteraction = CommandLine.arguments.contains("--regular-interaction")
let app = NSApplication.shared
app.setActivationPolicy(.regular)

func click(_ view: NSView, expecting count: Int) {
    let local = NSPoint(x: 10, y: 20)
    precondition(view.visibleRect.contains(local), "Button click target is clipped")
    let point = view.convert(local, to: nil)
    let timestamp = ProcessInfo.processInfo.systemUptime
    for (index, type) in [NSEvent.EventType.leftMouseDown, .leftMouseUp].enumerated() {
        let event = NSEvent.mouseEvent(
            with: type, location: point, modifierFlags: [], timestamp: timestamp + Double(index) * 0.01,
            windowNumber: view.window!.windowNumber, context: nil, eventNumber: index + 1,
            clickCount: 1, pressure: index == 0 ? 1 : 0)!
        app.postEvent(event, atStart: false)
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) {
        precondition(model.actions == count, "Button action not delivered exactly once")
        print("PASS: regular accessory button action \(count)")
        fflush(stdout)
    }
}

func window() -> NSWindow {
    let result = NSWindow(contentRect: NSRect(x: 120, y: 150, width: 648, height: 454),
                          styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
    result.isReleasedWhenClosed = false
    result.collectionBehavior = .fullScreenPrimary
    let accessory = NSTitlebarAccessoryViewController()
    accessory.layoutAttribute = .right
    accessory.view = NSHostingView(rootView: Accessory(model: model))
    result.addTitlebarAccessoryViewController(accessory)
    accessory.view.translatesAutoresizingMaskIntoConstraints = false
    return result
}

let first = window()
first.makeKeyAndOrderFront(nil)
app.activate(ignoringOtherApps: true)
DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
    if !regularInteraction { first.toggleFullScreen(nil) }
}
DispatchQueue.main.asyncAfter(deadline: .now() + 3) {
    precondition(first.styleMask.contains(.fullScreen) != regularInteraction, "Unexpected fullscreen state")
    let second = window()
    first.addTabbedWindow(second, ordered: .above)
    second.makeKeyAndOrderFront(nil)
    let dynamic = !CommandLine.arguments.contains("--static")
    let accessory = second.titlebarAccessoryViewControllers.first {
        $0.view is NSHostingView<Accessory>
    }!
    var visibleSize = NSSize.zero
    if dynamic { model.visible = true }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) {
        let size = accessory.view.frame.size
        precondition(size == accessory.view.fittingSize, "Accessory did not reach fitting size")
        if dynamic {
            precondition(size.width > 0 && size.height > 0, "Visible accessory has no space")
            visibleSize = size
            if regularInteraction { click(accessory.view, expecting: 1) }
        } else {
            precondition(size == .zero, "Static empty accessory occupies space")
        }
        print("Accessory visible/static size: \(size)")
        fflush(stdout)
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { model.visible = false }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
        precondition(accessory.view.frame.size == .zero, "Hidden accessory still occupies titlebar space")
        precondition(accessory.view.fittingSize == .zero, "Hidden accessory retains fitting size")
        print("PASS: hidden accessory releases titlebar space")
        fflush(stdout)
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
        if dynamic { model.visible = true }
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
        precondition(accessory.view.frame.size == visibleSize, "Revealed accessory changed size")
        precondition(accessory.view.fittingSize == visibleSize, "Revealed accessory fitting size changed")
        if regularInteraction { click(accessory.view, expecting: 2) }
        print("PASS: accessory re-expands to its original size")
        fflush(stdout)
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
        precondition(second.styleMask.contains(.fullScreen) != regularInteraction, "Unexpected new tab state")
        second.close()
        if !regularInteraction { first.toggleFullScreen(nil) }
    }
}
DispatchQueue.main.asyncAfter(deadline: .now() + 8) {
    precondition(!first.styleMask.contains(.fullScreen), "Fixture did not exit fullscreen")
    first.close()
    print("PASS: native AppKit tab lifecycle completed (inspect stderr for recursion)")
    exit(0)
}
app.run()
