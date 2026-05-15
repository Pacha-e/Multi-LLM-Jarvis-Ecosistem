#!/usr/bin/env bash
set -euo pipefail

JARVIS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install Node.js, then rerun ./install.sh"
  exit 1
fi

mkdir -p "${BIN_DIR}"

cat > "${BIN_DIR}/jarvis" <<EOF
#!/usr/bin/env bash
export JARVIS_HOME='${JARVIS_HOME}'
exec node "\$JARVIS_HOME/bin/jarvis-auto.mjs" "\$@"
EOF

cat > "${BIN_DIR}/jarvis-voz" <<EOF
#!/usr/bin/env bash
export JARVIS_HOME='${JARVIS_HOME}'
exec node "\$JARVIS_HOME/bin/jarvis-auto.mjs" --listen --speak "\$@"
EOF

chmod +x "${BIN_DIR}/jarvis" "${BIN_DIR}/jarvis-voz"

echo "Jarvis installed."
echo "Command: ${BIN_DIR}/jarvis"
echo ""
"${BIN_DIR}/jarvis" setup
