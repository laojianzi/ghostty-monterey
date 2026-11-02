#!/usr/bin/env python3
"""Exercise production Services routing with native Monterey pasteboards/files.

Only app/controller construction is replaced by a call recorder. This does not
register a service, open real terminals, change the user's clipboard or prove
Finder/Services menu discovery and cross-process invocation.
"""

import pathlib
import platform
import plistlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
provider = root / "macos/Sources/Features/Services/ServiceProvider.swift"
with (root / "macos/Ghostty-Info.plist").open("rb") as stream:
    services = plistlib.load(stream)["NSServices"]
assert {s["NSMessage"] for s in services} == {"openTab", "openWindow"}
assert all(s["NSRequiredContext"] == {"NSTextContent": "FilePath"} for s in services)
assert all(set(s["NSSendTypes"]) == {"NSFilenamesPboardType", "public.plain-text"} for s in services)

harness = r'''
import AppKit

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}

enum Ghostty {
    struct SurfaceConfiguration { var workingDirectory: String? }
}
final class AppDelegate: NSObject, NSApplicationDelegate { let ghostty = NSObject() }
final class TerminalController {
    struct Call { let tab: Bool; let directory: String?; let parent: NSWindow? }
    static var calls: [Call] = []
    static var preferredParent: TerminalController?
    let window = NSWindow(contentRect: .zero, styleMask: [], backing: .buffered, defer: false)
    static func newWindow(_ app: NSObject, withBaseConfig config: Ghostty.SurfaceConfiguration) -> TerminalController? {
        check(app === (NSApp.delegate as! AppDelegate).ghostty, "Wrong app instance")
        calls.append(Call(tab: false, directory: config.workingDirectory, parent: nil))
        return nil
    }
    static func newTab(_ app: NSObject, from parent: NSWindow?, withBaseConfig config: Ghostty.SurfaceConfiguration) -> TerminalController? {
        check(app === (NSApp.delegate as! AppDelegate).ghostty, "Wrong app instance")
        calls.append(Call(tab: true, directory: config.workingDirectory, parent: parent))
        return nil
    }
}

@main struct Runner {
    @MainActor static func main() throws {
        _ = NSApplication.shared
        let delegate = AppDelegate()
        NSApp.delegate = delegate
        defer { NSApp.delegate = nil }
        let service = ServiceProvider()
        check(service.responds(to: NSSelectorFromString("openTab:userData:error:")), "Missing tab selector")
        check(service.responds(to: NSSelectorFromString("openWindow:userData:error:")), "Missing window selector")
        let fm = FileManager.default
        let base = fm.temporaryDirectory.appendingPathComponent("ghostty-services-\(UUID())", isDirectory: true)
        try fm.createDirectory(at: base, withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: base) }
        let first = base.appendingPathComponent("space 'quote' \u{4E2D}\u{6587}", isDirectory: true)
        let second = base.appendingPathComponent("percent%hash#", isDirectory: true)
        try fm.createDirectory(at: first, withIntermediateDirectories: true)
        try fm.createDirectory(at: second, withIntermediateDirectories: true)
        let file = first.appendingPathComponent("a.txt")
        let another = first.appendingPathComponent("b.txt")
        try Data("test".utf8).write(to: file)
        try Data("test".utf8).write(to: another)
        let board = NSPasteboard.withUniqueName()
        defer { board.releaseGlobally() }

        func invoke(tab: Bool, expected: Set<String>?, parent: NSWindow? = nil) {
            TerminalController.calls = []
            // The provider's nonoptional autoreleasing pointer uses an empty
            // error string as the fixture's untouched success sentinel.
            var error: NSString = ""
            if tab { service.openTab(board, userData: nil, error: &error) }
            else { service.openWindow(board, userData: nil, error: &error) }
            guard let expected else {
                check(TerminalController.calls.isEmpty && error.length > 0, "Invalid input created a terminal or lost error")
                return
            }
            check(error.length == 0, "Valid input produced error: \(error)")
            let calls = TerminalController.calls
            check(calls.count == expected.count, "Directory deduplication/count: \(calls.map { $0.directory })")
            check(Set(calls.compactMap(\.directory)) == expected, "Directory resolution: \(calls.map { $0.directory })")
            check(calls.allSatisfy { $0.tab == tab && $0.parent === parent }, "Wrong target or parent")
        }

        // Legacy Finder service data uses a filename property list, not only
        // modern public.file-url objects. Files in one directory deduplicate.
        let legacy = NSPasteboard.PasteboardType("NSFilenamesPboardType")
        check(board.setPropertyList([file.path, another.path, second.path], forType: legacy), "Legacy write")
        invoke(tab: false, expected: [first.path, second.path])
        let parent = TerminalController()
        TerminalController.preferredParent = parent
        invoke(tab: true, expected: [first.path, second.path], parent: parent.window)
        TerminalController.preferredParent = nil
        invoke(tab: true, expected: [first.path, second.path])

        board.clearContents()
        check(board.writeObjects([file as NSURL, second as NSURL]), "NSURL write")
        invoke(tab: false, expected: [first.path, second.path])

        // Finder may publish a directory URI without a trailing slash. The
        // production resource-value lookup must recognize the actual directory.
        board.clearContents()
        let item = NSPasteboardItem()
        var uri = first.absoluteString
        if uri.hasSuffix("/") { uri.removeLast() }
        item.setString(uri, forType: .fileURL)
        check(board.writeObjects([item]), "Slashless directory write")
        invoke(tab: false, expected: [first.path])

        board.clearContents()
        check(board.writeObjects([URL(fileURLWithPath: "/", isDirectory: true) as NSURL]), "Root write")
        invoke(tab: true, expected: ["/"])

        board.clearContents()
        invoke(tab: false, expected: nil)
        board.setString("not a file path", forType: .string)
        invoke(tab: true, expected: nil)
        board.clearContents()
        check(board.writeObjects([NSURL(string: "https://example.invalid/file")!]), "Remote URL write")
        invoke(tab: false, expected: nil)
        // A bare text path is not converted to NSURL by Monterey AppKit. Keep
        // this explicit: advertised plain-text Services support is not proven
        // by testing Finder's filename representation.
        board.clearContents()
        board.setString(first.path, forType: .string)
        invoke(tab: true, expected: nil)
        board.clearContents()
        board.setString(first.absoluteString, forType: .string)
        invoke(tab: false, expected: nil)
        print("PASS: production service selectors, legacy/modern file data, directories, files, dedup, root, routing and errors")
    }
}
'''

with tempfile.TemporaryDirectory(prefix="ghostty-services-build-") as directory:
    tmp = pathlib.Path(directory)
    runner = tmp / "Runner.swift"
    runner.write_text(harness)
    source = provider.read_text()
    resource_check = "(try? url.resourceValues(forKeys: [.isDirectoryKey]))?.isDirectory ?? url.hasDirectoryPath"
    assert source.count(resource_check) == 1
    for optimize in ("-Onone", "-O"):
        for name, implementation in (("production", source),
                                     ("no-resource-check", source.replace(resource_check, "url.hasDirectoryPath"))):
            implementation_path = tmp / "ServiceProvider.swift"
            implementation_path.write_text(implementation)
            binary = tmp / "check"
            subprocess.run(["xcrun", "swiftc", optimize, "-target", f"{platform.machine()}-apple-macosx12.0",
                            str(implementation_path), str(root / "macos/Sources/Helpers/Extensions/URL+Extension.swift"),
                            str(runner), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimize + ": " + result.stdout.strip())
            else:
                assert result.returncode != 0 and "Directory resolution" in result.stderr, result.stdout + result.stderr
                print(optimize + ": PASS: compiled no-resource-check mutant rejected")
