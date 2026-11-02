#!/usr/bin/env python3
"""Test production MIME pasteboard helpers on Monterey without user clipboard writes.

Exercises native lazy providers and actual production shell escaping. This is
not an end-to-end OSC 5522 protocol or clipboard-permission UI test.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
pasteboard = root / "macos/Sources/Helpers/Extensions/NSPasteboard+Extension.swift"
shell = root / "macos/Sources/Ghostty/Ghostty.Shell.swift"
harness = r'''
import AppKit
import UniformTypeIdentifiers
import GhosttyKit
enum Ghostty {}

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}

final class Provider: NSObject, NSPasteboardItemDataProvider {
    var requests: [NSPasteboard.PasteboardType] = []
    let bytes: Data
    init(_ bytes: Data) { self.bytes = bytes }
    func pasteboard(_ pasteboard: NSPasteboard?, item: NSPasteboardItem,
                    provideDataForType type: NSPasteboard.PasteboardType) {
        requests.append(type)
        item.setData(bytes, forType: type)
    }
}

@main struct Runner {
    @MainActor static func main() {
        let board = NSPasteboard.withUniqueName()
        defer { board.releaseGlobally() }
        check(board.ghosttyAvailableMimes().isEmpty, "empty board advertises MIME types")
        check(board.ghosttyData(forMime: "text/plain") == nil, "empty board serves text")
        check(board.ghosttyData(forMime: "text/uri-list") == nil, "empty board serves URLs")

        let text = Data("hello \u{4E2D}\u{6587}\n".utf8)
        let provider = Provider(text)
        let lazy = NSPasteboardItem()
        lazy.setDataProvider(provider, forTypes: [.string])
        check(board.writeObjects([lazy]), "write lazy item failed")
        for _ in 0..<3 {
            check(board.ghosttyAvailableMimes() == ["text/plain"], "text MIME normalization")
        }
        check(provider.requests.isEmpty, "MIME enumeration fetched lazy contents")
        check(board.ghosttyData(forMime: "text/plain") == text, "UTF-8 text changed")
        check(provider.requests == [.string], "explicit read did not request the declared provider type")

        board.clearContents()
        let bytes = Data([0, 255, 128, 1, 0, 10, 13])
        let imageProvider = Provider(bytes)
        let image = NSPasteboardItem()
        image.setDataProvider(imageProvider, forTypes: [.png])
        board.writeObjects([image])
        // AppKit also declares synthesized TIFF/legacy image representations.
        let imageMimes = board.ghosttyAvailableMimes()
        check(imageMimes.contains("image/png") && Set(imageMimes).count == imageMimes.count,
              "PNG MIME mapping/deduplication: \(imageMimes)")
        check(imageProvider.requests.isEmpty, "MIME enumeration fetched image bytes")
        check(board.ghosttyData(forMime: "image/png") == bytes, "binary data changed")
        check(imageProvider.requests == [.png], "image provider not read")
        check(board.ghosttyData(forMime: "text/plain") == nil, "binary-only clipboard served text")

        board.clearContents()
        let fileProvider = Provider(Data(URL(fileURLWithPath: "/tmp/lazy file").absoluteString.utf8))
        let lazyFile = NSPasteboardItem()
        lazyFile.setDataProvider(fileProvider, forTypes: [.fileURL])
        board.writeObjects([lazyFile])
        let fileMimes = board.ghosttyAvailableMimes()
        check(fileMimes.contains("text/plain") && fileMimes.contains("text/uri-list"), "lazy file metadata")
        check(fileProvider.requests.isEmpty, "MIME enumeration fetched file URL contents")
        check(board.ghosttyData(forMime: "text/uri-list") == Data("file:///tmp/lazy%20file\r\n".utf8),
              "lazy file URI read")
        check(fileProvider.requests == [.fileURL], "file URL provider not read")

        board.clearContents()
        let paths = ["/tmp/a b.txt", "/tmp/quote'\";$name", "/tmp/\u{4E2D}\u{6587}.txt"]
        let urls = paths.map { URL(fileURLWithPath: $0) }
        let items = urls.map { url -> NSPasteboardItem in
            let item = NSPasteboardItem()
            item.setString(url.absoluteString, forType: .fileURL)
            item.setString("Finder label must not replace path", forType: .string)
            return item
        }
        board.writeObjects(items)
        let mimes = board.ghosttyAvailableMimes()
        check(mimes == ["text/plain", "text/uri-list"], "file MIME ordering/deduplication: \(mimes)")
        let escaped = paths.map { Ghostty.Shell.escape($0) }.joined(separator: " ")
        check(board.ghosttyData(forMime: "text/plain") == Data(escaped.utf8), "file path escaping/precedence")
        let uriList = urls.map { $0.absoluteString + "\r\n" }.joined()
        check(board.ghosttyData(forMime: "text/uri-list") == Data(uriList.utf8), "URI list encoding/order/CRLF")

        board.clearContents()
        let first = NSPasteboardItem()
        first.setString("one", forType: .string)
        let second = NSPasteboardItem()
        second.setString("two", forType: .string)
        board.writeObjects([first, second])
        check(board.ghosttyData(forMime: "text/plain") == Data("one two".utf8), "multi-item string ordering")
        check(board.ghosttyAvailableMimes() == ["text/plain"], "duplicate text MIME")
        check(board.ghosttyData(forMime: "image/png") == nil, "unavailable MIME served data")

        board.clearContents()
        let remote = NSPasteboardItem()
        remote.setString("https://example.invalid/file", forType: .fileURL)
        remote.setString("fallback text", forType: .string)
        board.writeObjects([remote])
        check(board.ghosttyData(forMime: "text/uri-list") == nil, "non-file URL treated as copied file")
        check(board.ghosttyData(forMime: "text/plain") == Data("fallback text".utf8), "non-file string fallback")

        board.clearContents()
        let customMime = "application/x-ghostty-test"
        let customType = NSPasteboard.PasteboardType(mimeType: customMime)!
        board.setData(bytes, forType: customType)
        check(board.ghosttyData(forMime: customMime) == bytes, "custom MIME round trip")
        check(board.ghosttyAvailableMimes().contains(customMime), "custom MIME metadata round trip")
        check(NSPasteboard.ghostty(GHOSTTY_CLIPBOARD_PRIMARY) == nil, "unsupported primary clipboard not rejected")
        check(NSPasteboard.ghostty(GHOSTTY_CLIPBOARD_STANDARD) === NSPasteboard.general, "standard clipboard routing")
        check(NSPasteboard.ghostty(GHOSTTY_CLIPBOARD_SELECTION) === NSPasteboard.ghosttySelection, "selection clipboard routing")
        print("PASS: lazy metadata-only MIME enumeration, UTF-8/binary, files, URI lists, routing")
    }
}
'''

with tempfile.TemporaryDirectory(prefix="ghostty-pasteboard-mime-") as directory:
    directory = pathlib.Path(directory)
    swift = directory / "Runner.swift"
    swift.write_text(harness)
    production = pasteboard.read_text()
    marker = "        let availableTypes = types ?? []"
    assert production.count(marker) == 1, "Update the eager-read mutation"
    mutant = directory / "EagerPasteboard.swift"
    mutant.write_text(production.replace(marker, marker + "\n        _ = string(forType: .string)"))
    for optimize in ("-Onone", "-O"):
        for name, implementation in (("production", pasteboard), ("eager-read-mutant", mutant)):
            binary = directory / name
            subprocess.run(["swiftc", "-enable-bare-slash-regex", optimize,
                            "-I", str(root / "macos/GhosttyKit.xcframework/macos-arm64_x86_64/Headers"),
                            str(shell), str(implementation), str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if name == "production":
                assert result.returncode == 0, result.stderr
                print(f"{optimize}: {result.stdout.strip()}")
            else:
                assert result.returncode != 0 and "MIME enumeration fetched lazy contents" in result.stderr, result.stderr
                print(f"{optimize}: PASS: compiled eager-read mutant rejected")
