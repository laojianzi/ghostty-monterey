#!/usr/bin/env python3
"""Test confirmed quit in a private real app, without intercepting app callbacks.

Requires existing Accessibility permission and an unlocked GUI session. Only
target-local AX menu/button actions are sent; no clipboard or global input.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys
import tempfile
import time


HERE = Path(__file__).resolve().parent


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def wait(message, predicate, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path)
    parser.add_argument("--negative-cancel", action="store_true", help="Omit Cancel press; this run must fail")
    parser.add_argument("--multi", choices=("review", "direct"), help="Exercise two windows and independent PTY children")
    parser.add_argument("--negative-review-cancel", action="store_true", help="Omit cancellation of the first reviewed sheet; must fail")
    args = parser.parse_args()
    if args.negative_review_cancel and args.multi != "review":
        parser.error("--negative-review-cancel requires --multi review")
    source = args.app.resolve(strict=True)
    work = Path(tempfile.mkdtemp(prefix="ghostty-confirmed-quit-", dir="/tmp"))
    print("Artifacts:", work, flush=True)
    client = work / "quit-client"
    subprocess.run(["xcrun", "swiftc", str(HERE / "quit-app-client.swift"), "-o", str(client)], check=True)
    subprocess.run([str(client), "--preflight"], check=True, timeout=10)
    app = work / "Ghostty.app"
    subprocess.run(["ditto", "--norsrc", str(source), str(app)], check=True)
    info_path = app / "Contents/Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    info["CFBundleIdentifier"] = "com.mitchellh.ghostty.monterey-smoke"
    info["SUEnableAutomaticChecks"] = False
    info_path.write_bytes(plistlib.dumps(info))
    subprocess.run(["codesign", "--force", "--sign", "-", "--preserve-metadata=entitlements", str(app)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
    heartbeats = work / "heartbeats"
    heartbeats.mkdir()
    child = work / "child.py"
    child.write_text("import json, os, pathlib, time\n"
                     f"target = pathlib.Path({str(heartbeats)!r}) / (str(os.getpid()) + '.json')\n"
                     "until = time.monotonic() + 90\n"
                     "while time.monotonic() < until:\n"
                     " pending = target.with_suffix('.pending')\n"
                     " pending.write_text(json.dumps({'pid': os.getpid(), 'at': time.monotonic(), 'tty': os.isatty(0)}))\n"
                     " pending.replace(target)\n time.sleep(0.05)\n")
    config = work / "config"
    config.write_text("auto-update = off\nwindow-save-state = never\nconfirm-close-surface = always\n"
                      "shell-integration = none\ncopy-on-select = none\nclipboard-read = deny\n"
                      "clipboard-write = deny\ndesktop-notifications = false\n"
                      "command = direct:" + shlex.join([sys.executable, str(child)]) + "\n")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GHOSTTY_", "DYLD_"))
           and key not in ("TERMINFO", "TERMINFO_DIRS", "ENV", "BASH_ENV", "ZDOTDIR")}
    env.update(XDG_CONFIG_HOME=str(work / "xdg-config"), XDG_CACHE_HOME=str(work / "xdg-cache"),
               XDG_STATE_HOME=str(work / "xdg-state"), GHOSTTY_USER_DEFAULTS_SUITE="org.ghostty." + work.name)
    pids = []
    def states():
        return [json.loads(path.read_text()) for path in heartbeats.glob("*.json")]

    def live_heartbeats_after(instant):
        current = states()
        return (len(current) == len(pids) and {state["pid"] for state in current} == set(pids)
                and all(state["at"] > instant + 0.2 and alive(state["pid"]) for state in current))

    with (work / "launch.log").open("w") as log, (work / "actions.log").open("w") as actions:
        process = subprocess.Popen([str(app / "Contents/MacOS/ghostty"), "--config-default-files=false",
                                    f"--config-file={config}"], cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait("No child heartbeat", lambda: len(states()) == 1)
            state = states()[0]
            pid = state["pid"]
            pids.append(pid)
            assert state["tty"] and alive(pid) and process.poll() is None

            def action(name, skip_cancel=False):
                command = [str(client), str(process.pid), name]
                if name == "cancel" and (args.negative_cancel or skip_cancel):
                    command.append("--skip-cancel")
                subprocess.run(command, stdout=actions,
                               stderr=subprocess.STDOUT, check=True, timeout=10)

            if args.multi:
                action("new-window")
                wait("Second PTY not ready", lambda: len(states()) == 2)
                pids = [state["pid"] for state in states()]
                assert len(set(pids)) == 2 and all(state["tty"] for state in states())
            quit_action = "quit-multi" if args.multi else "quit"
            action(quit_action)
            assert all(alive(pid) for pid in pids) and process.poll() is None, "Quit prompt killed child before confirmation"
            action("cancel")
            cancelled = time.monotonic()
            wait("Child stopped after cancellation", lambda: live_heartbeats_after(cancelled))
            assert process.poll() is None, "Cancellation did not preserve app"
            if args.multi == "review":
                action("quit-multi")
                action("review")
                action("cancel", skip_cancel=args.negative_review_cancel)
                cancelled_review = time.monotonic()
                wait("Review cancellation lost a child", lambda: live_heartbeats_after(cancelled_review))
                assert process.poll() is None, "Review cancellation quit app"
                action("quit-multi")
                action("review")
                action("accept")
                action("one-window")
                assert process.poll() is None, "First reviewed window quit app prematurely"
                first_review = time.monotonic()
                wait("Remaining reviewed PTY stopped before its confirmation",
                     lambda: any(state["at"] > first_review + 0.2 and alive(state["pid"]) for state in states()))
                action("accept")
            else:
                action(quit_action)
                action("accept-all" if args.multi else "accept")
            assert process.wait(timeout=10) == 0, "Confirmed quit did not exit cleanly"
            wait("Child survived confirmed app exit", lambda: all(not alive(pid) for pid in pids), seconds=5)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            known_pids = {state["pid"] for state in states()}
            wait("Owned child remains after cleanup; not blindly killing a reused PID",
                 lambda: all(not alive(pid) for pid in known_pids), seconds=5)
    text = (work / "launch.log").read_text()
    assert "failed assertion" not in text and "Validation Error" not in text, text
    report = {"app_exit": process.returncode, "child_pids": pids, "children_reaped": True, "multi": args.multi,
              "source_app": str(source), "source_binary_sha256": hashlib.sha256(
                  (source / "Contents/MacOS/ghostty").read_bytes()).hexdigest()}
    (work / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: real app quit cancelled with {len(pids)} live PTYs, then confirmed ({args.multi or 'single'}); app exits 0 and children disappear")


if __name__ == "__main__":
    main()
