#!/usr/bin/env python3
"""Check first-tab identity in a freshly launched, isolated test app.

The app must have exactly one initial window. This closes its test tab only.
"""

import pathlib
import subprocess
import sys

app = str(pathlib.Path(sys.argv[1]).resolve())
app = app.replace("\\", "\\\\").replace('"', '\\"')
hidden = len(sys.argv) > 2 and sys.argv[2] == "hidden"
tab_count = "count of windows" if hidden else "count of tabs of front window"
subprocess.run(
    ["osascript", "-"],
    input=f'''
tell application "{app}"
    if (count of windows) is not 1 then error "Expected one initial test window"
    set w to front window
    set s to split (focused terminal of selected tab of w) direction right
    if (count of terminals of selected tab of front window) is not 2 then error "Split count"
    set t to new tab in w
    delay 0.2
    set tabID to id of t
    if ({tab_count}) is not 2 then error "Tab count"
    close tab t
    if tabID is "" then error "New tab has no identity"
    close s
    return "PASS: returned first-tab reference survives tab-group creation"
end tell
''',
    text=True,
    check=True,
)
