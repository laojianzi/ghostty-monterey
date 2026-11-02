#!/usr/bin/env python3
"""Fast negative controls for result acceptance; not Swift runtime coverage."""
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest


inspect_result = runpy.run_path(str(Path(__file__).with_name("run.py")))["inspect_result"]
library_link = runpy.run_path(str(Path(__file__).with_name("build-candidate.py")))["library_link"]


class ResultTests(unittest.TestCase):
    transfer = (
        "\u2714 Test actualSurfacePasteboardRoundTrip() passed after 0.1 seconds.\n"
        "\u2714 Test run with 1 test passed after 0.2 seconds.\n"
    )

    def test_targeted_success(self):
        self.assertTrue(inspect_result(self.transfer, 0, "transfer")["accepted"])

    def test_nonzero_exit(self):
        self.assertFalse(inspect_result(self.transfer, 1, "transfer")["accepted"])

    def test_empty(self):
        self.assertFalse(inspect_result("", 0, "transfer")["accepted"])

    def test_incomplete(self):
        text = self.transfer.splitlines()[0]
        self.assertFalse(inspect_result(text, 0, "transfer")["accepted"])

    def test_wrong_test(self):
        text = self.transfer.replace("actualSurfacePasteboardRoundTrip", "unrelated")
        self.assertFalse(inspect_result(text, 0, "transfer")["accepted"])

    def test_missing_original_suite(self):
        self.assertFalse(inspect_result(self.transfer, 0, "all")["accepted"])

    def test_recorded_issue(self):
        text = self.transfer + "Test actualSurfacePasteboardRoundTrip() recorded an issue\n"
        self.assertFalse(inspect_result(text, 0, "transfer")["accepted"])

    def test_unexpected_skip(self):
        text = self.transfer.replace("1 test passed", "2 tests passed")
        text += '\u2718 Test unexpected() skipped: "Requires macOS 13"\n'
        self.assertFalse(inspect_result(text, 0, "transfer")["accepted"])

    def test_exact_full_skip_inventory(self):
        text = self.transfer.splitlines()[0] + "\n"
        text += "".join(f"\u2714 Test case{n}() passed after 0.1 seconds.\n" for n in range(283))
        text += "\u2718 Test example() skipped.\n"
        for name in ("multipleTypesAreRegistered", "multipleTypesProvideCorrectData",
                     "pasteboardItemContainsExpectedType", "pasteboardItemIsCreated",
                     "pasteboardItemProvidesCorrectData"):
            text += f'\u2718 Test {name}() skipped: "Requires macOS 13"\n'
        text += "\u2714 Test run with 290 tests passed after 0.2 seconds.\n"
        self.assertTrue(inspect_result(text, 0, "all")["accepted"])
        altered = text.replace("pasteboardItemIsCreated() skipped", "different() skipped")
        self.assertFalse(inspect_result(altered, 0, "all")["accepted"])


class LinkTests(unittest.TestCase):
    def fixture(self, directory, objects):
        root = Path(directory)
        filelist = root / "original.list"
        filelist.write_text("\n".join(objects) + "\n")
        app = root / "candidate-build/Debug/Ghostty.app/Contents/MacOS/ghostty"
        (root / "app-build.log").write_text(
            f'/usr/bin/clang -target x86_64-apple-macos12.0 -filelist "{filelist}" '
            f'-Xlinker -dependency_info -Xlinker "{root}/Ghostty_dependency_info.dat" '
            f'-o "{app}"\n'
        )
        return root

    def test_excludes_only_main_and_preserves_app_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory, ["/objects/main.o", "/objects/SurfaceView.o"])
            args, excluded, objects = library_link(root)
            self.assertEqual(excluded, ["/objects/main.o"])
            self.assertEqual(objects, ["/objects/SurfaceView.o"])
            self.assertIn("-dynamiclib", args)
            self.assertIn(str(root / "test-library-dependency.dat"), args)
            self.assertEqual((root / "original.list").read_text(),
                             "/objects/main.o\n/objects/SurfaceView.o\n")

    def test_missing_or_duplicate_main_is_rejected(self):
        for objects in (["/objects/SurfaceView.o"], ["/objects/main.o", "/other/main.o"]):
            with self.subTest(objects=objects), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(RuntimeError, "exactly one main.o"):
                    library_link(self.fixture(directory, objects))


class CoreBuilderTests(unittest.TestCase):
    def test_invalid_jobs_before_compiler_execution(self):
        script = Path(__file__).with_name("build-core.py")
        for jobs in ("0", "9"):
            result = subprocess.run(
                [sys.executable, str(script), "--zig", "/missing/compiler",
                 "--dependency-cache", "/missing/cache", "--output", "/missing/output", "--jobs", jobs],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Use 1-8 jobs", result.stderr)


if __name__ == "__main__":
    unittest.main()
