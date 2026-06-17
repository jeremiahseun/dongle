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

# 3. Build directory bundles with PyInstaller (--onedir = no per-run extraction, fast startup)
log "Building standalone binaries..."

# Interactive picker binary (heavy — includes prompt_toolkit)
pyinstaller --onedir \
    --noconfirm \
    --name dongle-pick \
    --add-data "dongle/shell:dongle/shell" \
    --hidden-import prompt_toolkit \
    --hidden-import pathspec \
    --clean \
    dongle/main.py

# CLI entry-point binary (lightweight dispatcher)
pyinstaller --onedir \
    --noconfirm \
    --name dongle \
    --add-data "dongle/shell:dongle/shell" \
    --hidden-import pathspec \
    --clean \
    dongle/init_cmd.py

deactivate

# 4. Install directory bundles to ~/.dongle/lib, thin wrapper scripts to ~/.dongle/bin
INSTALL_DIR="$HOME/.dongle/bin"
LIB_DIR="$HOME/.dongle/lib"

if [ -d "dist/dongle" ] && [ -d "dist/dongle-pick" ]; then
    log "Installing to ${LIB_DIR} and ${INSTALL_DIR}..."
    mkdir -p "$INSTALL_DIR" "$LIB_DIR"

    # Replace old lib bundles
    rm -rf "$LIB_DIR/dongle" "$LIB_DIR/dongle-pick"
    cp -r dist/dongle     "$LIB_DIR/dongle"
    cp -r dist/dongle-pick "$LIB_DIR/dongle-pick"

    # Create thin wrapper scripts (no extraction needed; just exec the real binary)
    _write_wrapper() {
        local name="$1" target="$2"
        cat > "$INSTALL_DIR/$name" <<WRAPPER
#!/bin/sh
exec "$LIB_DIR/$target/$target" "\$@"
WRAPPER
        chmod +x "$INSTALL_DIR/$name"
    }

    _write_wrapper dongle      dongle
    _write_wrapper dongle-pick dongle-pick
    _write_wrapper dongle-scan dongle-pick
    _write_wrapper dongle-list dongle-pick

    # Cache the shell init script so .zshrc can source it without spawning a subprocess
    log "Caching shell init scripts..."
    "$LIB_DIR/dongle/dongle" init zsh  > "$HOME/.dongle/zsh_init.zsh"  2>/dev/null && ok "Cached zsh init  → ~/.dongle/zsh_init.zsh"  || true
    "$LIB_DIR/dongle/dongle" init bash > "$HOME/.dongle/bash_init.sh" 2>/dev/null && ok "Cached bash init → ~/.dongle/bash_init.sh" || true

    ok "Build and installation successful! Binaries at: ${BOLD}${INSTALL_DIR}${RESET}"
    echo ""
    log "To test it:"
    echo "  dongle doctor"
else
    echo "Build failed: dist/dongle or dist/dongle-pick directory not found"
    exit 1
fi
