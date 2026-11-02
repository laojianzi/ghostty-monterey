#!/usr/bin/env python3
"""Negative controls for source metadata and architecture contracts."""

import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "macos"))
import release_source

spec = importlib.util.spec_from_file_location("bundle", ROOT / "test/macos-compatibility/bundle-check.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class PreflightTests(unittest.TestCase):
    def test_architectures(self):
        bundle.check_architectures({"x86_64"}, "x86_64", True)
        bundle.check_architectures({"x86_64", "arm64"}, "x86_64", False)
        for actual, contract, primary in [({"arm64"}, "x86_64", False),
                                          ({"x86_64"}, "universal", True),
                                          ({"x86_64", "arm64"}, "x86_64", True)]:
            with self.assertRaises(AssertionError):
                bundle.check_architectures(actual, contract, primary)

    def test_metadata(self):
        identity = {"version": "1.4.0", "build": "18462", "commit": "a" * 40}
        info = {"CFBundleShortVersionString": "1.4.0", "CFBundleVersion": "18462",
                "GhosttyCommit": "a" * 40, "GhosttyBuild": "Monterey ReleaseLocal " + "a" * 40}
        release_source.validate_metadata(info, identity)
        for key in info:
            altered = dict(info, **{key: "wrong"})
            with self.assertRaises(ValueError):
                release_source.validate_metadata(altered, identity)

    def test_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "build.zig.zon").write_text('.{ .version = "1.4.0" }\n')
            for args in [("add", "."), ("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                                       "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null",
                                       "commit", "-qm", "fixture")]:
                release_source.git(root, *args)
            self.assertEqual(release_source.source_identity(root)["build"], "1")
            (root / "unexpected").write_text("dirty")
            with self.assertRaises(ValueError):
                release_source.source_identity(root)


if __name__ == "__main__":
    unittest.main()
