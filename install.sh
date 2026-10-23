#!/usr/bin/env bash
# ──────────────────────────────────────────────
# Dongle Installer / Updater (Native C++17 Engine)
# Usage: curl -sSL https://raw.githubusercontent.com/jeremiahseun/dongle/main/install.sh | bash
# ──────────────────────────────────────────────

set -euo pipefail

REPO="jeremiahseun/dongle"
INSTALL_DIR="$HOME/.local/bin"
INIT_DIR="$HOME/.dongle"

# Detect OS & Arch
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux)
        if [ "$ARCH" = "x86_64" ]; then
            ARTIFACT="dongle-linux-x64"
        else
            echo "No pre-built binary for Linux $ARCH yet. Please install from source."
        fi
        ;;
    Darwin)
        if [ "$ARCH" = "x86_64" ]; then
            ARTIFACT="dongle-darwin-x64"
        elif [ "$ARCH" = "arm64" ]; then
            ARTIFACT="dongle-darwin-arm64"
        else
            echo "No pre-built binary for Darwin $ARCH yet. Please install from source."
        fi
        ;;
    *)
        echo "Unsupported OS: $OS"
        ;;
esac

header "⚡ Dongle Installer / Updater"
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

get_latest_tag() {
    curl -sSL "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
        | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/' || true
}

strip_v() { echo "${1#v}"; }

get_installed_version() {
    if [ -x "$INSTALL_DIR/dongle" ]; then
        "$INSTALL_DIR/dongle" version 2>/dev/null | awk '{print $2}' || true
    elif command -v dongle &>/dev/null; then
        dongle version 2>/dev/null | awk '{print $2}' || true
    fi
}

# ── Compile Native C++17 Engine from Source ───
compile_native_from_source() {
    header "Compiling Native C++17 Engine (<2ms startup)..."

    local CXX=""
    for compiler in clang++ g++ c++; do
        if command -v "$compiler" &>/dev/null; then
            CXX="$compiler"
            break
        fi
    done

    if [ -z "$CXX" ]; then
        return 1
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d)

    local src_file=""
    if [ -f "src/dongle.cpp" ]; then
        src_file="src/dongle.cpp"
        log "Using local src/dongle.cpp..."
    else
        log "Fetching latest src/dongle.cpp from GitHub..."
        if ! curl -fsSL "https://raw.githubusercontent.com/${REPO}/main/src/dongle.cpp" -o "${tmp_dir}/dongle.cpp"; then
            rm -rf "$tmp_dir"
            return 1
        fi
        src_file="${tmp_dir}/dongle.cpp"
    fi

    log "Compiling with ${CXX} -O3 -std=c++17..."
    mkdir -p "$INSTALL_DIR"
    rm -rf "$HOME/.dongle/lib" 2>/dev/null || true

    if "$CXX" -O3 -std=c++17 "$src_file" -o "$INSTALL_DIR/dongle" 2>/dev/null; then
        strip "$INSTALL_DIR/dongle" 2>/dev/null || true
        chmod +x "$INSTALL_DIR/dongle"
        ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-pick"
        ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-scan"
        ln -sf "$INSTALL_DIR/dongle" "$INSTALL_DIR/dongle-list"
        rm -rf "$tmp_dir"
        ok "Compiled & installed native binary at ${INSTALL_DIR}/dongle"
        add_to_path "$INSTALL_DIR"
        return 0
    fi

    rm -rf "$tmp_dir"
    return 1
}

# ── Download pre-built binary ─────────────────
install_via_binary() {
    local mode="${1:-install}"
    header "$([ "$mode" = "upgrade" ] && echo "Upgrading binary..." || echo "Downloading standalone binary...")"

    local artifact
    case "$PLATFORM" in
        darwin-arm64) artifact="dongle-darwin-arm64" ;;
        darwin-x64)   artifact="dongle-darwin-x64"   ;;
        linux-x64)    artifact="dongle-linux-x64"    ;;
        linux-arm64)  artifact="dongle-linux-arm64"  ;;
        *) error "No pre-built binary for platform: $PLATFORM" ;;
    esac

    local latest_tag
    latest_tag=$(get_latest_tag)
    if [ -z "$latest_tag" ]; then
        error "Could not determine the latest release. Check https://github.com/${REPO}/releases"
    fi
    ok "Latest release: ${latest_tag}"

    local tarball="${artifact}.tar.gz"
    local download_url="https://github.com/${REPO}/releases/download/${latest_tag}/${tarball}"

    log "Downloading ${tarball}..."

    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap "rm -rf '$tmp_dir'" EXIT

    local http_code
    http_code=$(curl -sSL -w "%{http_code}" -o "${tmp_dir}/${tarball}" "${download_url}")

    if [ "$http_code" != "200" ] || ! tar -tzf "${tmp_dir}/${tarball}" &>/dev/null; then
        error "Download failed (HTTP ${http_code}). Check https://github.com/${REPO}/releases"
    fi

    log "Extracting..."
    tar -xzf "${tmp_dir}/${tarball}" -C "${tmp_dir}"

    mkdir -p "$INSTALL_DIR"
    rm -rf "$HOME/.dongle/lib" 2>/dev/null || true
    cp -r "${tmp_dir}/${artifact}/"* "$INSTALL_DIR/"

    chmod +x \
        "$INSTALL_DIR/dongle" \
        "$INSTALL_DIR/dongle-pick" \
        "$INSTALL_DIR/dongle-scan" \
        "$INSTALL_DIR/dongle-list" 2>/dev/null || true

    ok "Binary $([ "$mode" = "upgrade" ] && echo "upgraded" || echo "installed") at ${INSTALL_DIR}/dongle"

    add_to_path "$INSTALL_DIR"

    trap - EXIT
    rm -rf "$tmp_dir"
}

# ── Cache shell init scripts ──────────────────
cache_init_scripts() {
    local init_dir="$HOME/.dongle"
    mkdir -p "$init_dir"

    if "$INSTALL_DIR/dongle" init zsh > "$init_dir/zsh_init.zsh" 2>/dev/null; then
        ok "Cached zsh init → ~/.dongle/zsh_init.zsh"
    fi
    if "$INSTALL_DIR/dongle" init bash > "$init_dir/bash_init.sh" 2>/dev/null; then
        ok "Cached bash init → ~/.dongle/bash_init.sh"
    fi
}

# ── Shell RC helpers ──────────────────────────
add_to_path() {
    local bin_dir="$1"
    local shell_name
    shell_name=$(basename "${SHELL:-zsh}")

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

    ok "Ensured $bin_dir is in PATH"
}

add_shell_integration() {
    local shell_name
    shell_name=$(basename "${SHELL:-zsh}")

    header "Shell Integration ($shell_name)"

    local rc_file init_line reload_cmd

    case "$shell_name" in
        bash)
            rc_file="$HOME/.bashrc"
            init_line='[ -f ~/.dongle/bash_init.sh ] && source ~/.dongle/bash_init.sh'
            reload_cmd="source ~/.bashrc"
            ;;
        zsh)
            rc_file="$HOME/.zshrc"
            init_line='[ -f ~/.dongle/zsh_init.zsh ] && source ~/.dongle/zsh_init.zsh'
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
            echo '    [ -f ~/.dongle/zsh_init.zsh ] && source ~/.dongle/zsh_init.zsh'
            return
            ;;
    esac

    if [ -f "$rc_file" ] && grep -qF 'eval "$(dongle init' "$rc_file"; then
        sed -i.bak 's|eval "\$(dongle init zsh)"|[ -f ~/.dongle/zsh_init.zsh ] \&\& source ~/.dongle/zsh_init.zsh|g' "$rc_file"
        sed -i.bak 's|eval "\$(dongle init bash)"|[ -f ~/.dongle/bash_init.sh ] \&\& source ~/.dongle/bash_init.sh|g' "$rc_file"
        ok "Migrated shell integration to source-based init in $rc_file"
    elif [ -f "$rc_file" ] && grep -qF "zsh_init.zsh" "$rc_file"; then
        ok "Shell integration already configured in $rc_file"
    elif [ -f "$rc_file" ] && grep -qF "bash_init.sh" "$rc_file"; then
        ok "Shell integration already configured in $rc_file"
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

if compile_native_from_source; then
    cache_init_scripts
    add_shell_integration
else
    install_via_binary "install"
    cache_init_scripts
    add_shell_integration
fi

# ── Show Welcome View ─────────────────────────
if [ -x "$INSTALL_DIR/dongle" ]; then
    "$INSTALL_DIR/dongle" welcome || true
fi

if [ -n "$RELOAD_CMD" ]; then
    echo -e "  Reload your shell to start using Dongle:"
    echo -e "  ${BOLD}${GREEN}${RELOAD_CMD}${RESET}"
    echo ""
fi
