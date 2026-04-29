#!/bin/bash
# Ever-1 Agent Installer - Hidden folder installation

set -e

AGENT_NAME="ever1"
INSTALL_DIR="$HOME/.$AGENT_NAME-agent"
BIN_DIR="$HOME/.local/bin"

echo "╔═══════════════════════════════════════╗"
echo "║   Ever-1 AI Agent Installer       ║"
echo "╚═══════════════════════════════════════╝"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    if command -v apt &> /dev/null; then
        sudo apt install -y python3 python3-pip
    elif command -v pkg &> /dev/null; then
        pkg install -y python
    fi
fi

# Create directory
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Clone repo only if not exists
if [ ! -d "$INSTALL_DIR/.git" ]; then
    echo "Downloading Ever-1..."
    git clone https://github.com/EverKrypton/ever1-agent.git "$INSTALL_DIR"
else
    echo "Updating Ever-1..."
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || true
fi

# Install dependencies
echo "Installing..."
cd "$INSTALL_DIR"
pip install -q requests 2>/dev/null || true

# Create everai CLI script (in hidden folder)
cat > "$BIN_DIR/everai" << 'EOF'
#!/bin/bash
DIR="$HOME/.ever1-agent"
cd "$DIR"
python3 main.py "$@"
EOF

chmod +x "$BIN_DIR/everai"

# Update PATH in bashrc
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ] && ! grep -q ".local/bin" "$BASHRC"; then
    echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$BASHRC"
fi

# Also check zshrc
ZSHRC="$HOME/.zshrc"
if [ -f "$ZSHRC" ] && ! grep -q ".local/bin" "$ZSHRC"; then
    echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$ZSHRC"
fi

echo
echo "╔═══════════════════════════════════════╗"
echo "║   ✓ Installation Complete!         ║"
echo "╚═══════════════════════════════════════╝"
echo
echo "To start Ever-1:"
echo "  source ~/.bashrc  # (first time only)"
echo "  everai"
echo "  OR: python3 ~/.ever1-agent/main.py"
echo

# Ask to start
read -p "Start Ever-1 now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$INSTALL_DIR"
    python3 main.py
fi