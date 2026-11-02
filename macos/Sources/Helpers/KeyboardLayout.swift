import AppKit
import Carbon

class KeyboardLayout {
    /// Return a string ID of the current keyboard input source.
    static var id: String? {
        if let source = TISCopyCurrentKeyboardInputSource()?.takeRetainedValue(),
           let sourceIdPointer = TISGetInputSourceProperty(source, kTISPropertyInputSourceID) {
            let sourceId = unsafeBitCast(sourceIdPointer, to: CFString.self)
            return sourceId as String
        }

        return nil
    }

    /// Translate a physical keycode for use as a menu key equivalent.
    ///
    /// AppKit retranslates against the current input source without changing its dead key state.
    ///
    /// - Important: Must be called on the main thread because underlying Text Input Sources APIs are not thread-safe.
    @MainActor static func character(
        for keyCode: UInt16,
        modifiers: NSEvent.ModifierFlags
    ) -> Character? {
        guard
            let event = NSEvent.keyEvent(
                with: .keyDown,
                location: .zero,
                modifierFlags: [],
                timestamp: 0,
                windowNumber: 0,
                context: nil,
                characters: "",
                charactersIgnoringModifiers: "",
                isARepeat: false,
                keyCode: keyCode)
        else { return nil }

        // Synthetic events can have no AppKit translation while an IME is active.
        // Fall back to its underlying layout without composing or changing IME state.
        guard
            let result = event.characters(byApplyingModifiers: modifiers)
                ?? characters(for: keyCode, modifiers: modifiers),
            result.count == 1
        else { return nil }

        return result.first
    }

    /// Translate a physical key through the current keyboard layout without
    /// asking AppKit to reinterpret an NSEvent.
    ///
    /// Control is intentionally ignored; Ghostty encodes control characters.
    /// Command is preserved for layouts such as Dvorak-QWERTY Command.
    static func characters(
        for keyCode: UInt16,
        modifiers: NSEvent.ModifierFlags = []
    ) -> String? {
        guard
            let source = TISCopyCurrentKeyboardLayoutInputSource()?.takeRetainedValue(),
            let rawLayoutData = TISGetInputSourceProperty(
                source,
                kTISPropertyUnicodeKeyLayoutData
            )
        else {
            return nil
        }

        let layoutData = Unmanaged<CFData>
            .fromOpaque(rawLayoutData)
            .takeUnretainedValue() as Data

        var modifierState: UInt32 = 0
        if modifiers.contains(.command) { modifierState |= UInt32(cmdKey >> 8) }
        if modifiers.contains(.shift) { modifierState |= UInt32(shiftKey >> 8) }
        if modifiers.contains(.option) { modifierState |= UInt32(optionKey >> 8) }
        if modifiers.contains(.capsLock) { modifierState |= UInt32(alphaLock >> 8) }

        let maxLength = 4
        var deadKeyState: UInt32 = 0
        var translated = [UniChar](repeating: 0, count: maxLength)
        var translatedCount = 0
        let status = layoutData.withUnsafeBytes { bytes in
            UCKeyTranslate(
                bytes.bindMemory(to: UCKeyboardLayout.self).baseAddress,
                keyCode,
                UInt16(kUCKeyActionDown),
                modifierState,
                UInt32(LMGetKbdType()),
                UInt32(kUCKeyTranslateNoDeadKeysMask),
                &deadKeyState,
                maxLength,
                &translatedCount,
                &translated
            )
        }

        guard status == noErr, translatedCount > 0 else { return nil }
        return String(utf16CodeUnits: translated, count: translatedCount)
    }
}
