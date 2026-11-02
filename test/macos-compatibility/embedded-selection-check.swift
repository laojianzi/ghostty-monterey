import AppKit
import GhosttyKit

// A real embedded core and NSWindow, not the full Ghostty application runtime.
// Events stay inside this window; clipboard callbacks never access pasteboards.
final class TerminalView: NSView, NSTextInputClient {
    var surface: ghostty_surface_t?
    var accessibilityText: AXTextCache { AXTextCache(surface: surface) }
    var cachedScreenContents: TextCache { TextCache(surface: surface) }
    var suppressNextLeftMouseUp = false
    var prevPressureStage = 0
    var markedText = NSMutableAttributedString()
    var keyTextAccumulator: [String]?
    var leadSurrogate: LeadSurrogate?
    var keyCallback: (() -> Void)?
    var expectedKeyTimestamp: TimeInterval?
    var interpretation: ((NSEvent) -> Void)?
    var nativeInterpretation = false
    var cellSize: CGSize {
        let size = ghostty_surface_size(surface)
        return CGSize(width: Int(size.cell_width_px), height: Int(size.cell_height_px))
    }
    var bell = false
    var lastPerformKeyEvent: TimeInterval?
    override func interpretKeyEvents(_ events: [NSEvent]) {
        if nativeInterpretation {
            super.interpretKeyEvents(events)
            return
        }
        precondition(events.count == 1)
        guard let interpretation else { preconditionFailure("Missing scripted input-method response") }
        interpretation(events[0])
    }
    override func keyDown(with event: NSEvent) {
        guard let expectedKeyTimestamp, abs(event.timestamp - expectedKeyTimestamp) < 0.000001 else { return }
        guard let callback = keyCallback else { return }
        keyCallback = nil
        precondition(NSApp.currentEvent?.type == .keyDown, "No real current key event")
        callback()
    }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override func mouseMoved(with event: NSEvent) {
        let p = convert(event.locationInWindow, from: nil)
        ghostty_surface_mouse_pos(surface, p.x, bounds.height - p.y,
                                 event.modifierFlags.contains(.option) ? GHOSTTY_MODS_ALT : GHOSTTY_MODS_NONE)
    }
    override func mouseDragged(with event: NSEvent) { mouseMoved(with: event) }
    // The harness adds the actual production mouseDown/mouseUp implementations
    // in an extension. Position routing above is explicitly the test adapter.
}

let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
let app = NSApplication.shared
app.setActivationPolicy(.regular)
func runChecks() {
    precondition(ghostty_init(UInt(CommandLine.argc), CommandLine.unsafeArgv) == 0)
    let config = ghostty_config_new()!
    ghostty_config_load_file(config, CommandLine.arguments[1])
    ghostty_config_finalize(config)
    precondition(ghostty_config_diagnostics_count(config) == 0, "Invalid fixture config")
    var runtime = ghostty_runtime_config_s()
    runtime.wakeup_cb = { _ in }
    runtime.action_cb = { _, _, _ in false }
    runtime.read_clipboard_cb = { _, _, _, _, _, _ in GHOSTTY_CLIPBOARD_READ_UNAVAILABLE }
    runtime.confirm_read_clipboard_cb = { _, _, _, _ in preconditionFailure("Unexpected clipboard confirmation") }
    runtime.write_clipboard_cb = { _, _, _, _, _ in preconditionFailure("Unexpected clipboard write") }
    runtime.close_surface_cb = { _, _ in }
    let core = ghostty_app_new(&runtime, config)!
    let window = NSWindow(contentRect: NSRect(x: 120, y: 150, width: 800, height: 400),
                          styleMask: [.titled, .closable], backing: .buffered, defer: false)
    let controller = NSWindowController(window: window)
    // Real pointer activity must not alter the fixture's synthetic gesture state.
    window.ignoresMouseEvents = true
    window.title = "Embedded Selection Probe"
    let view = TerminalView(frame: NSRect(x: 0, y: 0, width: 800, height: 400))
    view.wantsLayer = true
    window.contentView = view
    window.makeKeyAndOrderFront(nil)
    window.orderFrontRegardless()
    let previousFront = NSWorkspace.shared.frontmostApplication
    let activateForAX = CommandLine.arguments.contains("--ax-client") && !CommandLine.arguments.contains("--no-option")
    if activateForAX { app.activate(ignoringOtherApps: true) }
    defer { if activateForAX { previousFront?.activate(options: [.activateIgnoringOtherApps]) } }
    var options = ghostty_surface_config_new()
    options.platform_tag = GHOSTTY_PLATFORM_MACOS
    options.platform.macos.nsview = Unmanaged.passUnretained(view).toOpaque()
    options.scale_factor = 1
    let surface = ghostty_surface_new(core, &options)!
    view.surface = surface
    ghostty_surface_set_content_scale(surface, 1, 1)
    ghostty_surface_set_size(surface, 800, 400)
    ghostty_surface_set_focus(surface, true)
    window.makeFirstResponder(view)
    func pump(_ duration: TimeInterval) {
        let deadline = Date(timeIntervalSinceNow: duration)
        repeat {
            ghostty_app_tick(core)
            while let event = app.nextEvent(matching: .any, until: Date(), inMode: .default, dequeue: true) {
                app.sendEvent(event)
            }
            app.updateWindows()
            RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.005))
        } while Date() < deadline
    }
    let deadline = Date(timeIntervalSinceNow: 10)
    while !view.cachedScreenContents.get().contains("qrstuvwxyz012345") {
        pump(0.02)
        precondition(Date() < deadline, "Child text not received")
    }
    let size = ghostty_surface_size(surface)
    print("Grid \(size.columns)x\(size.rows), cell \(size.cell_width_px)x\(size.cell_height_px)")
    precondition(view.accessibilitySelectedText() == nil)
    func send(_ type: NSEvent.EventType, x: Double, y: Double, rectangle: Bool) {
        let point = NSPoint(x: x * Double(size.cell_width_px), y: 400 - y * Double(size.cell_height_px))
        let useOption = rectangle && !CommandLine.arguments.contains("--no-option")
        let event = NSEvent.mouseEvent(with: type, location: point, modifierFlags: useOption ? .option : [],
                                      timestamp: ProcessInfo.processInfo.systemUptime, windowNumber: window.windowNumber,
                                      context: nil, eventNumber: 1, clickCount: 1,
                                      pressure: type == .leftMouseUp ? 0 : 1)!
        // Motion is routed directly because inactive windows need not track it.
        if type == .mouseMoved { view.mouseMoved(with: event) } else { window.sendEvent(event) }
        pump(0.03)
    }
    for (rectangle, reverse) in [(true, false), (true, true), (false, false)] {
        let start = reverse ? (6.8, 3.5) : (2.2, 1.5)
        let end = reverse ? (2.2, 1.5) : (6.8, 3.5)
        send(.mouseMoved, x: start.0, y: start.1, rectangle: rectangle)
        send(.leftMouseDown, x: start.0, y: start.1, rectangle: rectangle)
        send(.leftMouseDragged, x: end.0, y: end.1, rectangle: rectangle)
        send(.leftMouseUp, x: end.0, y: end.1, rectangle: rectangle)
        let selected = view.accessibilitySelectedText() ?? ""
        let expected = rectangle ? "23456\nCDEFG\nstuvw" : "23456789abcdef\nABCDEFGHIJKLMNOP\nqrstuvw"
        precondition(selected == expected, "Mouse gesture selected unexpected text")
        let whole = view.cachedScreenContents.get()
        precondition(view.accessibilityValue() as? String == whole)
        precondition(view.accessibilityNumberOfCharacters() == whole.utf16.count)
        let ranges = view.accessibilitySelectedTextRanges()!.map { $0.rangeValue }
        precondition(ranges.count == (rectangle ? 3 : 1))
        let reconstructed = ranges.map { view.accessibilityString(for: $0)! }.joined(separator: rectangle ? "\n" : "")
        precondition(reconstructed == expected, "AX ranges must reconstruct exact selection")
        precondition(view.accessibilitySelectedTextRange() == ranges[0])
        print("PASS: rectangle=\(rectangle), reverse=\(reverse), actual AX UTF-16 ranges reconstruct selection")
        if let clientIndex = CommandLine.arguments.firstIndex(of: "--ax-client") {
            let remote = Process()
            remote.executableURL = URL(fileURLWithPath: CommandLine.arguments[clientIndex + 1])
            remote.arguments = [String(getpid()), rectangle ? "rectangle" : "contiguous"]
            do { try remote.run() } catch { preconditionFailure("Cannot launch AX client: \(error)") }
            // AX requests execute on the target's main thread: never block it
            // with waitUntilExit while the remote process is reading attributes.
            let deadline = Date(timeIntervalSinceNow: 5)
            while remote.isRunning && Date() < deadline { pump(0.01) }
            if remote.isRunning { remote.terminate(); preconditionFailure("Remote AX client timed out") }
            precondition(remote.terminationStatus == 0, "Remote AX selection failed")
        }
        pump(0.55)
    }
    if let inputIndex = CommandLine.arguments.firstIndex(of: "--committed-input") {
        let path = URL(fileURLWithPath: CommandLine.arguments[inputIndex + 1])
        precondition(!FileManager.default.fileExists(atPath: path.path), "Fixture already received input")
        for marked in ["ni", "\u{306b}\u{307b}\u{3093}", "\u{d55c}", "\u{1f680}e\u{301}"] {
            view.setMarkedText(marked, selectedRange: NSRange(location: marked.utf16.count, length: 0),
                               replacementRange: NSRange(location: NSNotFound, length: 0))
            precondition(view.hasMarkedText() && view.markedRange().length == marked.utf16.count)
            pump(0.03)
            precondition(!FileManager.default.fileExists(atPath: path.path), "Preedit leaked to PTY")
        }
        view.unmarkText()
        precondition(!view.hasMarkedText())
        pump(0.05)
        precondition(!FileManager.default.fileExists(atPath: path.path), "Cancelled preedit leaked to PTY")
        // Simulate commit payloads, not a particular input method's candidate UI.
        // Bracketed paste is enabled by the real child: typed text must not get
        // paste delimiters, normalization, duplicate bytes or physical-key text.
        let payloads = ["a", "\u{4e2d}\u{6587}", "\u{65e5}\u{672c}\u{8a9e}",
                        "\u{d55c}\u{ad6d}\u{c5b4}", "e\u{301}", "\u{1f680}"]
        var expected = Data()
        func dispatchCommit(event suppliedEvent: NSEvent? = nil, _ body: @escaping () -> Void) {
            precondition(view.keyCallback == nil)
            view.keyCallback = body
            let event = suppliedEvent ?? NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [],
                                        timestamp: ProcessInfo.processInfo.systemUptime,
                                        windowNumber: window.windowNumber, context: nil,
                                        characters: "a", charactersIgnoringModifiers: "a",
                                        isARepeat: false, keyCode: 0)!
            view.expectedKeyTimestamp = event.timestamp
            app.postEvent(event, atStart: false)
            let deadline = Date(timeIntervalSinceNow: 2)
            while view.keyCallback != nil && Date() < deadline { pump(0.01) }
            precondition(view.keyCallback == nil, "Local key event not delivered")
        }
        for payload in payloads {
            dispatchCommit {
                view.setMarkedText("preedit", selectedRange: NSRange(location: 7, length: 0),
                                   replacementRange: NSRange(location: NSNotFound, length: 0))
                view.insertText(payload as NSString, replacementRange: NSRange(location: NSNotFound, length: 0))
                precondition(!view.hasMarkedText(), "Commit must clear preedit")
            }
            expected.append(contentsOf: payload.utf8)
            let deadline = Date(timeIntervalSinceNow: 3)
            while (try? Data(contentsOf: path)) != expected && Date() < deadline { pump(0.01) }
            precondition((try? Data(contentsOf: path)) == expected, "Committed text PTY bytes mismatch")
        }
        func expectBytes(_ appended: String = "") {
            expected.append(contentsOf: appended.utf8)
            let deadline = Date(timeIntervalSinceNow: 3)
            while (try? Data(contentsOf: path)) != expected && Date() < deadline { pump(0.01) }
            pump(0.05)
            if (try? Data(contentsOf: path)) != expected {
                print("PTY mismatch expected=\(expected as NSData), actual=\(String(describing: try? Data(contentsOf: path) as NSData)), marked=\(view.markedText.string.debugDescription)")
                fflush(stdout)
            }
            precondition((try? Data(contentsOf: path)) == expected, "insertText branch PTY bytes mismatch")
        }
        dispatchCommit {
            view.insertText(NSAttributedString(string: "\u{4e2d}\u{1f680}"), replacementRange: NSRange())
        }
        expectBytes("\u{4e2d}\u{1f680}")
        func unit(_ value: unichar) -> NSString {
            var value = value
            return NSString(characters: &value, length: 1)
        }
        // AppKit may deliver a supplementary character as separate UTF-16
        // surrogate callbacks. No replacement characters may reach the PTY.
        dispatchCommit { view.insertText(unit(0xD83D), replacementRange: NSRange()) }
        expectBytes()
        dispatchCommit { view.insertText(unit(0xDE80), replacementRange: NSRange()) }
        expectBytes("\u{1f680}")
        dispatchCommit { view.insertText(unit(0xDE80), replacementRange: NSRange()) }
        expectBytes()
        dispatchCommit { view.insertText(unit(0xD83D), replacementRange: NSRange()) }
        dispatchCommit { view.insertText("x" as NSString, replacementRange: NSRange()) }
        expectBytes("x")
        dispatchCommit { view.insertText(unit(0xDE80), replacementRange: NSRange()) }
        expectBytes()
        dispatchCommit {
            view.keyTextAccumulator = []
            view.setMarkedText("composing", selectedRange: NSRange(), replacementRange: NSRange())
            view.insertText("ab" as NSString, replacementRange: NSRange())
            view.insertText(NSAttributedString(string: "\u{4e2d}"), replacementRange: NSRange())
            precondition(view.keyTextAccumulator == ["ab", "\u{4e2d}"], "Key event accumulator contents")
            precondition(!view.hasMarkedText(), "Accumulated commit must clear preedit")
            view.keyTextAccumulator = nil
        }
        expectBytes()
        func keyScenario(keyCode: UInt16, characters: String, modifiers: NSEvent.ModifierFlags = [],
                         marked: String?, output: String, interpret: @escaping (NSEvent) -> Void) {
            if let marked {
                view.setMarkedText(marked, selectedRange: NSRange(), replacementRange: NSRange())
            } else {
                view.unmarkText()
            }
            let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: modifiers,
                                            timestamp: ProcessInfo.processInfo.systemUptime,
                                            windowNumber: window.windowNumber, context: nil,
                                            characters: characters, charactersIgnoringModifiers: characters,
                                        isARepeat: false, keyCode: keyCode)!
            dispatchCommit(event: event) {
                guard let delivered = NSApp.currentEvent, delivered.keyCode == event.keyCode else {
                    preconditionFailure("Native current event must match posted key code")
                }
                view.interpretation = interpret
                // AppKit can add function/numeric-pad flags to arrow events.
                // Production receives the delivered event, not our input copy.
                view.productionKeyDown(with: delivered)
                view.interpretation = nil
                precondition(view.keyTextAccumulator == nil, "Production keyDown leaked accumulator")
            }
            expectBytes(output)
        }
        print("Input source: \(KeyboardLayout.id ?? "unknown"); interpretKeyEvents responses are scripted")
        keyScenario(keyCode: 0, characters: "a", marked: nil, output: "a") { _ in
            view.insertText("a" as NSString, replacementRange: NSRange())
        }
        keyScenario(keyCode: 0, characters: "a", marked: nil, output: "") { _ in
            view.setMarkedText("ni", selectedRange: NSRange(), replacementRange: NSRange())
        }
        keyScenario(keyCode: 36, characters: "\r", marked: "ni", output: "\u{4f60}") { _ in
            view.insertText("\u{4f60}" as NSString, replacementRange: NSRange())
        }
        keyScenario(keyCode: 51, characters: "\u{7f}", marked: "ni", output: "") { _ in view.unmarkText() }
        keyScenario(keyCode: 4, characters: "\u{8}", modifiers: .control, marked: "ni", output: "") { _ in
            view.unmarkText()
            view.insertText("\u{8}" as NSString, replacementRange: NSRange())
        }
        keyScenario(keyCode: 123, characters: "\u{f702}", marked: "\u{d55c}", output: "\u{d55c}") { _ in
            view.insertText("\u{d55c}" as NSString, replacementRange: NSRange())
        }
        keyScenario(keyCode: 124, characters: "\u{f703}", marked: "\u{d55c}", output: "\u{d55c}\u{1b}[C") { _ in
            view.insertText("\u{d55c}" as NSString, replacementRange: NSRange())
        }
        print("PASS: production keyDown composition start/commit/cancel, control suppression and arrow replay reach raw PTY")
        if CommandLine.arguments.contains("--native-input") {
            precondition(["com.apple.keylayout.ABC", "com.apple.keylayout.US"].contains(KeyboardLayout.id ?? ""),
                         "Native fixture requires existing ABC/US layout; does not change it")
            view.nativeInterpretation = true
            for (code, chars, modifiers): (UInt16, String, NSEvent.ModifierFlags) in [
                (0, "a", []), (0, "A", .shift),
                (0, "\u{1}", .control), (36, "\r", []),
                (51, "\u{7f}", []), (124, "\u{f703}", [])
            ] {
                let output = code == 124 ? "\u{1b}[C" : chars
                keyScenario(keyCode: code, characters: chars, modifiers: modifiers, marked: nil, output: output) { _ in
                    preconditionFailure("Native input unexpectedly used scripted callback")
                }
                precondition(!view.hasMarkedText(), "Unexpected composition in ABC/US fixture")
            }
            if CommandLine.arguments.contains("--dead-key") {
                keyScenario(keyCode: 14, characters: "\u{b4}", modifiers: .option, marked: nil, output: "") { _ in
                    preconditionFailure("Native dead key unexpectedly used scripted callback")
                }
                precondition(view.hasMarkedText(), "Native Option-E must start dead-key composition")
                let deadKey = view.markedText.string
                keyScenario(keyCode: 14, characters: "e", marked: deadKey, output: "\u{e9}") { _ in
                    preconditionFailure("Native dead-key commit unexpectedly used scripted callback")
                }
                precondition(!view.hasMarkedText(), "Native dead-key commit must clear composition")
            }
            view.nativeInterpretation = false
            print("PASS: native ABC/US plain/Shift/Ctrl/Enter/Backspace/Right reaches raw PTY")
        }
        pump(0.2)
        precondition((try? Data(contentsOf: path)) == expected, "Delayed duplicate committed bytes")
        print("PASS: native current-event insertText clears preedit and reaches raw PTY once, without paste delimiters (\(expected.count) bytes)")
    }
    view.surface = nil
    ghostty_surface_free(surface)
    ghostty_app_free(core)
    ghostty_config_free(config)
    window.orderOut(nil)
    withExtendedLifetime(controller) {}
    print("PASS: embedded gestures, AX mapped ranges and input; full-app VoiceOver verified separately")

}
DispatchQueue.main.async {
    runChecks()
    app.terminate(nil)
}
app.run()
