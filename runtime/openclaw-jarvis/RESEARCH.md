# Jarvis Research Notes

Updated: 2026-05-11

## Useful Patterns Found

### Leon

Leon is an open-source personal assistant with server runtime, web app, memory,
context management, skills, bridges, and setup checks. The useful pattern for
this Jarvis setup is not to copy Leon, but to keep Jarvis modular:

- `bin/` for runtime commands
- `config/` for portable profile
- docs for non-technical onboarding
- `doctor` command before deep debugging
- skills/adapters instead of one monolithic prompt

### Open Interpreter 01

01 is a voice interface for desktop/mobile/ESP32 with configurable profiles and
multiple server modes. It also warns that experimental agents need safeguards.
Useful pattern:

- keep voice separate from execution
- keep profiles editable
- never expose paid/service-control tools without guardrails

### Rhasspy / Home Assistant Assist / Piper

Rhasspy shows the low-cost voice architecture: local wake word, local STT,
intent routing, local TTS, and structured events. Home Assistant Assist uses a
pipeline with wake word -> STT -> intent -> TTS, and recommends avoiding
unnecessary audio streaming with local VAD. Piper is a fast local neural TTS
system.

Useful pattern for Jarvis:

- current: Windows Speech for zero-cost local voice
- next: optional Piper TTS for better local voice quality
- later: optional wake word/VAD pipeline
- avoid OpenAI Realtime/API voice by default because it increases cost

## Cost Policy

Default is `economy`.

Priority order:

1. Deterministic local command: help, doctor, budget, setup, voice config.
2. Distributed subscription CLI orchestration: Claude plans/architects, Codex
   implements/reviews.
3. Qwen council/review only when useful or explicitly requested.
4. OpenClaw/Gemini agents as explicit backend or fallback.
5. API voice/realtime only by explicit opt-in.

## Subscription vs API

Codex supports ChatGPT sign-in for subscription access and API-key sign-in for
usage-based access. Claude Code usage also depends on sign-in method: plan seats
hit usage limits, API keys are billed by token. Therefore Jarvis should prefer
CLI subscription auth for daily work and reserve API keys for automation,
CI/CD, or overflow.

## Implemented From Research

- `jarvis budget`
- `--budget economy|balanced|max`
- `--backend subscription-cli|openclaw-agent`
- default `economy` + `subscription-cli`
- subscription-distributed phases: `claude-plan`, `codex-plan`,
  `claude-architect`, `codex-implement`, `codex-review`
- subscription-first fallback ladder: `codex-implement -> spark`,
  `claude-* -> codex-*`, `codex-review -> qwen`, `qwen -> iris`
- deterministic local intents before model calls
- local Windows Speech voice by default
- portable config profile

## Not Implemented Yet

- Piper TTS installer
- local wake word/VAD loop
- Home Assistant Assist bridge
- browser/mobile UI
