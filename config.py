import os
import json
from pathlib import Path
from datetime import datetime

CONFIG_FILE = Path.home() / ".ever1-agent" / "config.json"
MEMORY_FILE = Path.home() / ".ever1-agent" / "memory.json"
STATE_FILE = Path.home() / ".ever1-agent" / "state.json"
LEARNING_FILE = Path.home() / ".ever1-agent" / "learnings.json"
QUEUE_FILE = Path.home() / ".ever1-agent" / "queue.json"

OPENROUTER_MODELS = {
    "minimax": {"id": "minimax/minimax-2.5-free", "name": "Minimax 2.5 (Free)", "price_input": 0, "price_output": 0},
    "qwen": {"id": "qwen/qwen-2.5-7b-instruct", "name": "Qwen 2.5 7B", "price_input": 0.00015, "price_output": 0.0003},
    "llama": {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "price_input": 0.0002, "price_output": 0.0002},
    "gpt4o": {"id": "openai/gpt-4o", "name": "GPT-4o", "price_input": 0.00225, "price_output": 0.009},
    "claude": {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5", "price_input": 0.003, "price_output": 0.015},
}

DEFAULT_CONFIG = {
    "provider": "openrouter",
    "api_url": "https://openrouter.ai/api/v1/chat/completions",
    "api_key": os.getenv("OPENROUTER_API_KEY", ""),
    "model": "minimax",
    "max_history": 20,
    "temperature": 0.7,
    "think_steps": 3,
    "stream": True,
    "show_tokens": True,
    "show_price": True,
    "tools": {
        "code_execution": True,
        "file_reading": True,
        "vision": False,
        "tts": False
    },
    "system_prompt": """You are Ever-1, an elite autonomous AI agent. You are direct, intelligent, and self-improving.

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

PERSONALITY:
- Professional but approachable
- Proactive in solving problems
- Honest about limitations
- Always striving to improve

Your goal: Be the best AI agent possible. Assist the user with any task efficiently."""
}

def load_config() -> dict:
    config_dir = CONFIG_FILE.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            user_config = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    return DEFAULT_CONFIG.copy()

def save_config(config: dict):
    config_dir = CONFIG_FILE.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_model_info(model_key: str) -> dict:
    return OPENROUTER_MODELS.get(model_key, OPENROUTER_MODELS["minimax"])

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            return {"pending_tasks": [], "last_task": None, " session_start": None}
    return {"pending_tasks": [], "last_task": None, "session_start": None}

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
            return []
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
            learnings = []
    
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
        lines = ["[LEARNINGS - Reference for better responses]"]
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
            return []
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