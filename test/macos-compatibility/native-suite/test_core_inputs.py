"""Reject stale or altered core inputs before the expensive candidate build."""
import json
from pathlib import Path
import runpy
import tempfile
import unittest


MODULE = runpy.run_path(str(Path(__file__).with_name("core-inputs.py")))


class CoreInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.core = self.root / "build/source"
        self.current = self.root / "current"
        self.names = ["build.zig", "src/main.zig", "macos/Sources/main.swift"]
        for directory in (self.core, self.current):
            for name in self.names:
                path = directory / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original")
        self.artifact = self.core / "macos/GhosttyKit.xcframework/ghostty.a"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_bytes(b"archive")
        self.inputs = self.core.parent / "inputs.json"
        self.result = self.core.parent / "result.json"
        self.inputs.write_text(json.dumps({"files": {n: MODULE["metadata"](self.core / n) for n in self.names}}))
        self.result.write_text(json.dumps({"exit": 0, "architectures": ["x86_64", "arm64"],
            "artifact_sha256": {str(self.artifact.relative_to(self.core)): MODULE["digest"](self.artifact)}}))

    def verify(self):
        return MODULE["verify"](self.core, self.current, self.names)

    def test_matching_snapshot(self):
        self.assertTrue(self.verify()["verified_snapshot"])

    def test_swift_only_edit_does_not_stale_zig_core(self):
        (self.current / "macos/Sources/main.swift").write_text("changed")
        self.assertTrue(self.verify()["verified_snapshot"])

    def test_changed_current_core_source(self):
        (self.current / "src/main.zig").write_text("changed")
        with self.assertRaisesRegex(ValueError, "source differs"):
            self.verify()

    def test_changed_snapshot_source(self):
        (self.core / "src/main.zig").write_text("changed")
        with self.assertRaisesRegex(ValueError, "source differs"):
            self.verify()

    def test_added_and_deleted_source(self):
        (self.current / "src/new.zig").write_text("new")
        self.names.append("src/new.zig")
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            self.verify()
        self.names.pop()
        (self.current / "src/main.zig").unlink()
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            self.verify()

    def test_modified_artifact(self):
        self.artifact.write_bytes(b"wrong archive")
        with self.assertRaisesRegex(ValueError, "artifact differs"):
            self.verify()

    def test_extra_artifact(self):
        self.artifact.with_name("extra.a").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "artifact inventory"):
            self.verify()

    def test_missing_provenance(self):
        self.result.unlink()
        with self.assertRaisesRegex(ValueError, "requires build-core"):
            self.verify()

    def test_failed_build_not_accepted(self):
        value = json.loads(self.result.read_text())
        value["exit"] = 1
        self.result.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "successful universal"):
            self.verify()

    def test_worktree_not_misrepresented_as_verified(self):
        self.assertFalse(MODULE["verify"](self.current, self.current)["verified_snapshot"])

    def test_unsafe_path(self):
        for name in ("/tmp/escape", "src/../../escape", ""):
            with self.subTest(name=name), self.assertRaises(ValueError):
                MODULE["safe_relative"](name)


if __name__ == "__main__":
    unittest.main()
