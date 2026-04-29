#!/usr/bin/env python3
"""Ever-1 AI Agent - Main Entry Point"""
import sys
import os
import signal
import tty
import termios

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import Ever1Agent, Colors, Emoji
from config import (load_config, save_config, load_state, get_relevant_learnings,
                   load_queue, add_to_queue, get_provider_info,
                   check_api_key, check_ollama, get_available_models, PROVIDERS,
                   detect_provider, fetch_models)


def print_banner():
    print("""
================================================
           EVER-1 AI AGENT
================================================
""")


def get_key():
    """Get arrow key input"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ch2 = sys.stdin.read(1)
            if ch2 == '[':
                ch3 = sys.stdin.read(1)
                if ch3 == 'A':
                    return 'UP'
                elif ch3 == 'B':
                    return 'DOWN'
                elif ch3 == 'C':
                    return 'RIGHT'
                elif ch3 == 'D':
                    return 'LEFT'
        return ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def select_model_arrows(models: dict, current: str) -> str:
    """Model selection with arrow keys"""
    model_list = list(models.keys())
    if not model_list:
        return current
    
    current_index = model_list.index(current) if current in model_list else 0
    
    print(f"\n{Colors.CYAN}Use ↑↓ arrows to select, ENTER to confirm:{Colors.END}\n")
    
    while True:
        for _ in range(len(model_list) + 2):
            sys.stdout.write('\033[F')
        
        print(f"\n{Colors.CYAN}Use ↑↓ arrows, ENTER:{Colors.END}\n")
        
        for i, key in enumerate(model_list):
            info = models[key]
            marker = "→" if i == current_index else " "
            name = info.get('name', key)[:25]
            free = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get('free') else ""
            vision = f" {Colors.YELLOW}[VISION]{Colors.END}" if info.get('vision') else ""
            
            if i == current_index:
                print(f"{Colors.CYAN}{marker} {key:20} {name}{free}{vision}{Colors.END}")
            else:
                print(f"  {Colors.GRAY}{key:20} {Colors.DIM}{name}{free}{vision}{Colors.END}")
        
        key = get_key()
        
        if key == 'UP':
            current_index = (current_index - 1) % len(model_list)
        elif key == 'DOWN':
            current_index = (current_index + 1) % len(model_list)
        elif key == '':
            break
        
        import time
        time.sleep(0.05)
    
    return model_list[current_index]


def check_setup() -> str:
    """Initial setup"""
    print(f"\n{Colors.CYAN}Checking...{Colors.END}")
    
    api_key = check_api_key()
    ollama = check_ollama()
    
    config = load_config()
    api_key = api_key or config.get("api_key", "")
    
    # Check Ollama first (local models)
    if ollama:
        print(f"{Colors.GREEN}✓ Ollama detected (local){Colors.END}")
        try:
            import urllib.request
            req = urllib.request.Request("http://localhost:11434/api/tags", headers={})
            with urllib.request.urlopen(req, timeout=5) as resp:
                import json
                data = json.loads(resp.read().decode())
                models = data.get("models", [])
                if models:
                    ollama_models = {}
                    for m in models:
                        name = m.get("name", "").split(":")[0]
                        ollama_models[name] = {"id": m.get("name", ""), "name": name, "provider": "ollama", "local": True}
                    config["ollama_models"] = ollama_models
                    print(f"{Colors.CYAN}  {len(models)} local models{Colors.END}")
                    if not api_key:
                        # Use first Ollama model
                        first_model = models[0].get("name", "")
                        config["api_url"] = "http://localhost:11434/v1/chat/completions"
                        config["model"] = first_model.split(":")[0]
                        config["model_id"] = first_model
                        config["provider"] = "ollama"
                        save_config(config)
                        print(f"{Colors.GREEN}✓ Using: {first_model}{Colors.END}")
                        return first_model.split(":")[0]
        except Exception as e:
            print(f"{Colors.YELLOW} Ollama error: {e}{Colors.END}")
    
    if not api_key and not ollama:
        print(f"\n{Colors.YELLOW}No API key or Ollama{Colors.END}")
        print(f"{Colors.CYAN}Run /connect to add API key{Colors.END}")
    
    if api_key:
        provider = detect_provider(api_key)
        print(f"{Colors.GREEN}✓ {get_provider_info(provider)['name']}{Colors.END}")
    
    print(f"\n{Colors.CYAN}Loading models...{Colors.END}")
    models = fetch_models(api_key, detect_provider(api_key))
    
    if not models:
        print(f"{Colors.RED}No models found{Colors.END}")
        return ""
    
    # Auto-select CLAUDE OPUS 4.7 (best model)
    config = load_config()
    
    # Look for explicit claude-opus model
    for key, info in models.items():
        model_id = info.get("id", "")
        if "claude-opus-4.7" in model_id.lower():
            config["model"] = key
            config["model_id"] = model_id
            save_config(config)
            print(f"{Colors.GREEN}✓ Model: {key}{Colors.END}")
            return key
    
    # Fallback to any opus model
    for key, info in models.items():
        model_id = info.get("id", "")
        if "claude-opus" in model_id.lower():
            config["model"] = key
            config["model_id"] = model_id
            save_config(config)
            print(f"{Colors.GREEN}✓ Model: {key}{Colors.END}")
            return key
    
    # Fallback to gpt-4o
    for key, info in models.items():
        model_id = info.get("id", "")
        if "gpt-4o" in model_id.lower():
            config["model"] = key
            config["model_id"] = model_id
            save_config(config)
            print(f"{Colors.GREEN}✓ Model: {key}{Colors.END}")
            return key
    
    # Fallback to first model
    first_key = list(models.keys())[0]
    first_info = models[first_key]
    config["model"] = first_key
    config["model_id"] = first_info.get("id", first_key)
    save_config(config)
    print(f"{Colors.CYAN}Model: {first_key}{Colors.END}")
    return first_key


def main():
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTSTP, lambda s, f: cleanup())
    
    model = check_setup()
    agent = Ever1Agent()
    
    print_banner()
    
    print(f"  {Colors.GRAY}Provider:{Colors.END} {agent.provider}")
    print(f"  {Colors.GRAY}Model:{Colors.END} {agent.model_id[:25]}...")
    
    if agent.conversation:
        print(f"\n{Colors.YELLOW}↻ Resume: {len(agent.conversation)} msgs{Colors.END}")
    
    print()
    print(f"{Colors.CYAN}Type /help for commands{Colors.END}\n")
    
    while True:
        try:
            user_input = input("> ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                handle_command(user_input, agent)
                continue
            
            print(f"\n{Colors.GREEN}Thinking...{Colors.END}")
            response = agent.chat(user_input)
            
            print(response)
            
            tokens = agent.get_token_display()
            if tokens:
                print(f"  {Colors.DIM}[{tokens}]{Colors.END}")
            
            print()
            
        except (KeyboardInterrupt, EOFError):
            cleanup(agent)
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")


def handle_command(cmd: str, agent: Ever1Agent):
    cmd_clean = cmd.strip()
    
    if cmd_clean == "/help":
        print(f"""
Commands:
  /exec <code> - Run code
  /read <path> - Read file  
  /write <path>=<content> - Write file
  /ls <dir>   - List files
  /vision <path> - Analyze image
  /speak <text> - Text to speech
  /clear     - Clear history
  /history  - View history
  /models   - Select model (arrows)
  /learn    - Show learnings
  /connect  - Connect to API/Ollama
  /telegram - Setup Telegram
  /quit     - Exit
""")
    
    elif cmd_clean == "/clear":
        agent.clear_history()
        print(f"✓ Cleared")
    
    elif cmd_clean == "/history":
        print(agent.show_history())
    
    elif cmd_clean == "/models":
        config = load_config()
        
        # Check for Ollama models first
        ollama_models = config.get("ollama_models", {})
        if ollama_models:
            config_model = config.get("model", "")
            selected = select_model_arrows(ollama_models, config_model)
            if selected:
                config["model"] = selected
                config["model_id"] = ollama_models[selected].get("id", selected)
                config["provider"] = "ollama"
                config["api_url"] = "http://localhost:11434/v1/chat/completions"
                save_config(config)
                print(f"{Colors.GREEN}✓ Selected: {selected}{Colors.END}")
            return
        
        # API models
        api_key = check_api_key() or config.get("api_key", "")
        
        if not api_key:
            print(f"{Colors.RED}No API key{Colors.END}")
            print(f"{Colors.CYAN}Run /connect to add one{Colors.END}")
            return
        
        provider = detect_provider(api_key)
        models = fetch_models(api_key, provider)
        
        if not models:
            print(f"{Colors.RED}No models{Colors.END}")
            return
        
        config_model = config.get("model", "")
        selected = select_model_arrows(models, config_model)
        
        if selected and selected in models:
            config["model"] = selected
            config["model_id"] = models[selected].get("id", selected)
            config["provider"] = provider
            save_config(config)
            print(f"{Colors.GREEN}✓ Selected: {selected}{Colors.END}")
    
    elif cmd_clean.startswith("/model "):
        key = cmd[7:].strip()
        print(agent.switch_model(key))
    
    elif cmd_clean == "/learn":
        learnings = get_relevant_learnings()
        print(f"\n{learnings}" if learnings else "No learnings")
    
    elif cmd_clean == "/connect" or cmd_clean.startswith("/connect "):
        print(f"\n{Colors.CYAN}Connect to API:{Colors.END}")
        
        if cmd_clean.startswith("/connect "):
            api_key = cmd_clean[8:].strip()
        else:
            api_key = input(f"API Key > ").strip()
        
        if not api_key:
            print(f"{Colors.YELLOW}API key required{Colors.END}")
            return
        
        if api_key.startswith("ollama"):
            config = load_config()
            config["provider"] = "ollama"
            config["api_url"] = "http://localhost:11434/v1/chat/completions"
            config["model"] = "llama2"
            save_config(config)
            print(f"{Colors.GREEN}✓ Connected to Ollama{Colors.END}")
            return
        
        provider = detect_provider(api_key)
        config = load_config()
        config["api_key"] = api_key
        config["provider"] = provider
        config["api_url"] = get_provider_info(provider).get("url", "") + get_provider_info(provider).get("chat_endpoint", "")
        save_config(config)
        print(f"{Colors.GREEN}✓ Connected to {provider}{Colors.END}")
        print(f"{Colors.CYAN}Loading models...{Colors.END}")
        
        models = fetch_models(api_key, provider)
        print(f"{Colors.GREEN}✓ {len(models)} models loaded{Colors.END}")
        
        if models:
            config_model = config.get("model", "")
            selected = select_model_arrows(models, config_model)
            if selected:
                config["model"] = selected
                config["model_id"] = models[selected].get("id", selected)
                save_config(config)
                print(f"{Colors.GREEN}✓ Selected: {selected}{Colors.END}")
    
    elif "/telegram" in cmd_clean.lower():
        print(f"\nTelegram Setup:")
        bot_token = input(f"Bot Token > ").strip()
        chat_id = input(f"Chat ID > ").strip()
        
        if bot_token and chat_id:
            config = load_config()
            config["telegram_bot_token"] = bot_token
            config["telegram_chat_id"] = chat_id
            save_config(config)
            print(f"✓ Telegram configured")
    
    elif cmd_clean in ["/quit", "/exit"]:
        cleanup(agent)
        sys.exit(0)
    
    else:
        print(f"Unknown: {cmd}")


def cleanup(agent=None):
    if agent:
        agent.save_state_on_quit()
    print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
    sys.exit(0)


if __name__ == "__main__":
    main()