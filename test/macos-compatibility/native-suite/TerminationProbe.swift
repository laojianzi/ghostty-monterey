import AppKit
import GhosttyKit
@testable import Ghostty

final class ProbeApplication: NSApplication {
    var replies: [Bool] = []
    override func reply(toApplicationShouldTerminate shouldTerminate: Bool) {
        precondition(Thread.isMainThread)
        replies.append(shouldTerminate)
    }
}
final class ProbeWindow: NSWindow {
    var closeCount = 0
    override func close() {
        closeCount += 1
        super.close()
    }
}
final class ProbeController: BaseTerminalController {
    var needsConfirmation = true
    override func windowCanBeClosedWithoutConfirmation() -> Bool { !needsConfirmation }
}
@MainActor final class ModalDriver: NSObject {
    let step: () -> Void
    init(step: @escaping () -> Void) { self.step = step }
    @objc func tick(_ timer: Timer) { step() }
}

func require(_ value: Bool, _ message: String) {
    if !value { fputs("FAIL: \(message)\n", stderr); exit(1) }
}
func buttons(_ view: NSView) -> [NSButton] {
    (view as? NSButton).map { [$0] } ?? view.subviews.flatMap(buttons)
}
@MainActor func waitFor(_ condition: () -> Bool) async {
    let until = Date().addingTimeInterval(3)
    while !condition() && Date() < until { try? await Task.sleep(nanoseconds: 10_000_000) }
    require(condition(), "deadline waiting for native state")
}
@MainActor func exercise(_ app: ProbeApplication) async {
    require(ghostty_init(1, CommandLine.unsafeArgv) == 0, "core init")
    let delegate = AppDelegate()
    require(delegate.ghostty.config.errors.isEmpty, "isolated config")
    func controller() -> ProbeController {
        let controller = ProbeController(delegate.ghostty, surfaceTree: .init())
        let window = ProbeWindow(contentRect: NSRect(x: 100, y: 100, width: 400, height: 250),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        controller.window = window
        window.windowController = controller
        return controller
    }
    require(delegate.terminate() == .terminateNow, "no windows exits immediately")
    for accept in [false, true] {
        let controller = controller()
        let window = controller.window!
        let count = app.replies.count
        require(delegate.terminate() == .terminateLater, "single window defers")
        await waitFor { window.attachedSheet != nil }
        let sheet = window.attachedSheet!
        let target = buttons(sheet.contentView!).first { $0.title == (accept ? "Terminate" : "Cancel") }
        require(target != nil, "native sheet button exists")
        target!.performClick(nil)
        await waitFor { app.replies.count == count + 1 }
        require(app.replies.last == accept, "single sheet response forwarded")
        await waitFor { window.attachedSheet == nil }
        controller.needsConfirmation = false
        window.close()
        print("PASS single \(accept ? "accept" : "cancel")")
    }
    for scenario in ["cancel", "terminate", "review-cancel", "review-all"] {
        let first = controller(), second = controller()
        let windows = [first.window, second.window].compactMap { $0 as? ProbeWindow }
        require(windows.count == 2, "two probe windows")
        var handledSheets = Set<ObjectIdentifier>()
        var didChoose = false
        let initialReplies = app.replies.count
        let driver = ModalDriver {
            if let modal = app.modalWindow, !didChoose {
                let title = scenario == "cancel" ? "Cancel" :
                    scenario == "terminate" ? "Terminate Processes" : "Review Windows..."
                if let button = buttons(modal.contentView!).first(where: { $0.title == title }) {
                    didChoose = true
                    button.performClick(nil)
                }
            }
            for window in windows {
                guard let sheet = window.attachedSheet,
                      !handledSheets.contains(ObjectIdentifier(sheet)) else { continue }
                let title = scenario == "review-cancel" ? "Cancel" : "Terminate"
                if let button = buttons(sheet.contentView!).first(where: { $0.title == title }) {
                    handledSheets.insert(ObjectIdentifier(sheet))
                    button.performClick(nil)
                }
            }
        }
        let timer = Timer(timeInterval: 0.02, target: driver, selector: #selector(ModalDriver.tick(_:)),
                          userInfo: nil, repeats: true)
        RunLoop.main.add(timer, forMode: .modalPanel)
        RunLoop.main.add(timer, forMode: .default)
        let response = delegate.terminate()
        if scenario.hasPrefix("review") {
            require(response == .terminateLater, "review defers termination")
            await waitFor { app.replies.count == initialReplies + 1 }
            require(app.replies.last == (scenario == "review-all"), "review reply")
            require(handledSheets.count == (scenario == "review-all" ? 2 : 1), "review sequence length")
            if scenario == "review-all" {
                require(windows.allSatisfy { $0.closeCount == 1 }, "accepted review closes each window once")
            } else {
                require(windows.allSatisfy { $0.closeCount == 0 }, "cancelled review preserves windows")
            }
        } else {
            require(response == (scenario == "cancel" ? .terminateCancel : .terminateNow), "modal reply")
            require(app.replies.count == initialReplies, "synchronous choice does not reply asynchronously")
            require(windows.allSatisfy { $0.closeCount == 0 }, "synchronous choice leaves cleanup to app")
        }
        timer.invalidate()
        first.needsConfirmation = false; second.needsConfirmation = false
        windows.forEach { $0.close() }
        print("PASS multi \(scenario)")
    }
    print("PASS native termination orchestration; no actual process termination")
    exit(0)
}
guard let app = ProbeApplication.shared as? ProbeApplication else { fatalError("Unexpected application class") }
require(!((CGSessionCopyCurrentDictionary() as? [String: Any])?["CGSSessionScreenIsLocked"] as? Bool ?? false), "session unlocked")
Task { @MainActor in await exercise(app) }
DispatchQueue.main.asyncAfter(deadline: .now() + 20) { fputs("FAIL watchdog\n", stderr); exit(1) }
app.run()
