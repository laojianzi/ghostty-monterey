#!/usr/bin/env python3
"""Detect transient blank frames during native tab switching on macOS.

Runs a signed, isolated copy, never the installed app. Requires an unlocked
GUI session and existing Accessibility/Screen Recording permission. Keep the
fixture foreground and unobstructed; run no other GUI probes concurrently.
Evidence stays in a fresh temporary directory, printed on entry and exit.
"""

import argparse
import hashlib
import json
import os
import pathlib
import plistlib
import shlex
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=pathlib.Path)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--no-vsync", action="store_true")
    parser.add_argument("--native-titlebar", action="store_true")
    parser.add_argument("--continuous-output", action="store_true")
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    source = args.app.resolve()
    binary = source / "Contents/MacOS/ghostty"
    if not binary.is_file():
        parser.error("expected a Ghostty.app bundle")
    work = pathlib.Path(tempfile.mkdtemp(prefix="ghostty-tab-flash-"))
    print(f"Evidence: {work}", flush=True)
    helper = work / "capture"
    subprocess.run([
        "xcrun", "swiftc", str(pathlib.Path(__file__).with_name("tab-flash-capture.swift")),
        "-o", str(helper),
    ], check=True)
    subprocess.run([str(helper), "--preflight"], check=True)
    app = work / "Ghostty.app"
    subprocess.run(["ditto", "--norsrc", str(source), str(app)], check=True)
    plist = app / "Contents/Info.plist"
    info = plistlib.loads(plist.read_bytes())
    identity = {key: info.get(key) for key in (
        "CFBundleShortVersionString", "CFBundleVersion", "GhosttyCommit",
    )}
    identity["sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    info["CFBundleIdentifier"] = "com.mitchellh.ghostty.monterey-smoke"
    info["SUEnableAutomaticChecks"] = False
    plist.write_bytes(plistlib.dumps(info))
    subprocess.run([
        "codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app),
    ], check=True)
    fixture = work / "fixture.py"
    fixture.write_text(
        "import time\n"
        "print('\\x1b]2;Tab flash fixture\\x07\\x1b[?25l"
        "\\x1b[48;2;0;255;0m\\x1b[2J\\x1b[H', end='', flush=True)\n"
        + ("while True:\n print('\\x1b[Htick', end='', flush=True); time.sleep(0.03)\n"
           if args.continuous_output else "while True: time.sleep(10)\n")
    )
    config = work / "config"
    config.write_text(
        "auto-update = off\nwindow-save-state = never\nconfirm-close-surface = false\n"
        "shell-integration = none\nbackground = #101010\n"
        "window-width = 100\nwindow-height = 30\n"
        "keybind = super+1=goto_tab:1\nkeybind = super+2=goto_tab:2\n"
        "keybind = super+t=new_tab\n"
        f"command = {shlex.join([sys.executable, str(fixture)])}\n"
        f"macos-titlebar-style = {'native' if args.native_titlebar else 'transparent'}\n"
        f"window-vsync = {'false' if args.no_vsync else 'true'}\n"
    )
    env = dict(os.environ)
    for key in (
        "GHOSTTY_RESOURCES_DIR", "GHOSTTY_BIN_DIR", "GHOSTTY_SHELL_INTEGRATION",
        "TERMINFO", "TERMINFO_DIRS", "ZDOTDIR", "ENV", "BASH_ENV", "GHOSTTY_LOG",
        "DYLD_INSERT_LIBRARIES", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH", "MTL_DEBUG_LAYER",
    ):
        env.pop(key, None)
    for key in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        directory = work / key
        directory.mkdir()
        env[key] = str(directory)
    results = []
    previous = subprocess.check_output([
        "osascript", "-e", 'tell application "System Events" to get unix id of first '
        'application process whose frontmost is true',
    ], text=True).strip()
    try:
        with (work / "launch.log").open("w") as log:
            proc = subprocess.Popen([
                str(app / "Contents/MacOS/ghostty"), "--config-default-files=false",
                f"--config-file={config}",
            ], env=env, cwd=work, stdout=log, stderr=subprocess.STDOUT)
            try:
                time.sleep(3)
                if proc.poll() is not None:
                    raise RuntimeError("test app exited; inspect launch.log")
                subprocess.run([str(helper), str(proc.pid), str(work), "setup"], check=True)
                for index, mode in enumerate(["baseline"] + ["switch"] * args.rounds):
                    out = work / f"{index:02d}-{mode}"
                    out.mkdir()
                    result = subprocess.run([
                        str(helper), str(proc.pid), str(out), mode,
                    ], capture_output=True, text=True, timeout=40)
                    (out / "result.txt").write_text(result.stdout + result.stderr)
                    print(f"{out.name}: exit={result.returncode} {result.stdout.strip()}", flush=True)
                    results.append({"run": out.name, "exit": result.returncode})
                    # A bad steady frame or invalid capture invalidates this test setup.
                    if mode == "baseline" and result.returncode != 0:
                        break
                    if result.returncode not in (0, 2):
                        break
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    finally:
        if previous.isdigit():
            subprocess.run([str(helper), "--activate", previous], check=False)
        (work / "summary.json").write_text(json.dumps({
            "source": str(source), "identity": identity,
            "options": {k: v for k, v in vars(args).items() if k != "app"},
            "runs": results,
        }, indent=2) + "\n")
        print(f"Evidence: {work}", flush=True)
    return 0 if len(results) == args.rounds + 1 and all(r["exit"] == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
