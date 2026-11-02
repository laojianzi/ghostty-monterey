#!/usr/bin/env python3
"""Run a bounded set of upstream assertions without Swift Testing macros.

The original test files stay untouched. This deliberately limited adapter fails
closed on unsupported attributes/macros and checks that every @Test is invoked.
It is NOT a replacement for the complete Xcode test suite or Swift Testing's
concurrency/trait semantics. Each invocation constructs a fresh suite instance.
"""

import argparse
import pathlib
import platform
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = [
    "macos/Sources/App/CommandLineOpenFileFilter.swift",
    "macos/Sources/Helpers/Extensions/URL+Extension.swift",
    "macos/Sources/Helpers/Extensions/Array+Extension.swift",
    "macos/Sources/Features/Splits/SplitTree.swift",
]
TESTS = [
    "CommandLineOpenFileFilterTests.swift",
    "URLTests.swift",
    "Splits/TerminalSplitDropZoneTests.swift",
    "Splits/SplitTreeTests.swift",
]


def adapt(source):
    suite = re.search(r"^struct (\w+Tests)\s*\{", source, re.MULTILINE)[1]
    # Match only the attributes used in these files, never silently skip a test.
    pattern = re.compile(r"@Test(?:\(arguments:\s*(\[.*?\])\))?\s+func (\w+)\((.*?)\)\s*(throws)?\s*\{", re.DOTALL)
    matches = list(pattern.finditer(source))
    assert len(matches) == source.count("@Test"), f"Unsupported @Test in {suite}"
    calls = []
    for match in matches:
        arguments, name, parameters, throwing = match.groups()
        prefix = "try " if throwing else ""
        if arguments:
            # The upstream tuple arrays provide their own concrete first row;
            # Swift infers all following enum members, unchanged from the tests.
            labels = re.findall(r"(\w+)\s*:\s*[^,]+", parameters)
            assert len(labels) > 1, f"Unsupported parameterization: {suite}.{name}"
            values = ", ".join(f"{label}: row.{i}" for i, label in enumerate(labels))
            calls.append(f"for row in {arguments} {{ {prefix}{suite}().{name}({values}); count += 1 }}")
        else:
            assert not parameters.strip(), f"Unexpected parameters: {suite}.{name}"
            calls.append(f"{prefix}{suite}().{name}(); count += 1")
    source = pattern.sub(lambda m: f"func {m[2]}({m[3]}) {'throws ' if m[4] else ''}{{", source)
    source = source.replace("import Testing\n", "").replace("@testable import Ghostty\n", "")
    source = source.replace("@Suite\n", "").replace("#expect(", "expect(")
    source = source.replace("Issue.record(", "recordIssue(")
    assert not re.search(r"#(?:expect|require)|@(?:Test|Suite)|Issue\.", source), suite
    return source, calls


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ablate", action="store_true", help="also verify assertions reject a broken file filter")
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix="ghostty-upstream-") as directory:
    tmp = pathlib.Path(directory)
    paths = [str(ROOT / path) for path in SOURCES]
    calls = []
    for test in TESTS:
        source, invocations = adapt((ROOT / "macos/Tests" / test).read_text())
        path = tmp / pathlib.Path(test).name
        path.write_text(source)
        paths.append(str(path))
        calls += invocations

    # The enum shares a file with the live terminal view. Compile its complete
    # production definition (including the SwiftUI overlay), not a copied formula.
    drop_source = (ROOT / "macos/Sources/Features/Splits/TerminalSplitTreeView.swift").read_text()
    drop_source = "import SwiftUI\n" + drop_source[drop_source.index("enum TerminalSplitDropZone:"):]
    drop_path = tmp / "DropZone.swift"
    drop_path.write_text(drop_source)
    paths.append(str(drop_path))

    runner = tmp / "Runner.swift"
    runner.write_text('''
import Foundation

func expect(_ condition: @autoclosure () -> Bool, _ message: String = "Expectation failed",
            file: StaticString = #file, line: UInt = #line) {
    precondition(condition(), message, file: file, line: line)
}

func recordIssue(_ message: String, file: StaticString = #file, line: UInt = #line) {
    preconditionFailure(message, file: file, line: line)
}

@main struct Runner {
    @MainActor static func main() throws {
        var count = 0
''' + "\n".join(calls) + '''
        print("PASS: \\(count) upstream test invocations (four suites, compatibility adapter)")
    }
}
''')
    paths.append(str(runner))
    for optimization in ("-Onone", "-O"):
        binary = tmp / "check"
        subprocess.run(["xcrun", "swiftc", "-swift-version", "5", optimization,
                        "-target", f"{platform.machine()}-apple-macosx12.0",
                        *paths, "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True, timeout=30)
    if args.ablate:
        source_path = ROOT / SOURCES[0]
        source = source_path.read_text()
        statement = "return filesToIgnore.remove(url) != nil"
        assert source.count(statement) == 1, "Update file-filter mutation for current production code"
        mutant = tmp / "BrokenFilter.swift"
        mutant.write_text(source.replace(statement, "return false"))
        mutant_paths = [str(mutant) if p == str(source_path) else p for p in paths]
        subprocess.run(["xcrun", "swiftc", "-swift-version", "5", "-O",
                        "-target", f"{platform.machine()}-apple-macosx12.0",
                        *mutant_paths, "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], text=True, capture_output=True, timeout=30)
        assert result.returncode != 0, "Broken filter unexpectedly passed upstream assertions"
        print("PASS: successfully compiled mutant rejected by upstream assertions")
