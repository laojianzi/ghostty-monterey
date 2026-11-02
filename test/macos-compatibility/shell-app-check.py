#!/usr/bin/env python3
"""Check automatic system-zsh integration through an isolated real app/PTY.

Only run via app-smoke.py --shell-integration. Does not source personal rc files
or invoke sudo/ssh. Prompt pixels, command-navigation keys, and physical input
remain separate acceptance checks.
"""

import pathlib
import plistlib
import shlex
import subprocess
import sys
import time


app, work = (pathlib.Path(arg).resolve() for arg in sys.argv[1:3])
info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
assert info["CFBundleIdentifier"] == "com.mitchellh.ghostty.monterey-smoke"


def literal(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def script(body):
    return subprocess.run(["osascript", "-"],
                          input=f"tell application {literal(app)}\n{body}\nend tell\n",
                          text=True, capture_output=True, timeout=15, check=True).stdout.strip()


def command(target, text):
    script(f'input text {literal(text)} to {target}\nsend key "enter" to {target}')


def wait_text(path):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.exists() and path.read_text().endswith("done\n"):
            return path.read_text().splitlines()[:-1]
        time.sleep(0.05)
    raise AssertionError(f"Shell did not finish {path.name}")


def wait_directory(target, directory):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        reported = script(f"return working directory of {target}")
        if reported and pathlib.Path(reported).resolve() == directory.resolve():
            return
        time.sleep(0.05)
    raise AssertionError(f"Shell did not report working directory {directory}: {reported}")


terminal = script("return id of focused terminal of selected tab of front window")
target = f"terminal id {literal(terminal)}"
output = work / "shell-integration-state"
command(target, "{ print -r -- $ZSH_VERSION $ZDOTDIR; "
        "print -r -- $+functions[_ghostty_precmd] $+functions[_ghostty_preexec]; "
        "print -r -- $precmd_functions; print -r -- $preexec_functions; "
        "print -r -- $TERM_PROGRAM $TERM; print done; } > " + shlex.quote(str(output)))
state = wait_text(output)
assert state[0].split()[0].startswith("5."), state
assert pathlib.Path(state[0].split(maxsplit=1)[1]).resolve() == work / "zsh-startup", state
assert state[1] == "1 1", state
assert "_ghostty_precmd" in state[2].split(), state
assert "_ghostty_preexec" in state[3].split(), state
assert state[4] == "ghostty xterm-ghostty", state

resources_output = work / "shell-resource-paths"
command(target, '{ print -r -- "$GHOSTTY_RESOURCES_DIR"; print -r -- "$TERMINFO"; '
        'print -r -- "$XDG_CACHE_HOME"; print -r -- "$XDG_STATE_HOME"; print done; } > '
        + shlex.quote(str(resources_output)))
paths = wait_text(resources_output)
assert len(paths) == 4, paths
assert pathlib.Path(paths[0]).resolve() == app / "Contents/Resources/ghostty", paths
assert pathlib.Path(paths[1]).resolve() == app / "Contents/Resources/terminfo", paths
assert pathlib.Path(paths[2]).resolve() == work / "xdg-cache", paths
assert pathlib.Path(paths[3]).resolve() == work / "xdg-state", paths
print("PASS: child uses this bundle's resources/terminfo and test-local XDG cache/state variables", flush=True)

# OSC 7 must reach the core and Swift surface, not just exist in shell variables.
directory = work / "shell directory 'quoted'"
directory.mkdir()
command(target, "cd -- " + shlex.quote(str(directory)))
wait_directory(target, directory)
try:
    for kind, create in (
        ("split", f"set t to split ({target}) direction right"),
        ("tab", "set newTab to new tab in front window\nset t to focused terminal of newTab"),
        ("window", "set w to new window\nset t to focused terminal of selected tab of w"),
    ):
        child = script(create + "\nreturn id of t")
        child_target = f"terminal id {literal(child)}"
        try:
            inherited = work / f"shell-inherited-directory-{kind}"
            command(child_target, "{ pwd -P; print done; } > " + shlex.quote(str(inherited)))
            values = wait_text(inherited)
            assert len(values) == 1 and pathlib.Path(values[0]).resolve() == directory.resolve(), (kind, values)
            wait_directory(child_target, directory)
        finally:
            script(f"close ({child_target})")
        assert script("return count of terminals") == "1", f"Leaked {kind} terminal"
finally:
    command(target, "cd -- " + shlex.quote(str(work)))
    wait_directory(target, work)
print("PASS: system zsh automatic hooks, isolated ZDOTDIR, OSC 7 cwd, split/tab/window cwd inheritance",
      flush=True)
