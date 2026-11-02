#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The app bridging header imports Foundation. Supply the same module import for
# this standalone build without changing the production UndoManager code.
{ printf 'import Foundation\n'; cat "$ROOT/macos/Sources/Helpers/ExpiringUndoManager.swift"; } > "$TMP/Undo.swift"
for OPT in -Onone -O; do
    xcrun swiftc -swift-version 5 "$OPT" -target "$(uname -m)-apple-macosx12.0" \
        "$ROOT/macos/Sources/Helpers/Extensions/Duration+Extension.swift" \
        "$TMP/Undo.swift" "$ROOT/test/macos-compatibility/undo-check.swift" -o "$TMP/check"
    "$TMP/check"
done
