#!/usr/bin/env python3
"""Run upstream Metal shaders on every local GPU without screen capture.

Compiles using MetallibStep's macOS flags. Native pipeline descriptions mirror
the Zig boundary; this is not execution of the Zig renderer or presentation.
"""

import os
import pathlib
import platform
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
shader = root / "src/renderer/shaders/shaders.metal"
runner = pathlib.Path(__file__).with_suffix(".swift")
with tempfile.TemporaryDirectory(prefix="ghostty-metal-") as directory:
    tmp = pathlib.Path(directory)
    binaries = {}
    for opt in ("-Onone", "-O"):
        binary = tmp / ("check" + opt)
        subprocess.run(["xcrun", "swiftc", opt, "-target", f"{platform.machine()}-apple-macosx12.0",
                        str(runner), "-o", str(binary)], check=True)
        binaries[opt] = binary
    for name in ("production", "zero-background", "no-padding-extension", "ignore-glyph-mask", "image-no-premultiply",
                 "background-no-repeat", "no-wide-cursor", "no-contrast", "no-linear-correction", "byte-vector-background"):
        source = shader.read_text()
        if name == "zero-background":
            start = source.index("fragment float4 bg_color_fragment(")
            end = source.index("\n}", start)
            body = source.index("{", start)
            source = source[:body + 1] + "\n  return float4(0.0);" + source[end:]
        elif name == "no-padding-extension":
            source = source.replace("uniforms.padding_extend & EXTEND_", "0u & EXTEND_")
            assert source != shader.read_text()
        elif name == "ignore-glyph-mask":
            source = source.replace("color *= a;", "color *= 1.0;")
            assert source != shader.read_text()
        elif name == "image-no-premultiply":
            start = source.index("fragment float4 image_fragment(")
            source = source[:start] + source[start:].replace("rgba.rgb *= rgba.a;", "rgba.rgb *= 1.0;")
            assert source != shader.read_text()
        elif name == "background-no-repeat":
            source = source.replace("if (in.repeat) {", "if (false) {")
            assert source != shader.read_text()
        elif name == "byte-vector-background":
            source = source.replace("uchar4(float4(float3(uniforms.bg_color.rgb), 255.0))",
                                    "uchar4(uniforms.bg_color.rgb, 255)")
            assert source != shader.read_text()
        elif name == "no-wide-cursor":
            source = source.replace("uniforms.cursor_wide &&", "false &&")
            assert source != shader.read_text()
        elif name == "no-contrast":
            source = source.replace("uniforms.min_contrast > 1.0f", "false")
            assert source != shader.read_text()
        elif name == "no-linear-correction":
            source = source.replace("if (uniforms.use_linear_correction) {", "if (false) {")
            assert source != shader.read_text()
        path = tmp / "shaders.metal"
        path.write_text(source)
        subprocess.run(["xcrun", "-sdk", "macosx", "metal", "-o", str(tmp / "shader.ir"),
                        "-c", str(path), "-mmacos-version-min=12.0"], check=True)
        library = tmp / "shader.metallib"
        subprocess.run(["xcrun", "-sdk", "macosx", "metallib", "-o", str(library),
                        str(tmp / "shader.ir")], check=True)
        for opt, binary in binaries.items():
            result = subprocess.run([str(binary), str(library)], text=True, capture_output=True, timeout=120,
                                    env=dict(os.environ, MTL_DEBUG_LAYER="1"))
            if name == "production":
                assert result.returncode == 0, result.stdout + result.stderr
                assert "error" not in result.stderr.lower(), result.stderr
                print(opt + ": " + result.stdout.strip(), flush=True)
            else:
                if name == "byte-vector-background" and result.returncode == 0:
                    print(opt + ": NOTE: byte-vector compiler regression not reproduced on these GPUs", flush=True)
                    continue
                assert result.returncode != 0 and "pixel mismatch" in result.stderr, result.stdout + result.stderr
                print(opt + f": PASS: compiled {name} mutant rejected", flush=True)
