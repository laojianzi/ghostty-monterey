import Foundation
import System

extension URL {
    /// The decoded path with trailing separators removed, except for the root path.
    var pathWithoutTrailingSlash: String {
        if #available(macOS 13, *) {
            return FilePath(path(percentEncoded: false)).string
        } else {
            return FilePath(path).string
        }
    }
}
