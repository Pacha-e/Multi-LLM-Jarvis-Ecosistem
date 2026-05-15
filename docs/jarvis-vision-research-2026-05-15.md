# Jarvis Vision Research - 2026-05-15

Objetivo: convertir el ecosistema actual en un Jarvis personal, barato de operar, potente cuando haga falta, con memoria persistente en Obsidian, orquestacion multi-LLM y capacidad real de actuar en navegador, archivos, voz y automatizaciones.

## Senales extraidas de los Reels

Extraccion realizada sin login: metadatos publicos del HTML de Instagram. No se obtuvo transcript real ni `video_url`; el HTML solo expone captions/engagement y flags internos. Para scraping completo se requiere actor gestionado, cookies de navegador o descarga + transcripcion local.

| Reel | Cuenta | Fecha | Senal util |
|---|---|---:|---|
| `DX-ogpKRVRc` | `everflw.email` | 2026-05-05 | Concepto J.A.R.V.I.S. vs F.R.I.D.A.Y.; contenido de asistente operativo con personalidad clara. |
| `DYM0Duvt4iP` | `lukebuildsai` | 2026-05-11 | "Jarvis" como producto con waitlist; enfoque aspiracional de asistente personal. |
| `DYPCGs0sFBv` | `proj.ectjarvis` | 2026-05-12 | Idea de Jarvis usando OpenClaw/OpenCove como orquestador y enlace facil de instalacion. |
| `DU3wC2vDPy_` | `programmersarealsohuman` | 2026-02-17 | Dolor real: instalar OpenClaw en VPS/24-7 puede ser complejo; conviene evitar sobreingenieria al inicio. |
| `DYDLxXBJwTd` | `wassimyounes_` | 2026-05-07 | Obsidian como memoria persistente para Claude Code, Codex y Gemini CLI; notas, indices, busqueda semantica y continuidad entre sesiones. |
| `DX3aKMgOfJi` | `soyenriquerocha` | 2026-05-02 | Mejorar navegador para Claude/CLI sin quemar tokens; usar browser automation persistente/token-efficient. |
| `DV9cPQuDIPp` | `proj.ectjarvis` | 2026-03-16 | Instalacion facil de Jarvis; menciona OpenCove como servicio externo con trial/subscripcion. Evaluar antes de depender de coste recurrente. |

## Investigacion externa relevante

### OpenClaw como control plane

- `openclaw/openclaw` define el patron central: Gateway local largo-vivo, WebSocket en `127.0.0.1:18789`, multi-canal, nodos, agentes, skills, cron, memoria y sandboxing.
- OpenClaw recomienda Windows via WSL2 para instalacion completa, pero el proyecto local ya demostro que tu entorno actual no tenia WSL instalado cuando Codex arranco. Decision pragmatica: fase 1 Windows-native; fase 2 WSL2 solo si OpenClaw lo exige.
- El Gateway debe ser el orquestador operacional; el `core/` Python actual debe quedar como laboratorio de RAG/tools/voice, no como runtime principal hasta que madure.

### 24/7 barato

Opciones comparadas:

- PC actual Windows: coste cero adicional, mejor para empezar, pero consume mas energia y depende de que la sesion/servicios queden supervisados.
- WSL2 en el PC actual: util si OpenClaw/servicios Linux lo requieren; requiere instalar WSL, systemd y configurar audio si hay voz.
- Mini PC x86/Nuc usado: mejor punto a medio plazo para 24/7 local, 16-32 GB RAM, bajo consumo, compatible con Docker/Ollama/browser automation.
- Raspberry Pi 5: barato y consume poco, pero flojo para browser automation y sin inferencia local seria.
- VPS/Railway: bajo coste mensual y uptime simple, pero datos fuera de casa y mayor superficie de seguridad.

Recomendacion: empezar Windows-native con Task Scheduler/servicios; migrar a mini PC o WSL2 cuando Jarvis ya tenga flujos utiles estables.

### Scraping de Reels

Cascada recomendada:

1. `curl`/HTML publico: barato, sin login, sirve para caption, autor, fecha, likes/comentarios y thumbnail.
2. `yt-dlp`: buena base para descarga multi-sitio, pero Instagram suele requerir cookies/login y puede fallar por rate-limit.
3. `gallery-dl`: fuerte para media scraping con cookies de navegador y configuracion persistente.
4. `instaloader`: fuerte para perfiles/reels/comments/captions; maneja sesion guardada pero es no oficial y puede romperse.
5. Whisper/faster-whisper local: transcribe el audio descargado sin pagar APIs.
6. OCR/keyframes opcional: extraer texto visible de videos tipo tutorial.
7. Apify Instagram Reel Scraper: fallback pagado estable cuando se necesiten transcript, comments, shares/views/duracion y dataset JSON sin pelearse con bloqueos.

No guardar cookies ni tokens en git. Si se usa scraping autenticado, las cookies deben vivir en storage local ignorado.

### Browser automation para Claude/Codex/Jarvis

Patron recomendado:

- Mantener Playwright MCP como baseline para QA y scraping controlado.
- Evaluar un browser CLI persistente para tareas largas porque reduce tokens frente a snapshots DOM completos.
- Usar un perfil de navegador dedicado para Jarvis, nunca el perfil personal principal.
- Separar tres modos: `read-only scrape`, `interactive browser`, `authenticated browser`.

### Obsidian como memoria central

El vault ya es la memoria operacional del ecosistema. Lo que falta para hacerlo robusto:

- Indice de proyecto por repo (`Repo - X.md`).
- Memoria de sesiones compacta.
- Busqueda semantica/RAG sobre notas.
- Notas de decisiones y setup tecnico con `updated:`.
- Un bridge MCP estable: `cyanheads/obsidian-mcp-server`, `obsidian-mcp-rest` o filesystem directo + Local REST API.

## Arquitectura objetivo

```text
Usuario
  -> Voz / CLI / Telegram-WebChat / Browser
  -> Jarvis Control Plane (OpenClaw Gateway o jarvis-auto)
  -> Router de tareas
      -> Local cheap: Ollama qwen/deepseek/phi
      -> Coding premium: Codex/Claude/Gemini/Qwen CLI
      -> Cloud fallback: OpenRouter/OpenAI/Gemini via LiteLLM
  -> Tool layer
      -> Obsidian memory
      -> Browser automation
      -> Filesystem/workspace
      -> Git/GitHub
      -> Scraping pipeline
      -> Voice pipeline
  -> Logs + memory compaction + approvals
```

## Lo que hay hoy

- Monorepo `Multi-LLM-Jarvis-Ecosistem` con `core/`, `ecosystem/`, `configs/` y `scripts/`.
- `core/`: Jarvis Python/FastAPI con RAG, memoria SQLite, LangGraph ReAct, tools, voz y UI inicial.
- `ecosystem/`: scripts de sincronizacion MCP/skills/memoria compartida.
- `configs/`: Aider/Codex/Claude parcial como dotfiles versionados.
- `jarvis` global apunta a `D:\Emmanuel\OpenClawJarvis`, no al monorepo.
- Ollama local funcionando con modelos pequenos.
- Codex MCP Windows estabilizado.
- Obsidian vault activo como memoria central.

## Lo que falta

1. Unificar fuente de verdad: integrar `D:\Emmanuel\OpenClawJarvis`, `C:\Users\Acer Nitro\OpenClawJarvis` y `jarvis_files` dentro del monorepo o definirlos como submodulos/externos.
2. Elegir runtime principal: OpenClaw/Jarvis CLI como control plane; Python `core/` como servicios auxiliares.
3. Crear `jarvis doctor` real dentro del repo: verifica PATH, Node, Python, Ollama, OpenClaw, Codex, Claude, Qwen, Gemini, Obsidian, browser, git.
4. Implementar model router barato: local primero, premium solo para tareas complejas.
5. Implementar scraping pipeline de Reels: metadatos -> descarga con cookies opcionales -> Whisper -> resumen -> nota Obsidian.
6. Implementar memoria Obsidian robusta: indice, sesiones, decisiones, RAG y writing policy.
7. Implementar supervisor 24/7: Task Scheduler/servicio Windows primero; WSL2/systemd despues si conviene.
8. Seguridad: perfiles dedicados, allowlists, sandbox, no secretos versionados, auditoria de skills/MCP.

## Backlog recomendado

### Fase 1 - Normalizacion local

- Mover/documentar OpenClawJarvis dentro de `apps/openclaw-jarvis/` o `runtime/openclaw-jarvis/`.
- Cambiar `jarvis.cmd` para apuntar al repo si se decide que el repo sera fuente de verdad.
- Crear `docs/current-state.md`, `docs/architecture.md`, `docs/backlog.md`.
- Corregir test falso positivo de `intent_classifier`.

### Fase 2 - Runtime operativo

- `jarvis doctor` con checks reproducibles.
- `jarvis start`, `jarvis stop`, `jarvis status`.
- Supervisor Windows con logs rotados.
- Router de modelos por coste/capacidad.

### Fase 3 - Memoria + scraping

- Nota Obsidian automatica por investigacion.
- Pipeline Reels: `metadata.json`, `caption.md`, `transcript.md`, `summary.md`.
- Fallback Apify configurado por env var, no obligatorio.

### Fase 4 - Voz y browser

- Voz local: openWakeWord/Silero/Whisper/Piper o VoiceMode.
- Browser dedicado: Playwright + perfil aislado + modo read-only.
- Workflows: resumen diario, investigacion web, coding review, mantenimiento del repo.

## Fuentes

- OpenClaw: https://github.com/openclaw/openclaw
- OpenClaw architecture: https://docs.openclaw.ai/concepts/architecture
- OpenClaw agent CLI: https://docs.openclaw.ai/cli/agent
- OpenClaw security: https://docs.openclaw.ai/gateway/security
- OpenClaw model failover: https://docs.openclaw.ai/concepts/model-failover
- OpenClaw cron: https://docs.openclaw.ai/automation/cron-jobs
- Apify Instagram Reel Scraper: https://apify.com/apify/instagram-reel-scraper
- Apify guide: https://blog.apify.com/scrape-instagram-reels/
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- Instaloader: https://github.com/instaloader/instaloader
- gallery-dl: https://github.com/mikf/gallery-dl
- OpenOcto: https://github.com/openocto-dev/openocto
- AgenticSeek: https://github.com/Fosowl/agenticSeek
- Leon: https://github.com/leon-ai/leon
- VoiceMode: https://github.com/mbailey/voicemode
- Browser Use: https://github.com/browser-use/browser-use
- Vercel Agent Browser: https://github.com/vercel-labs/agent-browser
- Obsidian MCP REST: https://github.com/PublikPrinciple/obsidian-mcp-rest
- Obsidian MCP Server: https://github.com/cyanheads/obsidian-mcp-server
