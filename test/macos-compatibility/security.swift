import Foundation

// Compile real production helpers without linking or launching the app.
enum Ghostty {}

@main
struct SecurityChecks {
    static var checks = 0

    static func check(_ condition: @autoclosure () -> Bool, _ message: String) {
        checks += 1
        precondition(condition(), message)
    }

    static func main() throws {
        for value in ["http://example.com", "https://example.com/path", "mailto:user@example.com"] {
            check(UntrustedURL(value).decision == .allow(URL(string: value)!), "safe scheme: \(value)")
        }
        for value in ["https:relative", "http:///missing-host"] {
            check(UntrustedURL(value).decision == .deny(.invalidWebURL), "missing host: \(value)")
        }
        for value in ["/tmp/file.txt", "../file.txt", "payload.command"] {
            check(UntrustedURL(value).decision == .deny(.malformedURL), "scheme required")
        }
        for value in ["vscode://file/tmp/example.swift", "ssh://example.com"] {
            check(UntrustedURL(value).decision == .confirm(URL(string: value)!), "custom scheme confirmation")
        }
        for value in ["\u{0085}", "\u{2028}", "\u{2029}", "\u{202E}", "\u{2066}", "\u{200B}"] {
            check(UntrustedURL("https://example.com/a\(value)b").decision == .deny(.unsafeCharacters), "unsafe scalar")
        }
        for value in ["\u{0085}", "\u{2028}", "\u{2029}"] {
            check(UntrustedURL("/tmp/preview\(value)////../payload.command////").displayString == "/tmp/payload.command",
                  "preview path normalization")
        }
        check(UntrustedURL("https://example.com/a\u{202E}b").displayString == "https://example.com/a\\u{202E}b",
              "escape bidi in preview")

        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: directory) }
        let safe = directory.appendingPathComponent("document.txt")
        try "safe".write(to: safe, atomically: true, encoding: .utf8)
        check(UntrustedURL(safe.absoluteString).decision == .allow(safe.standardizedFileURL.resolvingSymlinksInPath()),
              "allow regular document")
        for name in ["payload.command", "payload.tool", "payload.app", "payload.workflow", "payload.sh"] {
            let file = directory.appendingPathComponent(name)
            try "#!/bin/sh\n".write(to: file, atomically: true, encoding: .utf8)
            check(UntrustedURL(file.absoluteString).decision == .deny(.unsafeFile), "deny executable type: \(name)")
        }
        try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: safe.path)
        check(UntrustedURL(safe.absoluteString).decision == .deny(.unsafeFile), "deny executable bit")
        let link = directory.appendingPathComponent("link.txt")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: safe)
        check(UntrustedURL(link.absoluteString).decision == .deny(.unsafeFile), "resolve symlink before checking")
        check(UntrustedURL(directory.appendingPathComponent("missing").absoluteString).decision == .deny(.inaccessibleFile),
              "deny missing file")
        for value in ["file://remote.invalid/tmp/file", safe.absoluteString + "?x", safe.absoluteString + "#x"] {
            check(UntrustedURL(value).decision == .deny(.malformedURL), "deny ambiguous file URL")
        }
        for (value, expected) in [
            ("file:///tmp/example/", "/tmp/example"),
            ("file:///tmp/example///", "/tmp/example"),
            ("file:///tmp/example%20directory/", "/tmp/example directory"),
            ("file:///", "/")
        ] {
            check(URL(string: value)!.pathWithoutTrailingSlash == expected, "decoded path without trailing slash")
        }

        // Ask the actual shell to decode one quoted argument. No payload is ever
        // evaluated as shell syntax: the production quote function must contain it.
        let arguments = ["", "filename", "abcABC123@%_-+=:,./", "file name", "it's", "file$'name'",
                         "$(printf unsafe)", "a;b", "a\nb", "a\\b", "\u{00E9}", "\u{1F600}"]
        for argument in arguments {
            let process = Process()
            let pipe = Pipe()
            let input = Pipe()
            process.executableURL = URL(fileURLWithPath: "/bin/sh")
            // Foundation on Monterey normalizes Unicode Process arguments.
            // Supply the script as bytes so the test measures quoting, not argv.
            process.standardInput = input
            process.standardOutput = pipe
            try process.run()
            input.fileHandleForWriting.write(Data(("printf '%s' " + Ghostty.Shell.quote(argument)).utf8))
            try input.fileHandleForWriting.close()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            process.waitUntilExit()
            check(process.terminationStatus == 0 && data == Data(argument.utf8),
                  "shell argument round trip: \(argument.debugDescription), got \(Array(data))")
        }
        for scalar in (0...31).map(UInt32.init) + Array(127...159).map(UInt32.init) {
            let value = "a" + String(UnicodeScalar(scalar)!) + "b"
            check(Ghostty.Shell.containsControlCharacters(value), "reject terminal control")
        }
        check(!Ghostty.Shell.containsControlCharacters("/tmp/\u{00E9}/\u{1F468}\u{200D}\u{1F469}"), "allow Unicode paths")
        check(Ghostty.Shell.escape("a b\\c") == "a\\ b\\\\c", "live-buffer path escaping")
        print("Security helpers: \(checks) checks passed")
    }
}
