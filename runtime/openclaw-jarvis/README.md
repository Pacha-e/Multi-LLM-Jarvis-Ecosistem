# OpenClaw Jarvis Layer

This directory contains local workspaces and adapters that let OpenClaw act as
the top-level Jarvis/orchestrator for Emmanuel's multi-CLI AI ecosystem.

OpenClaw remains the control plane. These files add role definitions, portable
installers, CLI adapters, self-diagnostics, voice controls, and a simple
daily-use Jarvis interface that routes prompts automatically.

## Install

For a new device or non-technical user:

```text
Double-click START-JARVIS.cmd
```

Or from WSL/Linux:

```bash
cd OpenClawJarvis
./install.sh
jarvis chat
```

The installer writes `jarvis` and `jarvis-voz` wrappers to `~/.local/bin` and
binds them to this folder through `JARVIS_HOME`.

## Daily Use

Use `jarvis` from any WSL shell.

```bash
jarvis "revisa este repo y dime que falta para dejarlo operativo"
jarvis --target /path/to/project "arregla el bug del login y revisa el cambio"
jarvis --mode full "prepara, implementa y valida esta feature"
jarvis chat
jarvis voz
jarvis doctor
jarvis budget
jarvis improve
```

Default mode is `auto`:

- default backend is `subscription-cli`, not Gemini/OpenClaw agents
- implementation/fix prompts -> `claude-plan -> codex-implement -> codex-review`
- architecture/debug prompts -> `claude-architect -> codex-review`
- plan/spec prompts -> `claude-plan -> codex-plan`
- review/security prompts -> `codex-review -> claude-review`
- broad/end-to-end prompts -> `claude-plan -> codex-plan -> claude-architect -> codex-implement -> codex-review`

Useful overrides:

```bash
jarvis --budget economy "arregla este bug"
jarvis --budget balanced "arregla este bug y revisa el cambio"
jarvis --budget max "deja este proyecto listo de punta a punta"
jarvis --backend openclaw-agent "usa los agentes OpenClaw"
jarvis --mode fast "haz una revision rapida"
jarvis --mode council "valida esta arquitectura con mirada adversarial"
jarvis --role qwen "dame una segunda opinion critica"
jarvis --dry-run "arregla el login"
jarvis improve --apply
```

`jarvis voz` uses Windows Speech through PowerShell for one-shot voice input
and speaks the compact result when Windows audio/speech is available.
It cannot clone the Iron Man movie voice; it uses an original cinematic
assistant style and a configurable installed system voice.
Console output is compact by default; full provider JSON and traces remain in
`runs/`.

Voice controls:

```bash
jarvis voice list
jarvis voice test
jarvis voice set --name "Microsoft David Desktop" --rate -1 --volume 100
```

Cost controls:

- `economy` is the default. It prefers subscription CLIs (`codex`, `claude`,
  optionally `qwen`) and local deterministic commands before API-backed
  multi-agent runs.
- `subscription-cli` is the default backend. It preserves distribution by using
  separate Claude/Codex phases instead of OpenClaw/Gemini agents.
- `openclaw-agent` remains available as an explicit backend or fallback.
- `balanced` and `max` increase phases but still use subscription CLI routing
  unless `--backend openclaw-agent` is set.
- If a subscription CLI fails from quota/login/runtime limits, Jarvis falls back
  to the next useful route: `claude-* -> codex-*`,
  `codex-implement -> spark`, `codex-review -> qwen`, `qwen -> iris`.
- `jarvis budget` shows the active cost policy and estimated local prompt/code
  footprint.

Portable and operator docs:

- `QUICKSTART.md`
- `PORTABLE_SETUP.md`
- `VOICE.md`
- `SELF_IMPROVEMENT.md`
- `RESEARCH.md`

## Roles

- `orion`: product planning, task breakdown, routing proposal.
- `kiro`: specs, acceptance criteria, Kiro-style project planning.
- `nova`: architecture, hard debugging, security-sensitive design.
- `spark`: implementation through Codex.
- `aider`: optional focused editor through Gemini Flash when useful.
- `iris`: adversarial review and validation through Gemini/Qwen.

Telegram, Discord, WhatsApp, and n8n are intentionally excluded from this local
architecture.

## Dispatcher

Jarvis roles (`orion`, `kiro`, `nova`, `spark`, `iris`) run through
`openclaw agent --local` with fresh session ids. Raw CLI adapters remain
available as explicit roles: `kiro-cli`, `claude`, `codex`, `gemini`, `qwen`,
`aider`, and `multica`. The `multica` adapter uses the native Linux CLI and
exposes agent creation through `multica agent create`.

```bash
node /mnt/c/Users/EMMANUEL/OpenClawJarvis/bin/jarvis-dispatch.mjs \
  --role spark \
  --objective "Implement the smallest safe fix" \
  --target /path/to/project \
  --dry-run
```

`jarvis-auto.mjs` is the everyday router. `jarvis-dispatch.mjs` remains the
lower-level adapter for explicit routing and tests.

Runs are written under `runs/`. No secrets should be written here.

Secrets are loaded from OpenClaw SecretRefs and are not written to run logs.

## Current Backlog

See `PENDIENTES.md`.
