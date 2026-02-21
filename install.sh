#!/usr/bin/env bash
# Dongle Installer
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/dongle/main/install.sh | bash

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

log()    { echo -e "  ${CYAN}${*}${RESET}"; }
ok()     { echo -e "  ${GREEN}✓ ${*}${RESET}"; }
warn()   { echo -e "  ${YELLOW}⚠ ${*}${RESET}"; }
error()  { echo -e "  ${RED}✗ ${*}${RESET}"; exit 1; }
header() { echo -e "\n${BOLD}${*}${RESET}"; }

header "Dongle Installer"
echo ""

# ── Check Python ──────────────────────────────
log "Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    error "Python 3.10+ is required. Install from https://python.org"
fi

PY_VER=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    error "Python 3.10+ required. You have $PY_VER"
fi
ok "Python $PY_VER found"

# ── Check pip ─────────────────────────────────
log "Checking pip..."
if ! $PYTHON -m pip --version &>/dev/null; then
    warn "pip not found, attempting to install..."
    $PYTHON -m ensurepip --upgrade || error "Could not install pip"
fi
ok "pip ready"

# ── Install dongle ────────────────────────
log "Installing Dongle..."
INSTALL_FLAG=""
# Try user install first, fall back to system
if $PYTHON -m pip install --user dongle 2>/dev/null; then
    ok "Dongle installed (user)"
    # Ensure ~/.local/bin is in PATH
    LOCAL_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        warn "~/.local/bin not in PATH — we'll add it for you"
        NEED_PATH_FIX=1
    fi
else
    log "Trying system install..."
    pip install dongle || error "Installation failed. Try: pip install dongle"
    ok "Dongle installed (system)"
fi

# ── Detect shell ──────────────────────────────
SHELL_NAME=$(basename "$SHELL")
header "Shell Integration  ($SHELL_NAME detected)"

add_to_rc() {
    local rc="$1"
    local line="$2"
    local expanded="${rc/#\~/$HOME}"
    if [ -f "$expanded" ] && grep -qF "dongle" "$expanded"; then
        warn "Dongle already in $rc, skipping"
        return
    fi
    echo "" >> "$expanded"
    echo "# Dongle" >> "$expanded"
    echo "$line" >> "$expanded"
    ok "Added to $rc"
}

case "$SHELL_NAME" in
    bash)
        add_to_rc "~/.bashrc" 'eval "$(dongle init bash)"'
        RELOAD="source ~/.bashrc"
        ;;
    zsh)
        add_to_rc "~/.zshrc" 'eval "$(dongle init zsh)"'
        RELOAD="source ~/.zshrc"
        ;;
    fish)
        FISH_CFG="$HOME/.config/fish/config.fish"
        mkdir -p "$(dirname "$FISH_CFG")"
        add_to_rc "$FISH_CFG" 'dongle init fish | source'
        RELOAD="source $FISH_CFG"
        ;;
    *)
        warn "Shell '$SHELL_NAME' not recognized. Add manually:"
        echo '    eval "$(dongle init bash)"  # for bash'
        echo '    eval "$(dongle init zsh)"   # for zsh'
        RELOAD=""
        ;;
esac

# ── PATH fix ──────────────────────────────────
if [ "${NEED_PATH_FIX:-0}" = "1" ]; then
    case "$SHELL_NAME" in
        bash) echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" ;;
        zsh)  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" ;;
        fish) echo 'set -gx PATH $HOME/.local/bin $PATH' >> "$HOME/.config/fish/config.fish" ;;
    esac
    ok "Added ~/.local/bin to PATH"
fi

# ── Done ──────────────────────────────────────
header "Done! 🎉"
echo ""
echo -e "  Reload your shell to start using Dongle:"
echo -e "  ${BOLD}${RELOAD}${RESET}"
echo ""
echo -e "  ${CYAN}How to use:${RESET}"
echo -e "  Press ${BOLD}/${RESET} on an empty prompt → opens directory search"
echo -e "  Press ${BOLD}Ctrl+/${RESET} anywhere → opens directory search"
echo -e "  Type ${BOLD}ph${RESET} → same as above"
echo -e "  Type ${BOLD}phs${RESET} → pre-scan & cache current directory"
echo ""
echo -e "  ${CYAN}Docs:${RESET} https://github.com/yourusername/dongle"
echo ""
