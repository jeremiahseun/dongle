#!/bin/bash

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

echo "=> Fetching latest release tag..."
LATEST_TAG=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep -Po '"tag_name": "\K.*?(?=")')

echo "=> Downloading $ARTIFACT $LATEST_TAG..."
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/$ARTIFACT.tar.gz"

TMP_DIR=$(mktemp -d)
curl -sSL "$DOWNLOAD_URL" -o "$TMP_DIR/$ARTIFACT.tar.gz"

echo "=> Extracting..."
tar -xzf "$TMP_DIR/$ARTIFACT.tar.gz" -C "$TMP_DIR"

mkdir -p "$INSTALL_DIR"
cp "$TMP_DIR/$ARTIFACT/dongle" "$INSTALL_DIR/dongle"
chmod +x "$INSTALL_DIR/dongle"

rm -rf "$TMP_DIR"

echo "=> Caching shell scripts..."
mkdir -p "$INIT_DIR"
"$INSTALL_DIR/dongle" init bash > "$INIT_DIR/bash_init.sh"
"$INSTALL_DIR/dongle" init zsh > "$INIT_DIR/zsh_init.zsh"

SHELL_NAME=$(basename "$SHELL")
echo ""
echo "=> Setup complete!"
echo ""
echo "To finish, add this to your shell config file (e.g. ~/.zshrc or ~/.bashrc):"
echo ""
if [ "$SHELL_NAME" = "bash" ]; then
    echo "    [ -f ~/.dongle/bash_init.sh ] && source ~/.dongle/bash_init.sh"
elif [ "$SHELL_NAME" = "zsh" ]; then
    echo "    [ -f ~/.dongle/zsh_init.zsh ] && source ~/.dongle/zsh_init.zsh"
elif [ "$SHELL_NAME" = "fish" ]; then
    echo "    dongle init fish | source"
fi
echo ""
echo "Also ensure $INSTALL_DIR is in your PATH."
