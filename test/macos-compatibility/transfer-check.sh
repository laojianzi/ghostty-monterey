#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for OPT in -Onone -O; do
    xcrun swiftc -swift-version 5 "$OPT" -target "$(uname -m)-apple-macosx12.0" \
        "$ROOT/macos/Sources/Helpers/Extensions/UUID+Extension.swift" \
        "$ROOT/macos/Sources/Ghostty/Surface View/SurfaceView+Transferable.swift" \
        "$ROOT/test/macos-compatibility/transfer-check.swift" -o "$TMP/check"
    "$TMP/check"
done
