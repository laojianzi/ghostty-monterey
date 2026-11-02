-- Run with osascript: SCRIPT ABSOLUTE_APP_PATH OPERATION [ARGUMENT]
-- Operations target only the supplied app. Text input is never shell-evaluated here.
on run argv
    if (count argv) < 2 then error "Expected app path and operation" number -1700
    set appPath to item 1 of argv
    if appPath does not start with "/" then error "Use an absolute app path" number -1700
    set operation to item 2 of argv
    using terms from application "/Applications/Ghostty.app"
        tell application appPath
            if operation is "open" then
                set settings to new surface configuration
                if (count argv) > 2 then set initial working directory of settings to item 3 of argv
                set w to new window with configuration settings
                return id of w
            else if operation is "quick" then
                set ts to open quick terminal
                return id of item 1 of ts
            else if operation is "list" then
                set resultRows to {}
                repeat with t in terminals
                    set end of resultRows to {id of t, name of t, working directory of t, pid of t, tty of t}
                end repeat
                return resultRows
            end if
            if (count argv) < 3 then error "Expected terminal ID" number -1700
            set targetID to item 3 of argv
            set t to first terminal whose id is targetID
            if operation is "focus" then
                focus t
                return id of t
            else if operation is "close" then
                close t
                return true
            else if operation is "visible" then
                return visible text of t
            else if operation is "full" then
                return full contents of t
            else if operation is "selected" then
                return selected text of t
            else if operation is "action" then
                if (count argv) < 4 then error "Expected binding action" number -1700
                return perform action (item 4 of argv) on t
            else if operation is "split" then
                set childTerminal to split t direction right
                return id of childTerminal
            else if operation is "tab" then
                set newTab to new tab in front window
                return id of newTab
            else if operation is "ready" then
                repeat 40 times
                    if (pid of t) > 0 and (tty of t) is not "" then return {id of t, name of t, working directory of t, pid of t, tty of t}
                    delay 0.05
                end repeat
                error "Terminal metadata readiness timed out" number -1712
            end if
            error "Unknown operation" number -1700
        end tell
    end using terms from
end run
