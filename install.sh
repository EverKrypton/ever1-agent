#!/bin/bash
# Ever-1 - Simple Install (like opencode)
# curl -fsSL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh | bash

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[38;5;214m'
CYAN='\033[0;36m'
NC='\033[0m'

APP=ever1
INSTALL_DIR="$HOME/.ever1-agent"
BIN_DIR="$HOME/.local/bin"

# Create directories
mkdir -p "$INSTALL_DIR" "$BIN_DIR"

echo -e "${CYAN}Installing Ever-1...${NC}"

# Download core files - simple loop with progress
FILES="main.py client.py config.py tools.py"
for f in $FILES; do
    curl -fsSL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$INSTALL_DIR/$f"
done

# Fix DIM in client.py if needed
if ! grep -q "DIM = " "$INSTALL_DIR/client.py"; then
    sed -i "/BOLD = '\\\\033\[1m'/a\\\\    DIM = '\\\\033[2m'" "$INSTALL_DIR/client.py"
fi

# Create config with default API key
python3 << PYEOF
import json, os
cfg = {
    "api_key": "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",
    "model": "nemotron-3-nano",
    "provider": "openrouter"
}
os.makedirs("$INSTALL_DIR", exist_ok=True)
with open("$INSTALL_DIR/config.json", "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

# Create the everai command
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py "$@"' > "$BIN_DIR/everai"
chmod +x "$BIN_DIR/everai"

# Add to PATH if needed
for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$rc" ] && ! grep -q ".local/bin" "$rc"; then
        echo 'export PATH="$PATH:$HOME/.local/bin"' >> "$rc"
    fi
done

echo -e ""
echo -e "${GREEN}Installed!${NC}"
echo -e "Run: ${ORANGE}everai${NC}"
echo -e "Or: ${ORANGE}python3 ~/.ever1-agent/main.py${NC}"
echo -e ""

# Run now
cd "$INSTALL_DIR"
python3 main.py