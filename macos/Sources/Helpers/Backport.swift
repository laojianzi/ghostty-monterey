import SwiftUI

// All backport view/scene modifiers go as an extension on this. We use this
// so we can easily track and centralize all backports.
struct Backport<Content> {
    let content: Content
}

extension View {
    var backport: Backport<Self> { Backport(content: self) }
}

extension Scene {
    var backport: Backport<Self> { Backport(content: self) }
}

extension Backport where Content: Scene {
    // None currently
}

/// Result type for backported onKeyPress handler
enum BackportKeyPressResult {
    case handled
    case ignored
}

extension Backport where Content: View {
    func pointerVisibility(_ v: BackportVisibility) -> some View {
        #if compiler(>=6.0)
        if #available(macOS 15, *) {
            return content.pointerVisibility(v.official)
        } else {
            return content
        }
        #else
        return content
        #endif
    }

    func pointerStyle(_ style: BackportPointerStyle?) -> some View {
        #if compiler(>=6.0)
        if #available(macOS 15, *) {
            return content.pointerStyle(style?.official)
        } else {
            return legacyPointerStyle(style)
        }
        #else
        return legacyPointerStyle(style)
        #endif
    }

    @ViewBuilder
    private func legacyPointerStyle(_ style: BackportPointerStyle?) -> some View {
        // Split dividers already manage resize cursors with onHover on Monterey.
        if case .link? = style {
            content.background(LinkCursorRegion())
        } else {
            content
        }
    }

    /// Backported onKeyPress that works on macOS 14+ and is a no-op on macOS 13.
    func onKeyPress(_ key: KeyEquivalent, action: @escaping (EventModifiers) -> BackportKeyPressResult) -> some View {
        #if compiler(>=5.9)
        if #available(macOS 14, *) {
            return content.onKeyPress(key, phases: .down, action: { keyPress in
                switch action(keyPress.modifiers) {
                case .handled: return .handled
                case .ignored: return .ignored
                }
            })
        } else {
            return content
        }
        #else
        return content
        #endif
    }
}

private struct LinkCursorRegion: NSViewRepresentable {
    func makeNSView(context: Context) -> CursorView { CursorView() }
    func updateNSView(_ view: CursorView, context: Context) {}

    final class CursorView: NSView {
        override func hitTest(_ point: NSPoint) -> NSView? { nil }

        override func resetCursorRects() {
            super.resetCursorRects()
            addCursorRect(visibleRect, cursor: .pointingHand)
        }
    }
}

enum BackportVisibility {
    case automatic
    case visible
    case hidden

    @available(macOS 15, *)
    var official: Visibility {
        switch self {
        case .automatic: return .automatic
        case .visible: return .visible
        case .hidden: return .hidden
        }
    }
}

enum BackportPointerStyle {
    case `default`
    case grabIdle
    case grabActive
    case horizontalText
    case verticalText
    case link
    case resizeLeft
    case resizeRight
    case resizeUp
    case resizeDown
    case resizeUpDown
    case resizeLeftRight

    #if compiler(>=6.0)
    @available(macOS 15, *)
    var official: PointerStyle {
        switch self {
        case .default: return .default
        case .grabIdle: return .grabIdle
        case .grabActive: return .grabActive
        case .horizontalText: return .horizontalText
        case .verticalText: return .verticalText
        case .link: return .link
        case .resizeLeft: return .columnResize(directions: .leading)
        case .resizeRight: return .columnResize(directions: .trailing)
        case .resizeUp: return .rowResize(directions: .up)
        case .resizeDown: return .rowResize(directions: .down)
        case .resizeUpDown: return .rowResize
        case .resizeLeftRight: return .columnResize
        }
    }
    #endif
}

enum BackportGlass {
    case regular, clear

    #if compiler(>=6.2)
    @available(macOS 26, *)
    var official: Glass {
        switch self {
        case .regular: return .regular
        case .clear: return .clear
        }
    }
    #endif
}

/// Backported `TextField` with an AppKit selection bridge on older systems.
///
/// Although the API is available from macOS 15, we force it to be 26. Because on macOS 15,
/// SwiftUI will crash when deleting texts, even for this simple example.
///
///     struct ContentView: View {
///         @State private var text = ""
///         @State private var selection: TextSelection?
///         var body: some View {
///             TextField("Search", text: $text, selection: $selection)
///         }
///     }
struct BackportSelectionTextField: View {
    private let titleKey: LocalizedStringKey
    @Binding private var text: String
    @Binding private var textSelection: Range<String.Index>?

    init(
        _ titleKey: LocalizedStringKey,
        text: Binding<String>,
        selection: Binding<Range<String.Index>?>,
        focus: FocusState<Bool>.Binding? = nil
    ) {
        self.focus = focus
        self.titleKey = titleKey
        self._text = text
        self._textSelection = selection
    }

    var body: some View {
        #if compiler(>=6.2)
        if #available(macOS 26, *) {
            TextField(
                titleKey,
                text: _text,
                selection: Binding(
                    get: {
                        if let textSelection {
                            return TextSelection(range: textSelection)
                        } else {
                            return nil
                        }
                    },
                    set: { selection in
                        if let selection,
                           case .selection(let range) = selection.indices {
                            self.textSelection = range
                        } else {
                            self.textSelection = nil
                        }
                    }
                )
            )
            .modifier(OptionalTextFieldFocus(focus: focus))
        } else {
            legacyField
        }
        #else
        legacyField
        #endif
    }

    private let focus: FocusState<Bool>.Binding?

    private var legacyField: some View {
        // On Monterey, an outer focused modifier can target the representable
        // background instead of the field. Bind the actual text input first.
        Group {
            if let focus {
                TextField(titleKey, text: _text).focused(focus)
            } else {
                TextField(titleKey, text: _text)
            }
        }
            .background(TextFieldSelectionBridge(text: text, selection: $textSelection))
    }
}

private struct OptionalTextFieldFocus: ViewModifier {
    let focus: FocusState<Bool>.Binding?

    @ViewBuilder func body(content: Content) -> some View {
        if let focus {
            content.focused(focus)
        } else {
            content
        }
    }
}

private struct TextFieldSelectionBridge: NSViewRepresentable {
    let text: String
    @Binding var selection: Range<String.Index>?

    func makeNSView(context: Context) -> SelectionView { SelectionView() }

    func updateNSView(_ view: SelectionView, context: Context) {
        view.text = text
        view.selection = selection.map { NSRange($0, in: text) }
        view.writeSelection = { range in
            let value = Range(range, in: text)
            if selection != value { selection = value }
        }
        view.scheduleSelection()
    }

    final class SelectionView: NSView {
        var text = ""
        var selection: NSRange?
        var writeSelection: ((NSRange) -> Void)?
        private var pending = false
        private var applying = false
        private var edited = false
        private var editedText: String?

        override init(frame: NSRect) {
            super.init(frame: frame)
            let center = NotificationCenter.default
            center.addObserver(self, selector: #selector(editingBegan),
                               name: NSControl.textDidBeginEditingNotification, object: nil)
            center.addObserver(self, selector: #selector(selectionChanged),
                               name: NSTextView.didChangeSelectionNotification, object: nil)
            center.addObserver(self, selector: #selector(textChanged),
                               name: NSControl.textDidChangeNotification, object: nil)
        }

        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }

        deinit { NotificationCenter.default.removeObserver(self) }

        // SwiftUI owns the field and its delegate. Its native controls can be
        // siblings at the hosting root, so restrict lookup to our background's bounds.
        private var field: NSTextField? {
            func find(_ view: NSView) -> NSTextField? {
                if let field = view as? NSTextField,
                   bounds.contains(convert(NSPoint(x: field.bounds.midX, y: field.bounds.midY), from: field)) {
                    return field
                }
                return view.subviews.lazy.compactMap { find($0) }.first
            }
            var ancestor = superview
            while let view = ancestor {
                if let field = find(view) { return field }
                if view === window?.contentView { break }
                ancestor = view.superview
            }
            return nil
        }

        func scheduleSelection() {
            guard !pending else { return }
            pending = true
            DispatchQueue.main.async { [weak self] in
                guard let self else { return }
                self.pending = false
                // Monterey SwiftUI can drop an external replacement in the same
                // update as a native edit. Reconcile after that update, without
                // writing the model/pasteboard again or interrupting composition.
                if let field = self.field, let editor = field.currentEditor() as? NSTextView,
                   !editor.hasMarkedText(), editor.string != self.text {
                    self.applying = true
                    field.stringValue = self.text
                    editor.string = self.text
                    self.applying = false
                    self.edited = false
                }
                if self.edited {
                    self.edited = false
                    if self.editedText == self.text {
                        if let editor = self.field?.currentEditor() as? NSTextView,
                           editor.string == self.text, !editor.hasMarkedText() {
                            self.writeSelection?(editor.selectedRange())
                        }
                        return
                    }
                }
                guard let range = self.selection,
                      let field = self.field, field.stringValue == self.text,
                      let editor = field.currentEditor() as? NSTextView,
                      !editor.hasMarkedText(), editor.selectedRange() != range else { return }
                self.applying = true
                editor.setSelectedRange(range)
                self.applying = false
            }
        }

        @objc private func editingBegan(_ notification: Notification) {
            guard notification.object as? NSTextField === field else { return }
            scheduleSelection()
        }

        @objc private func textChanged(_ notification: Notification) {
            guard let changedField = notification.object as? NSTextField, changedField === field else { return }
            edited = true
            editedText = changedField.stringValue
            scheduleSelection()
        }

        @objc private func selectionChanged(_ notification: Notification) {
            guard !applying, !pending,
                  let editor = notification.object as? NSTextView,
                  editor === field?.currentEditor(), editor.string == text,
                  !editor.hasMarkedText() else { return }
            writeSelection?(editor.selectedRange())
        }
    }
}
