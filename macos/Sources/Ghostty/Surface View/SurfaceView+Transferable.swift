import AppKit
import CoreTransferable
import UniformTypeIdentifiers

/// Conformance to `Transferable` enables drag-and-drop.
@available(macOS 13, *)
extension Ghostty.SurfaceView: Transferable {
    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(contentType: .ghosttySurfaceId) { surface in
            surface.id.surfaceTransferData
        } importing: { data in
            guard let uuid = UUID(surfaceTransferData: data) else {
                throw TransferError.invalidData
            }

            guard let imported = await Self.find(uuid: uuid) else {
                throw TransferError.invalidData
            }

            return imported
        }
    }
}

extension Ghostty.SurfaceView {
    enum TransferError: Error {
        case invalidData
    }

    @MainActor
    static func find(uuid: UUID) -> Self? {
        guard let del = NSApp.delegate as? Ghostty.Delegate else { return nil }
        return del.ghosttySurface(id: uuid) as? Self
    }

    /// AppKit can serve this fixed 16-byte representation directly on Monterey,
    /// without the asynchronous Transferable bridge and its semaphore.
    func surfacePasteboardItem() -> NSPasteboardItem {
        let item = NSPasteboardItem()
        item.setData(id.surfaceTransferData, forType: .ghosttySurfaceId)
        return item
    }
}

extension UTType {
    /// A format that encodes the bare UUID only for the surface. This can be used if you have
    /// a way to look up a surface by ID.
    static let ghosttySurfaceId = UTType(exportedAs: "com.mitchellh.ghosttySurfaceId")
}

extension NSPasteboard.PasteboardType {
    /// Pasteboard type for dragging surface IDs.
    static let ghosttySurfaceId = NSPasteboard.PasteboardType(UTType.ghosttySurfaceId.identifier)
}
