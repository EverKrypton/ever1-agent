#!/bin/bash
# AI Agent Setup Script for Termux

echo "=========================================="
echo "  AI Agent - Termux Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    pkg update && pkg install python -y
fi

# Install dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Create config if not exists
CONFIG_DIR="$HOME/.ai-agent"
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_DIR/config.json" ]; then
    echo "Creating default config..."
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
    "api_url": "https://api.openrouter.ai/v1/chat/completions",
    "api_key": "",
    "model": "openai/gpt-3.5-turbo",
    "max_history": 10,
    "temperature": 0.7,
    "system_prompt": "You are a helpful AI assistant. Be concise and practical."
}
EOF
    echo "Config created at $CONFIG_DIR/config.json"
    echo "Edit it to add your API key."
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To run the AI agent:"
echo "  python3 main.py"
echo ""
echo "To add your API key, edit:"
echo "  ~/.ai-agent/config.json"
echo ""
echo "Or set environment variable:"
echo "  export OPENROUTER_API_KEY=your_key_here"
echo ""