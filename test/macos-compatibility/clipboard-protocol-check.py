#!/usr/bin/env python3
"""Probe OSC 5522 through an isolated app's PTY without accessing user clipboard data.

Requires app-smoke.py --clipboard-protocol. Standard reads/writes are denied;
the allow-policy stage targets only macOS's unsupported primary clipboard.
"""

import json
import pathlib
import shlex
import subprocess
import sys
import time

app, config, work = map(pathlib.Path, sys.argv[1:4])


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    result = subprocess.run(["osascript", "-"],
                            input=f"tell application {literal(app)}\n{body}\nend tell",
                            text=True, capture_output=True, timeout=15, check=True)
    return result.stdout.strip()


reader = work / "clipboard-wire.py"
reader.write_text(r'''
import base64, json, os, pathlib, re, select, sys, termios, time, tty
stage, output = sys.argv[1:]
fd = os.open('/dev/tty', os.O_RDWR)
original = termios.tcgetattr(fd)
results = []
buffer = bytearray()
def receive():
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        match = re.search(rb'\x1b\]5522;([^\x07]*?)(\x1b\\|\x07)', buffer)
        if match:
            packet = bytes(match[0])
            del buffer[:match.end()]
            return packet
        if select.select([fd], [], [], 0.1)[0]:
            buffer.extend(os.read(fd, 65536))
    raise AssertionError('no OSC 5522 response: ' + repr(buffer))
def request(op, ident, terminator):
    location = ':loc=primary' if stage != 'deny' else ''
    metadata = f'type={op}:id={ident}{location}'
    if op == 'read':
        packets = [f'\x1b]5522;{metadata};' + base64.b64encode(b'text/plain').decode() + terminator]
    else:
        packets = [f'\x1b]5522;{metadata}' + terminator,
                   '\x1b]5522;type=wdata:mime=dGV4dC9wbGFpbg==;cHJvdG9jb2wtdGVzdA==' + terminator,
                   '\x1b]5522;type=wdata' + terminator]
    os.write(fd, ''.join(packets).encode())
    packet = receive()
    expected = 'EPERM' if stage == 'deny' else 'ENOSYS'
    assert packet == f'\x1b]5522;type={op}:status={expected}:id={ident}{terminator}'.encode(), packet
    results.append(packet.decode())
try:
    tty.setraw(fd)
    for op in ('read', 'write'):
        for label, terminator in (('st', '\x1b\\'), ('bel', '\x07')):
            if stage != 'limits':
                request(op, op + '-' + label, terminator)
    if stage == 'limits':
        for ident, payload, expected in [('oversize', base64.b64encode(b'x' * 17).decode(), 'EFBIG'),
                                         ('malformed', '!!!!', 'EINVAL')]:
            wire = (f'\x1b]5522;type=write:id={ident}:loc=primary\x1b\\'
                    f'\x1b]5522;type=wdata:mime=dGV4dC9wbGFpbg==;{payload}\x1b\\'
                    '\x1b]5522;type=wdata\x1b\\')
            os.write(fd, wire.encode())
            packet = receive()
            assert packet == f'\x1b]5522;type=write:status={expected}:id={ident}\x1b\\'.encode(), packet
            results.append(packet.decode())
        # A failed write must not poison the next well-formed transaction.
        request('write', 'recovery', '\x1b\\')
    # Reject duplicate statuses or stray data left over for the shell to consume.
    if select.select([fd], [], [], 0.2)[0]:
        buffer.extend(os.read(fd, 65536))
    assert not buffer, ('unexpected trailing terminal bytes', bytes(buffer))
    pathlib.Path(output).write_text(json.dumps({'ok': True, 'packets': results}))
except BaseException as error:
    pathlib.Path(output).write_text(json.dumps({'ok': False, 'error': repr(error), 'packets': results}))
finally:
    termios.tcsetattr(fd, termios.TCSANOW, original)
    os.close(fd)
''')

original_config = config.read_text()
assert "clipboard-read = deny" in original_config and "clipboard-write = deny" in original_config
try:
    for stage in ("deny", "primary", "limits"):
        if stage != "deny":
            config.write_text(original_config + "clipboard-read = allow\nclipboard-write = allow\n" +
                              ("clipboard-write-limit-bytes = 16\n" if stage == "limits" else ""))
            assert script('perform action "reload_config" on focused terminal of selected tab of front window') == "true"
            time.sleep(0.5)
        output = work / f"clipboard-{stage}.json"
        command = shlex.join([sys.executable, str(reader), stage, str(output)])
        script(f'''
set t to focused terminal of selected tab of front window
input text {literal(command)} to t
send key "enter" to t
''')
        deadline = time.monotonic() + 25
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert output.exists(), f"No result from {stage} PTY probe"
        result = json.loads(output.read_text())
        assert result["ok"], result
        assert len(result["packets"]) == (3 if stage == "limits" else 4), result
        print(f"PASS: OSC 5522 {stage}: {len(result['packets'])} validated wire replies", flush=True)
        time.sleep(0.3)
finally:
    config.write_text(original_config)
    script('perform action "reload_config" on focused terminal of selected tab of front window')
