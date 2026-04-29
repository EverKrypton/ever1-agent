#!/bin/bash
# Ever-1 - Direct Install
# Usage: curl -sL url | bash -s <api_key>

API_KEY="${1:-}"

DIR="$HOME/.ever1-agent"
mkdir -p "$DIR"

# Download files
for f in main.py client.py config.py tools.py; do
    curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f"
done

# Fix DIM using python
python3 -c "
import re
with open('$DIR/client.py', 'r') as f:
    c = f.read()
if 'DIM' not in c:
    c = c.replace(\"BOLD = '\033[1m'\", \"BOLD = '\\033[1m'\\n    DIM = '\\033[2m'\")
    with open('$DIR/client.py', 'w') as f:
        f.write(c)
"

# Save API key in config if provided
if [ -n "$API_KEY" ] && [ "$API_KEY" != "-" ]; then
    python3 << PYEOF
import json, os
cfg = {
    "api_key": "$API_KEY",
    "model": "nemotron-3-nano",
    "provider": "openrouter"
}
os.makedirs("$DIR", exist_ok=True)
with open("$DIR/config.json", "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF
fi

# Create everai command
mkdir -p "$HOME/.local/bin"
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py "$@"' > "$HOME/.local/bin/everai"
chmod +x "$HOME/.local/bin/everai"

# Export PATH for this session
export PATH="$PATH:$HOME/.local/bin"

# Run with API key as argument if provided
cd "$DIR"
if [ -n "$API_KEY" ] && [ "$API_KEY" != "-" ]; then
    python3 main.py "$API_KEY"
else
    python3 main.py
fi