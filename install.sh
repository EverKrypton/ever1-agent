#!/bin/bash
# Ever-1 Install
# curl -fsSL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh | bash

set -euo pipefail

DIR="$HOME/.ever1-agent"
BIN="$HOME/.local/bin"

mkdir -p "$DIR" "$BIN"

echo ""
echo "╔═══════════════════════════════╗"
echo "║      EVER-1 AI Agent          ║"
echo "╚═══════════════════════════════╝"
echo "Installing..."

# Download files
for f in main.py client.py config.py tools.py; do
    curl -fsSL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f"
done

# Fix DIM
if ! grep -q "DIM = " "$DIR/client.py"; then
    sed -i "/BOLD = '.*/a\\    DIM = '\\\\033[2m'" "$DIR/client.py"
fi

# Config with API key
python3 << PYEOF
import json, os
cfg = {
    "api_key": "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",
    "model": "claude-opus-latest",
    "provider": "openrouter"
}
with open("$DIR/config.json", "w") as f:
    json.dump(cfg, f)
PYEOF

# Create everai command IN TERMUX DEFAULT PATH
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > /data/data/com.termux/files/home/bin/everai
chmod +x /data/data/com.termux/files/home/bin/everai

# Also in ~/.local/bin
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$BIN/everai"
chmod +x "$BIN/everai"

# Add to PATH for this session
export PATH="/data/data/com.termux/files/home/bin:$PATH"

echo ""
echo "Run: everai"
echo "Or: python3 ~/.ever1-agent/main.py"
echo ""

cd "$DIR"
python3 main.py