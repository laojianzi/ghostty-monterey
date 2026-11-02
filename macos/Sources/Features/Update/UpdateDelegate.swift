import Sparkle
import Cocoa

extension UpdateDriver: SPUUpdaterDelegate {
    func feedURLString(for updater: SPUUpdater) -> String? {
        guard let appDelegate = NSApplication.shared.delegate as? AppDelegate else {
            return nil
        }

        let channel = appDelegate.ghostty.config.autoUpdateChannel == .tip ? "tip" : "stable"
        return try? MontereyUpdateConfiguration(info: Bundle.main.infoDictionary ?? [:]).feedURL(channel: channel)
    }

    func updater(_ updater: SPUUpdater, mayPerform updateCheck: SPUUpdateCheck) throws {
        guard let appDelegate = NSApplication.shared.delegate as? AppDelegate else {
            throw MontereyUpdateConfiguration.unavailable
        }
        let channel = appDelegate.ghostty.config.autoUpdateChannel == .tip ? "tip" : "stable"
        _ = try MontereyUpdateConfiguration(info: Bundle.main.infoDictionary ?? [:]).feedURL(channel: channel)
    }

    /// Called when an update is scheduled to install silently,
    /// which occurs when `auto-update = download`.
    ///
    /// When `auto-update = check`, Sparkle will call the corresponding
    /// delegate method on the responsible driver instead.
    func updater(_ updater: SPUUpdater, willInstallUpdateOnQuit item: SUAppcastItem, immediateInstallationBlock immediateInstallHandler: @escaping () -> Void) -> Bool {
        viewModel.state = .installing(.init(
            appcastItem: item,
            retryTerminatingApplication: immediateInstallHandler
        ))
        AppDelegate.logger.info("Version: \(item.displayVersionString) installed silently, waiting for relaunch...")
        // Even when hasUnobtrusiveTarget is false, we don't show the alert immediately.
        // We wait until the user manually checks for updates or relaunches.
        return true
    }
}

/// Distribution metadata, not user preferences, selects the trusted update source.
/// A missing channel must never fall back to upstream's incompatible binaries.
struct MontereyUpdateConfiguration {
    let info: [String: Any]

    static var unavailable: NSError {
        NSError(domain: "GhosttyMonterey.Update", code: 1, userInfo: [
            NSLocalizedDescriptionKey: "Updates are not configured for this Monterey build. Install a verified Monterey release manually.",
            NSLocalizedRecoverySuggestionErrorKey:
                "Install a verified Monterey release manually. The distributor must configure a Monterey appcast and its signing key to enable in-app updates.",
        ])
    }

    func feedURL(channel: String) throws -> String {
        guard let key = info["SUPublicEDKey"] as? String,
              key != "wsNcGf5hirwtdXMVnYoxRIX/SqZQLMOsYlD3q3imeok=",
              Data(base64Encoded: key)?.count == 32,
              let feeds = info["GhosttyMontereyUpdateFeeds"] as? [String: String],
              let feed = feeds[channel],
              let url = URLComponents(string: feed),
              url.scheme?.lowercased() == "https",
              let host = url.host?.lowercased(), !host.isEmpty, !host.hasSuffix("."),
              host != "ghostty.org", !host.hasSuffix(".ghostty.org"),
              url.user == nil, url.password == nil, url.fragment == nil,
              url.url != nil else {
            throw Self.unavailable
        }
        return feed
    }
}
