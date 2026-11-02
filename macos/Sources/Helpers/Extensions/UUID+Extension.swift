import Foundation

extension UUID {
    /// The surface drag format is exactly the UUID's 16 bytes, not a string.
    var surfaceTransferData: Data {
        withUnsafeBytes(of: uuid) { Data($0) }
    }

    init?(surfaceTransferData data: Data) {
        guard data.count == 16 else { return nil }
        // Item provider data need not be aligned for a UUID load.
        var bytes: uuid_t = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        _ = withUnsafeMutableBytes(of: &bytes) { data.copyBytes(to: $0) }
        self.init(uuid: bytes)
    }

    /// Initialize a UUID from a CFUUID.
    init?(_ cfuuid: CFUUID) {
        guard let uuidString = CFUUIDCreateString(nil, cfuuid) as String? else { return nil }
        self.init(uuidString: uuidString)
    }
}
