# install-jarvis-supervisor.ps1 — register the Jarvis 24/7 watchdog in Task Scheduler.
# Run once in an elevated-or-normal PowerShell. Idempotent: re-running re-registers.
#
#   Register:    powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1
#   Uninstall:   powershell -ExecutionPolicy Bypass -File install-jarvis-supervisor.ps1 -Uninstall
#
# Task runs jarvis-watchdog.ps1 at logon + every 5 minutes (current user, no admin needed).
# Does NOT store credentials. Runs only while the user is logged on.

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$taskName  = "JarvisSupervisor"
$repo      = Split-Path -Parent $PSScriptRoot
$watchdog  = Join-Path $repo "scripts\jarvis-watchdog.ps1"

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

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdog`""

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

Write-Host "[supervisor] task '$taskName' registered (logon + every 5 min)."
Write-Host "[supervisor] logs: $repo\runtime\openclaw-jarvis\var\watchdog.log"
