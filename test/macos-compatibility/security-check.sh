#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
for OPT in -Onone -O; do
    xcrun swiftc -swift-version 5 -enable-bare-slash-regex "$OPT" \
        -target "$(uname -m)-apple-macosx12.0" \
        "$ROOT/macos/Sources/Helpers/UntrustedURL.swift" \
        "$ROOT/macos/Sources/Helpers/Extensions/URL+Extension.swift" \
        "$ROOT/macos/Sources/Ghostty/Ghostty.Shell.swift" \
        "$ROOT/test/macos-compatibility/security.swift" -o "$TMP/check"
    "$TMP/check"
done
