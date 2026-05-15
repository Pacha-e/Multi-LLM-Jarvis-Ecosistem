param(
  [string]$HomePath = $env:USERPROFILE,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-ValidSkillFile {
  param([string]$SkillFile)
  if (-not (Test-Path $SkillFile)) { return $false }
  $raw = Get-Content -Raw -Path $SkillFile
  if ([string]::IsNullOrWhiteSpace($raw)) { return $false }
  if (-not $raw.StartsWith("---")) { return $false }
  $parts = $raw -split "`r?`n---`r?`n", 3
  return ($parts.Count -ge 2)
}

function Get-FileHashSafe {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return "" }
  return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

function Get-DirectorySignature {
  param([string]$DirPath)
  if (-not (Test-Path $DirPath)) { return "" }
  $files = Get-ChildItem -Path $DirPath -File -Recurse | Sort-Object FullName
  $parts = @()
  foreach ($f in $files) {
    $h = (Get-FileHash -Path $f.FullName -Algorithm SHA256).Hash
    $parts += ("{0}|{1}" -f $f.FullName.Substring($DirPath.Length), $h)
  }
  $joined = $parts -join "`n"
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($joined)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
  } finally {
    $sha.Dispose()
  }
}

$claudeSkills = Join-Path $HomePath ".claude\skills"
$codexSkills = Join-Path $HomePath ".codex\skills"
$reportPath = Join-Path $HomePath ".llm-ecosystem\skills-sync-report.json"

if (-not (Test-Path $claudeSkills)) { throw "No existe $claudeSkills" }
if (-not (Test-Path $codexSkills)) { New-Item -ItemType Directory -Path $codexSkills | Out-Null }

$sourceDirs = Get-ChildItem -Path $claudeSkills -Directory | Sort-Object Name
$synced = @()
$skipped = @()

foreach ($dir in $sourceDirs) {
  $skillFile = Join-Path $dir.FullName "SKILL.md"
  if (-not (Test-ValidSkillFile -SkillFile $skillFile)) {
    $skipped += @{
      name = $dir.Name
      reason = "missing_or_invalid_frontmatter"
    }
    continue
  }

  $destDir = Join-Path $codexSkills $dir.Name
  $destSkillFile = Join-Path $destDir "SKILL.md"

  $srcHash = Get-DirectorySignature -DirPath $dir.FullName
  $dstHash = Get-DirectorySignature -DirPath $destDir
  $action = "none"

  if (-not (Test-Path $destDir)) {
    $action = "create"
    if (-not $DryRun) {
      Copy-Item -Path $dir.FullName -Destination $destDir -Recurse -Force
    }
  } elseif ($srcHash -ne $dstHash) {
    $action = "update"
    if (-not $DryRun) {
      Remove-Item -Path $destDir -Recurse -Force
      Copy-Item -Path $dir.FullName -Destination $destDir -Recurse -Force
    }
  }

  $synced += @{
    name = $dir.Name
    action = $action
  }
}

$summary = @{
  dryRun = [bool]$DryRun
  sourceCount = $sourceDirs.Count
  syncedCount = @($synced | Where-Object { $_.action -ne "none" }).Count
  unchangedCount = @($synced | Where-Object { $_.action -eq "none" }).Count
  skippedCount = $skipped.Count
  synced = $synced
  skipped = $skipped
}

$json = $summary | ConvertTo-Json -Depth 10
$safeJson = [regex]::Replace($json, '[\uD800-\uDFFF]', '?')
Set-Content -Path $reportPath -Value $safeJson -Encoding UTF8

Write-Host "=== Skills Sync Claude -> Codex ==="
Write-Host "DryRun:      $([bool]$DryRun)"
Write-Host "Source total: $($sourceDirs.Count)"
Write-Host "Synced:       $($summary.syncedCount)"
Write-Host "Unchanged:    $($summary.unchangedCount)"
Write-Host "Skipped:      $($summary.skippedCount)"
Write-Host "Report:       $reportPath"
