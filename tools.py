import os
import json
import subprocess
from pathlib import Path
from typing import Optional

class ToolExecutor:
    def __init__(self):
        self.results = []
    
    def execute_code(self, code: str, language: str = "python") -> dict:
        result = {"success": False, "output": "", "error": ""}
        
        try:
            if language == "python":
                proc = subprocess.run(
                    ["python3", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif language in ["bash", "sh"]:
                proc = subprocess.run(code, shell=True, capture_output=True, text=True, timeout=30)
            elif language == "node":
                proc = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=30)
            else:
                result["error"] = f"Unknown language: {language}"
                return result
            
            result["success"] = proc.returncode == 0
            result["output"] = proc.stdout or proc.stderr
            
        except subprocess.TimeoutExpired:
            result["error"] = "Timeout (30s)"
        except Exception as e:
            result["error"] = str(e)
        
        self.results.append(result)
        return result
    
    def read_file(self, path: str, limit: int = 5000) -> dict:
        result = {"success": False, "content": "", "error": "", "path": path}
        
        try:
            path = os.path.expanduser(path)
            if not os.path.exists(path):
                result["error"] = "Not found"
                return result
            
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(limit)
                if len(content) >= limit:
                    content += f"\n... (truncated)"
                result["content"] = content
                result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def write_file(self, path: str, content: str) -> dict:
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
        result = {"success": False, "files": [], "error": ""}
        
        try:
            path = os.path.expanduser(path)
            p = Path(path)
            
            if "*" in pattern:
                files = list(p.glob(pattern))
            else:
                files = list(p.glob(f"*{pattern}*"))
            
            result["files"] = [str(f.name) for f in files[:30]]
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def get_available_tools(self) -> list:
        return [
            {"name": "execute", "desc": "Run Python/Bash/Node code"},
            {"name": "read_file", "desc": "Read file contents"},
            {"name": "write_file", "desc": "Write content to file"},
            {"name": "list_files", "desc": "List files in directory"},
        ]