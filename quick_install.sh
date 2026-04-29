#!/bin/bash
# Ever-1 - Direct Install (no clone)
# Usage: curl -sL https://bit.ly/ever1-install | bash
# Or: bash <(curl -sL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh)

set -e

DIR="$HOME/.ever1-agent"
BIN="$HOME/.local/bin/everai"

echo "╔══════════════════════════════╗"
echo "║ Ever-1 Installer    ║"
echo "╚════════════════════════════╝"

mkdir -p "$DIR" "$BIN/.."

# Download core files
echo "Downloading..."
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/main.py" -o "$DIR/main.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/client.py" -o "$DIR/client.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/config.py" -o "$DIR/config.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/tools.py" -o "$DIR/tools.py"

# Create command
echo '#!/bin/bash
cd "$HOME/.ever1-agent"
python3 main.py "$@"' > "$BIN"
chmod +x "$BIN"

# Add to PATH
grep -q ".local/bin" ~/.bashrc 2>/dev/null || echo 'PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc

echo "✓ Done!"
echo "Run: source ~/.bashrc && everai"
echo "Or: python3 ~/.ever1-agent/main.py"