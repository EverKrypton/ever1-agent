#!/bin/bash
# Ever-1 - Direct Install
# Usage: curl -sL url | bash -s <api_key>
# Or: curl -sL url | bash -s your_api_key_here

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
    c = re.sub(r\"(BOLD = '\033\[1m')\", r\"BOLD = '\\033[1m'\\n    DIM = '\\033[2m'\", c)
    with open('$DIR/client.py', 'w') as f:
        f.write(c)
"

# If API key provided as argument, save it
if [ -n "$API_KEY" ]; then
    python3 -c "
import json, os
cfg = {'api_key': '$API_KEY', 'model': 'nemotron-3-nano'}
os.makedirs('$DIR', exist_ok=True)
with open('$DIR/config.json', 'w') as f:
    json.dump(cfg, f)
"
    echo "API key saved!"
fi

# Run
cd "$DIR"
python3 main.py