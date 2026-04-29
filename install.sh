#!/bin/bash
# Ever-1 - Simple Install
echo "╔══════════════════════╗"
echo "║ Ever-1 Installer   ║"
echo "╚══════════════════════╝"

DIR="$HOME/.ever1-agent"
mkdir -p "$DIR"

# Simple download - just works
echo "Downloading..."
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/main.py" -o "$DIR/main.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/client.py" -o "$DIR/client.py"  
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/config.py" -o "$DIR/config.py"
curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/tools.py" -o "$DIR/tools.py"

# Create command - directly runnable
echo '#!/bin/bash
cd ~/.ever1-agent; python3 main.py' > /data/data/com.termux/files/home/bin/everai
chmod +x /data/data/com.termux/files/home/bin/everai

# Also try standard location
mkdir -p ~/.local/bin
echo '#!/bin/bash
cd ~/.ever1-agent; python3 main.py' > ~/.local/bin/everai
chmod +x ~/.local/bin/everai

# Add to PATH now
export PATH="$PATH:/data/data/com.termux/files/home/bin:$HOME/.local/bin"

echo "✓ Done! Running Ever-1..."
echo

# Run directly
cd "$DIR"
python3 main.py