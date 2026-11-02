#!/usr/bin/env python3
"""Observe PTY-to-parser throughput in app-smoke's isolated app.

DSR replies fence parser consumption, not rendering or display presentation.
There is no performance pass threshold or upstream comparison in this probe.
"""

import hashlib
import json
import pathlib
import plistlib
import shlex
import subprocess
import sys
import time

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
pid = int(sys.argv[3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
with (app / "Contents/Info.plist").open("rb") as stream:
    info = plistlib.load(stream)
assert info["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.check_output(["osascript", "-"],
        input=f"tell application {literal(app)}\n{body}\nend tell",
        text=True, timeout=15).strip()


def measure():
    fields = subprocess.check_output(["ps", "-p", str(pid), "-o", "rss=,time="], text=True).split()
    assert len(fields) == 2, ("App exited", fields)
    days, separator, clock = fields[1].rpartition("-")
    cpu = float(days) * 86400 if separator else 0.0
    cpu += sum(float(part) * 60 ** index for index, part in enumerate(reversed(clock.split(":"))))
    return {"monotonic": time.monotonic(), "rss_kib": int(fields[0]), "cpu_seconds": cpu}


probe = work / "throughput-wire.py"
probe.write_text(r'''
import fcntl, json, os, pathlib, re, select, struct, sys, termios, time, tty
output, workload = pathlib.Path(sys.argv[1]), sys.argv[2]
lines = {
    "ascii": b"0123456789 abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ\r\n",
    "ansi": b"\x1b[38;2;120;180;220mcolored text\x1b[0m \x1b[1mbold\x1b[0m regular\r\n",
    "unicode": ("\u4e2d\u6587 \u65e5\u672c\u8a9e e\u0301 \U0001f680 \U0001f600 text\r\n").encode(),
}
line = lines[workload]
payload = line * ((4 * 1024 * 1024 + len(line) - 1) // len(line))
fd = os.open('/dev/tty', os.O_RDWR | os.O_NONBLOCK)
saved = termios.tcgetattr(fd)
result = {"ok": False, "workload": workload, "bytes": 0, "chunks": 0}
def write_all(data, deadline):
    view = memoryview(data)
    while view:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("PTY write deadline")
        if select.select([], [fd], [], min(remaining, 0.1))[1]:
            try:
                count = os.write(fd, view[:65536])
                if count <= 0:
                    raise RuntimeError("PTY stopped accepting bytes")
                view = view[count:]
            except BlockingIOError:
                pass
def fence(deadline):
    write_all(b'\x1b[6n', deadline)
    response = bytearray()
    while time.monotonic() < deadline:
        if select.select([fd], [], [], 0.1)[0]:
            response.extend(os.read(fd, 1024))
            if re.fullmatch(rb'\x1b\[\d+;\d+R', response):
                return response.decode()
            if len(response) > 128:
                raise RuntimeError(("Unexpected reply", bytes(response)))
    raise TimeoutError(("Parser fence deadline", bytes(response)))
try:
    tty.setraw(fd)
    result["winsize"] = struct.unpack('HHHH', fcntl.ioctl(fd, termios.TIOCGWINSZ, bytes(8)))
    # Fence setup/prompt output before starting the workload clock.
    result["initial_reply"] = fence(time.monotonic() + 5)
    started = time.monotonic()
    # Reuse one allocation; run long enough to observe more than startup bursts.
    # Cap both wall time and total traffic even on an unexpectedly fast host.
    while time.monotonic() - started < 2 and result["chunks"] < 128:
        write_all(payload, started + 25)
        result["bytes"] += len(payload)
        result["chunks"] += 1
    result["write_seconds"] = time.monotonic() - started
    result["final_reply"] = fence(started + 25)
    result["parser_seconds"] = time.monotonic() - started
    result["mib_per_second"] = result["bytes"] / 1048576 / result["parser_seconds"]
    result["ok"] = True
except BaseException as error:
    result["error"] = repr(error)
finally:
    termios.tcsetattr(fd, termios.TCSANOW, saved)
    os.close(fd)
    temporary = output.with_suffix('.pending')
    temporary.write_text(json.dumps(result))
    temporary.rename(output)
''')

report = {
    "app": str(app), "pid": pid, "commit": info.get("GhosttyCommit"),
    "executable_sha256": hashlib.sha256((app / "Contents/MacOS/ghostty").read_bytes()).hexdigest(),
    "host": subprocess.check_output(["sw_vers"], text=True),
    "architecture": subprocess.check_output(["uname", "-m"], text=True).strip(),
    "runs": [],
    "limits": "DSR fences parser consumption only. RSS is sampled, not peak allocation or GPU memory. "
              "CPU includes scripting/setup and ps sampling overhead. No upstream comparison or FPS claim.",
}
try:
    for round_index in range(3):
        for workload in ("ascii", "ansi", "unicode"):
            output = work / f"throughput-{round_index}-{workload}.json"
            command = shlex.join([sys.executable, str(probe), str(output), workload])
            before = measure()
            script(f'''set t to focused terminal of selected tab of front window
input text {literal(command)} to t
send key "enter" to t''')
            samples = [before]
            deadline = time.monotonic() + 35
            while not output.exists() and time.monotonic() < deadline:
                samples.append(measure())
                time.sleep(0.1)
            assert output.exists(), f"Missing PTY workload result: {workload}"
            after = measure()
            samples.append(after)
            result = json.loads(output.read_text())
            report["runs"].append({"round": round_index, "result": result, "samples": samples,
                "app_cpu_seconds": after["cpu_seconds"] - before["cpu_seconds"],
                "sampled_max_rss_kib": max(sample["rss_kib"] for sample in samples)})
            assert result["ok"], result
            print(json.dumps(report["runs"][-1], sort_keys=True), flush=True)
            # Let the shell regain its PTY before injecting the next command.
            time.sleep(0.3)
    print("PASS: nine bounded PTY workloads consumed and acknowledged; performance observations only", flush=True)
finally:
    (work / "throughput-resources.json").write_text(json.dumps(report, indent=2) + "\n")
