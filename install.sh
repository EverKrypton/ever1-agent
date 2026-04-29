#!/bin/bash
# Ever-1 - Direct Install

DIR="$HOME/.ever1-agent"

# Download files
for f in main.py client.py config.py tools.py; do
    curl -sL "https://raw.githubusercontent.com/EverKrypton/ever1-agent/main/$f" -o "$DIR/$f"
done

# Fix DIM 
python3 -c "
import re
with open('$DIR/client.py', 'r') as f:
    c = f.read()
if 'DIM' not in c:
    c = c.replace(\"BOLD = '\033[1m'\", \"BOLD = '\\033[1m'\\n    DIM = '\\033[2m'\")
    with open('$DIR/client.py', 'w') as f:
        f.write(c)
"

# Pre-create config that loads_config can find
python3 << PYEOF
import json, os
cfg = {
    "api_key": "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",
    "model": "nemotron-3-nano",
    "provider": "openrouter"
}
# Use exact path load_config expects
cfg_path = os.path.expanduser("~/.ever1-agent/config.json")
os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
print("Config saved to:", cfg_path)
PYEOF

# Create everai command
mkdir -p "$HOME/.local/bin"
echo '#!/bin/bash
cd ~/.ever1-agent
python3 main.py' > "$HOME/.local/bin/everai"
chmod +x "$HOME/.local/bin/everai"

# Run now
cd "$DIR"
python3 main.py