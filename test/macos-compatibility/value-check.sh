#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for OPT in -Onone -O; do
    xcrun swiftc -swift-version 5 "$OPT" -target "$(uname -m)-apple-macosx12.0" \
        "$ROOT/macos/Sources/Helpers/Extensions/Duration+Extension.swift" \
        "$ROOT/macos/Sources/Helpers/Extensions/UUID+Extension.swift" \
        "$ROOT/macos/Sources/Helpers/Extensions/FileHandle+Extension.swift" \
        "$ROOT/macos/Sources/Helpers/Extensions/KeyboardShortcut+Extension.swift" \
        "$ROOT/test/macos-compatibility/value-check.swift" -o "$TMP/check"
    "$TMP/check"
done
