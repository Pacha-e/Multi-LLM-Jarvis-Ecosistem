#!/usr/bin/env bash
set -euo pipefail

BASE_WIN_MOUNT="/mnt/c/Users/Acer Nitro/.llm-ecosystem"
WIN_BASE="$(wslpath -w "$BASE_WIN_MOUNT")"

run_ps() {
  local script="$1"
  shift || true
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "${WIN_BASE}\\${script}" "$@"
}

run_ps "sync-mcp-bidirectional.ps1" -Direction both
run_ps "sync-skills-claude-to-codex.ps1"
run_ps "generate-plugin-map.ps1"

echo "[llm-ecosystem] WSL sync complete."
