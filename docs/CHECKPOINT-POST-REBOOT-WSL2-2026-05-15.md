# Checkpoint Post-Reboot - WSL2 Jarvis (2026-05-15)

Estado antes del reinicio:

- `wsl --install -d Ubuntu` ejecuto correctamente.
- Windows indico: los cambios se aplicaran despues de reiniciar.
- `wsl --set-default-version 2` ejecuto correctamente.
- `wsl -l -v` aun no lista distribuciones; esperado hasta reiniciar.

Al volver:

1. Abrir Ubuntu desde Inicio.
2. Crear usuario Linux y password.
3. Verificar desde Windows:

```cmd
wsl -l -v
```

Esperado:

```text
NAME      STATE      VERSION
Ubuntu    Running    2
```

Luego seguir `docs/setup-wsl2-2026-05-15.md` desde la seccion de entorno Python Linux.

Comandos clave dentro de Ubuntu:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip ffmpeg nodejs npm
cd "/mnt/c/Users/Acer Nitro/Multi-LLM-Jarvis-Ecosistem"
python3 -m venv .venv
.venv/bin/python -m pip install -U pip
.venv/bin/pip install -r core/requirements.txt
.venv/bin/python -m playwright install chromium
node runtime/openclaw-jarvis/bin/jarvis-lifecycle.mjs status
node runtime/openclaw-jarvis/bin/jarvis-lifecycle.mjs start
node runtime/openclaw-jarvis/bin/jarvis-lifecycle.mjs status
```

Registrar supervisor desde Windows:

```powershell
cd "C:\Users\Acer Nitro\Multi-LLM-Jarvis-Ecosistem\scripts"
powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1 -Wsl -Distro Ubuntu
```

Ultimos commits remotos antes del reinicio:

- `cde50fe` docs(handoff): registrar commit supervisor WSL2
- `1160644` feat(supervisor): preparar Jarvis 24-7 con WSL2
- `ed6edfc` fix(reels): corregir ruta default OBSIDIAN_VAULT a D:\Emmanuel\OBSIDIAN\CLAUDE CODE

Obsidian checkpoint: `Claude Code/Checkpoint - Jarvis WSL2 Post-Reboot.md`.
