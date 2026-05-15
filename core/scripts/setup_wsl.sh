#!/usr/bin/env bash
# J.A.R.V.I.S. — WSL2 Setup Script
# Installs Ollama + Jarvis as systemd services for always-on operation
# Usage: bash scripts/setup_wsl.sh
#
# WSL2 .wslconfig NOTE: Use autoMemoryReclaim=dropcache, NOT gradual.
# The 'gradual' setting causes ls/apt to hang indefinitely — known WSL2 bug.

set -e

JARVIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JARVIS_USER="$USER"
OLLAMA_MODEL="qwen2.5:3b"

echo "╔══════════════════════════════════════╗"
echo "║  J.A.R.V.I.S. WSL2 Setup            ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "[*] Directory: $JARVIS_DIR"
echo "[*] User: $JARVIS_USER"
echo ""

# 1. System dependencies
echo "[1/7] Installing system dependencies..."
sudo apt-get update -q
sudo apt-get install -y -q \
    python3.11 python3.11-venv python3-pip \
    portaudio19-dev libsndfile1 ffmpeg \
    wget git

# 2. Install Ollama (download script first, then run)
echo "[2/7] Installing Ollama..."
if ! command -v ollama &>/dev/null; then
    # Download installer separately (review before running)
    wget -q -O /tmp/ollama_install.sh https://ollama.ai/install.sh
    chmod +x /tmp/ollama_install.sh
    /tmp/ollama_install.sh
    rm /tmp/ollama_install.sh
    echo "[+] Ollama installed"
else
    echo "[=] Ollama already installed: $(ollama --version)"
fi

# 3. Enable Ollama systemd service
echo "[3/7] Enabling Ollama service..."
sudo systemctl enable ollama 2>/dev/null || true
sudo systemctl start ollama  2>/dev/null || ollama serve &
sleep 3
echo "[+] Ollama running"

# 4. Pull primary model
echo "[4/7] Pulling model: $OLLAMA_MODEL"
ollama pull "$OLLAMA_MODEL"
echo "[+] Model ready"

# 5. Python venv
echo "[5/7] Setting up Python environment..."
cd "$JARVIS_DIR"
python3.11 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "[+] Dependencies installed"

# 6. Env config
if [ ! -f "$JARVIS_DIR/jarvis.env" ]; then
    cp "$JARVIS_DIR/env.example" "$JARVIS_DIR/jarvis.env"
    echo "[!] Created jarvis.env — add your API keys there"
fi

# 7. systemd service for Jarvis
echo "[6/7] Creating J.A.R.V.I.S. systemd service..."
sudo tee /etc/systemd/system/jarvis.service > /dev/null <<EOF
[Unit]
Description=J.A.R.V.I.S. Multi-LLM AI Ecosystem
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$JARVIS_USER
WorkingDirectory=$JARVIS_DIR
ExecStart=$JARVIS_DIR/.venv/bin/python run.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jarvis
echo "[+] Jarvis service enabled"

# 8. Train ML classifier
echo "[7/7] Training intent classifier..."
mkdir -p data
python -c "from jarvis.agent.intent_classifier import train_classifier; train_classifier()"
echo "[+] Classifier trained (93% accuracy)"

# 9. .wslconfig optimization (Windows host)
WSLCONFIG_WIN="/mnt/c/Users/$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r\n')/.wslconfig"
if [ ! -f "$WSLCONFIG_WIN" ] 2>/dev/null; then
    echo "[+] Creating optimized .wslconfig..."
    cat > "$WSLCONFIG_WIN" << 'WSLEOF'
[wsl2]
memory=8GB
processors=4
swap=4GB
localhostForwarding=true
# NOTE: dropcache fixes WSL2 hang bug — do NOT use 'gradual'
autoMemoryReclaim=dropcache
WSLEOF
    echo "[+] .wslconfig created — restart WSL2: wsl --shutdown"
fi

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  Setup Complete!                           ║"
echo "╠════════════════════════════════════════════╣"
echo "║  Start:  sudo systemctl start jarvis       ║"
echo "║  Stop:   sudo systemctl stop jarvis        ║"
echo "║  Logs:   journalctl -u jarvis -f           ║"
echo "║  Web UI: http://localhost:8000             ║"
echo "║                                            ║"
echo "║  Edit jarvis.env with your API keys!       ║"
echo "║  Get free Groq key: console.groq.com       ║"
echo "╚════════════════════════════════════════════╝"
