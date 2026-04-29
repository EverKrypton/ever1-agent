import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Generator
from urllib.request import Request, urlopen
from urllib.error import HTTPError

try:
    from config import (load_config, save_config, detect_provider, get_provider_info,
                       load_state, save_state, load_memory, save_memory, add_learning, 
                       get_relevant_learnings, load_queue, get_next_task, add_to_queue, 
                       get_available_models, get_chat_url, PROVIDERS)
except ImportError:
    from .config import (load_config, save_config, detect_provider, get_provider_info,
                       load_state, save_state, load_memory, save_memory, add_learning,
                       get_relevant_learnings, load_queue, get_next_task, add_to_queue,
                       get_available_models, get_chat_url, PROVIDERS)


class Colors:
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ActionIndicator:
    def __init__(self):
        self.actions = ["Thinking", "Processing", "Executing", "Learning"]
        self.current_action = "Starting"
        self.frames = ["●○○○○", "○○●○○", "○○○●○", "○○○○●"]
        self.current = 0
        self.running = False
        self.thread = None
        
    def set_action(self, action: str):
        self.current_action = action
        
    def start(self, action: str = "Processing"):
        self.running = True
        self.current_action = action
        self.current = 0
        
        def animate():
            while self.running:
                sys.stdout.write(f"\r{Colors.CYAN}{self.current_action} {self.frames[self.current]}{Colors.END}")
                sys.stdout.flush()
                self.current = (self.current + 1) % len(self.frames)
                time.sleep(0.12)
        
        self.thread = threading.Thread(target=animate, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            time.sleep(0.15)
        sys.stdout.write("\r" + " " * 30 + "\r")
        sys.stdout.flush()


class ProgressBar:
    def __init__(self, width: int = 25):
        self.width = width
    
    def show(self, current: int, total: int, prefix: str = ""):
        if total == 0:
            percent = 100
            filled = self.width
        else:
            percent = min(100, int((current / total) * 100))
            filled = int(self.width * current / total) if total > 0 else 0
        
        bar = "●" * filled + "○" * (self.width - filled)
        prefix_text = f"{Colors.CYAN}{prefix}{Colors.END}" if prefix else ""
        sys.stdout.write(f"\r{prefix_text}[{Colors.CYAN}{bar}{Colors.END}] {Colors.CYAN}{percent}%{Colors.END}")
        sys.stdout.flush()


class TokenTracker:
    def __init__(self):
        self.session_prompt_tokens = 0
        self.session_completion_tokens = 0
        self.total_cost = 0.0
        self.price_input = 0.0
        self.price_output = 0.0
    
    def set_prices(self, price_in: float, price_out: float):
        self.price_input = price_in
        self.price_output = price_out
    
    def update(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.session_prompt_tokens += prompt_tokens
        self.session_completion_tokens += completion_tokens
        
        cost = (prompt_tokens * self.price_input / 1000) + \
               (completion_tokens * self.price_output / 1000)
        self.total_cost += cost
    
    def get_display(self) -> str:
        total = self.session_prompt_tokens + self.session_completion_tokens
        cost_str = f"${self.total_cost:.4f}" if self.total_cost > 0 else "$0.00"
        
        if self.price_input > 0:
            return f"tokens: {total} | cost: {cost_str}"
        return f"tokens: {total}"


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
        
        self.interrupted = False
        
        self._ensure_model_loaded()
    
    def _ensure_model_loaded(self):
        """Ensure model is loaded - get from API if not set"""
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
            
            # Try first available model
            if models:
                first_key = list(models.keys())[0]
                first_info = models[first_key]
                self.model_key = first_key
                self.model_id = first_info.get("id", first_key)
                self.config["model"] = first_key
                self.config["model_id"] = self.model_id
                save_config(self.config)
                self.tokens.set_prices(first_info.get("price_input", 0), first_info.get("price_output", 0))
    
    def _build_messages(self, user_input: str) -> list:
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
        
        messages.append({"role": "user", "content": user_input})
        return messages
    
    def _detect_command(self, user_input: str) -> dict:
        cmd_lower = user_input.lower().strip()
        result = {"used": False, "action": "conversation"}
        
        if cmd_lower.startswith("/exec ") or "run code" in cmd_lower:
            code = user_input[6:].strip() if user_input.startswith("/exec ") else user_input
            result = {"used": True, "action": "coding", "tool": "execute", "code": code}
        
        elif cmd_lower.startswith("/read ") or "read file" in cmd_lower:
            path = user_input[6:].strip()
            result = {"used": True, "action": "reading", "tool": "read_file", "path": path}
        
        elif cmd_lower.startswith("/write ") and "=" in user_input:
            parts = user_input[7:].split("=", 1)
            result = {"used": True, "action": "writing", "tool": "write_file", "path": parts[0].strip(), "content": parts[1].strip()}
        
        elif cmd_lower.startswith("/ls ") or "list files" in cmd_lower:
            path = user_input[4:].strip() or "."
            result = {"used": True, "action": "listing", "tool": "list_files", "path": path}
        
        return result
    
    def _execute_tool(self, tool: str, params: dict) -> dict:
        result = {"success": False, "output": "", "error": ""}
        
        if tool == "execute":
            import subprocess
            try:
                code = params.get("code", "")
                lang = "python" if "python" in code else "bash"
                
                if lang == "python":
                    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
                else:
                    proc = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)
                
                result["success"] = proc.returncode == 0
                result["output"] = proc.stdout if proc.stdout else proc.stderr
                
            except Exception as e:
                result["error"] = str(e)
        
        elif tool == "read_file":
            try:
                path = os.path.expanduser(params.get("path", ""))
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        result["output"] = f.read(5000)
                        result["success"] = True
                else:
                    result["error"] = f"File not found: {path}"
            except Exception as e:
                result["error"] = str(e)
        
        elif tool == "write_file":
            try:
                path = os.path.expanduser(params.get("path", ""))
                content = params.get("content", "")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                result["success"] = True
                result["output"] = f"Written to {path}"
            except Exception as e:
                result["error"] = str(e)
        
        elif tool == "list_files":
            try:
                from pathlib import Path
                path = os.path.expanduser(params.get("path", "."))
                p = Path(path)
                files = [str(f.name) for f in p.glob("*")][:20]
                result["output"] = "\n".join(files)
                result["success"] = True
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def _self_evaluate(self, response: str) -> dict:
        score = 7
        notes = "Good response"
        
        if len(response) < 20:
            score = 5
            notes = "Response too brief"
        elif "don't know" in response.lower() or "cannot" in response.lower():
            score = 6
            notes = "Uncertain"
        
        return {"score": score, "notes": notes}
    
    def chat(self, user_input: str, stream: bool = True) -> Generator[str, None, None]:
        self.interrupted = False
        
        # Show thinking briefly
        self.action.set_action("Thinking")
        self.action.start("Thinking")
        time.sleep(0.5)  # Brief think
        self.action.stop()
        
        cmd_result = self._detect_command(user_input)
        
        if cmd_result.get("used"):
            if cmd_result.get("tool"):
                self.action.set_action(cmd_result.get("action", "executing"))
                self.action.start(cmd_result.get("action", "executing"))
                
                result = self._execute_tool(cmd_result.get("tool"), cmd_result)
                self.action.stop()
                
                if result.get("success"):
                    yield f"{Colors.GREEN}✓ Done{Colors.END}\n{result.get('output', '')}\n"
                    add_learning(cmd_result.get("action"), user_input[:100], True, 9)
                else:
                    yield f"{Colors.RED}✗ Error{Colors.END}\n{result.get('error', '')}\n"
                    add_learning(cmd_result.get("action"), user_input[:100], False, 4)
                
                self.conversation.append([user_input, result.get("output", result.get("error", ""))])
                self._save_state()
                return
        
        # Call API
        yield from self._api_chat(user_input, stream=stream)
    
    def _api_chat(self, user_input: str, stream: bool = True) -> Generator[str, None, None]:
        """Chat with OpenAI-compatible API"""
        sys.stdout.write(f"{Colors.CYAN}Processing...{Colors.END}\r")
        sys.stdout.flush()
        
        messages = self._build_messages(user_input)
        
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
            "X-Title": "Ever-1 Agent"
        }
        
        try:
            req = Request(
                chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            assistant_content = []
            chunk_count = 0
            done = False
            
            with urlopen(req, timeout=120) as response:
                for line in response:
                    if self.interrupted:
                        yield f"\n{Colors.YELLOW}⚠ Interrupted{Colors.END}"
                        return
                    
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            done = True
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content_piece = delta.get("content", "")
                            if content_piece:
                                assistant_content.append(content_piece)
                                yield content_piece
                                chunk_count += 1
                                
                                # Show single progress line - clears each time
                                pct = min(100, chunk_count * 5)
                                bar = "●" * min(8, pct // 12) + "○" * max(0, 8 - pct // 12)
                                sys.stdout.write(f"\r{Colors.CYAN}[{bar}]{Colors.END} {pct}%      \r")
                                sys.stdout.flush()
                                
                            usage = data.get("usage", {})
                            self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                        except json.JSONDecodeError:
                            continue
            
            # Clear line and show complete
            total = self.tokens.session_prompt_tokens + self.tokens.session_completion_tokens
            cost = f" ${self.tokens.total_cost:.4f}" if self.tokens.total_cost > 0 else ""
            print(f"\r{Colors.GREEN}✓ Done{Colors.END} │ tokens: {total}{cost}      ")
            
            response_text = "".join(assistant_content)
            evaluation = self._self_evaluate(response_text)
            add_learning("conversation", user_input[:100], evaluation["score"] > 6, evaluation["score"], evaluation["notes"])
            
            self.conversation.append([user_input, response_text])
            self._save_state()
            
        except HTTPError as e:
            try:
                error_body = e.read().decode()
                error_data = json.loads(error_body)
                yield f"\n{Colors.RED}Error: {error_data.get('error', {}).get('message', str(e))}{Colors.END}\n"
            except:
                yield f"\n{Colors.RED}Error: HTTP {e.code}{Colors.END}\n"
        except Exception as e:
            yield f"\n{Colors.RED}Error: {str(e)}{Colors.END}\n"
    
    def _anthropic_chat(self, user_input: str, stream: bool = True) -> Generator[str, None, None]:
        messages = self._build_messages(user_input)
        
        chat_url = get_chat_url("anthropic")
        
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        
        anthropic_messages = []
        for m in messages[1:]:
            if m["role"] in ["user", "assistant"]:
                anthropic_messages.append(m)
        
        payload = {
            "model": self.model_id,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "system": system_msg,
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        try:
            self.action.set_action("Sending")
            req = Request(
                chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            assistant_content = []
            
            with urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                content = result.get("content", [{}])[0].get("text", "")
                assistant_content.append(content)
                yield content
                
                usage = result.get("usage", {})
                self.tokens.update(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            
            response_text = "".join(assistant_content)
            self.conversation.append([user_input, response_text])
            self._save_state()
            
        except Exception as e:
            yield f"\n{Colors.RED}Error: {str(e)}{Colors.END}\n"
    
    def get_token_display(self) -> str:
        if self.config.get("show_tokens", True):
            return self.tokens.get_display()
        return ""
    
    def _save_state(self):
        self.state["conversation"] = self.conversation
        self.state["model"] = self.model_key
        self.state["model_id"] = self.model_id
        save_state(self.state)
    
    def clear_history(self):
        self.conversation = []
        self._save_state()
        print(f"{Colors.GREEN}✓ History cleared{Colors.END}")
    
    def show_history(self):
        if not self.conversation:
            print(f"{Colors.GRAY}No conversation history{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}=== History ==={Colors.END}")
        for conv in self.conversation[-10:]:
            if isinstance(conv, list) and len(conv) >= 2:
                print(f"\n--- User ---")
                print(conv[0][:200])
                print(f"\n--- Ever-1 ---")
                print(conv[1][:200])
    
    def show_queue(self):
        queue = load_queue()
        if not queue:
            print(f"{Colors.GRAY}Queue is empty{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}=== Task Queue ==={Colors.END}")
        for i, task in enumerate(queue):
            status = "○" if i == 0 else "○"
            print(f"{status} {task.get('description', f'Task {i+1}')}")
    
    def switch_model(self, model_key: str):
        models = get_available_models(self.api_key)
        
        if model_key in models:
            from config import save_config
            info = models[model_key]
            
            self.config["model"] = model_key
            self.config["model_id"] = info.get("id", model_key)
            save_config(self.config)
            
            self.model_key = model_key
            self.model_id = info.get("id", model_key)
            self.tokens.set_prices(info.get("price_input", 0), info.get("price_output", 0))
            
            print(f"{Colors.GREEN}✓ Model: {info.get('name', model_key)}{Colors.END}")
        else:
            print(f"{Colors.RED}Model not found: {model_key}{Colors.END}")
            print("Use /models to see available")
    
    def save_state_on_quit(self):
        self._save_state()
        
        # Save session summary
        summary_file = os.path.expanduser("~/.ever1-agent/session.md")
        tokens_info = self.get_token_display()
        
        with open(summary_file, "w") as f:
            f.write(f"# Ever-1 Session Summary\n\n")
            f.write(f"**Provider:** {self.provider}\n")
            f.write(f"**Model:** {self.model_id}\n")
            f.write(f"**Tokens:** {tokens_info}\n")
            f.write(f"\n**Last conversation:**\n")
            if self.conversation:
                f.write(f"User: {self.conversation[-1][0][:100]}...\n")
                f.write(f"Ever-1: {self.conversation[-1][1][:100]}...\n")
        
        print(f"{Colors.CYAN}✓ State saved{Colors.END}")