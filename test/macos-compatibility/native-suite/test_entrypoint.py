"""Fast checks for the public Monterey unit entry point; no Xcode execution."""
import argparse
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "macos/test-monterey.py"
commands = runpy.run_path(str(SCRIPT))["commands"]


class EntryPointTests(unittest.TestCase):
    def arguments(self, package=None):
        return argparse.Namespace(swiftc=Path("/tools/swiftc"), nu=Path("/tools/nu"),
                                  core_root=Path("/core"), source_packages=Path("/packages"),
                                  testing_package=package, skip_package_updates=True)

    def test_default_rebuilds_dependencies_then_prepares_then_runs_hosted(self):
        pipeline = commands(self.arguments(), Path("/output"))
        self.assertEqual([name for name, _ in pipeline], ["dependencies", "prepare", "xcode-unit"])
        self.assertIn("/tools/swift", pipeline[0][1])
        self.assertIn("--skip-update", pipeline[0][1])
        self.assertIn("--prepare-only", pipeline[1][1])
        self.assertIn("--hosted-test", pipeline[2][1])
        self.assertIn("/output/testing", pipeline[2][1])

    def test_reuse_requires_explicit_dependency_path(self):
        pipeline = commands(self.arguments(Path("/explicit/testing")), Path("/output"))
        self.assertEqual([name for name, _ in pipeline], ["prepare", "xcode-unit"])
        self.assertIn("/explicit/testing", pipeline[1][1])

    def invoke(self, output):
        return subprocess.run([sys.executable, str(SCRIPT), "--swiftc", "/missing/swiftc",
            "--nu", "/missing/nu", "--core-root", "/missing/core",
            "--source-packages", "/missing/packages", "--output", str(output)],
            capture_output=True, text=True, check=False)

    def test_refuses_worktree_before_starting_tools(self):
        result = self.invoke(ROOT / "must-not-create")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the worktree", result.stderr)
        self.assertFalse((ROOT / "must-not-create").exists())

    def test_refuses_existing_output_without_touching_it(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "owned"
            marker.write_text("keep")
            result = self.invoke(directory)
            self.assertEqual(result.returncode, 2)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(marker.read_text(), "keep")

    def test_refuses_missing_prerequisites_without_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new"
            result = self.invoke(output)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Missing prerequisite", result.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
