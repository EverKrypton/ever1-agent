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

# Download all files
FILES="main.py client.py config.py tools.py telegram_bot.py __init__.py"
for f in $FILES; do
    curl -fsSL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f"
done

# Config with API key if not exists
if [ ! -f "$DIR/config.json" ]; then
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
fi

# Create everai command
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$BIN/everai"
chmod +x "$BIN/everai"

# Add to PATH in .bashrc if not already
BASHRC="$HOME/.bashrc"
if [ -f "$BASHRC" ]; then
    if ! grep -q ".local/bin" "$BASHRC"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$BASHRC"
    fi
fi

# Termux
TERMUX_PREFIX="/data/data/com.termux/files/home"
TERMUX_BIN="$TERMUX_PREFIX/bin"

if [ -d "$TERMUX_PREFIX" ]; then
    mkdir -p "$TERMUX_BIN"
    echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$TERMUX_BIN/everai"
    chmod +x "$TERMUX_BIN/everai"
    
    # Add to PATH in termux .bashrc
    TERMUX_BASHRC="$TERMUX_PREFIX/.bashrc"
    if [ -f "$TERMUX_BASHRC" ]; then
        if ! grep -q ".local/bin" "$TERMUX_BASHRC"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$TERMUX_BASHRC"
        fi
    fi
fi

echo ""
echo "=============================================="
echo "Done! Run: everai"
echo "=============================================="
echo ""

cd "$DIR"
python3 main.py