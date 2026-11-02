#!/usr/bin/env python3
"""Run upstream Swift configuration assertions against the built native Zig core.

Build the current universal GhosttyKit first. This bounded Swift Testing adapter
does not replace Xcode/Swift Testing execution semantics. Config/input sources
are compiled whole; only FullscreenMode's cases are extracted (no window actions
are exercised). No default user configuration or Apple events are used.
"""

import argparse
import os
import pathlib
import platform
import plistlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--menu-shortcuts", action="store_true",
                    help="also exercise upstream shortcut tests and native menu dispatch")
args = parser.parse_args()
LIB = ROOT / "macos/GhosttyKit.xcframework/macos-arm64_x86_64"
SOURCES = [
    "Ghostty/GhosttyPackageMeta.swift", "Ghostty/GhosttyPackage.swift",
    "Ghostty/Ghostty.Config.swift", "Ghostty/Ghostty.ConfigTypes.swift",
    "Ghostty/Ghostty.ChildExitedMessage.swift",
    "Ghostty/Ghostty.Command.swift", "Ghostty/Ghostty.Input.swift",
    "Helpers/KeyboardLayout.swift", "Helpers/AppInfo.swift", "Helpers/Private/Dock.swift",
    "Helpers/Extensions/Duration+Extension.swift", "Helpers/Extensions/EventModifiers+Extension.swift",
    "Helpers/Extensions/OSColor+Extension.swift", "Helpers/Extensions/NSScreen+Extension.swift",
    "Helpers/Extensions/UUID+Extension.swift", "Helpers/Extensions/UserDefaults+Extension.swift",
    "Helpers/Extensions/String+Extension.swift", "Helpers/Extensions/Array+Extension.swift",
    "Features/Splits/SplitTree.swift", "Features/QuickTerminal/QuickTerminalPosition.swift",
    "Features/QuickTerminal/QuickTerminalSize.swift", "Features/QuickTerminal/QuickTerminalScreen.swift",
    "Features/QuickTerminal/QuickTerminalSpaceBehavior.swift",
]
tests = (ROOT / "macos/Tests/Ghostty/ConfigTests.swift").read_text()
pattern = re.compile(r"@Test(?:\(arguments:\s*(\[.*?\])\))?\s+func (\w+)\((.*?)\)\s*(throws)?\s*\{", re.S)
matches = list(pattern.finditer(tests))
assert len(matches) == tests.count("@Test") == 38, "Update bounded config adapter"
calls = []
for match in matches:
    arguments, name, parameters, throwing = match.groups()
    prefix = "try " if throwing else ""
    if arguments:
        labels = re.findall(r"(\w+)\s*:\s*[^,]+", parameters)
        assert len(labels) == 2
        values = ", ".join(f"{label}: row.{i}" for i, label in enumerate(labels))
        calls.append(f"for row in {arguments} {{ {prefix}ConfigTests().{name}({values}); count += 1 }}")
    else:
        assert not parameters.strip()
        calls.append(f"{prefix}ConfigTests().{name}(); count += 1")
tests = pattern.sub(lambda m: f"func {m[2]}({m[3]}) {'throws ' if m[4] else ''}{{", tests)
tests = tests.replace("import Testing", "").replace("@testable import Ghostty", "")
tests = tests.replace("@Suite", "").replace("#expect(", "check(").replace("#require(", "require(")
assert not re.search(r"@(?:Suite|Test)|#(?:expect|require)", tests)
helper = (ROOT / "macos/Tests/Helpers/TemporaryConfig.swift").read_text()
helper = helper.replace("@testable import Ghostty\n", "").replace("@testable import GhosttyKit", "import GhosttyKit")
assert helper.count("temporaryFile.path()") == 2
helper = helper.replace("temporaryFile.path()", "temporaryFile.path")
fullscreen = (ROOT / "macos/Sources/Helpers/Fullscreen.swift").read_text()
cases = fullscreen.split("enum FullscreenMode: String, Codable {", 1)[1].split("    /// Initializes", 1)[0]
assert len(re.findall(r"^    case ", cases, re.M)) == 4
runner = r'''
import SwiftUI
import GhosttyKit
struct Missing: Error {}
func check(_ value: Bool, _ message: String = "Upstream config assertion failed",
           file: StaticString = #file, line: UInt = #line) {
    if !value {
        FileHandle.standardError.write(Data("FAIL: \(message) (\(file):\(line))\n".utf8))
        exit(1)
    }
}
func require<T>(_ value: T?) throws -> T {
    guard let value else { throw Missing() }
    return value
}
enum FullscreenMode: String, Codable { FULLSCREEN_CASES }
@main struct Runner {
    @MainActor static func main() throws {
        check(ghostty_init(UInt(CommandLine.argc), CommandLine.unsafeArgv) == 0, "Core init")
        var count = 0
        UPSTREAM_CALLS
        let config = try TemporaryConfig("""
        undo-timeout = 123456789ns
        notify-on-command-finish-after = 1250ms
        abnormal-command-exit-runtime = 4294967295
        """)
        check(config.errors.isEmpty, "Duration config diagnostics")
        check(config.undoTimeout == .milliseconds(123), "Undo duration C ABI units")
        check(config.notifyOnCommandFinishAfter == .milliseconds(1250), "Notification duration C ABI units")
        check(config.abnormalCommandExitRuntime == .milliseconds(UInt32.max), "Exit runtime C ABI width")
        for value: UInt32 in [0, 250, 2500] {
            let runtime = try TemporaryConfig("abnormal-command-exit-runtime = \(value)")
            check(runtime.abnormalCommandExitRuntime == .milliseconds(value), "Exit runtime C ABI value")
        }
        check(Ghostty.Config(config: nil).abnormalCommandExitRuntime == .milliseconds(250),
              "Missing config exit runtime fallback")
        // Exercise the actual message consumer, including the inclusive boundary.
        let threshold = try TemporaryConfig("abnormal-command-exit-runtime = 2500")
        for (exitCode, elapsed, error) in [(UInt32(0), UInt64(2499), true),
                                          (0, 2500, true), (0, 2501, false), (1, 2501, true)] {
            let message = Ghostty.ChildExitedMessage(
                .init(exit_code: exitCode, timetime_ms: elapsed),
                threshold: threshold.abnormalCommandExitRuntime)
            check((message.level == .error) == error, "Configured child-exit threshold behavior")
            check(message.text.contains("Process exited after") == (elapsed <= 2500),
                  "Child-exit duration explanation")
        }
        let longRunning = Ghostty.ChildExitedMessage(
            .init(exit_code: 0, timetime_ms: UInt64.max), threshold: .milliseconds(UInt32.max))
        check(longRunning.level == .success, "Long child runtime overflow")
        let geometry = try TemporaryConfig("""
        window-position-x = -32768
        window-position-y = 32767
        quick-terminal-size = 25%,300px
        quick-terminal-position = right
        quick-terminal-animation-duration = 0.125
        quick-terminal-autohide = false
        resize-overlay-duration = 1250ms
        """)
        check(geometry.errors.isEmpty, "Geometry config diagnostics")
        check(geometry.windowPositionX == Int16.min && geometry.windowPositionY == Int16.max,
              "Signed coordinate C ABI")
        check(geometry.quickTerminalPosition == .right && !geometry.quickTerminalAutoHide,
              "Quick terminal enum/bool C ABI")
        check(geometry.quickTerminalAnimationDuration == 0.125, "Quick terminal float C ABI")
        check(geometry.resizeOverlayDuration == 1250, "Resize overlay duration C ABI")
        let size = geometry.quickTerminalSize
        let landscape = CGSize(width: 1200, height: 800)
        check(size.calculate(position: .right, screenDimensions: landscape) == CGSize(width: 300, height: 300),
              "Quick terminal tagged size C ABI")
        check(size.calculate(position: .top, screenDimensions: landscape) == CGSize(width: 300, height: 200),
              "Quick terminal size axes")
        let cloned = Ghostty.Config(clone: try require(config.config))
        try config.reload("undo-timeout = 0s")
        check(config.undoTimeout == .seconds(0), "Zero timeout reload")
        check(cloned.undoTimeout == .milliseconds(123), "Clone aliases reloaded configuration")
        print("PASS: \(count) upstream configuration invocations; duration/geometry ABI, child-exit behavior, reload and clone ownership")
    }
}
'''.replace("FULLSCREEN_CASES", cases).replace("UPSTREAM_CALLS", "\n".join(calls))

menu_tests = ""
if args.menu_shortcuts:
    SOURCES += ["Ghostty/Ghostty.MenuShortcutManager.swift", "Helpers/Weak.swift"]
    menu_calls = []
    for suite, expected in (("MenuShortcutManagerTests", 3), ("NormalizedMenuShortcutKeyTests", 12)):
        text = (ROOT / f"macos/Tests/Ghostty/{suite}.swift").read_text()
        # Run these synchronous AppKit operations serially on the main actor;
        # the upstream async methods only await actor hops, not asynchronous IO.
        text = re.sub(r'@Test\(\.bug\("https://github.com/ghostty-org/ghostty/issues/\d+", id: \d+\)\)',
                      "@Test", text)
        pattern = re.compile(r"@Test\s+func (\w+)\(\)\s*(async\s+)?(throws\s+)?\{")
        methods = list(pattern.finditer(text))
        assert len(methods) == text.count("@Test") == expected, suite
        for method in methods:
            menu_calls.append(f"{'try ' if method[3] else ''}{suite}().{method[1]}()")
        text = pattern.sub(lambda m: f"func {m[1]}() {'throws ' if m[3] else ''}{{", text)
        text = text.replace("await ", "").replace("@Suite", "@MainActor")
        if suite == "MenuShortcutManagerTests":
            text = text.replace("struct MenuShortcutManagerTests", "@MainActor struct MenuShortcutManagerTests")
            selector = "#selector(BaseTerminalController.splitRight(_:))"
            assert text.count(selector) == 1
            text = text.replace(selector, 'NSSelectorFromString("splitRight:")')
        text = text.replace("import Testing", "").replace("@testable import Ghostty", "")
        text = text.replace("#expect(", "check(").replace("#require(", "require(")
        assert not re.search(r"@(?:Suite|Test)|#(?:expect|require)|\bawait\b", text), suite
        menu_tests += text + "\n"
    menu_tests += (ROOT / "test/macos-compatibility/menu-shortcut-check.swift").read_text()
    runner = runner.replace("        var count = 0", "        " + "\n        ".join(menu_calls) +
                            "\n        try checkMenuDispatch()\n        var count = 0")

with tempfile.TemporaryDirectory(prefix="ghostty-config-check-", dir="/tmp") as directory:
    tmp = pathlib.Path(directory)
    app = tmp / "ConfigProbe.app"
    binary = app / "Contents/MacOS/probe"
    binary.parent.mkdir(parents=True)
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps({
        "CFBundleIdentifier": "com.mitchellh.ghostty.config-probe",
        "CFBundleExecutable": "probe", "CFBundlePackageType": "APPL",
    }))
    for name, text in (("Tests.swift", tests + menu_tests), ("TemporaryConfig.swift", helper), ("Runner.swift", runner),
                       ("Bridge.h", "#import <Cocoa/Cocoa.h>\n")):
        (tmp / name).write_text(text)
    source_paths = [ROOT / "macos/Sources" / path for path in SOURCES]
    config_index = SOURCES.index("Ghostty/Ghostty.Config.swift")
    implementation = source_paths[config_index].read_text()
    original = "return .milliseconds(v)"
    # Change only undoTimeout's units, not all duration accessors.
    start = implementation.index("var undoTimeout:")
    end = implementation.index("\n        var ", start + 1)
    segment = implementation[start:end]
    assert segment.count(original) == 1
    mutant = implementation[:start] + segment.replace(original, "return .nanoseconds(v)") + implementation[end:]
    start = implementation.index("var abnormalCommandExitRuntime:")
    end = implementation.index("\n        var ", start + 1)
    segment = implementation[start:end]
    assert segment.count("var v: UInt32 = 0") == 1
    optional = segment.replace("var v: UInt32 = 0", "var v: UInt32?")
    optional = optional.replace("return .milliseconds(v)",
                                "guard let v else { return defaultValue }\n            return .milliseconds(v)")
    optional_mutant = implementation[:start] + optional + implementation[end:]
    env = dict(os.environ)
    env.pop("DYLD_INSERT_LIBRARIES", None)
    # Negative controls exit at an assertion without Swift deinit. Keep their
    # TemporaryConfig files inside the Python-owned directory for cleanup too.
    config_directory = tmp / "configs"
    config_directory.mkdir()
    env["TMPDIR"] = str(config_directory) + "/"
    variants = [("production", implementation), ("wrong-undo-units", mutant),
                ("optional-integer-storage", optional_mutant)]
    expected_failures = {"wrong-undo-units": "Undo duration C ABI units",
                         "optional-integer-storage": "Exit runtime C ABI width"}
    if args.menu_shortcuts:
        menu_index = SOURCES.index("Ghostty/Ghostty.MenuShortcutManager.swift")
        menu_source = source_paths[menu_index].read_text()
        guard = "guard item.isEnabled else {"
        assert menu_source.count(guard) == 1
        disabled_mutant = menu_source.replace(guard, "guard true else {")
        variants.append(("disabled-menu-dispatch", implementation))
        expected_failures["disabled-menu-dispatch"] = "Disabled physical binding consumed"
    for optimization in ("-Onone", "-O"):
        for name, source in variants:
            if args.menu_shortcuts:
                menu_path = tmp / "MenuShortcutManager.swift"
                menu_path.write_text(disabled_mutant if name == "disabled-menu-dispatch" else menu_source)
                source_paths[menu_index] = menu_path
            config_source = tmp / "Config.swift"
            config_source.write_text(source)
            source_paths[config_index] = config_source
            command = ["xcrun", "swiftc", optimization, "-target", f"{platform.machine()}-apple-macosx12.0",
                       "-import-objc-header", str(tmp / "Bridge.h"), "-I", str(LIB / "Headers"),
                       *map(str, source_paths), *[str(tmp / p) for p in ("Tests.swift", "TemporaryConfig.swift", "Runner.swift")],
                       str(LIB / "ghostty-internal.a"), "-lc++", "-o", str(binary)]
            for framework in ("Metal", "MetalKit", "CoreVideo", "CoreText", "Carbon", "QuartzCore", "IOSurface"):
                command += ["-framework", framework]
            subprocess.run(command, check=True)
            result = subprocess.run([str(binary)], env=env, text=True, capture_output=True, timeout=30)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimization + ": " + result.stdout.strip(), flush=True)
            else:
                expected = expected_failures[name]
                assert result.returncode != 0 and expected in result.stderr, result.stdout + result.stderr
                print(optimization + f": PASS: compiled {name} mutant rejected", flush=True)
