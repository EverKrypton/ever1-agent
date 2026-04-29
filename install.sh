#!/bin/bash
# Ever-1 Agent - Direct Install from URL
# Run: bash <(curl -L https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh)
# Or: curl -sL https://bit.ly/ever1ai | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
END='\033[0m'

print_banner() {
    echo -e "
${CYAN}╔═══════════════════════════════════════╗
${CYAN}║   ${GREEN}Ever-1 AI Agent${CYAN} Installer     ║
${CYAN}╚═══════════════════════════════════════╝${END}
"
}

progress() {
    echo -ne "${BLUE}[${GREEN}"
    for i in $(seq 1 $1); do echo -n "█"; done
    for i in $(seq $1 20); do echo -n "░"; done
    echo -ne "${BLUE}]${END} $2%\r"
}

print_banner

# Check Python
echo -e "${CYAN}Checking Python...${END}"
progress 5 5
if ! command -v python3 &> /dev/null; then
    if command -v pkg &> /dev/null; then
        pkg install -y python >/dev/null 2>&1
    fi
fi
progress 10 10

# Setup dirs
INSTALL_DIR="$HOME/.ever1-agent"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

# Download files
echo -e "\n${CYAN}Downloading Ever-1...${END}"
FILES="main.py client.py config.py tools.py telegram_bot.py"

cd "$INSTALL_DIR"

for file in $FILES; do
    progress 20 20
    curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$file" -o "$file"
    progress 50 50
done
progress 80 80

# Install deps
pip install -q requests 2>/dev/null || true
progress 95 95

# Create everai command
cat > "$BIN_DIR/everai" << 'EOF'
#!/bin/bash
cd "$HOME/.ever1-agent"
python3 main.py "$@"
EOF
chmod +x "$BIN_DIR/everai"

# Update PATH
for rc in ~/.bashrc ~/.zshrc ~/.profile; do
    [ -f "$rc" ] && ! grep -q ".local/bin" "$rc" && echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$rc"
done

progress 100 100
echo -e "\n\n${GREEN}✓ Installation Complete!${END}"
echo -e "${CYAN}Run: everai${END} (or source ~/.bashrc first time)"
echo -e "${CYAN}Or: python3 ~/.ever1-agent/main.py${END}"