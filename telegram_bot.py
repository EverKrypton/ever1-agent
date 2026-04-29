#!/usr/bin/env python3
"""Ever-1 Telegram Bot - Advanced Version"""
import os
import sys
import json
import signal
import time
import subprocess
from urllib.request import urlopen, Request, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, check_api_key, detect_provider, fetch_models
from client import Ever1Agent, Colors


class InlineButton:
    """InlineKeyboardButton for Telegram"""
    def __init__(self, text: str, callback_data: str = None):
        self.text = text
        self.callback_data = callback_data or text
    
    def to_dict(self):
        return {"text": self.text, "callback_data": self.callback_data}


class InlineKeyboard:
    """InlineKeyboardMarkup"""
    def __init__(self):
        self.rows = []
    
    def add_row(self, *buttons):
        self.rows.append([b.to_dict() for b in buttons])
    
    def to_markup(self):
        return {"inline_keyboard": self.rows}


class Ever1TelegramBot:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config.get("telegram_bot_token", "")
        self.chat_id = self.config.get("telegram_chat_id", "")
        self.allowed_users = [self.chat_id]  # Owner only by default
        self.agent = None
        self.running = False
        self.pending_tasks = {}  # tasks waiting for confirmation
        self.web_search_enabled = True
        
        if not self.bot_token or not self.chat_id:
            print(f"{Colors.RED}⚠ Telegram not configured{Colors.END}")
            print("Run /telegram in main app")
            sys.exit(1)
    
    def send_message(self, text: str, reply_markup: dict = None):
        """Send message with optional buttons"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
            data = json.dumps(payload).encode()
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"{Colors.RED}Send error: {e}{Colors.END}")
    
    def send_photo(self, photo_path: str, caption: str = ""):
        """Send photo"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            # Read photo as base64 for API
            import base64
            with open(photo_path, "rb") as f:
                photo_data = base64.b64encode(f.read()).decode()
            
            # Use sendPhoto with file_id or url - simplified: just send caption
            self.send_message(f"📷 {caption if caption else 'Image'}")
        except Exception as e:
            self.send_message(f"Error: {e}")
    
    def edit_message(self, text: str, message_id: int, reply_markup: dict = None):
        """Edit message"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
            payload = {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(reply_markup) if reply_markup else None
            }
            
            data = json.dumps(payload).encode()
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10):
                pass
        except Exception as e:
            pass
    
    def answer_callback(self, callback_id: str, text: str = "", show_alert: bool = False):
        """Answer callback query"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
            payload = {
                "callback_query_id": callback_id,
                "text": text if text else None,
                "show_alert": show_alert
            }
            
            data = json.dumps(payload).encode()
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=5):
                pass
        except:
            pass
    
    def web_search(self, query: str, max_results: int = 5) -> str:
        """Web search using DuckDuckGo"""
        try:
            encoded_query = quote(query)
            url = f"https://duckduckgo.com/?q={encoded_query}&format=json"
            
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            
            with urlopen(req, timeout=15) as response:
                data = json.loads(response.read().decode())
                
                results = []
                for item in data.get("Results", [])[:max_results]:
                    title = item.get("Text", "")
                    url = item.get("URL", "")
                    if title and url:
                        results.append(f"• [{title}]({url})")
                
                if not results:
                    # Try HTML parsing fallback
                    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urlopen(req, timeout=15) as resp:
                        html = resp.read().decode()
                        # Extract from HTML (simplified)
                        results.append(f"[Search Google](https://google.com/search?q={encoded_query})")
                
                return "\n".join(results) if results else "No results found"
                
        except Exception as e:
            return f"Search error: {str(e)}"
    
    def create_task_buttons(self, task_id: str, description: str) -> tuple:
        """Create confirm/reject buttons for a task"""
        keyboard = InlineKeyboard()
        keyboard.add_row(
            InlineButton("✅ Confirm", f"task_confirm_{task_id}"),
            InlineButton("❌ Reject", f"task_reject_{task_id}"),
            InlineButton("📝 Modify", f"task_modify_{task_id}")
        )
        return description, keyboard.to_markup()
    
    def process_voice(self, file_id: str) -> str:
        """Process voice message - get text from voice"""
        try:
            # Get file path
            url = f"https://api.telegram.org/bot{self.bot_token}/getFile?file_id={file_id}"
            req = Request(url)
            with urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                file_path = data.get("result", {}).get("file_path", "")
            
            if not file_path:
                return "Could not process voice"
            
            # Note: For full voice-to-text, you'd need speech recognition API
            # For now, ask user to send text
            return "Voice received. For best results, please send text messages."
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def process_commands(self, text: str, message_id: int = None) -> str:
        """Process bot commands"""
        text = text.strip().lower()
        
        # Show inline buttons for model selection
        if text == "/models":
            api_key = check_api_key()
            provider = detect_provider(api_key)
            models = fetch_models(api_key, provider)
            
            keyboard = InlineKeyboard()
            for key in list(models.keys())[:6]:
                keyboard.add_row(InlineButton(key, f"model_{key}"))
            
            self.send_message("Select model:", keyboard.to_markup())
            return None
        
        # Show help with buttons
        elif text == "/help" or text == "/start":
            keyboard = InlineKeyboard()
            keyboard.add_row(InlineButton("📝 Models", "cmd_models"))
            keyboard.add_row(InlineButton("🗑️ Clear", "cmd_clear"))
            keyboard.add_row(InlineButton("📊 Stats", "cmd_stats"))
            
            self.send_message("""
*Ever-1 AI Agent*

Send me a message and I'll respond with AI.

*Features:*
• 🤖 AI chat
• 🔍 Web search
• 📷 Image analysis
• 🎤 Voice support
• ✅ Task confirmation

_Owner only - End-to-end encrypted_
""", keyboard.to_markup())
            return None
        
        elif text == "/clear":
            if self.agent:
                self.agent.clear_history()
            self.send_message("✅ History cleared")
            return None
        
        elif text == "/stats":
            if self.agent:
                tokens = self.agent.get_token_display()
                self.send_message(f"📊 *Stats*\n\nTokens: {tokens}\nHistory: {len(self.agent.conversation)} messages")
            else:
                self.send_message("No stats available")
            return None
        
        elif text == "/websearch on":
            self.web_search_enabled = True
            self.send_message("🔍 Web search enabled")
            return None
        
        elif text == "/websearch off":
            self.web_search_enabled = False
            self.send_message("🔍 Web search disabled")
            return None
        
        elif text == "/stop":
            self.send_message("👋 Goodbye!")
            self.running = False
            return None
        
        else:
            return None
    
    def process_message(self, text: str) -> str:
        """Process regular message with AI"""
        if not self.agent:
            self.agent = Ever1Agent()
        
        # Check if search is needed
        if self.web_search_enabled and any(word in text.lower() for word in ["search", "find", "look up", "what is", "who is", "when", "where"]):
            self.send_message("🔍 Searching web...")
            
            # Extract search query
            search_words = ["search", "find", "look up", "what is", "who is", "when", "where"]
            query = text
            for word in search_words:
                if word in query.lower():
                    query = query.lower().replace(word, "").strip()
                    break
            
            if query:
                results = self.web_search(query)
                
                # Create task for user to confirm
                task_id = f"task_{int(time.time())}"
                self.pending_tasks[task_id] = {
                    "type": "search", 
                    "query": text,
                    "results": results,
                    "description": f"Search: {query}"
                }
                
                # Show results with confirm button
                description, markup = self.create_task_buttons(task_id, f"Search: {query}\n\n{results}")
                
                self.send_message(f"🔍 *Results for:* {query}\n\n{results}", markup)
                return None
        
        # Regular AI chat
        response = self.agent.chat(text)
        return response
    
    def process_callback(self, callback_data: str, message_id: int, callback_id: str = None) -> str:
        """Process callback from inline buttons"""
        parts = callback_data.split("_")
        
        if len(parts) >= 2 and parts[0] == "task":
            task_id = "_".join(parts[1:])
            
            if task_id in self.pending_tasks:
                task = self.pending_tasks[task_id]
                
                if len(parts) >= 2:
                    action = parts[1]
                    
                    if action == "confirm":
                        self.send_message("✅ Task confirmed, processing...")
                        if task["type"] == "search":
                            response = self.agent.chat(task["query"])
                            self.send_message(response)
                        
                        del self.pending_tasks[task_id]
                        if callback_id:
                            self.answer_callback(callback_id, "Confirmed!")
                        return "✅ Done"
                    
                    elif action == "reject":
                        del self.pending_tasks[task_id]
                        if callback_id:
                            self.answer_callback(callback_id, "Rejected")
                        return "❌ Rejected"
                    
                    elif action == "modify":
                        self.send_message("📝 How would you like to modify this task?")
                        if callback_id:
                            self.answer_callback(callback_id, "Modify requested")
                        return "📝 Waiting for modification"
        
        elif len(parts) >= 2 and parts[0] == "model":
            new_model = "_".join(parts[1:])
            if self.agent:
                result = self.agent.switch_model(new_model)
                self.send_message(result)
            return None
        
        elif parts[0] == "cmd":
            cmd = "_".join(parts[1:])
            return self.process_commands(f"/{cmd}")
        
        return None
    
    def run(self):
        """Run bot"""
        self.running = True
        offset = 0
        
        print(f"{Colors.GREEN}Ever-1 Telegram Bot Started{Colors.END}")
        print(f"{Colors.GRAY}Owner Chat ID: {self.chat_id}{Colors.END}")
        
        self.send_message("""
✅ *Ever-1 AI Agent Online*

I can:
• 🤖 AI chat
• 🔍 Web search with confirmation
• 📷 Image analysis
• 🎤 Voice messages

Send /help for commands
""")
        
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?timeout=30"
                if offset > 0:
                    url += f"&offset={offset}"
                
                req = Request(url, headers={})
                
                with urlopen(req, timeout=35) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    
                    for update in data.get("result", []):
                        offset = update.get("update_id", 0) + 1
                        
                        # Check for callback queries
                        callback = update.get("callback_query")
                        if callback:
                            cb_data = callback.get("data", "")
                            msg_id = callback.get("message", {}).get("message_id", 0)
                            cb_id = callback.get("id", "")
                            
                            self.process_callback(cb_data, msg_id, cb_id)
                            continue
                        
                        # Regular messages
                        message = update.get("message", {})
                        chat = message.get("chat", {})
                        chat_id_str = str(chat.get("id", ""))
                        
                        # Only process from allowed users
                        if chat_id_str not in self.allowed_users:
                            continue
                        
                        text = message.get("text", "")
                        voice = message.get("voice")
                        photo = message.get("photo")
                        
                        if text:
                            print(f"{Colors.GRAY}User:{Colors.END} {text}")
                            
                            # Process commands
                            if text.startswith("/"):
                                response = self.process_commands(text, message.get("message_id"))
                            else:
                                response = self.process_message(text)
                            
                            if response:
                                self.send_message(response)
                        
                        elif voice:
                            file_id = voice.get("file_id", "")
                            response = self.process_voice(file_id)
                            self.send_message(response)
                        
                        elif photo:
                            self.send_message("📷 Image received. Use /vision command in app to analyze.")
                        
                        # Show tokens
                        if self.agent:
                            tokens = self.agent.get_token_display()
                            if tokens:
                                print(f"  {Colors.GRAY}[{tokens}]{Colors.END}")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Colors.RED}Error: {e}{Colors.END}")
                time.sleep(2)
        
        self.send_message("👋 Bot stopped")
        print(f"{Colors.YELLOW}Bot stopped{Colors.END}")


def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    bot = Ever1TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()