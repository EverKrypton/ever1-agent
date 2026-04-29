#!/bin/bash
# Ever-1 Agent Installer for Termux/Linux/macOS

set -e

AGENT_NAME="ever1-agent"
INSTALL_DIR="$HOME/$AGENT_NAME"
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
    elif command -v brew &> /dev/null; then
        brew install python3
    elif command -v pkg &> /dev/null; then
        pkg install -y python
    fi
fi

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"

# Clone or update repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating Ever-1..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "Cloning Ever-1..."
    git clone https://github.com/EverKrypton/ever1-agent.git "$INSTALL_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
cd "$INSTALL_DIR"
pip install -q requests pyttsx3 gtts 2>/dev/null || true

# Create everai CLI script
cat > "$BIN_DIR/everai" << 'EOF'
#!/bin/bash
AGENT_DIR="$HOME/ever1-agent"
cd "$AGENT_DIR"
python3 main.py "$@"
EOF

chmod +x "$BIN_DIR/everai"

# Add to PATH if not already
BASHRC="$HOME/.bashrc"
ZSHRC="$HOME/.zshrc"
PROFILE_FILE=""

if [ -f "$BASHRC" ]; then
    PROFILE_FILE="$BASHRC"
elif [ -f "$ZSHRC" ]; then
    PROFILE_FILE="$ZSHRC"
elif [ -f "$HOME/.profile" ]; then
    PROFILE_FILE="$HOME/.profile"
fi

if [ -n "$PROFILE_FILE" ]; then
    if ! grep -q "$BIN_DIR" "$PROFILE_FILE"; then
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$PROFILE_FILE"
    fi
fi

echo
echo "╔═══════════════════════════════════════╗"
echo "║   Installation Complete!          ║"
echo "╚═══════════════════════════════════════╝"
echo
echo "To start Ever-1:"
echo "  $ everai"
echo
echo "Or run directly:"
echo "  python3 $INSTALL_DIR/main.py"
echo
echo "Setup API key when prompted!"
echo

# Quick start option
read -p "Start Ever-1 now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$INSTALL_DIR"
    python3 main.py
fi