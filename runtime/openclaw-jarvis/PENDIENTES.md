# OpenClaw Jarvis Pendientes

Estado verificado: 2026-05-11.

## Operativo local

0. Interfaz diaria Jarvis.
   - Comando simple en PATH: `jarvis`.
   - Instalador portatil: `OpenClawJarvis/install.sh` crea wrappers en `~/.local/bin` con `JARVIS_HOME` dinamico.
   - Onboarding no tecnico documentado en `QUICKSTART.md` y `PORTABLE_SETUP.md`.
   - Diagnostico simple: `jarvis doctor`.
   - Chat interactivo: `jarvis` o `jarvis chat`.
   - Voz one-shot: `jarvis voz` o `jarvis --listen --speak` usando Windows Speech via PowerShell cuando el microfono/idioma estan disponibles.
   - Voz configurada como estilo cinematic-original con `Microsoft David Desktop`; no clona voces de peliculas ni de actores.
   - Control de voz: `jarvis voice list|set|test`.
   - Auto-mejora: `jarvis improve` audita el setup; `jarvis improve --apply` permite aplicar mejoras seguras sobre `OpenClawJarvis`.
   - Backend default: `subscription-cli`, no OpenClaw/Gemini API.
   - Router automatico subscription: implementacion -> `claude-plan`+`codex-implement`+`codex-review`; arquitectura/debug -> `claude-architect`+`codex-review`; plan/spec -> `claude-plan`+`codex-plan`; review/security -> `codex-review`+`claude-review`; modo amplio -> pipeline Claude/Codex distribuido.
   - Backend alternativo explicito: `--backend openclaw-agent` usa `orion/kiro/nova/spark/iris`.
   - Overrides: `--mode fast|full|council`, `--budget economy|balanced|max`, `--backend subscription-cli|openclaw-agent`, `--role <agente>`, `--target <ruta>`, `--dry-run`, `--speak`.
   - Salida diaria limpia: muestra solo respuesta util; JSON/meta completo queda en `runs/`.

1. OpenClaw queda como control plane local/Jarvis.
   - Gateway systemd user activo en `127.0.0.1:18789`.
   - Dispatcher local usa `openclaw agent --local` para `orion`, `kiro`, `nova`, `spark` e `iris`.
   - Dispatcher directo maneja `codex`, `claude` y `qwen` con rutas absolutas y modo no interactivo.
   - El dispatcher carga `GEMINI_API_KEY` desde el secret store local cuando no existe en el entorno.

2. Agentes OpenClaw listos.
   - `orion`, `kiro`, `nova`, `spark` e `iris` tienen identidad/usuario fijados.
   - `BOOTSTRAP.md` fue eliminado de los workspaces para evitar prompts de primera conversacion.
   - Smoke tests del dispatcher local: los cinco roles devuelven `status: succeeded`.

3. Aider listo como editor opcional.
   - Config activo: `~/.aider.conf.yml`.
   - Modelo: `gemini/gemini-2.5-flash`.
   - Sin auto-commits, sin dirty-commits, sin update check.
   - Smoke real desde dispatcher: OK.

4. Secretos migrados.
   - `gateway.auth.token` y `models.providers.google.apiKey` usan SecretRef de archivo.
   - Secret store: `/home/emmanuel/.openclaw/secrets.json`, permisos `600`.
   - `openclaw secrets audit --json`: clean, 0 plaintext, 0 unresolved refs.

5. Multica nativo.
   - Binario Linux nativo compilado en `/mnt/c/Users/EMMANUEL/.multica/bin/multica-linux`.
   - Wrapper `/mnt/c/Users/EMMANUEL/bin/multica` prioriza Linux nativo y deja `multica.exe` solo como fallback.
   - Config nativa WSL en `/home/emmanuel/.multica/` con permisos restrictivos.
   - Daemon nativo corriendo y detectando runtimes locales: Claude, Codex, OpenClaw, Gemini y Kimi.
   - `multica agent create --help` operativo para crear agentes.

## Fuera de alcance por decision actual

6. Telegram, Discord y WhatsApp.
   - El usuario decidio no usarlos.
   - `commands.ownerAllowFrom` queda sin canal externo por diseno.
   - El warning de owner en `doctor` es esperado mientras no exista un canal chat permitido.

7. n8n.
   - Queda fuera de esta arquitectura por preferencia actual.

## Pendientes externos no bloqueantes

8. Kiro CLI nativo.
   - `kiro-cli` esta instalado, pero `doctor`/chat headless no es fiable en este contexto.
   - No bloquea: el agente OpenClaw `kiro` ya esta operativo como spec architect.

9. Qwen en Multica.
   - Jarvis/OpenClaw maneja Qwen via dispatcher directo.
   - Multica upstream no registra Qwen como runtime nativo; no bloquear por esto.

10. Reverse proxy.
   - `gateway.trusted_proxies_missing` solo importa si Control UI se expone detras de proxy.
   - Mientras el gateway siga local-only en loopback, no bloquear por este warning.

## Verificacion actual

- `openclaw doctor --non-interactive --no-workspace-suggestions`: owner falta por diseno sin canal chat externo; skills/plugins sin errores criticos.
- `openclaw security audit --deep --json`: 0 critical, 1 warn, 1 info.
- `openclaw secrets audit --json`: clean, 0 plaintext, 0 unresolved refs.
- `openclaw agents list --json`: `main`, `orion`, `kiro`, `nova`, `spark`, `iris` presentes.
- `openclaw config validate`: config valida.
- `jarvis-dispatch`: `orion`, `kiro`, `nova`, `spark`, `iris`, `aider` smoke OK; Codex plan/review smoke real OK; Claude integrado por CLI, sujeto a cuota/reset del plan; `qwen` y `multica` disponibles por dispatcher.
- `jarvis`: comando global OK; `jarvis setup` OK; `jarvis doctor` OK; `jarvis budget` OK; `jarvis improve --dry-run` OK; `jarvis voice list/set/test` OK; smoke real con `--role orion` OK; routing `--dry-run` OK para subscription default, `--budget max` y `--backend openclaw-agent`.
- `multica daemon status --output json`: running; runtimes locales online.
