#!/usr/bin/env python3
"""Check production AX count/range/string methods against native UTF-16 text.

Extracts only these methods with a fixed screen cache, not terminal rendering or
AX transport. Full-app transport coverage lives in services-standalone-check.
"""

import pathlib
import platform
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Ghostty/Surface View/SurfaceView_AppKit.swift").read_text()


def method(name):
    start = source.index("    override func " + name)
    end = source.index("\n    }", start) + len("\n    }")
    return source[start:end]


methods = "\n".join(method(name) for name in (
    "accessibilityNumberOfCharacters", "accessibilityVisibleCharacterRange", "accessibilityString",
    "accessibilityLine", "accessibilityValue", "accessibilitySelectedTextRange()",
    "accessibilitySelectedTextRanges", "accessibilitySelectedText()"))
harness = r'''
import AppKit
final class Cache {
    struct Snapshot {
        var text = ""
        var selectedText = ""
        var ranges: [NSRange] = []
    }
    var value = Snapshot()
    func get() -> Snapshot { value }
}
final class Surface: NSView {
    let accessibilityText = Cache()
    METHODS
}
func check(_ value: Bool, _ message: String) {
    if !value {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}
@main struct Runner {
    static func main() {
        _ = NSApplication.shared
        let surface = Surface()
        let native = NSTextView()
        check(surface.accessibilitySelectedText() == nil, "no selected text")
        check(surface.accessibilitySelectedTextRange().location == NSNotFound, "no selected range")
        check(surface.accessibilitySelectedTextRanges()?.isEmpty == true, "no selected ranges")
        for text in ["", "ASCII\nline", "\u{1f680}", "e\u{301}", "\u{4e2d}\u{6587}",
                     "a\u{1f469}\u{200d}\u{1f4bb}e\u{301}\nlast"] {
            native.string = text
            surface.accessibilityText.value.text = text
            let count = (text as NSString).length
            check(native.accessibilityNumberOfCharacters() == count, "native UTF-16 control")
            check(surface.accessibilityNumberOfCharacters() == count, "production UTF-16 character count")
            let range = surface.accessibilityVisibleCharacterRange()
            check(range == NSRange(location: 0, length: count), "production UTF-16 visible range")
            check(surface.accessibilityString(for: range) == text, "full visible range round trip")
            for index in text.indices {
                let next = text.index(after: index)
                let part = index..<next
                check(surface.accessibilityString(for: NSRange(part, in: text)) == String(text[part]),
                      "grapheme substring at UTF-16 range")
            }
            check(surface.accessibilityString(for: NSRange(location: count + 1, length: 1)) == nil,
                  "out-of-bounds range rejected")
        }
        for text in ["", "ASCII\nnext", "\u{1f680}\nnext", "e\u{301}\nnext",
                     "\u{1f469}\u{200d}\u{1f4bb}\nsecond\nthird"] {
            surface.accessibilityText.value.text = text
            let units = Array(text.utf16)
            for offset in 0...units.count {
                let expected = units.prefix(offset).filter { $0 == 10 }.count
                check(surface.accessibilityLine(for: offset) == expected,
                      "UTF-16 line index at \(offset) in \(text.debugDescription)")
            }
            check(surface.accessibilityLine(for: -1) == NSNotFound, "negative line index rejected")
        }
        let text = "\u{1f680}repeat\nrepeat"
        surface.accessibilityText.value.text = text
        // The second occurrence must retain its origin, not string-search back
        // to the first. Disjoint ranges must not include unselected columns.
        for ranges in [[NSRange(location: 9, length: 6)],
                       [NSRange(location: 2, length: 2), NSRange(location: 9, length: 2)]] {
            let selected = ranges.map { (text as NSString).substring(with: $0) }.joined(separator: "\n")
            surface.accessibilityText.value.selectedText = selected
            surface.accessibilityText.value.ranges = ranges
            check(surface.accessibilityValue() as? String == text, "snapshot value")
            check(surface.accessibilitySelectedText() == selected, "snapshot selected text")
            check(surface.accessibilitySelectedTextRange() == ranges.first!, "snapshot first range")
            check(surface.accessibilitySelectedTextRanges()?.map { $0.rangeValue } == ranges,
                  "snapshot multiple ranges")
        }
        print("PASS: native UTF-16 count, Unicode ranges/lines, snapshot value and disjoint selected ranges")
    }
}
'''.replace("METHODS", methods)
with tempfile.TemporaryDirectory(prefix="ghostty-ax-text-") as directory:
    directory = pathlib.Path(directory)
    for optimization in ("-Onone", "-O"):
        assert methods.count("content.utf16.count") == 2, "Update the count/range mutation boundary"
        variants = [("production", harness, None),
                    ("grapheme-count", harness.replace("content.utf16.count", "content.count"),
                     "production UTF-16 character count"),
                    ("grapheme-range", harness.replace("length: content.utf16.count", "length: content.count"),
                     "production UTF-16 visible range"),
                    ("grapheme-line", harness.replace(
                        "String(decoding: content.utf16.prefix(index), as: UTF16.self)",
                        "String(content.prefix(index))"), "UTF-16 line index")]
        for label, text, failure in variants:
            swift = directory / "Check.swift"
            binary = directory / "check"
            swift.write_text(text)
            subprocess.run(["xcrun", "swiftc", optimization, "-parse-as-library", "-target",
                            f"{platform.machine()}-apple-macosx12.0", str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if failure:
                assert result.returncode != 0 and failure in result.stderr, result.stdout + result.stderr
                print(f"{optimization}: PASS: compiled {label} mutant rejected", flush=True)
            else:
                assert result.returncode == 0, result.stdout + result.stderr
                print(f"{optimization}: {result.stdout.strip()}", flush=True)
