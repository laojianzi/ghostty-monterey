# Non-selection acceptance follow-up

2026-11-01, Intel macOS 12.7.6, ReleaseLocal 1.4.0/build18457.
Source executable SHA256:
`c456ff946ec0242a7dd961170415844fbc40cf874d8c45ab77cb16228bb98ac7`.
No product source changes or rebuild were needed for this follow-up.

The user's latest instruction excludes AX selection work. The previously
demonstrated selected-text speech limitation remains recorded, not fixed or
passed. Signing/notarization, ARM, other hosts/OS versions and Japanese/Korean
layouts also remain excluded. This report supersedes older requests for human
acceptance of the representative paths below, not every possible configuration.

## Results

| Feature | Result | Observation and boundary |
| --- | --- | --- |
| Automatic Secure Input | Pass | Own canonical/no-echo PTY enables Carbon secure input; restoring echo disables it. No password was typed or collected. |
| Secure Input lifetime | Pass | App deactivation releases it, reactivation reacquires it; closing the secure surface in the unmodified ReleaseLocal releases it. |
| Global Secure Keyboard Entry | Pass | Native menu toggles on/off; inactive app yields and active app reacquires. Independent read-only Carbon probe observes state. |
| Progress | Pass | OSC 9;4 normal/error/paused/indeterminate reports expose expected labels and value descriptions; screenshots show the bar. Explicit removal, 15-second expiry and progress-style=false suppression pass. |
| Bell | Pass for visual paths | BEL marks the title and draws the border; focus clears the indication. Original ReleaseLocal screenshot inspected. Audio/system sound and Dock animation were not measured. |
| Command completion policy | Pass | Explicit OSC 133 markers: focused command suppressed by unfocused policy; short command suppressed by one-second threshold; long unfocused command triggers Bell. |
| Desktop notification | Pass on original ReleaseLocal | OSC 777 notification visible in native Notification Center; clicking it activates the source app and clears the item. |
| Command notifications | Pass on original ReleaseLocal | Success and exit-code-7 failure display the correct native notification title/body. Refocus clears the successful command notification. |
| SSH wrapper boundary | Pass, eight cases | Argument/env preservation, installation, cache hit/bypass, resolution/install fallback and exit status propagation. Fake ssh is only a boundary fixture. |
| Actual SSH transport | Pass, five cases | System OpenSSH connects to temporary key-authenticated loopback AsyncSSH server; real tic compilation and infocmp readback, cache hit, disabled features, install failure fallback and exit status 29. Not an external OpenSSH-server matrix. |
| Current-build bounded stability | Pass, ten minutes | 600.058 seconds, 5,780 DSR-checked cycles, 9,617,920 output bytes and 121 process samples. Not an overnight, GPU/frame-time or comparative performance benchmark. |

## Fixture failures and their disposition

- A successful NSRunningApplication activation request did not always change the
  foreground app during Secure Input. Assertions now exercise native Hide Ghostty,
  wait for transition and explicitly unhide on reactivation. No product focus
  change was made. The first too-early Hide/BEL sequence was also a harness race.
- SwiftUI exposes the progress value through AXValueDescription on this host,
  not AXValue. The observer was corrected; labels/values remain asserted.
- Private re-identified/ad-hoc copies were rejected by usernoted before delivery
  with UNErrorDomain code 1. Registering one fresh private bundle did not fix it.
  The unmodified original ReleaseLocal bundle receives authorization and adds
  notifications successfully; native Notification Center confirms actual delivery.
  This rules out a blanket claim that ReleaseLocal needs Developer ID for these
  tested notifications. No notification database or system security setting was
  changed; the existing original-bundle authorization was used.
- The SSH fixture first used an explicit remote command, which the unchanged
  upstream installer prepends to its install script. The successful fixture tests
  interactive sessions instead; explicit remote-command installation is not
  claimed. The wrapper continues with fallback when installation fails.
- macOS system tic 5.7 rejects `tic -x -`. The inherited upstream install script
  uses that syntax; the successful server fixture uses existing ncurses 6.6 tic.
  The system-tic failure correctly falls back to xterm-256color. No new product
  workaround was introduced for this remote-tool limitation.
- AsyncSSH's default input line editor initially consumed terminfo escapes;
  disabling the fixture line editor preserves the transfer. This is not a
  Ghostty terminal parser fix.
- SSH cache uses XDG_STATE_HOME, not XDG_CACHE_HOME. The first real-loopback run
  accidentally added its unique fixture@127.0.0.1:63712 entry to the user's cache.
  Only that exact test entry was removed with +ssh-cache --remove; the repeated
  passing run isolates HOME, cache and state directories. No personal hosts,
  keys or SSH configuration were used. No full cache clear was performed.

## Evidence and scope

Durable evidence is in `evidence/2026-11-01-nonax/`. Raw working fixtures remain
under `/tmp/ghostty-monterey/nonax-43`, `nonax-44` and `nonax-45`.
The 43/44 GUI fixtures copy the current release and alter only bundle identity,
ad-hoc signature and isolated runtime configuration. The 45 notification and
additional checks run the original, unmodified release executable in place with
isolated configuration/defaults. Do not confuse the source executable hash with
the changed signature bytes of a copied fixture executable.

The evidence scripts are session fixtures, not portable test entry points:
they contain temporary paths, observed PIDs and native UI coordinates. Private
SSH keys, dependencies and app binaries are deliberately not copied into the
repository. Native notification evidence is filtered to synthetic fixture content.
No personal notifications were acted upon. No system sshd or Remote Login was
enabled, and the temporary SSH server accepts only its generated fixture key on
127.0.0.1. Existing archive, unit and UI results in INPUT-ACCEPTANCE.md remain
applicable because the product executable is unchanged.

The bounded workload's RSS grows from 64,572 to 112,428 KiB (the observed peak)
while filling terminal scrollback and renderer caches. This is recorded resource
usage, not proof of a memory plateau or absence of leaks. Every workload cycle
received its DSR response within the five-second deadline; no crash or terminal
stall occurred. Temporary foreground changes for notification checks mean this
is a mixed focused/unfocused workload, not uninterrupted foreground rendering.

All three test apps and their PTY children exited. The loopback SSH listener is
closed. Foreground Finder, WeType and the complete enabled input-source inventory
match the initial snapshot exactly; Secure Input is off. The original executable
hash is unchanged. Only acceptance documentation/evidence was added this turn.
No commit, upload, system daemon enablement or security-policy change occurred.
