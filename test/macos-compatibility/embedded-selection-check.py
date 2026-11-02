#!/usr/bin/env python3
"""Exercise the real embedded core with window-local mouse gestures on macOS 12.

Not the full Ghostty SurfaceView: this tests the C bridge,
native core gestures, extracted production button/AX methods and ownership.
Position/cache and scripted interpretKeyEvents responses remain test adapters.
Modifier mapping, key identity lookup and keyDown orchestration use production
code with native Carbon and the real encoder/PTY, not full OS IME dispatch.
No global input, user config, clipboard access or permission changes.
--accessibility temporarily activates the probe and queries it from another
process using existing AX permission; normal completion restores prior focus.
"""
import argparse
import os
import pathlib
import platform
import plistlib
import re
import shlex
import subprocess
import sys
import tempfile
import time

root = pathlib.Path(__file__).resolve().parents[2]
lib = root / "macos/GhosttyKit.xcframework/macos-arm64_x86_64"
surface_source = (root / "macos/Sources/Ghostty/Surface View/SurfaceView_AppKit.swift").read_text()
input_source = (root / "macos/Sources/Ghostty/Ghostty.Input.swift").read_text()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--accessibility", action="store_true", help="Require existing AX permission and query from another process")
parser.add_argument("--committed-input", action="store_true", help="Check production committed-text encoding into a raw PTY")
parser.add_argument("--native-input", action="store_true", help="Also run native interpretKeyEvents; requires current ABC/US layout")
parser.add_argument("--dead-key", action="store_true", help="Experimental native Option-E probe; currently fails with synthetic events")
args = parser.parse_args()
if args.dead_key:
    args.native_input = True
if args.native_input:
    args.committed_input = True


def method(name):
    indent = "    " if name.startswith(("accessibility", "isAccessibility", "doCommand")) else "        "
    start = surface_source.index(indent + "override func " + name)
    closing = re.search(r"\n {" + str(len(indent)) + r"," + str(len(indent) + 1) + r"}\}", surface_source[start:])
    assert closing, f"Missing method boundary: {name}"
    end = start + closing.end()
    return surface_source[start:end]


def plain_method(name, indent="    ", private=False):
    start = surface_source.index(indent + ("private " if private else "") + "func " + name + "(")
    end = surface_source.index("\n" + indent + "}", start) + len("\n" + indent + "}")
    return surface_source[start:end].replace("private func", "func", 1)


with tempfile.TemporaryDirectory(prefix="ghostty-embedded-selection-") as directory:
    work = pathlib.Path(directory)
    child = work / "child.py"
    child.write_text("import os, pathlib, time, tty\n"
                     f"pathlib.Path({str(work / 'child.pid')!r}).write_text(str(os.getpid()))\n"
                     + ("tty.setraw(0)\nprint('\\x1b[?2004h', end='', flush=True)\n" if args.committed_input else "") +
                     "print('\\x1b[2J\\x1b[H\\U0001f680e\\u030123456 CDEFG stuvw\\r\\n0123456789abcdef\\r\\nABCDEFGHIJKLMNOP\\r\\nqrstuvwxyz012345', flush=True)\n"
                     + (f"destination = pathlib.Path({str(work / 'input.bin')!r})\n"
                        "data = b''\nwhile True:\n data += os.read(0, 4096)\n"
                        " temporary = destination.with_suffix('.pending')\n temporary.write_bytes(data)\n"
                        " temporary.replace(destination)\n" if args.committed_input else "while True: time.sleep(1)\n"))
    config = work / "config"
    config.write_text("shell-integration = none\ncopy-on-select = none\nclipboard-read = deny\n"
                      "clipboard-write = deny\nwindow-padding-x = 0\nwindow-padding-y = 0\n"
                      "window-padding-balance = false\nfont-size = 16\n"
                      "command = shell:" + shlex.join([sys.executable, str(child)]) + "\n")
    if args.native_input:
        with config.open("a") as stream:
            stream.write("macos-option-as-alt = false\n")
    bundle = work / "SelectionProbe.app"
    (bundle / "Contents/MacOS").mkdir(parents=True)
    (bundle / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "com.mitchellh.ghostty.selection-probe",
        "CFBundleExecutable": "check", "CFBundleName": "SelectionProbe",
        "CFBundlePackageType": "APPL", "LSMinimumSystemVersion": "12.0",
        "NSPrincipalClass": "NSApplication",
    }))
    binary = bundle / "Contents/MacOS/check"
    source = work / "main.swift"
    def input_method(name):
        start = input_source.index("    static func " + name + "(")
        end = input_source.index("\n    }", start) + len("\n    }")
        return input_source[start:end]

    snapshot_adapter = "struct AccessibilityTextSnapshot {" + surface_source.split("struct AccessibilityTextSnapshot {", 1)[1].split("/// Caches a value", 1)[0]
    source.write_text(snapshot_adapter + "\n" + pathlib.Path(__file__).with_suffix(".swift").read_text() + "\n" + r'''
enum Ghostty {
    struct Input {}
    typealias SurfaceView = TerminalView
''' + input_method("ghosttyMods") + "\n" + input_method("eventModifierFlags") + r'''
}
extension TerminalView {
''' + "\n".join(method(name) for name in (
        "mouseDown", "mouseUp", "accessibilityValue", "accessibilitySelectedText()",
        "accessibilitySelectedTextRange()", "accessibilitySelectedTextRanges",
        "accessibilityNumberOfCharacters", "accessibilityString", "isAccessibilityElement",
        "accessibilityRole", "doCommand")) + "\n" +
        plain_method("selectedText") + "\n" +
        plain_method("committedTextAction", "        ", True) + "\n" +
        plain_method("keyAction", "        ", True) + "\n" +
        plain_method("shouldReplayCommittedPreeditKey", "        ", True) + "\n" +
        method("keyDown").replace("override func keyDown", "func productionKeyDown", 1) + "\n" +
        "    static func shouldSuppressComposingControlInput(" +
        surface_source.split("    static func shouldSuppressComposingControlInput(", 1)[1].split("\n    }", 1)[0] + "\n    }\n" +
        "\n".join(plain_method(name) for name in ("setMarkedText", "unmarkText", "hasMarkedText", "markedRange", "insertText",
                                                "selectedRange", "validAttributesForMarkedText", "attributedSubstring",
                                                "characterIndex", "firstRect")) + "\n" +
        plain_method("syncPreedit", private=True) + "\n}\n" +
        "struct LeadSurrogate {" + surface_source.split("struct LeadSurrogate {", 1)[1] + "\n" +
        r'''
struct AXTextCache {
    let surface: ghostty_surface_t?
    func get() -> AccessibilityTextSnapshot {
        guard let surface else { return .init() }
        return AccessibilityTextSnapshot(surface: surface)
    }
}
// Uncached original full-text reader for independent text comparison.
struct TextCache {
    let surface: ghostty_surface_t?
    func get() -> String {
        guard let surface else { return "" }
        var value = ghostty_text_s()
        let selection = ghostty_selection_s(
            top_left: ghostty_point_s(tag: GHOSTTY_POINT_SCREEN, coord: GHOSTTY_POINT_COORD_TOP_LEFT, x: 0, y: 0),
            bottom_right: ghostty_point_s(tag: GHOSTTY_POINT_SCREEN, coord: GHOSTTY_POINT_COORD_BOTTOM_RIGHT, x: 0, y: 0),
            rectangle: false)
        guard ghostty_surface_read_text(surface, selection, &value) else { return "" }
        defer { ghostty_surface_free_text(surface, &value) }
        return String(cString: value.text)
    }
}
''' + input_source[input_source.index("// MARK: Ghostty.Input.Key"):] + "\n" +
        (root / "macos/Sources/Helpers/Extensions/String+Extension.swift").read_text().split("    func truncate", 1)[0] + "}\n")
    command = ["xcrun", "swiftc", "-Onone", "-target", f"{platform.machine()}-apple-macosx12.0",
               "-I", str(lib / "Headers"), str(source),
               str(root / "macos/Sources/Helpers/KeyboardLayout.swift"),
               str(root / "macos/Sources/Ghostty/NSEvent+Extension.swift"),
               str(lib / "ghostty-internal.a"), "-lc++", "-o", str(binary)]
    for framework in ("Metal", "MetalKit", "CoreVideo", "CoreText", "Carbon", "QuartzCore", "IOSurface"):
        command += ["-framework", framework]
    subprocess.run(command, check=True)
    ax_args = []
    if args.accessibility:
        client = work / "ax-client"
        subprocess.run(["xcrun", "swiftc", str(pathlib.Path(__file__).with_name("embedded-selection-ax-client.swift")),
                        "-o", str(client)], check=True)
        ax_args = ["--ax-client", str(client)]
    env = os.environ.copy()
    env["GHOSTTY_RESOURCES_DIR"] = str(root / "macos/build/ReleaseLocal/Ghostty.app/Contents/Resources/ghostty")
    input_args = ["--committed-input", str(work / "input.bin")] if args.committed_input else []
    if args.native_input:
        input_args += ["--native-input"]
    if args.dead_key:
        input_args += ["--dead-key"]
    def run(extra, remote=True):
        (work / "input.bin").unlink(missing_ok=True)
        (work / "child.pid").unlink(missing_ok=True)
        timeout = None
        try:
            result = subprocess.run([str(binary), str(config), *extra, *(ax_args if remote else []), *input_args], env=env,
                                    capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as error:
            timeout = error
        # Surface teardown (or process death for the negative control) must
        # release the real child. Never blindly kill a possibly reused PID.
        pid = int((work / "child.pid").read_text())
        deadline = time.monotonic() + 5
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            assert time.monotonic() < deadline, f"Child {pid} retained after fixture"
            time.sleep(0.05)
        if timeout:
            print(timeout.stdout, timeout.stderr, flush=True)
            raise timeout
        return result

    for label, extra in [("production", []), ("no-option-control", ["--no-option"])]:
        result = run(extra)
        if label == "production":
            assert result.returncode == 0, result.stdout + result.stderr
            print(result.stdout.strip(), flush=True)
        else:
            assert result.returncode != 0 and "Mouse gesture selected unexpected text" in result.stderr, result.stdout + result.stderr
            print("PASS: no-Option negative control rejected by rectangle assertion", flush=True)
    if args.committed_input:
        text = source.read_text()
        mutants = [
            ("paste-instead-of-key", "key_ev.text = ptr\n                return ghostty_surface_key(surface, key_ev)",
             "key_ev.text = ptr\n                ghostty_surface_paste_text(surface, ptr, UInt(text.utf8.count)); return true",
             "Committed text PTY bytes mismatch"),
            ("lost-surrogate-pair", 'chars = leadSurrogate?.encode(trail: trail) ?? ""', 'chars = ""',
             "insertText branch PTY bytes mismatch"),
            ("bypassed-accumulator", "if var acc = keyTextAccumulator {", "if var acc = Optional<[String]>.none {",
             "Key event accumulator contents"),
            ("lost-arrow-replay", "if shouldReplayCommittedPreeditKey(translationEvent) {", "if false {",
             "insertText branch PTY bytes mismatch"),
            ("leaked-composing-control", "return scalar.value < 0x20\n", "return false\n",
             "insertText branch PTY bytes mismatch"),
            ("replayed-plain-left", "return !event.modifierFlags.isDisjoint(with: [.shift, .control, .option, .command])",
             "return true", "insertText branch PTY bytes mismatch"),
        ]
        for label, old, new, diagnostic in mutants:
            assert text.count(old) == 1
            source.write_text(text.replace(old, new))
            subprocess.run(command, check=True)
            result = run([], remote=False)
            assert result.returncode != 0 and diagnostic in result.stderr, result.stdout + result.stderr
            print(f"PASS: compiled {label} mutant rejected by {diagnostic}", flush=True)
