# Fase 1 — Unificación Monorepo (Completada 2026-05-15)

## Objetivo
Consolidar `jarvis_files/` + `OpenClawJarvis/` dispersos en monorepo único `Multi-LLM-Jarvis-Ecosistem/`, con runtime, core, configs y docs versionados juntos.

## Commits Fase 1
| SHA | Asunto |
|-----|--------|
| `6873a45` | feat: unify openclaw-jarvis runtime into monorepo |
| `6e032b1` | fix(doctor): detect codex/claude/qwen .CMD shims on Windows |
| `ecea009` | fix(test): intent_classifier exposes real accuracy (was silent false positive) |
| `123c5db` | docs(configs): add settings.example.json and hooks.example.json templates |

## Cambios técnicos

### 1. Runtime unificado
- `runtime/openclaw-jarvis/` ← antes `C:\Users\Acer Nitro\OpenClawJarvis\`
- Allowlist `.gitignore` para `registry.json`, `config/*.json`, policies.
- `runs/`, logs, caches, secretos → excluidos.

### 2. Doctor PATH Windows (`bin/jarvis-auto.mjs`)
- `findExecutableInPath(name)`: walker nativo PATH+PATHEXT (PATHEXT primero, `""` último).
- `findExecutable()`: native antes de fallback `bash -lc command -v`.
- `runSmall()`: rutea `.cmd`/`.bat` por `cmd.exe /c` (preserva argv quoting). No `shell: true`.
- Adapter detection añade candidatos `codex.cmd`, `claude.cmd`, `qwen.cmd`, `openclaw.cmd`.

**Antes**: codex/claude/qwen `unavailable`.
**Después**: todos `OK` con path completo (`C:\Users\Acer Nitro\AppData\Local\pnpm\codex.CMD`).

### 3. Test suite (`core/test_jarvis.py`)
- Bug: `intent_classifier` siempre añadía a `passed` sin importar accuracy.
- Fix: threshold `0.6` → si menor, va a `errors`.
- Resultado tras fix: **6/7 PASS** (clasificador real predice 0/5 en español — bug separado pendiente).

### 4. Templates configs (allowlist `!**/*.example.json`)
- `configs/claude/settings.example.json` — env vars + permissions + hooks vacíos.
- `configs/codex/hooks.example.json` — placeholders `<RUTA_HOOKS>`.

### 5. Legacy congelado
- `C:\Users\Acer Nitro\jarvis_files\LEGACY.md`
- `C:\Users\Acer Nitro\OpenClawJarvis\LEGACY.md`
- No borrados (preserva `runs/` histórico).

## Restricciones seguridad respetadas
- Remote sin token embebido (push vía GCM helper override).
- Sin cookies/tokens en git.
- `runs/`, logs, DBs, secretos no versionados.

## Bug abierto post-Fase 1
**`IntentClassifier`**: training accuracy 100%, predict 0/5 en español. Sospecha: mismatch tokenizer entre train/predict, o normalización (acentos/lowercase) inconsistente. Pendiente investigación.

## Próximo (Fase 2 candidata)
- `jarvis start/stop/status` reproducibles
- Router modelos por coste/capacidad
- Pipeline Reels (metadata → download → Whisper → Obsidian)
- Supervisor 24/7 (Task Scheduler)
- Fix tokenizer `IntentClassifier`
