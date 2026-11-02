#!/usr/bin/env python3
"""Exercise real Services without AppleScript or the shared smoke bundle ID.

Uses a disposable uniquely registered app, unique pasteboards, and child-written
cwd/PTY evidence. Does not change user service enablement, clipboard contents,
Automation consent or installed Ghostty. Requires an unlocked GUI session.
Artifacts remain in the printed directory; the app is unregistered on exit.
WindowServer counts distinguish tab versus window creation. --accessibility
also checks native tab membership/selection and terminal text via read-only AX
queries, requiring existing permission (never prompts). No Finder menu test.
"""

import argparse
import json
import os
import pathlib
import plistlib
import shlex
import subprocess
import sys
import tempfile
import time


REGISTER = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
PBS = "/System/Library/CoreServices/pbs"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    parser.add_argument("--accessibility", action="store_true", help="Require existing AX permission and verify tab/text tree")
    parser.add_argument("--selection", action="store_true",
                        help="Also check AX Select All, UTF-16 ranges and selection notifications")
    parser.add_argument("--write-selection", action="store_true", help="Verify real AX selection setter")
    parser.add_argument("--rectangle", action="store_true",
                        help="Experimental PID-targeted Option drag; currently fails due to native AppKit event routing")
    parser.add_argument("--native-rectangle", action="store_true",
                        help="Explicitly activate the fixture and use foreground WindowServer pointer routing")
    args = parser.parse_args()
    if args.native_rectangle and not args.rectangle:
        parser.error("--native-rectangle requires --rectangle")
    if args.selection and not args.accessibility:
        parser.error("--selection requires --accessibility")
    if args.write_selection and not args.selection:
        parser.error("--write-selection requires --selection")
    if args.rectangle and not args.selection:
        parser.error("--rectangle requires --selection")
    source = args.app.resolve()
    assert (source / "Contents/MacOS/ghostty").is_file(), "Expected a built app"
    work = pathlib.Path(tempfile.mkdtemp(prefix="ghostty-services-", dir="/tmp")).resolve()
    print(f"Artifacts: {work}", flush=True)
    app = work / "Ghostty.app"
    subprocess.run(["ditto", "--norsrc", str(source), str(app)], check=True)
    plist = app / "Contents/Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info["CFBundleIdentifier"] = "com.mitchellh.ghostty.services-" + work.name.removeprefix("ghostty-services-")
    info["SUEnableAutomaticChecks"] = False
    services = {}
    for service in info["NSServices"]:
        name = f"{work.name} {service['NSMessage']}"
        service["NSMenuItem"] = {"default": name}
        services[service["NSMessage"]] = name
    assert set(services) == {"openTab", "openWindow"}
    plist.write_bytes(plistlib.dumps(info))
    subprocess.run(["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)

    # Each real terminal process reports independently; no app scripting or
    # controller substitution is needed. Atomic rename avoids partial JSON reads.
    child = work / "child.py"
    rectangle_text = "\n0123456789abcdef\nABCDEFGHIJKLMNOP\nqrstuvwxyz012345" if args.rectangle else ""
    child.write_text("import json, os, pathlib, time\n"
                     f"root = pathlib.Path({str(work)!r})\n"
                     "print('\\x1b[2J\\x1b[H' + 'SERVICE-PTY:' + os.getcwd() + '\\U0001f680e\\u0301\\nAX-LINE-END'"
                     f" + {rectangle_text!r}, flush=True)\n"
                     "temporary = root / (str(os.getpid()) + '.pending')\n"
                     "temporary.write_text(json.dumps({'cwd': os.getcwd(), 'pid': os.getpid(), "
                     "'tty': os.isatty(0) and os.isatty(1), 'grid': list(os.get_terminal_size())}))\n"
                     "temporary.rename(temporary.with_suffix('.json'))\n"
                     "while True: time.sleep(1)\n")
    config = work / "config"
    # The prefix also avoids treating the opening quote as a config-string
    # delimiter. Shell quoting preserves paths containing spaces/metacharacters.
    command = "shell:" + shlex.join([sys.executable, str(child)])
    config.write_text("auto-update = off\nwindow-save-state = never\nconfirm-close-surface = false\n"
                      "shell-integration = none\nmacos-applescript = false\n"
                      "copy-on-select = none\nclipboard-read = deny\nclipboard-write = deny\n"
                      f"command = {command}\nworking-directory = {work}\n")
    if args.rectangle:
        with config.open("a") as stream:
            stream.write("window-padding-x = 0\nwindow-padding-y = 0\nwindow-padding-balance = false\n"
                         "font-size = 20\nwindow-width = 80\nwindow-height = 12\n")
    swift = work / "client.swift"
    swift.write_text(r'''
import AppKit
let session = CGSessionCopyCurrentDictionary() as? [String: Any]
precondition(!(session?["CGSSessionScreenIsLocked"] as? Bool ?? false), "Unlock the session first")
if CommandLine.arguments.contains("--preflight") {
    if CommandLine.arguments.contains("--accessibility") {
        precondition(AXIsProcessTrusted(), "Existing Accessibility permission required; no prompt requested")
    }
    exit(0)
}
_ = NSApplication.shared
if CommandLine.arguments[1] == "--accessibility" {
    precondition(AXIsProcessTrusted(), "Accessibility permission missing")
    let root = AXUIElementCreateApplication(pid_t(CommandLine.arguments[2])!)
    func attribute(_ element: AXUIElement, _ key: String) -> CFTypeRef? {
        var value: CFTypeRef?
        return AXUIElementCopyAttributeValue(element, key as CFString, &value) == .success ? value : nil
    }
    func tree(_ element: AXUIElement, depth: Int = 0) -> [String: Any] {
        var row: [String: Any] = [:]
        for key in [kAXRoleAttribute, kAXTitleAttribute, kAXValueAttribute] {
            if let value = attribute(element, key) { row[key] = String(describing: value) }
        }
        if row[kAXRoleAttribute] as? String == kAXTextAreaRole,
           let text = attribute(element, kAXValueAttribute) as? String {
            guard let count = attribute(element, kAXNumberOfCharactersAttribute) as? NSNumber,
                  let rawRange = attribute(element, kAXVisibleCharacterRangeAttribute),
                  CFGetTypeID(rawRange) == AXValueGetTypeID() else {
                fatalError("Missing AX text count/range")
            }
            var range = CFRange()
            // The CF type ID is checked above; AXValue has no conditional Swift cast.
            // swiftlint:disable:next force_cast
            precondition(AXValueGetValue(rawRange as! AXValue, .cfRange, &range), "Invalid AX range")
            precondition(count.intValue == text.utf16.count, "AX count must use UTF-16")
            precondition(range.location == 0 && range.length == text.utf16.count, "AX visible range must use UTF-16")
            var substring: CFTypeRef?
            precondition(AXUIElementCopyParameterizedAttributeValue(
                element, kAXStringForRangeParameterizedAttribute as CFString, rawRange, &substring) == .success,
                "AX substring request failed")
            precondition(substring as? String == text, "AX visible range must round-trip full Unicode text")
            if let marker = text.range(of: "AX-LINE-END") {
                let offset = NSRange(text.startIndex..<marker.lowerBound, in: text).length
                for index in [offset - 1, offset] where index >= 0 {
                    var line: CFTypeRef?
                    precondition(AXUIElementCopyParameterizedAttributeValue(
                        element, kAXLineForIndexParameterizedAttribute as CFString,
                        NSNumber(value: index), &line) == .success, "AX line query failed")
                    let prefix = (text as NSString).substring(to: index)
                    let expected = prefix.components(separatedBy: .newlines).count - 1
                    precondition((line as? NSNumber)?.intValue == expected, "AX line index must use UTF-16")
                }
                row["lineChecked"] = true
            }
            row["utf16Count"] = count.intValue
        }
        if depth < 12, let children = attribute(element, kAXChildrenAttribute) as? [AXUIElement] {
            row["children"] = children.map { tree($0, depth: depth + 1) }
        }
        return row
    }
    // Query AXWindows explicitly: root AXChildren can expose an incomplete
    // placeholder window during Monterey's accessibility tree initialization.
    guard let windows = attribute(root, kAXWindowsAttribute) as? [AXUIElement],
          let focused = attribute(root, kAXFocusedWindowAttribute) else {
        fatalError("Missing accessibility windows/focus")
    }
    let rows = windows.map { window -> [String: Any] in
        var row = tree(window)
        row["focused"] = CFEqual(window, focused)
        return row
    }
    print(String(data: try JSONSerialization.data(withJSONObject: rows), encoding: .utf8)!)
    exit(0)
}
if CommandLine.arguments[1] == "--windows" {
    let pid = Int(CommandLine.arguments[2])!
    let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements],
                                            kCGNullWindowID) as? [[String: Any]] ?? []
    let owned = windows.filter {
        $0[kCGWindowOwnerPID as String] as? Int == pid && $0[kCGWindowLayer as String] as? Int == 0
    }
    print(String(data: try JSONSerialization.data(withJSONObject: owned), encoding: .utf8)!)
    exit(0)
}
NSUpdateDynamicServices()
RunLoop.main.run(until: Date(timeIntervalSinceNow: 1))
func perform() -> Bool {
    let board = NSPasteboard.withUniqueName()
    defer { board.releaseGlobally() }
    let path = CommandLine.arguments[2]
    switch CommandLine.arguments[3] {
    case "filenames":
        precondition(board.setPropertyList([path], forType: NSPasteboard.PasteboardType("NSFilenamesPboardType")))
    case "text":
        precondition(board.setString(path, forType: .string))
    default:
        fatalError("Unknown pasteboard representation")
    }
    return NSPerformService(CommandLine.arguments[1], board)
}
let success = perform()
print("NSPerformService=\(success)")
exit(success ? 0 : 1)
'''.lstrip())
    client = work / "client"
    subprocess.run(["xcrun", "swiftc", str(swift), "-o", str(client)], check=True)
    subprocess.run([str(client), "--preflight", *(["--accessibility"] if args.accessibility else [])], check=True)
    selection_client = work / "selection-client"
    if args.selection:
        subprocess.run(["xcrun", "swiftc", str(pathlib.Path(__file__).with_name("accessibility-selection-client.swift")),
                        "-o", str(selection_client)], check=True)

    with (work / "launch.log").open("w") as log:
        process = subprocess.Popen([str(app / "Contents/MacOS/ghostty"), "--config-default-files=false",
                                    f"--config-file={config}"], cwd=work, stdout=log, stderr=subprocess.STDOUT)

        def records():
            return {path.stem: json.loads(path.read_text()) for path in work.glob("*.json")}

        def wait_count(count):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                current = records()
                assert len(current) <= count, f"Unexpected extra terminal: {current}"
                if len(current) == count:
                    return current
                assert process.poll() is None, "App exited while waiting for terminal evidence"
                time.sleep(0.05)
            raise AssertionError(f"Expected {count} terminal reports, got {records()}")

        def wait_windows(count, label):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = subprocess.check_output([str(client), "--windows", str(process.pid)], text=True, timeout=5)
                windows = json.loads(result)
                (work / f"{label}-windows.txt").write_text(result)
                if len(windows) == count:
                    return
                time.sleep(0.1)
            raise AssertionError(f"{label}: expected {count} visible app windows, got {windows}")

        def descendants(node, role):
            result = [node] if node.get("AXRole") == role else []
            for child in node.get("children", []):
                result.extend(descendants(child, role))
            return result

        def wait_accessibility(window_count, tab_count, directory, label):
            if not args.accessibility:
                return
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = subprocess.run([str(client), "--accessibility", str(process.pid)],
                                        capture_output=True, text=True, timeout=5)
                assert result.returncode == 0, result.stdout + result.stderr
                rows = json.loads(result.stdout)
                (work / f"{label}-accessibility.txt").write_text(json.dumps(rows, indent=2) + "\n")
                groups = [group for row in rows for group in descendants(row, "AXTabGroup")]
                tabs = [tab for group in groups for tab in descendants(group, "AXRadioButton")]
                focused = [row for row in rows if row["focused"]]
                text = [node.get("AXValue", "") for row in focused for node in descendants(row, "AXTextArea")]
                line_checked = any(node.get("lineChecked") for row in focused for node in descendants(row, "AXTextArea"))
                # Terminal lines may wrap; the marker contains only fixture data.
                marker = "SERVICE-PTY:" + str(directory) + "\U0001f680e\u0301"
                if (len(rows) == window_count and len(focused) == 1 and line_checked and
                        len(groups) == (1 if tab_count > 1 else 0) and
                        len(tabs) == (tab_count if tab_count > 1 else 0) and
                        sum(tab.get("AXValue") == "1" for tab in tabs) == (1 if tab_count > 1 else 0) and
                        any(marker in value.replace("\n", "").replace("\r", "") for value in text)):
                    print(f"PASS: {label}: AX windows/tabs/selection and focused terminal marker", flush=True)
                    return
                time.sleep(0.1)
            raise AssertionError(f"{label}: AX tree/selection/text mismatch; see accessibility artifact")

        try:
            initial = wait_count(1)
            assert all(r["cwd"] == str(work) and r["tty"] for r in initial.values()), initial
            window_count = 1
            tab_count = 1
            wait_windows(window_count, "initial")
            wait_accessibility(window_count, tab_count, work, "initial")
            if args.selection:
                extra = ["--rectangle", *map(str, next(iter(initial.values()))["grid"])] if args.rectangle else []
                if args.write_selection:
                    extra.append("--write-selection")
                if args.native_rectangle:
                    extra.append("--native-rectangle")
                result = subprocess.run([str(selection_client), str(process.pid), "SERVICE-PTY:" + str(work), *extra],
                                        capture_output=True, text=True, timeout=15)
                (work / "selection.log").write_text(result.stdout + result.stderr)
                assert result.returncode == 0, result.stdout + result.stderr
                print(result.stdout.strip(), flush=True)
            subprocess.run([REGISTER, "-f", str(app)], check=True, timeout=15)
            subprocess.run([PBS, "-update"], check=True, timeout=15)
            inventory = subprocess.check_output([PBS, "-dump"], text=True, timeout=15)
            (work / "inventory.txt").write_text(inventory)
            assert all(name in inventory for name in services.values()), "Unique service names not discovered"

            for message in ("openTab", "openWindow"):
                for representation in ("filenames", "text"):
                    for kind in ("directory", "file"):
                        label = f"{message}-{representation}-{kind}"
                        directory = work / (label + " 'quoted directory'")
                        directory.mkdir()
                        path = directory
                        if kind == "file":
                            path = directory / "selected file.txt"
                            path.write_text("Service should open the parent directory.\n")
                        before = records()
                        result = subprocess.run([str(client), services[message], str(path), representation],
                                                capture_output=True, text=True, timeout=20)
                        (work / f"{label}.log").write_text(result.stdout + result.stderr)
                        assert result.returncode == 0 and "NSPerformService=true" in result.stdout, (
                            label, result.stdout, result.stderr)
                        after = wait_count(len(before) + 1)
                        created = [after[key] for key in after.keys() - before.keys()]
                        assert len(created) == 1 and created[0]["cwd"] == str(directory) and created[0]["tty"], created
                        if message == "openWindow":
                            window_count += 1
                        else:
                            tab_count += 1
                        wait_windows(window_count, label)
                        wait_accessibility(window_count, tab_count, directory, label)
                        print(f"PASS: {label}: real child cwd/PTY, {window_count} visible app window(s)", flush=True)
            time.sleep(0.25)
            assert len(records()) == 9, "Service created extra terminal processes"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            subprocess.run([REGISTER, "-u", str(app)], check=True, timeout=15)
            subprocess.run([PBS, "-update"], check=True, timeout=15)
    # Every reporting child must terminate with the test app. Never kill a PID
    # blindly: report retained processes instead of risking PID reuse.
    for record in records().values():
        try:
            os.kill(record["pid"], 0)
        except ProcessLookupError:
            continue
        raise AssertionError(f"Child may still be alive after app cleanup: {record['pid']}")
    print("PASS: eight cross-process Services calls; unique pasteboards, app unregistered, children exited")


if __name__ == "__main__":
    main()
