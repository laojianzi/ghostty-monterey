import AppKit
import Darwin
import GhosttyKit
@testable import Ghostty

final class ChildProbeApplication: NSApplication {
    var replies: [Bool] = []
    override func reply(toApplicationShouldTerminate shouldTerminate: Bool) {
        precondition(Thread.isMainThread)
        replies.append(shouldTerminate)
    }
}

func require(_ value: Bool, _ message: String) {
    if !value { fputs("FAIL: \(message)\n", stderr); exit(1) }
}
func buttons(_ view: NSView) -> [NSButton] {
    (view as? NSButton).map { [$0] } ?? view.subviews.flatMap(buttons)
}
@MainActor func waitFor(_ message: String, _ condition: () -> Bool) async {
    let until = Date().addingTimeInterval(5)
    while !condition() && Date() < until { try? await Task.sleep(nanoseconds: 10_000_000) }
    require(condition(), message)
}

@MainActor func exercise(_ app: ChildProbeApplication) async {
    require(ghostty_init(1, CommandLine.unsafeArgv) == 0, "core init")
    let delegate = AppDelegate()
    require(delegate.ghostty.config.errors.isEmpty, "isolated config")
    var controller: BaseTerminalController? = BaseTerminalController(delegate.ghostty)
    weak var releasedController = controller
    weak var surface = controller?.surfaceTree.root?.leaves().first
    require(surface != nil, "actual surface created")
    let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 400, height: 250),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
    window.isReleasedWhenClosed = false
    controller?.window = window
    window.windowController = controller
    window.delegate = controller
    let pidPath = ProcessInfo.processInfo.environment["GHOSTTY_CHILD_PID_PATH"]!
    await waitFor("child readiness") { FileManager.default.fileExists(atPath: pidPath) }
    let pid = pid_t((try? String(contentsOfFile: pidPath))?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "")!
    require(kill(pid, 0) == 0, "child alive before quit request")
    require(surface?.processExited == false, "core observes running child")
    require(surface?.needsConfirmQuit == true, "real surface requests confirmation")
    require(controller?.windowCanBeClosedWithoutConfirmation() == false, "real controller requests confirmation")
    require(delegate.ghostty.needsConfirmQuit, "real app requests confirmation")

    for accept in [false, true] {
        let count = app.replies.count
        require(delegate.applicationShouldTerminate(app) == .terminateLater, "real quit policy defers")
        await waitFor("native sheet") { window.attachedSheet != nil }
        let sheet = window.attachedSheet!
        guard let button = buttons(sheet.contentView!).first(where: { $0.title == (accept ? "Terminate" : "Cancel") }) else {
            fatalError("Missing native sheet button")
        }
        button.performClick(nil)
        await waitFor("quit reply") { app.replies.count == count + 1 }
        require(app.replies.last == accept, "real child sheet reply")
        await waitFor("sheet removed") { window.attachedSheet == nil }
        require(kill(pid, 0) == 0 && surface?.processExited == false, "reply boundary preserves child until teardown")
        print("PASS real child \(accept ? "accept" : "cancel")")
    }
    window.close()
    window.windowController = nil
    controller = nil
    await waitFor("controller and surface released") { releasedController == nil && surface == nil }
    await waitFor("owned child reaped after surface release") { kill(pid, 0) == -1 && errno == ESRCH }
    require(!delegate.ghostty.needsConfirmQuit, "app no longer has confirming surfaces")
    require(delegate.applicationShouldTerminate(app) == .terminateNow, "quit after teardown is immediate")
    print("PASS real surface teardown reaps child")
    withExtendedLifetime(delegate) {}
    exit(0)
}

guard let app = ChildProbeApplication.shared as? ChildProbeApplication else { fatalError("Unexpected app class") }
require(!((CGSessionCopyCurrentDictionary() as? [String: Any])?["CGSSessionScreenIsLocked"] as? Bool ?? false), "session unlocked")
Task { @MainActor in await exercise(app) }
app.run()
