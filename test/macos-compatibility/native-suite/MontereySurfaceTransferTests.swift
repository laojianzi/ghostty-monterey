import AppKit
import Testing
import UniformTypeIdentifiers
@testable import Ghostty
import GhosttyKit

@MainActor
struct MontereySurfaceTransferTests {
    @Test func actualSurfacePasteboardRoundTrip() async throws {
        let session = try #require(CGSessionCopyCurrentDictionary() as? [String: Any])
        try #require(!(session["CGSSessionScreenIsLocked"] as? Bool ?? false))
        try #require(NSScreen.main != nil)
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("ghostty-native-transfer-\(UUID())", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let config = directory.appendingPathComponent("config")
        try """
        shell-integration = none
        command = /usr/bin/true
        copy-on-select = none
        clipboard-read = deny
        clipboard-write = deny
        desktop-notifications = false
        """.write(to: config, atomically: true, encoding: .utf8)
        let app = Ghostty.App(configPath: config.path)
        #expect(app.config.errors.isEmpty)
        let coreApp = try #require(app.app)
        let uuid = try #require(UUID(uuidString: "00112233-4455-6677-8899-AABBCCDDEEFF"))
        var surfaceConfig = Ghostty.SurfaceConfiguration()
        surfaceConfig.command = "/usr/bin/true"
        surfaceConfig.workingDirectory = directory.path
        surfaceConfig.waitAfterCommand = true
        var view: Ghostty.SurfaceView? = Ghostty.SurfaceView(coreApp, baseConfig: surfaceConfig, uuid: uuid)
        weak var releasedView = view
        let surface = try #require(view?.surface)
        let deadline = Date().addingTimeInterval(5)
        while !ghostty_surface_process_exited(surface) && Date() < deadline {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        try #require(ghostty_surface_process_exited(surface))
        let item = try #require(view?.surfacePasteboardItem())
        #expect(item.types == [.ghosttySurfaceId])
        let expected = Data([0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77,
                             0x88, 0x99, 0xaa, 0xbb, 0xcc, 0xdd, 0xee, 0xff])
        #expect(item.data(forType: .ghosttySurfaceId) == expected)
        let board = NSPasteboard.withUniqueName()
        defer { board.releaseGlobally() }
        try #require(board.writeObjects([item]))
        view = nil
        #expect(releasedView == nil)
        let payload = try #require(board.data(forType: .ghosttySurfaceId))
        #expect(payload == expected)
        #expect(UUID(surfaceTransferData: payload) == uuid)
        for data in [payload, Data(), Data(payload.dropLast()), payload + Data([0])] {
            let provider = NSItemProvider()
            provider.registerDataRepresentation(forTypeIdentifier: UTType.ghosttySurfaceId.identifier,
                                                visibility: .all) { completion in
                DispatchQueue.global().async { completion(data, nil) }
                return nil
            }
            let received: Data = try await withCheckedThrowingContinuation { continuation in
                _ = provider.loadDataRepresentation(forTypeIdentifier: UTType.ghosttySurfaceId.identifier) { received, error in
                    if let error {
                        continuation.resume(throwing: error)
                    } else if let received {
                        continuation.resume(returning: received)
                    } else {
                        continuation.resume(throwing: CocoaError(.fileReadUnknown))
                    }
                }
            }
            #expect(received == data)
            #expect(UUID(surfaceTransferData: received) == (data.count == 16 ? uuid : nil))
        }
        try await verifyControllerMoves(config: surfaceConfig)
        withExtendedLifetime(app) {}
    }

    private func verifyControllerMoves(
        config: Ghostty.SurfaceConfiguration
    ) async throws {
        let directory = FileManager.default.temporaryDirectory
            .appendingPathComponent("ghostty-drop-child-\(UUID())", isDirectory: true)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let script = directory.appendingPathComponent("child.pl")
        let replies = directory.appendingPathComponent("replies")
        try """
        use strict;
        use POSIX qw(ttyname);
        alarm 30;
        open(my $out, '>', $ARGV[0]) or die $!;
        select((select($out), $| = 1)[0]);
        my $tty = ttyname(0) // die 'not a tty';
        print $out "$$ $tty ready\\n";
        while (my $line = <STDIN>) {
            last if $line eq "quit\\n";
            print $out "$$ $tty $line";
        }
        """.write(to: script, atomically: true, encoding: .utf8)
        let childConfig = directory.appendingPathComponent("config")
        try #require(!script.path.contains(" ") && !replies.path.contains(" "))
        try """
        command = direct:/usr/bin/perl \(script.path) \(replies.path)
        shell-integration = none
        copy-on-select = none
        clipboard-read = deny
        clipboard-write = deny
        desktop-notifications = false
        """.write(to: childConfig, atomically: true, encoding: .utf8)
        let childApp = Ghostty.App(configPath: childConfig.path)
        try #require(childApp.config.errors.isEmpty)
        var liveConfig = config
        liveConfig.command = nil
        let childCore = try #require(childApp.app)
        let source = Ghostty.SurfaceView(childCore, baseConfig: liveConfig)
        defer { withExtendedLifetime(childApp) {} }
        let destination = Ghostty.SurfaceView(childCore, baseConfig: config)
        let other = Ghostty.SurfaceView(childCore, baseConfig: config)
        let originalCore = try #require(source.surface)
        let deadline = Date().addingTimeInterval(5)
        for view in [destination, other] {
            let core = try #require(view.surface)
            while !ghostty_surface_process_exited(core) && Date() < deadline {
                try await Task.sleep(nanoseconds: 10_000_000)
            }
            try #require(ghostty_surface_process_exited(core))
        }
        defer { send("quit\n", to: originalCore) }
        let readyDeadline = Date().addingTimeInterval(5)
        while !((try? String(contentsOf: replies)) ?? "").contains("ready\n") && Date() < readyDeadline {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        let ready = try String(contentsOf: replies).split(separator: "\n").first.map(String.init)
        let identity = try #require(ready?.split(separator: " ").prefix(2).joined(separator: " "))
        let childPID = try #require(Int32(identity.split(separator: " ").first ?? ""))
        try #require(identity.contains("/dev/"))
        try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
        let first = BaseTerminalController(childApp, surfaceTree: .init(view: source))
        let second = BaseTerminalController(childApp, surfaceTree: .init(view: destination))
        let windows = [first, second].map { controller -> NSWindow in
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 320, height: 200),
                                  styleMask: [.titled], backing: .buffered, defer: false)
            window.isReleasedWhenClosed = false
            controller.window = window
            window.windowController = controller
            window.delegate = controller
            return window
        }
        defer {
            for controller in [first, second] {
                controller.undoManager?.removeAllActions(withTarget: controller)
                controller.surfaceTree = .init()
                controller.window = nil
            }
            for window in windows {
                window.delegate = nil
                window.windowController = nil
                window.close()
            }
        }
#if GHOSTTY_XCODE_HOSTED_TEST
        let undo = try #require(first.undoManager)
        try #require(second.undoManager === undo)
        // Explicit groups avoid depending on run-loop event grouping in async tests.
        let groupsByEvent = undo.groupsByEvent
        undo.groupsByEvent = false
        defer {
            undo.removeAllActions(withTarget: first)
            undo.removeAllActions(withTarget: second)
            undo.groupsByEvent = groupsByEvent
        }
#endif
        for zone in [TerminalSplitDropZone.left, .right, .top, .bottom] {
            first.surfaceTree = .init(view: source)
            second.surfaceTree = .init(view: destination)
            #expect(BaseTerminalController.controller(owning: source) === first)
#if GHOSTTY_XCODE_HOSTED_TEST
            undo.removeAllActions(withTarget: first)
            undo.removeAllActions(withTarget: second)
            undo.beginUndoGrouping()
#endif
            second.performSplitAction(.drop(.init(payload: source, destination: destination, zone: zone)))
#if GHOSTTY_XCODE_HOSTED_TEST
            undo.endUndoGrouping()
#endif
            #expect(first.surfaceTree.isEmpty)
            #expect(BaseTerminalController.controller(owning: source) === second)
            try verifyOrder(second, source: source, destination: destination, zone: zone)
            #expect(source.surface == originalCore)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)

#if GHOSTTY_XCODE_HOSTED_TEST
            try #require(undo.canUndo)
            undo.undo()
            let sourceRestored = first.surfaceTree.root == .leaf(view: source)
            let destinationRestored = second.surfaceTree.root == .leaf(view: destination)
            #expect(sourceRestored)
            #expect(destinationRestored)
            #expect(BaseTerminalController.controller(owning: source) === first)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
            try #require(undo.canRedo)
            undo.redo()
            #expect(first.surfaceTree.isEmpty)
            #expect(BaseTerminalController.controller(owning: source) === second)
            try verifyOrder(second, source: source, destination: destination, zone: zone)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
            undo.removeAllActions(withTarget: first)
            undo.removeAllActions(withTarget: second)
            // Reversing direction makes the same-window undo observable.
            let priorTree = second.surfaceTree
            let opposite: TerminalSplitDropZone
            switch zone {
            case .left: opposite = .right
            case .right: opposite = .left
            case .top: opposite = .bottom
            case .bottom: opposite = .top
            }
            undo.beginUndoGrouping()
            second.performSplitAction(.drop(.init(payload: source, destination: destination, zone: opposite)))
            undo.endUndoGrouping()
            try verifyOrder(second, source: source, destination: destination, zone: opposite)
            try #require(undo.canUndo)
            undo.undo()
            let sameWindowRestored = second.surfaceTree.root == priorTree.root
            #expect(sameWindowRestored)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
            try #require(undo.canRedo)
            undo.redo()
            try verifyOrder(second, source: source, destination: destination, zone: opposite)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
            undo.beginUndoGrouping()
#endif
            // Repeat from the same tree to reach the distinct same-window path.
            second.performSplitAction(.drop(.init(payload: source, destination: destination, zone: zone)))
#if GHOSTTY_XCODE_HOSTED_TEST
            undo.endUndoGrouping()
#endif
            try verifyOrder(second, source: source, destination: destination, zone: zone)
            #expect(source.surface == originalCore)
            try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)

            let before = second.surfaceTree
            second.performSplitAction(.drop(.init(payload: source, destination: other, zone: zone)))
            #expect(second.surfaceTree.root == before.root)
            #expect(second.surfaceTree.zoomed == before.zoomed)
            #expect(BaseTerminalController.controller(owning: source) === second)
        }
        // Failed cross-window insertion must not remove the original source.
        first.surfaceTree = .init(view: source)
        second.surfaceTree = .init(view: destination)
        second.performSplitAction(.drop(.init(payload: source, destination: other, zone: .left)))
        #expect(first.surfaceTree.root == .leaf(view: source))
        #expect(second.surfaceTree.root == .leaf(view: destination))
        #expect(BaseTerminalController.controller(owning: source) === first)
        #expect(source.surface == originalCore)
        try await checkpoint(originalCore, replies: replies, identity: identity, pid: childPID)
        send("quit\n", to: originalCore)
        let exitDeadline = Date().addingTimeInterval(5)
        while !ghostty_surface_process_exited(originalCore) && Date() < exitDeadline {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        try #require(ghostty_surface_process_exited(originalCore))
        let reaped = kill(childPID, 0) == -1 && errno == ESRCH
        #expect(reaped)
        // Drain queued focus changes before the windows/controllers are released.
        try await Task.sleep(nanoseconds: 50_000_000)
    }

    private func send(_ text: String, to core: ghostty_surface_t) {
        text.withCString { ghostty_surface_text(core, $0, UInt(text.utf8.count)) }
    }

    private func checkpoint(_ core: ghostty_surface_t, replies: URL, identity: String, pid: Int32) async throws {
        let marker = UUID().uuidString
        send(marker + "\n", to: core)
        let expected = "\(identity) \(marker)\n"
        let until = Date().addingTimeInterval(3)
        while !((try? String(contentsOf: replies)) ?? "").contains(expected) && Date() < until {
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        let acknowledged = ((try? String(contentsOf: replies)) ?? "").contains(expected)
        try #require(acknowledged)
        #expect(!ghostty_surface_process_exited(core))
        #expect(kill(pid, 0) == 0)
    }

    private func verifyOrder(
        _ controller: BaseTerminalController,
        source: Ghostty.SurfaceView,
        destination: Ghostty.SurfaceView,
        zone: TerminalSplitDropZone
    ) throws {
        guard case .split(let split) = controller.surfaceTree.root else {
            Issue.record("Expected real two-surface split")
            return
        }
        let sourceFirst = zone == .left || zone == .top
        let leftMatches = split.left == .leaf(view: sourceFirst ? source : destination)
        let rightMatches = split.right == .leaf(view: sourceFirst ? destination : source)
        #expect(leftMatches)
        #expect(rightMatches)
        #expect(split.direction == ((zone == .left || zone == .right) ? .horizontal : .vertical))
        #expect(Array(controller.surfaceTree).count == 2)
    }
}
