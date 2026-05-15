# Decisiones de Arquitectura — Multi-LLM Ecosystem
<!-- Escribe aquí decisiones duraderas con razonamiento. -->
<!-- Format: ## [YYYY-MM-DD] Título → Decisión + Por qué -->

## [2026-05-15] Equipar Qwen Code con MCPs completos
- **Decisión**: Crear `~/.qwen/mcp.json` con 12 MCPs (context7, claudeMem, obsidian, github, playwright, filesystem, supabase, n8n, nanobanana, stitch, lean-ctx).
- **Por qué**: Qwen Code (Gemini Flash, DeepSeek R1, Qwen3-Coder free) es el backend de bajo costo. Sin MCPs no puede acceder a memoria ni herramientas → reduce su utilidad a texto puro.
- **Impacto**: Todos los modelos del ecosistema ahora tienen acceso simétrico a herramientas.

## [2026-05-15] Router v2 con cost-awareness y eval-loop
- **Decisión**: Reescribir multi-llm-router.js con 8 reglas, cost tiers, logging a JSONL.
- **Por qué**: Router v1 era solo hint sin logging. v2 agrega: eval-loop hint (MAR pattern), DeepSeek para razonamiento, Haiku para tareas simples, log de routing para análisis posterior.
- **Impacto**: Cada prompt ahora guía al modelo correcto con indicador de costo.

## [2026-05-15] Arquitectura MAR (Multi-Agent Reflexion)
- **Decisión**: Implementar patrón Generator→Critic(Gemini)→Refiner como skill /eval-loop.
- **Por qué**: Cross-model critique reduce bias (crítico detecta mejor errores de otro modelo que de sí mismo). Gemini como crítico porque es barato ($0.15/Mtok).
- **Referencia**: arxiv 2512.20845 (MAR 2025).

## [2026-05-15] Shared Memory cross-CLI
- **Decisión**: `~/.llm-ecosystem/shared-memory/` como capa de memoria neutral.
- **Por qué**: Obsidian vault es buena memoria humana pero lenta para CLIs. Directorio de archivos planos es más rápido y accesible desde cualquier herramienta sin MCP.
