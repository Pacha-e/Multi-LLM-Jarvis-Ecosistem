param(
  [string]$HomePath = $env:USERPROFILE
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Load-JsonOrEmpty {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return @{} }
  $raw = Get-Content -Raw -Path $Path
  if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
  return $raw | ConvertFrom-Json
}

function Normalize-Name {
  param([string]$Name)
  return (($Name -replace "[-_\s]", "")).ToLowerInvariant()
}

$claudePluginsRoot = Join-Path $HomePath ".claude\plugins\marketplaces"
$codexPluginsRoot = Join-Path $HomePath ".codex\.tmp\plugins\plugins"
$claudeJsonPath = Join-Path $HomePath ".claude.json"
$codexTomlPath = Join-Path $HomePath ".codex\config.toml"

$outJson = Join-Path $HomePath ".llm-ecosystem\plugin-map.json"
$outMd = Join-Path $HomePath ".llm-ecosystem\plugin-map.md"
$outDir = Split-Path -Parent $outJson
if (-not (Test-Path $outDir)) {
  New-Item -ItemType Directory -Path $outDir | Out-Null
}

$claudePlugins = @()
if (Test-Path $claudePluginsRoot) {
  $marketplaces = Get-ChildItem -Path $claudePluginsRoot -Directory
  foreach ($m in $marketplaces) {
    $pluginsPath = Join-Path $m.FullName "plugins"
    if (Test-Path $pluginsPath) {
      $claudePlugins += Get-ChildItem -Path $pluginsPath -Directory | ForEach-Object { $_.Name }
    }
  }
}
$claudePlugins = @($claudePlugins | Sort-Object -Unique)

$codexPlugins = @()
if (Test-Path $codexPluginsRoot) {
  $codexPlugins = @(Get-ChildItem -Path $codexPluginsRoot -Directory | ForEach-Object { $_.Name } | Sort-Object -Unique)
}

$claudeJson = Load-JsonOrEmpty -Path $claudeJsonPath
$claudeMcp = @()
if ($null -ne $claudeJson.mcpServers) {
  $claudeMcp = @($claudeJson.mcpServers.PSObject.Properties.Name | Sort-Object -Unique)
}

$codexMcp = @()
if (Test-Path $codexTomlPath) {
  $content = Get-Content -Raw -Path $codexTomlPath
  $tomlMatches = [regex]::Matches($content, '^\[mcp_servers\.(?:"([^"]+)"|([^\]]+))\]', "Multiline")
  $codexMcp = @($tomlMatches | ForEach-Object { if ($_.Groups[1].Success) { $_.Groups[1].Value } else { $_.Groups[2].Value } } | Sort-Object -Unique)
}

$codexNorm = @{}
foreach ($p in $codexPlugins) { $codexNorm[(Normalize-Name $p)] = $p }
$codexMcpNorm = @{}
foreach ($m in $codexMcp) { $codexMcpNorm[(Normalize-Name $m)] = $m }

$rows = @()
foreach ($p in $claudePlugins) {
  $n = Normalize-Name $p
  $mappedCodexPlugin = $null
  $mappedCodexMcp = $null
  if ($codexNorm.ContainsKey($n)) { $mappedCodexPlugin = $codexNorm[$n] }
  if ($codexMcpNorm.ContainsKey($n)) { $mappedCodexMcp = $codexMcpNorm[$n] }

  $status = "unmapped"
  if ($mappedCodexPlugin -and $mappedCodexMcp) { $status = "plugin_and_mcp" }
  elseif ($mappedCodexPlugin) { $status = "plugin_only" }
  elseif ($mappedCodexMcp) { $status = "mcp_only" }

  $rows += [pscustomobject]@{
    claudePlugin = $p
    codexPlugin = $mappedCodexPlugin
    codexMcp = $mappedCodexMcp
    status = $status
  }
}

$summary = [pscustomobject]@{
  generatedAt = (Get-Date).ToString("s")
  claudePlugins = $claudePlugins.Count
  codexPlugins = $codexPlugins.Count
  claudeMcp = $claudeMcp.Count
  codexMcp = $codexMcp.Count
  mappedPluginAndMcp = @($rows | Where-Object { $_.status -eq "plugin_and_mcp" }).Count
  mappedPluginOnly = @($rows | Where-Object { $_.status -eq "plugin_only" }).Count
  mappedMcpOnly = @($rows | Where-Object { $_.status -eq "mcp_only" }).Count
  unmapped = @($rows | Where-Object { $_.status -eq "unmapped" }).Count
}

[pscustomobject]@{
  summary = $summary
  rows = $rows
} | ConvertTo-Json -Depth 6 | Set-Content -Path $outJson -Encoding UTF8

$md = @()
$md += "# Plugin Map (Claude -> Codex)"
$md += ""
$md += "- Generated: $($summary.generatedAt)"
$md += "- Claude plugins: $($summary.claudePlugins)"
$md += "- Codex plugins: $($summary.codexPlugins)"
$md += "- Claude MCP: $($summary.claudeMcp)"
$md += "- Codex MCP: $($summary.codexMcp)"
$md += "- plugin_and_mcp: $($summary.mappedPluginAndMcp)"
$md += "- plugin_only: $($summary.mappedPluginOnly)"
$md += "- mcp_only: $($summary.mappedMcpOnly)"
$md += "- unmapped: $($summary.unmapped)"
$md += ""
$md += "| Claude plugin | Codex plugin | Codex MCP | Status |"
$md += "|---|---|---|---|"
foreach ($r in $rows | Sort-Object claudePlugin) {
  $c = ([string]$r.claudePlugin).Replace("|", "\|")
  $p = ([string]$r.codexPlugin).Replace("|", "\|")
  $m = ([string]$r.codexMcp).Replace("|", "\|")
  $s = ([string]$r.status).Replace("|", "\|")
  $md += "| $c | $p | $m | $s |"
}
Set-Content -Path $outMd -Value ($md -join "`r`n") -Encoding UTF8

Write-Host "Plugin map generated:"
Write-Host "- $outJson"
Write-Host "- $outMd"
