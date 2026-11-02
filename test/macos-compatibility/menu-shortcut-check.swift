import AppKit

private final class MenuActionTarget: NSObject {
    var calls: [String] = []

    @objc func invoke(_ sender: NSMenuItem) { calls.append(sender.title) }
}

@MainActor
func checkMenuDispatch() throws {
    _ = NSApplication.shared
    let target = MenuActionTarget()
    let menu = NSMenu(title: "Isolated shortcut fixture")
    menu.autoenablesItems = false
    let manager = Ghostty.MenuShortcutManager()
    let config = try TemporaryConfig("""
    keybind = clear
    keybind = super+backquote=toggle_quick_terminal
    keybind = super+a=new_window
    """)
    check(config.errors.isEmpty, "Shortcut fixture config")

    func item(_ title: String, action: String) -> NSMenuItem {
        let item = NSMenuItem(title: title, action: #selector(MenuActionTarget.invoke(_:)), keyEquivalent: "")
        item.target = target
        menu.addItem(item)
        manager.syncMenuShortcut(config, action: action, menuItem: item)
        return item
    }

    func event(_ code: UInt16, text: String, modifiers: NSEvent.ModifierFlags = .command) -> NSEvent {
        NSEvent.keyEvent(with: .keyDown, location: .zero, modifierFlags: modifiers,
                        timestamp: 0, windowNumber: 0, context: nil, characters: text,
                        charactersIgnoringModifiers: text, isARepeat: false, keyCode: code)!
    }

    let physical = item("physical", action: "toggle_quick_terminal")
    let unicode = item("unicode", action: "new_window")
    let both = event(0x32, text: "a")
    check(manager.performGhosttyBindingMenuKeyEquivalent(with: both), "Physical menu dispatch")
    check(target.calls == ["physical"], "Physical key must precede Unicode binding")
    physical.isEnabled = false
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: both), "Disabled physical binding consumed")
    check(target.calls == ["physical"], "Disabled physical binding fell through to Unicode")
    physical.isEnabled = true
    check(manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a")), "Unicode menu dispatch")
    check(target.calls.last == "unicode", "Wrong Unicode menu target")
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a", modifiers: .option)),
          "Wrong modifiers dispatched")
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "")), "Empty key dispatched")

    let replacement = item("replacement", action: "new_window")
    check(manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a")), "Duplicate binding dispatch")
    check(target.calls.last == "replacement", "Last registration must win")
    menu.removeItem(replacement)
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a")), "Detached menu item dispatched")
    manager.reset()
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: both), "Reset retained shortcut index")

    weak var released: NSMenuItem?
    autoreleasepool {
        let transient = item("transient", action: "new_window")
        released = transient
        menu.removeItem(transient)
    }
    check(released == nil, "Shortcut index owns menu item")
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a")), "Released menu item dispatched")
    try config.reload("keybind = clear\nkeybind = super+a=new_window\nkeybind = super+a=unbind")
    manager.reset()
    manager.syncMenuShortcut(config, action: "new_window", menuItem: unicode)
    check(unicode.keyEquivalent.isEmpty && unicode.keyEquivalentModifierMask.isEmpty,
          "Reload did not clear unbound shortcut")
    check(!manager.performGhosttyBindingMenuKeyEquivalent(with: event(0, text: "a")), "Unbound menu item dispatched")
    print("PASS: 15 upstream shortcut tests; native menu dispatch, physical precedence, disablement, reset, reload and weak ownership")
}
