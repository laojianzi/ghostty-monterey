import Foundation

private final class Target {
    var calls = 0
}

@main
struct UndoChecks {
    static func main() {
        let manager = ExpiringUndoManager()
        manager.groupsByEvent = false
        let target = Target()

        func register(_ duration: GhosttyDuration) {
            manager.beginUndoGrouping()
            manager.registerUndo(withTarget: target, expiresAfter: duration) { $0.calls += 1 }
            manager.endUndoGrouping()
        }

        register(.seconds(1))
        precondition(manager.canUndo)
        manager.undo()
        precondition(target.calls == 1 && !manager.canUndo)

        manager.registerUndo(withTarget: target, expiresAfter: .seconds(0)) { $0.calls += 1 }
        manager.registerUndo(withTarget: target, expiresAfter: .milliseconds(-1)) { $0.calls += 1 }
        precondition(!manager.canUndo)
        manager.disableUndoRegistration()
        manager.registerUndo(withTarget: target, expiresAfter: .seconds(1)) { $0.calls += 1 }
        manager.enableUndoRegistration()
        precondition(!manager.canUndo)

        register(.milliseconds(20))
        precondition(manager.canUndo)
        RunLoop.main.run(until: Date(timeIntervalSinceNow: 0.1))
        precondition(!manager.canUndo && target.calls == 1)

        register(.seconds(30))
        manager.removeAllActions(withTarget: target)
        precondition(!manager.canUndo)
        register(.seconds(30))
        manager.removeAllActions()
        precondition(!manager.canUndo)

        let other = Target()
        manager.beginUndoGrouping()
        manager.registerUndo(withTarget: target, expiresAfter: .seconds(30)) { $0.calls += 1 }
        manager.registerUndo(withTarget: other, expiresAfter: .seconds(30)) { $0.calls += 1 }
        manager.endUndoGrouping()
        manager.removeAllActions(withTarget: target)
        manager.undo()
        precondition(other.calls == 1 && target.calls == 1)

        // Registering the inverse inside the handler must retain normal redo
        // behavior; releasing the consumed proxy must not remove the inverse.
        manager.beginUndoGrouping()
        manager.registerUndo(withTarget: target, expiresAfter: .seconds(30)) { value in
            value.calls += 1
            manager.registerUndo(withTarget: value, expiresAfter: .seconds(30)) { $0.calls -= 1 }
        }
        manager.endUndoGrouping()
        manager.undo()
        precondition(target.calls == 2 && manager.canRedo)
        manager.redo()
        precondition(target.calls == 1)
        manager.removeAllActions()

        // The undo entry must not own the real terminal/controller.
        weak var weakTarget: Target?
        do {
            let temporary = Target()
            weakTarget = temporary
            manager.beginUndoGrouping()
            manager.registerUndo(withTarget: temporary, expiresAfter: .seconds(30)) { _ in
                preconditionFailure("Dead target must not receive undo")
            }
            manager.endUndoGrouping()
        }
        precondition(weakTarget == nil)
        manager.undo()
        precondition(!manager.canUndo)

        // A timer must not keep the manager alive after its owning window closes.
        weak var weakManager: ExpiringUndoManager?
        do {
            let temporary = ExpiringUndoManager()
            temporary.groupsByEvent = false
            weakManager = temporary
            temporary.beginUndoGrouping()
            temporary.registerUndo(withTarget: target, expiresAfter: .seconds(30)) { $0.calls += 1 }
            temporary.endUndoGrouping()
        }
        precondition(weakManager == nil)
        print("PASS: native expiring undo execution, TTL, disable/removal, weak target and manager lifetime")
    }
}
