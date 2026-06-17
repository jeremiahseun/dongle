#!/bin/bash
# ──────────────────────────────────────────────
# Dongle macOS Build Script
# ──────────────────────────────────────────────

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
CYAN="\033[0;36m"
RESET="\033[0m"

log() { echo -e "  ${CYAN}${*}${RESET}"; }
ok()  { echo -e "  ${GREEN}✓ ${*}${RESET}"; }

log "Starting Dongle build for macOS..."

# 1. Create venv if it doesn't exist
if [ ! -d "build_venv" ]; then
    log "Creating build virtual environment..."
    python3 -m venv build_venv
fi

source build_venv/bin/activate

# 2. Install dependencies
log "Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller
pip install -e .

# 3. Build standalone binaries with PyInstaller
log "Building standalone binaries..."

# Interactive picker binary (heavy)
pyinstaller --onefile \
    --noconfirm \
    --name dongle-pick \
    --add-data "dongle/shell:dongle/shell" \
    --hidden-import prompt_toolkit \
    --hidden-import pathspec \
    --clean \
    dongle/main.py

# CLI entry-point binary (lightweight dispatcher)
pyinstaller --onefile \
    --noconfirm \
    --name dongle \
    --add-data "dongle/shell:dongle/shell" \
    --hidden-import pathspec \
    --clean \
    dongle/init_cmd.py

deactivate

# 4. Install locally to ~/.dongle/bin
INSTALL_DIR="$HOME/.dongle/bin"
if [ -f "dist/dongle" ] && [ -f "dist/dongle-pick" ]; then
    log "Installing built binaries to ${INSTALL_DIR}..."
    mkdir -p "$INSTALL_DIR"
    cp dist/dongle "$INSTALL_DIR/dongle"
    cp dist/dongle-pick "$INSTALL_DIR/dongle-pick"
    cp dist/dongle-pick "$INSTALL_DIR/dongle-scan"
    cp dist/dongle-pick "$INSTALL_DIR/dongle-list"
    
    chmod +x \
        "$INSTALL_DIR/dongle" \
        "$INSTALL_DIR/dongle-pick" \
        "$INSTALL_DIR/dongle-scan" \
        "$INSTALL_DIR/dongle-list"
        
    ok "Build and installation successful! Standalone binaries located at: ${BOLD}${INSTALL_DIR}${RESET}"
    echo ""
    log "To test it:"
    echo "  dongle doctor"
else
    echo "Build failed: binaries not found in dist/"
    exit 1
fi
