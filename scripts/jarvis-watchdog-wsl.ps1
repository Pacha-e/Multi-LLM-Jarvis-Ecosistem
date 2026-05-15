# jarvis-watchdog-wsl.ps1 — Windows-side health check that drives Jarvis INSIDE WSL2.
# Invoked by Windows Task Scheduler on a recurring trigger.
# One pass: check `jarvis-lifecycle status` inside the WSL distro, restart if not healthy.
#
# The Jarvis core (FastAPI/uvicorn) runs inside WSL2; Windows only supervises.
# No credentials stored. Runs while the user is logged on.

param([string]$Distro = "Ubuntu")

$ErrorActionPreference = "Stop"
$repo      = Split-Path -Parent $PSScriptRoot
# Repo path translated to the WSL view (C:\ -> /mnt/c/).
$repoWsl   = "/mnt/c" + ($repo -replace '^[A-Za-z]:','' -replace '\\','/')
$lifecycle = "$repoWsl/runtime/openclaw-jarvis/bin/jarvis-lifecycle.mjs"
$logDir    = Join-Path $repo "runtime\openclaw-jarvis\var"
$wdLog     = Join-Path $logDir "watchdog-wsl.log"

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $wdLog -Value "$ts $msg"
}

# `node jarvis-lifecycle.mjs status` exits 0 only when alive AND health ok.
& wsl -d $Distro -- node "$lifecycle" status | Out-Null
if ($LASTEXITCODE -eq 0) {
    Log "ok"
    exit 0
}

Log "down (exit=$LASTEXITCODE) -> restarting inside WSL2 [$Distro]"
& wsl -d $Distro -- node "$lifecycle" start | Out-Null
& wsl -d $Distro -- node "$lifecycle" status | Out-Null
if ($LASTEXITCODE -eq 0) { Log "restart ok" } else { Log "restart FAILED (exit=$LASTEXITCODE)" }
exit $LASTEXITCODE
