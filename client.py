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
    from config import (load_config, save_config, get_model_info, load_state, save_state,
                       load_memory, save_memory, add_learning, get_relevant_learnings,
                       load_queue, get_next_task, add_to_queue, clear_queue, 
                       get_available_models, DEFAULT_MODELS)
except ImportError:
    from .config import (load_config, save_config, get_model_info, load_state, save_state,
                        load_memory, save_memory, add_learning, get_relevant_learnings,
                        load_queue, get_next_task, add_to_queue, clear_queue,
                        get_available_models, DEFAULT_MODELS)


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
    GRAY_DARK = '\033[38;5;240m'
    BG_BLACK = '\033[40m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'
    
    @staticmethod
    def input_color(text: str) -> str:
        return f"{Colors.GREEN}{text}{Colors.END}"
    
    @staticmethod
    def output_color(text: str) -> str:
        return f"{Colors.WHITE}{text}{Colors.END}"
    
    @staticmethod
    def status_color(text: str) -> str:
        return f"{Colors.CYAN}{text}{Colors.END}"
    
    @staticmethod
    def error_color(text: str) -> str:
        return f"{Colors.RED}{text}{Colors.END}"

    @staticmethod
    def success_color(text: str) -> str:
        return f"{Colors.GREEN}{text}{Colors.END}"


class ActionIndicator:
    def __init__(self):
        self.actions = ["Thinking", "Analyzing", "Processing", "Executing", "Learning"]
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
    
    def update(self, action: str):
        self.current_action = action


class ProgressBar:
    def __init__(self, width: int = 25):
        self.width = width
    
    def show(self, current: int, total: int, prefix: str = "", color: str = Colors.CYAN):
        if total == 0:
            percent = 100
            filled = self.width
        else:
            percent = min(100, int((current / total) * 100))
            filled = int(self.width * current / total) if total > 0 else 0
        
        bar = "●" * filled + "○" * (self.width - filled)
        prefix_text = f"{color}{prefix}{Colors.END}" if prefix else ""
        sys.stdout.write(f"\r{prefix_text}[{Colors.CYAN}{bar}{Colors.END}] {color}{percent}%{Colors.END}")
        sys.stdout.flush()


class TokenTracker:
    def __init__(self):
        self.session_prompt_tokens = 0
        self.session_completion_tokens = 0
        self.total_cost = 0.0
        self.model_price_input = 0.0
        self.model_price_output = 0.0
    
    def set_model_prices(self, model_key: str):
        info = get_model_info(model_key)
        self.model_price_input = info.get("price_input", 0)
        self.model_price_output = info.get("price_output", 0)
    
    def update(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.session_prompt_tokens += prompt_tokens
        self.session_completion_tokens += completion_tokens
        
        cost = (prompt_tokens * self.model_price_input / 1000) + \
               (completion_tokens * self.model_price_output / 1000)
        self.total_cost += cost
    
    def get_display(self) -> str:
        total = self.session_prompt_tokens + self.session_completion_tokens
        cost_str = f"${self.total_cost:.4f}" if self.total_cost > 0 else "$0.00"
        
        if self.model_price_input > 0:
            return f"tokens: {total} ({self.session_prompt_tokens}+{self.session_completion_tokens}) | cost: {cost_str}"
        return f"tokens: {total}"


class Ever1Agent:
    def __init__(self):
        self.config = load_config()
        self.state = load_state()
        
        self.provider = self.config.get("provider", "openrouter")
        self.api_url = self.config["api_url"]
        self.model_key = self.config.get("model", "minimax")
        self.model_info = get_model_info(self.model_key)
        self.model_id = self.model_info["id"]
        
        self.temperature = self.config["temperature"]
        self.system_prompt = self.config["system_prompt"]
        
        self.conversation = []
        self.memory = load_memory()
        self.queue = load_queue()
        
        self.action = ActionIndicator()
        self.progress = ProgressBar()
        self.tokens = TokenTracker()
        self.tokens.set_model_prices(self.model_key)
        
        self.interrupted = False
        self.is_thinking = False
        
        self._load_history()
        self._check_pending_tasks()
    
    def _load_history(self):
        history_file = os.path.expanduser("~/.ever1-agent/history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file) as f:
                    self.conversation = json.load(f)
            except Exception:
                self.conversation = []
    
    def _save_history(self):
        history_file = os.path.expanduser("~/.ever1-agent/history.json")
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        max_history = self.config.get("max_history", 20)
        
        with open(history_file, "w") as f:
            json.dump(self.conversation[-max_history:], f)
    
    def _check_pending_tasks(self):
        state = load_state()
        if state.get("pending_tasks"):
            print(f"\n{Colors.YELLOW}⚠ Pending tasks from last session:{Colors.END}")
            for task in state["pending_tasks"][:3]:
                print(f"  • {task.get('description', 'Task')}")
            print()
    
    def interrupt(self):
        self.interrupted = True
        self.action.stop()
        print(f"\n{Colors.YELLOW}⚠ Interrupted{Colors.END}")
    
    def add_task_to_queue(self, task: dict):
        add_to_queue(task)
        if not self.queue:
            self.queue = [task]
        else:
            self.queue.append(task)
    
    def check_queue(self):
        if self.queue:
            task = get_next_task()
            if task:
                self.action.set_action(f"Queue: {task.get('description', 'Task')[:20]}")
                return task
        return None
    
    def _build_messages(self, user_input: str) -> list:
        messages = []
        
        relevant = get_relevant_learnings(user_input)
        if relevant:
            messages.append({"role": "system", "content": self.system_prompt + "\n\n" + relevant})
        else:
            messages.append({"role": "system", "content": self.system_prompt})
        
        for conv in self.conversation:
            if isinstance(conv, list) and len(conv) >= 2:
                messages.append({"role": "user", "content": conv[0]})
                messages.append({"role": "assistant", "content": conv[1]})
        
        messages.append({"role": "user", "content": user_input})
        return messages
    
    def _detect_command(self, user_input: str) -> dict:
        """Detect tool or command usage"""
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
        
        elif cmd_lower.startswith("/todo ") or "create todo" in cmd_lower:
            result = {"used": True, "action": "planning", "tool": "create_todo", "content": user_input[6:].strip()}
        
        elif "/queue" in cmd_lower or "add to queue" in cmd_lower:
            result = {"used": True, "action": "queueing", "tool": "add_queue", "content": user_input.replace("/queue", "").replace("add to queue", "").strip()}
        
        return result
    
    def _execute_tool(self, tool: str, params: dict) -> dict:
        """Execute tool and return result"""
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
                files = [str(f) for f in p.glob("*")][:20]
                result["output"] = "\n".join(files)
                result["success"] = True
            except Exception as e:
                result["error"] = str(e)
        
        return result
    
    def _self_evaluate(self, response: str) -> dict:
        """Evaluate response quality"""
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
        
        self.action.set_action("Analyzing")
        cmd_result = self._detect_command(user_input)
        
        if cmd_result.get("used"):
            self.action.start(cmd_result.get("action", "executing"))
            
            if cmd_result.get("tool"):
                result = self._execute_tool(cmd_result.get("tool"), cmd_result)
                
                if result.get("success"):
                    self.action.stop()
                    yield f"{Colors.GREEN}✓ Done{Colors.END}\n{result.get('output', '')}\n"
                    add_learning(cmd_result.get("action"), user_input[:100], True, 9, result.get("output", "")[:50])
                else:
                    self.action.stop()
                    yield f"{Colors.RED}✗ Error{Colors.END}\n{result.get('error', '')}\n"
                    add_learning(cmd_result.get("action"), user_input[:100], False, 4, result.get("error", ""))
                
                self.conversation.append([user_input, result.get("output", result.get("error", ""))])
                self._save_history()
                return
            
            self.action.stop()
        
        self.action.start("Thinking")
        
        if self.provider == "openrouter":
            yield from self._openrouter_chat(user_input, stream=stream)
        else:
            yield from self._ollama_chat(user_input, stream=stream)
    
    def _openrouter_chat(self, user_input: str, stream: bool = True) -> Generator[str, None, None]:
        api_key = self.config.get("api_key", "") or os.getenv("OPENROUTER_API_KEY", "")
        
        if not api_key:
            yield f"\n{Colors.RED}Error: No API key.{Colors.END}\n"
            yield "Set OPENROUTER_API_KEY env variable or configure in config.json\n"
            return
        
        self.action.set_action("Connecting")
        messages = self._build_messages(user_input)
        
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "stream": stream
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ever1.local",
            "X-Title": "Ever-1 Agent"
        }
        
        try:
            self.action.set_action("Sending")
            req = Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            
            assistant_content = []
            chunk_count = 0
            
            if stream:
                self.action.set_action("Streaming")
                with urlopen(req, timeout=120) as response:
                    for line in response:
                        if self.interrupted:
                            yield f"\n{Colors.YELLOW}⚠ Interrupted{Colors.END}"
                            return
                        
                        line = line.decode("utf-8")
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content_piece = delta.get("content", "")
                                if content_piece:
                                    assistant_content.append(content_piece)
                                    yield content_piece
                                    chunk_count += 1
                                    if chunk_count % 10 == 0:
                                        self.progress.show(chunk_count, 50, "Loading: ", Colors.CYAN)
                            except json.JSONDecodeError:
                                continue
                                
                                usage = data.get("usage", {})
                                prompt_tok = usage.get("prompt_tokens", 0)
                                completion_tok = usage.get("completion_tokens", 0)
                                self.tokens.update(prompt_tok, completion_tok)
            else:
                with urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    content = result["choices"][0]["message"]["content"]
                    assistant_content.append(content)
                    
                    usage = result.get("usage", {})
                    self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                    yield content
            
            self.progress.show(50, 50, "Complete: ", Colors.GREEN)
            print()
            
            response_text = "".join(assistant_content)
            evaluation = self._self_evaluate(response_text)
            add_learning("conversation", user_input[:100], evaluation["score"] > 6, evaluation["score"], evaluation["notes"])
            
            self.conversation.append([user_input, response_text])
            self._save_history()
            
        except HTTPError as e:
            try:
                error_body = e.read().decode()
                error_data = json.loads(error_body)
                yield f"\n{Colors.RED}Error: {error_data.get('error', {}).get('message', str(e))}{Colors.END}\n"
            except:
                yield f"\n{Colors.RED}Error: HTTP {e.code}{Colors.END}\n"
        except Exception as e:
            yield f"\n{Colors.RED}Error: {str(e)}{Colors.END}\n"
    
    def _ollama_chat(self, user_input: str, stream: bool = True) -> Generator[str, None, None]:
        messages = self._build_messages(user_input)
        
        api_url = f"{self.api_url}/api/chat"
        
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": self.temperature}
        }
        
        try:
            req = Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            assistant_content = []
            
            if stream:
                with urlopen(req, timeout=180) as response:
                    for line in response:
                        if self.interrupted:
                            return
                        
                        line = line.decode("utf-8").strip()
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    content_piece = data.get("message", {}).get("content", "")
                                    if content_piece:
                                        assistant_content.append(content_piece)
                                        yield content_piece
                                if data.get("done"):
                                    break
                            except:
                                continue
            else:
                with urlopen(req, timeout=180) as response:
                    result = json.loads(response.read().decode("utf-8"))
                    content = result.get("message", {}).get("content", "")
                    assistant_content.append(content)
                    yield content
            
            self.conversation.append([user_input, "".join(assistant_content)])
            self._save_history()
            
        except Exception as e:
            yield f"\n{Colors.RED}Error: {str(e)}{Colors.END}\n"
    
    def get_token_display(self) -> str:
        if self.config.get("show_tokens", True):
            return self.tokens.get_display()
        return ""
    
    def clear_history(self):
        self.conversation = []
        self._save_history()
        print(f"{Colors.GREEN}✓ History cleared{Colors.END}")
    
    def show_history(self):
        if not self.conversation:
            print(f"{Colors.GRAY}No conversation history{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}=== History ==={Colors.END}")
        for i, conv in enumerate(self.conversation[-10:]):
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
        from config import get_available_models, DEFAULT_MODELS
        models = get_available_models()
        
        if model_key in models:
            from config import save_config
            config = load_config()
            config["model"] = model_key
            save_config(config)
            
            self.model_key = model_key
            self.model_info = get_model_info(model_key)
            self.model_id = self.model_info["id"]
            self.tokens.set_model_prices(model_key)
            
            print(f"{Colors.GREEN}✓ Model: {self.model_info['name']}{Colors.END}")
        else:
            print(f"{Colors.RED}Unknown model: {model_key}{Colors.END}")
    
    def save_state_on_quit(self):
        state = load_state()
        state["session_end"] = datetime.now().isoformat()
        
        queue = load_queue()
        if queue:
            state["pending_tasks"] = queue
        
        state_file = os.path.expanduser("~/.ever1-agent/state.json")
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)
        
        summary_file = os.path.expanduser("~/.ever1-agent/session.md")
        tokens_info = self.get_token_display()
        
        with open(summary_file, "w") as f:
            f.write(f"# Ever-1 Session Summary\n\n")
            f.write(f"**Ended:** {datetime.now().isoformat()}\n\n")
            f.write(f"**Tokens:** {tokens_info}\n\n")
            f.write(f"**Model:** {self.model_info['name']}\n\n")
            if queue:
                f.write(f"## Pending Tasks\n")
                for task in queue:
                    f.write(f"- {task.get('description', 'Task')}\n")
            f.write(f"\n**Last conversation:**\n")
            if self.conversation:
                f.write(f"User: {self.conversation[-1][0][:100]}...\n")
                f.write(f"Ever-1: {self.conversation[-1][1][:100]}...\n")
        
        print(f"{Colors.CYAN}✓ State saved{Colors.END}")