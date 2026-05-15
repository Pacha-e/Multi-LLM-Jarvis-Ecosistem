# Unification Plan - 2026-05-15

Objetivo: que `C:\Users\Acer Nitro\Multi-LLM-Jarvis-Ecosistem` sea la fuente canonica del ecosistema Jarvis/Multi-LLM.

## Estado actual

| Fuente | Estado | Decision |
|---|---|---|
| `C:\Users\Acer Nitro\Multi-LLM-Jarvis-Ecosistem` | Monorepo Git sincronizado. | Fuente canonica. |
| `C:\Users\Acer Nitro\jarvis_files` | Repo viejo; mismo codigo fuente que `core/` salvo caches/logs. | Congelar como legado; no seguir editando. |
| `D:\Emmanuel\OpenClawJarvis` | Runtime real usado por `jarvis.cmd`; contiene cambios mas recientes. | Migrado a `runtime/openclaw-jarvis/`. |
| `C:\Users\Acer Nitro\OpenClawJarvis` | Copia parcial mas vieja; difiere en dispatchers y docs. | Congelar como legado; no seguir editando. |
| `C:\Users\Acer Nitro\.local\bin\jarvis*` | Wrappers globales apuntan a `D:\Emmanuel\OpenClawJarvis`. | Repuntar al monorepo tras verificar runtime. |

## Estructura canonica

```text
Multi-LLM-Jarvis-Ecosistem/
  configs/                 # Dotfiles versionables: Codex, Claude, Aider
  core/                    # Jarvis Python/FastAPI, RAG, memoria, voice, UI
  docs/                    # Arquitectura, investigacion, backlog, runbooks
  ecosystem/               # Sync MCP/skills/memoria compartida
  runtime/openclaw-jarvis/ # Runtime Jarvis CLI/OpenClaw operativo
  scripts/                 # Setup local y symlinks
```

## Reglas

- No versionar `runs/`, logs, caches, bases de datos ni secretos.
- No editar mas `jarvis_files` ni las copias externas salvo para comparar o recuperar.
- Los wrappers globales deben apuntar al runtime dentro del monorepo.
- Obsidian registra decisiones duraderas y estado operativo.
- Commits y pushes solo con permiso explicito.

## Pasos de consolidacion

1. Copiar `D:\Emmanuel\OpenClawJarvis` a `runtime/openclaw-jarvis/` excluyendo `runs/` y `agents/*/.openclaw/`.
2. Ajustar `.gitignore` para permitir JSON seguros del runtime y seguir bloqueando secretos.
3. Verificar `jarvis doctor` usando `JARVIS_HOME` del repo.
4. Repuntar wrappers `C:\Users\Acer Nitro\.local\bin\jarvis` y `jarvis.cmd` al repo.
5. Registrar en Obsidian.
6. Revisar diff, commit y push si el usuario lo autoriza.

