#!/bin/bash
# ──────────────────────────────────────────────
# Dongle macOS Native Build Script (C++17)
# Zero dependencies, <2ms startup, single Mach-O binary
# ──────────────────────────────────────────────

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
RESET="\033[0m"

log() { echo -e "  ${CYAN}${*}${RESET}"; }
ok()  { echo -e "  ${GREEN}✓ ${*}${RESET}"; }

mkdir -p build_native

if [ "${1:-}" != "--install-only" ]; then
    log "Compiling native C++17 Dongle binary (clang++ -O3)..."
    clang++ -O3 -std=c++17 -Wall -Wextra src/dongle.cpp -o build_native/dongle
    strip build_native/dongle 2>/dev/null || true
    ok "Compiled build_native/dongle ($(du -h build_native/dongle | awk '{print $1}'))"
fi

INSTALL_DIR="$HOME/.dongle/bin"
LIB_DIR="$HOME/.dongle/lib"

log "Installing native binary to ${INSTALL_DIR}..."
mkdir -p "$INSTALL_DIR"
rm -rf "$LIB_DIR" 2>/dev/null || true

cp build_native/dongle "$INSTALL_DIR/dongle"
chmod +x "$INSTALL_DIR/dongle"

# Create symlinks for subcommand entrypoints (backwards compatibility)
ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-pick"
ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-scan"
ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-list"

# Cache shell init scripts so .zshrc / .bashrc source them with zero overhead
log "Caching shell init scripts..."
"$INSTALL_DIR/dongle" init zsh  > "$HOME/.dongle/zsh_init.zsh"  2>/dev/null && ok "Cached zsh init  → ~/.dongle/zsh_init.zsh"  || true
"$INSTALL_DIR/dongle" init bash > "$HOME/.dongle/bash_init.sh" 2>/dev/null && ok "Cached bash init → ~/.dongle/bash_init.sh" || true

# Ensure ~/.zshrc has PATH and shell integration
if [ -f "$HOME/.zshrc" ]; then
    if ! grep -qF "$INSTALL_DIR" "$HOME/.zshrc" 2>/dev/null; then
        echo "" >> "$HOME/.zshrc"
        echo "# Dongle — fast fuzzy directory navigation" >> "$HOME/.zshrc"
        echo "export PATH=\"\$HOME/.dongle/bin:\$PATH\"" >> "$HOME/.zshrc"
        ok "Added ~/.dongle/bin to PATH in ~/.zshrc"
    fi
    if ! grep -qF "zsh_init.zsh" "$HOME/.zshrc" 2>/dev/null && ! grep -qF "dongle init" "$HOME/.zshrc" 2>/dev/null; then
        echo "[ -f ~/.dongle/zsh_init.zsh ] && source ~/.dongle/zsh_init.zsh" >> "$HOME/.zshrc"
        ok "Added shell integration to ~/.zshrc"
    fi
fi

ok "Native C++ installation complete! Binary at: ${BOLD}${INSTALL_DIR}/dongle${RESET}"
echo ""
log "Verify with:"
echo "  dongle doctor"
