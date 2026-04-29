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
╔═══════════════════════════════╗
║      EVER-1 AI Agent          ║
║  Self-Learning AI             ║
╚═══════════════════════════════╝
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
        # Clear previous lines
        for _ in range(len(model_list) + 2):
            sys.stdout.write('\033[F')
        
        print(f"\n{Colors.CYAN}Use ↑↓ arrows, ENTER:{Colors.END}\n")
        
        for i, key in enumerate(model_list):
            info = models[key]
            marker = "→" if i == current_index else " "
            name = info.get('name', key)[:25]
            free = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get('free') else ""
            
            if i == current_index:
                print(f"{Colors.CYAN}{marker} {key:15} {name}{free}{Colors.END}")
            else:
                print(f"  {Colors.GRAY}{key:15} {Colors.DIM}{name}{free}{Colors.END}")
        
        key = get_key()
        
        if key == 'UP':
            current_index = (current_index - 1) % len(model_list)
        elif key == 'DOWN':
            current_index = (current_index + 1) % len(model_list)
        elif key == '':
            # Enter key
            break
        
        import time
        time.sleep(0.05)
    
    return model_list[current_index]


def check_setup() -> str:
    """Initial setup"""
    print(f"\n{Colors.CYAN}Checking...{Colors.END}")
    
    api_key = check_api_key()
    ollama = check_ollama()
    
    if not api_key:
        config = load_config()
        api_key = config.get("api_key", "")
    
    if not api_key and not ollama:
        print(f"\n{Colors.YELLOW}No API key found{Colors.END}")
    
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
            user_input = input(f"{Colors.GREEN}> {Colors.END}").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                handle_command(user_input, agent)
                continue
            
            print(f"\n{Emoji.THINKING} Thinking...")
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
    cmd_clean = cmd.lower().strip()
    
    if cmd_clean == "/help":
        print(f"""
{Emoji.CODE} Commands:
  /exec <code> - Run code
  /read <path> - Read file  
  /write <path>=<content> - Write file
  /ls <dir>   - List files
  /vision <path> - Analyze image
  /speak <text> - Text to speech
  /clear     - Clear history
  /history  - View history
  /models   - List models
  /model <name> - Switch model
  /learn    - Show learnings
  /telegram - Setup Telegram
  /quit     - Exit
""")
    
    elif cmd_clean == "/clear":
        agent.clear_history()
        print(f"{Colors.GREEN}✓ Cleared{Colors.END}")
    
    elif cmd_clean == "/history":
        print(agent.show_history())
    
    elif cmd_clean == "/models":
        api_key = check_api_key()
        config = load_config()
        api_key = api_key or config.get("api_key", "")
        provider = detect_provider(api_key)
        models = fetch_models(api_key, provider)
        
        if not models:
            print(f"{Colors.RED}No models{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}Models ({len(models)}):{Colors.END}")
        
        # Just show models, no arrow selection
        for key, info in list(models.items())[:15]:
            free = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get("free") else ""
            current = " ←" if key == agent.model_key else ""
            print(f"  {Colors.BLUE}{key}{Colors.END}{free}{current}")
    
    elif cmd_clean.startswith("/model "):
        key = cmd[7:].strip()
        print(agent.switch_model(key))
    
    elif cmd_clean == "/learn":
        learnings = get_relevant_learnings()
        print(f"\n{learnings}" if learnings else "No learnings")
    
    elif "/telegram" in cmd_clean:
        print(f"\n{Colors.CYAN}Telegram Setup:{Colors.END}")
        bot_token = input(f"{Colors.GREEN}Bot Token{Colors.END} > ").strip()
        chat_id = input(f"{Colors.GREEN}Chat ID{Colors.END} > ").strip()
        
        if bot_token and chat_id:
            config = load_config()
            config["telegram_bot_token"] = bot_token
            config["telegram_chat_id"] = chat_id
            save_config(config)
            print(f"{Colors.GREEN}✓ Telegram configured{Colors.END}")
    
    elif cmd_clean in ["/quit", "/exit"]:
        cleanup(agent)
        sys.exit(0)
    
    else:
        print(f"{Colors.YELLOW}Unknown: {cmd}{Colors.END}")


def cleanup(agent=None):
    if agent:
        agent.save_state_on_quit()
    print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
    sys.exit(0)


if __name__ == "__main__":
    main()