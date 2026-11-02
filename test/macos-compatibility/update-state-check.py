#!/usr/bin/env python3
"""Run bounded upstream update suites against production state and real Sparkle.

No updater is constructed and no network, user preferences or installation is
used. Swift Testing attributes/assertions are adapted, not the test bodies.
"""

import argparse
import pathlib
import platform
import plistlib
import re
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=pathlib.Path)
args = parser.parse_args()
frameworks = args.app.resolve() / "Contents/Frameworks"
assert (frameworks / "Sparkle.framework/Sparkle").is_file()
headers = args.app.resolve().parent
assert (headers / "Sparkle.framework/Modules/module.modulemap").is_file(), "Build-directory Sparkle headers required"
for base in (headers, frameworks):
    with (base / "Sparkle.framework/Resources/Info.plist").open("rb") as stream:
        assert plistlib.load(stream)["CFBundleShortVersionString"] == "2.9.6"
production = (root / "macos/Sources/Features/Update/UpdateViewModel.swift").read_text()
tests = []
calls = []
for name in ("UpdateStateTests", "UpdateViewModelTests", "ReleaseNotesTests"):
    source = (root / f"macos/Tests/Update/{name}.swift").read_text()
    pattern = re.compile(r"@Test(?:\(\s*arguments:\s*(\[.*?\])\s*\))?\s+func (\w+)\((.*?)\)(\s+async)?(\s+throws)?\s*\{", re.DOTALL)
    matches = list(pattern.finditer(source))
    assert len(matches) == source.count("@Test"), f"Unsupported test attribute in {name}"
    for match in matches:
        arguments, method, parameters, asynchronous, throwing = match.groups()
        prefix = ("try " if throwing else "") + ("await " if asynchronous else "")
        if arguments:
            assert parameters == "_ state: UpdateState, expected: Bool", parameters
            calls.append(f"for row in {arguments} {{ {prefix}{name}().{method}(row.0, expected: row.1); count += 1 }}")
        else:
            assert not parameters, parameters
            calls.append(f"{prefix}{name}().{method}(); count += 1")
    source = pattern.sub(lambda m: f"func {m[2]}({m[3]}){m[4] or ''}{m[5] or ''} {{", source)
    source = source.replace("import Testing", "").replace("@testable import Ghostty", "")
    source = source.replace("#expect(", "check(").replace("Issue.record(", "recordIssue(")
    assert not re.search(r"#(?:expect|require)|@(?:Suite|Test)|Issue\.", source), name
    tests.append(source)

harness = r'''
import Foundation
import Sparkle

func check(_ condition: @autoclosure () -> Bool, _ message: String = "Upstream expectation failed",
           file: StaticString = #file, line: UInt = #line) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message) (\(file):\(line))\n".utf8))
        exit(1)
    }
}
func recordIssue(_ message: String) { check(false, message) }

// Lock-protected recorder can safely be captured by the production Sendable
// callback types without weakening their concurrency contract for this test.
final class Replies: @unchecked Sendable {
    private let lock = NSLock()
    private var storage: [String] = []
    func append(_ value: String) {
        lock.lock()
        defer { lock.unlock() }
        storage.append(value)
    }
    var values: [String] {
        lock.lock()
        defer { lock.unlock() }
        return storage
    }
}

@main struct Runner {
    @MainActor static func main() async throws {
        let expectedFramework = URL(fileURLWithPath: CommandLine.arguments[1]).resolvingSymlinksInPath()
        check(Bundle(for: SUAppcastItem.self).bundleURL.resolvingSymlinksInPath() == expectedFramework,
              "Loaded Sparkle outside the supplied app")
        var count = 0
        CALLS
        print("PASS: \(count) upstream update test invocations across three suites")
        let replies = Replies()
        let item = SUAppcastItem.empty()
        let cancellable: [(UpdateState, String)] = [
            (.checking(.init(cancel: { replies.append("checking") })), "checking"),
            (.downloading(.init(cancel: { replies.append("download") }, expectedLength: nil, progress: 0)), "download"),
            (.notFound(.init(acknowledgement: { replies.append("ack") })), "ack"),
            (.error(.init(error: NSError(domain: "fixture", code: 1),
                          retry: { replies.append("unexpected-retry") }, dismiss: { replies.append("dismiss") })), "dismiss"),
            (.updateAvailable(.init(appcastItem: item, reply: { choice in
                replies.append(choice == .dismiss ? "dismiss-update" : "unexpected-install")
            })), "dismiss-update"),
        ]
        for (state, expected) in cancellable {
            let before = replies.values.count
            check(state.isCancellable, "Cancellable state not advertised")
            state.cancel()
            check(replies.values.count == before + 1 && replies.values.last == expected,
                  "Cancel callback routing")
        }
        let before = replies.values
        let inert: [UpdateState] = [
            .idle,
            .permissionRequest(.init(request: SPUUpdatePermissionRequest(systemProfile: []),
                                     reply: { _ in replies.append("unexpected-permission") })),
            .extracting(.init(progress: 0.5)),
            .installing(.init(appcastItem: item, retryTerminatingApplication: { replies.append("unexpected-retry") })),
        ]
        for state in inert {
            check(!state.isCancellable, "Inert state advertises cancellation")
            state.cancel()
        }
        check(replies.values == before, "Inert cancellation invoked callback")
        var available = UpdateState.updateAvailable(.init(appcastItem: item, reply: { choice in
            replies.append(choice == .install ? "install" : "unexpected-dismiss")
        }))
        available.confirm()
        check(replies.values.last == "install", "Confirm did not request install")
        var installing = UpdateState.installing(.init(appcastItem: item,
                                                       retryTerminatingApplication: { replies.append("restart") }))
        check(!installing.shouldTerminateWithoutWarning && installing.isHidden, "Auto-install initial state")
        installing.confirm()
        check(installing.shouldTerminateWithoutWarning && !installing.isHidden,
              "Confirmed installation did not suppress termination warnings")
        check(replies.values.last == "restart", "Confirm did not retry termination")
        var idle = UpdateState.idle
        let finalReplies = replies.values
        idle.confirm()
        check(replies.values == finalReplies && idle == .idle, "Idle confirmation changed state")
        print("PASS: native Sparkle objects, cancellation/confirmation routing and termination policy")
    }
}
'''.replace("CALLS", "\n".join(calls))

with tempfile.TemporaryDirectory(prefix="ghostty-update-state-") as directory:
    tmp = pathlib.Path(directory)
    runner = tmp / "Runner.swift"
    runner.write_text("\n".join(tests) + "\n" + harness)
    cancel = "return { available.reply(.dismiss) }"
    confirm = "suppressTerminationWarnings.appcastItem = nil"
    assert production.count(cancel) == production.count(confirm) == 1
    for optimization in ("-Onone", "-O"):
        for name, body, diagnostic in (
            ("production", production, None),
            ("cancel-installs", production.replace(cancel, "return { available.reply(.install) }"),
             "Cancel callback routing"),
            ("confirm-retains-item", production.replace(confirm, "// retain appcastItem"),
             "Confirmed installation did not suppress termination warnings"),
        ):
            implementation = tmp / "UpdateViewModel.swift"
            implementation.write_text(body)
            binary = tmp / name
            subprocess.run(["xcrun", "swiftc", optimization, "-target", f"{platform.machine()}-apple-macosx12.0",
                            "-F", str(headers), "-framework", "Sparkle", "-Xlinker", "-rpath",
                            "-Xlinker", str(frameworks), str(implementation), str(runner), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary), str(frameworks / "Sparkle.framework")],
                                    text=True, capture_output=True, timeout=20)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimization + ": " + result.stdout.strip())
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, result.stdout + result.stderr
                print(optimization + f": PASS: compiled {name} mutant rejected")
