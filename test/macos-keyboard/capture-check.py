#!/usr/bin/env python3
"""Test recorder ownership/cleanup on private PTYs, not physical keyboard input."""

import json
import os
import pathlib
import pty
import select
import signal
import stat
import subprocess
import sys
import tempfile
import termios
import time

capture = pathlib.Path(__file__).with_name("capture.py")


def normalized_mode(fd):
    value = termios.tcgetattr(fd)
    # Darwin sets PENDIN on raw-to-canonical transitions: a kernel request to
    # reprocess queued input, not a changed user terminal-mode setting.
    value[3] &= ~getattr(termios, "PENDIN", 0)
    return value


with tempfile.TemporaryDirectory(prefix="ghostty-key-capture-") as directory:
    work = pathlib.Path(directory)
    for mode, stop in (("legacy", False), ("kitty", False), ("kitty", True)):
        master, slave = pty.openpty()
        original = normalized_mode(slave)
        output = work / f"{mode}-{stop}.jsonl"
        args = [sys.executable, str(capture), str(output), "--seconds", "1.5",
                "--protocol", mode, "--label", "synthetic fixture; not human acceptance"]
        process = subprocess.Popen(args, stdin=slave, stdout=slave, stderr=subprocess.PIPE)
        received = bytearray()

        def read_until(marker, timeout=5):
            deadline = time.monotonic() + timeout
            while marker not in received and time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    received.extend(os.read(master, 4096))
            assert marker in received, (received, process.poll())

        try:
            read_until(b"Wait for automatic completion.")
            payload = b"\x01\x03\x1b[97;5u" + "\U0001f680e\u0301\u4e2d\u6587".encode()
            os.write(master, payload)
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                records = [json.loads(line) for line in output.read_text().splitlines()]
                actual = b"".join(bytes.fromhex(row["hex"]) for row in records if row["type"] == "bytes")
                if actual == payload:
                    break
                time.sleep(0.01)
            assert actual == payload, (actual, payload)
            if stop:
                process.send_signal(signal.SIGTERM)
            assert process.wait(timeout=5) == (143 if stop else 0), process.stderr.read()
            read_until(b"terminal mode restored.")
            assert normalized_mode(slave) == original, ("PTY termios not restored", original, termios.tcgetattr(slave))
            assert received.count(b"\x1b[>31u") == (1 if mode == "kitty" else 0)
            assert received.count(b"\x1b[<u") == (1 if mode == "kitty" else 0)
            assert stat.S_IMODE(output.stat().st_mode) == 0o600
            records = [json.loads(line) for line in output.read_text().splitlines()]
            assert records[0]["type"] == "metadata" and records[-1]["type"] == "end"
            assert records[-1]["signal"] == (signal.SIGTERM if stop else None)
            before = output.read_bytes()
            result = subprocess.run(args, stdin=slave, capture_output=True, timeout=5)
            assert result.returncode != 0 and b"Output already exists" in result.stderr
            assert output.read_bytes() == before and normalized_mode(slave) == original
            print(f"PASS: {mode}, signal={stop}: exact bytes, protocol/mode cleanup, private file, no overwrite")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            os.close(master)
            os.close(slave)
    result = subprocess.run([sys.executable, str(capture), str(work / "non-tty"), "--label", "fixture"],
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert result.returncode != 0 and b"Run interactively" in result.stderr
    assert not (work / "non-tty").exists()
    print("PASS: noninteractive capture refused before file creation")
