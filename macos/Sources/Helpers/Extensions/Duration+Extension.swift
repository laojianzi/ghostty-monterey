import Foundation

@available(macOS 13, *)
extension Duration {
    var timeInterval: TimeInterval {
        return TimeInterval(self.components.seconds) +
               TimeInterval(self.components.attoseconds) / 1_000_000_000_000_000_000
    }
}

/// Durations crossing the app's configuration/C ABI boundary are integral
/// milliseconds or nanoseconds. Store them without narrowing UInt64 to Int64
/// nanoseconds (which would overflow for valid long configuration intervals).
struct GhosttyDuration: Equatable, Comparable, Sendable {
    private let seconds: Int64
    private let nanoseconds: Int32

    private init<T: BinaryInteger>(_ value: T, unitsPerSecond: UInt64, nanosPerUnit: Int64) {
        let magnitude = UInt64(value.magnitude)
        let whole = magnitude / unitsPerSecond
        let negative = value < 0
        let quotient = negative && whole > 0 ? -Int64(whole - 1) - 1 : Int64(whole)
        let fraction = Int64(magnitude % unitsPerSecond) * nanosPerUnit
        let remainder = negative ? -fraction : fraction
        // Canonical floor representation makes comparisons exact, including
        // negative subsecond values, without floating point conversions.
        seconds = remainder < 0 ? quotient - 1 : quotient
        nanoseconds = Int32(remainder < 0 ? remainder + 1_000_000_000 : remainder)
    }

    static func seconds<T: BinaryInteger>(_ value: T) -> Self {
        Self(value, unitsPerSecond: 1, nanosPerUnit: 1_000_000_000)
    }

    static func milliseconds<T: BinaryInteger>(_ value: T) -> Self {
        Self(value, unitsPerSecond: 1_000, nanosPerUnit: 1_000_000)
    }

    static func nanoseconds<T: BinaryInteger>(_ value: T) -> Self {
        Self(value, unitsPerSecond: 1_000_000_000, nanosPerUnit: 1)
    }

    var timeInterval: TimeInterval {
        TimeInterval(seconds) + TimeInterval(nanoseconds) / 1_000_000_000
    }

    /// Task's older nanosecond sleep API cannot represent arbitrarily large
    /// configuration intervals. Saturate only at that API boundary.
    var sleepNanoseconds: UInt64 {
        guard seconds >= 0 else { return 0 }
        let (whole, overflow) = UInt64(seconds).multipliedReportingOverflow(by: 1_000_000_000)
        let (total, additionOverflow) = whole.addingReportingOverflow(UInt64(nanoseconds))
        return overflow || additionOverflow ? UInt64.max : total
    }

    static func < (lhs: Self, rhs: Self) -> Bool {
        lhs.seconds == rhs.seconds ? lhs.nanoseconds < rhs.nanoseconds : lhs.seconds < rhs.seconds
    }

    /// Match the upstream localized formatter when the OS provides it. On
    /// Monterey, use Foundation's localized unit formatter, including ms.
    var abbreviatedDescription: String {
        if #available(macOS 13, *) {
            return (Duration.seconds(seconds) + .nanoseconds(Int64(nanoseconds))).formatted(
                .units(allowed: [.hours, .minutes, .seconds, .milliseconds],
                       width: .abbreviated, fractionalPart: .hide)
            )
        }

        let formatter = MeasurementFormatter()
        formatter.unitStyle = .short
        formatter.unitOptions = .providedUnit
        formatter.numberFormatter.maximumFractionDigits = 0
        let units: [(Int64, UnitDuration)] = [
            (seconds / 3600, .hours),
            ((seconds % 3600) / 60, .minutes),
            (seconds % 60, .seconds),
            (Int64(nanoseconds) / 1_000_000, .milliseconds),
        ]
        let parts = units.filter { $0.0 != 0 }.map {
            formatter.string(from: Measurement<UnitDuration>(value: Double($0.0), unit: $0.1))
        }
        return parts.isEmpty
            ? formatter.string(from: Measurement<UnitDuration>(value: 0, unit: .milliseconds))
            : parts.joined(separator: " ")
    }
}

/// Darwin's continuous clock advances through sleep and ignores wall-clock
/// adjustments, matching the focus/cache semantics of Swift ContinuousClock.
struct GhosttyInstant: Equatable, Comparable, Sendable {
    private let nanoseconds: UInt64

    static var now: Self {
        Self(nanoseconds: clock_gettime_nsec_np(CLOCK_MONOTONIC_RAW))
    }

    func duration(to other: Self) -> GhosttyDuration {
        if other.nanoseconds >= nanoseconds {
            return .nanoseconds(other.nanoseconds - nanoseconds)
        }
        // Instants come from the same monotonically increasing boot clock.
        return .nanoseconds(-Int64(nanoseconds - other.nanoseconds))
    }

    static func < (lhs: Self, rhs: Self) -> Bool {
        lhs.nanoseconds < rhs.nanoseconds
    }
}
