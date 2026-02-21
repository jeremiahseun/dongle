# Dongle — Zsh Integration
# Add to your ~/.zshrc:
#   source /path/to/dongle/shell/zsh.sh
# Or if installed via pip:
#   eval "$(dongle init zsh)"

__dongle_widget() {
    local chosen
    chosen="$(dongle-pick 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        if [ -z "$BUFFER" ]; then
            # Empty prompt: navigate directly
            cd "$chosen"
            local display="${chosen/#$HOME/~}"
            zle -M "  → $display"
            zle reset-prompt
        else
            # Insert into current buffer at cursor
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

# Bind / on empty line, Ctrl+/ anywhere
bindkey "/" __dongle_slash
bindkey "^_" __dongle_widget   # Ctrl+/
bindkey "^]p" __dongle_widget  # Ctrl+] p fallback

# Convenience shortcuts
dg() {
    local chosen
    chosen="$(dongle-pick 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen"
}

dgs() {
    dongle-scan "$@"
}

dgw() {
    local chosen
    chosen="$(dongle-pick --workspace </dev/tty 2>/dev/tty)"
    [ $? -eq 0 ] && [ -n "$chosen" ] && cd "$chosen"
}

dgws() {
    dongle-scan --workspace "$@"
}

# Auto pre-scan the current directory in the background on shell load
(dongle-scan &>/dev/null &)

echo "  🔌 Dongle loaded. Press / on empty prompt, Ctrl+/ anywhere, or type 'dg'"
