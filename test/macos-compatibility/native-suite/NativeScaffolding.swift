import AppKit
import XCTest
import Testing
import GhosttyKit
#if GHOSTTY_XCODE_HOSTED_TEST
@testable import Ghostty
#endif

final class NativeTests: XCTestCase {
    @MainActor func testAll() async {
        _ = NSApplication.shared
#if GHOSTTY_XCODE_HOSTED_TEST
        // The real app main already initialized libghostty before XCTest loads.
        guard let delegate = NSApp.delegate as? AppDelegate, delegate.ghostty.app != nil else {
            XCTFail("Expected initialized real Ghostty app host")
            return
        }
#else
        // Do not parse xctest's bundle path as a Ghostty configuration argument.
        guard ghostty_init(1, CommandLine.unsafeArgv) == 0 else {
            XCTFail("ghostty_init failed")
            return
        }
#endif
        await XCTestScaffold.runAllTests(hostedBy: self)
    }
}
