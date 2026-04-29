#!/bin/bash
# Ever-1 - Direct Install
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
    c = re.sub(r\"(BOLD = '\033\[1m'\)\", r\"BOLD = '\\033[1m'\\n    DIM = '\\033[2m'\", c)
    with open('$DIR/client.py', 'w') as f:
        f.write(c)
"

# Run
cd "$DIR"
python3 main.py