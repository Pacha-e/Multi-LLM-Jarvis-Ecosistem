# Documentación del Ecosistema Multi-LLM Jarvis

Esta documentación detalla la arquitectura de tu ecosistema, centralizada en este repositorio.

## 1. Visión General
El proyecto `Multi-LLM-Jarvis-Ecosistem` es una solución completa para un asistente personal (Jarvis) con capacidades de RAG, multi-agente, memoria persistente y orquestación de herramientas externas.

## 2. Estructura de Directorios
- `core/`: Núcleo de la aplicación Jarvis (Python).
- `ecosystem/`: Orquestación, sincronización de plugins y hooks (WSL/Windows).
- `configs/`: Configuraciones versionadas de herramientas externas (Claude, Codex, Aider).
- `scripts/`: Herramientas de automatización y setup (symlinks).

## 3. Componentes Detallados

### A. Jarvis (core/)
- `jarvis/`: Lógica principal, enrutador de LLMs, memoria y agentes.
- `jarvis/agent/`: Módulos de IA (router, rag, memory, personas, tools).
- `jarvis/voice/`: Módulos de voz (stt, tts, wake_word).
- `jarvis/ui/`: Interfaz web del asistente.

### B. Ecosistema de Orquestación (ecosystem/)
- Mapeo de plugins (`plugin-map.json`).
- Sincronización bidireccional (scripts `.ps1` y `.sh`).
- Memoria compartida (`shared-memory/`).

### C. Configuraciones Externas (configs/)
- `aider/`: `.aider.conf.yml`, `.aider.model.settings.yml`.
- `claude/`: `settings.json`.
- `codex/`: `config.toml`, `hooks.json`.

## 4. Conectividad
- **Symlinks:** Las configuraciones se vinculan mediante enlaces simbólicos desde este repositorio a sus ubicaciones originales (`~/.claude/`, `~/.codex/`, etc.), garantizando que este repo sea la "fuente de verdad".
- **Scripts:** `ecosystem/` contiene los hooks que mantienen la coherencia entre el sistema Windows y el entorno de ejecución (WSL2).

---
*Para más detalles, consultar `core/docs/informe_proyecto.md` y `ecosystem/README.md`.*
