import os
import sys
import json
import time
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
    from config import (load_config, save_config, detect_provider, get_provider_info,
                       load_state, save_state, add_learning, get_relevant_learnings,
                       load_queue, get_next_task, add_to_queue, 
                       get_available_models, get_chat_url, PROVIDERS, SESSION_FILE)
except ImportError:
    from .config import (load_config, save_config, detect_provider, get_provider_info,
                         load_state, save_state, add_learning, get_relevant_learnings,
                         load_queue, get_next_task, add_to_queue,
                         get_available_models, get_chat_url, PROVIDERS, SESSION_FILE)

try:
    from tools import ToolExecutor
except ImportError:
    from .tools import ToolExecutor


class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


class Emoji:
    THINKING = "🤔"
    PROCESSING = "⚙️"
    DONE = "✅"
    ERROR = "❌"
    SPEAK = "🔊"
    VISION = "🖼️"
    CODE = "⚡"
    FILE = "📄"
    VISION = "🖼️"


class ActionIndicator:
    """Simple action indicator with single state"""
    def __init__(self):
        self.current_action = ""
        self.frames = ["◐", "◑", "◒", "◓"]
        self.current = 0
        self.running = False
        
    def start(self, action: str):
        self.current_action = action
        self.current = 0
        self.running = True
        
    def update(self):
        if not self.running:
            return ""
        self.current = (self.current + 1) % len(self.frames)
        return f"{self.frames[self.current]}"
    
    def stop(self):
        self.running = False
        self.current_action = ""


class ProgressBar:
    def __init__(self, width: int = 8):
        self.width = width
    
    def show(self, pct: int) -> str:
        filled = "●" * min(self.width, int(pct / 12.5))
        empty = "○" * max(0, self.width - int(pct / 12.5))
        return f"[{filled}{empty}] {pct}%"


class TokenTracker:
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = 0.0
        self.price_in = 0.0
        self.price_out = 0.0
    
    def set_prices(self, p_in: float, p_out: float):
        self.price_in = p_in
        self.price_out = p_out
    
    def update(self, prompt: int = 0, completion: int = 0):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.cost = (prompt * self.price_in / 1000) + (completion * self.price_out / 1000)
    
    def display(self) -> str:
        total = self.prompt_tokens + self.completion_tokens
        cost_str = f" ${self.cost:.4f}" if self.cost > 0 else ""
        return f"tokens: {total}{cost_str}"


class Ever1Agent:
    def __init__(self):
        self.config = load_config()
        self.state = load_state()
        
        self.api_key = self.config.get("api_key", "")
        if not self.api_key:
            from config import check_api_key
            self.api_key = check_api_key()
        
        self.provider = detect_provider(self.api_key)
        self.provider_info = get_provider_info(self.provider)
        
        self.model_key = self.config.get("model", "")
        self.model_id = self.config.get("model_id", "")
        
        self.temperature = self.config["temperature"]
        self.system_prompt = self.config["system_prompt"]
        
        self.conversation = self.state.get("conversation", [])
        
        self.action = ActionIndicator()
        self.progress = ProgressBar()
        self.tokens = TokenTracker()
        
        self.tools = ToolExecutor()
        self.interrupted = False
        
        self._ensure_model_loaded()
    
    def _ensure_model_loaded(self):
        if not self.model_id:
            models = get_available_models(self.api_key)
            
            for key, info in models.items():
                if self.model_key == key or self.model_key in info.get("id", ""):
                    self.model_id = info.get("id", "")
                    self.config["model"] = key
                    self.config["model_id"] = self.model_id
                    save_config(self.config)
                    self.tokens.set_prices(info.get("price_input", 0), info.get("price_output", 0))
                    return
            
            if models:
                first_key = list(models.keys())[0]
                first_info = models[first_key]
                self.model_key = first_key
                self.model_id = first_info.get("id", first_key)
                self.config["model"] = first_key
                self.config["model_id"] = self.model_id
                save_config(self.config)
                self.tokens.set_prices(first_info.get("price_input", 0), first_info.get("price_output", 0))
    
    def _build_messages(self, user_input: str, image_data: str = None) -> list:
        messages = []
        
        relevant = get_relevant_learnings()
        if relevant:
            messages.append({"role": "system", "content": self.system_prompt + "\n\n" + relevant})
        else:
            messages.append({"role": "system", "content": self.system_prompt})
        
        for conv in self.conversation[-10:]:
            if isinstance(conv, list) and len(conv) >= 2:
                messages.append({"role": "user", "content": conv[0]})
                messages.append({"role": "assistant", "content": conv[1]})
        
        if image_data:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_input},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def _detect_command(self, user_input: str) -> dict:
        cmd_lower = user_input.lower().strip()
        result = {"used": False, "action": "chat"}
        
        # Tool commands
        if cmd_lower.startswith("/exec ") or "run code" in cmd_lower:
            code = user_input[6:].strip() or user_input
            result = {"used": True, "action": "code", "tool": "execute", "code": code}
        
        elif cmd_lower.startswith("/read ") or "read" in cmd_lower:
            path = cmd_lower.replace("/read", "").replace("read", "").strip()
            result = {"used": True, "action": "file", "tool": "read_file", "path": path}
        
        elif cmd_lower.startswith("/write ") and "=" in user_input:
            parts = user_input[7:].split("=", 1)
            result = {"used": True, "action": "file", "tool": "write_file", "path": parts[0].strip(), "content": parts[1].strip()}
        
        elif cmd_lower.startswith("/ls ") or "list files" in cmd_lower:
            path = cmd_lower.replace("/ls", "").replace("list files", "").strip() or "."
            result = {"used": True, "action": "file", "tool": "list_files", "path": path}
        
        elif "/speak" in cmd_lower or "speak" in cmd_lower:
            text = user_input.replace("/speak", "").replace("speak", "").strip()
            result = {"used": True, "action": "speak", "tool": "speak", "text": text}
        
        elif "/vision" in cmd_lower or "analyze" in cmd_lower:
            result = {"used": True, "action": "vision", "tool": "analyze_image", "path": ""}
        
        elif "/help" in cmd_lower:
            result = {"used": True, "action": "help", "tool": "help"}
        
        return result
    
    def _execute_tool(self, tool: str, params: dict) -> dict:
        result = {"success": False, "output": "", "error": ""}
        
        if tool == "execute":
            result = self.tools.execute_code(params.get("code", ""))
        elif tool == "read_file":
            result = self.tools.read_file(params.get("path", ""))
        elif tool == "write_file":
            result = self.tools.write_file(params.get("path", ""), params.get("content", ""))
        elif tool == "list_files":
            result = self.tools.list_files(params.get("path", "."))
        elif tool == "analyze_image":
            result = self.tools.analyze_image(params.get("path", ""))
        elif tool == "speak":
            result = self.tools.speak(params.get("text", ""), self.config.get("tts_engine", "pyttsx3"))
        
        return result
    
    def _self_evaluate(self, response: str) -> dict:
        score = 7
        notes = "Good"
        if len(response) < 20:
            score = 5
            notes = "Short"
        elif "don't" in response.lower() or "cannot" in response.lower():
            score = 6
            notes = "Uncertain"
        return {"score": score, "notes": notes}
    
    def chat(self, user_input: str, stream: bool = True, image_path: str = None) -> str:
        """Main chat method - returns full response"""
        self.interrupted = False
        
        # Show thinking
        self.action.start("Thinking")
        
        cmd_result = self._detect_command(user_input)
        
        if cmd_result.get("used"):
            self.action.stop()
            self.action.start(cmd_result.get("action", "Processing"))
            
            tool = cmd_result.get("tool")
            
            if tool == "help":
                tools = self.tools.get_available_tools()
                output = f"📱 *Ever-1 Tools*\n\n"
                for t in tools:
                    output += f"{t['icon']} /{t['name']}: {t['desc']}\n"
                add_learning("tool", "help", True, 10)
                self.conversation.append([user_input, output])
                self._save_state()
                return output
            
            if tool == "analyze_image":
                self.action.start("Analyze")
                img_result = self.tools.analyze_image(image_path or cmd_result.get("path", ""))
                if img_result.get("success") and img_result.get("data"):
                    return self._vision_chat(user_input, img_result["data"], img_result.get("mime", "image/jpeg"))
                else:
                    self.action.stop()
                    return f"❌ {img_result.get('error', 'Could not analyze image')}"
            
            if tool == "speak":
                result = self._execute_tool(tool, cmd_result)
                self.action.stop()
                return f"✅ Spoke: {cmd_result.get('text', '')[:50]}..." if result.get("success") else f"❌ {result.get('error', '')}"
            
            result = self._execute_tool(tool, cmd_result)
            self.action.stop()
            
            if result.get("success"):
                add_learning(tool, user_input[:100], True, 9)
                output = result.get("output", "Done")
                self.conversation.append([user_input, output])
                self._save_state()
                return f"✅ {output}"
            else:
                add_learning(tool, user_input[:100], False, 4)
                return f"❌ {result.get('error', 'Error')}"
        
        # Regular chat
        return self._api_chat(user_input, stream, image_path)
    
    def _vision_chat(self, user_input: str, image_data: str, mime: str) -> str:
        """Chat with image"""
        self.action.start("Vision")
        
        messages = self._build_messages(user_input, image_data)
        
        chat_url = get_chat_url(self.provider)
        
        # Check if model supports vision
        provider_info = get_provider_info(self.provider)
        vision_models = provider_info.get("vision_models", [])
        
        # Use first available model if current doesn't support vision
        model_id = self.model_id
        if not any(vm in model_id.lower() for vm in ["vision", "gpt-4o", "opus", "sonnet"]):
            models = get_available_models(self.api_key)
            for k, v in models.items():
                if v.get("vision"):
                    model_id = v.get("id", k)
                    break
        
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 2048
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            req = Request(chat_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            
            with urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"]
                
                usage = result.get("usage", {})
                self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                
                self.action.stop()
                add_learning("vision", user_input[:100], True, 9)
                self.conversation.append([user_input, content])
                self._save_state()
                return content
                
        except Exception as e:
            self.action.stop()
            return f"❌ Error: {str(e)}"
    
    def _api_chat(self, user_input: str, stream: bool, image_data: str = None) -> str:
        """API chat"""
        messages = self._build_messages(user_input, image_data)
        
        chat_url = get_chat_url(self.provider)
        
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "stream": stream
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ever1.local",
            "X-Title": "Ever-1"
        }
        
        try:
            req = Request(chat_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            
            response_text = ""
            
            with urlopen(req, timeout=120) as response:
                for line in response:
                    if self.interrupted:
                        return "⚠ Interrupted"
                    
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                response_text += content
                            
                            usage = data.get("usage", {})
                            self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                        except:
                            continue
            
            if not response_text:
                # Non-streaming fallback
                req = Request(chat_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
                with urlopen(req, timeout=60) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    response_text = result["choices"][0]["message"]["content"]
                    
                    usage = result.get("usage", {})
                    self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
            
            evaluation = self._self_evaluate(response_text)
            add_learning("chat", user_input[:100], evaluation["score"] > 6, evaluation["score"], evaluation["notes"])
            
            self.conversation.append([user_input, response_text])
            self._save_state()
            
            return response_text
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _save_state(self):
        self.state["conversation"] = self.conversation
        self.state["model"] = self.model_key
        self.state["model_id"] = self.model_id
        save_state(self.state)
    
    def get_token_display(self) -> str:
        return self.tokens.display()
    
    def clear_history(self):
        self.conversation = []
        self._save_state()
    
    def show_history(self):
        if not self.conversation:
            return "No conversation"
        
        output = "=== History ===\n"
        for conv in self.conversation[-5:]:
            if isinstance(conv, list) and len(conv) >= 2:
                output += f"\nYou: {conv[0][:100]}\nEver-1: {conv[1][:100]}\n"
        return output
    
    def switch_model(self, model_key: str):
        models = get_available_models(self.api_key)
        
        if model_key in models:
            self.config["model"] = model_key
            self.config["model_id"] = models[model_key].get("id", model_key)
            save_config(self.config)
            
            self.model_key = model_key
            self.model_id = models[model_key].get("id", model_key)
            self.tokens.set_prices(models[model_key].get("price_input", 0), models[model_key].get("price_output", 0))
            return f"✅ Model: {models[model_key].get('name', model_key)}"
        return f"❌ Model not found: {model_key}"
    
    def save_state_on_quit(self):
        self._save_state()
        
        # Save session
        with open(SESSION_FILE, "w") as f:
            f.write(f"# Ever-1 Session\n\n")
            f.write(f"**Provider:** {self.provider}\n")
            f.write(f"**Model:** {self.model_id}\n")
            f.write(f"**Tokens:** {self.get_token_display()}\n")
            if self.conversation:
                f.write(f"\n**Last:** {self.conversation[-1][0][:50]}...\n")