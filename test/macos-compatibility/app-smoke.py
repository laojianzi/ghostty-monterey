#!/usr/bin/env python3
"""Launch an isolated copy of a built app and verify Monterey GUI/PTY basics.

Usage: python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app
Requires a logged-in GUI session. Artifacts remain in the printed temporary path.
Does not test physical keyboard events or Apple Silicon runtime. --pixels adds
a bounded compositor check, not complete visual acceptance.
"""

import argparse
import os
import pathlib
import plistlib
import shlex
import subprocess
import sys
import tempfile
import time


def apple_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=pathlib.Path)
parser.add_argument("--titlebar", choices=("native", "transparent", "tabs", "hidden"), default="transparent")
parser.add_argument("--fullscreen", choices=("false", "true", "visible-menu", "padded-notch"))
parser.add_argument("--fullscreen-tabs", action="store_true")
parser.add_argument("--clipboard-protocol", action="store_true")
parser.add_argument("--automation", action="store_true")
parser.add_argument("--automation-text", action="store_true", help="Read scrollback/viewport/selection through scripting")
parser.add_argument("--throughput", action="store_true", help="Observe bounded PTY/parser throughput and app resources")
parser.add_argument("--automation-policy", action="store_true", help="Verify live AppleScript disable/re-enable policy")
parser.add_argument("--services", action="store_true")
parser.add_argument("--renderer-stress", action="store_true")
parser.add_argument("--inspector", action="store_true")
parser.add_argument("--palette", action="store_true", help="Check the actual command palette through existing AX permission")
parser.add_argument("--lifecycle", action="store_true", help="Measure repeated terminal creation/expiry resource recovery")
parser.add_argument("--pixels", action="store_true", help="Capture only the test window and verify rendered color blocks")
parser.add_argument("--shell-integration", action="store_true",
                    help="Use system zsh with isolated startup files and check automatic integration")
args = parser.parse_args()
if args.pixels and args.renderer_stress:
    parser.error("--pixels requires a plain background; do not combine with --renderer-stress")
if args.fullscreen_tabs and (args.fullscreen is None or args.titlebar == "hidden"):
    parser.error("--fullscreen-tabs requires --fullscreen and a tab-capable titlebar")
source = args.app.resolve()
assert (source / "Contents/MacOS/ghostty").is_file(), "Expected a built Ghostty.app"
work = pathlib.Path(tempfile.mkdtemp(prefix="ghostty-monterey-smoke-", dir="/tmp"))
print(f"Artifacts: {work}", flush=True)
app = work / "Ghostty.app"
subprocess.run(["ditto", "--norsrc", str(source), str(app)], check=True)
info_path = app / "Contents/Info.plist"
with info_path.open("rb") as stream:
    info = plistlib.load(stream)
# A stable test-only identifier avoids asking for new Automation permission on
# every run. It is separate from the installed app's preferences/restoration.
info["CFBundleIdentifier"] = "com.mitchellh.ghostty.monterey-smoke"
info["SUEnableAutomaticChecks"] = False
if args.services:
    for service in info["NSServices"]:
        service["NSMenuItem"] = {"default": f"Ghostty Test {work.name} {service['NSMessage']}"}
with info_path.open("wb") as stream:
    plistlib.dump(info, stream)
subprocess.run(
    ["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)],
    check=True,
)
subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
config = work / "config"
shell_config = ("shell-integration = detect\ncommand = /bin/zsh\n" if args.shell_integration else
                "shell-integration = none\ncommand = /bin/sh\n")
config.write_text(
    "auto-update = off\nwindow-save-state = never\nconfirm-close-surface = false\n"
    "macos-applescript = true\n" + shell_config + "undo-timeout = 5s\n"
    "quick-terminal-autohide = false\n"
    f"macos-titlebar-style = {args.titlebar}\n"
    f"working-directory = {work}\n"
)
shell_env = {}
if args.shell_integration:
    zdotdir = work / "zsh-startup"
    zdotdir.mkdir()
    # Ghostty restores this directory before sourcing .zshenv. Avoid personal
    # startup files and subsequent global rc files; keep local .zshrc enabled.
    (zdotdir / ".zshenv").write_text("unsetopt GLOBAL_RCS\n")
    (zdotdir / ".zshrc").write_text("PROMPT='monterey-test%# '\nHISTFILE=/dev/null\n")
    shell_env = {"ZDOTDIR": str(zdotdir)}
if args.fullscreen is not None:
    with config.open("a") as stream:
        stream.write(f"macos-non-native-fullscreen = {args.fullscreen}\n")
if args.clipboard_protocol:
    with config.open("a") as stream:
        stream.write("clipboard-read = deny\nclipboard-write = deny\n")
if args.renderer_stress:
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("renderer-app-check.py")),
                    str(app), str(config), str(work), "--prepare"], check=True)


def script(body):
    result = subprocess.run(
        ["osascript", "-"],
        input=f"tell application {apple_string(app)}\n{body}\nend tell\n",
        text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def wait_for_file(path, process):
    deadline = time.monotonic() + 10
    while not path.exists() and time.monotonic() < deadline:
        assert process.poll() is None, f"App exited while waiting for {path.name}"
        time.sleep(0.05)
    assert path.exists(), f"Timed out waiting for {path.name}"


log_path = work / "launch.log"
# Do not let the launching terminal supply resources from an installed app or
# inject a shell startup/debug library into this supposedly isolated bundle.
launch_env = dict(os.environ)
for key in ("GHOSTTY_RESOURCES_DIR", "GHOSTTY_BIN_DIR", "GHOSTTY_SHELL_INTEGRATION",
            "TERMINFO", "TERMINFO_DIRS", "ZDOTDIR", "ENV", "BASH_ENV",
            "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
            "MTL_DEBUG_LAYER", "GHOSTTY_LOG"):
    launch_env.pop(key, None)
launch_env.update(shell_env)
launch_env.update({"XDG_CONFIG_HOME": str(work / "xdg-config"),
                   "XDG_CACHE_HOME": str(work / "xdg-cache"),
                   "XDG_STATE_HOME": str(work / "xdg-state")})
if args.renderer_stress or args.inspector:
    launch_env.update({"MTL_DEBUG_LAYER": "1", "GHOSTTY_LOG": "stderr"})
elif args.shell_integration:
    launch_env["GHOSTTY_LOG"] = "stderr"
with log_path.open("w") as log:
    process = subprocess.Popen(
        [str(app / "Contents/MacOS/ghostty"), "--config-default-files=false",
         f"--config-file={config}"],
        cwd=work, stdout=log, stderr=subprocess.STDOUT,
        env=launch_env,
    )
    try:
        # Avoid sending an activation event that could launch a second instance
        # without our isolation arguments. Cocoa scripting is ready after startup.
        time.sleep(2)
        assert process.poll() is None, "App exited during startup"
        assert script("return count of windows") == "1", "Expected one initial window"
        if args.shell_integration:
            subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("shell-app-check.py")),
                 str(app), str(work)], check=True, timeout=60,
            )
        if args.services:
            subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("services-app-check.py")),
                 str(app), str(work)], check=True, timeout=90,
            )
        if args.automation:
            subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("automation-check.py")),
                 str(app), str(work)], check=True, timeout=90,
            )
        if args.automation_text:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("automation-text-check.py")),
                            str(app), str(work)], check=True, timeout=60)
        if args.throughput:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("throughput-app-check.py")),
                            str(app), str(work), str(process.pid)], check=True, timeout=300)
        if args.automation_policy:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("automation-policy-check.py")),
                            str(app), str(work), str(process.pid)], check=True, timeout=60)
        if args.clipboard_protocol:
            subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("clipboard-protocol-check.py")),
                 str(app), str(config), str(work)], check=True, timeout=60,
            )
        if args.renderer_stress:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("renderer-app-check.py")),
                            str(app), str(config), str(work)], check=True, timeout=120)
        if args.inspector:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("inspector-app-check.py")),
                            str(app), str(work)], check=True, timeout=90)
        if args.palette:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("palette-app-check.py")),
                            str(app), str(work), str(process.pid)], check=True, timeout=90)
        if args.lifecycle:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("lifecycle-app-check.py")),
                            str(app), str(work), str(process.pid)], check=True, timeout=120)
        if args.pixels:
            subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("pixels-app-check.py")),
                            str(app), str(work), str(process.pid)], check=True, timeout=60)
        result_path = work / "pty-result"
        command = f"printf 'monterey-pty-ok\\n' > '{result_path}'"
        script(f'''
set t to focused terminal of selected tab of front window
if tty of t is "" then error "Missing PTY"
input text {apple_string(command)} to t
send key "enter" to t
''')
        wait_for_file(result_path, process)
        assert result_path.read_text() == "monterey-pty-ok\n", "PTY command failed"

        # Read the actual PTY bytes in raw mode: ISIG/IXON must not consume
        # control characters before the assertion. This exercises the scripting
        # synthesis -> core key encoder -> PTY path, not AppKit event dispatch.
        reader = work / "read-keys.py"
        reader.write_text('''
import os, pathlib, select, termios, time, tty
fd = 0
original = termios.tcgetattr(fd)
try:
    tty.setraw(fd)
    pathlib.Path("keys-ready").touch()
    data = bytearray()
    deadline = time.monotonic() + 10
    while len(data) < 12 and time.monotonic() < deadline:
        if select.select([fd], [], [], 0.1)[0]:
            data.extend(os.read(fd, 1024))
    pathlib.Path("keys-result").write_bytes(data)
finally:
    termios.tcsetattr(fd, termios.TCSANOW, original)
''')
        reader_command = f"{shlex.quote(sys.executable)} {shlex.quote(str(reader))}"
        script(f'''
set t to focused terminal of selected tab of front window
input text {apple_string(reader_command)} to t
send key "enter" to t
''')
        wait_for_file(work / "keys-ready", process)
        script('''
set t to focused terminal of selected tab of front window
send key "a" modifiers "control" to t
send key "c" modifiers "control" to t
send key "d" modifiers "control" to t
send key "s" modifiers "control" to t
send key "q" modifiers "control" to t
send key "z" modifiers "control" to t
input text "\u4e2d\u6587" to t
''')
        wait_for_file(work / "keys-result", process)
        expected = bytes([1, 3, 4, 19, 17, 26]) + "\u4e2d\u6587".encode()
        received = (work / "keys-result").read_bytes()
        assert received == expected, f"PTY encoding: {received.hex()} != {expected.hex()}"
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).with_name("tab-reference.py")), str(app), args.titlebar],
            check=True, timeout=20,
        )
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).with_name("reopen-check.py")), str(app), args.titlebar],
            check=True, timeout=25,
        )
        # Retained closed terminals must release their PTY children after the
        # configured undo window, rather than running forever in the background.
        closed_pid = int(script('''
set original to focused terminal of selected tab of front window
set temporary to split original direction right
delay 0.3
set childPID to pid of temporary
close temporary
return childPID
'''))
        assert closed_pid > 1
        os.kill(closed_pid, 0)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                os.kill(closed_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            state = subprocess.run(["ps", "-p", str(closed_pid), "-o", "pid,ppid,stat,etime,command"],
                                   text=True, capture_output=True)
            (work / "undo-expiry-process.txt").write_text(state.stdout + state.stderr)
            subprocess.run(["sample", str(process.pid), "1", "-file", str(work / "undo-expiry-sample.txt")],
                           capture_output=True, timeout=15)
            try:
                diagnostic = script('''
set beforeCount to count of terminals
set t to focused terminal of selected tab of front window
set handled to perform action "undo" on t
delay 0.2
return {beforeCount, handled, count of terminals}
''')
                (work / "undo-expiry-action.txt").write_text(diagnostic)
            except Exception as error:
                (work / "undo-expiry-action.txt").write_text(repr(error))
            raise AssertionError(f"Closed terminal child survived undo expiration: {state.stdout.strip()}")
        subprocess.run(
            [sys.executable, str(pathlib.Path(__file__).with_name("quick-terminal-check.py")), str(app), str(process.pid)],
            check=True, timeout=25,
        )
        if args.fullscreen is not None:
            subprocess.run(
                [sys.executable, str(pathlib.Path(__file__).with_name("fullscreen-check.py")),
                 str(app), str(process.pid), args.fullscreen,
                 *(["--tabs"] if args.fullscreen_tabs else [])], check=True, timeout=90,
            )
        # This build has no distributor feed. Manual update requests must remain
        # responsive and explain the unavailable service, not invoke upstream.
        # The policy suite separately tests source/key rejection; this smoke
        # check alone is not a network or update-installation assertion.
        if not info.get("SUPublicEDKey"):
            assert script('''
set t to focused terminal of selected tab of front window
return perform action "check_for_updates" on t
''') == "true", "Manual update action was not handled"
        script('''
if (count of windows) is not 1 then error "Window count after close"
if (count of tabs of front window) is not 1 then error "Tab count after close"
if (count of terminals of selected tab of front window) is not 1 then error "Split count after close"
quit
''')
        assert process.wait(timeout=10) == 0, "App quit unsuccessfully"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

log_text = log_path.read_text()
if args.shell_integration:
    assert "shell integration automatically injected shell=.zsh" in log_text, log_text
assert "constant that exceeds internal limits" not in log_text, log_text
assert "Can't have a toolbar" not in log_text, log_text
assert "failed assertion" not in log_text, log_text
assert "Validation Error" not in log_text, log_text
if args.renderer_stress or args.inspector:
    assert "Metal API Validation Enabled" in log_text, log_text
    assert "ghostty version=" in log_text, "Core stderr logging was not enabled"
    assert "error rendering inspector" not in log_text.lower(), log_text
if args.renderer_stress:
    for index in range(2):
        assert f"loaded custom shader path={work}/renderer-{index}.glsl" in log_text, log_text
    # A locked/headless session can lack a display link; upstream uses its
    # event-driven fallback. Do not silently accept other renderer failures.
    renderer_scopes = ("generic_renderer", "metal", "shadertoy")
    for line in log_text.splitlines():
        if any(f"warning({scope})" in line or f"error({scope})" in line for scope in renderer_scopes):
            assert "error creating display link; using fallback rendering" in line, line
assert not list(work.glob("*.profraw")), "Release app emitted profiling data"
print(f"PASS ({args.titlebar}): startup, PTY/control/UTF-8, split/tab/window undo/redo, TTL cleanup, quit, layout log")
