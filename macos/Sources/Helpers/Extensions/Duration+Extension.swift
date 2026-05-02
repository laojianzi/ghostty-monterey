import Foundation

struct Duration: Equatable, Comparable, Sendable {
    private let rawNanoseconds: Int64

    var timeInterval: TimeInterval {
        return TimeInterval(rawNanoseconds) / 1_000_000_000
    }

    var sleepNanoseconds: UInt64 {
        return UInt64(max(rawNanoseconds, 0))
    }

    var abbreviatedDescription: String {
        let milliseconds = max(rawNanoseconds / 1_000_000, 0)
        let hours = milliseconds / 3_600_000
        let minutes = (milliseconds % 3_600_000) / 60_000
        let seconds = (milliseconds % 60_000) / 1_000
        let remainingMilliseconds = milliseconds % 1_000

        if hours > 0 {
            return "\(hours)h \(minutes)m \(seconds)s"
        }
        if minutes > 0 {
            return "\(minutes)m \(seconds)s"
        }
        if seconds > 0 {
            return "\(seconds)s"
        }
        return "\(remainingMilliseconds)ms"
    }

    static func seconds<T: BinaryInteger>(_ value: T) -> Self {
        return .init(rawNanoseconds: Int64(value) * 1_000_000_000)
    }

    static func milliseconds<T: BinaryInteger>(_ value: T) -> Self {
        return .init(rawNanoseconds: Int64(value) * 1_000_000)
    }

    static func nanoseconds<T: BinaryInteger>(_ value: T) -> Self {
        return .init(rawNanoseconds: Int64(value))
    }

    static func < (lhs: Self, rhs: Self) -> Bool {
        return lhs.rawNanoseconds < rhs.rawNanoseconds
    }
}
