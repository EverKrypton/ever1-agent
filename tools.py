import os
import sys
import json
import subprocess
import base64
from pathlib import Path
from urllib.request import Request, urlopen


class ToolExecutor:
    """Tools for Ever-1 Agent"""
    
    def __init__(self):
        self.results = []
    
    def execute_code(self, code: str, language: str = "python") -> dict:
        """Execute code in Python, Bash, or Node"""
        result = {"success": False, "output": "", "error": ""}
        
        try:
            if language == "python":
                proc = subprocess.run(
                    [sys.executable, "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif language in ["bash", "sh"]:
                proc = subprocess.run(
                    code, shell=True, capture_output=True, text=True, timeout=30
                )
            elif language == "node":
                proc = subprocess.run(
                    ["node", "-e", code], capture_output=True, text=True, timeout=30
                )
            else:
                result["error"] = f"Unknown language: {language}"
                return result
            
            result["success"] = proc.returncode == 0
            result["output"] = proc.stdout if proc.stdout else proc.stderr
            
        except subprocess.TimeoutExpired:
            result["error"] = "Timeout (30s)"
        except Exception as e:
            result["error"] = str(e)
        
        self.results.append(result)
        return result
    
    def read_file(self, path: str, limit: int = 5000) -> dict:
        """Read file content"""
        result = {"success": False, "content": "", "error": "", "path": path}
        
        try:
            path = os.path.expanduser(path)
            if not os.path.exists(path):
                result["error"] = "File not found"
                return result
            
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(limit)
                if len(content) >= limit:
                    content += f"\n... (truncated {limit} chars)"
                result["content"] = content
                result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def write_file(self, path: str, content: str) -> dict:
        """Write content to file"""
        result = {"success": False, "error": "", "path": path}
        
        try:
            path = os.path.expanduser(path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def list_files(self, path: str = ".", pattern: str = "*") -> dict:
        """List files in directory"""
        result = {"success": False, "files": [], "error": ""}
        
        try:
            path = os.path.expanduser(path)
            p = Path(path)
            
            if "*" in pattern:
                files = list(p.glob(pattern))
            else:
                files = list(p.glob(f"*{pattern}*"))
            
            result["output"] = [f"{'📁 ' if f.is_dir() else '📄 '}{f.name}" for f in files[:30]]
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def analyze_image(self, image_path: str) -> dict:
        """Get image info for AI analysis"""
        result = {"success": False, "info": "", "error": "", "data": None}
        
        try:
            path = os.path.expanduser(image_path)
            if not os.path.exists(path):
                result["error"] = f"Image not found: {image_path}"
                return result
            
            # Get image info
            size = os.path.getsize(path)
            name = os.path.basename(path)
            
            # Read and encode as base64
            with open(path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            
            result["success"] = True
            result["info"] = f"Image: {name} ({size:,} bytes)"
            result["data"] = img_data
            result["mime"] = f"image/{'jpeg' if path.endswith('.jpg') or path.endswith('.jpeg') else 'png'}"
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def speak(self, text: str, engine: str = "pyttsx3") -> dict:
        """Text to speech"""
        result = {"success": False, "error": ""}
        
        try:
            if engine == "pyttsx3":
                try:
                    import pyttsx3
                    tts = pyttsx3.init()
                    tts.say(text)
                    tts.runAndWait()
                    result["success"] = True
                except ImportError:
                    result["error"] = "pyttsx3 not installed. Run: pip install pyttsx3"
            elif engine == "gtts":
                try:
                    from gtts import gTTS
                    tts = gTTS(text=text, lang="en")
                    tts.save("/tmp/ever1_speak.mp3")
                    subprocess.run(["play", "/tmp/ever1_speak.mp3"], capture_output=True)
                    result["success"] = True
                except ImportError:
                    result["error"] = "gtts not installed. Run: pip install gtts"
            else:
                result["error"] = f"Unknown TTS engine: {engine}"
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def telegram_send(self, message: str, bot_token: str = None, chat_id: str = None) -> dict:
        """Send message via Telegram"""
        result = {"success": False, "error": ""}
        
        if not bot_token or not chat_id:
            result["error"] = "Telegram bot_token and chat_id required"
            return result
        
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }).encode()
            
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10) as response:
                response.read()
                result["success"] = True
                
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_available_tools(self) -> list:
        """List all available tools"""
        return [
            {"name": "execute", "desc": "Run Python/Bash/Node code", "icon": "⚡"},
            {"name": "read_file", "desc": "Read file contents", "icon": "📖"},
            {"name": "write_file", "desc": "Write content to file", "icon": "✍️"},
            {"name": "list_files", "desc": "List files in directory", "icon": "📁"},
            {"name": "analyze_image", "desc": "Analyze image", "icon": "🖼️"},
            {"name": "speak", "desc": "Text to speech", "icon": "🔊"},
            {"name": "telegram", "desc": "Send Telegram message", "icon": "📱"},
        ]