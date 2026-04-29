# Ever-1 AI Agent

🤖 Self-Learning AI Agent with Vision, Voice, and Telegram integration.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![GitHub](https://img.shields.io/github/stars/EverKrypton/ever1-agent)

**Ever-1** is an autonomous AI agent that learns from every interaction, supports images/analyze, text-to-speech, runs in Telegram, and works with any OpenAI-compatible API (OpenRouter, OpenAI, Anthropic).

---

## Features

| Feature | Command | Description |
|---------|---------|-------------|
| 🤖 **AI Chat** | `/model <name>` | Switch between models |
| 🖼️ **Vision** | `/vision <path>` | Analyze images |
| 🔊 **Voice** | `/speak <text>` | Text to speech |
| ⚡ **Code** | `/exec <code>` | Execute Python/Bash |
| 📄 **Files** | `/read`, `/write`, `/ls` | File operations |
| 📱 **Telegram** | `/telegram` | Setup bot |
| 🔍 **Web Search** | Telegram only | Search with confirmation |
| ✅ **Task Confirm** | Telegram inline | Confirm before executing |

## Installation

### Option 1: Quick Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/EverKrypton/ever1-agent.git
cd ever1-agent

# Run the installer
chmod +x install.sh
./install.sh
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install requests pyttsx3 gtts

# Run the agent
python3 main.py
```

### Option 3: everai CLI (After install)

```bash
# Install once
bash install.sh

# Start anytime
everai

# Or from anywhere
python3 ~/ever1-agent/main.py
```

---

## First Run Setup

### 1. Get API Key

| Provider | Website | Free Tier |
|----------|---------|----------|
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) | ✅ 1000 credits/day |
| OpenAI | [platform.openai.com](https://platform.openai.com) | $5 credit |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | $5 credit |

### 2. Run Ever-1

```bash
cd ever1-agent
python3 main.py
```

### 3. Enter API Key

When prompted, paste your API key. Ever-1 will:
- Auto-detect provider (OpenRouter/OpenAI/Anthropic)
- Fetch available models
- Show free models highlighted

### 4. Select Model

```
Available Models (50):
  nemotron-3-nano    (FREE/FREE) [FREE]
  laguna-xs.2       (FREE/FREE) [FREE]
  gpt-4o            ($0.00225/$0.009)
  claude-3.5        ($0.003/$0.015)

Select model (enter): nemotron-3-nano
```

---

## Commands

### CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/clear` | Clear conversation history |
| `/history` | View conversation |
| `/models` | List available models |
| `/model <name>` | Switch to another model |
| `/learn` | Show AI learnings |
| `/config` | Show/edit config |
| `/quit` | Exit (saves state) |

### Tool Commands

| Command | Example | Description |
|---------|---------|-------------|
| `/exec` | `/exec print("hi")` | Run Python code |
| `/read` | `/read ~/.bashrc` | Read file |
| `/write` | `/write test.txt=hello` | Write file |
| `/ls` | `/ls ~/projects` | List files |
| `/vision` | `/vision photo.jpg` | Analyze image |
| `/speak` | `/speak Hello` | Text to speech |

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Ctrl+C | Interrupt |
| Ctrl+Z | Stop bot |

---

## Telegram Bot Setup

### 1. Create Bot

1. Open Telegram
2. Message: @BotFather
3. Command: `/newbot`
4. Name: `Ever-1 AI`
5. Username: `ever1_ai_bot`
6. Copy the token

### 2. Get Chat ID

1. Message @userinfobot to get your chat_id
2. Or start your bot and check the logs

### 3. Configure

Run in CLI:
```
/telegram
Bot Token: <paste_token>
Chat ID: <paste_chat_id>
```

### 4. Start Bot

```bash
python3 telegram_bot.py
```

### Telegram Features

- **Owner-only** - Only you can control the bot
- **Inline buttons** - Confirm/reject tasks
- **Web search** - With confirmation
- **Voice** - Audio messages
- **Images** - Send photo to analyze

---

## Configuration

### Config File Location

```
~/.ever1-agent/config.json
```

### Edit Manually

```json
{
    "api_key": "sk-or-...",
    "provider": "openrouter",
    "model": "nemotron-3-nano",
    "temperature": 0.7,
    "show_tokens": true,
    "show_price": true,
    "telegram_bot_token": "",
    "telegram_chat_id": ""
}
```

### Environment Variables

```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## File Structure

```
ever1-agent/
├── main.py           # Main CLI entry point
├── client.py        # AI agent logic
├── config.py        # Configuration & providers
├── tools.py         # Tool executor (code, files, etc)
├── telegram_bot.py  # Telegram bot
├── install.sh       # Installer script
├── BUSINESS.md      # Business model
├── Agents.md       # Agent configuration
└── README.md       # This file
```

---

## Models Available

### Free Models (OpenRouter)

| Model | Provider | Notes |
|-------|----------|-------|
| Nemotron 3 Nano | NVIDIA | Best free option |
| Laguna XS | Poolside | Free |
| Qwen 2.5 | Alibaba | Good for coding |

### Paid Models

| Model | Input/1k | Output/1k |
|-------|----------|-----------|
| GPT-4o | $2.25 | $9.00 |
| Claude 3.5 | $3.00 | $15.00 |
| Llama 3.1 | $0.20 | $0.20 |

---

## Examples

### Chat

```
You> What is Python?
Ever-1> Python is a high-level programming language...
```

### Execute Code

```
You> /exec print([i**2 for i in range(5)])
Ever-1> ✅ [0, 1, 4, 9, 16]
```

### Read File

```
You> /read ~/.bashrc
Ever-1> ✅ # ~/.bashrc contents...
```

### Switch Model

```
You> /model gpt-4o
Ever-1> ✅ Model: GPT-4o
```

---

## Troubleshooting

### No API Key

```
Error: No API key
```
**Fix:** Enter API key when prompted, or set `OPENROUTER_API_KEY` env var

### Model Not Found

```
Error: Model not found
```
**Fix:** Use `/models` to see available, then `/model <name>`

### Telegram Not Working

```
⚠ Telegram not configured
```
**Fix:** Run `/telegram` to set up bot token and chat ID

### Tokens Not Tracking

```
tokens: 0
```
**Fix:** Use streaming mode, or provider may not return usage

---

## Requirements

- Python 3.10+
- requests (for API calls)
- pyttsx3 (for TTS - optional)
- gtts (for Google TTS - optional)

---

## Business Use

See [BUSINESS.md](BUSINESS.md) for:
- How to make money with Ever-1
- Pricing models
- Cuba-friendly payment options

---

## Links

- **GitHub**: https://github.com/EverKrypton/ever1-agent
- **Author**: @EverKrypton

---

## License

MIT - Feel free to use, modify, and distribute.

---

## Quick Start Commands

```bash
# Clone and run
git clone https://github.com/EverKrypton/ever1-agent.git
cd ever1-agent
python3 main.py

# Or install and use everai CLI
bash install.sh
everai
```