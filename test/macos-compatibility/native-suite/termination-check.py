#!/usr/bin/env python3
"""Exercise native quit dialogs against an already accepted candidate unit build.

Only the probe's windows/buttons are manipulated. No global input or actual
application termination is requested; the NSApplication reply boundary is logged.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import shlex
import subprocess
import sys
import time
import uuid


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-output", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--negative", action="store_true", help="Reverse one expected reply in the probe copy")
    parser.add_argument("--real-child", action="store_true", help="Use actual surface/PTY confirmation and teardown")
    args = parser.parse_args()
    unit = args.unit_output.resolve(strict=True)
    if not json.loads((unit / "result.json").read_text())["accepted"]:
        parser.error("The supplied candidate test run was not accepted")
    metadata = json.loads((unit / "inputs.json").read_text())
    candidate = Path(metadata["candidate"])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    command = next(cmd for cmd in json.loads((unit / "commands.json").read_text()) if "-emit-library" in cmd)
    command = [value for value in command if not value.endswith((".swift", ".o"))]
    index = command.index("-load-plugin-executable")
    del command[index:index + 2]
    command.remove("-emit-library")
    command[command.index("-module-name") + 1] = "TerminationProbe"
    host = output / "TerminationProbe.app/Contents"
    (host / "MacOS").mkdir(parents=True)
    executable = host / "MacOS/TerminationProbe"
    command[command.index("-o") + 1] = str(executable)
    source = output / "main.swift"
    shutil.copy2(HERE / ("TerminationChildProbe.swift" if args.real_child else "TerminationProbe.swift"), source)
    if args.negative:
        text = source.read_text()
        message = "real child sheet reply" if args.real_child else "single sheet response forwarded"
        needle = f'require(app.replies.last == accept, "{message}")'
        if text.count(needle) != 1:
            raise RuntimeError("Negative-control seam changed")
        source.write_text(text.replace(needle, needle.replace("== accept", "== !accept")))
    command.append(str(source))
    (output / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    identity = "org.ghostty.termination-probe." + str(uuid.uuid4())
    (host / "Info.plist").write_bytes(plistlib.dumps({
        "CFBundleExecutable": "TerminationProbe", "CFBundleIdentifier": identity,
        "CFBundleName": "Termination Probe", "CFBundleVersion": "1",
        "CFBundlePackageType": "APPL", "LSUIElement": True,
    }))
    with (output / "build.log").open("w") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
    config = output / "config"
    config.write_text("auto-update = off\nwindow-save-state = never\nshell-integration = none\n"
                      "command = /usr/bin/true\ncopy-on-select = none\nclipboard-read = deny\n"
                      "clipboard-write = deny\ndesktop-notifications = false\n")
    pid_path = output / "child.pid"
    if args.real_child:
        child = output / "child.py"
        child.write_text("import os, pathlib, time\n"
                         f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()))\n"
                         "time.sleep(20)\n")
        with config.open("a") as stream:
            stream.write("confirm-close-surface = always\ncommand = direct:" +
                         shlex.join([sys.executable, str(child)]) + "\n")
    env = {key: value for key, value in os.environ.items() if not key.startswith(("DYLD_", "GHOSTTY_"))}
    env.update(GHOSTTY_CONFIG_PATH=str(config), GHOSTTY_USER_DEFAULTS_SUITE=identity,
               GHOSTTY_RESOURCES_DIR=str(candidate / "candidate-build/Debug/Ghostty.app/Contents/Resources/ghostty"),
               XDG_CONFIG_HOME=str(output / "xdgconfig"), XDG_CACHE_HOME=str(output / "xdgcache"))
    if args.real_child:
        env["GHOSTTY_CHILD_PID_PATH"] = str(pid_path)
    with (output / "run.log").open("w") as log:
        try:
            result = subprocess.run([str(executable)], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=30)
        finally:
            if args.real_child and pid_path.exists():
                pid = int(pid_path.read_text())
                until = time.monotonic() + 5
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    if time.monotonic() >= until:
                        raise RuntimeError(f"Probe child {pid} remains alive; do not blindly kill a reusable PID")
                    time.sleep(0.05)
    text = (output / "run.log").read_text()
    if args.negative:
        message = "real child sheet reply" if args.real_child else "single sheet response forwarded"
        accepted = result.returncode == 1 and f"FAIL: {message}" in text
    elif args.real_child:
        expected = {"PASS real child cancel", "PASS real child accept", "PASS real surface teardown reaps child"}
        accepted = result.returncode == 0 and set(text.splitlines()) == expected
    else:
        expected = {"PASS single cancel", "PASS single accept", "PASS multi cancel", "PASS multi terminate",
                    "PASS multi review-cancel", "PASS multi review-all",
                    "PASS native termination orchestration; no actual process termination"}
        accepted = result.returncode == 0 and set(text.splitlines()) == expected
    report = {"exit": result.returncode, "accepted": accepted, "negative_control": args.negative,
              "real_child": args.real_child}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if not accepted:
        raise RuntimeError("Termination probe did not meet its expected result; inspect run.log")


if __name__ == "__main__":
    main()
