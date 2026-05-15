# Jarvis Quickstart

For a non-technical user:

Double-click on Windows:

```text
START-JARVIS.cmd
```

Or from WSL/Linux:

```bash
cd OpenClawJarvis
./install.sh
jarvis chat
```

Daily commands:

```bash
jarvis "help me understand this project"
jarvis "fix the login bug and review the change"
jarvis --target /path/to/project "make this operational"
jarvis doctor
jarvis budget
jarvis improve
jarvis voz
```

Jarvis routes automatically:

- fixes and implementation -> Claude plan, Codex implement, Codex review
- architecture and debugging -> Claude architect, Codex review
- planning and specs -> Claude plan, Codex plan
- security and review -> Codex review, Claude review
- broad end-to-end requests -> distributed Claude/Codex pipeline

Use `jarvis doctor` when something feels broken.
Use `jarvis budget` to inspect cost/token policy.
Use `jarvis improve` to audit Jarvis itself.
Use `jarvis improve --apply` only when you want Jarvis to edit its own setup.

Cheapest daily mode is already the default:

```bash
jarvis --budget economy "your request"
```

Escalate only when needed:

```bash
jarvis --budget balanced "fix and review this"
jarvis --budget max "take this project end to end"
jarvis --backend openclaw-agent "use OpenClaw/Gemini agents"
```
