import os
import json
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
import subprocess
import base64
import io

CONFIG_FILE = Path.home() / ".ever1-agent" / "config.json"
MEMORY_FILE = Path.home() / ".ever1-agent" / "memory.json"
STATE_FILE = Path.home() / ".ever1-agent" / "state.json"
LEARNING_FILE = Path.home() / ".ever1-agent" / "learnings.json"
QUEUE_FILE = Path.home() / ".ever1-agent" / "queue.json"
SESSION_FILE = Path.home() / ".ever1-agent" / "session.md"

PROVIDERS = {
    "openrouter": {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1",
        "models_url": "https://openrouter.ai/api/v1/models",
        "chat_endpoint": "/chat/completions",
        "vision_models": ["google/gemini-pro-vision", "openai/gpt-4-vision", "anthropic/claude-3-opus"],
        "detect": ["or-", "sk-or-"],
    },
    "openai": {
        "name": "OpenAI", 
        "url": "https://api.openai.com/v1",
        "models_url": "https://api.openai.com/v1/models",
        "chat_endpoint": "/chat/completions",
        "vision_models": ["gpt-4-vision-preview", "gpt-4o"],
        "detect": ["sk-", "sk-proj-"],
    },
    "anthropic": {
        "name": "Anthropic",
        "url": "https://api.anthropic.com",
        "models_url": "https://api.anthropic.com/v1/models",
        "chat_endpoint": "/messages",
        "vision_models": ["claude-3-opus", "claude-3-sonnet"],
        "detect": ["sk-ant-", "clz-"],
    },
}

DEFAULT_CONFIG = {
    "provider": "openrouter",
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key": "",
    "model": "",
    "model_id": "",
    "max_history": 20,
    "temperature": 0.7,
    "stream": True,
    "show_tokens": True,
    "show_price": True,
    "tts_engine": "pyttsx3",
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "system_prompt": """You are Ever-1, an elite autonomous AI agent. Direct, intelligent, self-improving.

CORE PRINCIPLES:
1. Be direct and concise - no hedging
2. Think step-by-step for complex tasks
3. Always evaluate your response quality
4. Learn and adapt from every interaction

CAPABILITIES:
- Execute code (Python, Bash, Node.js)
- Read/write files
- Analyze images (describe what you see)
- Text to speech (speak responses)
- Telegram integration

Your goal: Be the best AI agent possible.""",
}

MODELS_CACHE = {}


def detect_provider(api_key: str) -> str:
    if not api_key:
        return "openrouter"
    for provider, info in PROVIDERS.items():
        for prefix in info.get("detect", []):
            if api_key.startswith(prefix):
                return provider
    return "openrouter"


def get_provider_info(provider: str) -> dict:
    return PROVIDERS.get(provider, PROVIDERS["openrouter"])


def check_api_key() -> str:
    config = load_config()
    key = config.get("api_key", "")
    if not key:
        key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        key = os.getenv("ANTHROPIC_API_KEY", "")
    return key


def check_ollama() -> bool:
    try:
        result = subprocess.run(["curl", "-s", "-m", "2", "http://localhost:11434/", "-o", "/dev/null"], 
                              capture_output=True)
        return result.returncode == 0
    except:
        return False


def load_config() -> dict:
    config_dir = CONFIG_FILE.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                user_config = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)
                return config
        except:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    config_dir = CONFIG_FILE.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def fetch_models(api_key: str = None, provider: str = None) -> dict:
    global MODELS_CACHE
    
    if not api_key:
        api_key = check_api_key()
    if not provider:
        provider = detect_provider(api_key)
    
    cache_key = f"{provider}_{api_key[:20]}"
    if cache_key in MODELS_CACHE:
        return MODELS_CACHE[cache_key]
    
    provider_info = get_provider_info(provider)
    models_url = provider_info.get("models_url")
    
    if not models_url:
        MODELS_CACHE[cache_key] = {}
        return {}
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if provider == "anthropic":
            headers["anthropic-version"] = "2023-06-01"
        
        req = Request(models_url, headers=headers, method="GET")
        
        with urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode())
            
            models = {}
            
            if provider in ["openrouter", "openai"]:
                for m in data.get("data", [])[:50]:
                    model_id = m.get("id", "")
                    model_name = model_id.split("/")[-1][:20]
                    
                    pricing = m.get("pricing", {})
                    price_in = float(pricing.get("prompt", 0))
                    price_out = float(pricing.get("completion", 0))
                    is_free = price_in == 0 and price_out == 0
                    supports_vision = any(vm in model_id.lower() for vm in ["vision", "vision", "opUS", "gpt-4o"])
                    
                    models[model_name] = {
                        "id": model_id,
                        "name": model_name,
                        "price_input": price_in,
                        "price_output": price_out,
                        "free": is_free,
                        "provider": provider,
                        "vision": supports_vision,
                    }
            
            if models:
                MODELS_CACHE[cache_key] = models
                return models
            
    except Exception as e:
        print(f"Could not fetch models: {e}")
    
    return {}


def get_available_models(api_key: str = None) -> dict:
    if not api_key:
        api_key = check_api_key()
    
    provider = detect_provider(api_key)
    return fetch_models(api_key, provider)


def get_chat_url(provider: str) -> str:
    provider_info = get_provider_info(provider)
    base_url = provider_info.get("url", "")
    endpoint = provider_info.get("chat_endpoint", "/chat/completions")
    
    if provider == "anthropic":
        return f"{base_url}/v1/messages"
    
    return f"{base_url}{endpoint}"


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"pending_tasks": [], "last_task": None, "conversation": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_memory() -> list:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_memory(memory: list):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory[-100:], f)


def add_learning(learning_type: str, content: str, success: bool, score: int = 8, notes: str = ""):
    learnings = []
    if LEARNING_FILE.exists():
        try:
            with open(LEARNING_FILE) as f:
                learnings = json.load(f)
        except:
            pass
    
    learnings.append({
        "type": learning_type,
        "content": content[:200],
        "success": success,
        "score": score,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(LEARNING_FILE, "w") as f:
        json.dump(learnings[-100:], f)


def get_relevant_learnings() -> str:
    if not LEARNING_FILE.exists():
        return ""
    try:
        with open(LEARNING_FILE) as f:
            learnings = json.load(f)
        if not learnings:
            return ""
        recent = learnings[-10:]
        lines = ["[LEARNINGS]"]
        for l in recent:
            status = "✓" if l.get("success") else "✗"
            lines.append(f"{status} {l.get('type')}: {l.get('content', '')[:60]}")
        return "\n".join(lines)
    except:
        return ""


def load_queue() -> list:
    if QUEUE_FILE.exists():
        try:
            with open(QUEUE_FILE) as f:
                return json.load(f)
        except:
            pass
    return []


def save_queue(queue: list):
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def add_to_queue(task: dict):
    queue = load_queue()
    queue.append(task)
    save_queue(queue)


def get_next_task() -> dict | None:
    queue = load_queue()
    if queue:
        task = queue.pop(0)
        save_queue(queue)
        return task
    return None


def clear_queue():
    save_queue([])