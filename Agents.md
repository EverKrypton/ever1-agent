# Ever-1 Agent Configuration

## API
provider: openrouter
api_url: https://openrouter.ai/api/v1/chat/completions
model: minimax

## Models Available
models:
  minimax: Minimax 2.5 (Free)
  qwen: Qwen 2.5 7B
  llama: Llama 3.1 8B 
  gpt4o: GPT-4o
  claude: Claude 3.5

## Behavior
temperature: 0.7
think_steps: 3
max_history: 20

## Memory & Learning
learn_from_tasks: true
auto_evaluate: true
save_state_on_quit: true

## Tools Enabled
tools:
  code_execution: true
  file_reading: true
  vision: false
  tts: false

## Features
show_tokens: true
show_price: true
interrupt_key: Ctrl+Z
queue_enabled: true