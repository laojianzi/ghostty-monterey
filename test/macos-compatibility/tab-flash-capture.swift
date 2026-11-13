import AppKit
import ApplicationServices
import ImageIO

func require(_ condition: Bool, _ message: String) {
    if !condition {
        fputs("Invalid test: \(message)\n", stderr)
        exit(3)
    }
}

let args = CommandLine.arguments
if args.count == 3 && args[1] == "--activate" {
    if let pid = pid_t(args[2]) {
        NSRunningApplication(processIdentifier: pid)?.activate(options: [.activateIgnoringOtherApps])
    }
    exit(0)
}
require(CGPreflightScreenCaptureAccess(), "Existing Screen Recording permission required")
require(AXIsProcessTrusted(), "Existing Accessibility permission required")
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
require(session != nil && !(session?["CGSSessionScreenIsLocked"] as? Bool ?? false),
        "An unlocked GUI session is required")
if args.count == 2 && args[1] == "--preflight" { exit(0) }
require(args.count == 4, "Expected PID, evidence directory, and mode")
guard let pid = pid_t(args[1]), let app = NSRunningApplication(processIdentifier: pid) else {
    fatalError("Test application not running")
}
let out = URL(fileURLWithPath: args[2], isDirectory: true)
let mode = args[3]
require(["setup", "baseline", "switch"].contains(mode), "Unknown mode")
app.activate(options: [.activateIgnoringOtherApps])
usleep(500_000)
func key(_ code: CGKeyCode) {
    require(NSWorkspace.shared.frontmostApplication?.processIdentifier == pid, "Test app lost foreground")
    for down in [true, false] {
        let event = CGEvent(keyboardEventSource: nil, virtualKey: code, keyDown: down)!
        event.flags = .maskCommand
        event.postToPid(pid)
        usleep(10_000)
    }
}
if mode == "setup" {
    key(17) // Command-T
    sleep(2)
    exit(0)
}
func windows() -> [[String: Any]] {
    let all = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], 0)
        as? [[String: Any]] ?? []
    return all.filter {
        ($0[kCGWindowOwnerPID as String] as? Int) == Int(pid)
            && ($0[kCGWindowLayer as String] as? Int) == 0
    }
}
func visibleWindow() -> (Int, CGRect) {
    let owned = windows()
    require(owned.count == 1, "Expected one visible test window")
    guard let number = owned[0][kCGWindowNumber as String] as? Int,
          let bounds = owned[0][kCGWindowBounds as String] as? [String: Any],
          let rect = CGRect(dictionaryRepresentation: bounds as CFDictionary) else {
        fatalError("No visible window bounds")
    }
    return (number, rect)
}
let (initialID, rect) = visibleWindow()
// Sample the compositor, not an offscreen window snapshot. Only the fixture's
// central terminal area is captured; keep other windows/overlays away from it.
let crop = CGRect(x: rect.minX + rect.width * 0.15, y: rect.minY + rect.height * 0.25,
                  width: rect.width * 0.7, height: rect.height * 0.6)
require(CGDisplayBounds(CGMainDisplayID()).contains(crop), "Move the fixture fully onto the main display")
func save(_ image: CGImage, _ name: String) {
    let url = out.appendingPathComponent(name).appendingPathExtension("png")
    let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, image, nil)
    require(CGImageDestinationFinalize(dest), "Could not save evidence")
}
var rows = ["time,event,target,green,black,width,height,capture_ms,visible_window"]
let start = CFAbsoluteTimeGetCurrent()
var nextSwitch = 1.0
var switches = 0
var target = 2
var index = 0
var worst = 1.0
var bad = 0
var minCapture = 1000.0
var maxCapture = 0.0
var lastID = initialID
var changes = 0
var observedIDs: Set<Int> = [initialID]
var pendingSwitch = false
let end = mode == "baseline" ? 4.0 : 15.0
while CFAbsoluteTimeGetCurrent() - start < end {
    require(NSWorkspace.shared.frontmostApplication?.processIdentifier == pid, "Test app lost foreground")
    let now = CFAbsoluteTimeGetCurrent() - start
    var event = "sample"
    if mode == "switch" && now >= nextSwitch && switches < 20 {
        require(!pendingSwitch, "Previous tab switch did not take effect")
        target = target == 1 ? 2 : 1
        key(target == 1 ? 18 : 19) // Command-1 / Command-2
        pendingSwitch = true
        event = "switch"
        switches += 1
        nextSwitch += 0.6
    }
    let captureStart = CFAbsoluteTimeGetCurrent()
    guard let image = CGWindowListCreateImage(crop, .optionOnScreenOnly, 0, [.bestResolution]) else {
        fatalError("Capture failed")
    }
    let elapsed = (CFAbsoluteTimeGetCurrent() - captureStart) * 1000
    minCapture = min(minCapture, elapsed)
    maxCapture = max(maxCapture, elapsed)
    // Downsample for scoring; save unmodified crops for visual inspection.
    let size = 80
    var bytes = [UInt8](repeating: 0, count: size * size * 4)
    bytes.withUnsafeMutableBytes { storage in
        let context = CGContext(data: storage.baseAddress, width: size, height: size,
                                bitsPerComponent: 8, bytesPerRow: size * 4,
                                space: CGColorSpaceCreateDeviceRGB(),
                                bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
        context.draw(image, in: CGRect(x: 0, y: 0, width: size, height: size))
    }
    var green = 0
    var black = 0
    for offset in stride(from: 0, to: bytes.count, by: 4) {
        if bytes[offset + 1] > 180 && bytes[offset] < 60 && bytes[offset + 2] < 60 { green += 1 }
        if bytes[offset] < 40 && bytes[offset + 1] < 40 && bytes[offset + 2] < 40 { black += 1 }
    }
    let fraction = Double(green) / Double(size * size)
    if index == 0 { save(image, "first") }
    if fraction < worst { worst = fraction; save(image, "worst") }
    if fraction < 0.95 {
        bad += 1
        if bad <= 30 { save(image, "bad-\(index)") }
    }
    let (windowID, currentRect) = visibleWindow()
    require(currentRect == rect, "Window moved or resized during capture")
    if windowID != lastID {
        require(pendingSwitch, "Unexpected window change")
        changes += 1
        pendingSwitch = false
        lastID = windowID
        observedIDs.insert(windowID)
    }
    rows.append("\(now),\(event),\(target),\(fraction),\(Double(black) / Double(size * size)),"
                + "\(image.width),\(image.height),\(elapsed),\(windowID)")
    index += 1
}
try rows.joined(separator: "\n").write(to: out.appendingPathComponent("frames.csv"),
                                       atomically: true, encoding: .utf8)
print("samples=\(index) switches=\(switches) window_changes=\(changes) bad=\(bad) "
      + "min_green=\(worst) capture_ms=\(minCapture)...\(maxCapture)")
require(index >= (mode == "baseline" ? 60 : 300), "Too few compositor samples")
if mode == "switch" {
    require(switches == 20 && changes == 20 && observedIDs.count == 2 && !pendingSwitch,
            "Did not verify all 20 switches between two native tabs")
}
exit(bad == 0 ? 0 : 2)
