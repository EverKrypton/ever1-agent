# Ever-1 — Fix Completo para Termux + Roadmap SaaS/AaaS

---

## Diagnóstico: Por qué falla la instalación en Termux

Hay **7 categorías de bugs** críticos distribuidos en todos los archivos. Ninguno por sí solo rompe todo, pero juntos hacen que el agente sea inoperable en Termux y poco confiable en producción.

---

## BUG 1 — `install.sh` / `quick_install.sh`: Incompatibilidades con Termux

### Problemas detectados

**1a. `set -euo pipefail` rompe en Termux si cualquier comando falla silenciosamente.**
El script usa `set -e` + `set -u` combinados. En Termux, comandos como `grep` retornan exit code 1 cuando no encuentran coincidencias (comportamiento normal), y eso mata el script completo sin mensaje de error útil.

**1b. `$HOME/.local/bin` no está en el PATH de Termux por defecto.**
Termux usa `/data/data/com.termux/files/usr/bin` como PATH primario. El script crea el ejecutable en `~/.local/bin/everai` pero ese directorio no existe ni está en PATH, así que `everai` nunca es encontrado.

**1c. No instala dependencias Python antes de correr `main.py`.**
El script descarga los `.py` y ejecuta `python3 main.py` inmediatamente sin un `pip install requests` previo. Falla con `ModuleNotFoundError`.

**1d. `readline>=6.2` en `requirements.txt` no es un paquete pip.**
`readline` es una librería C del sistema. `pip install readline` falla con error de compilación en Termux. Debe eliminarse.

**1e. El heredoc Python en `install.sh` tiene comillas que el shell interpreta mal.**
```bash
python3 << PYEOF   # ← sin comillas en el delimitador, el shell expande variables
```
La variable `$DIR` dentro del heredoc se expande por el shell, no por Python. Si `$DIR` contiene espacios o caracteres especiales, la ruta en el JSON queda corrupta.

**1f. `curl` puede no estar instalado en Termux fresh.**
Termux minimal no incluye curl. El script debe verificar e instalar `curl` + `python` antes de usarlos.

**1g. `source ~/.bashrc` al final de `quick_install.sh` no tiene efecto en el proceso actual.**
`source` modifica el shell actual, pero el script corre en un subshell. El usuario nunca ve `everai` disponible sin abrir una nueva sesión.

### Fix: `install.sh` completo

```bash
#!/data/data/com.termux/files/usr/bin/bash
# Ever-1 Install - Termux Compatible
set -e

AGENT_DIR="$HOME/.ever1-agent"
TERMUX_BIN="/data/data/com.termux/files/usr/bin"
LOCAL_BIN="$HOME/.local/bin"

echo ""
echo "========================================"
echo "         EVER-1 AI AGENT                "
echo "========================================"

# 1. Instalar dependencias del sistema si no existen
for pkg in curl python; do
  if ! command -v "$pkg" &>/dev/null; then
    echo "Instalando $pkg..."
    pkg install -y "$pkg"
  fi
done

# 2. Actualizar pip y instalar dependencias Python
echo "Instalando dependencias Python..."
pip install --quiet --upgrade requests 2>/dev/null || true

# 3. Crear directorio del agente
mkdir -p "$AGENT_DIR"

# 4. Descargar archivos del agente
BASE_URL="https://raw.githubusercontent.com/EverKrypton/ever1-agent/main"
for f in main.py client.py config.py tools.py telegram_bot.py __init__.py; do
  echo "Descargando $f..."
  curl -fsSL "$BASE_URL/$f" -o "$AGENT_DIR/$f"
done

# 5. Crear config inicial (sin heredoc problemático)
python3 - <<'PYEOF'
import json, os, sys

cfg_path = os.path.join(os.path.expanduser("~"), ".ever1-agent", "config.json")

# Solo crear si no existe (no sobreescribir config existente)
if not os.path.exists(cfg_path):
    cfg = {
        "provider": "openrouter",
        "api_key": "",
        "model": "",
        "model_id": "",
        "temperature": 0.7,
        "stream": True,
        "show_tokens": True,
        "show_price": True
    }
    with open(cfg_path, "w") as f:
        json.dump(cfg, f, indent=2)
    print("Config inicial creada.")
else:
    print("Config existente preservada.")
PYEOF

# 6. Crear ejecutable en ubicación que Termux sí tiene en PATH
EXEC_PATH="$TERMUX_BIN/everai"
cat > "$EXEC_PATH" << 'BASHEOF'
#!/data/data/com.termux/files/usr/bin/bash
cd "$HOME/.ever1-agent"
exec python3 main.py "$@"
BASHEOF
chmod +x "$EXEC_PATH"

# También crear en ~/.local/bin por si el usuario usa bash estándar
mkdir -p "$LOCAL_BIN"
cp "$EXEC_PATH" "$LOCAL_BIN/everai"

echo ""
echo "========================================"
echo "✓ Instalación completada"
echo "  Ejecutar: everai"
echo "  O: python3 ~/.ever1-agent/main.py"
echo "========================================"
echo ""

# Preguntar si configurar API key ahora
read -p "¿Ingresar API key de OpenRouter ahora? (s/n): " ans
if [ "$ans" = "s" ] || [ "$ans" = "S" ]; then
  read -p "API Key: " api_key
  if [ -n "$api_key" ]; then
    python3 - "$api_key" <<'PYEOF'
import json, sys, os
key = sys.argv[1]
cfg_path = os.path.join(os.path.expanduser("~"), ".ever1-agent", "config.json")
with open(cfg_path) as f:
    cfg = json.load(f)
cfg["api_key"] = key
with open(cfg_path, "w") as f:
    json.dump(cfg, f, indent=2)
print("✓ API key guardada.")
PYEOF
  fi
fi

cd "$AGENT_DIR"
python3 main.py
```

---

## BUG 2 — `requirements.txt`: Paquete inválido

### Fix: `requirements.txt`

```
requests>=2.31.0
```

Eliminar `openai`, `rich`, `python-dotenv` y `readline`. El agente usa `urllib` (stdlib) directamente, no el SDK de OpenAI. Instalar paquetes que no se usan aumenta el tiempo de setup y puede fallar en Termux.

Para TTS opcional, documentar por separado:
```bash
pip install pyttsx3   # Solo si tienes espeak instalado: pkg install espeak
pip install gtts      # Alternativa usando Google TTS (requiere internet)
```

---

## BUG 3 — `main.py`: Comandos de herramientas nunca llegan al agente

### Problema crítico

```python
while True:
    user_input = input(...)
    
    if user_input.startswith("/"):
        handle_command(user_input, agent)  # ← /exec, /read, /ls van aquí
        continue
    
    response = agent.chat(user_input)  # ← /exec nunca llega aquí
```

`handle_command` solo maneja: `/help`, `/clear`, `/history`, `/models`, `/model`, `/learn`, `/telegram`, `/quit`.

Los comandos `/exec`, `/read`, `/write`, `/ls`, `/vision`, `/speak` caen en el `else` de `handle_command` y imprimen `"Unknown: /exec ..."`. Nunca ejecutan código ni leen archivos.

### Fix en `handle_command`

```python
TOOL_COMMANDS = {"/exec", "/read", "/write", "/ls", "/vision", "/speak"}

def handle_command(cmd: str, agent: Ever1Agent):
    cmd_clean = cmd.lower().strip()
    
    # Reenviar comandos de herramientas al agente directamente
    for tc in TOOL_COMMANDS:
        if cmd_clean.startswith(tc):
            print(f"\n{Emoji.PROCESSING} Procesando...")
            response = agent.chat(cmd)
            print(response)
            tokens = agent.get_token_display()
            if tokens:
                print(f"  {Colors.DIM}[{tokens}]{Colors.END}")
            return
    
    if cmd_clean == "/help":
        # ... resto igual
```

### Problema secundario: `tty`/`termios` en Termux

La función `get_key()` llama `tty.setraw()` que puede corromper el terminal de Termux si ocurre una excepción dentro. Siempre debe ir en un bloque `try/finally` que restaure el terminal. Ya está así en el código pero la función `select_model_arrows` no la llama desde el flujo principal — no es un problema bloqueante, pero sí molesto.

### Fix: envolver `get_key` con restauración garantizada

```python
def get_key() -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # Leer secuencia de escape completa con timeout implícito
            try:
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    return {'A': 'UP', 'B': 'DOWN', 'C': 'RIGHT', 'D': 'LEFT'}.get(ch3, '')
            except Exception:
                return ''
        if ch in ('\r', '\n'):
            return 'ENTER'
        return ch
    except Exception:
        return ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

---

## BUG 4 — `tools.py`: Clave `output` ausente en resultados

### Problema

`client.py` siempre accede al resultado de herramientas con:
```python
output = result.get("output", "Done")
```

Pero `tools.py` retorna claves distintas según la herramienta:
- `read_file` → retorna `result["content"]`, nunca `result["output"]`
- `list_files` → retorna `result["files"]`, nunca `result["output"]`
- `write_file` → no retorna `result["output"]`

**Resultado**: `/read ~/.bashrc` siempre muestra `"✅ Done"` en lugar del contenido del archivo.

### Fix en `tools.py` — normalizar todas las respuestas

```python
def read_file(self, path: str, limit: int = 5000) -> dict:
    result = {"success": False, "output": "", "error": ""}
    try:
        path = os.path.expanduser(path)
        if not os.path.exists(path):
            result["error"] = f"Archivo no encontrado: {path}"
            return result
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(limit)
        if len(content) >= limit:
            content += f"\n... (truncado en {limit} caracteres)"
        result["output"] = content
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result

def write_file(self, path: str, content: str) -> dict:
    result = {"success": False, "output": "", "error": ""}
    try:
        path = os.path.expanduser(path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        result["output"] = f"Escrito: {path} ({len(content)} bytes)"
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result

def list_files(self, path: str = ".", pattern: str = "*") -> dict:
    result = {"success": False, "output": "", "error": ""}
    try:
        path = os.path.expanduser(path)
        p = Path(path)
        files = list(p.glob(pattern if "*" in pattern else f"*{pattern}*"))
        lines = [f"{'📁' if f.is_dir() else '📄'} {f.name}" for f in sorted(files)[:30]]
        result["output"] = "\n".join(lines) if lines else "(vacío)"
        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    return result
```

---

## BUG 5 — `client.py`: Fallback de streaming usa payload incorrecto

### Problema

```python
payload = {
    "model": self.model_id,
    "messages": messages,
    "temperature": self.temperature,
    "stream": True,   # ← stream=True en payload
}

# ... intento streaming ...

if not response_text:
    # Fallback "non-streaming"
    req = Request(chat_url, data=json.dumps(payload).encode(), ...)  # ← mismo payload con stream=True
    with urlopen(req, timeout=60) as response:
        result = json.loads(response.read())  # ← OpenRouter devuelve stream, no JSON plano
```

El fallback falla exactamente igual que el intento original porque el payload no cambia.

### Fix en `_api_chat`

```python
def _api_chat(self, user_input: str, stream: bool, image_data: str = None) -> str:
    messages = self._build_messages(user_input, image_data)
    chat_url = get_chat_url(self.provider)
    headers = {
        "Authorization": f"Bearer {self.api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ever1.local",
        "X-Title": "Ever-1",
    }

    # Intento 1: streaming
    if stream:
        stream_payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "stream": True,
        }
        try:
            req = Request(chat_url, data=json.dumps(stream_payload).encode(), headers=headers, method="POST")
            response_text = ""
            with urlopen(req, timeout=120) as response:
                for raw_line in response:
                    if self.interrupted:
                        return "⚠ Interrumpido"
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        response_text += delta.get("content", "")
                        usage = chunk.get("usage") or {}
                        if usage:
                            self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
                    except json.JSONDecodeError:
                        continue
            if response_text:
                self._record_response(user_input, response_text)
                return response_text
        except Exception:
            pass  # Caer al fallback no-streaming

    # Intento 2: non-streaming (fallback o cuando stream=False)
    sync_payload = {
        "model": self.model_id,
        "messages": messages,
        "temperature": self.temperature,
        "stream": False,
    }
    try:
        req = Request(chat_url, data=json.dumps(sync_payload).encode(), headers=headers, method="POST")
        with urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
        response_text = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        self.tokens.update(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        self._record_response(user_input, response_text)
        return response_text
    except Exception as e:
        return f"❌ Error: {str(e)}"

def _record_response(self, user_input: str, response_text: str):
    evaluation = self._self_evaluate(response_text)
    add_learning("chat", user_input[:100], evaluation["score"] > 6, evaluation["score"], evaluation["notes"])
    self.conversation.append([user_input, response_text])
    self._save_state()
```

---

## BUG 6 — `telegram_bot.py`: Parsing de callbacks roto

### Problema

El callback_data se guarda como `"task_confirm_task_1234567890"` pero al parsear:

```python
cb = callback_data.split("_")
# cb = ["task", "confirm", "task", "1234567890"]

task_id = "_".join(cb[1:])
# task_id = "confirm_task_1234567890"  ← nunca coincide con la clave guardada
```

Las tareas pendientes nunca se confirman ni rechazan. El bot queda en estado colgado.

También, `self.answer_callback(f"{cb[1]}_{task_id}", ...)` pasa el string reconstruido en lugar del `callback_query_id` real que viene del update de Telegram.

### Fix: usar separador distinto para el prefijo

```python
# Al crear los botones, usar ":" como separador del prefijo
def create_task_buttons(self, task_id: str, description: str) -> tuple:
    keyboard = InlineKeyboard()
    keyboard.add_row(
        InlineButton("✅ Confirmar", f"confirm:{task_id}"),
        InlineButton("❌ Rechazar", f"reject:{task_id}"),
        InlineButton("📝 Modificar", f"modify:{task_id}"),
    )
    return description, keyboard.to_markup()

# Al procesar callbacks
def process_callback(self, callback_id: str, callback_data: str, message_id: int):
    """callback_id es el id real del callback_query de Telegram"""
    if ":" not in callback_data:
        # Callback de modelo u otro
        if callback_data.startswith("model:"):
            new_model = callback_data[6:]
            if self.agent:
                result = self.agent.switch_model(new_model)
                self.send_message(result)
            self.answer_callback(callback_id, "Modelo cambiado")
        return

    action, task_id = callback_data.split(":", 1)
    self.answer_callback(callback_id)  # siempre responder primero

    if task_id not in self.pending_tasks:
        self.send_message("⚠ Tarea expirada")
        return

    task = self.pending_tasks.pop(task_id)

    if action == "confirm":
        self.send_message("✅ Procesando...")
        if task.get("type") == "search" and self.agent:
            response = self.agent.chat(task["query"])
            self.send_message(response)
        else:
            self.send_message("✅ Tarea completada")

    elif action == "reject":
        self.send_message("❌ Tarea rechazada")

    elif action == "modify":
        self.pending_tasks[task_id] = task  # devolver a la cola
        self.send_message("📝 Envía el texto modificado:")

# En el loop principal, pasar el callback_id correcto:
callback = update.get("callback_query")
if callback:
    cb_data = callback.get("data", "")
    cb_id = callback.get("id", "")           # ← id real del callback_query
    msg_id = callback.get("message", {}).get("message_id", 0)
    self.process_callback(cb_id, cb_data, msg_id)  # ← pasar cb_id, no reconstruirlo
    continue
```

### Fix secundario: web search funcional

DuckDuckGo no tiene API JSON pública en esa URL. Usar la API Instant Answer que sí funciona, o simplemente generar un link de búsqueda y pasar el contexto al LLM:

```python
def web_search(self, query: str) -> str:
    """Búsqueda via DuckDuckGo Instant Answer API"""
    try:
        from urllib.parse import quote_plus
        encoded = quote_plus(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        req = Request(url, headers={"User-Agent": "Ever-1-Agent/1.0"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        abstract = data.get("AbstractText", "")
        if abstract:
            results.append(f"📋 {abstract[:400]}")

        for item in data.get("RelatedTopics", [])[:4]:
            if isinstance(item, dict) and item.get("Text"):
                text = item["Text"][:120]
                url_item = item.get("FirstURL", "")
                results.append(f"• {text}\n  {url_item}")

        if not results:
            results.append(f"🔗 Sin resultados directos. [Buscar en Google](https://google.com/search?q={encoded})")

        return "\n\n".join(results)
    except Exception as e:
        return f"Error de búsqueda: {str(e)}"
```

---

## BUG 7 — `config.py`: Colisión de nombres de modelos

### Problema

```python
model_name = model_id.split("/")[-1][:20]
```

OpenRouter devuelve IDs como `openai/gpt-4o-2024-11-20` y `openai/gpt-4o-2024-08-06`. Ambos se truncan a `gpt-4o-2024-08-06` o similar. Si la parte final es idéntica hasta el carácter 20, el segundo modelo sobreescribe al primero en el diccionario. El usuario ve menos modelos de los que existen.

### Fix

```python
# Usar el ID completo como clave del dict, mostrar nombre limpio aparte
models[model_id] = {
    "id": model_id,
    "name": model_id.split("/")[-1],          # nombre completo sin truncar
    "display": model_id.split("/")[-1][:30],  # para mostrar en UI
    "price_input": price_in,
    "price_output": price_out,
    "free": is_free,
    "provider": provider,
    "vision": supports_vision,
}
```

Y actualizar `switch_model` en `client.py` para buscar por ID parcial si no hay match exacto:

```python
def switch_model(self, model_key: str) -> str:
    models = get_available_models(self.api_key)
    
    # Buscar coincidencia exacta primero
    if model_key in models:
        match = models[model_key]
    else:
        # Buscar coincidencia parcial por nombre
        matches = [(k, v) for k, v in models.items() if model_key.lower() in k.lower()]
        if not matches:
            return f"❌ Modelo no encontrado: {model_key}"
        match = matches[0][1]
        model_key = matches[0][0]
    
    self.config["model"] = model_key
    self.config["model_id"] = match.get("id", model_key)
    save_config(self.config)
    self.model_key = model_key
    self.model_id = match.get("id", model_key)
    self.tokens.set_prices(match.get("price_input", 0), match.get("price_output", 0))
    return f"✅ Modelo: {match.get('name', model_key)}"
```

---

## Orden de Aplicación de Fixes

Aplicar en este orden exacto para no romper dependencias entre archivos:

```
1. requirements.txt    → eliminar readline, openai, rich, python-dotenv
2. tools.py            → normalizar clave "output" en todos los métodos
3. config.py           → fix colisión de nombres de modelos
4. client.py           → fix streaming fallback + _record_response
5. main.py             → fix routing de /exec /read /ls /write /vision /speak
6. telegram_bot.py     → fix callback parsing + web search
7. install.sh          → reemplazar completamente con versión Termux-compatible
```

---

## Checklist de Verificación Post-Fix

Ejecutar estos comandos en Termux para verificar que todo funciona:

```bash
# 1. Verificar que el agente arranca
cd ~/.ever1-agent && python3 -c "from config import load_config; print('config OK')"
cd ~/.ever1-agent && python3 -c "from client import Ever1Agent; print('client OK')"
cd ~/.ever1-agent && python3 -c "from tools import ToolExecutor; t = ToolExecutor(); print(t.list_files('.'))"

# 2. Verificar comandos de herramientas
python3 -c "
import sys; sys.path.insert(0, '$HOME/.ever1-agent')
from tools import ToolExecutor
t = ToolExecutor()
r = t.read_file('$HOME/.ever1-agent/config.json')
assert r['success'] and 'output' in r and r['output'], f'FAIL: {r}'
print('read_file: OK')

r = t.list_files('$HOME/.ever1-agent')
assert r['success'] and 'output' in r, f'FAIL: {r}'
print('list_files: OK')
"

# 3. Test de chat real (requiere API key configurada)
cd ~/.ever1-agent && python3 -c "
from client import Ever1Agent
a = Ever1Agent()
r = a.chat('Di exactamente: TEST_OK')
print('chat:', r[:50])
"
```

---

## Lo que le falta para ser una herramienta personal sólida

Estos son los gaps que existen **después de aplicar todos los fixes** para uso personal confiable:

**Memoria persistente real** — El sistema de `learnings.json` guarda entradas pero no hace RAG ni búsqueda semántica. El agente no recuerda conversaciones pasadas más allá del `max_history` en RAM. Para uso personal real necesitas un vector store ligero como ChromaDB o simplemente SQLite con búsqueda de texto en el historial.

**Manejo de errores de red** — En Cuba / redes lentas, los timeouts de 120s del streaming se cuelgan silenciosamente. Necesita retry con backoff exponencial y mensajes de progreso visibles.

**Seguridad de `execute_code`** — Actualmente ejecuta código Python/Bash sin ningún sandbox. Para uso personal esto es aceptable, pero para producción es un vector de inyección si el LLM devuelve código malicioso.

**Validación de configuración al arranque** — Si `config.json` tiene una API key inválida, el agente arranca y solo falla en el primer chat. Debe validar la key al inicio con una llamada liviana.

---

## Lo que le falta para ser SaaS / AaaS global

Esto es lo que hay que construir **de cero** — no son fixes, son componentes nuevos:

### Infraestructura multiusuario

El agente actual está diseñado para **un solo usuario**. Todos los paths son `~/.ever1-agent/`. Para múltiples usuarios necesitas:

- Base de datos por usuario (PostgreSQL o MongoDB)
- Aislamiento de conversaciones: `conversations/{user_id}/`
- Aislamiento de configuración: cada usuario tiene su modelo, temperatura, API key o créditos propios
- Rate limiting por usuario

### Sistema de autenticación y API keys propias

Actualmente no existe ningún sistema de auth. Para AaaS necesitas:

- Registro de usuarios con hash de password (bcrypt)
- Generación de API keys propias estilo `everai_sk_XXXX`
- Middleware de validación de key en cada request
- Tabla de créditos/quotas por usuario

### Backend HTTP

El agente es una CLI. Para ofrecer servicio vía API necesitas un servidor:

```
FastAPI (Python) o Express (Node.js)
├── POST /v1/chat          → proxy al LLM con tracking de uso
├── POST /v1/execute       → ejecutar herramientas (con sandbox)
├── GET  /v1/models        → modelos disponibles según plan del usuario
├── POST /auth/register    → registro
├── POST /auth/login       → login + JWT
└── GET  /billing/usage    → uso del mes actual
```

### Sistema de billing

Para monetizar necesitas:
- Contador de tokens por usuario en DB
- Planes (Free/Pro/Business) con límites distintos
- Integración de pagos: OxaPay (crypto, ya lo conoces de Bets Pro), Stripe via terceros
- Facturación automática mensual o por créditos prepagados

### Sandboxing de ejecución de código

La herramienta `/exec` en producción multiusuario es **inaceptable sin sandbox**. Opciones:
- Docker por usuario (caro en VPS pequeño)
- `restrictedpython` para Python limitado
- E2B (sandbox cloud, tiene free tier) — la opción más práctica para MVP

### Panel web de administración

Hoy mismo puedes reutilizar lo que ya sabes de Next.js + MongoDB de Bets Pro:
- Dashboard de usuarios activos, tokens consumidos, revenue
- Gestión de planes y créditos manual (para beta)
- Logs de uso por usuario

### Telegram como canal de distribución

El `telegram_bot.py` ya existe pero es owner-only. Para escalar:
- Un bot multiusuario donde cada usuario se registra con `/start`
- Vinculación Telegram ↔ cuenta en el backend
- Envío de respuestas via webhook (no polling) para VPS

---

## ¿Sirve esto para crear un modelo agéntico y tu startup AaaS?

**La respuesta honesta tiene dos partes.**

### Como base de código para uso personal y MVP: Sí, con los fixes aplicados

Lo que tienes es un **agente CLI funcional** con arquitectura correcta (config / client / tools / telegram separados), soporte para múltiples proveedores LLM, herramientas de sistema básicas y un canal Telegram. Después de los fixes documentados arriba, este agente puede correr estable en tu Termux para uso diario.

Para llegar a un MVP de AaaS con primeros usuarios pagos, la ruta es:
1. Aplicar todos los fixes (1-2 días)
2. Agregar FastAPI encima del `Ever1Agent` como servidor HTTP (2-3 días)
3. Agregar auth básica con JWT y tabla de usuarios en MongoDB (1-2 días)
4. Desplegar en tu VPS con PM2 o Docker (1 día)
5. Conectar OxaPay para pagos crypto (ya lo tienes resuelto de Bets Pro)

Con 2 semanas de trabajo enfocado llegas a un SaaS funcional con los primeros usuarios.

### Como "modelo agéntico" propio en el sentido de IA: No, y es importante entenderlo

El agente **no es un modelo de IA**. Es un **cliente de LLM** con herramientas. El "aprendizaje" que implementa (`learnings.json`) es solo un log de texto que se inyecta en el system prompt. No hay entrenamiento, no hay fine-tuning, no hay embeddings, no hay nada que modifique los pesos de ningún modelo.

Lo que tienes es lo mismo que Claude Code, ChatGPT con plugins, o cualquier agente ReAct: un LLM externo (Minimax, GPT-4o, Claude) + un loop que le da herramientas + un prompt de sistema. Eso está perfectamente bien para un negocio AaaS — no necesitas un modelo propio para tener un producto rentable.

Si el objetivo es diferenciarte con un modelo ajustado a tu dominio (usuarios cubanos, transfers, español rioplatense/cubano), la ruta real sería fine-tuning de Llama 3.1 en Hugging Face con datos propios, lo que requiere GPU y datos etiquetados. Eso es una versión 2.0 del producto.

**El camino más rentable para tu contexto**: construir la capa de producto (auth, billing, UX, canal Telegram/web) sobre modelos gratuitos de OpenRouter es el diferenciador real, no el modelo en sí. Tus ventajas competitivas son el mercado hispano/cubano que conoces, el canal de distribución Telegram que ya tienes, y la capacidad de integrar pagos crypto que la mayoría de los competidores no tiene para ese mercado.
