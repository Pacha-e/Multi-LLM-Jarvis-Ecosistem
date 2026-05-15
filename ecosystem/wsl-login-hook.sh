#!/usr/bin/env bash
set -u

STAMP="$HOME/.llm-ecosystem/.last_wsl_sync_epoch"
NOW="$(date +%s)"
PREV="0"

if [ -f "$STAMP" ]; then
  PREV="$(cat "$STAMP" 2>/dev/null || echo 0)"
fi

# Run full sync at most once every 6 hours.
if [ $((NOW - PREV)) -ge 21600 ]; then
  bash "$HOME/.llm-ecosystem/run-sync-wsl.sh" >/dev/null 2>&1 || true
  echo "$NOW" > "$STAMP"
fi
