# J.A.R.V.I.S. — Multi-LLM AI Ecosystem

> **Just A Rather Very Intelligent System** — Asistente de IA personal con enrutamiento multi-LLM, sistema de personas, RAG, y operación 24/7 en WSL2.

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-green)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST+WS-red)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 1. Planteamiento del Problema

Los asistentes de IA actuales presentan tres limitaciones críticas para uso personal avanzado:

1. **Dependencia de un único proveedor LLM** — si el servicio cae, el asistente deja de funcionar
2. **Falta de especialización contextual** — un modelo genérico no es óptimo para programar, investigar, planificar o crear simultáneamente
3. **Sin memoria persistente ni conocimiento personal** — cada sesión comienza desde cero sin contexto acumulado

**¿Cómo construir un asistente de IA personal que sea resiliente, especializable, y con memoria persistente, ejecutándose 24/7 en hardware de consumidor?**

---

## 2. Objetivo

Desarrollar un ecosistema de IA personal (J.A.R.V.I.S.) que integre:

- **Enrutamiento multi-LLM con failover automático**: Ollama (local) → Groq → Anthropic → OpenAI
- **Sistema de personas especializadas** con switching en tiempo real (5 modos)
- **Clasificación de intención** en 17 categorías para enrutar herramientas adecuadas
- **RAG sobre base de conocimiento personal** (Obsidian vault + ChromaDB)
- **Memoria persistente** episódica y semántica (SQLite)
- **Operación 24/7** en WSL2 con systemd sin PC externo

---

## 3. Metodología

### Flujo de Arquitectura

```
+-------------------------------------------------------------------+
|                    ENTRADA DEL USUARIO                            |
|              (Web UI / Telegram / Voice / API)                    |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                    INTENT ROUTER (17 tipos)                       |
|   SEARCH, CODE, WEATHER, PLAN, DEBUG, REMEMBER...                |
|   Selecciona persona sugerida + herramientas activas              |
+----------+-----------------------------+--------------------------+
           |                             |
           v                             v
+----------------------+    +----------------------------------+
|   PERSONA MANAGER    |    |         MEMORY LAYER            |
|  jarvis / coder /    |    |  SQLite: episodica + semantica  |
|  researcher /        |    |  RAG: ChromaDB + TF-IDF        |
|  creative / planner  |    |  Top-5 facts en system prompt  |
+----------+-----------+    +----------------+-----------------+
           |                                 |
           +------------------+--------------+
                              |
                              v
+-------------------------------------------------------------------+
|               LANGGRAPH REACT AGENT LOOP                          |
|                                                                   |
|   [REASON] ---> [ACT] ---> [OBSERVE]                            |
|   (LLM plan)   (tool use)  (tool result)                        |
|       ^                         |                                 |
|       +-------------------------+                                 |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                    MULTI-LLM ROUTER (failover)                    |
|                                                                   |
|   Ollama (local) --> Groq --> Anthropic --> OpenAI               |
|   qwen2.5/llama3   llama3    claude         gpt-4               |
|                                                                   |
|   Auto-failover: modelo primario falla -> siguiente en chain     |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                      HERRAMIENTAS (9)                             |
|                                                                   |
|  get_weather | web_search | scrape_url | calculate               |
|  get_system_info | remember_fact | recall_fact                   |
|  search_memory | get_current_datetime                            |
+-------------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                    SALIDA AL USUARIO                              |
|         (Streaming WebSocket / REST / Telegram / TTS)            |
+-------------------------------------------------------------------+
```

### Stack Tecnologico

| Capa | Tecnologia | Rol |
|------|-----------|-----|
| Orquestacion | LangGraph ReAct | Bucle Reason-Act-Observe |
| Framework LLM | LangChain | Tool binding, message types |
| LLMs locales | Ollama (qwen2.5, llama3.2) | GPU GTX 1650 4GB, gratis |
| LLMs cloud | Groq, Anthropic, OpenAI | Failover, alta calidad |
| API | FastAPI + WebSockets | REST + streaming tiempo real |
| Memoria | SQLite (aiosqlite) | Episodica + semantica |
| RAG | ChromaDB + TF-IDF | Base de conocimiento personal |
| Voz | openWakeWord + Whisper | Wake word + STT |
| Bot | python-telegram-bot | Canal Telegram |
| Infraestructura | WSL2 + systemd | 24/7 sin PC externo |

### Temas de IA Integrados

1. **Agentes ReAct** (Reason-Act-Observe) — LangGraph multi-step planning
2. **RAG** (Retrieval-Augmented Generation) — ChromaDB + TF-IDF sobre vault personal
3. **Multi-LLM Routing** — Failover automatico entre modelos
4. **NLP Intent Classification** — 17 tipos de intencion, keyword-based
5. **Memoria de Agentes** — Episodica + semantica + checkpointing LangGraph

---

## 4. Desarrollo

### Estructura del Proyecto

```
jarvis_files/
+-- jarvis/
|   +-- agent/
|   |   +-- core.py          # JarvisAgent: LangGraph ReAct loop
|   |   +-- llm_router.py    # Multi-LLM failover chain
|   |   +-- memory.py        # SQLite: episodica + semantica
|   |   +-- tools.py         # 9 LangChain tools
|   |   +-- personas.py      # 5 personas especializadas
|   |   +-- router.py        # 17-intent classifier + channel config
|   |   +-- rag.py           # ChromaDB + TF-IDF RAG
|   +-- integrations/
|   |   +-- telegram_bot.py  # Bot Telegram
|   +-- voice/
|   |   +-- wake_word.py     # openWakeWord + Whisper STT
|   +-- main.py              # FastAPI app + WebSocket
|   +-- config.py            # Configuracion centralizada
+-- scripts/
|   +-- setup_wsl.sh         # Setup automatizado WSL2
|   +-- jarvis.service       # Systemd unit 24/7
+-- run.py                   # Entry point
+-- requirements.txt
+-- env.example
```

### Componentes Clave

#### Multi-LLM Router (failover automatico)
```python
# Ollama local -> Groq -> Anthropic -> OpenAI
llm = get_langchain_llm()  # Auto-selects best available
# Si Ollama cae: automaticamente usa Groq API
# Si Groq rate-limit: usa Anthropic Claude
```

#### Sistema de Personas (runtime switching)
```
/persona coder    -> JARVIS-DEV modo programador
/persona research -> JARVIS-RESEARCH investigacion profunda
/persona creative -> JARVIS-CREATIVE brainstorming
/persona planner  -> JARVIS-PLAN gestion de proyectos
```

#### Intent Router (17 tipos)
```python
route = jarvis_router.classify_intent(message)
# WEATHER, CALCULATE, SEARCH, CODE, DEBUG, REMEMBER...
# Selecciona herramientas especificas por intencion
```

---

## 5. Resultados

### Funcionalidades Implementadas

| Funcionalidad | Estado | Proveedor |
|---------------|--------|-----------|
| Multi-LLM failover (4 proveedores) | OK | Ollama/Groq/Anthropic/OpenAI |
| LangGraph ReAct agent | OK | LangGraph |
| 5 personas especializadas | OK | Sistema propio |
| 17 tipos de intencion | OK | Sistema propio |
| 9 herramientas LangChain | OK | LangChain tools |
| Memoria SQLite (episodica + semantica) | OK | aiosqlite |
| RAG ChromaDB | OK | ChromaDB + TF-IDF |
| FastAPI REST + WebSocket streaming | OK | FastAPI |
| Bot Telegram | OK | python-telegram-bot |
| Wake word detection | OK | openWakeWord |
| WSL2 24/7 systemd | OK | systemd |
| Web UI chat | OK | HTML/JS vanilla |

### Comparacion de Arquitecturas

| Enfoque | Single LLM | Multi-LLM basico | J.A.R.V.I.S. (este proyecto) |
|---------|-----------|-----------------|-------------------------------|
| Resiliencia | Punto unico de falla | Failover basico | 4-provider chain automatico |
| Especializacion | Generico | Prompts manuales | 5 personas + routing por intencion |
| Memoria | Por sesion | In-memory | SQLite + RAG sobre vault personal |
| Costo local | Siempre cloud | Parcialmente local | Ollama-first, cloud como fallback |
| Canales | Uno | Manual | Web+Telegram+Voice+API |
| 24/7 | Manual | Manual | systemd autostart en WSL2 |

### API Endpoints

```
GET  /health           -> estado del sistema + proveedor activo
GET  /provider         -> info del LLM activo
POST /chat             -> chat REST (non-streaming)
WS   /ws/{session_id}  -> WebSocket streaming
GET  /history/{id}     -> historial de sesion
GET  /personas         -> lista de personas disponibles
POST /persona/{name}   -> cambiar persona activa
GET  /rebuild          -> forzar re-deteccion de proveedor
```

---

## 6. Discusion

### Logros Principales

1. **Resiliencia demostrada**: el failover automatico Ollama-Groq-Anthropic-OpenAI elimina el punto unico de falla. Durante pruebas, cuando Ollama no responde, el cambio a Groq ocurre en menos de 2 segundos sin intervencion del usuario.

2. **Especializacion efectiva**: las 5 personas con prompts de sistema distintos mejoran la calidad de respuesta en dominios especificos. JARVIS-DEV produce codigo mas limpio con manejo de errores; JARVIS-RESEARCH cita fuentes y estructura hallazgos.

3. **Economia de hardware**: el modelo qwen2.5:7b corre en GTX 1650 4GB (4GB VRAM) con ~1.5 tokens/segundo. Para respuestas rapidas, Groq (gratuito, 6K tok/min) es el failover ideal.

4. **Arquitectura extensible**: agregar un nuevo proveedor LLM requiere solo un bloque en `llm_router.py`. Agregar herramienta: decorar con `@tool` y agregar a `JARVIS_TOOLS`. Agregar persona: una entrada al dict `PERSONAS`.

### Limitaciones

- **Latencia local**: qwen2.5:7b en GTX 1650 produce ~1.5 tok/s; respuestas largas pueden tomar 30-60 segundos
- **RAG escalabilidad**: TF-IDF fallback funciona pero pierde calidad semantica; ChromaDB requiere sentence-transformers (~500MB extra)
- **Telegram en WSL2**: funciona en desarrollo; produccion requiere webhook o polling como servicio separado

### Trabajo Futuro

- Sub-agentes especializados por dominio (OpenClaw pattern completo)
- Fine-tuning de modelo local con datos propios del usuario
- Interfaz web avanzada con React + historial visual
- Integracion con calendario, correo, y servicios de productividad
- Sintesis de voz (TTS) para respuestas habladas

---

## Instalacion Rapida

```bash
# 1. Clonar repositorio
git clone https://github.com/Pacha-e/Multi-LLM-Jarvis-Ecosistem.git
cd Multi-LLM-Jarvis-Ecosistem

# 2. Entorno virtual
python -m venv .venv
source .venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Configuracion
cp env.example jarvis.env
# Editar jarvis.env con tus API keys

# 5. Ollama (opcional, LLM local)
# Ver https://ollama.ai/download
ollama pull qwen2.5:7b

# 6. Ejecutar
python run.py
# Abrir http://localhost:8000
```

### Variables de Entorno

```bash
# jarvis.env
GROQ_API_KEY=gsk_...          # Gratis en console.groq.com
ANTHROPIC_API_KEY=sk-ant-...  # Opcional
OPENAI_API_KEY=sk-...         # Opcional (ultimo failover)
WEATHER_API_KEY=...           # OpenWeatherMap (gratis)
```

### WSL2 24/7

```bash
# En WSL2:
sudo cp scripts/jarvis.service /etc/systemd/system/
sudo systemctl enable jarvis
sudo systemctl start jarvis
# JARVIS arranca automaticamente con Windows
```

---

## Licencia

MIT

---

*Desarrollado por Emmanuel Hernandez — EAFIT 2026-1*
