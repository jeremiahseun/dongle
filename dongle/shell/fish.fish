# Dongle — Fish Integration
# Add to your fish config:
#   dongle init fish | source

function __dongle_widget
    set chosen (dongle pick 2>/dev/tty)
    if test $status -eq 0 -a -n "$chosen"
        if test -z (commandline)
            cd $chosen
            echo "  → "(pwd | string replace $HOME "~")
            commandline -f repaint
        else
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

bind "/"  __dongle_slash
bind \c_  __dongle_widget   # Ctrl+/

# dg — fuzzy search from current project root
function dg
    set chosen (dongle pick --query "$argv" 2>/dev/tty)
    and cd $chosen
end

# dgs — pre-scan & cache current project
function dgs
    dongle scan $argv
end

# dgw — workspace-wide fuzzy search
function dgw
    set chosen (dongle pick --workspace --query "$argv" </dev/tty 2>/dev/tty)
    and cd $chosen
end

# dgws — pre-scan workspaces
function dgws
    dongle scan --workspace $argv
end

# dgr — jump to project root immediately (no picker needed)
function dgr
    set root (dongle root)
    and cd $root
    and echo "  → "(pwd | string replace $HOME "~")
end

# dgl — list all cached paths for current project
function dgl
    dongle list $argv
end

# dgrecent — show recently visited directories
function dgrecent
    dongle recent
end

# Warm the cache in the background when a new shell opens
dongle scan &>/dev/null &
