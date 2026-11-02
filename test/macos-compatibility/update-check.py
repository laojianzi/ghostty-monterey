#!/usr/bin/env python3
"""Compile the production update metadata policy; never contact an update feed."""

import pathlib
import argparse
import platform
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "macos/Sources/Features/Update/UpdateDelegate.swift").read_text()
policy = "import Foundation\n" + source[source.index("struct MontereyUpdateConfiguration {"):]
checks = r'''
import Foundation

@main struct Checks {
    static func main() throws {
        let key = Data(repeating: 42, count: 32).base64EncodedString()
        let feed = "https://updates.example.com/monterey/stable.xml"
        let valid: [String: Any] = [
            "SUPublicEDKey": key,
            "GhosttyMontereyUpdateFeeds": ["stable": feed,
                "tip": "https://updates.example.com/monterey/tip.xml"],
        ]
        let policy = MontereyUpdateConfiguration(info: valid)
        let stable = try policy.feedURL(channel: "stable")
        let tip = try policy.feedURL(channel: "tip")
        precondition(stable == feed)
        precondition(tip.hasSuffix("tip.xml"))
        var count = 2
        func rejects(_ info: [String: Any], channel: String = "stable") {
            do {
                _ = try MontereyUpdateConfiguration(info: info).feedURL(channel: channel)
                fatalError("Unsafe update metadata accepted: \(info)")
            } catch {
                precondition((error as NSError).domain == "GhosttyMonterey.Update")
                count += 1
            }
        }
        rejects([:])
        rejects(valid, channel: "unknown")
        rejects(["SUPublicEDKey": key])
        for badKey in ["", "$(GHOSTTY_MONTEREY_UPDATE_KEY)", "not base64",
                       Data(repeating: 0, count: 31).base64EncodedString(),
                       "wsNcGf5hirwtdXMVnYoxRIX/SqZQLMOsYlD3q3imeok="] {
            var info = valid
            info["SUPublicEDKey"] = badKey
            rejects(info)
        }
        for badFeed in ["", "$(GHOSTTY_MONTEREY_UPDATE_STABLE_URL)",
                        "http://updates.example.com/appcast.xml", "file:///tmp/feed.xml",
                        "https:///feed.xml", "https://ghostty.org/feed.xml",
                        "https://release.files.ghostty.org/appcast.xml",
                        "https://TIP.FILES.GHOSTTY.ORG/appcast.xml",
                        "https://release.files.ghostty.org./appcast.xml",
                        "https://user:password@updates.example.com/feed.xml",
                        "https://updates.example.com/feed.xml#fragment"] {
            var info = valid
            info["GhosttyMontereyUpdateFeeds"] = ["stable": badFeed]
            rejects(info)
        }
        var singleChannel = valid
        singleChannel["GhosttyMontereyUpdateFeeds"] = ["stable": feed]
        rejects(singleChannel, channel: "tip")
        print("PASS: \(count) update source/key policy checks (no network)")
    }
}
'''
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ablate", action="store_true", help="verify assertions reject the upstream signing key")
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix="ghostty-update-") as directory:
    tmp = pathlib.Path(directory)
    (tmp / "Policy.swift").write_text(policy)
    (tmp / "Checks.swift").write_text(checks)
    for optimization in ("-Onone", "-O"):
        binary = tmp / "check"
        subprocess.run(["xcrun", "swiftc", "-swift-version", "5", optimization,
                        "-target", f"{platform.machine()}-apple-macosx12.0",
                        str(tmp / "Policy.swift"), str(tmp / "Checks.swift"),
                        "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    if args.ablate:
        guard = 'key != "wsNcGf5hirwtdXMVnYoxRIX/SqZQLMOsYlD3q3imeok=",'
        assert policy.count(guard) == 1
        (tmp / "Policy.swift").write_text(policy.replace(guard, "true,"))
        subprocess.run(["xcrun", "swiftc", "-O", str(tmp / "Policy.swift"),
                        str(tmp / "Checks.swift"), "-o", str(binary)], check=True)
        result = subprocess.run([str(binary)], capture_output=True)
        assert result.returncode != 0, "Upstream-key mutant unexpectedly passed"
        print("PASS: compiled upstream-key acceptance mutant rejected")
