# jarvis-watchdog.ps1 — single health check + restart-if-down.
# Invoked by Windows Task Scheduler on a recurring trigger (see install-jarvis-supervisor.ps1).
# One pass: check `jarvis status`, restart via `jarvis start` if not healthy.

$ErrorActionPreference = "Stop"
$repo      = Split-Path -Parent $PSScriptRoot
$lifecycle = Join-Path $repo "runtime\openclaw-jarvis\bin\jarvis-lifecycle.mjs"
$logDir    = Join-Path $repo "runtime\openclaw-jarvis\var"
$wdLog     = Join-Path $logDir "watchdog.log"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $wdLog -Value "$ts $msg"
}

# `node jarvis-lifecycle.mjs status` exits 0 only when alive AND health ok.
& node $lifecycle status | Out-Null
if ($LASTEXITCODE -eq 0) {
    Log "ok"
    exit 0
}

Log "down (exit=$LASTEXITCODE) -> restarting"
& node $lifecycle start | Out-Null
& node $lifecycle status | Out-Null
if ($LASTEXITCODE -eq 0) { Log "restart ok" } else { Log "restart FAILED (exit=$LASTEXITCODE)" }
exit $LASTEXITCODE
