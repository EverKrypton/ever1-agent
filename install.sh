#!/bin/bash
# Ever-1 - Simple Install
echo "╔══════════════╗"
echo "║ Ever-1 Installer ║"
echo "╚══════════════╝"

DIR="$HOME/.ever1-agent"
mkdir -p "$DIR"

# Download files with cache bypass
echo "Downloading..."
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/main.py?$(date +%s)" -o "$DIR/main.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/client.py?$(date +%s)" -o "$DIR/client.py"  
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/config.py?$(date +%s)" -o "$DIR/config.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/tools.py?$(date +%s)" -o "$DIR/tools.py"

# Fix DIM color if missing
if ! grep -q "DIM.*=" "$DIR/client.py"; then
    sed -i "s/BOLD = '\\\\033\[1m'/BOLD = '\\\\033[1m'\n    DIM = '\\\\033[2m'/" "$DIR/client.py"
fi

echo "Done!, running..."
cd "$DIR"
python3 main.py