# Shared Memory — Multi-LLM Ecosystem
<!-- Auto-maintained. Todos los CLIs leen y escriben aquí. -->
<!-- Formato: [[slug]] → archivo en este directorio. -->
<!-- TTL: entradas sin actualizar en >30 días se archivan. -->

## Memoria activa

| Slug | Tipo | Descripción | Actualizado |
|------|------|-------------|-------------|
| [[routing-stats]] | stats | Métricas de routing por CLI | auto |
| [[task-context]] | context | Tarea activa cross-sesión | manual |
| [[decisions]] | decisions | Decisiones arquitectónicas tomadas | manual |
| [[model-perf]] | perf | Performance observada por modelo | auto |

## Protocolo de lectura (todos los CLIs)

1. Leer `INDEX.md` al inicio de sesión compleja.
2. Buscar contexto relevante en archivos listados.
3. Al aprender algo duradero → escribir en archivo apropiado.

## Protocolo de escritura

- `task-context.md`: tarea activa, archivos modificados, próximos pasos.
- `decisions.md`: decisiones con razonamiento y fecha.
- `model-perf.md`: cuándo un modelo falló o sobresalió en qué tipo de tarea.
- `routing-stats.md`: generado automáticamente por multi-llm-router.js.
