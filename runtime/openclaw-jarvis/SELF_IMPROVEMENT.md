# Jarvis Self-Improvement

Jarvis can evaluate its own setup and propose improvements.

Audit only:

```bash
jarvis improve
```

Apply safe improvements:

```bash
jarvis improve --apply
```

Rules:

- audit mode does not edit files
- apply mode targets the Jarvis home folder
- no secrets are printed or copied
- no auto-commit, auto-push, or deploy
- smallest safe improvement first
- verification and docs update are required after edits

Use `jarvis doctor` after any self-improvement run.

Cost and token audit:

```bash
jarvis budget
```

Default policy is `economy`: use deterministic local commands and subscription
CLIs first, then escalate to API-backed multi-agent execution only when useful.

Escalation policy:

- `economy`: distributed Claude/Codex subscription phases, minimal path.
- `balanced`: more review/synthesis, still subscription-first.
- `max`: full distributed pipeline, still subscription-first by default.
- `openclaw-agent`: explicit backend for OpenClaw/Gemini agents when wanted.
- Fallbacks preserve power when subscriptions are exhausted:
  `codex-write -> spark`, `claude -> nova`, `qwen -> iris`.

Risky work includes auth, login, payments, database migrations, deployment,
production, secrets, and token handling.
