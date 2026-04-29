#!/bin/bash
# Ever-1 - Direct Install
# Usage: curl -sL url | bash [-s api_key]

API_KEY="${1:-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}"

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

# Save API key - default to the one user gave or prompt for one
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

# Create everai command
mkdir -p "$HOME/.local/bin"
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$HOME/.local/bin/everai"
chmod +x "$HOME/.local/bin/everai"

# Run
cd "$DIR"
python3 main.py