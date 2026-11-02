import Foundation
import SwiftUI

@main
struct ValueChecks {
    static func equal<T: Equatable>(_ lhs: T, _ rhs: T) -> Bool { lhs == rhs }

    static func main() throws {
        // Exercise protocol witnesses as well as direct extension calls.
        precondition(equal(KeyEquivalent.return, .return))
        precondition(!equal(KeyEquivalent.return, .escape))
        let shortcut = KeyboardShortcut("x", modifiers: [.command, .shift])
        let description: CustomStringConvertible = shortcut
        precondition(description.description == shortcut.keyList.joined())
        let pipe = Pipe()
        var writer = pipe.fileHandleForWriting
        print("conformance", to: &writer)
        try writer.close()
        precondition(pipe.fileHandleForReading.readDataToEndOfFile() == Data("conformance\n".utf8))
        try pipe.fileHandleForReading.close()

        precondition(GhosttyDuration.milliseconds(1000) == .seconds(1))
        precondition(GhosttyDuration.milliseconds(UInt8.max) == .milliseconds(255))
        precondition(GhosttyDuration.nanoseconds(Int8.min) == .nanoseconds(-128))
        precondition(GhosttyDuration.nanoseconds(-1).sleepNanoseconds == 0)
        precondition(GhosttyDuration.milliseconds(UInt64.max).sleepNanoseconds == UInt64.max)
        precondition(GhosttyDuration.nanoseconds(UInt64.max).sleepNanoseconds == UInt64.max)
        precondition(GhosttyDuration.milliseconds(123).sleepNanoseconds == 123_000_000)
        let instant = GhosttyInstant.now
        Thread.sleep(forTimeInterval: 0.002)
        precondition(instant < .now)
        precondition(instant.duration(to: .now) >= .milliseconds(2))
        precondition(GhosttyDuration.nanoseconds(-1) < .seconds(0))
        precondition(GhosttyDuration.milliseconds(-1001) == .nanoseconds(-1_001_000_000))
        precondition(GhosttyDuration.milliseconds(UInt64.max) > .nanoseconds(UInt64.max))
        precondition(GhosttyDuration.nanoseconds(UInt64.max) > .seconds(18_446_744_073))
        precondition(GhosttyDuration.seconds(3_153_600_000).timeInterval == 3_153_600_000)
        precondition(abs(GhosttyDuration.milliseconds(-1).timeInterval + 0.001) < 1e-12)
        precondition(GhosttyDuration.seconds(Int64.min) < .milliseconds(Int64.min))
        precondition(GhosttyDuration.seconds(Int64.max) > .milliseconds(Int64.max))
        for value in -1000...1000 {
            precondition(GhosttyDuration.milliseconds(value) == .nanoseconds(value * 1_000_000))
            precondition(GhosttyDuration.nanoseconds(value) < .nanoseconds(value + 1))
        }
        for duration in [GhosttyDuration.seconds(0), .milliseconds(251), .milliseconds(3_661_251)] {
            precondition(!duration.abbreviatedDescription.isEmpty)
        }

        let uuid = UUID(uuidString: "00112233-4455-6677-8899-AABBCCDDEEFF")!
        let data = uuid.surfaceTransferData
        precondition(Array(data) == Array(stride(from: 0, through: 255, by: 17)).map(UInt8.init))
        precondition(UUID(surfaceTransferData: data) == uuid)
        for count in [0, 1, 15, 17, 64] {
            precondition(UUID(surfaceTransferData: Data(repeating: 0, count: count)) == nil)
        }
        let padded = Data([255]) + data
        precondition(UUID(surfaceTransferData: padded.dropFirst()) == uuid)
        for _ in 0..<1000 {
            let value = UUID()
            precondition(UUID(surfaceTransferData: value.surfaceTransferData) == value)
        }
        print("Duration range/precision, UUID transfer and shared protocol witness checks passed")
    }
}
