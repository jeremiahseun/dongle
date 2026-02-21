# Dongle — Fish Integration
# Add to your fish config:
#   source /path/to/dongle/shell/fish.fish
# Or if installed via pip:
#   dongle init fish | source

function __dongle_widget
    set chosen (dongle-pick 2>/dev/tty)
    if test $status -eq 0 -a -n "$chosen"
        if test -z (commandline)
            # Empty prompt: navigate
            cd $chosen
            commandline -f repaint
            echo "  → "(pwd | string replace $HOME "~")
        else
            # Insert at cursor
            commandline -i $chosen
        end
    end
    commandline -f repaint
end

function __dongle_slash
    if test -z (commandline)
        __dongle_widget
    else
        commandline -i "/"
    end
end

# Keybinding: / on empty prompt triggers picker
bind "/" __dongle_slash
bind \c_ __dongle_widget   # Ctrl+/

# Convenience functions
function dg
    set chosen (dongle-pick 2>/dev/tty)
    and cd $chosen
end

function dgs
    dongle-scan $argv
end

# Auto pre-scan the current directory in the background
dongle-scan &>/dev/null &

echo "  🔌 Dongle loaded. Press / on empty prompt, Ctrl+/ anywhere, or use dg"
