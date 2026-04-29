#!/bin/bash
# Ever-1 Agent - Direct Install (Termux optimized)
# Run: curl -sL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh | bash

set -e

# Colors
R='\033[0m' G='\033[0;32m' B='\033[0;34m' C='\033[0;36m'

echo -e "${G}╔═══════════════════════════════════════╗${R}"
echo -e "${G}║     Ever-1 AI Agent Installer     ║${R}"
echo -e "${G}╚═══════════════════════════════════════╝${R}"
echo

DIR="$HOME/.ever1-agent"
mkdir -p "$DIR"

echo -e "${C}Installing files...${R}"
echo -ne "${B}[${G}"

# Download 4 core files with progress
FILES="main.py client.py config.py tools.py"
COUNT=0
for f in $FILES; do
    COUNT=$((COUNT + 1))
    PROG=$((COUNT * 25))
    BAR=$((PROG / 5))
    echo -ne "\r${B}[${G}"
    for i in $(seq 1 $BAR); do echo -n "█"; done
    for i in $(seq $BAR 20); do echo -n "░"; done
    echo -ne "${B}] ${PROG}%${R}"
    
    curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f"
done

echo -ne "\r${B}[${G}████████████████████${B}]100%${R}"
echo -e "\n${G}✓ Files downloaded${R}"

# Create everai command
echo "Creating command..."
mkdir -p "$HOME/.local/bin"
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$HOME/.local/bin/everai"
chmod +x "$HOME/.local/bin/everai"

# Setup PATH for current session
export PATH="$PATH:$HOME/.local/bin"

# For future sessions - create bashrc/zshrc
for SHELL_RC in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$SHELL_RC" ]; then
        if ! grep -q ".local/bin" "$SHELL_RC" 2>/dev/null; then
            echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$SHELL_RC"
        fi
    else
        echo 'export PATH="$PATH:$HOME/.local/bin"' > "$SHELL_RC"
    fi
done

# If no shell rc exists, create one
if [ ! -f "$HOME/.bashrc" ] && [ ! -f "$HOME/.zshrc" ]; then
    echo 'export PATH="$PATH:$HOME/.local/bin"' > "$HOME/.bashrc"
fi

echo -e "${G}✓ Installation Complete!${R}"
echo
echo -e "${B}Run: everai${R}"
echo -e "${B}Or: python3 ~/.ever1-agent/main.py${R}"
echo

# Option to run directly
read -p "Start Ever-1 now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd "$DIR"
    python3 main.py
fi