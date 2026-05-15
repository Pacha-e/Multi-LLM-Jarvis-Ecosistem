#!/bin/bash
# J.A.R.V.I.S. — Quick Start Script

set -e
JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$JARVIS_DIR"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "[!] Run setup first: bash scripts/setup_wsl.sh"
    exit 1
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null 2>&1; then
    echo "[*] Starting Ollama..."
    ollama serve > /tmp/ollama.log 2>&1 &
    sleep 2
fi

# Load env
if [ -f "jarvis.env" ]; then
    set -a
    source jarvis.env
    set +a
fi

echo "[+] Starting J.A.R.V.I.S..."
python run.py
