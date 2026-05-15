<#
Configures local CLI config files as symlinks to this repository.

This script is intentionally non-destructive: existing files are moved to a
timestamped backup only after source files are verified and symlink creation is
confirmed to be available in the current PowerShell session.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$RepoPath = "",
    [string]$UserHome = $HOME
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoPath)) {
    $ScriptRoot = if ($PSScriptRoot) {
        $PSScriptRoot
    }
    else {
        Split-Path -Parent $MyInvocation.MyCommand.Path
    }

    $RepoPath = Split-Path -Parent $ScriptRoot
}

$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
$UserHome = (Resolve-Path -LiteralPath $UserHome).Path
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

$Links = [ordered]@{
    (Join-Path $UserHome ".aider.conf.yml") = (Join-Path $RepoPath "configs\aider\.aider.conf.yml")
    (Join-Path $UserHome ".aider.model.settings.yml") = (Join-Path $RepoPath "configs\aider\.aider.model.settings.yml")
    (Join-Path $UserHome ".claude\settings.json") = (Join-Path $RepoPath "configs\claude\settings.json")
    (Join-Path $UserHome ".codex\config.toml") = (Join-Path $RepoPath "configs\codex\config.toml")
    (Join-Path $UserHome ".codex\hooks.json") = (Join-Path $RepoPath "configs\codex\hooks.json")
}

foreach ($Source in $Links.Values) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Missing source file: $Source"
    }
}

$ProbePath = Join-Path $env:TEMP "jarvis-symlink-probe-$Timestamp.tmp"
$ProbeTarget = $Links.Values | Select-Object -First 1
try {
    New-Item -ItemType SymbolicLink -Path $ProbePath -Target $ProbeTarget -Force | Out-Null
}
catch {
    throw "Cannot create symlinks in this session. Run PowerShell as Administrator or enable Windows Developer Mode. No files were changed."
}
finally {
    if (Test-Path -LiteralPath $ProbePath) {
        Remove-Item -LiteralPath $ProbePath -Force
    }
}

foreach ($Target in $Links.Keys) {
    $Source = $Links[$Target]
    $Parent = Split-Path -Parent $Target

    if (-not (Test-Path -LiteralPath $Parent -PathType Container)) {
        New-Item -ItemType Directory -Path $Parent -Force | Out-Null
    }

    $BackupPath = $null
    try {
        if (Test-Path -LiteralPath $Target) {
            $Existing = Get-Item -LiteralPath $Target -Force
            $ExistingTarget = @($Existing.Target) -join ";"

            if ($Existing.LinkType -eq "SymbolicLink" -and $ExistingTarget -eq $Source) {
                Write-Host "Already linked: $Target -> $Source"
                continue
            }

            $BackupPath = "$Target.backup-before-symlink-$Timestamp"
            if ($PSCmdlet.ShouldProcess($Target, "Move existing item to $BackupPath")) {
                Move-Item -LiteralPath $Target -Destination $BackupPath
                Write-Host "Backed up existing item: $BackupPath"
            }
        }

        if ($PSCmdlet.ShouldProcess($Target, "Create symlink to $Source")) {
            New-Item -ItemType SymbolicLink -Path $Target -Target $Source | Out-Null
            Write-Host "Linked: $Target -> $Source"
        }
    }
    catch {
        if ($BackupPath -and (Test-Path -LiteralPath $BackupPath) -and -not (Test-Path -LiteralPath $Target)) {
            Move-Item -LiteralPath $BackupPath -Destination $Target
            Write-Warning "Restored backup after failure: $Target"
        }
        throw
    }
}
