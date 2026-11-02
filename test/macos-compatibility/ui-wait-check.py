#!/usr/bin/env python3
"""Type-check existing UI tests and exercise their Monterey XCTest wait helpers.

Does not launch UI automation, send global events or change system appearance.
The runtime fixture replaces XCUIElement state only; XCTest predicates/waiters
are real. Theme tests and Swift Testing are separate unresolved toolchain gates.
"""

import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
developer = pathlib.Path(subprocess.check_output(["xcode-select", "-p"], text=True).strip())
platform = developer / "Platforms/MacOSX.platform/Developer"
frameworks = platform / "Library/Frameworks"
libraries = platform / "usr/lib"
flags = ["-F", str(frameworks), "-I", str(libraries)]
tests = root / "macos/GhosttyUITests"
sources = [tests / name for name in (
    "GhosttyCustomConfigCase.swift", "GhosttyCommandPaletteTests.swift", "GhosttyMouseStateTests.swift",
    "GhosttyTitlebarTabsUITests.swift", "GhosttyWindowPositionUITests.swift", "GhosttyTitleUITests.swift")]
for arch in ("x86_64", "arm64"):
    subprocess.run(["xcrun", "swiftc", "-typecheck", "-target", f"{arch}-apple-macos12.0",
                    *flags, *map(str, sources)], check=True)
    print(f"PASS: {arch} UI wait/mouse/palette/tab/title/window source type-check", flush=True)
text = sources[0].read_text()
helpers = text.split("extension XCUIElement {", 1)[1].split("\nclass GhosttyCustomConfigCase:", 1)[0]
harness = '''import Foundation
import XCTest
final class Element: NSObject {
    var exists = true
    var count = 0
}
extension Element {''' + helpers.replace("KeyPath<XCUIElement, Value>", "KeyPath<Element, Value>") + r'''
func check(_ result: Bool, _ message: String) {
    if !result {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}
let element = Element()
check(!element.waitUntilAbsent(timeout: 0.05), "present element must time out")
element.exists = false
check(element.waitUntilAbsent(timeout: 0.05), "already absent element")
check(!element.waitUntil(\.count, equals: 3, timeout: 0.05), "wrong value must time out")
element.count = 3
check(element.waitUntil(\.count, equals: 3, timeout: 0.05), "already equal value")
element.exists = true
DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { element.exists = false }
check(element.waitUntilAbsent(timeout: 2), "delayed disappearance")
element.count = 0
DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { element.count = 3 }
check(element.waitUntil(\.count, equals: 3, timeout: 2), "delayed value equality")
print("PASS: real XCTest waits accept transitions and reject unsatisfied deadlines")
'''
with tempfile.TemporaryDirectory(prefix="ghostty-ui-wait-") as directory:
    work = pathlib.Path(directory)
    swift = work / "main.swift"
    binary = work / "check"
    for optimization in ("-Onone", "-O"):
        for label, source in (("production", harness), ("always-pass", harness.replace("== .completed", "!= .interrupted"))):
            swift.write_text(source)
            subprocess.run(["xcrun", "swiftc", optimization, *flags, str(swift),
                            "-Xlinker", "-rpath", "-Xlinker", str(frameworks),
                            "-L", str(libraries), "-Xlinker", "-rpath", "-Xlinker", str(libraries),
                            "-o", str(binary)], check=True)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=15)
            if label == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(result.stdout.strip(), flush=True)
            else:
                assert result.returncode != 0 and "present element must time out" in result.stderr, result
                print(f"PASS: {optimization} false-success mutant rejected", flush=True)
