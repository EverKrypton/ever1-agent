#!/usr/bin/env python3
import sys
import os
import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import Ever1Agent, Colors
from config import (load_config, save_config, load_state, OPENROUTER_MODELS, get_relevant_learnings,
                   load_queue, add_to_queue, clear_queue, get_model_info)


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


def print_input_box():
    line = "─" * 50
    print(f"{Colors.GRAY}┌{line}┐{Colors.END}")
    print(f"{Colors.GRAY}│{Colors.END}" + " " * 48 + f"{Colors.GRAY}│{Colors.END}")
    

def main():
    signal.signal(signal.SIGINT, lambda s, f: (print(f"\n{Colors.GRAY}Esc pressed, exiting...{Colors.END}"), 
                                         clean_exit()))
    signal.signal(signal.SIGTSTP, lambda s, f: clean_exit())
    
    agent = Ever1Agent()
    
    print_banner()
    
    print(f"  {Colors.GRAY}Provider:{Colors.END} {agent.provider}")
    print(f"  {Colors.GRAY}Model:{Colors.WHITE} {agent.model_info['name']}{Colors.END}")
    print(f"  {Colors.GRAY}Queue:{Colors.END} {len(load_queue())} pending")
    
    token_info = agent.get_token_display()
    if token_info:
        print(f"  {Colors.GRAY}Session:{Colors.END} {token_info}")
    
    warnings = []
    if not agent.config.get("api_key") and not os.getenv("OPENROUTER_API_KEY"):
        warnings.append("No API key set")
    
    if warnings:
        print(f"  {Colors.YELLOW}⚠ {', '.join(warnings)}{Colors.END}")
    
    print()
    
    state = load_state()
    if state.get("pending_tasks"):
        print(f"{Colors.YELLOW}⚠ You have pending tasks from last session{Colors.END}")
        print(f"{Colors.GRAY}   Type /tasks to see them{Colors.END}\n")
    
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
            clean_exit(agent)
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
  {Colors.BLUE}/model{Colors.END}   - Switch model
  {Colors.BLUE}/models{Colors.END}- List available models
  {Colors.BLUE}/learn{Colors.END}  - Show learnings
  {Colors.BLUE}/config{Colors.END} - Edit config
  {Colors.BLUE}/quit{Colors.END}   - Exit (saves state)

{Colors.CYAN}Tool Commands:{Colors.END}
  {Colors.BLUE}/exec <code>{Colors.END}  - Run Python code
  {Colors.BLUE}/read <path>{Colors.END} - Read file
  {Colors.BLUE}/write <path>=<content>{Colors.END} - Write file
  {Colors.BLUE}/ls <dir>{Colors.END}   - List files
  {Colors.BLUE}/todo <list>{Colors.END} - Create todo list

{Colors.CYAN}Tips:{Colors.END}
  • Press {Colors.YELLOW}Ctrl+Z{Colors.END} to interrupt
  • Add "queue" to add task to queue
  • Use ! before command for quick access
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
        else:
            print(f"{Colors.YELLOW}Usage: /queue <task description>{Colors.END}")
    
    elif cmd_clean == "/model":
        print(f"\n{Colors.CYAN}Current: {agent.model_info['name']}{Colors.END}")
        print("Use /model <name> to switch")
        print("Models available:")
        for key, info in OPENROUTER_MODELS.items():
            price = "FREE" if info["price_input"] == 0 else f"${info['price_input']}/1k"
            print(f"  {Colors.BLUE}{key}{Colors.END}: {info['name']} ({price})")
    
    elif cmd_clean.startswith("/model "):
        model_key = cmd[7:].strip()
        if model_key in OPENROUTER_MODELS:
            agent.switch_model(model_key)
            print(f"{Colors.GREEN}Model switched. Restart not needed.{Colors.END}")
        else:
            print(f"{Colors.RED}Unknown model: {model_key}{Colors.END}")
            print("Use /models to see available")
    
    elif cmd_clean == "/models":
        print(f"\n{Colors.CYAN}Available Models:{Colors.END}")
        for key, info in OPENROUTER_MODELS.items():
            price_in = "FREE" if info["price_input"] == 0 else f"${info['price_input']}/1k"
            price_out = "FREE" if info["price_output"] == 0 else f"${info['price_output']}/1k"
            current = " {Colors.GREEN}●{Colors.END}" if key == agent.model_key else ""
            print(f"  {Colors.BLUE}{key}{Colors.END}: {info['name']} ({price_in}/{price_out}){current}")
    
    elif cmd_clean == "/learn":
        learnings = get_relevant_learnings()
        if learnings:
            print(f"\n{learnings}")
        else:
            print(f"{Colors.GRAY}No learnings yet{Colors.END}")
    
    elif cmd_clean == "/config":
        config = load_config()
        print(f"\n{Colors.CYAN}Configuration:{Colors.END}")
        for k, v in config.items():
            if k == "api_key" and v:
                print(f"  {k}: {'*' * 20}")
            elif k == "system_prompt":
                print(f"  {k}: (see file)")
            else:
                print(f"  {k}: {v}")
    
    elif cmd_clean in ["/quit", "/exit", "!/"]:
        clean_exit(agent)
        sys.exit(0)
    
    else:
        print(f"{Colors.YELLOW}Unknown: {cmd}{Colors.END}")
        print(f"Type {Colors.BLUE}/help{Colors.END}")


def clean_exit(agent=None):
    if agent:
        agent.save_state_on_quit()
    print(f"\n{Colors.CYAN}Goodbye!{Colors.END}")
    sys.exit(0)


if __name__ == "__main__":
    main()