# Monterey update distribution

The fork must not install an official Ghostty update over a Monterey build.
Official 1.4 is the functional baseline, not a compatible binary update source.

## Current behavior

The default local build has no update feed or public key. It does not start
Sparkle or resume its background schedule. A manual check reports that this
Monterey build needs a verified manual update. Changing `auto-update` or
`auto-update-channel` cannot select an official feed.

This is a distribution prerequisite, not an OS limitation: Sparkle remains
bundled and its existing download, verification, installation, and UI are kept.
When a distributor supplies valid metadata, the configured channel uses the
normal upstream updater path and `auto-update` preferences. No private signing
key is generated or committed by this adaptation.

## Enabling signed fork updates

Build through `macos/build.nu` with:

```sh
nu macos/build.nu --configuration ReleaseLocal \
  --update-key '<base64 Ed25519 public key>' \
  --update-stable-url 'https://<distributor>/monterey/stable.xml' \
  --update-tip-url 'https://<distributor>/monterey/tip.xml'
```

These are placeholders, not an existing service. The key and URLs enter the
Info.plist before signing. A missing/invalid selected channel is rejected; there
is no fallback between channels or to upstream. Official domains and the
upstream public key are rejected. Runtime policy validates HTTPS, key length,
and URL structure; it does not prove that a host or a supplied key is trusted.
Only the distributor should set these build parameters.

The distributor must own the matching private key, protect it outside the repo,
sign update archives with Sparkle, and publish a Monterey-only appcast. Keep
minimum-system/architecture metadata accurate and retain Sparkle's signature
verification. HTTP redirects must remain under the distributor's control.
Commit-count build numbers require full history and monotonically increasing
release revisions. The build wrapper rejects shallow clones; fetch full history
before building. Forks/rebases still require explicit release-order review.

Before enabling this in a public artifact, verify a full update cycle on macOS
12: discovery, both channels, invalid-signature rejection, download cancellation,
installation, relaunch, preservation of configuration, and framework loading.
Cross-building arm64 is not runtime evidence. These update-cycle gates have not
yet passed; merely supplying a syntactically valid URL/key does not satisfy them.

Ad-hoc ReleaseLocal distribution is not Developer ID notarization. Do not remove
the library-validation exception from ad-hoc bundles or claim Gatekeeper trust.
No release or update service is published by the compatibility tests.

## Local state-machine regression coverage

```sh
python3 test/macos-compatibility/update-state-check.py macos/build/ReleaseLocal/Ghostty.app
```

The check compiles the production UpdateViewModel/UpdateState with the matching
build-directory Sparkle 2.9.6 headers and verifies that the loaded framework is
the supplied app's embedded Sparkle. It adapts Swift Testing attributes and
assertions for 43 upstream test invocations across UpdateState, UpdateViewModel
and ReleaseNotes, preserving their bodies. Additional checks exercise cancel,
dismiss, install-confirm and termination-warning policy callbacks. Both
optimization modes must reject cancel-installs and confirm-retains-item mutants.

No updater is constructed, no feed is contacted, no preferences are changed and
no installation occurs. This is evidence for retained state/UI logic, not
SPUUserDriver delivery, update-signature validation or an end-to-end update.
Release-note URL tests preserve upstream informational links; those links are
not the allowed binary-update sources.
