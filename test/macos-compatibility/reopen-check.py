#!/usr/bin/env python3
"""Verify live split/tab/window close/undo/redo retains terminal identity and PID.

Run only against an already running, isolated test app with one initial terminal.
"""

import pathlib
import subprocess
import sys

app = str(pathlib.Path(sys.argv[1]).resolve()).replace("\\", "\\\\").replace('"', '\\"')
hidden = len(sys.argv) > 2 and sys.argv[2] == "hidden"
tab_count = "count of windows" if hidden else "count of tabs of front window"
subprocess.run(["osascript", "-"], input=f'''
tell application "{app}"
    if (count of terminals) is not 1 then error "Expected one isolated terminal"
    set original to focused terminal of selected tab of front window
    set restored to split original direction right
    delay 0.3
    set savedID to id of restored
    set savedPID to pid of restored
    set savedTTY to tty of restored
    if savedPID is 0 or savedTTY is "" then error "Split has no running PTY"
    close restored
    delay 0.2
    if (count of terminals) is not 1 then error "Split close failed"
    if not (perform action "undo" on original) then error "Undo action rejected"
    delay 0.3
    if (count of terminals) is not 2 then error "Split undo failed"
    set restored to terminal id savedID
    if pid of restored is not savedPID then error "Undo restarted the child process"
    if tty of restored is not savedTTY then error "Undo replaced the PTY"
    if not (perform action "redo" on original) then error "Redo action rejected"
    delay 0.2
    if (count of terminals) is not 1 then error "Split redo failed"
    if not (perform action "undo" on original) then error "Second undo action rejected"
    delay 0.3
    if (count of terminals) is not 2 then error "Second split undo failed"
    set restored to terminal id savedID
    if pid of restored is not savedPID then error "Second undo restarted the child"
    close restored
    delay 0.2

    set createdTab to new tab in front window
    delay 0.3
    set tabTerminal to focused terminal of createdTab
    set savedID to id of tabTerminal
    set savedPID to pid of tabTerminal
    set savedTTY to tty of tabTerminal
    if not (perform action "close_tab:this" on tabTerminal) then error "Close tab action rejected"
    delay 0.2
    if ({tab_count}) is not 1 then error "Tab close failed"
    if not (perform action "undo" on original) then error "Tab undo action rejected"
    delay 0.3
    if ({tab_count}) is not 2 then error "Tab undo failed"
    set tabTerminal to terminal id savedID
    if pid of tabTerminal is not savedPID or tty of tabTerminal is not savedTTY then error "Tab undo replaced child/PTY"
    if not (perform action "redo" on tabTerminal) then error "Tab redo action rejected"
    delay 0.2
    if ({tab_count}) is not 1 then error "Tab redo failed"

    set createdWindow to new window
    delay 0.3
    set windowTerminal to focused terminal of selected tab of createdWindow
    set savedID to id of windowTerminal
    set savedPID to pid of windowTerminal
    set savedTTY to tty of windowTerminal
    close window createdWindow
    delay 0.2
    if (count of windows) is not 1 then error "Window close failed"
    if not (perform action "undo" on original) then error "Window undo action rejected"
    delay 0.3
    if (count of windows) is not 2 then error "Window undo failed: windows=" & (count of windows) & ", terminals=" & (count of terminals) & ", tabs=" & (count of tabs of front window)
    set windowTerminal to terminal id savedID
    if pid of windowTerminal is not savedPID or tty of windowTerminal is not savedTTY then error "Window undo replaced child/PTY"
    if not (perform action "redo" on windowTerminal) then error "Window redo action rejected"
    delay 0.2
    if (count of windows) is not 1 then error "Window redo failed"
    return "PASS: split/tab/window close/undo/redo preserves surface ID, running process and PTY"
end tell
''', text=True, check=True, timeout=20)
