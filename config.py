import os
import json
from pathlib import Path
from datetime import datetime
import subprocess
from urllib.request import Request, urlopen
from urllib.error import HTTPError

CONFIG_FILE = Path.home() / ".ever1-agent" / "config.json"
MEMORY_FILE = Path.home() / ".ever1-agent" / "memory.json"
STATE_FILE = Path.home() / ".ever1-agent" / "state.json"
LEARNING_FILE = Path.home() / ".ever1-agent" / "learnings.json"
QUEUE_FILE = Path.home() / ".ever1-agent" / "queue.json"

DEFAULT_MODELS = {
    "minimax": {"id": "minimax/minimax-2.5-free", "name": "Minimax 2.5", "price_input": 0, "price_output": 0, "free": True},
    "qwen": {"id": "qwen/qwen-2.5-7b-instruct", "name": "Qwen 2.5 7B", "price_input": 0.00015, "price_output": 0.0003, "free": False},
    "llama": {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "price_input": 0.0002, "price_output": 0.0002, "free": False},
    "gpt4o": {"id": "openai/gpt-4o", "name": "GPT-4o", "price_input": 0.00225, "price_output": 0.009, "free": False},
    "claude": {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5", "price_input": 0.003, "price_output": 0.015, "free": False},
}

MODELS_CACHE = None


def fetch_models_from_api(api_key: str = None) -> dict:
    """Fetch real models from OpenRouter API"""
    global MODELS_CACHE
    
    if MODELS_CACHE is not None:
        return MODELS_CACHE
    
    if not api_key:
        api_key = check_api_key()
    
    if not api_key:
        return DEFAULT_MODELS
    
    try:
        url = "https://openrouter.ai/api/v1/models"
        req = Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        
        with urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            
            models = {}
            for m in data.get("data", [])[:30]:
                model_id = m.get("id", "")
                model_name = m.get("name", model_id)
                
                price = m.get("pricing", {})
                price_in = float(price.get("prompt", 0))
                price_out = float(price.get("completion", 0))
                
                is_free = price_in == 0 and price_out == 0
                
                short_id = model_id.split("/")[-1].replace("-instruct", "").replace("-2", "2").replace("-1", "1")[:15]
                
                models[short_id] = {
                    "id": model_id,
                    "name": model_name[:30],
                    "price_input": price_in,
                    "price_output": price_out,
                    "free": is_free
                }
            
            if models:
                MODELS_CACHE = models
                return models
            
    except Exception as e:
        print(f"Could not fetch models: {e}")
    
    return DEFAULT_MODELS


def get_available_models(api_key: str = None) -> dict:
    """Get models - tries API first, falls back to defaults"""
    return fetch_models_from_api(api_key)

DEFAULT_CONFIG = {
    "provider": "openrouter",
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key": "",
    "model": "minimax",
    "max_history": 20,
    "temperature": 0.7,
    "think_steps": 3,
    "stream": True,
    "show_tokens": True,
    "show_price": True,
    "tools": {"code_execution": True, "file_reading": True, "vision": False, "tts": False},
    "system_prompt": """You are Ever-1, an elite autonomous AI agent. Direct, intelligent, and self-improving.

CORE PRINCIPLES:
1. Be direct and concise - no hedging
2. Think step-by-step for complex tasks
3. Always evaluate your response quality
4. Learn and adapt from every interaction
5. Use tools when needed to accomplish tasks

CAPABILITIES:
- Execute code (Python, Bash, Node.js)
- Read/write files
- Create todo lists for complex tasks
- Self-correction when mistakes are made
- Auto-evaluation after each task

Your goal: Be the best AI agent possible."""
}

def check_api_key() -> str:
    """Check for API key in config or env"""
    config = load_config()
    key = config.get("api_key", "")
    if not key:
        key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        key = os.getenv("OPENAI_API_KEY", "")
    return key

def check_ollama() -> bool:
    """Check if Ollama is running"""
    try:
        result = subprocess.run(["curl", "-s", "-m", "3", "http://localhost:11434/", "-o", "/dev/null"], capture_output=True)
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

def get_model_info(model_key: str) -> dict:
    models = get_available_models()
    if model_key in models:
        return models[model_key]
    for k, v in models.items():
        if v.get('id', '').endswith(model_key) or model_key in v.get('id', ''):
            return v
    if 'minimax' in DEFAULT_MODELS:
        return DEFAULT_MODELS["minimax"]
    return {"id": model_key, "name": model_key, "price_input": 0, "price_output": 0, "free": True}

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return {"pending_tasks": [], "last_task": None}

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

def get_relevant_learnings(query: str = "") -> str:
    if not LEARNING_FILE.exists():
        return ""
    try:
        with open(LEARNING_FILE) as f:
            learnings = json.load(f)
        if not learnings:
            return ""
        recent = learnings[-10:]
        lines = ["[LEARNINGS - Reference]"]
        for l in recent:
            status = "✓" if l.get("success") else "✗"
            lines.append(f"{status} {l.get('type')}: {l.get('content', '')[:80]} (score: {l.get('score', 0)})")
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