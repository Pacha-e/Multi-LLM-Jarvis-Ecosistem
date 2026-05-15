@echo off
set "BASE=%USERPROFILE%\.llm-ecosystem"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BASE%\sync-mcp-bidirectional.ps1" -Direction both
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BASE%\sync-skills-claude-to-codex.ps1"
if errorlevel 1 exit /b 1

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BASE%\generate-plugin-map.ps1"
if errorlevel 1 exit /b 1
