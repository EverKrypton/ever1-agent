#!/usr/bin/env python3
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import Ever1Agent, Colors
from config import (load_config, save_config, load_state, get_relevant_learnings,
                   load_queue, add_to_queue, clear_queue, get_provider_info,
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
║  {Colors.BLUE}Self-Learning AI Agent • Autonomous • Secure                    {Colors.GRAY}║
╚══════════════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)


def check_and_setup() -> str:
    """Check API key, detect provider, fetch models, return model choice"""
    print(f"\n{Colors.CYAN}Checking configuration...{Colors.END}")
    
    api_key = check_api_key()
    ollama_running = check_ollama()
    
    if not api_key and not ollama_running:
        print(f"\n{Colors.RED}⚠ No API key detected and Ollama not running{Colors.END}")
        print(f"\n{Colors.YELLOW}Please enter your API key:{Colors.END}")
        print(f"{Colors.GRAY}(OpenRouter, OpenAI, or Anthropic - Get key from their website){Colors.END}")
        
        new_key = input(f"\n{Colors.GREEN}API Key{Colors.GRAY}:{Colors.END} ").strip()
        
        if new_key:
            provider = detect_provider(new_key)
            config = load_config()
            config["api_key"] = new_key
            config["provider"] = provider
            save_config(config)
            api_key = new_key
            print(f"{Colors.GREEN}✓ API key saved ({provider}){Colors.END}\n")
    
    if api_key:
        provider = detect_provider(api_key)
        provider_info = get_provider_info(provider)
        print(f"{Colors.GREEN}✓ {provider_info['name']} detected{Colors.END}")
    
    if ollama_running:
        print(f"{Colors.GREEN}✓ Ollama is running{Colors.END}")
    
    print(f"\n{Colors.CYAN}Fetching models from API...{Colors.END}")
    models = fetch_models(api_key, provider)
    
    if not models:
        print(f"{Colors.YELLOW}Could not fetch models, using defaults{Colors.END}")
        models = {}
    
    print(f"\n{Colors.CYAN}Available Models ({len(models)}):{Colors.END}")
    
    # Show first 15 models
    for i, (key, info) in enumerate(list(models.items())[:15]):
        price_in = "FREE" if info["price_input"] == 0 else f"${info['price_input']:.5f}/1k"
        price_out = "FREE" if info["price_output"] == 0 else f"${info['price_output']:.5f}/1k"
        free_tag = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get("free") else ""
        print(f"  {Colors.BLUE}{key:20}{Colors.END} ({price_in}/{price_out}){free_tag}")
    
    current = load_config().get("model", "")
    print(f"\n{Colors.CYAN}Current model:{Colors.END} {Colors.WHITE}{current or 'auto'}{Colors.END}")
    
    choice = input(f"\n{Colors.GREEN}Select model{Colors.GRAY}(enter for auto){Colors.END}: ").strip()
    
    if choice and choice in models:
        config = load_config()
        config["model"] = choice
        config["model_id"] = models[choice].get("id", choice)
        save_config(config)
        print(f"{Colors.GREEN}✓ Model set to {choice}{Colors.END}")
        return choice
    
    return current


def main():
    signal.signal(signal.SIGINT, lambda s, f: cleanup())
    signal.signal(signal.SIGTSTP, lambda s, f: cleanup())
    
    model = check_and_setup()
    agent = Ever1Agent()
    
    print_banner()
    
    print(f"  {Colors.GRAY}Provider:{Colors.END} {agent.provider}")
    print(f"  {Colors.GRAY}Model:{Colors.WHITE} {agent.model_id}{Colors.END}")
    print(f"  {Colors.GRAY}Queue:{Colors.END} {len(load_queue())} tasks")
    
    token_info = agent.get_token_display()
    if token_info:
        print(f"  {Colors.GRAY}Session:{Colors.END} {token_info}")
    
    # Load previous conversation if exists
    if agent.conversation:
        print(f"\n{Colors.YELLOW}Resuming previous conversation ({len(agent.conversation)} messages){Colors.END}")
    
    print()
    
    state = load_state()
    if state.get("pending_tasks"):
        print(f"{Colors.YELLOW}⚠ Pending tasks from last session{Colors.END}")
        for task in state["pending_tasks"][:3]:
            print(f"  • {task.get('description', 'Task')}")
        print()
    
    while True:
        try:
            prompt = f"{Colors.GRAY}┌─:{Colors.END}{Colors.GREEN}You{Colors.GRAY}:─>{Colors.END} "
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/") or user_input.startswith("!"):
                handle_command(user_input, agent)
                continue
            
            print()
            
            for chunk in agent.chat(user_input, stream=True):
                print(chunk, end="", flush=True)
            
            print()
            
            token_info = agent.get_token_display()
            if token_info:
                print(f"  {Colors.GRAY}[{token_info}]{Colors.END}")
            
            queue = load_queue()
            if queue:
                print(f"  {Colors.CYAN}⚡ {len(queue)} tasks in queue{Colors.END}")
            
            print()
            
        except (KeyboardInterrupt, EOFError):
            cleanup(agent)
            break
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.END}")


def handle_command(cmd: str, agent: Ever1Agent):
    cmd_clean = cmd.lower().strip()
    
    if cmd_clean in ["/help", "!??"]:
        print(f"""
{Colors.CYAN}Commands:{Colors.END}
  {Colors.BLUE}/help{Colors.END}     - Show this help
  {Colors.BLUE}/clear{Colors.END}   - Clear history
  {Colors.BLUE}/history{Colors.END}- View history
  {Colors.BLUE}/tasks{Colors.END}  - Show queue tasks
  {Colors.BLUE}/queue{Colors.END} <task> - Add task to queue
  {Colors.BLUE}/models{Colors.END}- List available models
  {Colors.BLUE}/model{Colors.END} <name> - Switch model
  {Colors.BLUE}/learn{Colors.END}  - Show learnings
  {Colors.BLUE}/quit{Colors.END}   - Exit (saves state)

{Colors.CYAN}Tool Commands:{Colors.END}
  {Colors.BLUE}/exec <code>{Colors.END}  - Run Python code
  {Colors.BLUE}/read <path>{Colors.END} - Read file
  {Colors.BLUE}/write <path>=<content>{Colors.END} - Write file
  {Colors.BLUE}/ls <dir>{Colors.END}   - List files
""")
    
    elif cmd_clean == "/clear":
        agent.clear_history()
    
    elif cmd_clean == "/history":
        agent.show_history()
    
    elif cmd_clean in ["/tasks", "/queue"]:
        agent.show_queue()
    
    elif cmd_clean.startswith("/queue "):
        task_desc = cmd[7:].strip()
        if task_desc:
            add_to_queue({"description": task_desc, "added": "now"})
            print(f"{Colors.GREEN}✓ Added to queue: {task_desc}{Colors.END}")
    
    elif cmd_clean == "/models":
        api_key = check_api_key()
        provider = detect_provider(api_key)
        models = fetch_models(api_key, provider)
        
        if not models:
            print(f"{Colors.YELLOW}Could not fetch models{Colors.END}")
            return
        
        print(f"\n{Colors.CYAN}Available Models ({len(models)}):{Colors.END}")
        for key, info in list(models.items())[:25]:
            price_in = "FREE" if info["price_input"] == 0 else f"${info['price_input']:.5f}/1k"
            price_out = "FREE" if info["price_output"] == 0 else f"${info['price_output']:.5f}/1k"
            current = " (current)" if key == agent.model_key else ""
            free = f" {Colors.GREEN}[FREE]{Colors.END}" if info.get("free") else ""
            print(f"  {Colors.BLUE}{key}{Colors.END}: ({price_in}/{price_out}){free}{current}")
    
    elif cmd_clean.startswith("/model "):
        model_key = cmd[7:].strip()
        agent.switch_model(model_key)
    
    elif cmd_clean == "/model":
        print(f"\n{Colors.CYAN}Current: {agent.model_id}{Colors.END}")
        print("Use /model <name> to switch")
    
    elif cmd_clean == "/learn":
        learnings = get_relevant_learnings()
        print(f"\n{learnings}" if learnings else f"{Colors.GRAY}No learnings yet{Colors.END}")
    
    elif cmd_clean in ["/quit", "/exit"]:
        cleanup(agent)
        sys.exit(0)
    
    else:
        print(f"{Colors.YELLOW}Unknown: {cmd}{Colors.END}")
        print(f"Type {Colors.BLUE}/help{Colors.END}")


def cleanup(agent=None):
    if agent:
        agent.save_state_on_quit()
    print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
    sys.exit(0)


if __name__ == "__main__":
    main()