import Foundation

/// App-global operations provided to GhosttyKit by the application delegate.
protocol GhosttyDelegate: AnyObject {
    func ghosttySurface(id: UUID) -> Ghostty.SurfaceView?
}

extension Ghostty {
    typealias Delegate = GhosttyDelegate
}
