#!/usr/bin/env bash
# ──────────────────────────────────────────────
# Dongle Installer
# Usage: curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh | bash
# ──────────────────────────────────────────────

set -euo pipefail

REPO="jeremiahseun/dongle"
INSTALL_DIR="$HOME/.dongle/bin"

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

header "🔌 Dongle Installer"
echo ""

# ── Detect OS and Architecture ────────────────
detect_platform() {
    local os arch
    os="$(uname -s)"
    arch="$(uname -m)"

    case "$os" in
        Darwin) os="darwin" ;;
        Linux)  os="linux"  ;;
        *)      error "Unsupported OS: $os. Dongle supports macOS and Linux." ;;
    esac

    case "$arch" in
        x86_64|amd64)   arch="x64"   ;;
        arm64|aarch64)  arch="arm64" ;;
        *)              error "Unsupported architecture: $arch" ;;
    esac

    echo "${os}-${arch}"
}

PLATFORM=$(detect_platform)
log "Detected platform: ${BOLD}${PLATFORM}${RESET}"

# ── Try pip install first ─────────────────────
install_via_pip() {
    header "Installing via pip..."

    local PYTHON=""
    if command -v python3 &>/dev/null; then
        PYTHON=python3
    elif command -v python &>/dev/null; then
        PYTHON=python
    fi

    if [ -z "$PYTHON" ]; then
        return 1
    fi

    # Check Python version >= 3.10
    local py_major py_minor
    py_major=$($PYTHON -c "import sys; print(sys.version_info.major)")
    py_minor=$($PYTHON -c "import sys; print(sys.version_info.minor)")

    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
        warn "Python $py_major.$py_minor found, but 3.10+ required. Falling back to binary."
        return 1
    fi

    # Check pip
    if ! $PYTHON -m pip --version &>/dev/null; then
        warn "pip not found. Falling back to binary."
        return 1
    fi

    ok "Python $py_major.$py_minor with pip found"

    # Try user install first, then system
    if $PYTHON -m pip install --user dongle 2>/dev/null; then
        ok "Dongle installed via pip (user)"
    elif $PYTHON -m pip install dongle 2>/dev/null; then
        ok "Dongle installed via pip (system)"
    else
        warn "pip install failed. Falling back to binary."
        return 1
    fi

    # Ensure ~/.local/bin is in PATH
    local LOCAL_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        add_to_path "$LOCAL_BIN"
    fi

    return 0
}

# ── Download pre-built binary ─────────────────
install_via_binary() {
    header "Installing standalone binary..."
    log "No Python required! Downloading pre-built binary for ${PLATFORM}..."

    # Get the latest release tag from GitHub
    local latest_tag
    latest_tag=$(curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name"' | head -1 | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

    if [ -z "$latest_tag" ]; then
        error "Could not determine the latest release. Check https://github.com/${REPO}/releases"
    fi

    ok "Latest release: ${latest_tag}"

    local binary_name="dongle-${PLATFORM}"
    local init_binary_name="dongle-${PLATFORM}-init"
    local base_url="https://github.com/${REPO}/releases/download/${latest_tag}"

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    # Download main binary
    log "Downloading ${binary_name}..."
    if ! curl -sSL -o "${INSTALL_DIR}/dongle-pick" "${base_url}/${binary_name}"; then
        error "Failed to download binary. Check your internet connection."
    fi
    chmod +x "${INSTALL_DIR}/dongle-pick"
    ok "Downloaded dongle-pick"

    # Download init binary
    log "Downloading ${init_binary_name}..."
    if ! curl -sSL -o "${INSTALL_DIR}/dongle" "${base_url}/${init_binary_name}"; then
        error "Failed to download init binary."
    fi
    chmod +x "${INSTALL_DIR}/dongle"
    ok "Downloaded dongle"

    # Create convenience symlinks
    ln -sf "${INSTALL_DIR}/dongle-pick" "${INSTALL_DIR}/dongle-scan"
    ln -sf "${INSTALL_DIR}/dongle-pick" "${INSTALL_DIR}/dongle-list"

    ok "Binaries installed to ${INSTALL_DIR}"

    # Add to PATH
    add_to_path "$INSTALL_DIR"
}

# ── Shell RC helpers ──────────────────────────
add_to_path() {
    local bin_dir="$1"
    local shell_name
    shell_name=$(basename "$SHELL")

    case "$shell_name" in
        bash)
            grep -qF "$bin_dir" "$HOME/.bashrc" 2>/dev/null || \
                echo "export PATH=\"$bin_dir:\$PATH\"" >> "$HOME/.bashrc"
            ;;
        zsh)
            grep -qF "$bin_dir" "$HOME/.zshrc" 2>/dev/null || \
                echo "export PATH=\"$bin_dir:\$PATH\"" >> "$HOME/.zshrc"
            ;;
        fish)
            local fish_cfg="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$fish_cfg")"
            grep -qF "$bin_dir" "$fish_cfg" 2>/dev/null || \
                echo "set -gx PATH $bin_dir \$PATH" >> "$fish_cfg"
            ;;
    esac

    ok "Added $bin_dir to PATH"
}

add_shell_integration() {
    local shell_name
    shell_name=$(basename "$SHELL")

    header "Shell Integration  ($shell_name detected)"

    local rc_file init_line reload_cmd

    case "$shell_name" in
        bash)
            rc_file="$HOME/.bashrc"
            init_line='eval "$(dongle init bash)"'
            reload_cmd="source ~/.bashrc"
            ;;
        zsh)
            rc_file="$HOME/.zshrc"
            init_line='eval "$(dongle init zsh)"'
            reload_cmd="source ~/.zshrc"
            ;;
        fish)
            rc_file="$HOME/.config/fish/config.fish"
            mkdir -p "$(dirname "$rc_file")"
            init_line='dongle init fish | source'
            reload_cmd="source $rc_file"
            ;;
        *)
            warn "Shell '$shell_name' not recognized. Add manually:"
            echo '    eval "$(dongle init bash)"  # for bash'
            echo '    eval "$(dongle init zsh)"   # for zsh'
            echo '    dongle init fish | source   # for fish'
            return
            ;;
    esac

    # Only add if not already present
    if [ -f "$rc_file" ] && grep -qF "dongle init" "$rc_file"; then
        warn "Dongle init already in $rc_file, skipping"
    else
        echo "" >> "$rc_file"
        echo "# Dongle — fast fuzzy directory navigation" >> "$rc_file"
        echo "$init_line" >> "$rc_file"
        ok "Added to $rc_file"
    fi

    RELOAD_CMD="$reload_cmd"
}

# ── Main ──────────────────────────────────────

RELOAD_CMD=""

# Try pip first, fall back to binary
if install_via_pip; then
    log "Installed via pip (Python)"
else
    install_via_binary
fi

# Set up shell integration
add_shell_integration

# ── Done ──────────────────────────────────────
header "Done! 🎉"
echo ""
echo -e "  Reload your shell to start using Dongle:"
echo -e "  ${BOLD}${RELOAD_CMD}${RESET}"
echo ""
echo -e "  ${CYAN}How to use:${RESET}"
echo -e "  Press ${BOLD}/${RESET} on an empty prompt → opens directory search"
echo -e "  Press ${BOLD}Ctrl+/${RESET} anywhere → opens directory search"
echo -e "  Type ${BOLD}dg${RESET}  → same as pressing /"
echo -e "  Type ${BOLD}dgw${RESET} → search across all your workspaces"
echo -e "  Type ${BOLD}dgs${RESET} → pre-scan & cache current directory"
echo ""
echo -e "  ${CYAN}Docs:${RESET} https://github.com/${REPO}"
echo ""
