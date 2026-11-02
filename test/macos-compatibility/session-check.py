#!/usr/bin/env python3
"""Check AppKit session restoration in an isolated copy, never the installed app.

Creates test-only preferences/restoration state under a dedicated bundle ID.
Leaves artifacts on failure for diagnosis. Does not claim shell-process survival:
unlike undo, a full app restart necessarily creates new PTYs and processes.
"""

import argparse
import json
import os
import pathlib
import plistlib
import re
import signal
import subprocess
import tempfile
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("app", type=pathlib.Path)
parser.add_argument("--titlebar", choices=("native", "transparent", "tabs"), default="transparent")
parser.add_argument("--selected-tab", choices=("alpha", "beta"), default="alpha")
parser.add_argument("--front-window", choices=("standalone", "tabbed"), default="standalone")
parser.add_argument("--launch-via", choices=("direct", "launchservices"), default="direct")
parser.add_argument("--fixed-window-geometry", action="store_true",
                    help="Use explicit non-maximized dimensions/position rather than saved defaults")
parser.add_argument("--replace-fullscreen-tab", action="store_true",
                    help="Replace beta while its group is native fullscreen before saving")
parser.add_argument("--fullscreen", choices=("false", "true", "visible-menu", "padded-notch"),
                    help="macos-non-native-fullscreen value; false selects native fullscreen")
parser.add_argument("--minimized-tabs", action="store_true", help="Debug-only LLDB-assisted minimized session probe")
args = parser.parse_args()
if args.replace_fullscreen_tab and (args.fullscreen != "false" or args.front_window != "tabbed" or
                                    args.selected_tab != "beta"):
    parser.error("--replace-fullscreen-tab requires native fullscreen, tabbed front window and selected beta")
if args.minimized_tabs and (args.fullscreen or args.front_window != "standalone"):
    parser.error("--minimized-tabs requires a standalone front window and no --fullscreen")
if args.minimized_tabs:
    entitlements = subprocess.check_output(["codesign", "-d", "--entitlements", ":-", str(args.app)],
                                          stderr=subprocess.DEVNULL)
    if not plistlib.loads(entitlements.rstrip(b"\x00")).get("com.apple.security.get-task-allow"):
        parser.error("--minimized-tabs requires a Debug app with debugger entitlement")
if args.fullscreen and args.fullscreen != "false" and args.front_window != "standalone":
    parser.error("Non-native --fullscreen requires --front-window=standalone")
front_title = "restore-gamma" if args.front_window == "standalone" else f"restore-{args.selected_tab}"
work = pathlib.Path(tempfile.mkdtemp(prefix="ghostty-session-", dir="/tmp"))
print(f"Artifacts: {work}", flush=True)
app = work / "Ghostty.app"
subprocess.run(["ditto", "--norsrc", str(args.app.resolve()), str(app)], check=True)
info_path = app / "Contents/Info.plist"
info = plistlib.loads(info_path.read_bytes())
info["CFBundleIdentifier"] = "com.mitchellh.ghostty.monterey-smoke"
info["SUEnableAutomaticChecks"] = False
info_path.write_bytes(plistlib.dumps(info))
subprocess.run(["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)], check=True)
config = work / "config"
base = ("auto-update = off\nconfirm-close-surface = false\nmacos-applescript = true\n"
        "shell-integration = none\ncommand = /bin/sh\n"
        f"working-directory = {work}\nmacos-titlebar-style = {args.titlebar}\n")
if args.fullscreen:
    base += f"macos-non-native-fullscreen = {args.fullscreen}\n"
if args.fixed_window_geometry:
    base += "window-width = 80\nwindow-height = 24\nwindow-position-x = 120\nwindow-position-y = 100\n"
config.write_text(base + "window-save-state = never\n")

if args.fullscreen:
    geometry_source = work / "geometry.swift"
    geometry_source.write_text('''
import Cocoa
let pid = Int(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                       kCGNullWindowID) as! [[String: Any]]
let bounds = windows.filter {
    $0[kCGWindowOwnerPID as String] as? Int == pid &&
    $0[kCGWindowLayer as String] as? Int == 0
}.compactMap { $0[kCGWindowBounds as String] as? [String: Any] }
let screens = NSScreen.screens.map { ["Width": $0.frame.width, "Height": $0.frame.height] }
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
let locked = session?["CGSSessionScreenIsLocked"] as? Bool ?? false
let data = try JSONSerialization.data(withJSONObject: ["windows": bounds, "screens": screens,
                                                      "locked": locked])
print(String(data: data, encoding: .utf8)!)
''')
    geometry_binary = work / "geometry"
    subprocess.run(["xcrun", "swiftc", str(geometry_source), "-o", str(geometry_binary)], check=True)
    if args.fullscreen == "false":
        session = json.loads(subprocess.check_output([str(geometry_binary), "0"], text=True))
        assert not session["locked"], "Native fullscreen requires an unlocked GUI session; unlock and rerun"


def geometry():
    return json.loads(subprocess.check_output([str(geometry_binary), str(process.app_pid)], text=True))


def wait_geometry(predicate, window_count=2):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        value = geometry()
        windows = value["windows"]
        # AppKit exposes a separate titlebar window while the native fullscreen
        # toolbar is revealed. Compare their combined extent, not mouse-dependent
        # content bounds. Regular/exit geometry still requires the original count.
        if (args.fullscreen == "false" and window_count == 1 and len(windows) == 2 and
                min(w["Height"] for w in windows) <= 100):
            left = min(w["X"] for w in windows)
            top = min(w["Y"] for w in windows)
            right = max(w["X"] + w["Width"] for w in windows)
            bottom = max(w["Y"] + w["Height"] for w in windows)
            if all(w["X"] == left and w["Width"] == right - left for w in windows):
                windows = [{"X": left, "Y": top, "Width": right - left, "Height": bottom - top}]
        if len(windows) == window_count and predicate(windows[0], value["screens"]):
            return windows[0]
        time.sleep(0.1)
    raise AssertionError(f"Session fullscreen geometry mismatch: {value}")


def script(body):
    result = subprocess.run(["osascript", "-"],
                            input=f'tell application "{app}"\n{body}\nend tell\n',
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def launch(number):
    log = (work / f"launch-{number}.log").open("w")
    executable = str(app / "Contents/MacOS/ghostty")
    command = (["open", "-W", "-n", "-a", str(app), "--args"]
               if args.launch_via == "launchservices" else [executable])
    process = subprocess.Popen([*command,
                                "--config-default-files=false", f"--config-file={config}"],
                               cwd=work, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    time.sleep(3)
    assert process.poll() is None, "App exited during launch"
    process.app_pid = process.pid
    if args.launch_via == "launchservices":
        # open -W is the lifecycle handle, but WindowServer/LLDB need the app PID.
        matches = subprocess.check_output(["pgrep", "-f", "^" + re.escape(executable) + "($| )"], text=True).split()
        assert len(matches) == 1, f"Expected one isolated app process: {matches}"
        process.app_pid = int(matches[0])
    return process


def minimized_state(stage, operation=""):
    # Run native operations on the app's main queue after detaching. This keeps
    # debugger evaluation off AppKit's UI path and leaves production unchanged.
    output = work / f"minimized-{stage}.json"
    commands = work / f"minimized-{stage}.lldb"
    expression = '''[(NSOperationQueue *)[NSOperationQueue mainQueue] addOperationWithBlock:^{
NSMutableArray *rows = [NSMutableArray array];
for (NSWindow *w in (NSArray *)[(id)[NSApplication sharedApplication] windows]) {
    NSString *label = (NSString *)[w title];
    if (![label hasPrefix:@"restore-"]) continue;
    OPERATION
    [rows addObject:@{@"title": label, @"mini": @([w isMiniaturized]),
                     @"visible": @([w isVisible])}];
}
NSData *data = [NSJSONSerialization dataWithJSONObject:rows options:0 error:NULL];
[data writeToFile:@"OUTPUT" atomically:YES];
}];'''.replace("OPERATION", operation).replace("OUTPUT", str(output))
    commands.write_text("expression -l objc++ -- @import AppKit\n"
                        "expression -l objc++ -- " + " ".join(expression.splitlines()) + "\n"
                        "process detach\nquit\n")
    result = subprocess.run(["xcrun", "lldb", "--batch", "-p", str(process.app_pid), "-s", str(commands)],
                            capture_output=True, text=True, timeout=25)
    (work / f"minimized-{stage}.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    deadline = time.monotonic() + 5
    while not output.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert output.exists(), result.stdout + result.stderr
    rows = json.loads(output.read_text())
    assert {row["title"] for row in rows} == {"restore-alpha", "restore-beta", "restore-gamma"}, rows
    return rows


def assert_minimized(rows):
    assert all(row["mini"] and not row["visible"] for row in rows if row["title"] != "restore-gamma"), rows
    assert all(not row["mini"] and row["visible"] for row in rows if row["title"] == "restore-gamma"), rows


process = launch(1)
try:
    assert script("return count of windows") == "1"
    config.write_text(base + "window-save-state = always\n")
    script('''
set t to focused terminal of selected tab of front window
if not (perform action "reload_config" on t) then error "Config reload rejected"
delay 1
''')
    focused_id = script('''
set w to front window
set firstTab to selected tab of w
set name override of firstTab to "restore-alpha"
set s to split (focused terminal of firstTab) direction right
set secondTab to new tab in w
set name override of secondTab to "restore-beta"
select tab firstTab
delay 0.5
if name override of selected tab of w is not "restore-alpha" then error "Fixture did not select alpha"
set secondWindow to new window
set name override of selected tab of secondWindow to "restore-gamma"
delay 0.5
if (count of windows) is not 2 or (count of terminals) is not 4 then error "Invalid session fixture"
if name override of selected tab of w is not "restore-alpha" then error "Fixture lost alpha selection"
return id of focused terminal of firstTab
''')
    # Change selection after AppKit has had time to encode the first fixture.
    time.sleep(2)
    script(f'''
repeat with w in windows
    repeat with t in tabs of w
        if name override of t is "restore-{args.selected_tab}" then
            set targetID to id of t
            set targetWindowID to id of w
        end if
        if name override of t is "restore-gamma" then set gammaID to id of w
    end repeat
end repeat
select tab (tab id targetID of window id targetWindowID)
activate window (window id gammaID)
{ 'activate window (window id targetWindowID)' if args.front_window == 'tabbed' else '' }
delay 0.5
if name override of selected tab of front window is not "{front_title}" then error "Fixture front window activation failed"
''')
    if args.fullscreen:
        regular_frame = wait_geometry(lambda bounds, screens: True)
        if args.fixed_window_geometry:
            assert all(regular_frame["Width"] < screen["Width"] and
                       regular_frame["Height"] < screen["Height"] - 100
                       for screen in geometry()["screens"]), "Expected non-maximized fixture window"
        assert script('perform action "toggle_fullscreen" on focused terminal of selected tab of front window') == "true"
        # A native fullscreen Space hides the other window. A maximized regular
        # window can already be near display size, so wait for a changed frame.
        fullscreen_window_count = 1 if args.fullscreen == "false" else 2
        fullscreen_frame = wait_geometry(lambda bounds, screens: bounds != regular_frame and any(
            bounds["Width"] == screen["Width"] and bounds["Height"] >= screen["Height"] - 40
            for screen in screens), window_count=fullscreen_window_count)
        assert fullscreen_frame != regular_frame, "Fixture did not enter fullscreen"
        print(f"Saved regular frame: {regular_frame}; fullscreen: {fullscreen_frame}", flush=True)
        if args.replace_fullscreen_tab:
            script('''
set w to front window
set oldBeta to selected tab of w
repeat with t in tabs of w
    if name override of t is "restore-alpha" then select tab t
end repeat
if not (perform action "close_tab:this" on focused terminal of oldBeta) then error "Cannot close old beta"
delay 0.5
set replacement to new tab in front window
set name override of replacement to "restore-beta"
select tab replacement
delay 0.5
if name override of selected tab of front window is not "restore-beta" then error "Replacement tab not selected"
if (count of terminals) is not 4 then error "Replacement tab lost terminals"
''')
            wait_geometry(lambda bounds, screens: bounds == fullscreen_frame,
                          window_count=fullscreen_window_count)
            print("PASS: replaced selected tab while native fullscreen before saving", flush=True)
    if args.minimized_tabs:
        minimized_state("minimize", f'if ([label isEqualToString:@"restore-{args.selected_tab}"]) [w miniaturize:nil];')
        time.sleep(1)
        assert_minimized(minimized_state("before-quit"))
    script('''
set t to focused terminal of selected tab of front window
if not (perform action "reload_config" on t) then error "Config reload rejected"
delay 1
repeat with w in windows
    if (name override of every tab of w) contains "restore-alpha" then
        if name override of selected tab of w is not "EXPECTED" then error "Selection changed before quit"
    end if
end repeat
if name override of selected tab of front window is not "FRONT_TITLE" then error "Fixture frontmost window changed"
quit
'''.replace("EXPECTED", f"restore-{args.selected_tab}").replace("FRONT_TITLE", front_title))
    assert process.wait(timeout=10) == 0
    process = launch(2)
    if args.minimized_tabs:
        assert_minimized(minimized_state("after-relaunch"))
        print("PASS: minimized tab group restored across app quit/relaunch", flush=True)
    result = script('''
if (count of windows) is not 2 then error "Restored window count: " & (count of windows)
if (count of terminals) is not 4 then error "Restored terminal count: " & (count of terminals)
set foundAlpha to false
set foundBeta to false
set foundGamma to false
set selectionRestored to true
set frontRestored to name override of selected tab of front window is "FRONT_TITLE"
repeat with w in windows
    set labels to name override of every tab of w
    if labels contains "restore-alpha" then
        if (count of tabs of w) is not 2 or labels does not contain "restore-beta" then error "Lost alpha/beta tab grouping"
        if labels is not {"restore-alpha", "restore-beta"} then error "Tab order changed"
        if name override of selected tab of w is not "EXPECTED" then set selectionRestored to false
    else if labels contains "restore-gamma" then
        if (count of tabs of w) is not 1 then error "Standalone window merged into tab group"
    else
        error "Unexpected restored window"
    end if
    repeat with t in tabs of w
        set label to name override of t
        if label is "restore-alpha" then
            if (count of terminals of t) is not 2 then error "Lost restored split"
            if id of focused terminal of t is not "FOCUSED_ID" then error "Lost focused split"
            set foundAlpha to true
        else if label is "restore-beta" then
            set foundBeta to true
        else if label is "restore-gamma" then
            set foundGamma to true
        end if
    end repeat
end repeat
if not (foundAlpha and foundBeta and foundGamma) then error "Restored tab titles missing"
return {selectionRestored, frontRestored}
'''.replace("EXPECTED", f"restore-{args.selected_tab}").replace("FOCUSED_ID", focused_id)
        .replace("FRONT_TITLE", front_title))
    print("PASS: across-launch windows, tabs, split tree and title overrides", flush=True)
    if args.minimized_tabs:
        # Object enumeration must not silently expand the restored group.
        assert_minimized(minimized_state("after-enumeration"))
        minimized_state("deminimize", f'if ([label isEqualToString:@"restore-{args.selected_tab}"]) [w deminiaturize:nil];')
        time.sleep(1)
        rows = minimized_state("after-deminimize")
        assert not any(row["mini"] for row in rows), rows
        marker = work / "minimized-restored-pty"
        script(f'''
repeat with w in windows
    if (name override of every tab of w) contains "restore-alpha" then
        if name override of selected tab of w is not "restore-{args.selected_tab}" then error "Deminimize lost selection"
        input text "printf restored > '{marker}'" to focused terminal of selected tab of w
        send key "enter" to focused terminal of selected tab of w
    end if
end repeat
''')
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists() and marker.read_text() == "restored", "Deminimized restored PTY failed"
        print("PASS: scripting preserves minimized state; deminiaturization retains selected tab and live PTY", flush=True)
    if args.fullscreen:
        print(f"Restored selection/order: {result}; geometry: {geometry()}", flush=True)
        wait_geometry(lambda bounds, screens: bounds == fullscreen_frame,
                      window_count=fullscreen_window_count)
        assert script(f'''
repeat with w in windows
    repeat with t in tabs of w
        if name override of t is "{front_title}" then
            return perform action "toggle_fullscreen" on focused terminal of t
        end if
    end repeat
end repeat
error "Missing restored fullscreen terminal"
''') == "true"
        time.sleep(1)
        print(f"After restored fullscreen toggle: {geometry()}", flush=True)
        wait_geometry(lambda bounds, screens: bounds == regular_frame)
        script(f'''
repeat with w in windows
    if (name override of every tab of w) contains "restore-alpha" then
        if name override of every tab of w is not {{"restore-alpha", "restore-beta"}} then error "Fullscreen exit changed tab order"
        if name override of selected tab of w is not "restore-{args.selected_tab}" then error "Fullscreen exit changed selected tab"
    end if
end repeat
if name override of selected tab of front window is not "{front_title}" then error "Fullscreen exit changed front window"
''')
        marker = work / "restored-fullscreen-pty"
        script(f'''
repeat with w in windows
    repeat with t in tabs of w
        if name override of t is "{front_title}" then
            input text "printf restored > '{marker}'" to focused terminal of t
            send key "enter" to focused terminal of t
        end if
    end repeat
end repeat
''')
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert marker.exists() and marker.read_text() == "restored", "Restored fullscreen PTY failed"
        print("PASS: fullscreen restored across launch, original frame recovered on exit, live PTY", flush=True)
    # Leave no persistent fixture for the next run of this dedicated test ID.
    config.write_text(base + "window-save-state = never\n")
    script('''
set t to focused terminal of selected tab of front window
perform action "reload_config" on t
delay 0.5
quit
''')
    assert process.wait(timeout=10) == 0
    process = launch(3)
    assert script("return count of windows") == "1", "never restored old windows"
    assert script("return count of terminals") == "1", "never restored old splits/tabs"
    script("quit")
    assert process.wait(timeout=10) == 0
    print("PASS: window-save-state=never prevents subsequent session restoration")
    selection_restored, front_restored = result.split(", ")
    assert selection_restored == "true", "Selected tab not restored"
    print("PASS: selected tab, tab order and focused split restored", flush=True)
    assert front_restored == "true", "Frontmost window not restored"
    print("PASS: frontmost window restored")
finally:
    if process.poll() is None:
        try:
            os.kill(process.app_pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.kill(process.app_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.kill()
            process.wait(timeout=5)
