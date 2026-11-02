// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "MontereyTestingDependencies",
    platforms: [.macOS(.v12)],
    dependencies: [
        .package(url: "https://github.com/swiftlang/swift-testing.git",
                 revision: "8097dd8bcf7f2ed85f8aa8883635ce413012f53b"),
        .package(url: "https://github.com/apple/swift-syntax.git",
                 revision: "2bc86522d115234d1f588efe2bcb4ce4be8f8b82")
    ],
    targets: [
        .target(name: "DependencyProbe", dependencies: [.product(name: "Testing", package: "swift-testing")])
    ]
)
