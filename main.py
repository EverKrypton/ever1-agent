#!/usr/bin/env python3
"""Ever-1 AI Agent - Main Entry Point"""
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import Ever1Agent, Colors, Emoji
from config import (load_config, save_config, load_state, get_relevant_learnings,
                   load_queue, add_to_queue, get_provider_info,
                   check_api_key, check_ollama, get_available_models, PROVIDERS,
                   detect_provider, fetch_models)


def print_banner():
    banner = f"""
{Colors.GRAY}╔══════════════════════════════════════════════════════════════════╗
║  {Colors.WHITE}  ____  _      _     ____                        _                 {Colors.GRAY}║
║  {Colors.WHITE} |  _ \\| |    | |   / ___| _ __ ___  ___ ___ | | __              {Colors.GRAY}║
║  {Colors.WHITE} | |_) | |    | |   \\___ \\| '__/ _ \\/ __/ __| |/ /              {Colors.GRAY}║
║  {Colors.WHITE} |  __/| |____| |    ___) | | |  __/\\__ \\ (__|   <               {Colors.GRAY}║
║  {Colors.WHITE} |_|   |______|_|   |____/|_|  \\___||___/\\___|_|\\_\\              {Colors.GRAY}║
║                                                                    ║
║  {Colors.BLUE}Self-Learning AI Agent • Vision • Voice • Telegram   {Colors.GRAY}║
╚══════════════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)


def check_setup() -> str:
    """Initial setup and model selection"""
    print(f"\n{Colors.CYAN}Checking configuration...{Colors.END}")
    
    api_key = check_api_key()
    ollama = check_ollama()
    
    if not api_key and not ollama:
        print(f"\n{Colors.RED}⚠ No API key detected{Colors.END}")
        print(f"\n{Colors.YELLOW}Enter API key:{Colors.END}")
        print(f"{Colors.GRAY}(OpenRouter, OpenAI, or Anthropic){Colors.END}")
        
        new_key = input(f"\n{Colors.GREEN}API Key{Colors.GRAY}:{Colors.END} ").strip()
        
        if new_key:
            provider = detect_provider(new_key)
            config = load_config()
            config["api_key"] = new_key
            config["provider"] = provider
            save_config(config)
            api_key = new_key
            print(f"{Colors.GREEN}✓ Saved ({provider}){Colors.END}\n")
    
    if api_key:
        provider = detect_provider(api_key)
        print(f"{Colors.GREEN}✓ {get_provider_info(provider)['name']}{Colors.END}")
    
    if ollama:
        print(f"{Colors.GREEN}✓ Ollama running{Colors.END}")
    
    print(f"\n{Colors.CYAN}Fetching models...{Colors.END}")
    models = fetch_models(api_key, detect_provider(api_key))
    
    if not models:
        print(f"{Colors.YELLOW}No models found{Colors.END}")
        return ""
    
    print(f"\n{Colors.CYAN}Available Models ({len(models)}):{Colors.END}")
    
    free_models = [(k, v) for k, v in models.items() if v.get("free")]
    paid_models = [(k, v) for k, v in models.items() if not v.get("free")]
    
    for key, info in free_models[:8]:
        print(f"  {Colors.GREEN}{key:15}{Colors.END} {info['name'][:20]} [FREE]")
    
    for key, info in paid_models[:5]:
        print(f"  {Colors.BLUE}{key:15}{Colors.END} {info['name'][:20]}")
    
    current = load_config().get("model", "")
    print(f"\n{Colors.CYAN}Current:{Colors.END} {current or 'auto'}")
    
    choice = input(f"\n{Colors.GREEN}Select{Colors.GRAY}(enter){Colors.END}: ").strip()
    
    if choice and choice in models:
        config = load_config()
        config["model"] = choice
        config["model_id"] = models[choice].get("id", choice)
        save_config(config)
        print(f"{Colors.GREEN}✓ {choice}{Colors.END}")
        return choice
    
    return current


def main():
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTSTP, lambda s, f: cleanup())
    
    model = check_setup()
    agent = Ever1Agent()
    
    print_banner()
    
    print(f"  {Colors.GRAY}Provider:{Colors.END} {agent.provider}")
    print(f"  {Colors.GRAY}Model:{Colors.END} {agent.model_id}")
    
    if agent.conversation:
        print(f"\n{Colors.YELLOW}↻ Resuming ({len(agent.conversation)} messages){Colors.END}")
    
    print()
    
    # Main loop
    while True:
        try:
            user_input = input(f"{Colors.GRAY}┌─:{Colors.END}{Colors.GREEN}You{Colors.GRAY}:─>{Colors.END} ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                handle_command(user_input, agent)
                continue
            
            print()
            
            # Think briefly
            print(f"{Emoji.THINKING} Thinking...")
            response = agent.chat(user_input)
            
            # Show response
            print(response)
            
            # Show tokens
            tokens = agent.get_token_display()
            if tokens:
                print(f"  {Colors.GRAY}[{tokens}]{Colors.END}")
            
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
{Emoji.CODE} /exec <code>  - Run code
{Emoji.FILE} /read <path> - Read file
{Emoji.FILE} /write <path>=<content> - Write file
{Emoji.FILE} /ls <dir>   - List files
{Emoji.VISION} /vision <path> - Analyze image
{Emoji.SPEAK} /speak <text> - Text to speech
{Emoji.CODE} /clear     - Clear history
{Emoji.CODE} /history  - View history
{Emoji.CODE} /models   - List models
{Emoji.CODE} /model <name> - Switch model
{Emoji.CODE} /learn    - Show learnings
{Emoji.CODE} /telegram - Setup Telegram
{Emoji.CODE} /quit     - Exit
""")
    
    elif cmd_clean == "/clear":
        agent.clear_history()
        print(f"{Colors.GREEN}✓ Cleared{Colors.END}")
    
    elif cmd_clean == "/history":
        print(agent.show_history())
    
    elif cmd_clean == "/models":
        api_key = check_api_key()
        models = fetch_models(api_key, detect_provider(api_key))
        
        if not models:
            print(f"{Colors.RED}No models{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}Models ({len(models)}):{Colors.END}")
        for key, info in list(models.items())[:20]:
            current = " ←" if key == agent.model_key else ""
            free = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get("free") else ""
            vision = f" {Colors.CYAN}[Vision]{Colors.END}" if info.get("vision") else ""
            print(f"  {Colors.BLUE}{key}{Colors.END}{free}{vision}{current}")
    
    elif cmd_clean.startswith("/model "):
        key = cmd[7:].strip()
        print(agent.switch_model(key))
    
    elif cmd_clean == "/learn":
        learnings = get_relevant_learnings()
        print(f"\n{learnings}" if learnings else "No learnings")
    
    elif "/telegram" in cmd_clean:
        print(f"\n{Colors.CYAN}Telegram Setup:{Colors.END}")
        print("1. Create bot: @BotFather on Telegram")
        print("2. Get bot token")
        print("3. Start chat with bot to get chat_id")
        
        bot_token = input(f"{Colors.GREEN}Bot Token{Colors.GRAY}:{Colors.END} ").strip()
        chat_id = input(f"{Colors.GREEN}Chat ID{Colors.GRAY}:{Colors.END} ").strip()
        
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