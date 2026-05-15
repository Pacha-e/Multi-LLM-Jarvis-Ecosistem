# Portable Setup

Goal: copy this Jarvis folder to another WSL/Linux device and make it usable by
someone with no prior knowledge.

## Install

For Windows users, double-click:

```text
START-JARVIS.cmd
```

For voice mode, double-click:

```text
START-JARVIS-VOICE.cmd
```

For terminal setup:

```bash
cd OpenClawJarvis
./install.sh
```

The installer:

- detects the current folder as `JARVIS_HOME`
- creates `~/.local/bin/jarvis`
- creates `~/.local/bin/jarvis-voz`
- creates or validates `config/jarvis-profile.json`
- runs `jarvis doctor`

## Required

- Node.js available as `node`
- OpenClaw installed and authenticated for full orchestration

## Optional Adapters

- Codex: implementation adapter
- Claude: architecture adapter
- Qwen: council/review adapter
- Gemini: validation/fallback adapter
- Multica: local agent platform
- PowerShell/Windows Speech: voice input/output on WSL + Windows

If optional adapters are missing, `jarvis doctor` reports `WARN` instead of
blocking basic use.

## First Run For A New User

```bash
jarvis setup
jarvis doctor
jarvis chat
```

Inside chat:

```text
jarvis> explain what you can do
jarvis> /target /path/to/project
jarvis> fix the failing tests and review the result
```
