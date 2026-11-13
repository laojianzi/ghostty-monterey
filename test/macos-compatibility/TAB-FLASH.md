# Native tab flash: diagnosis and regression

## Scope and root cause

Issue: https://github.com/laojianzi/ghostty-monterey/issues/4#issuecomment-6621370895

Verified locally on Intel macOS 12.7.6, using Xcode 14.1 and ReleaseLocal.
The report describes a brief blank frame when switching tabs in 1.4.0 but not
1.3.1. Earlier local comparisons reproduced that distinction with both released
1.3.1 builds and 1.4.0-monterey.1; see the separate local diagnostics archive.

The failure is a shared IOSurface lifetime error, not a titlebar redraw policy:

1. `renderer/generic.zig:setVisible(false)` releases the hidden swapchain.
2. `renderer/metal/Target.zig:deinit` called `IOSurface.deinit`.
3. That wrapper explicitly calls `IOSurfaceSetPurgeable(kIOSurfacePurgeableEmpty)`
   before releasing its reference. Other owners retaining the surface cannot
   prevent this explicit discard of its pixels.
4. `IOSurfaceLayer` still holds the last frame through `CALayer.contents`, or
   retains a surface for a queued presentation. Revealing that layer before the
   next rendered frame exposes empty contents.

Upstream commit `c4e16970a803b170e352432424f44192cb59f3ac` introduced hidden-surface
GPU reclamation (PR #14017). Official v1.4.0 at
`83fb95624b0439ee660c2679b43b38c8b63769cd` has the same relevant reclamation and
forced-purge code. This explains why the older tab lifecycle did not expose the
bug. This is an upstream source comparison, **not** a runtime test of the official
v1.4.0 binary or of macOS 13/14. Those platforms were not tested here.

An exploratory CALayer/IOSurface probe also confirmed that dropping the creator's
reference with forced purge leaves the layer-retained surface in Empty state;
ordinary release leaves it NonVolatile. It corroborates the ownership diagnosis,
but the real compositor regression below is the acceptance test.

## Engineering choice

Change only `Target.deinit` to call the existing `IOSurface.release` API. The
render target drops its ownership without invalidating other owners' contents;
the Metal texture is still released. The shared surface survives until its last
owner releases it.

This preserves hidden-tab reclamation of the swapchain, font atlas copies, cell
buffers and custom shader textures. The layer normally retains the last displayed
surface per hidden terminal; pending presentations/compositor work can retain
additional surfaces transiently. This is not retention of the whole swapchain.
It does retain valid last-frame storage rather than forcibly emptying it; exact
GPU memory overhead has not been measured.

Do not disable hidden-resource reclamation, add timing delays, force speculative
redraws, or introduce macOS-version branches to hide the symptom. Do not change
the low-level `IOSurface.deinit` contract globally: fixing this shared-owner call
site is narrower and leaves unrelated exclusive-owner/error paths untouched.

## Reusable test

```sh
python3 test/macos-compatibility/tab-flash-check.py /path/to/Ghostty.app
python3 test/macos-compatibility/tab-flash-check.py /path/to/Ghostty.app --no-vsync
python3 test/macos-compatibility/tab-flash-check.py /path/to/Ghostty.app --native-titlebar
python3 test/macos-compatibility/tab-flash-check.py /path/to/Ghostty.app --continuous-output
```

Requires Python 3, Xcode command-line tools, an unlocked GUI session and existing
Accessibility/Screen Recording permissions. Restoring focus uses System Events
automation. Run sequentially with the test window unobstructed on the main
display. This actively switches tabs and temporarily takes focus.

The runner compiles `tab-flash-capture.swift`, copies/ad-hoc signs an isolated app,
disables default configuration loading, and uses a green terminal fixture over a
dark configured background. It never replaces the installed app. It terminates
only its own app and attempts to restore the previous foreground app.

A four-second steady baseline must pass before two fifteen-second rounds of 20
tab switches. Each round checks that all 20 actual visible window-ID changes
occurred between two native tabs, with stable bounds and foreground ownership.
The capture samples the on-screen compositor's central terminal region, not an
offscreen snapshot. Less than 95% green coverage is a failure. The runner exits
nonzero on invalid setup, failed switches or bad samples. It writes source binary
identity, options, CSV samples, unmodified PNG crops and logs to the printed
temporary evidence directory. Keep evidence separately; do not commit app copies.

These are screenshot **samples**, not unique display frames. Counts do not measure
flash duration or the percentage of switches affected. Sampling can miss shorter
transients, so zero bad samples is not proof for every machine/timing condition.

## Red-to-green results (2026-11-13)

Both builds use base commit `15192391a90812001f8b0c5be017dda142aed39c`, version
1.4.0/build18466 and the same local toolchain. The only production source change
in the fixed build is `Target.deinit`. Both core and app builds succeeded; the
app was built through `macos/build.nu --configuration ReleaseLocal --architecture x86_64`.

| Artifact / configuration | Round 1 bad / samples | Round 2 bad / samples | Verified switches | Verdict |
| --- | --- | --- | --- | --- |
| Clean source, before fix | 19 / 909 | 20 / 912 | 40 | FAIL (runner exit 1) |
| Fixed, default | 0 / 917 | 0 / 913 | 40 | PASS |
| Fixed, VSync off | 0 / 912 | 0 / 914 | 40 | PASS |
| Fixed, native titlebar | 0 / 915 | 0 / 922 | 40 | PASS |
| Fixed, continuous output | 0 / 874 | 0 / 878 | 40 | PASS |

All five steady baselines passed. Before the fix, captured crops show the dark
background replacing the green terminal. After the fix, every captured sample
in these four configurations retained full green coverage.

SHA-256 of original `Contents/MacOS/ghostty` (before test-copy re-signing):

- Clean: `6ccec7c44ed8996067c06b119e04c8b846fbd7da57971d9b5b4b82ed1bdd30c7`
- Fixed: `fb243cfb12ec5217a555b5fcb5588a0c435cbaa80b04755e889bb7041a4c54cf`

Additional targeted checks on the fixed artifact:

```sh
python3 test/macos-compatibility/app-smoke.py macos/build/ReleaseLocal/Ghostty.app --renderer-stress --lifecycle
python3 test/macos-compatibility/bundle-check.py macos/build/ReleaseLocal/Ghostty.app --architecture x86_64
```

- Renderer stress passed with Metal validation enabled: custom shaders,
  background images, resizing and Kitty raw/PNG transfer/replacement/cleanup in
  native, linear and linear-corrected blending modes.
- Four lifecycle batches passed: split/tab/window creation and closure, expiry
  of all 12 child PTYs, and preservation of the original surface/process/PTY.
  Startup, control/UTF-8 input, undo/redo and quick-terminal preservation also
  passed. Resource observations are recorded, not a proof of no GPU leaks.
- Intel bundle audit passed for all seven Mach-O files: deployment targets,
  dependencies, absence of coverage instrumentation and local bundle integrity.
  The first invocation omitted `--architecture x86_64` and failed the script's
  default universal-build requirement; the corrected Intel-scope command passed.
  No ARM runtime, distribution signing or notarization acceptance is claimed.
- Zig formatting, Python syntax and diff whitespace checks passed. The Swift
  capture helper compiled and ran. SwiftLint was unavailable and was not run.

Raw evidence is archived locally at
`~/Downloads/Ghostty-issue4-fix-20261113/`: regression CSV/PNG/results, build and
test logs, artifact identities and checksums. Exploratory lifetime-probe source
and output are kept there under `exploratory/`, not shipped as a regression test.

This is a targeted bug-fix acceptance record, not a new release certification or
a rerun of the entire frozen suite. No installed app replacement, commit, push
or publication is part of this verification.
