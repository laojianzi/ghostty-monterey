#!/usr/bin/env python3
"""Exercise production layout translation across already-enabled input sources.

Changes the selected input source temporarily, never enables/removes a source,
and restores the original selection. Requires an unlocked local GUI session.
Complements full-app scripting/IME checks; does not type into the foreground app.
"""
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
probe = r'''import AppKit
import Carbon

func id(_ source: TISInputSource) -> String {
    guard let raw = TISGetInputSourceProperty(source, kTISPropertyInputSourceID) else { return "" }
    return Unmanaged<CFString>.fromOpaque(raw).takeUnretainedValue() as String
}

@main struct Main {
    @MainActor static func main() {
        _ = NSApplication.shared
        let session = CGSessionCopyCurrentDictionary() as? [String: Any]
        precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false))
        let original = TISCopyCurrentKeyboardInputSource().takeRetainedValue()
        let sources = TISCreateInputSourceList(nil, false).takeRetainedValue() as! [TISInputSource]
        let names = ["com.apple.keylayout.ABC", "com.tencent.inputmethod.wetype.pinyin",
                     "com.apple.inputmethod.SCIM.ITABC"]
        var failures: [String] = []
        for name in names {
            guard let source = sources.first(where: { id($0) == name }) else {
                failures.append("Missing enabled source: \(name)")
                continue
            }
            guard TISSelectInputSource(source) == noErr else {
                failures.append("Cannot select: \(name)")
                continue
            }
            RunLoop.current.run(until: Date().addingTimeInterval(0.5))
            if KeyboardLayout.id != name { failures.append("Source did not settle: \(name)") }
            for (key, plain, shifted): (UInt16, String, String) in [(0, "a", "A"), (18, "1", "!"), (50, "`", "~")] {
                let cases: [(NSEvent.ModifierFlags, String)] = [([], plain), (.shift, shifted)]
                for (mods, expected) in cases {
                    let got = KeyboardLayout.character(for: key, modifiers: mods).map(String.init)
                    if got == nil { failures.append("\(name) key=\(key) mods=\(mods.rawValue): no translation") }
                    // Pinyin can translate punctuation to full-width characters.
                    if (name == "com.apple.keylayout.ABC" || key == 0) && got != expected {
                        failures.append("\(name) key=\(key) mods=\(mods.rawValue): \(got ?? "nil") != \(expected)")
                    }
                    let event = NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: [],
                        timestamp: 0, windowNumber: 0, context: nil, characters: "",
                        charactersIgnoringModifiers: "", isARepeat: false, keyCode: key)!
                    if let native = event.characters(byApplyingModifiers: mods), native.count == 1,
                       got != native { failures.append("Changed AppKit translation: \(name) key=\(key)") }
                }
            }
            if KeyboardLayout.character(for: UInt16.max, modifiers: []) != nil {
                failures.append("Invalid key accepted: \(name)")
            }
        }
        let restored = TISSelectInputSource(original) == noErr
        RunLoop.current.run(until: Date().addingTimeInterval(0.5))
        if !restored || KeyboardLayout.id != id(original) { failures.append("Original source not restored") }
        failures.forEach { print("FAIL: \($0)") }
        if failures.isEmpty { print("PASS: ABC, WeType and system Pinyin layout translation; original source restored") }
        exit(failures.isEmpty ? 0 : 1)
    }
}
'''
for optimization in ("-Onone", "-O"):
    with tempfile.TemporaryDirectory(prefix="ghostty-layout-input-") as directory:
        work = Path(directory)
        swift, executable = work / "probe.swift", work / "check"
        swift.write_text(probe)
        subprocess.run(["xcrun", "swiftc", "-parse-as-library", optimization,
                        str(ROOT / "macos/Sources/Helpers/KeyboardLayout.swift"),
                        str(swift), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True, timeout=15)
