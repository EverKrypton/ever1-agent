#!/bin/bash
# Ever-1 Install
# curl -fsSL https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/install.sh | bash

set -euo pipefail

DIR="$HOME/.ever1-agent"
BIN="$HOME/.local/bin"

mkdir -p "$DIR" "$BIN"

echo ""
echo "=============================================="
echo "           EVER-1 AI AGENT                    "
echo "=============================================="
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

# Create everai command in both possible locations
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$BIN/everai"
chmod +x "$BIN/everai"

TERMUX_PREFIX="/data/data/com.termux/files/home"
TERMUX_BIN="$TERMUX_PREFIX/bin"

if [ -d "$TERMUX_PREFIX" ]; then
    mkdir -p "$TERMUX_BIN"
    echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$TERMUX_BIN/everai"
    chmod +x "$TERMUX_BIN/everai"
fi

echo ""
echo "=============================================="
echo "Done! Run: everai"
echo "=============================================="
echo ""

cd "$DIR"
python3 main.py