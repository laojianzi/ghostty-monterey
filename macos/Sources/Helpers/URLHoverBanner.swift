import SwiftUI

struct URLHoverBanner: View {
    // True if we're hovering over the left URL view, so we can show it on the right.
    @State private var isHoveringURLLeft: Bool = false
    let padding: CGFloat = 5
    let cornerRadius: CGFloat = 9
    let url: String

    private var displayedURL: String {
        UntrustedURL(url).displayString
    }

    var body: some View {
        ZStack {
            HStack {
                Spacer()
                VStack(alignment: .leading) {
                    Spacer()

                    Text(verbatim: displayedURL)
                        .padding(.init(top: padding, leading: padding, bottom: padding, trailing: padding))
                        .background(
                            bannerBackground(topLeading: true)
                        )
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .opacity(isHoveringURLLeft ? 1 : 0)
                }
            }

            HStack {
                VStack(alignment: .leading) {
                    Spacer()

                    Text(verbatim: displayedURL)
                        .padding(.init(top: padding, leading: padding, bottom: padding, trailing: padding))
                        .background(
                            bannerBackground(topLeading: false)
                        )
                        .lineLimit(1)
                        .truncationMode(.middle)
                        .opacity(isHoveringURLLeft ? 0 : 1)
                        .onHover(perform: { hovering in
                            isHoveringURLLeft = hovering
                        })
                }
                Spacer()
            }
        }
    }

    @ViewBuilder
    private func bannerBackground(topLeading: Bool) -> some View {
        #if compiler(>=5.9)
        if #available(macOS 14, *) {
            UnevenRoundedRectangle(cornerRadii: .init(
                topLeading: topLeading ? cornerRadius : 0,
                topTrailing: topLeading ? 0 : cornerRadius
            ))
            .fill(.background)
        } else {
            legacyBackground(topLeading: topLeading)
        }
        #else
        legacyBackground(topLeading: topLeading)
        #endif
    }

    private func legacyBackground(topLeading: Bool) -> some View {
        URLBannerShape(radius: cornerRadius, topLeading: topLeading)
            .fill(.background)
    }
}

/// The banner meets the window's bottom corner, so only its inner top corner
/// is rounded. SwiftUI mirrors the shape for right-to-left layout.
private struct URLBannerShape: Shape {
    let radius: CGFloat
    let topLeading: Bool

    func path(in rect: CGRect) -> Path {
        let radius = min(max(radius, 0), min(rect.width, rect.height))
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.maxY))
        if topLeading {
            path.addLine(to: CGPoint(x: rect.minX, y: rect.minY + radius))
            path.addArc(
                center: CGPoint(x: rect.minX + radius, y: rect.minY + radius),
                radius: radius,
                startAngle: .degrees(180), endAngle: .degrees(270), clockwise: false
            )
            path.addLine(to: CGPoint(x: rect.maxX, y: rect.minY))
        } else {
            path.addLine(to: CGPoint(x: rect.minX, y: rect.minY))
            path.addLine(to: CGPoint(x: rect.maxX - radius, y: rect.minY))
            path.addArc(
                center: CGPoint(x: rect.maxX - radius, y: rect.minY + radius),
                radius: radius,
                startAngle: .degrees(270), endAngle: .degrees(360), clockwise: false
            )
        }
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}
