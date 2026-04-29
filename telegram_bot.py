#!/usr/bin/env python3
"""Ever-1 Telegram Bot"""
import os
import sys
import json
import signal
import threading
import time
from urllib.request import urlopen, Request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, check_api_key, detect_provider
from client import Ever1Agent, Colors


class Ever1TelegramBot:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config.get("telegram_bot_token", "")
        self.chat_id = self.config.get("telegram_chat_id", "")
        self.agent = None
        self.running = False
        
        if not self.bot_token or not self.chat_id:
            print(f"{Colors.RED}⚠ Telegram not configured{Colors.END}")
            print("Run /telegram in main app to setup")
            sys.exit(1)
    
    def send_message(self, text: str):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }).encode()
            
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"{Colors.RED}Send error: {e}{Colors.END}")
    
    def get_updates(self, offset: int = 0) -> list:
        """Get Telegram updates"""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates?timeout=60"
            if offset > 0:
                url += f"&offset={offset}"
            
            req = Request(url, headers={})
            with urlopen(req, timeout=70) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("result", [])
        except:
            return []
    
    def process_message(self, text: str) -> str:
        """Process message with Ever-1 agent"""
        if not self.agent:
            self.agent = Ever1Agent()
        
        # Think
        self.send_message("🤔 Thinking...")
        
        # Process
        response = self.agent.chat(text)
        
        # Done
        return response
    
    def run(self):
        """Run bot"""
        self.running = True
        offset = 0
        
        print(f"{Colors.GREEN}Ever-1 Telegram Bot Started{Colors.END}")
        print(f"{Colors.GRAY}Chat ID: {self.chat_id}{Colors.END}")
        print(f"{Colors.CYAN}Send /start to bot to begin{Colors.END}")
        
        self.send_message("✅ *Ever-1 AI Agent*\nBot is now online!\nUse /help for commands.")
        
        while self.running:
            try:
                updates = self.get_updates(offset)
                
                for update in updates:
                    offset = update.get("update_id", 0) + 1
                    
                    message = update.get("message", {})
                    text = message.get("text", "")
                    chat = message.get("chat", {})
                    chat_id_str = str(chat.get("id", ""))
                    
                    if chat_id_str != self.chat_id:
                        continue
                    
                    if not text:
                        continue
                    
                    print(f"{Colors.GRAY}User:{Colors.END} {text}")
                    
                    # Process commands
                    if text.startswith("/"):
                        if text == "/start":
                            self.send_message("✅ *Ever-1* online!\n\nSend me a message and I'll respond with AI.")
                        elif text == "/help":
                            self.send_message("""
*Ever-1 Commands:*

/start - Start bot
/help - Show help
/clear - Clear history
/history - View history
/model <name> - Switch model
/models - List models
/stop - Stop bot
""")
                        elif text == "/stop":
                            self.send_message("👋 Goodbye!")
                            self.running = False
                        elif text == "/clear":
                            if self.agent:
                                self.agent.clear_history()
                            self.send_message("✅ History cleared")
                        elif text == "/history":
                            if self.agent:
                                self.send_message(self.agent.show_history())
                            else:
                                self.send_message("No history")
                        elif text == "/models":
                            self.send_message("Use /model <name> in app")
                        else:
                            self.send_message(f"Unknown: {text}")
                    else:
                        # Regular message
                        response = self.process_message(text)
                        self.send_message(response)
                    
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
        
        print(f"{Colors.YELLOW}Bot stopped{Colors.END}")
    
    def stop(self):
        self.running = False


def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    bot = Ever1TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()