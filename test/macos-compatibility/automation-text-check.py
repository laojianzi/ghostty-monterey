#!/usr/bin/env python3
"""Read real PTY output via scripting, without AX or clipboard access.

Only run against app-smoke's disposable bundle. A child emits enough lines to
separate scrollback from the viewport; its command line contains none of the
expected markers. Queries poll through the production text-cache lifetime.
"""

import pathlib
import plistlib
import shlex
import subprocess
import sys
import time

app, work = (pathlib.Path(value).resolve() for value in sys.argv[1:3])
assert app.parent == work and work.name.startswith("ghostty-monterey-smoke-")
assert plistlib.loads((app / "Contents/Info.plist").read_bytes())["CFBundleIdentifier"] == (
    "com.mitchellh.ghostty.monterey-smoke")


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    result = subprocess.run(["osascript", "-"],
        input=f"tell application {literal(app)}\n{body}\nend tell", text=True,
        capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return result.stdout.rstrip("\n")


terminal = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(terminal)}"
# Fail before sending input if the bundle does not expose the new dictionary.
for prop in ("full contents", "visible text", "selected text"):
    script(f"return {prop} of {target}")

first = "MONTEREY-SCROLLBACK-FIRST"
last = "MONTEREY-VIEWPORT-LAST-\U0001f680-e\u0301-\u4e2d\u6587"
probe = work / "text-output.py"
probe.write_text("import os\n"
                 "os.write(1, b'\\x1b[2J\\x1b[H')\n"
                 f"print({first!r})\n"
                 "for i in range(300): print('scrollback-row-%03d' % i)\n"
                 f"print({last!r}, flush=True)\n")
command = " ".join(shlex.quote(str(part)) for part in (sys.executable, probe))
script(f'input text {literal(command)} to {target}\nsend key "enter" to {target}')


def wait_for(check):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.1)
    raise AssertionError("Terminal text did not reach the expected state")


def check_output():
    full = script(f"return full contents of {target}")
    visible = script(f"return visible text of {target}")
    return (first in full and last in full and last in visible and first not in visible
            and "scrollback-row-150" in full and "scrollback-row-150" not in visible)


wait_for(check_output)
script(f'perform action "select_all" on {target}')
wait_for(lambda: first in script(f"return selected text of {target}")
         and last in script(f"return selected text of {target}"))
# Escape clears the selection; do not read or write the user's pasteboard.
script(f'send key "escape" to {target}')
wait_for(lambda: script(f"return selected text of {target}") == "")
# Escape can also reach the shell's line editor. Cancel that input before the
# next probe, rather than leaving a pending escape sequence in the shared PTY.
script(f'send key "c" modifiers "control" to {target}')
print("PASS: scripting reads scrollback, distinct viewport, Unicode selection and cleared selection")
