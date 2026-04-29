#!/bin/bash
# Ever-1 Agent - Direct Install
# Run: curl -sL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh | bash

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
END='\033[0m'

echo -e "${BOLD}╔═══════════════════════════════════════╗${END}"
echo -e "${BOLD}║     ${GREEN}Ever-1 AI Agent${CYAN} Installer     ${BOLD}║${END}"
echo -e "${BOLD}╚═══════════════════════════════════════╝${END}"
echo

DIR="$HOME/.ever1-agent"
BIN="$HOME/.local/bin"
mkdir -p "$DIR" "$BIN"

echo -e "${CYAN}Installing...${END}"

# Download files
for f in main.py client.py config.py tools.py; do
    curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f" --progress-bar 2>/dev/null
done

# Create everai command
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py "$@"' > "$BIN/everai"
chmod +x "$BIN/everai"

# For Termux - add to path differently
if [ -d "$HOME/.termux" ]; then
    echo '[ -d "$HOME/.local/bin" ] && export PATH="$PATH:$HOME/.local/bin"' >> ~/.bashrc 2>/dev/null
    echo '[ -d "$HOME/.local/bin" ] && export PATH="$PATH:$HOME/.local/bin"' >> ~/.zshrc 2>/dev/null
fi

echo
echo -e "${GREEN}✓ Installation Complete!${END}"
echo
echo -e "Run: ${BLUE}everai${END}"
echo -e "or: ${BLUE}python3 ~/.ever1-agent/main.py${END}"
echo