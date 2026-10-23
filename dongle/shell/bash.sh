# Dongle — Bash Integration
# Add to your ~/.bashrc:
#   eval "$(dongle init bash)"

__dongle_widget() {
    local current_line="$READLINE_LINE"
    local current_point="$READLINE_POINT"
    local chosen
    chosen="$(dongle pick </dev/tty 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$current_line" ]; then
            cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
            READLINE_LINE=""
            READLINE_POINT=0
        else
            local escaped="${chosen// /\\ }"
            READLINE_LINE="${current_line:0:$current_point}$escaped${current_line:$current_point}"
            READLINE_POINT=$(( current_point + ${#escaped} ))
        fi
    fi
}

__dongle_slash() {
    if [ -z "$READLINE_LINE" ]; then
        if [ -c /dev/tty ] && { true </dev/tty; } 2>/dev/null; then
            __dongle_widget
        else
            READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
            READLINE_POINT=$(( READLINE_POINT + 1 ))
        fi
    else
        READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
        READLINE_POINT=$(( READLINE_POINT + 1 ))
    fi
}

bind -x '"/":__dongle_slash'
bind -x '"\C-_":__dongle_widget'   # Ctrl+/
bind -x '"\C-o":__dongle_widget'   # Ctrl+O

# dg — fuzzy search from current project root
dg() {
    local chosen
    chosen="$(dongle pick --query "$*" </dev/tty 2>/dev/tty)"
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

# dgpin — pin / unpin directory
alias dgpin='dongle pin'

# dgrecent — show recently visited directories
alias dgrecent='dongle recent'

# Tab completion for dongle subcommands
_dongle_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -d -- "$cur"))
}
complete -F _dongle_complete dongle

# Warm the cache in the background only when missing or stale
__dongle_warm_cache() {
    local cache="$HOME/.dongle_cache.json"
    local mtime=0
    if [ -f "$cache" ]; then
        mtime=$(stat -f %m "$cache" 2>/dev/null || stat -c %Y "$cache" 2>/dev/null || echo 0)
    fi
    if [ ! -f "$cache" ] || [ $(( $(date +%s) - mtime )) -gt 600 ]; then
        (dongle scan &>/dev/null &)
    fi
}
__dongle_warm_cache
unset -f __dongle_warm_cache
