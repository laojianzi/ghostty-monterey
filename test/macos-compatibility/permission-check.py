#!/usr/bin/env python3
"""Exercise production permission sheets/cache using an isolated defaults suite.

Ends only alerts owned by this native fixture. No system permissions, clipboard,
network or user preferences are read or changed. Not physical-click UI evidence.
"""

import os
import pathlib
import platform
import subprocess
import tempfile
import uuid

root = pathlib.Path(__file__).resolve().parents[2]
permission = (root / "macos/Sources/Helpers/PermissionRequest.swift").read_text()
harness = r'''
import AppKit

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}
func waitFor(_ condition: () -> Bool) {
    let end = Date(timeIntervalSinceNow: 3)
    while !condition() && Date() < end {
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.01))
    }
    check(condition(), "Permission callback timed out")
}
func buttons(_ view: NSView) -> [NSButton] {
    (view as? NSButton).map { [$0] } ?? view.subviews.flatMap { buttons($0) }
}

@main struct Runner {
    @MainActor static func main() {
        _ = NSApplication.shared
        let suite = ProcessInfo.processInfo.environment["GHOSTTY_USER_DEFAULTS_SUITE"]!
        check(suite.hasPrefix("ghostty-permission-test-"), "Unsafe defaults suite")
        let defaults = UserDefaults.ghostty
        defaults.removePersistentDomain(forName: suite)
        defer { defaults.removePersistentDomain(forName: suite) }
        let window = NSWindow(contentRect: NSRect(x: 100, y: 100, width: 500, height: 300),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.orderFront(nil)
        defer { window.close() }

        func prompt(_ key: String, response: NSApplication.ModalResponse, remember: Bool = false,
                    allow: PermissionRequest.AllowDuration = .once,
                    duration: GhosttyDuration? = .seconds(86400), label: String? = "Remember my decision for one day") {
            var results: [Bool] = []
            PermissionRequest.show(key, message: "Fixture permission", informative: "Test only",
                                   allowDuration: allow, rememberDuration: duration, window: window) {
                check(Thread.isMainThread, "Permission completion off main thread")
                results.append($0)
            }
            check(results.isEmpty, "Fresh or expired request unexpectedly used cache")
            waitFor { window.attachedSheet != nil }
            check(results.isEmpty, "Fresh request completed before sheet response")
            let sheet = window.attachedSheet!
            let controls = buttons(sheet.contentView!)
            check(controls.contains { $0.title == "Allow" } && controls.contains { $0.title == "Don't Allow" },
                  "Missing permission controls")
            let checkbox = controls.first { $0.title.hasPrefix("Remember my decision") }
            if let label {
                check(checkbox?.title == label && checkbox?.state == .off, "Remember label/default state")
            } else {
                check(checkbox == nil, "Unexpected remember control")
            }
            if remember { checkbox!.state = .on }
            window.endSheet(sheet, returnCode: response)
            waitFor { results.count == 1 && window.attachedSheet == nil }
            check(results == [response == .alertFirstButtonReturn], "Permission response mapping")
        }
        func cached(_ key: String, expected: Bool) {
            var results: [Bool] = []
            PermissionRequest.show(key, message: "Must not display", window: window) { results.append($0) }
            check(results == [expected] && window.attachedSheet == nil, "Cached decision not reused")
        }

        prompt("once", response: .alertFirstButtonReturn)
        check(defaults.data(forKey: "once") == nil, "One-time allow persisted")
        prompt("once", response: .alertSecondButtonReturn)
        check(defaults.data(forKey: "once") == nil, "One-time denial persisted")
        prompt("cancel", response: .abort, allow: .forever, duration: nil, label: nil)
        check(defaults.data(forKey: "cancel") == nil, "Dismissal cached an allow")

        prompt("deny", response: .alertSecondButtonReturn, remember: true, allow: .forever)
        cached("deny", expected: false)
        prompt("allow", response: .alertFirstButtonReturn, remember: true)
        cached("allow", expected: true)
        prompt("automatic", response: .alertFirstButtonReturn, allow: .duration(.seconds(60)),
               duration: nil, label: nil)
        cached("automatic", expected: true)
        prompt("forever", response: .alertFirstButtonReturn, allow: .forever, duration: nil, label: nil)
        cached("forever", expected: true)
        prompt("no-auto-deny", response: .alertSecondButtonReturn, allow: .duration(.seconds(60)))
        check(defaults.data(forKey: "no-auto-deny") == nil, "Allow policy cached unremembered denial")

        // Negative TTL makes expiry deterministic without long sleep or clock changes.
        prompt("expired", response: .alertFirstButtonReturn, allow: .duration(.seconds(-1)), duration: nil, label: nil)
        check(defaults.data(forKey: "expired") != nil, "Expiry fixture was not stored")
        prompt("expired", response: .alertSecondButtonReturn, duration: nil, label: nil)
        check(defaults.data(forKey: "expired") == nil, "Expired permission not removed")
        // Remember duration overrides even a forever automatic allow.
        prompt("override", response: .alertFirstButtonReturn, remember: true, allow: .forever,
               duration: .seconds(-86400), label: "Remember my decision for -1 days")
        prompt("override", response: .alertSecondButtonReturn)
        check(defaults.data(forKey: "override") == nil, "Remember TTL did not override forever")

        for (seconds, label) in [(1, "1 seconds"), (60, "1 minute"), (120, "2 minutes"),
                                 (3600, "1 hour"), (7200, "2 hours"), (172800, "2 days")] {
            prompt("label-\(seconds)", response: .alertSecondButtonReturn,
                   duration: .seconds(seconds), label: "Remember my decision for \(label)")
        }
        check(defaults.data(forKey: "deny") != nil && defaults.data(forKey: "allow") != nil,
              "Unrelated permission keys changed")
        print("PASS: native permission sheets, response mapping, checkbox labels, one-time/remembered/automatic allow/deny, TTL expiry and key isolation")
    }
}
'''

with tempfile.TemporaryDirectory(prefix="ghostty-permission-") as directory:
    tmp = pathlib.Path(directory)
    runner = tmp / "Runner.swift"
    runner.write_text(harness)
    for optimize in ("-Onone", "-O"):
        for name, source, diagnostic in (
            ("production", permission, None),
            ("denial-allows", permission.replace("case .alertSecondButtonReturn: // Don't Allow\n            result = false",
                                                "case .alertSecondButtonReturn: // Don't Allow\n            result = true"),
             "Permission response mapping"),
            ("never-expires", permission.replace("if Date() > storedPermission.expiry {", "if false {"),
             "Fresh or expired request unexpectedly used cache"),
        ):
            assert name == "production" or source != permission
            implementation = tmp / "PermissionRequest.swift"
            implementation.write_text(source)
            binary = tmp / name
            subprocess.run(["xcrun", "swiftc", optimize, "-D", "DEBUG", "-target", f"{platform.machine()}-apple-macosx12.0",
                            str(root / "macos/Sources/Helpers/Extensions/Duration+Extension.swift"),
                            str(root / "macos/Sources/Helpers/Extensions/UserDefaults+Extension.swift"),
                            str(implementation), str(runner), "-o", str(binary)], check=True)
            env = dict(os.environ, GHOSTTY_USER_DEFAULTS_SUITE="ghostty-permission-test-" + uuid.uuid4().hex)
            try:
                result = subprocess.run([str(binary)], text=True, capture_output=True, env=env, timeout=45)
            finally:
                # Remove even a mutant's persisted fixture, without touching any other domain.
                subprocess.run(["defaults", "delete", env["GHOSTTY_USER_DEFAULTS_SUITE"]],
                               capture_output=True, timeout=5)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(optimize + ": " + result.stdout.strip())
            else:
                assert result.returncode != 0 and diagnostic in result.stderr, result.stdout + result.stderr
                print(optimize + f": PASS: compiled {name} mutant rejected")
