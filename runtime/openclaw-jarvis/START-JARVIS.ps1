$ErrorActionPreference = "Stop"

function ConvertTo-WslPath {
  param([Parameter(Mandatory = $true)][string]$WindowsPath)

  $resolved = (Resolve-Path -LiteralPath $WindowsPath).Path
  if ($resolved -match "^([A-Za-z]):\\(.*)$") {
    $drive = $Matches[1].ToLowerInvariant()
    $rest = $Matches[2] -replace "\\", "/"
    return "/mnt/$drive/$rest"
  }

  throw "Unsupported Windows path for WSL: $resolved"
}

function ConvertTo-BashSingleQuoted {
  param([Parameter(Mandatory = $true)][string]$Value)

  return "'" + ($Value -replace "'", "'\''") + "'"
}

$root = $PSScriptRoot
$wslRoot = ConvertTo-WslPath $root
$quotedWslRoot = ConvertTo-BashSingleQuoted $wslRoot
$wslCommand = "set -e; cd $quotedWslRoot; if [ ! -x `$HOME/.local/bin/jarvis ] || ! grep -Fq $quotedWslRoot `$HOME/.local/bin/jarvis 2>/dev/null; then ./install.sh; fi; exec `$HOME/.local/bin/jarvis chat"

Write-Host "Starting Jarvis..."
Write-Host "Home: $root"

& wsl.exe bash -lc $wslCommand

if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Jarvis stopped with an error. Run: jarvis doctor"
  pause
}
