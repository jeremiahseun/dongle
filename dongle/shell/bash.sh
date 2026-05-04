# Dongle — Bash Integration
# Add to your ~/.bashrc:
#   eval "$(dongle init bash)"

__dongle_widget() {
    local current_line="$READLINE_LINE"
    local current_point="$READLINE_POINT"
    local chosen
    chosen="$(dongle pick 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$current_line" ]; then
            cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
            READLINE_LINE=""
            READLINE_POINT=0
        else
            READLINE_LINE="${current_line:0:$current_point}$chosen${current_line:$current_point}"
            READLINE_POINT=$(( current_point + ${#chosen} ))
        fi
    fi
}

__dongle_slash() {
    if [ -z "$READLINE_LINE" ]; then
        __dongle_widget
    else
        READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
        READLINE_POINT=$(( READLINE_POINT + 1 ))
    fi
}

bind -x '"/":__dongle_slash'
bind -x '"":__dongle_widget'   # Ctrl+/

# dg — fuzzy search from current project root
dg() {
    local chosen
    chosen="$(dongle pick --query "$*" 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

# dgs — pre-scan & cache current project
alias dgs='dongle scan'

# dgw — workspace-wide fuzzy search
dgw() {
    local chosen
    chosen="$(dongle pick --workspace --query "$*" </dev/tty 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

# dgws — pre-scan workspaces
alias dgws='dongle scan --workspace'

# dgr — jump to project root immediately (no picker needed)
dgr() {
    local root
    root="$(dongle root)"
    [ $? -eq 0 ] && [ -n "$root" ] && cd "$root" && echo "  → $(pwd | sed "s|$HOME|~|")"
}

# dgl — list all cached paths for current project
alias dgl='dongle list'

# dgrecent — show recently visited directories
alias dgrecent='dongle recent'

# Tab completion for dongle subcommands
_dongle_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -d -- "$cur"))
}
complete -F _dongle_complete dongle pick scan

# Warm the cache in the background when a new shell opens
(dongle scan &>/dev/null &)
