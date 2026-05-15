# Informe de Proyecto: J.A.R.V.I.S. — Ecosistema de IA Multi-LLM

**Asignatura:** Introduccion a la Inteligencia Artificial
**Universidad:** Universidad EAFIT
**Semestre:** 2026-1
**Autor:** Emmanuel Hernandez
**Repositorio:** https://github.com/Pacha-e/Multi-LLM-Jarvis-Ecosistem

---

## 1. Planteamiento del Problema (10%)

### Contexto

El auge de los modelos de lenguaje grande (LLMs) ha generado una proliferacion de asistentes de IA de proposito general: ChatGPT, Claude, Gemini, entre otros. Sin embargo, su uso practico como asistentes personales **24/7** presenta limitaciones estructurales:

**Problema 1: Dependencia de un proveedor unico**
Si el servicio del proveedor presenta caidas, interrupciones por mantenimiento, o cambios en precios/politicas, el usuario queda sin asistente. No existe un mecanismo de fallback automatico.

**Problema 2: Falta de especializacion contextual**
Un modelo generico produce respuestas de calidad media en todos los dominios. Un programador necesita respuestas con codigo funcional, tipado estricto y manejo de errores; un investigador necesita sintesis de fuentes multiples con citas; un planificador necesita descomposicion de tareas con dependencias y estimaciones. Un unico sistema de prompts no puede optimizar todos estos contextos simultaneamente.

**Problema 3: Amnesia entre sesiones**
Los asistentes comerciales no recuerdan conversaciones pasadas entre sesiones (salvo con planes de pago). No tienen acceso a la base de conocimiento personal del usuario (notas, proyectos, preferencias acumuladas durante meses).

**Pregunta de investigacion:**
*Como construir un asistente de IA personal que sea (a) resiliente ante fallos de proveedores, (b) especializable por dominio en tiempo de ejecucion, y (c) con memoria persistente y RAG sobre conocimiento personal, operando 24/7 en hardware de consumidor (GTX 1650 4GB)?*

### Justificacion

La combinacion de modelos locales (Ollama) con APIs cloud y un orquestador de agentes (LangGraph) permite abordar los tres problemas simultaneamente. El costo operativo puede minimizarse priorizando inferencia local y usando APIs cloud como fallback.

---

## 2. Objetivo (10%)

### Objetivo General

Desarrollar J.A.R.V.I.S. (Just A Rather Very Intelligent System): un ecosistema de IA personal que integre multiples proveedores LLM con failover automatico, un sistema de personas especializadas, clasificacion de intenciones, RAG sobre base de conocimiento personal, y operacion continua en WSL2.

### Objetivos Especificos

1. Implementar un enrutador multi-LLM con cadena de failover: Ollama → Groq → Anthropic → OpenAI
2. Disenar e implementar un sistema de 5 personas especializadas con switching en tiempo real
3. Construir un clasificador de intenciones de 17 tipos para enrutamiento de herramientas
4. Integrar RAG (ChromaDB + TF-IDF) sobre vault de Obsidian como base de conocimiento personal
5. Exponer el sistema mediante FastAPI con WebSocket streaming y bot de Telegram
6. Configurar operacion 24/7 en WSL2 mediante systemd

---

## 3. Metodologia (15% — incluye diagrama de flujo obligatorio)

### 3.1 Enfoque Metodologico

El proyecto sigue un enfoque de **desarrollo iterativo** con las siguientes fases:

1. **Fase de investigacion**: analisis de arquitecturas de agentes ReAct, patrones multi-LLM, y frameworks disponibles (LangChain, LangGraph, LlamaIndex)
2. **Fase de diseno**: definicion de componentes, interfaces, y contratos entre modulos
3. **Fase de implementacion**: desarrollo incremental, modulo por modulo
4. **Fase de integracion**: ensamblaje de componentes y pruebas de integracion
5. **Fase de despliegue**: configuracion de WSL2 systemd para operacion 24/7

### 3.2 Diagrama de Flujo del Sistema

```
+-------------------------------------------------------------------+
|                    ENTRADA DEL USUARIO                            |
|              (Web UI / Telegram / Voice / API REST)               |
+---------------------------+---------------------------------------+
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
+---------------------+           +---------------------+
| /persona <nombre>   |           |  Mensaje normal     |
| -> Cambio de persona|           |  -> Procesamiento   |
| -> Respuesta        |           |     normal          |
| inmediata           |           +----------+----------+
+---------------------+                      |
                                             v
                            +-----------------------------------+
                            |         INTENT ROUTER             |
                            |   classify_intent(message)        |
                            |                                   |
                            |  WEATHER | CODE | SEARCH |       |
                            |  DEBUG | PLAN | REMEMBER...      |
                            |   (17 tipos, keyword-based)      |
                            +----------------+------------------+
                                             |
                     +-----------------------+-----------------------+
                     |                       |                       |
                     v                       v                       v
           +-----------------+   +-------------------+   +------------------+
           | PERSONA MANAGER |   |   MEMORY LAYER    |   |  RAG RETRIEVAL   |
           |                 |   |                   |   |                  |
           | current_persona |   | SQLite episodic   |   | ChromaDB search  |
           | -> system_prompt|   | SQLite semantic   |   | TF-IDF fallback  |
           | (5 modos)       |   | Top-5 facts       |   | Obsidian vault   |
           +--------+--------+   +---------+---------+   +--------+---------+
                    |                      |                       |
                    +----------------------+-----------------------+
                                           |
                                           v
                            +-----------------------------------+
                            |    SYSTEM PROMPT CONSTRUCTION     |
                            |                                   |
                            |  persona.system_prompt            |
                            |  + memory_digest (top-5 facts)   |
                            |  + rag_context (relevant notes)  |
                            |  + PLANNER_PROMPT                |
                            +----------------+------------------+
                                             |
                                             v
+-------------------------------------------------------------------+
|               LANGGRAPH REACT AGENT LOOP                          |
|                                                                   |
|   +---------+     +---------+     +------------------------+     |
|   | REASON  +---->+   ACT   +---->+       OBSERVE          |     |
|   | LLM     |     | invoke  |     | tool result -> context |     |
|   | planea  |     | tool    |     | -> siguiente iteracion |     |
|   +---------+     +---------+     +-----------+------------+     |
|        ^                                       |                  |
|        +---------------------------------------+                  |
|                  (loop hasta respuesta final)                     |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                    MULTI-LLM ROUTER                               |
|                                                                   |
|   1. Ollama (local, GTX 1650) <- intento primario               |
|        |                                                          |
|        v (si falla: timeout/error)                               |
|   2. Groq API (gratuito, llama3-70b)                            |
|        |                                                          |
|        v (si falla: rate-limit)                                  |
|   3. Anthropic (claude-3-haiku)                                  |
|        |                                                          |
|        v (si falla)                                              |
|   4. OpenAI (gpt-4o-mini) <- ultimo recurso                     |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                   HERRAMIENTAS DISPONIBLES (9)                    |
|                                                                   |
|  get_weather(city)           -> OpenWeatherMap API               |
|  web_search(query)           -> DuckDuckGo scraping              |
|  scrape_url(url)             -> BeautifulSoup4                   |
|  calculate(expression)       -> Python eval seguro               |
|  get_system_info()           -> psutil (CPU/RAM/disco)           |
|  remember_fact(key, value)   -> SQLite write                     |
|  recall_fact(key)            -> SQLite read                      |
|  search_memory(query)        -> SQLite FTS                       |
|  get_current_datetime()      -> datetime.now()                   |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|              POST-PROCESAMIENTO (fix_tool_call_response)          |
|   Detecta si modelo devolvio JSON en lugar de texto natural      |
|   Ejecuta herramienta y devuelve resultado como texto            |
+---------------------------+---------------------------------------+
                            |
                            v
+-------------------------------------------------------------------+
|                    SALIDA AL USUARIO                              |
|   WebSocket streaming (web) | REST (API) | Telegram | TTS (voz) |
+-------------------------------------------------------------------+
```

### 3.3 Patron de Agente ReAct

El patron ReAct (Reason-Act-Observe) es central en la arquitectura:

1. **Reason**: el LLM analiza el mensaje y decide si necesita usar herramientas
2. **Act**: invoca la herramienta seleccionada con los argumentos apropiados
3. **Observe**: recibe el resultado de la herramienta y lo incorpora al contexto
4. **Loop**: repite hasta tener suficiente informacion para responder

LangGraph implementa este loop como un grafo de estados con `create_react_agent()`.

### 3.4 Temas de IA Integrados

| Tema | Implementacion | Modulo |
|------|---------------|--------|
| Agentes ReAct | LangGraph create_react_agent | core.py |
| RAG | ChromaDB + TF-IDF + Obsidian | rag.py |
| Multi-LLM Routing | Failover chain 4 proveedores | llm_router.py |
| Intent Classification | Keyword-based 17 tipos | router.py |
| Memoria de agentes | SQLite episodica + semantica | memory.py |
| NLP/Prompting | 5 system prompts especializados | personas.py |

---

## 4. Desarrollo (25%)

### 4.1 Modulo: Multi-LLM Router (`jarvis/agent/llm_router.py`)

El enrutador intenta proveedores en orden de preferencia:
- Ollama (local, sin costo, privado) como primera opcion
- Groq (gratuito hasta 6K tok/min) como primer fallback
- Anthropic y OpenAI como respaldo final

Cuando un proveedor falla (timeout, error de conexion, rate limit), el siguiente es intentado automaticamente en el mismo ciclo de solicitud.

### 4.2 Modulo: LangGraph ReAct Agent (`jarvis/agent/core.py`)

`JarvisAgent` encapsula:
- `_build_agent()`: crea el agente ReAct con el LLM activo y las 9 herramientas
- `_build_system_messages()`: construye el prompt de sistema con persona + memoria + RAG
- `chat()`: invocacion sincrona con persona detection, intent routing, y fallback
- `chat_stream()`: streaming asicrono via WebSocket
- `_fix_tool_call_response()`: post-procesamiento para modelos que devuelven JSON crudo

### 4.3 Modulo: Sistema de Personas (`jarvis/agent/personas.py`)

5 personas con system prompts especializados:

| Persona | Modo | Especializacion |
|---------|------|----------------|
| jarvis | Default | Asistente general, formal, eficiente |
| coder | /persona coder | Python/TS/Rust, codigo limpio, debug |
| researcher | /persona researcher | Busqueda multi-fuente, sintesis, citas |
| creative | /persona creative | Brainstorming, escritura, ideas |
| planner | /persona planner | Proyectos, tareas, metodologias agiles |

El switching ocurre en tiempo real sin reiniciar el agente. El system prompt cambia dinamicamente en cada solicitud.

### 4.4 Modulo: Intent Router (`jarvis/agent/router.py`)

Clasificador keyword-based de 17 tipos de intencion con configuracion por canal:

```
Canal  | max_tokens | streaming | tools
-------|-----------|-----------|------
web    | 2048      | si        | si
telegram| 1024     | no        | si
voice  | 512       | no        | no
api    | 4096      | si        | si
```

### 4.5 Modulo: Herramientas (`jarvis/agent/tools.py`)

9 herramientas LangChain decoradas con `@tool`:

1. `get_weather`: temperatura, descripcion, humedad via OpenWeatherMap
2. `web_search`: DuckDuckGo HTML scraping sin API key
3. `scrape_url`: extraccion de contenido web con BeautifulSoup4
4. `calculate`: evaluador de expresiones matematicas con whitelist de operadores
5. `get_system_info`: metricas de CPU, RAM, disco via psutil
6. `remember_fact` / `recall_fact` / `search_memory`: CRUD de memoria semantica SQLite
7. `get_current_datetime`: fecha y hora actual formateada

### 4.6 Modulo: RAG (`jarvis/agent/rag.py`)

Dos implementaciones con fallback:
1. **ChromaDB**: busqueda vectorial semantica sobre documentos del vault de Obsidian
2. **TF-IDF** (fallback): busqueda lexica cuando ChromaDB/sentence-transformers no estan disponibles

El contexto recuperado se inyecta automaticamente en el system prompt antes de cada solicitud.

### 4.7 Integraciones

- **FastAPI** (`jarvis/main.py`): REST API + WebSocket para streaming
- **Telegram Bot** (`jarvis/integrations/telegram_bot.py`): canal de mensajeria
- **Wake Word** (`jarvis/voice/wake_word.py`): deteccion de "Hey JARVIS" + Whisper STT

### 4.8 Infraestructura WSL2 24/7

`scripts/jarvis.service` es un unit file de systemd que:
- Inicia automaticamente con WSL2
- Reinicia en caso de crash (RestartSec=10)
- Lee variables de entorno desde `jarvis.env`
- Redirige logs a journald

---

## 5. Resultados (20%)

### 5.1 Sistema Funcional

El ecosistema J.A.R.V.I.S. opera completamente en el hardware objetivo (GTX 1650 4GB, Win11+WSL2) con todas las funcionalidades implementadas.

### 5.2 Metricas de Rendimiento

| Metrica | Valor | Condicion |
|---------|-------|-----------|
| Latencia Ollama (qwen2.5:7b) | ~1.5 tok/s | GTX 1650, 4GB VRAM |
| Latencia Groq (llama3-70b) | ~180 tok/s | API gratuita |
| Tiempo failover Ollama→Groq | <2 segundos | Cuando Ollama no responde |
| Precision intent router | ~85% en pruebas manuales | 17 tipos |
| Herramientas funcionales | 9/9 | En condiciones normales |
| Personas implementadas | 5/5 | Switching en tiempo real |
| Canales soportados | 4 | Web, Telegram, Voice, API |

### 5.3 Casos de Uso Demostrados

1. **Consulta con herramientas**: "Cual es el clima en Medellin?" → intent=WEATHER → get_weather tool → respuesta en lenguaje natural
2. **Programacion**: "/persona coder" + "Escribe un decorator de retry en Python" → JARVIS-DEV → codigo con manejo de errores
3. **Investigacion**: "Investiga sobre transformers en NLP" → intent=SEARCH → web_search → sintesis multi-fuente
4. **Memoria**: "Recuerda que mi proyecto favorito es JARVIS" → remember_fact → confirmacion → "Que proyectos tengo?" → recall automatico
5. **Failover**: Ollama offline → solicitud automaticamente procesada por Groq sin intervencion del usuario

### 5.4 Comparacion con Baselines

| Metrica | ChatGPT (web) | Ollama solo | J.A.R.V.I.S. |
|---------|--------------|-------------|---------------|
| Disponibilidad | Depende de OpenAI | Depende de GPU local | 4 proveedores en cadena |
| Costo mensual | $20+ (Plus) | $0 (local) | ~$0 (Groq gratuito + local) |
| Memoria entre sesiones | Solo con memoria activada | No | Si (SQLite + RAG) |
| Especializacion | Prompts manuales | Prompts manuales | 5 personas automaticas |
| Privacidad | Datos a OpenAI | Total (local) | Configurable por canal |
| Canales | 1 (web) | API local | 4 (web/telegram/voice/API) |

---

## 6. Discusion (15%)

### 6.1 Analisis de Resultados

**Exito del enfoque multi-LLM**: la cadena de failover funciona correctamente. El usuario experimenta transparencia total: si Ollama esta sobrecargado o apagado, la solicitud se procesa via Groq sin ninguna intervencion manual. Esto resuelve el problema 1 (dependencia de proveedor unico) de forma efectiva.

**Efectividad de las personas**: los diferentes system prompts producen respuestas cualitativamente distintas. JARVIS-DEV incluye manejo de errores y typing en sus fragmentos de codigo; JARVIS-RESEARCH estructura sus respuestas con contexto → hallazgos → conclusiones; JARVIS-PLAN genera listas accionables con estimaciones de tiempo. El problema 2 (falta de especializacion) esta resuelto para los dominios implementados.

**Memoria y RAG**: la memoria SQLite persiste entre sesiones correctamente. El RAG sobre el vault de Obsidian inyecta contexto personal relevante cuando existe. Sin embargo, la calidad del RAG depende de la disponibilidad de sentence-transformers; el fallback TF-IDF funciona pero tiene menor precision semantica.

### 6.2 Limitaciones Identificadas

**Latencia del modelo local**: qwen2.5:7b produce ~1.5 tok/s en GTX 1650. Para solicitudes que requieren respuestas largas (>200 tokens), el tiempo de espera puede superar 30 segundos. La solucion actual es usar Groq como failover para estas solicitudes, pero requiere conexion a internet.

**Escalabilidad del RAG**: el vault de Obsidian puede crecer indefinidamente. La indexacion en ChromaDB es incremental pero la busqueda puede degradarse con cientos de miles de documentos sin particionamiento apropiado.

**Intent classification precision**: el clasificador keyword-based tiene falsos positivos/negativos cuando mensajes contienen palabras de multiples categorias. Un clasificador basado en embeddings o fine-tuning mejoraria la precision, a costo de mayor complejidad.

### 6.3 Contribuciones

1. **Patron de failover multi-LLM con LangChain**: implementacion practica y extensible del encadenamiento de proveedores con recuperacion automatica
2. **Sistema de personas como capa de prompting**: abstraccion que separa la logica de especializacion del codigo del agente
3. **Integracion RAG con vault personal**: pipeline completo desde documentos Obsidian hasta contexto en system prompt
4. **Configuracion WSL2 24/7**: servicio systemd probado para operacion continua en hardware de consumidor

### 6.4 Trabajo Futuro

1. **Sub-agentes especializados** (OpenClaw pattern): en lugar de cambiar prompts, instanciar agentes LangGraph separados por dominio con herramientas distintas
2. **Clasificador de intenciones basado en embeddings**: reemplazar keyword matching con modelo de clasificacion para mayor precision
3. **Fine-tuning del modelo local**: adaptar qwen2.5 con datos de conversaciones del usuario para respuestas mas personalizadas
4. **Interfaz React con historial visual**: visualizacion de herramientas usadas, personas activas, y metricas en tiempo real
5. **Integracion con productividad**: Google Calendar, Gmail, Notion para acciones sobre el entorno del usuario

---

## Anexo A: Instrucciones de Instalacion

Ver README.md en la raiz del repositorio para instrucciones detalladas.

## Anexo B: Variables de Entorno

```
GROQ_API_KEY          - API key de Groq (gratuita)
ANTHROPIC_API_KEY     - API key de Anthropic (opcional)
OPENAI_API_KEY        - API key de OpenAI (opcional)
WEATHER_API_KEY       - OpenWeatherMap API key (gratuita)
TELEGRAM_BOT_TOKEN    - Token del bot de Telegram (opcional)
RAG_ENABLED           - true/false (default: true)
OBSIDIAN_VAULT_PATH   - Ruta al vault de Obsidian
DB_PATH               - Ruta a la base de datos SQLite
```

## Anexo C: Referencias

1. Yao, S. et al. (2022). ReAct: Synergizing Reasoning and Acting in Language Models. arXiv:2210.03629
2. Lewis, P. et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020
3. LangGraph Documentation. https://langchain-ai.github.io/langgraph/
4. Ollama. https://ollama.ai
5. LangChain Tools Documentation. https://python.langchain.com/docs/concepts/tools/
