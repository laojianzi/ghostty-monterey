#!/usr/bin/env python3
"""Compile the unchanged cache implementation without the app's UI dependencies."""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
source = (ROOT / "macos/Sources/Ghostty/Surface View/SurfaceView_AppKit.swift").read_text()
start = source.index("class CachedValue<T> {")
end = source.index("/// Check if a UTF16 text", start)
with tempfile.TemporaryDirectory(prefix="ghostty-cache-") as directory:
    directory = pathlib.Path(directory)
    extracted = directory / "CachedValue.swift"
    extracted.write_text("import Foundation\n" + source[start:end])
    for optimization in ("-Onone", "-O"):
        subprocess.run([
            "xcrun", "swiftc", "-swift-version", "5", optimization,
            "-target", subprocess.check_output(["uname", "-m"], text=True).strip() + "-apple-macosx12.0",
            str(extracted),
            str(ROOT / "macos/Sources/Helpers/Extensions/Duration+Extension.swift"),
            str(ROOT / "test/macos-compatibility/cache-check.swift"),
            "-o", str(directory / "check"),
        ], check=True)
        subprocess.run([str(directory / "check")], check=True, timeout=30)
