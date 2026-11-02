import Foundation

extension Ghostty {
    /// Possible errors from internal Ghostty calls.
    enum Error: Swift.Error, LocalizedError {
        case apiFailed

        var errorDescription: String? {
            switch self {
            case .apiFailed: return "libghostty API call failed"
            }
        }
    }
}
