#!/usr/bin/env python3
"""Exercise configuration records through a running app's real AppleScript/PTY.

Only run against the isolated app prepared by app-smoke.py --automation.
Does not execute a user Shortcut or assert App Intents availability.
"""

import json
import pathlib
import plistlib
import shlex
import subprocess
import sys
import time


def apple_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


app = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(sys.argv[2]).resolve()
with (app / "Contents/Info.plist").open("rb") as stream:
    assert plistlib.load(stream)["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def script(body):
    result = subprocess.run(
        ["osascript", "-"],
        input=f"tell application {apple_string(app)}\n{body}\nend tell\n",
        text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


assert script("return count of windows") == "1", "Expected isolated initial window"
original_id = script("return id of focused terminal of selected tab of front window")
directory = work / "automation directory 'quoted'"
directory.mkdir()
probe = work / "automation-probe.py"
probe.write_text('''import json, os, pathlib, sys
result = {"cwd": os.getcwd(), "value": os.environ.get("GHOSTTY_MONTEREY_TEST"),
          "empty": os.environ.get("GHOSTTY_MONTEREY_EMPTY"), "tty": os.isatty(0)}
pathlib.Path(sys.argv[1]).write_text(json.dumps(result))
''')
value = "spaces 'quoted' = equal \\ slash"

# Each probe checks the child process, not only an echoed scripting record.
# Copy then mutate the record to prove value semantics across Apple events.
for location in ("window", "tab", "split"):
    output = work / f"automation-{location}.json"
    command = " ".join(shlex.quote(str(part)) for part in (sys.executable, probe, output))
    create = {
        "window": "set createdWindow to new window with configuration configured\n"
                  "set created to focused terminal of selected tab of createdWindow",
        "tab": "set createdTab to new tab in front window with configuration configured\n"
               "set created to focused terminal of createdTab",
        "split": "set created to split (focused terminal of selected tab of front window) "
                 "direction right with configuration configured",
    }[location]
    terminal_id = script(f'''
set base to new surface configuration
set initial working directory of base to {apple_string(directory)}
set environment variables of base to {{"GHOSTTY_MONTEREY_TEST=original"}}
set configured to new surface configuration from base
set environment variables of configured to {{{apple_string("GHOSTTY_MONTEREY_TEST=" + value)}, "GHOSTTY_MONTEREY_EMPTY="}}
set initial input of configured to {apple_string(command)} & linefeed
if (environment variables of base) is not {{"GHOSTTY_MONTEREY_TEST=original"}} then error "Record copy aliases original"
if (initial input of base) is not "" then error "Record copy changed original input"
{create}
if (tty of created) is "" then error "Missing created PTY"
return id of created
''')
    try:
        deadline = time.monotonic() + 10
        while not output.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert output.exists(), f"No child result for {location}"
        actual = json.loads(output.read_text())
        assert actual == {"cwd": str(directory), "value": value, "empty": "", "tty": True}, actual
        # The configured initial input must leave the original shell available.
        marker = work / f"automation-{location}-alive"
        script(f'''
set created to terminal id {apple_string(terminal_id)}
input text {apple_string("printf alive > " + shlex.quote(str(marker)))} to created
send key "enter" to created
''')
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists() and marker.read_text() == "alive", f"Shell lost after {location} initial input"
    finally:
        script(f"close (terminal id {apple_string(terminal_id)})")
    assert script("return count of windows") == "1", f"Window leak after {location}"
    assert script("return count of tabs of front window") == "1", f"Tab leak after {location}"
    assert script("return count of terminals of selected tab of front window") == "1", f"Split leak after {location}"
    assert script("return id of focused terminal of selected tab of front window") == original_id

print("PASS: AppleScript configuration copies, window/tab/split cwd/env/initial input and live PTYs")
