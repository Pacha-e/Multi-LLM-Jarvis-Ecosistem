# install-jarvis-supervisor.ps1 — register the Jarvis 24/7 watchdog in Task Scheduler.
# Run once in an elevated-or-normal PowerShell. Idempotent: re-running re-registers.
#
#   Register (Windows core): powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1
#   Register (WSL2 core):    powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1 -Wsl -Distro Ubuntu
#   Uninstall:               powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1 -Uninstall
#
# Task runs the watchdog at logon + every 5 minutes (current user, no admin needed).
# Does NOT store credentials. Runs only while the user is logged on.

param(
    [switch]$Uninstall,
    [switch]$Wsl,                  # -Wsl: supervise the Jarvis core running inside WSL2
    [string]$Distro = "Ubuntu"     # WSL distro name (only used with -Wsl)
)

$ErrorActionPreference = "Stop"
$taskName  = "JarvisSupervisor"
$repo      = Split-Path -Parent $PSScriptRoot
if ($Wsl) {
    $watchdog = Join-Path $repo "scripts\jarvis-watchdog-wsl.ps1"
} else {
    $watchdog = Join-Path $repo "scripts\jarvis-watchdog.ps1"
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "[supervisor] task '$taskName' removed."
    } else {
        Write-Host "[supervisor] task '$taskName' not found."
    }
    return
}

if (-not (Test-Path $watchdog)) { throw "watchdog script missing: $watchdog" }

$wdArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdog`""
if ($Wsl) { $wdArgs += " -Distro `"$Distro`"" }
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $wdArgs

# Trigger 1: at logon. Trigger 2: every 5 min indefinitely.
$tLogon = New-ScheduledTaskTrigger -AtLogOn
$tRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 4)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName `
    -Action $action -Trigger @($tLogon, $tRepeat) `
    -Settings $settings -Principal $principal `
    -Description "Jarvis 24/7 watchdog: keeps the FastAPI core alive (health-check + restart every 5 min)." | Out-Null

$mode = if ($Wsl) { "WSL2 [$Distro]" } else { "Windows-native" }
$logName = if ($Wsl) { "watchdog-wsl.log" } else { "watchdog.log" }
Write-Host "[supervisor] task '$taskName' registered ($mode; logon + every 5 min)."
Write-Host "[supervisor] logs: $repo\runtime\openclaw-jarvis\var\$logName"
