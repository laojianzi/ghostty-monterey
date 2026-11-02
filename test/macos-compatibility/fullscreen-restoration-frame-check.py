#!/usr/bin/env python3
"""Exercise the production fullscreen exit-frame capture/codec boundary with AppKit.

Uses real tabbed windows and NSCoder; shell/controller construction is replaced
by a small NSWindowController shell. Across-launch behavior is in session-check.
"""

import pathlib
import platform
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
controller = (root / "macos/Sources/Features/Terminal/TerminalController.swift").read_text()
capture = controller[controller.index("    var nativeFullscreenFrame:"):controller.index(
    "    // Called when the window will be encoded.")]
restoration = (root / "macos/Sources/Features/Terminal/TerminalRestorable.swift").read_text()
key = next(line.strip() for line in restoration.splitlines() if "static let nativeFullscreenFrameKey" in line)
decode = restoration[restoration.index("        let nativeFrame ="):restoration.index(
    "        let nonNativeFrame =")]
seed = restoration[restoration.index("        if state.effectiveFullscreenMode == .native, let frame = nativeFrame,"):
                   restoration.index("        completionHandler(window, nil)")]
encode = controller[controller.index("        if window.styleMask.contains(.fullScreen), let frame = nativeFullscreenFrame {"):
                    controller.index("        if let frame = (fullscreenStyle as? NonNativeFullscreen)?.restorationFrame {")]
non_native_key = next(line.strip() for line in restoration.splitlines() if "static let nonNativeFullscreenFrameKey" in line)
non_native_decode = restoration[restoration.index("        let nonNativeFrame ="):restoration.index(
    "        guard let state = TerminalRestorableState(coder:")]
non_native_seed = restoration[restoration.index("        if let frame = nonNativeFrame,"):
                             restoration.index("        c.toggleFullscreen(mode: mode)")]
harness = r'''
import Cocoa
class TerminalController: NSWindowController {
    CAPTURE
    func encode(_ window: NSWindow, state: NSCoder) {
        ENCODE
    }
}
enum TerminalWindowRestoration { KEY; OTHER_KEY }
enum FullscreenMode { case native, nonNative }
struct State { let effectiveFullscreenMode: FullscreenMode }
func restore(_ state: NSCoder, mode: FullscreenMode, controller c: TerminalController) {
    let nativeFullscreenFrameKey = TerminalWindowRestoration.nativeFullscreenFrameKey
    DECODE
    let state = State(effectiveFullscreenMode: mode)
    let window = c.window!
    SEED
}
func restoreNonNative(_ state: NSCoder, window: NSWindow) {
    let nonNativeFullscreenFrameKey = TerminalWindowRestoration.nonNativeFullscreenFrameKey
    OTHER_DECODE
    OTHER_SEED
}
func check(_ value: Bool, _ message: String) {
    if !value { FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8)); exit(1) }
}
class ProbeWindow: NSWindow {
    var reportsFullscreen = false
    override var styleMask: NSWindow.StyleMask {
        get { reportsFullscreen ? super.styleMask.union(.fullScreen) : super.styleMask }
        set { super.styleMask = newValue }
    }
}
func window(_ rect: NSRect) -> ProbeWindow {
    let w = ProbeWindow(contentRect: rect, styleMask: [.titled, .resizable], backing: .buffered, defer: false)
    w.isReleasedWhenClosed = false
    w.tabbingMode = .disallowed
    return w
}
@main struct Runner {
    static func main() throws {
        _ = NSApplication.shared
        let a = window(NSRect(x: 100, y: 100, width: 600, height: 400))
        let b = window(NSRect(x: 150, y: 150, width: 500, height: 300))
        let ca = TerminalController(window: a)
        let cb = TerminalController(window: b)
        a.addTabbedWindow(b, ordered: .above)
        let expected = a.frame
        ca.windowWillEnterFullScreen(Notification(name: NSWindow.willEnterFullScreenNotification, object: a))
        check(ca.nativeFullscreenFrame == expected && cb.nativeFullscreenFrame == expected, "capture all tabs")
        // Simulate an already-fullscreen sibling when a tab joins; do not invoke
        // the real asynchronous Space transition in this bounded codec fixture.
        a.reportsFullscreen = true
        ca.nativeFullscreenFrame = expected
        cb.windowWillEnterFullScreen(Notification(name: NSWindow.willEnterFullScreenNotification, object: b))
        check(cb.nativeFullscreenFrame == expected, "inherit sibling exit frame")
        let encoder = NSKeyedArchiver(requiringSecureCoding: true)
        ca.encode(a, state: encoder)
        encoder.finishEncoding()
        let target = window(NSRect(x: 10, y: 10, width: 200, height: 100))
        let ct = TerminalController(window: target)
        let decoder = try NSKeyedUnarchiver(forReadingFrom: encoder.encodedData)
        restore(decoder, mode: .native, controller: ct)
        decoder.finishDecoding()
        check(target.frame == expected && ct.nativeFullscreenFrame == expected, "seed native exit frame")
        a.reportsFullscreen = false
        let regular = NSKeyedArchiver(requiringSecureCoding: true)
        ca.encode(a, state: regular)
        regular.finishEncoding()
        let regularDecoder = try NSKeyedUnarchiver(forReadingFrom: regular.encodedData)
        check(!regularDecoder.containsValue(forKey: TerminalWindowRestoration.nativeFullscreenFrameKey), "omit stale regular frame")
        let before = target.frame
        restore(regularDecoder, mode: .native, controller: ct)
        check(target.frame == before, "old archives without rectangle remain unchanged")
        regularDecoder.finishDecoding()
        let nonNative = NSKeyedArchiver(requiringSecureCoding: true)
        nonNative.encode(NSRect(x: 30, y: 30, width: 400, height: 200),
                         forKey: TerminalWindowRestoration.nativeFullscreenFrameKey)
        nonNative.finishEncoding()
        let nonNativeDecoder = try NSKeyedUnarchiver(forReadingFrom: nonNative.encodedData)
        restore(nonNativeDecoder, mode: .nonNative, controller: ct)
        check(target.frame == before, "non-native restoration ignores native rectangle")
        nonNativeDecoder.finishDecoding()
        // Non-native restoration runs after AppKit has restored the borderless
        // fullscreen rectangle; it must seed the regular frame before enter().
        let nonNativeFrame = NSRect(x: 120, y: 200, width: 648, height: 454)
        let nonNativeArchive = NSKeyedArchiver(requiringSecureCoding: true)
        nonNativeArchive.encode(nonNativeFrame, forKey: TerminalWindowRestoration.nonNativeFullscreenFrameKey)
        nonNativeArchive.finishEncoding()
        let nr = try NSKeyedUnarchiver(forReadingFrom: nonNativeArchive.encodedData)
        restoreNonNative(nr, window: target)
        nr.finishDecoding()
        check(target.frame == nonNativeFrame, "seed non-native exit frame")
        target.setFrame(expected, display: false)
        for invalid in [NSRect.zero, NSRect(x: 0, y: 0, width: -1, height: 1),
                        NSRect(x: CGFloat.infinity, y: 0, width: 1, height: 1)] {
            let bad = NSKeyedArchiver(requiringSecureCoding: true)
            bad.encode(invalid, forKey: TerminalWindowRestoration.nativeFullscreenFrameKey)
            bad.finishEncoding()
            let reader = try NSKeyedUnarchiver(forReadingFrom: bad.encodedData)
            restore(reader, mode: .native, controller: ct)
            reader.finishDecoding()
            check(target.frame == expected, "ignore invalid rectangle \(invalid): \(target.frame), expected \(expected)")
            let badNonNative = NSKeyedArchiver(requiringSecureCoding: true)
            badNonNative.encode(invalid, forKey: TerminalWindowRestoration.nonNativeFullscreenFrameKey)
            badNonNative.finishEncoding()
            let br = try NSKeyedUnarchiver(forReadingFrom: badNonNative.encodedData)
            restoreNonNative(br, window: target)
            br.finishDecoding()
            check(target.frame == expected, "ignore invalid non-native rectangle")
        }
        a.close(); b.close(); target.close()
        print("PASS: capture all tabs, inherit exit frame, secure rectangle codec, seed, regular-state omission and invalid frame rejection")
    }
}
'''
for name, value in (("OTHER_KEY", non_native_key), ("OTHER_DECODE", non_native_decode),
                    ("OTHER_SEED", non_native_seed), ("CAPTURE", capture), ("ENCODE", encode),
                    ("KEY", key), ("DECODE", decode), ("SEED", seed)):
    harness = harness.replace(name, value)
with tempfile.TemporaryDirectory(prefix="ghostty-native-frame-") as directory:
    directory = pathlib.Path(directory)
    swift = directory / "Probe.swift"
    binary = directory / "probe"
    variants = [("production", harness, None),
                ("no-seed", harness.replace("window.setFrame(frame, display: false)", "_ = frame"), "seed native exit frame"),
                ("no-nonnative-seed", harness.replace(non_native_seed, non_native_seed.replace(
                    "window.setFrame(frame, display: false)", "_ = frame")), "seed non-native exit frame"),
                ("negative-size", harness.replace("frame.size.width > 0", "frame.width > 0"), "ignore invalid rectangle")]
    for optimization in ("-Onone", "-O"):
        for name, text, failure in variants:
            assert name == "production" or text != harness
            swift.write_text(text)
            subprocess.run(["xcrun", "swiftc", "-parse-as-library", optimization,
                            "-target", f"{platform.machine()}-apple-macosx12.0",
                            str(swift), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            if failure:
                assert result.returncode != 0 and failure in result.stderr, result.stdout + result.stderr
                print(f"{optimization}: PASS: compiled {name} mutant rejected", flush=True)
            else:
                assert result.returncode == 0, result.stdout + result.stderr
                print(f"{optimization}: {result.stdout.strip()}", flush=True)
