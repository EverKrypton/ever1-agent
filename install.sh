#!/bin/bash
# Ever-1 - Simple Install
echo "╔══════════════╗"
echo "║ Ever-1 Installer ║"
echo "╚══════════════╝"

DIR="$HOME/.ever1-agent"
mkdir -p "$DIR"

# Download files
echo "Downloading..."
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/main.py" -o "$DIR/main.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/client.py" -o "$DIR/client.py"  
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/config.py" -o "$DIR/config.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/tools.py" -o "$DIR/tools.py"

# Create command
mkdir -p "$HOME/.local/bin"
echo '#!/bin/bash
cd ~/.ever1-agent; python3 main.py' > "$HOME/.local/bin/everai"
chmod +x "$HOME/.local/bin/everai"

# Run
cd "$DIR"
python3 main.py