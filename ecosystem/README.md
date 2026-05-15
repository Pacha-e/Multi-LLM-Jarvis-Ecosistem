# LLM CLI Ecosystem - Integracion Operativa

Este workspace unifica tu operacion entre Codex, Claude Code y otros clientes CLI
que consumen configuraciones locales en `C:\Users\Acer Nitro`.

## Topologia actual detectada

- `C:\Users\Acer Nitro\.codex\config.toml`: capa principal de Codex (MCP + reglas).
- `C:\Users\Acer Nitro\.codex\AGENTS.md`: puente de comportamiento Claude -> Codex.
- `C:\Users\Acer Nitro\.claude\commands`: libreria de intenciones tipo slash command.
- `C:\Users\Acer Nitro\.claude\agents`: criterios de especialistas.
- `C:\Users\Acer Nitro\.mcp.json`: definicion MCP minima compartida para otros clientes.
- `C:\Users\Acer Nitro\.claude.json`: definicion MCP extendida de Claude Code.

## Capa de enrutamiento recomendada

Usa esta regla mental para mantener consistencia entre agentes:

1. **Reglas y estilo**: `AGENTS.md` y `CLAUDE.md`.
2. **Documentacion tecnica**: `openaiDeveloperDocs` y `context7`.
3. **Memoria**: `claudeMem` y `obsidian`.
4. **Acciones externas**: `github`, `vercel`, `supabase`, `n8n`, `dockerGateway`.
5. **Navegacion/UI**: `playwright`.
6. **Imagenes**: `imagegen` (nativo) y `nanobanana` cuando lo pidas explicitamente.

## Flujo estandar de trabajo (multi-LLM)

1. **Plan corto**: objetivo, alcance, criterio de exito.
2. **Ejecucion lean**: buscar primero, leer solo lo necesario.
3. **Verificacion minima util**: lint/typecheck/test segun cambio.
4. **Revision de riesgo**: seguridad y side effects antes de mutaciones.
5. **Cierre**: resumen de cambios, validacion, proximos pasos.

## Seguridad obligatoria

- No copiar secretos entre archivos.
- No imprimir tokens en consola ni reportes.
- Rotar credenciales cuando se detecten en texto plano.
- Preferir variables de entorno en vez de valores hardcodeados.

## Siguiente hardening recomendado

1. Migrar secretos de `.mcp.json` y `.claude.json` a environment variables del sistema.
2. Mantener una sola fuente de verdad MCP (generar derivados, no editar duplicados a mano).
3. Crear script de chequeo rapido de salud MCP antes de iniciar sesion.

## Sync bidireccional MCP

Script: `C:\Users\Acer Nitro\.llm-ecosystem\sync-mcp-bidirectional.ps1`

- Dry run (sin cambios):
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-mcp-bidirectional.ps1" -Direction both -DryRun`
- Aplicar de Claude -> Codex:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-mcp-bidirectional.ps1" -Direction claude-to-codex`
- Aplicar de Codex -> Claude:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-mcp-bidirectional.ps1" -Direction codex-to-claude`
- Aplicar en ambos sentidos:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-mcp-bidirectional.ps1" -Direction both`

Notas:
- Usa `mcp-alias-map.json` para normalizar nombres legacy.
- Antes de escribir, crea backup con timestamp de cada archivo objetivo.

## Sync de skills

Script: `C:\Users\Acer Nitro\.llm-ecosystem\sync-skills-claude-to-codex.ps1`

- Dry run:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-skills-claude-to-codex.ps1" -DryRun`
- Aplicar:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\sync-skills-claude-to-codex.ps1"`

Compatibilidad:
- Solo sincroniza skills con `SKILL.md` y frontmatter valido.
- Genera reporte en `C:\Users\Acer Nitro\.llm-ecosystem\skills-sync-report.json`.

## Mapa de plugins

Script: `C:\Users\Acer Nitro\.llm-ecosystem\generate-plugin-map.ps1`

- Ejecutar:
  - `powershell -ExecutionPolicy Bypass -File "C:\Users\Acer Nitro\.llm-ecosystem\generate-plugin-map.ps1"`

Salida:
- JSON: `C:\Users\Acer Nitro\.llm-ecosystem\plugin-map.json`
- Markdown: `C:\Users\Acer Nitro\.llm-ecosystem\plugin-map.md`

## Auto sync al iniciar sesion

`run-mcp-sync.cmd` ahora ejecuta:
1. Sync MCP bidireccional.
2. Sync skills Claude -> Codex.
3. Generacion de mapa de plugins.

## Migracion WSL (Ubuntu)

Archivos agregados:
- `C:\Users\Acer Nitro\.llm-ecosystem\run-sync-wsl.sh`
- `C:\Users\Acer Nitro\.llm-ecosystem\wsl-login-hook.sh`

Instalacion WSL aplicada:
- `~/.llm-ecosystem/run-sync-wsl.sh`
- `~/.llm-ecosystem/wsl-login-hook.sh`
- `~/.llm-ecosystem/.last_wsl_sync_epoch` (control de frecuencia)

Ejecucion manual en Ubuntu:
- `bash ~/.llm-ecosystem/run-sync-wsl.sh`

Comportamiento:
- El hook de login en WSL dispara sync completo.
- Throttle: maximo 1 ejecucion cada 6 horas para evitar ruido.
