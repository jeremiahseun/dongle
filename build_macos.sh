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
pip install prompt_toolkit pathspec pyinstaller

# 3. Build standalone binary
log "Building standalone binary with PyInstaller..."
# --add-data "source:destination"
# On macOS/Linux, destination is relative to the bundle root
pyinstaller --onefile \
    --name dongle \
    --add-data "dongle/shell:dongle/shell" \
    --clean \
    dongle/cli.py

deactivate

if [ -f "dist/dongle" ]; then
    ok "Build successful! Binary located at: ${BOLD}dist/dongle${RESET}"
    echo ""
    log "To test it:"
    echo "  ./dist/dongle version"
else
    echo "Build failed: dist/dongle not found."
    exit 1
fi
