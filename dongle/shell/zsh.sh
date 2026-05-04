# Dongle — Zsh Integration
# Add to your ~/.zshrc:
#   eval "$(dongle init zsh)"

__dongle_widget() {
    local chosen
    chosen="$(dongle pick 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$BUFFER" ]; then
            cd "$chosen"
            local display="${chosen/#$HOME/~}"
            zle -M "  → $display"
            zle reset-prompt
        else
            LBUFFER="${LBUFFER}${chosen}"
        fi
    fi
    zle reset-prompt
}

__dongle_slash() {
    if [ -z "$BUFFER" ]; then
        __dongle_widget
    else
        LBUFFER="${LBUFFER}/"
    fi
}

zle -N __dongle_widget
zle -N __dongle_slash

bindkey "/"   __dongle_slash
bindkey "^_"  __dongle_widget   # Ctrl+/
bindkey "^O"  __dongle_widget   # Ctrl+O  (macOS fallback)
bindkey "^]p" __dongle_widget   # Ctrl+] p fallback

# dg — fuzzy search from current project root
dg() {
    local chosen
    chosen="$(dongle pick --query "$*" 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen"
}

# dgs — pre-scan & cache current project
dgs() { dongle scan "$@"; }

# dgw — workspace-wide fuzzy search
dgw() {
    local chosen
    chosen="$(dongle pick --workspace --query "$*" </dev/tty 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen"
}

# dgws — pre-scan workspaces
dgws() { dongle scan --workspace "$@"; }

# dgr — jump to project root immediately (no picker needed)
dgr() {
    local root
    root="$(dongle root)"
    [ $? -eq 0 ] && [ -n "$root" ] && cd "$root" && echo "  → ${root/#$HOME/~}"
}

# dgl — list all cached paths for current project
dgl() { dongle list "$@"; }

# dgrecent — show recently visited directories
dgrecent() { dongle recent; }

# Warm the cache in the background when a new shell opens
(dongle scan &>/dev/null &)
