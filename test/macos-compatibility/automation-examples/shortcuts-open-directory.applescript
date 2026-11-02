-- Accept a directory path as data, never concatenate it into shell source.
on run {input, parameters}
    set directoryPath to input as text
    if directoryPath does not start with "/" then error "Expected absolute directory path" number -1700
    set appPath to "/Applications/Ghostty.app"
    using terms from application "/Applications/Ghostty.app"
        tell application appPath
            set settings to new surface configuration
            set initial working directory of settings to directoryPath
            set w to new window with configuration settings
            return id of w
        end tell
    end using terms from
end run
