import Foundation

#if compiler(>=6.0)
extension FileHandle: @retroactive TextOutputStream {}
#else
extension FileHandle: TextOutputStream {}
#endif

extension FileHandle {
    /// Write a string to a filehandle.
    public func write(_ string: String) {
        let data = Data(string.utf8)
        self.write(data)
    }
}
