# Resource and Bell acceptance follow-up

2026-11-01, Intel macOS 12.7.6, unchanged ReleaseLocal 1.4.0/build18457.
Executable SHA256:
`c456ff946ec0242a7dd961170415844fbc40cf874d8c45ab77cb16228bb98ac7`.
AX selection remains excluded. No product source change or rebuild is involved.

## Resource experiment

The prior ten-minute workload used default scrollback and grew from about
63 MiB to 110 MiB RSS. That observation alone cannot distinguish retained
history/caches from a leak. This follow-up fixes scrollback to 1,000,000 logical
bytes and 1,000 lines, uses the same finite glyph/style set, and continuously
replaces old history. Limits apply to newly created surfaces.

The unmodified original app runs an isolated own-PTY child for eight minutes,
emitting 64 ANSI/color/Unicode lines per cycle and requiring an exact DSR reply
within five seconds. Samples record RSS, accumulated CPU time and ps CPU percent
every five seconds. DSR latency measures terminal response, not GPU presentation.
After 30 seconds idle, ten additional windows are created, loaded for three
seconds and closed sequentially. Each fixture child must exit, and the original
window must remain. Undo retention is explicitly one second; post-close samples
wait beyond retention rather than treating an undoable surface as a leak.

Predeclared bounded criteria in the recorded runner:

- Final four minutes: RSS range below 8 MiB and net growth magnitude below 4 MiB.
- Ten close cycles: final post-close RSS less than 8 MiB above cycle-three RSS.
- Every output cycle has a valid, timely DSR reply; all ten children are reaped.

These are practical regression-screen thresholds, not statistical proof of no
leaks, an official performance budget or a comparison with a newer macOS build.
An initial harness attempt addressed the scripting PID (the login wrapper), not
the child PID. It emitted no workload and is not counted as a passing sample.
The corrected run reads the fixture's own PID file and has an explicit timeout.

The Bell probe briefly changes foreground application during the resource run;
this is recorded as a mixed active/inactive workload. No keyboard is injected
into the DSR workload. Do not report this as isolated uninterrupted foreground
rendering or infer frame-time equivalence from its response times.

### Measured result

Both predeclared bounded resource criteria pass, without changing product code.

| Metric | Result |
| --- | --- |
| Workload | 480.010 seconds, 20,169 cycles, 67,122,432 output bytes |
| DSR latency | Median 0.225 ms, p95 1.199 ms, maximum 9.647 ms |
| Final four minutes RSS | 59,104-60,092 KiB; net growth 940 KiB |
| Extra-window lifecycle | Ten of ten load/close cycles pass; all children reaped |
| Post-close RSS, cycle three to ten | 69,884 -> 71,100 KiB, growth 1,216 KiB |

The large default-history growth does not recur at that scale with bounded
history. This supports history/cache retention as an explanation for much of
the earlier growth, not a complete attribution or proof of leak freedom.
Post-close RSS does not return to the initial baseline and still rises slightly;
allocator/framework caching and small leaks cannot be separated by this short
experiment. There is no demonstrated runaway growth or stuck child in these
measured bounds. No official same-host or GPU performance parity is claimed.

## Bell subsystem checks

Five positive/negative checks pass on a copied ReleaseLocal with a temporary
observer dylib; this is instrumented evidence, not an unmodified-binary claim:

| Check | Actual observation |
| --- | --- |
| All three features disabled | BEL produces no observed sound/attention calls |
| Custom audio enabled | Original NSSound.play returns true; volume is 0.100 |
| System sound enabled | Original NSBeep is invoked through the Swift AppKit overlay |
| Background attention enabled | Original requestUserAttention receives informational type 10 and returns request 0 |
| Features disabled again | BEL again produces no observed sound/attention calls |

The custom sound is a generated 200 ms quiet tone, not a personal file. The system
Bell is invoked once in the successful run; no global volume/mute setting is
changed. The observer forwards all calls to their original implementations and
is never applied to the product bundle. The first observer incorrectly targeted
an Objective-C beep method: Swift uses its AppKit overlay and NSBeep instead.
Changing the observer, not the product, establishes the system call.

This closes subsystem dispatch/configuration coverage. No microphone recording,
physical speaker audibility assertion or frame-by-frame Dock bounce measurement
is made. Output-device/mute state can legitimately change audible results.
Visual title/border and focus clearing already pass on unmodified ReleaseLocal
in NONAX-ACCEPTANCE.md.

## Evidence and reproducibility

`evidence/2026-11-01-resource/` retains measured samples/results, fixture sources,
Bell observer and logs, plus the current artifact's full successful build,
archive, unit and UI logs copied from earlier runs. EVIDENCE-INDEX.md gives the
recipe, supported entry points and the limits of session-bound scripts.

RELEASE-READINESS.md is now a current-state index rather than a mixture of old
blockers and later passes. READINESS-HISTORY.md preserves its earlier chronology
without deleting failed assertions or pretending excluded features were fixed.
No full archive/test rebuild is justified by documentation-only changes.

All fixture apps and children exited. Foreground application and complete input
source snapshot match the start exactly; Secure Input is off. The original
executable hash is unchanged. No observer dylib, debug hook, audio setting or
test configuration was installed into the product or user's configuration.
