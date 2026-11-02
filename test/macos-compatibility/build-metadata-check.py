#!/usr/bin/env python3
"""Exercise build.nu metadata with real local Git histories, without building.

Only the final `env -i ... xcodebuild` invocation is replaced by an argument
recorder. Nushell, Git, version parsing and preflight checks run unchanged.
No network access, source-repository commits or signing are performed.
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nu", default="nu", help="Nushell executable")
    args = parser.parse_args()
    nu = shutil.which(args.nu)
    assert nu, "Nushell not found"
    with tempfile.TemporaryDirectory(prefix="ghostty-build-metadata-") as directory:
        tmp = pathlib.Path(directory)
        source = tmp / "source"
        (source / "macos").mkdir(parents=True)
        shutil.copy2(ROOT / "macos/build.nu", source / "macos/build.nu")
        shutil.copy2(ROOT / "build.zig.zon", source / "build.zig.zon")
        git(source, "init", "--quiet")
        git(source, "config", "user.name", "Metadata Test")
        git(source, "config", "user.email", "metadata@example.invalid")
        git(source, "config", "commit.gpgsign", "false")
        git(source, "config", "core.hooksPath", str(tmp / "no-hooks"))
        git(source, "add", ".")
        for index in range(3):
            git(source, "commit", "--quiet", "--allow-empty", "-m", f"fixture {index}")

        # Intercept only the external env command used to launch Xcode. Its
        # arguments include the clean environment and all computed build values.
        tools = tmp / "tools"
        tools.mkdir()
        recorded = tmp / "arguments.json"
        recorder = tools / "env"
        recorder.write_text(
            f"#!{sys.executable}\nimport json, pathlib, sys\n"
            f"pathlib.Path({str(recorded)!r}).write_text(json.dumps(sys.argv[1:]))\n"
        )
        recorder.chmod(0o755)
        environment = dict(os.environ, PATH=f"{tools}:/usr/bin:/bin:/usr/sbin:/sbin")

        def invoke(repo):
            recorded.unlink(missing_ok=True)
            result = subprocess.run(
                [nu, "--no-config-file", str(repo / "macos/build.nu"),
                 "--configuration", "ReleaseLocal"],
                env=environment, capture_output=True, text=True,
            )
            values = json.loads(recorded.read_text()) if recorded.exists() else None
            return result, values

        revision = git(source, "rev-parse", "HEAD")
        result, values = invoke(source)
        assert result.returncode == 0, result.stdout + result.stderr
        assert values and values[0] == "-i" and "xcodebuild" in values, values
        assert "CURRENT_PROJECT_VERSION=3" in values, values
        assert f"GHOSTTY_COMMIT={revision}" in values, values
        assert f"GHOSTTY_BUILD=Monterey ReleaseLocal {revision}" in values, values
        assert "CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NO" in values, values
        print("PASS: full history produces exact clean revision and commit-count build")

        (source / "untracked.txt").write_text("local modification\n")
        result, values = invoke(source)
        assert result.returncode == 0, result.stdout + result.stderr
        assert f"GHOSTTY_COMMIT={revision}-dirty" in values, values
        assert "CURRENT_PROJECT_VERSION=3" in values, values
        print("PASS: untracked work is labeled dirty without changing the build count")

        shallow = tmp / "shallow"
        subprocess.run(["git", "clone", "--quiet", "--depth", "2", source.as_uri(), str(shallow)], check=True)
        assert git(shallow, "rev-parse", "--is-shallow-repository") == "true"
        assert git(shallow, "rev-list", "--count", "HEAD") == "2"
        result, values = invoke(shallow)
        assert result.returncode != 0 and "full Git history" in result.stdout + result.stderr, (
            "Shallow history must fail explicitly", result.returncode, result.stdout, result.stderr, values)
        assert values is None, "Shallow history reached Xcode"
        print("PASS: shallow history is rejected before Xcode/signing")

        # Recovery uses only the local fixture's objects, not a remote service.
        git(shallow, "fetch", "--quiet", "--unshallow")
        result, values = invoke(shallow)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "CURRENT_PROJECT_VERSION=3" in values and f"GHOSTTY_COMMIT={revision}" in values, values
        print("PASS: fetching full history restores the correct build identity")


if __name__ == "__main__":
    main()
