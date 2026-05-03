import SwiftUI

struct AboutView: View {
    @Environment(\.openURL) var openURL

    private let githubURL = URL(string: "https://github.com/laojianzi/ghostty-monterey")
    private let docsURL = URL(string: "https://ghostty.org/docs")

    /// Read the commit from the bundle.
    private var build: String? { Bundle.main.infoDictionary?["CFBundleVersion"] as? String }
    private var commit: String? { Bundle.main.infoDictionary?["GhosttyCommit"] as? String }
    private var commitURL: URL? {
        guard let commit, commit != "" else { return nil }
        return URL(string: "https://github.com/laojianzi/ghostty-monterey/commit/\(commit)")
    }
    private var version: String? { Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String }
    private var copyright: String? { Bundle.main.infoDictionary?["NSHumanReadableCopyright"] as? String }

    #if os(macOS)
    // This creates a background style similar to the Apple "About My Mac" Window
    private struct VisualEffectBackground: NSViewRepresentable {
        let material: NSVisualEffectView.Material
        let blendingMode: NSVisualEffectView.BlendingMode
        let isEmphasized: Bool

        init(material: NSVisualEffectView.Material,
             blendingMode: NSVisualEffectView.BlendingMode = .behindWindow,
             isEmphasized: Bool = false) {
            self.material = material
            self.blendingMode = blendingMode
            self.isEmphasized = isEmphasized
        }

        func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
            nsView.material = material
            nsView.blendingMode = blendingMode
            nsView.isEmphasized = isEmphasized
        }

        func makeNSView(context: Context) -> NSVisualEffectView {
            let visualEffect = NSVisualEffectView()
            visualEffect.autoresizingMask = [.width, .height]
            return visualEffect
        }
    }
    #endif

    var body: some View {
        VStack(alignment: .center) {
            CyclingIconView()

            VStack(alignment: .center, spacing: 32) {
                VStack(alignment: .center, spacing: 8) {
                    Text("Ghostty")
                        .bold()
                        .font(.title)
                    Text("macOS 12 compatibility build \nfrom ghostty-monterey.")
                        .multilineTextAlignment(.center)
                        .fixedSize(horizontal: false, vertical: true)
                        .font(.caption)
                        .tint(.secondary)
                        .opacity(0.8)
                }
                .textSelection(.enabled)

                VStack(spacing: 2) {
                    if let version {
                        PropertyRow(label: "Version", text: version)
                    }
                    if let build {
                        PropertyRow(label: "Build", text: build)
                    }
                    if let commit, let url = commitURL {
                        PropertyRow(label: "Commit", text: commit, url: url)
                    }
                    if let url = githubURL {
                        PropertyRow(label: "Source", text: "ghostty-monterey", url: url)
                    }
                }
                .frame(maxWidth: .infinity)

                HStack(spacing: 8) {
                    if let url = docsURL {
                        Button("Docs") {
                            openURL(url)
                        }
                    }
                    if let url = githubURL {
                        Button("GitHub") {
                            openURL(url)
                        }
                    }
                }

                if let copy = self.copyright {
                    Text(copy)
                        .font(.caption)
                        .textSelection(.enabled)
                        .tint(.secondary)
                        .opacity(0.8)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                }
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.top, 8)
        .padding(32)
        .frame(minWidth: 256)
        #if os(macOS)
        .background(VisualEffectBackground(material: .underWindowBackground).ignoresSafeArea())
        #endif
    }

    private struct PropertyRow: View {
        private let label: String
        private let text: String
        private let url: URL?

        init(label: String, text: String, url: URL? = nil) {
            self.label = label
            self.text = text
            self.url = url
        }

        @ViewBuilder private var textView: some View {
            Text(text)
                .lineLimit(1)
                .minimumScaleFactor(0.75)
                .frame(maxWidth: .infinity, alignment: .leading)
                .tint(.secondary)
                .opacity(0.8)
                .font(.system(.body, design: .monospaced))
        }

        var body: some View {
            HStack(spacing: 4) {
                Text(label)
                    .frame(width: 72, alignment: .trailing)
                if let url {
                    Link(destination: url) {
                        textView
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                } else {
                    textView
                }
            }
            .font(.callout)
            .textSelection(.enabled)
            .frame(width: 240)
        }
    }
}

struct AboutView_Previews: PreviewProvider {
    static var previews: some View {
        AboutView()
    }
}
