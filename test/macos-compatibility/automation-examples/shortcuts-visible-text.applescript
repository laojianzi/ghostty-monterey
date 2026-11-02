-- Paste into Shortcuts' Run AppleScript action. Adjust BOTH app paths first.
on run {input, parameters}
    set appPath to "/Applications/Ghostty.app"
    using terms from application "/Applications/Ghostty.app"
        tell application appPath
            if (count windows) is 0 then error "No Ghostty window is open" number -1728
            set t to focused terminal of selected tab of front window
            return visible text of t
        end tell
    end using terms from
end run
