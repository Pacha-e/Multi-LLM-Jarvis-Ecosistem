# Jarvis Voice

Jarvis cannot clone or exactly imitate the Iron Man movie voice. The configured
voice is an original cinematic assistant style: formal, calm, precise, and
slightly warm.

Voice commands:

```bash
jarvis voice list
jarvis voice test
jarvis voice set --name "Microsoft David Desktop" --rate -1 --volume 100
jarvis voz
```

`jarvis voz` performs one voice capture through Windows Speech and speaks a
compact result back. If Windows Speech, microphone permissions, or language
settings are not ready, use:

```bash
jarvis chat
jarvis "your request here" --speak
```

Configuration lives in:

```bash
OpenClawJarvis/config/jarvis-profile.json
```

Cost policy:

- Default voice is local Windows Speech: no token cost, no voice API bill.
- Do not use OpenAI Realtime/API voice unless explicitly enabled later.
- Best next upgrade is local Piper TTS for better voice quality without API
  cost.
- Best later upgrade is a wake-word/VAD pipeline so Jarvis only processes audio
  when someone is actually speaking.
