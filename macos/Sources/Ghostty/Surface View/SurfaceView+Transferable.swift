#if canImport(AppKit)
import AppKit
#endif
import UniformTypeIdentifiers

extension Ghostty.SurfaceView {
    #if canImport(AppKit)
    func pasteboardItem() -> NSPasteboardItem? {
        let item = NSPasteboardItem()
        let data = withUnsafeBytes(of: id.uuid) { Data($0) }
        guard item.setData(data, forType: .ghosttySurfaceId) else { return nil }
        return item
    }
    #endif

    static func surfaceID(from data: Data) -> UUID? {
        guard data.count == 16 else { return nil }
        return data.withUnsafeBytes {
            $0.load(as: UUID.self)
        }
    }

    @MainActor
    static func find(uuid: UUID) -> Self? {
        #if canImport(AppKit)
        guard let del = NSApp.delegate as? GhosttyDelegate else { return nil }
        return del.ghosttySurface(id: uuid) as? Self
        #elseif canImport(UIKit)
        // We should be able to use UIApplication here.
        return nil
        #else
        return nil
        #endif
    }
}

extension UTType {
    /// A format that encodes the bare UUID only for the surface. This can be used if you have
    /// a way to look up a surface by ID.
    static let ghosttySurfaceId = UTType(exportedAs: "com.mitchellh.ghosttySurfaceId")
}

#if canImport(AppKit)
extension NSPasteboard.PasteboardType {
    /// Pasteboard type for dragging surface IDs.
    static let ghosttySurfaceId = NSPasteboard.PasteboardType(UTType.ghosttySurfaceId.identifier)
}
#endif
