# Dongle — Bash Integration
# Add to your ~/.bashrc:
#   source /path/to/dongle/shell/bash.sh
# Or if installed via pip:
#   eval "$(dongle init bash)"

__dongle_widget() {
    # Save current line
    local current_line="$READLINE_LINE"
    local current_point="$READLINE_POINT"

    # Run picker, capture output
    local chosen
    chosen="$(dongle-pick 2>/dev/tty)"

    if [ $? -eq 0 ] && [ -n "$chosen" ]; then
        # If the line already has content, replace it or cd directly
        if [ -z "$current_line" ]; then
            # Empty prompt: cd to the path
            cd "$chosen" && echo "  → $(pwd | sed "s|$HOME|~|")"
        else
            # Insert path into current command line
            READLINE_LINE="${current_line:0:$current_point}$chosen${current_line:$current_point}"
            READLINE_POINT=$(( current_point + ${#chosen} ))
            return
        fi
        # Redraw prompt
        READLINE_LINE=""
        READLINE_POINT=0
    fi
}

# Bind / key at the START of an empty line to trigger picker
# Bind Ctrl+/ anywhere to trigger picker
__dongle_slash() {
    if [ -z "$READLINE_LINE" ]; then
        __dongle_widget
    else
        READLINE_LINE="${READLINE_LINE:0:$READLINE_POINT}/${READLINE_LINE:$READLINE_POINT}"
        READLINE_POINT=$(( READLINE_POINT + 1 ))
    fi
}

# Keybindings
bind -x '"/":__dongle_slash'
bind -x '"":__dongle_widget'   # Ctrl+/

# Convenience shortcuts
alias dg='cd "$(dongle-pick)" && echo "  → $(pwd | sed "s|$HOME|~|")"'
alias dgs='dongle-scan'

# Tab completion for dongle command
_dongle_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    COMPREPLY=($(compgen -d -- "$cur"))
}
complete -F _dongle_complete dongle-pick dongle-scan

# Auto pre-scan the current directory in the background
(dongle-scan &>/dev/null &)

echo "  🔌 Dongle loaded. Press / on empty prompt or Ctrl+/ anywhere."
echo "  Also try: dg (launch picker)"
