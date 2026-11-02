#!/usr/bin/env python3
"""Check bundled icon assets/composition without changing Dock or Finder icons."""

import pathlib
import platform
import re
import subprocess
import sys
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
app = pathlib.Path(sys.argv[1]).resolve()
assert (app / "Contents/Resources/Assets.car").is_file()
tests = (root / "macos/Tests/ColorizedGhosttyIconTests.swift").read_text()
methods = re.findall(r"@Test func (\w+)\(\)( throws)?", tests)
assert len(methods) == tests.count("@Test") == 10, "Update bounded test adapter"
tests = tests.replace("import Testing", "").replace("@testable import Ghostty", "")
tests = tests.replace("@Test ", "").replace("#expect(", "check(").replace("#require(", "require(")
assert not re.search(r"#(?:expect|require)|@(?:Test|Suite)", tests)
harness = r'''
import AppKit
import CryptoKit
enum Ghostty {}
func check(_ condition: Bool, _ message: String = "Upstream assertion failed",
           file: StaticString = #file, line: UInt = #line) {
    if !condition {
        FileHandle.standardError.write(Data("FAIL: \(message) (\(file):\(line))\n".utf8))
        exit(1)
    }
}
struct MissingValue: Error {}
func require<T>(_ value: T?) throws -> T {
    guard let value else { throw MissingValue() }
    return value
}
enum Issue { static func record(_ message: String) { check(false, message) } }
func pixels(_ image: NSImage) -> Data {
    check(image.size.width > 0 && image.size.height > 0, "Empty icon dimensions")
    let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil)!
    // Normalize dimensions and color space to compare decoded assets/composition.
    let context = CGContext(data: nil, width: 64, height: 64, bitsPerComponent: 8,
                            bytesPerRow: 256, space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    context.draw(cg, in: CGRect(x: 0, y: 0, width: 64, height: 64))
    let data = Data(bytes: context.data!, count: 64 * 256)
    check(data.contains { $0 != 0 }, "Empty rendered icon")
    return data
}
@main struct Runner {
    static func main() throws {
        _ = NSApplication.shared
        UPSTREAM_CALLS
        let app = Bundle(path: CommandLine.arguments[1])!
        let plugin = Bundle(path: CommandLine.arguments[1] + "/Contents/PlugIns/DockTilePlugin.plugin")!
        let builtins: [AppIcon] = [.blueprint, .chalkboard, .glass, .holographic, .microchip, .paper, .retro, .xray]
        var hashes = Set<Data>()
        for icon in builtins {
            let image = try require(icon.image(in: app))
            let data = pixels(image)
            check(data == pixels(try require(icon.image(in: plugin))), "App/plugin asset mismatch")
            hashes.insert(Data(SHA256.hash(data: data)))
            let decoded = try JSONDecoder().decode(AppIcon.self, from: JSONEncoder().encode(icon))
            check(decoded == icon, "Built-in persistence")
        }
        check(hashes.count == builtins.count, "Built-in icons collapsed to duplicate images")
        check(AppIcon.official.image(in: app) == nil, "Official override should reset icon")
        check(AppIcon.custom(Data()).image(in: app) == nil, "Invalid custom data accepted")
        let image = try require(builtins[0].image(in: app))
        let custom = AppIcon.custom(try require(image.tiffRepresentation))
        check(pixels(try require(custom.image(in: app))) == pixels(image), "Custom image decoding")
        let baseApp = pixels(try require(app.image(forResource: "AppIconImage")))
        check(baseApp == pixels(try require(plugin.image(forResource: "AppIconImage"))), "Default asset mismatch")
        var styles = Set<Data>()
        for frame in [Ghostty.MacOSIconFrame.aluminum, .beige, .plastic, .chrome] {
            for alternate in [false, true] {
                let style = ColorizedGhosttyIcon(screenColors: alternate ? [.red, .yellow] : [.blue, .green],
                                                 ghostColor: alternate ? .black : .white, frame: frame)
                let data = pixels(try require(style.makeImage(in: app)))
                check(data == pixels(try require(style.makeImage(in: plugin))), "Custom style app/plugin mismatch")
                styles.insert(Data(SHA256.hash(data: data)))
                let persisted = AppIcon.customStyle(style)
                let decoded = try JSONDecoder().decode(AppIcon.self, from: JSONEncoder().encode(persisted))
                check(decoded == persisted, "Custom style persistence")
            }
        }
        check(styles.count == 8, "Frame or color variation lost")
        check(NSImage.combine(images: [], blendingModes: []) == nil, "Empty composition accepted")
        check(NSImage.combine(images: [image], blendingModes: []) == nil, "Mismatched composition accepted")
        print("PASS: 10 upstream icon tests; 8 built-ins, 8 custom styles, app/plugin raster parity, custom data and persistence")
    }
}
'''.replace("UPSTREAM_CALLS", "\n".join(f"{'try ' if throwing else ''}ColorizedGhosttyIconTests().{method}()" for method, throwing in methods))

with tempfile.TemporaryDirectory(prefix="ghostty-icons-") as directory:
    tmp = pathlib.Path(directory)
    (tmp / "Runner.swift").write_text(harness)
    (tmp / "Tests.swift").write_text(tests)
    sources = [root / "macos/Sources/Ghostty/Ghostty.ConfigTypes.swift",
               root / "macos/Sources/Features/Custom App Icon/AppIcon.swift",
               root / "macos/Sources/Features/Custom App Icon/ColorizedGhosttyIcon.swift",
               root / "macos/Sources/Helpers/Extensions/NSImage+Extension.swift",
               root / "macos/Sources/Helpers/Extensions/OSColor+Extension.swift",
               tmp / "Tests.swift", tmp / "Runner.swift"]
    implementation = sources[2].read_text()
    mutant = implementation.replace('bundle.image(forResource: baseName)',
                                    'bundle.image(forResource: "CustomIconBaseAluminum")')
    assert mutant != implementation
    for opt in ("-Onone", "-O"):
        for name, source in (("production", implementation), ("ignore-frame", mutant)):
            sources[2] = tmp / "ColorizedGhosttyIcon.swift"
            sources[2].write_text(source)
            binary = tmp / "icons"
            subprocess.run(["xcrun", "swiftc", opt, "-D", "DOCK_TILE_PLUGIN", "-target",
                            f"{platform.machine()}-apple-macosx12.0", *map(str, sources), "-o", str(binary)], check=True)
            result = subprocess.run([str(binary), str(app)], text=True, capture_output=True, timeout=60)
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                print(opt + ": " + result.stdout.strip(), flush=True)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
            else:
                assert result.returncode != 0 and "Frame or color variation lost" in result.stderr, result.stdout + result.stderr
                print(opt + ": PASS: compiled ignore-frame mutant rejected", flush=True)
