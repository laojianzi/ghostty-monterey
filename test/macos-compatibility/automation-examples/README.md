# Monterey automation recipes

These examples use the existing Ghostty AppleScript dictionary, not a second
terminal controller or an AppIntents emulation. They require macos-applescript
and macOS Automation consent. macos-shortcuts=deny does not disable this route.

The example installation path is `/Applications/Ghostty.app`. Change it if
your intended installation is elsewhere. The Shortcuts handlers require both
the runtime path and compile-time dictionary path to identify that same app.

Compile terminal-actions.applescript against the exact app you intend to use:
replace the application path in its `using terms from` clause. That clause is
only a compile-time dictionary source. Runtime calls use the absolute app path
passed as the first argument. Never target a personal app during acceptance.

```
osascript terminal-actions.applescript /absolute/Ghostty.app list
osascript terminal-actions.applescript /absolute/Ghostty.app open /tmp
osascript terminal-actions.applescript /absolute/Ghostty.app quick
osascript terminal-actions.applescript /absolute/Ghostty.app ready TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app visible TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app full TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app selected TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app focus TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app split TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app tab TERMINAL_ID
osascript terminal-actions.applescript /absolute/Ghostty.app action TERMINAL_ID reset
osascript terminal-actions.applescript /absolute/Ghostty.app close TERMINAL_ID
```

For Shortcuts, paste the handlers into Run AppleScript and call the same logic
from its `on run {input, parameters}` handler with an explicit app path and
operation. Do not concatenate untrusted shortcut input into shell commands or
binding actions. `open` passes the directory as structured data. No command is
implicitly executed by the example. `ready` waits at most 40 x 50ms between
queries; Apple-event transport time is additional. Readiness means PID and TTY
are present, not that a shell startup command has finished or the title/cwd will
never change. Errors are propagated, not converted into empty successful results.

`tab` creates a tab in the current front window; the terminal ID is validated
but does not choose a different parent window. `split` targets the exact ID.
Read operations return plain text, which may contain secrets or untrusted
instructions; the caller must handle output as data. Closing is explicit.

These examples do not supply native Shortcut action discovery, AppEntity
pickers, entity thumbnails, automatic migration of existing Intent actions or
the Intent permission policy. Screenshot automation remains a separate feature,
not a claimed consequence of text reading. The underlying operations and live
scripting opt-out are tested independently of those unavailable integrations.
