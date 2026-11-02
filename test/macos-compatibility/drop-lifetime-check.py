#!/usr/bin/env python3
"""Check the production async surface-drop callback against native providers.

Extracts the exact callback; surface/app shells record identity and lookup.
Does not simulate physical drag hit testing or apply actual split-tree moves.
"""

import pathlib
import platform
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Features/Splits/TerminalSplitTreeView.swift").read_text()
start = source.index("            _ = provider.loadDataRepresentation(")
end = source.index("\n\n            return true", start)
callback = source[start:end]
assert callback.count("loadDataRepresentation") == 1
zone = source[source.index("enum TerminalSplitDropZone:"):]

harness = r'''
import AppKit
import SwiftUI
import UniformTypeIdentifiers

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}

protocol TestDelegate: NSApplicationDelegate {
    func ghosttySurface(id: UUID) -> AnyObject?
}
enum Ghostty {
    typealias Delegate = TestDelegate
    final class SurfaceView {
        let id = UUID()
    }
}
final class Delegate: NSObject, TestDelegate {
    var surfaces: [UUID: Ghostty.SurfaceView] = [:]
    var lookups = 0
    func ghosttySurface(id: UUID) -> AnyObject? {
        check(Thread.isMainThread, "Surface lookup off main thread")
        lookups += 1
        return surfaces[id]
    }
}
enum TerminalSplitOperation {
    struct Drop {
        let payload: Ghostty.SurfaceView
        let destination: Ghostty.SurfaceView
        let zone: TerminalSplitDropZone
    }
    case drop(Drop)
}
var submissions = 0
var completions = 0

func load(provider: NSItemProvider, destinationSurface: Ghostty.SurfaceView,
          zone: TerminalSplitDropZone, action: @escaping (TerminalSplitOperation) -> Void) {
    submissions += 1
    CALLBACK
}

// A real NSItemProvider requests data asynchronously. Hold its completion until
// the test has closed a source/destination or changed the registry as needed.
final class Gate {
    let provider = NSItemProvider()
    let requested = DispatchSemaphore(value: 0)
    private let lock = NSLock()
    private var completion: ((Data?, Error?) -> Void)?
    init() {
        provider.registerDataRepresentation(forTypeIdentifier: UTType.ghosttySurfaceId.identifier,
                                            visibility: .all) { [weak self] completion in
            guard let self else { return nil }
            self.lock.lock()
            self.completion = completion
            self.lock.unlock()
            self.requested.signal()
            return nil
        }
    }
    func finish(_ data: Data?, error: Error? = nil) {
        check(requested.wait(timeout: .now() + 3) == .success, "Provider not requested")
        lock.lock()
        let complete = completion
        completion = nil
        lock.unlock()
        check(complete != nil, "No pending provider callback")
        DispatchQueue.global().async { complete?(data, error) }
    }
}

func drain(until predicate: () -> Bool) {
    let end = Date(timeIntervalSinceNow: 3)
    while !predicate() && Date() < end {
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.01))
    }
    check(predicate(), "Drop callback timed out")
}

@main struct Runner {
    @MainActor static func main() {
        _ = NSApplication.shared
        let delegate = Delegate()
        NSApp.delegate = delegate
        defer { NSApp.delegate = nil }
        let source = Ghostty.SurfaceView()
        let destination = Ghostty.SurfaceView()
        delegate.surfaces[source.id] = source
        var calls = 0
        let receive: (TerminalSplitOperation) -> Void = { operation in
            check(Thread.isMainThread, "Drop action off main thread")
            guard case .drop(let drop) = operation else { fatalError() }
            check(drop.payload === source && drop.destination === destination, "Wrong drop identity")
            check(drop.zone == .right, "Drop zone changed while loading")
            calls += 1
        }
        let valid = Gate()
        load(provider: valid.provider, destinationSurface: destination, zone: .right, action: receive)
        check(calls == 0, "Drop acted before data arrived")
        valid.finish(source.id.surfaceTransferData)
        drain { calls == 1 }
        check(delegate.lookups == 1, "Unexpected lookup count")

        // A test-only defer in the provider callback queues a completion marker
        // after any action work, so negative assertions do not rely on sleeps.
        func settle() {
            drain { completions == submissions }
        }
        for bytes in [Data(), Data(repeating: 0, count: 15), Data(repeating: 0, count: 17)] {
            let gate = Gate()
            let before = delegate.lookups
            load(provider: gate.provider, destinationSurface: destination, zone: .right, action: receive)
            gate.finish(bytes)
            settle()
            check(calls == 1 && delegate.lookups == before, "Malformed payload reached registry or action")
        }
        let failure = Gate()
        load(provider: failure.provider, destinationSurface: destination, zone: .right, action: receive)
        failure.finish(nil, error: NSError(domain: "test-provider", code: 1))
        settle()
        check(calls == 1, "Provider error dispatched a drop")

        let selfDrop = Gate()
        load(provider: selfDrop.provider, destinationSurface: source, zone: .right) { _ in
            check(false, "Self drop dispatched")
        }
        let beforeSelf = delegate.lookups
        selfDrop.finish(source.id.surfaceTransferData)
        drain { delegate.lookups > beforeSelf }
        settle()

        let vanishedSource = Gate()
        load(provider: vanishedSource.provider, destinationSurface: destination, zone: .right, action: receive)
        delegate.surfaces.removeValue(forKey: source.id)
        let beforeSource = delegate.lookups
        vanishedSource.finish(source.id.surfaceTransferData)
        drain { delegate.lookups > beforeSource }
        settle()
        check(calls == 1, "Closed source still dispatched a drop")
        delegate.surfaces[source.id] = source

        weak var released: Ghostty.SurfaceView?
        let vanishedDestination = Gate()
        autoreleasepool {
            let temporary = Ghostty.SurfaceView()
            released = temporary
            load(provider: vanishedDestination.provider, destinationSurface: temporary, zone: .right) { _ in
                check(false, "Closed destination still dispatched a drop")
            }
        }
        check(released == nil, "Pending drop retains destination")
        let beforeDestination = delegate.lookups
        vanishedDestination.finish(source.id.surfaceTransferData)
        settle()
        check(delegate.lookups == beforeDestination, "Closed destination still looks up source")

        // Valid transfers remain usable after failed/vanished transfers.
        for _ in 0..<20 {
            let expected = calls + 1
            let gate = Gate()
            load(provider: gate.provider, destinationSurface: destination, zone: .right, action: receive)
            gate.finish(source.id.surfaceTransferData)
            drain { calls == expected }
            settle()
        }
        print("PASS: async drop identity/zone, main-thread lookup/action, malformed/error/self drops, closed source/destination, recovery")
    }
}
'''

with tempfile.TemporaryDirectory(prefix="ghostty-drop-lifetime-") as directory:
    tmp = pathlib.Path(directory)
    assert callback.count("[weak destinationSurface]") == 1
    strong = callback.replace("[weak destinationSurface]", "[destinationSurface]").replace(
        "guard let destinationSurface,", "guard true,")
    assert callback.count("sourceSurface !== destinationSurface") == 1
    self_drop = callback.replace("sourceSurface !== destinationSurface", "true")
    assert callback.count("DispatchQueue.main.async") == 1
    background = callback.replace("DispatchQueue.main.async", "DispatchQueue.global().async")
    for optimization in ("-Onone", "-O"):
        for name, body, diagnostic in (
            ("production", callback, None),
            ("strong-destination", strong, "Pending drop retains destination"),
            ("allow-self", self_drop, "Self drop dispatched"),
            ("background-lookup", background, "Surface lookup off main thread"),
        ):
            runner = tmp / "Runner.swift"
            assert body.count("data, _ in\n") == 1
            observed = body.replace("data, _ in\n", "data, _ in\n"
                                    "                defer { DispatchQueue.main.async { completions += 1 } }\n")
            runner.write_text(harness.replace("CALLBACK", observed) + "\n" + zone)
            binary = tmp / name
            subprocess.run(["xcrun", "swiftc", optimization, "-target", f"{platform.machine()}-apple-macosx12.0",
                            str(root / "macos/Sources/Helpers/Extensions/UUID+Extension.swift"),
                            str(root / "macos/Sources/Ghostty/Surface View/SurfaceView+Transferable.swift"),
                            str(runner), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=20)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimization + ": " + result.stdout.strip())
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, result.stdout + result.stderr
                print(optimization + f": PASS: compiled {name} mutant rejected")
