# Documentacion del Ecosistema Multi-LLM Jarvis

Este repositorio centraliza el ecosistema Jarvis: codigo, orquestacion, configuraciones de CLIs y documentacion operativa.

## 1. Vision General

`Multi-LLM-Jarvis-Ecosistem` busca convertir Jarvis en un asistente personal multi-LLM con memoria persistente, RAG, herramientas locales, browser automation, voz y ejecucion 24/7 de bajo coste.

## 2. Estructura de Directorios

- `core/`: nucleo Python/FastAPI de Jarvis, RAG, memoria, tools, voz y UI inicial.
- `ecosystem/`: scripts de orquestacion, sincronizacion MCP/skills y memoria compartida.
- `configs/`: configuraciones versionadas de herramientas externas como Claude, Codex y Aider.
- `runtime/openclaw-jarvis/`: runtime operativo del comando `jarvis`, agentes OpenClaw y dispatcher multi-CLI.
- `scripts/`: automatizacion local, setup, symlinks y supervisor 24/7.
- `docs/`: investigacion, arquitectura, backlog y runbooks del ecosistema.

## 3. Componentes Detallados

### Jarvis (`core/`)

- `jarvis/`: logica principal, enrutador de LLMs, memoria y agentes.
- `jarvis/agent/`: router, RAG, memory, personas y tools.
- `jarvis/voice/`: STT, TTS y wake word.
- `jarvis/pipelines/`: pipelines de contenido como Reels -> Whisper -> Obsidian.
- `jarvis/ui/`: interfaz web del asistente.

### Ecosistema de Orquestacion (`ecosystem/`)

- Mapeo de plugins y MCPs.
- Sincronizacion bidireccional entre herramientas.
- Memoria compartida para decisiones, indices y rendimiento.

### Configuraciones Externas (`configs/`)

- `aider/`: `.aider.conf.yml`, `.aider.model.settings.yml`.
- `claude/`: settings versionables no sensibles.
- `codex/`: `config.toml` y hooks versionables.

### Runtime Operativo (`runtime/openclaw-jarvis/`)

- `bin/jarvis-auto.mjs`: interfaz diaria, doctor, routing y modos de ejecucion.
- `bin/jarvis-dispatch.mjs`: dispatcher hacia Claude, Codex, Qwen, Aider, Multica y agentes OpenClaw.
- `bin/jarvis-lifecycle.mjs`: `start|stop|status` del core FastAPI.
- `agents/`: perfiles `orion`, `kiro`, `nova`, `spark` e `iris`.
- `config/`: perfil de Jarvis versionable sin secretos.

## 4. Conectividad

- Las configuraciones se vinculan mediante symlinks desde sus ubicaciones originales (`~/.claude/`, `~/.codex/`, etc.) hacia este repo.
- `ecosystem/` contiene hooks y scripts para mantener coherencia entre Windows, WSL y herramientas AI.
- Obsidian funciona como memoria central del ecosistema y debe registrar decisiones duraderas.

## 5. Investigacion y Runbooks

- `docs/jarvis-vision-research-2026-05-15.md`: vision Jarvis, OpenClaw, Obsidian, scraping de Reels, browser automation, voz local y plan 24/7.
- `docs/unification-plan-2026-05-15.md`: plan paso a paso para que el monorepo sea la unica fuente de verdad.
- `docs/fase1-completion-2026-05-15.md`: cierre Fase 1.
- `docs/setup-wsl2-2026-05-15.md`: runbook para ejecutar Jarvis 24/7 con WSL2 + Windows Task Scheduler.
- `docs/HANDOFF-2026-05-15.md`: estado actual, decisiones, riesgos y siguientes pasos.

## 6. Estado Fase 1 - Completa (2026-05-15)

Commits clave:

- `6873a45` unify runtime.
- `6e032b1` doctor PATH Windows (.CMD shims).
- `17b05f9` IntentClassifier 5/5 en espanol real.
- `123c5db` templates `*.example.json`.

Doctor `jarvis doctor`: Codex/Claude/Qwen OK con paths nativos Windows. Tests: 7/7 PASS. Legacy `jarvis_files/` y `OpenClawJarvis/` marcados `LEGACY.md`, congelados.

## 7. Estado Fase 2 - En Curso (2026-05-15)

- Router de modelos por coste/capacidad: `simple`, `medium`, `complex`.
- Pipeline `jarvis reels <url>`: `yt-dlp -> Playwright perfil dedicado -> Apify opcional -> Whisper -> Obsidian`.
- Vault por defecto: `D:\Emmanuel\OBSIDIAN\CLAUDE CODE`.
- Plan 24/7 elegido: WSL2 + Windows Task Scheduler, sin VPS.
- Agent Browser de Vercel queda como mejora futura dentro de WSL2; Playwright sigue como fallback actual.
