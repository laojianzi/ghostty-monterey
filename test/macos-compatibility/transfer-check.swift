import AppKit
import UniformTypeIdentifiers

// Only the terminal/app shells are stand-ins. Compile the real production
// pasteboard implementation and UUID codec against native AppKit providers.
protocol TestGhosttyDelegate: NSApplicationDelegate {
    func ghosttySurface(id: UUID) -> AnyObject?
}

enum Ghostty {
    typealias Delegate = TestGhosttyDelegate

    final class SurfaceView {
        let id: UUID

        init(id: UUID) {
            self.id = id
        }
    }
}

@main
struct TransferChecks {
    static func main() throws {
        let uuid = UUID(uuidString: "00112233-4455-6677-8899-AABBCCDDEEFF")!
        let surface = Ghostty.SurfaceView(id: uuid)
        let item = surface.surfacePasteboardItem()
        precondition(item.types == [.ghosttySurfaceId])
        let board = NSPasteboard(name: .init("ghostty-transfer-test-\(UUID())"))
        defer { board.releaseGlobally() }
        precondition(board.writeObjects([item]))
        let data = board.data(forType: .ghosttySurfaceId)!
        precondition(data.count == 16)
        precondition(UUID(surfaceTransferData: data) == uuid)

        // Native asynchronous item-provider transport uses exactly the drop
        // consumer's type identifier, including malformed payload handling.
        for payload in [data, Data(data.dropLast()), Data(), data + Data([0])] {
            let provider = NSItemProvider()
            provider.registerDataRepresentation(forTypeIdentifier: UTType.ghosttySurfaceId.identifier,
                                                visibility: .all) { complete in
                DispatchQueue.global().async { complete(payload, nil) }
                return nil
            }
            let finished = DispatchSemaphore(value: 0)
            _ = provider.loadDataRepresentation(forTypeIdentifier: UTType.ghosttySurfaceId.identifier) {
                received, error in
                precondition(error == nil)
                precondition(received == payload)
                precondition(UUID(surfaceTransferData: received!) == (payload.count == 16 ? uuid : nil))
                finished.signal()
            }
            precondition(finished.wait(timeout: .now() + 5) == .success, "Item provider timed out")
        }
        print("PASS: production pasteboard, native item provider, UUID and malformed transport")
    }
}
