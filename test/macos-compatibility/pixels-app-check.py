#!/usr/bin/env python3
"""Capture only app-smoke's window; verify actual compositor color output.

Requires existing Screen Recording permission (never requests it). Does not
capture other windows or the desktop. Text samples support visual inspection;
pixel counts are not glyph-shaping, GPU performance or all-renderer acceptance.
"""

import pathlib
import plistlib
import shlex
import struct
import subprocess
import sys
import time
import zlib

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
pid = int(sys.argv[3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
assert plistlib.loads((app / "Contents/Info.plist").read_bytes())["CFBundleIdentifier"] == (
    "com.mitchellh.ghostty.monterey-smoke")


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.check_output(["osascript", "-"],
        input=f"tell application {literal(app)}\n{body}\nend tell", text=True, timeout=15).strip()


source = work / "pixels-client.swift"
source.write_text(r'''
import AppKit
import ImageIO
precondition(CGPreflightScreenCaptureAccess(), "Existing Screen Recording permission required; no prompt requested")
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
if CommandLine.arguments[1] == "--preflight" { exit(0) }
let pid = Int(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                       kCGNullWindowID) as? [[String: Any]] ?? []
let owned = windows.filter {
    $0[kCGWindowOwnerPID as String] as? Int == pid && $0[kCGWindowLayer as String] as? Int == 0
}
precondition(owned.count == 1, "Expected exactly one visible isolated-app window")
let number = CGWindowID((owned[0][kCGWindowNumber as String] as! NSNumber).uint32Value)
guard let image = CGWindowListCreateImage(.null, .optionIncludingWindow, number,
                                         [.boundsIgnoreFraming, .bestResolution]) else {
    fatalError("Cannot capture the isolated window")
}
let url = URL(fileURLWithPath: CommandLine.arguments[2])
let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil)!
CGImageDestinationAddImage(destination, image, nil)
precondition(CGImageDestinationFinalize(destination))
let width = image.width
let height = image.height
var bytes = [UInt8](repeating: 0, count: width * height * 4)
let space = CGColorSpace(name: CGColorSpace.sRGB)!
bytes.withUnsafeMutableBytes { storage in
    let context = CGContext(data: storage.baseAddress, width: width, height: height,
                            bitsPerComponent: 8, bytesPerRow: width * 4, space: space,
                            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
}
var counts = [0, 0, 0]
for offset in stride(from: 0, to: bytes.count, by: 4) {
    // Exclude window chrome (notably the green traffic-light button) and edges.
    // Symmetric margins also avoid relying on the bitmap's vertical orientation.
    let x = (offset / 4) % width
    let y = (offset / 4) / width
    guard x >= width / 10, x < width * 9 / 10,
          y >= height / 10, y < height * 9 / 10 else { continue }
    let rgb = bytes[offset..<(offset + 3)].map(Int.init)
    for channel in 0..<3 {
        if rgb[channel] > 180 && rgb[(channel + 1) % 3] < 80 && rgb[(channel + 2) % 3] < 80 {
            counts[channel] += 1
        }
    }
}
print("window=\(number) pixels=\(width)x\(height) RGB-counts=\(counts)")
fflush(stdout)
if CommandLine.arguments[3] == "color" {
    precondition(counts.allSatisfy { $0 > 1000 }, "Missing visible red/green/blue terminal blocks")
} else if CommandLine.arguments[3] == "kitty-red" {
    precondition(counts[0] > 1000 && counts[1] < 300 && counts[2] < 300,
                 "Kitty image did not present red pixels")
} else if CommandLine.arguments[3] == "kitty-green" {
    precondition(counts[1] > 1000 && counts[0] < 300 && counts[2] < 300,
                 "Kitty replacement did not replace red with green pixels")
} else if CommandLine.arguments[3] == "shader-blue" || CommandLine.arguments[3] == "background-blue" {
    precondition(counts[2] > width * height / 2 && counts[0] < 300 && counts[1] < 300,
                 "Custom shader did not cover the terminal with blue output")
} else {
    precondition(counts.allSatisfy { $0 < 300 }, "Blank-screen control still contains colored blocks")
}
''')
client = work / "pixels-client"
subprocess.run(["xcrun", "swiftc", str(source), "-o", str(client)], check=True)
subprocess.run([str(client), "--preflight"], check=True)
terminal = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(terminal)}"
child = work / "pixels-output.py"
child.write_text(r'''
import base64, pathlib, sys
stage, ready = sys.argv[1:]
if stage not in ('kitty-replace', 'kitty-green'):
    print('\x1b[0m\x1b[2J\x1b[H', end='')
if stage == 'blank':
    print('\x1b_Ga=d,d=A,q=2\x1b\\', end='')
if stage == 'color':
    print('Monterey compositor: RGB blocks and Unicode\r')
    for _ in range(4):
        print(''.join('\x1b[48;2;' + color + 'm' + ' ' * 16
                      for color in ('255;0;0', '0;255;0', '0;0;255')) + '\x1b[0m\r')
    print('ASCII: Ghostty 1.4 0123456789 != ->\r')
    print('CJK: \u4e2d\u6587 \u65e5\u672c\u8a9e \ud55c\uad6d\uc5b4\r')
    print('Unicode: e\u0301 \U0001f680 \U0001f600\r')
    print('\x1b[1mBold\x1b[0m \x1b[3mItalic\x1b[0m \x1b[4mUnderline\x1b[0m\r')
elif stage in ('kitty-red', 'kitty-replace'):
    color = (255, 0, 0, 255) if stage == 'kitty-red' else (0, 255, 0, 255)
    data = base64.b64encode(bytes(color) * 16 * 16).decode()
    # A retransmission removes old placements under the upstream protocol.
    # Verify that intermediate blank state before explicitly placing it again.
    if stage == 'kitty-red':
        print('\x1b[5;10H', end='')
        control = 'a=T,f=32,s=16,v=16,i=73,c=40,r=8,q=2'
    else:
        control = 'a=t,f=32,s=16,v=16,i=73,q=2'
    print('\x1b_G' + control + ';' + data + '\x1b\\', end='')
    print('\x1b[18;1H', end='')
elif stage == 'kitty-green':
    print('\x1b[5;10H\x1b_Ga=p,i=73,c=40,r=8,q=2\x1b\\\x1b[18;1H', end='')
sys.stdout.flush()
pathlib.Path(ready).touch()
''')
for index, stage in enumerate(("blank", "color", "blank", "kitty-red", "kitty-replace", "kitty-green", "blank")):
    ready = work / f"pixels-{stage}-ready"
    ready.unlink(missing_ok=True)
    command = shlex.join([sys.executable, str(child), stage, str(ready)])
    script(f'input text {literal(command)} to {target}\nsend key "enter" to {target}')
    deadline = time.monotonic() + 5
    while not ready.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert ready.exists(), "PTY did not finish the visual fixture"
    # Core output is asynchronous; the following capture must observe its result,
    # not just the child's completed write. No product flush or render hook.
    time.sleep(0.7)
    subprocess.run([str(client), str(pid), str(work / f"pixels-{index}-{stage}.png"), stage], check=True, timeout=10)
print("PASS: compositor RGB blocks and Kitty upload/replacement/deletion; blank controls remain blank", flush=True)

# The shader must visibly affect the actual app drawable, not merely compile or
# appear in a log. Removing it must restore the blank terminal without relaunch.
shader = work / "pixels-solid-blue.glsl"
shader.write_text("void mainImage(out vec4 fragColor, in vec2 fragCoord) {\n"
                  "    fragColor = vec4(0.0, 0.0, 1.0, 1.0);\n}\n")
config = work / "config"
original = config.read_text()
try:
    config.write_text(original + f"\ncustom-shader = {shader}\ncustom-shader-animation = false\n")
    assert script(f'perform action "reload_config" on {target}') == "true"
    time.sleep(1)
    subprocess.run([str(client), str(pid), str(work / "pixels-shader-blue.png"), "shader-blue"],
                   check=True, timeout=10)
finally:
    config.write_text(original)
    assert script(f'perform action "reload_config" on {target}') == "true"
    time.sleep(1)
subprocess.run([str(client), str(pid), str(work / "pixels-shader-removed.png"), "blank"],
               check=True, timeout=10)
print("PASS: live custom-shader blue output and normal rendering after configuration removal", flush=True)

def chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


# A lossless solid PNG gives an unambiguous background-texture signal without
# depending on font rasterization, image interpolation or a reference screenshot.
png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress((b"\0" + bytes([0, 0, 255, 255]) * 2) * 2))
       + chunk(b"IEND", b""))
background = work / "pixels-background.png"
background.write_bytes(png)
try:
    config.write_text(original + f"\nbackground-image = {background}\n"
                      "background-image-fit = stretch\nbackground-image-opacity = 1\n")
    assert script(f'perform action "reload_config" on {target}') == "true"
    time.sleep(1)
    subprocess.run([str(client), str(pid), str(work / "pixels-background-blue.png"), "background-blue"],
                   check=True, timeout=10)
finally:
    config.write_text(original)
    assert script(f'perform action "reload_config" on {target}') == "true"
    time.sleep(1)
subprocess.run([str(client), str(pid), str(work / "pixels-background-removed.png"), "blank"],
               check=True, timeout=10)
print("PASS: PNG background load/display and normal rendering after configuration removal", flush=True)
