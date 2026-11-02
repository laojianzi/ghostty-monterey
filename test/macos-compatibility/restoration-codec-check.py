#!/usr/bin/env python3
"""Run upstream archive migrations through the production schemas/secure bridge.

Controller constructors and terminal surfaces are not linked. Use the upstream
MockView and dummy restorable types, and extract complete schema declarations.
This proves archive compatibility, not GUI restoration or shell state survival.
"""

import pathlib
import platform
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]


def source(path):
    return (ROOT / "macos" / path).read_text()


terminal = source("Sources/Features/Terminal/TerminalRestorable.swift")
quick = source("Sources/Features/QuickTerminal/QuickTerminalRestorableState.swift")
protocol = terminal.split("/// The state stored for terminal window restoration.")[0]
assert "func encode(with coder: NSCoder)" in protocol
terminal_versions = re.findall(r"    static var (?:version|minimumVersion): Int \{ \d+ \}", terminal)
quick_versions = re.findall(r"    static var version: Int \{ \d+ \}", quick)
assert len(terminal_versions) == 2 and len(quick_versions) == 1
terminal_schema = source("Sources/Features/Terminal/TerminalRestorableState+InteralState.swift").split(
    "extension TerminalRestorableState.InternalState where")[0]
quick_schema = "extension QuickTerminalRestorableState {" + quick.split(
    "extension QuickTerminalRestorableState {", 1)[1].split(
    "extension QuickTerminalRestorableState.InternalState where")[0]
fullscreen = source("Sources/Helpers/Fullscreen.swift").split(
    "enum FullscreenMode: String, Codable {", 1)[1].split("    /// Initializes", 1)[0]
assert len(re.findall(r"^    case ", fullscreen, re.M)) == 4
tab_color = source("Sources/Features/Terminal/TerminalTabColor.swift").split("// MARK: - Menu View")[0]
mock = source("Tests/Splits/SplitTreeTests.swift").split("class MockView:", 1)[1].split(
    "struct SplitTreeTests", 1)[0]
tests = source("Tests/Terminal/TerminalRestorableTests.swift")
pattern = re.compile(r"@Test\s+func (\w+)\(\)\s*(throws\s+)?\{")
methods = list(pattern.finditer(tests))
assert len(methods) == tests.count("@Test") == 3
calls = [f'print("RUN: {m[1]}"); fflush(stdout)\n' +
         f"{'try ' if m[2] else ''}TerminalRestorableTests().{m[1]}()" for m in methods]
tests = pattern.sub(lambda m: f"func {m[1]}() {'throws ' if m[2] else ''}{{", tests)
tests = tests.replace("import Testing", "").replace("@testable import Ghostty", "")
tests = tests.replace("@Suite", "").replace("#expect(", "check(").replace("#require(", "require(")
assert not re.search(r"@(?:Suite|Test)|#(?:expect|require)", tests)

runner = r'''
import Cocoa
import os

// Only dependencies of the protocol's unused default configuration and logging.
enum Ghostty { struct SurfaceConfiguration {} }
enum AppDelegate { static let logger = Logger(subsystem: "restoration-codec-probe", category: "test") }
enum TerminalRestorableState { TERMINAL_VERSIONS }
enum QuickTerminalRestorableState {
    QUICK_VERSIONS
    static var minimumVersion: Int { version }
}
enum FullscreenMode: String, Codable { FULLSCREEN_CASES }
struct Missing: Error {}
func check(_ value: Bool, file: StaticString = #file, line: UInt = #line) {
    if !value {
        FileHandle.standardError.write(Data("FAIL: archive assertion at \(file):\(line)\n".utf8))
        exit(1)
    }
}
func require<T>(_ value: T?) throws -> T {
    guard let value else { throw Missing() }
    return value
}

@main struct Runner {
    @MainActor static func main() {
        do { try run() } catch {
            FileHandle.standardError.write(Data("FAIL: archive decode: \(error)\n".utf8))
            exit(1)
        }
    }

    @MainActor static func run() throws {
        UPSTREAM_CALLS
        print("RUN: current protocol round trip"); fflush(stdout)
        let left = MockView()
        let right = MockView()
        let tree = try SplitTree<MockView>(view: left).inserting(view: right, at: left, direction: .right)
        let state = DummyTerminalRestorableState(.init(
            focusedSurface: right.id.uuidString, surfaceTree: tree,
            effectiveFullscreenMode: .nonNativeVisibleMenu, tabColor: .teal, titleOverride: "round trip"))
        let encoder = NSKeyedArchiver(requiringSecureCoding: true)
        encoder.setClassName("CodecProbeBridge", for: CodableBridge<DummyTerminalRestorableState>.self)
        state.encode(with: encoder)
        encoder.finishEncoding()
        let decoder = try NSKeyedUnarchiver(forReadingFrom: encoder.encodedData)
        decoder.setClass(CodableBridge<DummyTerminalRestorableState>.self, forClassName: "CodecProbeBridge")
        decoder.requiresSecureCoding = true
        let decoded = try require(DummyTerminalRestorableState(coder: decoder)).internalState
        decoder.finishDecoding()
        check(decoded.focusedSurface == right.id.uuidString)
        check(decoded.effectiveFullscreenMode == .nonNativeVisibleMenu)
        check(decoded.tabColor == .teal && decoded.titleOverride == "round trip")
        check(decoded.surfaceTree.map { $0.id } == tree.map { $0.id })
        for version in [0, 4] {
            let old = NSKeyedArchiver(requiringSecureCoding: true)
            old.encode(version, forKey: DummyTerminalRestorableState.versionKey)
            old.encode(CodableBridge(state), forKey: DummyTerminalRestorableState.selfKey)
            old.finishEncoding()
            let decoder = try NSKeyedUnarchiver(forReadingFrom: old.encodedData)
            decoder.requiresSecureCoding = true
            check(DummyTerminalRestorableState(coder: decoder) == nil)
            decoder.finishDecoding()
        }
        print("PASS: three upstream migration tests (four historical archives), current secure round trip and pre-v5 rejection")
    }
}
'''.replace("TERMINAL_VERSIONS", "\n".join(terminal_versions)).replace(
    "QUICK_VERSIONS", "\n".join(quick_versions)).replace("FULLSCREEN_CASES", fullscreen).replace(
    "UPSTREAM_CALLS", "\n".join(calls))

paths = [ROOT / "macos/Sources" / p for p in (
    "Helpers/CodableBridge.swift", "Features/Splits/SplitTree.swift",
    "Helpers/Extensions/Array+Extension.swift", "Helpers/Extensions/NSScreen+Extension.swift",
    "Helpers/Extensions/UUID+Extension.swift", "Helpers/Extensions/UserDefaults+Extension.swift",
    "Features/QuickTerminal/QuickTerminalScreenStateCache.swift",
)]
with tempfile.TemporaryDirectory(prefix="ghostty-restoration-codec-") as directory:
    tmp = pathlib.Path(directory)
    for name, text in (("Protocol.swift", protocol), ("Schemas.swift", terminal_schema + quick_schema),
                       ("TabColor.swift", tab_color), ("MockView.swift", "import Cocoa\nclass MockView:" + mock),
                       ("Tests.swift", tests + runner)):
        path = tmp / name
        path.write_text(text)
        paths.append(path)
    for optimization in ("-Onone", "-O"):
        for mutation in (False, True):
            # A required field in place of a v7 optional must reject the real v5 archive.
            schema = terminal_schema.replace("let titleOverride: String?", "let titleOverride: String") if mutation else terminal_schema
            assert not mutation or schema != terminal_schema
            # Keep the test compilable while intentionally making v5 decoding fail.
            (tmp / "Schemas.swift").write_text(schema + quick_schema)
            binary = tmp / "check"
            subprocess.run(["xcrun", "swiftc", "-swift-version", "5", optimization,
                            "-target", f"{platform.machine()}-apple-macosx12.0",
                            *map(str, paths), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=30)
            if mutation:
                # CodableBridge deliberately converts a decoding failure to nil;
                # the upstream require then throws Missing in the migration test.
                assert (result.returncode != 0 and "FAIL: archive decode: Missing()" in result.stderr and
                        result.stdout.rstrip().endswith("RUN: restoreTerminal57")), result.stdout + result.stderr
                print(f"{optimization}: PASS: compiled required-v7-field mutant rejects historical v5 archive", flush=True)
            else:
                assert result.returncode == 0, result.stdout + result.stderr
                print(f"{optimization}: {result.stdout.strip()}", flush=True)
