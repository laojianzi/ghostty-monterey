#!/usr/bin/env python3
"""Manually record bytes delivered to this terminal's PTY for a bounded interval.

Run inside the Ghostty build under test, never against another process/device.
Does not install hooks, inject input, switch layouts, or change permissions.
Output is sensitive: type only test inputs, never passwords or personal text.
Read chunks are not physical key-event boundaries or parsed Kitty events.
"""

import argparse
import datetime
import json
import os
import pathlib
import select
import signal
import sys
import termios
import time
import tty


def capture(fd, output, seconds, protocol, label):
    original = termios.tcgetattr(fd)
    previous_handlers = {}
    stop_signal = None
    pushed = False
    started = time.monotonic()

    def stop(number, _frame):
        nonlocal stop_signal
        stop_signal = number

    def record(value):
        output.write(json.dumps(value, ensure_ascii=True) + "\n")
        output.flush()

    record({"type": "metadata", "format": 1, "label": label, "protocol": protocol,
            "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "system": list(os.uname()), "tty": os.ttyname(fd), "seconds": seconds,
            "term": os.environ.get("TERM"), "term_program": os.environ.get("TERM_PROGRAM"),
            "term_program_version": os.environ.get("TERM_PROGRAM_VERSION"),
            "limitation": "PTY read chunks, not key events; environment is not binary identity proof"})
    try:
        for number in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            previous_handlers[number] = signal.signal(number, stop)
        # TCSANOW avoids discarding queued input during entry or restoration.
        tty.setraw(fd, when=termios.TCSANOW)
        if protocol == "kitty":
            os.write(fd, b"\x1b[>31u")
            pushed = True
        os.write(fd, b"\r\nCapture active; type only test inputs. Wait for automatic completion.\r\n")
        started = time.monotonic()
        while stop_signal is None:
            remaining = seconds - (time.monotonic() - started)
            if remaining <= 0:
                break
            ready, _, _ = select.select([fd], [], [], min(remaining, 0.1))
            if not ready:
                continue
            data = os.read(fd, 4096)
            if not data:
                break
            record({"type": "bytes", "elapsed_ns": int((time.monotonic() - started) * 1e9),
                    "hex": data.hex(), "length": len(data)})
    finally:
        try:
            if pushed:
                os.write(fd, b"\x1b[<u")
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSANOW, original)
            finally:
                for number, handler in previous_handlers.items():
                    signal.signal(number, handler)
    record({"type": "end", "elapsed_seconds": time.monotonic() - started, "signal": stop_signal})
    os.write(fd, b"\r\nCapture finished; terminal mode restored.\r\n")
    return 128 + stop_signal if stop_signal else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=pathlib.Path, help="New JSONL file; refuses overwrite")
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--protocol", choices=("legacy", "kitty"), default="legacy")
    parser.add_argument("--label", required=True, help="Build revision, layout, option-as-alt and planned keys")
    args = parser.parse_args()
    if not 0 < args.seconds <= 300:
        parser.error("Capture duration must be greater than zero and at most 300 seconds")
    if not os.isatty(sys.stdin.fileno()):
        parser.error("Run interactively inside the terminal under test")
    # Read/write one terminal only. Never infer or open another app's PTY.
    fd = os.open(os.ttyname(sys.stdin.fileno()), os.O_RDWR | os.O_NOCTTY)
    try:
        try:
            output_fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            parser.error("Output already exists; choose a new path")
        with os.fdopen(output_fd, "w") as output:
            return capture(fd, output, args.seconds, args.protocol, args.label)
    finally:
        os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
