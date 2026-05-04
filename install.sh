#!/usr/bin/env bash
# ──────────────────────────────────────────────
# Dongle Installer / Updater
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
DIM="\033[2m"
RESET="\033[0m"

log()    { echo -e "  ${CYAN}${*}${RESET}"; }
ok()     { echo -e "  ${GREEN}✓ ${*}${RESET}"; }
warn()   { echo -e "  ${YELLOW}⚠ ${*}${RESET}"; }
error()  { echo -e "  ${RED}✗ ${*}${RESET}"; exit 1; }
header() { echo -e "\n${BOLD}${*}${RESET}"; }
dim()    { echo -e "  ${DIM}${*}${RESET}"; }

header "Dongle Installer / Updater"
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
        x86_64|amd64)  arch="x64"   ;;
        arm64|aarch64) arch="arm64" ;;
        *)             error "Unsupported architecture: $arch" ;;
    esac

    echo "${os}-${arch}"
}

PLATFORM=$(detect_platform)
log "Detected platform: ${BOLD}${PLATFORM}${RESET}"

# ── Version helpers ───────────────────────────

# Fetch the latest release tag from GitHub (returns e.g. "v0.3.0")
get_latest_tag() {
    curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" \
        | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/'
}

# Strip leading "v" from a version string
strip_v() { echo "${1#v}"; }

# Get the currently installed version ("0.3.0"), or empty string if not installed
get_installed_version() {
    if command -v dongle &>/dev/null; then
        dongle version 2>/dev/null | awk '{print $2}'
    fi
}

# Returns "pip", "binary", or "" (not installed)
detect_install_type() {
    if ! command -v dongle &>/dev/null; then
        echo ""
        return
    fi
    # pip-installed dongle can be detected via pip show
    local PYTHON=""
    for py in python3 python; do
        if command -v "$py" &>/dev/null; then
            PYTHON="$py"
            break
        fi
    done
    if [ -n "$PYTHON" ] && $PYTHON -m pip show dongle &>/dev/null 2>&1; then
        echo "pip"
        return
    fi
    # Fall back to checking if it's in our binary install dir
    echo "binary"
}

# ── Install via pip ───────────────────────────
install_via_pip() {
    local mode="${1:-install}"   # "install" or "upgrade"
    header "$([ "$mode" = "upgrade" ] && echo "Upgrading via pip..." || echo "Installing via pip...")"

    local PYTHON=""
    for py in python3 python; do
        if command -v "$py" &>/dev/null; then
            PYTHON="$py"
            break
        fi
    done

    if [ -z "$PYTHON" ]; then
        return 1
    fi

    local py_major py_minor
    py_major=$($PYTHON -c "import sys; print(sys.version_info.major)")
    py_minor=$($PYTHON -c "import sys; print(sys.version_info.minor)")

    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 10 ]; }; then
        warn "Python $py_major.$py_minor found, but 3.10+ required. Falling back to binary."
        return 1
    fi

    if ! $PYTHON -m pip --version &>/dev/null; then
        warn "pip not found. Falling back to binary."
        return 1
    fi

    ok "Python $py_major.$py_minor with pip found"

    local pip_flags="--upgrade"
    if $PYTHON -m pip install $pip_flags --user dongle 2>/dev/null; then
        ok "Dongle $([ "$mode" = "upgrade" ] && echo "upgraded" || echo "installed") via pip (user)"
    elif $PYTHON -m pip install $pip_flags dongle 2>/dev/null; then
        ok "Dongle $([ "$mode" = "upgrade" ] && echo "upgraded" || echo "installed") via pip (system)"
    else
        warn "pip install failed. Falling back to binary."
        return 1
    fi

    local LOCAL_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        add_to_path "$LOCAL_BIN"
    fi

    return 0
}

# ── Download pre-built binary ─────────────────
install_via_binary() {
    local mode="${1:-install}"
    header "$([ "$mode" = "upgrade" ] && echo "Upgrading binary..." || echo "Installing standalone binary...")"
    log "Downloading pre-built binary for ${PLATFORM}..."

    local latest_tag
    latest_tag=$(get_latest_tag)

    if [ -z "$latest_tag" ]; then
        error "Could not determine the latest release. Check https://github.com/${REPO}/releases"
    fi

    ok "Latest release: ${latest_tag}"

    local binary_name="dongle"
    local base_url="https://github.com/${REPO}/releases/download/${latest_tag}"

    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR" || error "Failed to cd to $INSTALL_DIR"

    log "Downloading ${binary_name}..."
    if ! curl -sSL -o "${binary_name}" "${base_url}/${binary_name}"; then
        error "Failed to download binary. Check your internet connection."
    fi

    chmod +x "${binary_name}"
    ok "Binary $([ "$mode" = "upgrade" ] && echo "upgraded" || echo "installed") at ${INSTALL_DIR}/${binary_name}"

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

    header "Shell Integration  ($shell_name)"

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
            warn "Shell '$shell_name' not recognised. Add manually:"
            echo '    eval "$(dongle init bash)"  # bash'
            echo '    eval "$(dongle init zsh)"   # zsh'
            echo '    dongle init fish | source   # fish'
            return
            ;;
    esac

    if [ -f "$rc_file" ] && grep -qF "dongle init" "$rc_file"; then
        ok "Shell integration already in $rc_file"
    else
        echo "" >> "$rc_file"
        echo "# Dongle — fast fuzzy directory navigation" >> "$rc_file"
        echo "$init_line" >> "$rc_file"
        ok "Added shell integration to $rc_file"
    fi

    RELOAD_CMD="$reload_cmd"
}

# ── Main ──────────────────────────────────────

RELOAD_CMD=""

INSTALLED_VERSION=$(get_installed_version)
INSTALL_TYPE=$(detect_install_type)

if [ -n "$INSTALLED_VERSION" ]; then
    # ── Already installed: check if an update is available ──
    log "Found existing install: dongle ${BOLD}${INSTALLED_VERSION}${RESET}"
    log "Checking for updates..."

    LATEST_TAG=$(get_latest_tag)
    LATEST_VERSION=$(strip_v "$LATEST_TAG")

    if [ -z "$LATEST_VERSION" ]; then
        warn "Could not reach GitHub to check for updates. Try again later."
        exit 0
    fi

    if [ "$INSTALLED_VERSION" = "$LATEST_VERSION" ]; then
        echo ""
        ok "Already up to date  (${BOLD}v${INSTALLED_VERSION}${RESET})"
        echo ""
        dim "Run 'dongle doctor' if something seems wrong."
        echo ""
        exit 0
    fi

    echo ""
    log "Update available: ${BOLD}v${INSTALLED_VERSION}${RESET} → ${GREEN}${BOLD}v${LATEST_VERSION}${RESET}"
    echo ""

    # Upgrade using the same method as the original install
    if [ "$INSTALL_TYPE" = "pip" ]; then
        install_via_pip "upgrade" || install_via_binary "upgrade"
    else
        install_via_binary "upgrade"
    fi

else
    # ── Fresh install ──
    if install_via_pip "install"; then
        log "Installed via pip"
    else
        install_via_binary "install"
    fi

    add_shell_integration
fi

# ── Done ──────────────────────────────────────
header "Done!"
echo ""
if [ -n "$RELOAD_CMD" ]; then
    echo -e "  Reload your shell to start using Dongle:"
    echo -e "  ${BOLD}${RELOAD_CMD}${RESET}"
    echo ""
fi
echo -e "  ${CYAN}Quick start:${RESET}"
echo -e "  Press ${BOLD}/${RESET} on an empty prompt    → open directory search"
echo -e "  Press ${BOLD}Ctrl+O${RESET} anywhere          → open directory search"
echo -e "  Type  ${BOLD}dg${RESET}                       → same as /"
echo -e "  Type  ${BOLD}dgw${RESET}                      → search across all your projects"
echo -e "  Type  ${BOLD}dgr${RESET}                      → jump to project root instantly"
echo ""
echo -e "  ${CYAN}Docs:${RESET} https://github.com/${REPO}"
echo ""
