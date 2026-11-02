#!/usr/bin/env python3
"""Exercise image/shader configuration and Kitty wire traffic in the isolated app.

This is API-validation/liveness evidence, not a screen-pixel assertion.
"""

import json
import pathlib
import plistlib
import shlex
import struct
import subprocess
import sys
import time
import zlib

app, config, work = map(pathlib.Path, sys.argv[1:4])
with (app / "Contents/Info.plist").open("rb") as stream:
    assert plistlib.load(stream)["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"
assert config.parent == work and work.name.startswith("ghostty-monterey-smoke-")

if "--prepare" in sys.argv:
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    pixels = b"".join(b"\0" + b"".join(bytes([x * 16, y * 16, 128, 192])
                                     for x in range(16)) for y in range(16))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 16, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")
    (work / "renderer.png").write_bytes(png)
    for index in range(2):
        (work / f"renderer-{index}.glsl").write_text("""
void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = texture(iChannel0, uv);
}
""")
    with config.open("a") as stream:
        stream.write(f"background-image = {work / 'renderer.png'}\nbackground-image-opacity = 0.5\n"
                     "background-image-fit = contain\nbackground-image-repeat = true\n"
                     "background-opacity = 0.9\ncustom-shader-animation = false\n"
                     f"custom-shader = {work / 'renderer-0.glsl'}\n"
                     f"custom-shader = {work / 'renderer-1.glsl'}\n")
    sys.exit(0)


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.run(["osascript", "-"], input=f"tell application {literal(app)}\n{body}\nend tell",
                          text=True, capture_output=True, timeout=15, check=True).stdout.strip()


probe = work / "renderer-wire.py"
probe.write_text(r'''
import base64, json, os, pathlib, re, select, sys, termios, time, tty
output, stage = sys.argv[1:]
fd = os.open('/dev/tty', os.O_RDWR)
saved = termios.tcgetattr(fd)
packets = []
pending = bytearray()
def request(command, ident, payload=b''):
    os.write(fd, b'\x1b_G' + command.encode() + b';' + base64.b64encode(payload) + b'\x1b\\')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        match = re.search(rb'\x1b_G([^\x1b]*)\x1b\\', pending)
        if match:
            packet = bytes(match[0])
            del pending[:match.end()]
            assert packet == f'\x1b_Gi={ident};OK\x1b\\'.encode(), packet
            packets.append(packet.decode())
            return
        if select.select([fd], [], [], 0.1)[0]:
            pending.extend(os.read(fd, 65536))
    raise AssertionError(('Kitty response timeout', bytes(pending)))
try:
    tty.setraw(fd)
    # Unicode text exercises the real font/atlas route in addition to images.
    os.write(fd, ('\r\nMonterey ' + chr(0x4e2d) + chr(0x6587) + ' e\u0301 ' + chr(0x1f680) + '\r\n').encode())
    rgba = bytes([255, 32, 96, 128]) * 16 * 16
    request('a=T,f=32,s=16,v=16,i=71,c=4,r=2,q=0', 71, rgba)
    # Retransmitting the ID replaces the image and removes its old placements.
    request('a=t,f=32,s=16,v=16,i=71,q=0', 71, bytes([32, 128, 255, 192]) * 256)
    png = pathlib.Path(__file__).with_name('renderer.png').read_bytes()
    request('a=T,f=100,i=72,c=4,r=2,q=0', 72, png)
    # Render-thread work is asynchronous; allow it to observe live placements.
    time.sleep(0.6)
    os.write(fd, b'\x1b_Ga=d,d=A,q=2\x1b\\')
    if select.select([fd], [], [], 0.2)[0]:
        pending.extend(os.read(fd, 65536))
    assert not pending, ('Unexpected terminal bytes', bytes(pending))
    pathlib.Path(output).write_text(json.dumps({'ok': True, 'packets': packets}))
except BaseException as error:
    pathlib.Path(output).write_text(json.dumps({'ok': False, 'error': repr(error), 'packets': packets}))
finally:
    termios.tcsetattr(fd, termios.TCSANOW, saved)
    os.close(fd)
''')

original = config.read_text()
try:
    for blending in ("native", "linear", "linear-corrected"):
        config.write_text(original + f"alpha-blending = {blending}\n")
        assert script('perform action "reload_config" on focused terminal of selected tab of front window') == "true"
        time.sleep(0.7)
        output = work / f"renderer-{blending}.json"
        command = shlex.join([sys.executable, str(probe), str(output), blending])
        script(f'''set t to focused terminal of selected tab of front window
input text {literal(command)} to t
send key "enter" to t''')
        deadline = time.monotonic() + 25
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert output.exists(), f"Missing {blending} PTY result"
        result = json.loads(output.read_text())
        assert result["ok"] and len(result["packets"]) == 3, result
        print(f"PASS: {blending}: raw/PNG Kitty transfer+placement, replacement, cleanup, Unicode PTY", flush=True)
finally:
    config.write_text(original)
    script('perform action "reload_config" on focused terminal of selected tab of front window')
