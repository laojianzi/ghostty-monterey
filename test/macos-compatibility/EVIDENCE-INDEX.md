# Current local acceptance evidence

This index describes the current Intel Monterey ReleaseLocal acceptance, not
every historical experiment in STATUS.md. Product executable SHA256:
`8aa1ec74bb987e72cf2ecaa0a0723e2a5942d67614a14be6de779cd7fff195c2`.

## Retained evidence

| Area | Durable evidence | What it establishes |
| --- | --- | --- |
| Final verification | evidence/2026-11-02-final-verification | Fresh candidate unit/UI, rebuilt-resource archive and AX checks, matched 30-minute soak/30 teardown cycles, formal release gate refusal and cleanup |
| AX/automation follow-up | evidence/2026-11-01-ax-automation | New core/app/archive, live AX setter/rectangle and VoiceOver, scripting recipes, native input/IME, measured mapping cost and cleanup; see AX-AUTOMATION-WORK.md |
| Prior input, IME, unit/UI verdicts | evidence/2026-11-01-input | Actual PTY bytes, native IME, parsed Xcode results, keyboard red/green and ablations, fixed-width disposition |
| Cross-window focus | evidence/2026-11-01-focus | Artifact-specific four-direction, undo/redo/cancel and input routing evidence; use its own identity rather than silently relabeling old runs |
| Secure Input, progress, notifications, SSH | evidence/2026-11-01-nonax | Actual original-release and private-copy checks distinguished; eight-minute versus ten-minute workloads must not be conflated |
| Resource plateau, repeated teardown, Bell dispatch | evidence/2026-11-01-resource | Follow-up sampled workload and explicitly instrumented Bell observer; see RESOURCE-ACCEPTANCE.md |
| Prior matched build/archive/unit/UI logs | evidence/2026-11-01-resource/matched-build-test-logs | Four plaintext logs copied from the matching earlier successful runs, with source paths and SHA256 in origin.json |

The prior matched-build-test-logs are the preceding ReleaseLocal build, extended package test,
WeType-selected unit candidate and 27-method UI candidate. These are preserved
earlier results, not newly rerun tests. Large xcresult bundles remain outside the
repository; their parsed verdicts are retained in the input evidence. The bundle
identity and candidate differences still matter even when all logs are durable.

Each new evidence directory has a SHA256.json manifest. Checksums detect changed
evidence; they do not turn a failed result into a pass or authenticate a publisher.
Artifacts are not checked in: no app binaries, SSH private keys or dependency
environments are included. Logs contain development paths and synthetic fixture
data, not passwords or personal clipboard contents.

## Reproduction entry points

- Build: follow BUILDING.md and the repository-owned macos/build.nu entry.
- Unit execution: follow TEST-TOOLCHAIN.md and macos/test-monterey.py. Preserve
  candidate-only toolchain/source adaptations and the six explicit skips.
- Archive validation: follow BUILDING.md and macos/package-monterey.py. Match
  the executable identity before treating an old result as current evidence.
- Input-source regression: keyboard-layout-input-source-check.py; retain the
  pre-fix negative control rather than relying only on a successful launch.
- Native session scripts: inspect their report and prerequisites first. The
  archived scripts contain recorded PIDs, temporary paths and coordinates and
  are deliberately not advertised as safe portable unattended commands.

## Resource follow-up recipe

1. Use an isolated config/defaults suite, no personal shell startup, and a bounded
   own-PTY child. Keep the product binary unchanged. Set scrollback byte/line
   limits explicitly; a growing default history is not a leak test.
2. Record original foreground/input sources and the product hash. Poll the actual
   fixture child's PID file: the scripting pid may identify its login wrapper.
3. Emit the same ANSI/color/Unicode workload for eight minutes. Require exact
   DSR syntax and a five-second response deadline, not merely process survival.
   Record latency and RSS/CPU every five seconds; do not inject keyboard input
   into that PTY during the response check.
4. After idle sampling, create/load/close ten extra windows sequentially. Wait
   beyond undo retention, verify each child exits and one original window remains.
5. Evaluate the predeclared bounded RSS criteria, preserve failures, and restore
   the session. This is neither an overnight test nor a GPU presentation metric.

## Bell observer boundary

The session-only observer replaces selected Objective-C method implementations
and interposes NSBeep in a copied app, always forwarding to the original system
implementation. Disabled/enabled/disabled controls distinguish actual dispatch
from unrelated startup activity. NSSound playback returning true establishes
acceptance by the sound subsystem, not acoustic output from the speakers.
An informational attention request is not a frame-by-frame Dock animation test.
The observer is never linked into or shipped with the product.
