# Monterey compatibility maintenance

This directory contains reusable verification sources and the development
record for the macOS 12 port. It is not a collection of unconditional release
certificates. Read the artifact identity and scope of each result.

## Current entry points

- BUILDING.md: build and verification commands and tool prerequisites.
- RELEASE-READINESS.md: current acceptance index and unresolved boundaries.
- FINAL-VERIFICATION.md: latest recorded unit/UI, archive and resource results.
- AX-AUTOMATION-WORK.md: current AX implementation and acceptance limits.
- AUTOMATION.md and automation-examples/: scripting alternatives and policies.
- UPDATES.md: safe manual updates and requirements for a fork update service.
- PACKAGING-PLAN.md: proposed Intel-only packaging, not implemented options.
- native-suite/README.md: isolated Swift toolchain/test adaptations.

The original fixed-width UI expectation and incomplete unfiltered core run
remain recorded; committing these files does not resolve them. The validated
release artifacts predate this commit and are not relabeled as clean builds.

## Historical records and local evidence

STATUS.md, READINESS-HISTORY.md and older acceptance/research reports preserve
the investigation history. Earlier exclusions, pending statements and results
must not override the current index or be combined across different binaries.
Absolute temporary paths in those reports identify past sessions, not required
installation locations or portable commands.

Raw evidence/ files, large execution logs, screenshots and session-specific
helpers remain in the local evidence archive and are not shipped in this source
tree. EVIDENCE-INDEX.md describes their local inventory; its relative evidence
links require that separate archive. A fresh clone does not contain it. Publish
only a reviewed, sanitized archive separately if the evidence is needed.

The optional-ax/ directory retains an explanation of a superseded experiment;
its unapplied patch and historical source snapshots are local archive files,
not build/test dependencies. In contrast, native-suite/*.patch are required
inputs to the current isolated test workflow and are intentionally tracked.

Run GUI probes sequentially in an unlocked session. Inspect permissions and
cleanup requirements before invoking a probe; do not substitute a session-bound
script with recorded PIDs or coordinates for a reusable test entry point.
