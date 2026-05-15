param(
  [string]$HomePath = $env:USERPROFILE
)

function Test-JsonPath {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    return $null
  }
  try {
    return Get-Content -Raw -Path $Path | ConvertFrom-Json
  } catch {
    return $null
  }
}

function Get-ServerNames {
  param($Obj, [string]$PropName)
  if ($null -eq $Obj) { return @() }
  if ($null -eq $Obj.$PropName) { return @() }
  return @($Obj.$PropName.PSObject.Properties.Name)
}

$claudeJsonPath = Join-Path $HomePath ".claude.json"
$mcpJsonPath = Join-Path $HomePath ".mcp.json"
$codexTomlPath = Join-Path $HomePath ".codex\config.toml"
$aliasMapPath = Join-Path $HomePath ".llm-ecosystem\mcp-alias-map.json"

$claudeJson = Test-JsonPath -Path $claudeJsonPath
$mcpJson = Test-JsonPath -Path $mcpJsonPath

$claudeServers = Get-ServerNames -Obj $claudeJson -PropName "mcpServers"
$mcpServers = Get-ServerNames -Obj $mcpJson -PropName "mcpServers"

$aliasMap = @{}
$aliasJson = Test-JsonPath -Path $aliasMapPath
if ($null -ne $aliasJson) {
  foreach ($p in $aliasJson.PSObject.Properties) {
    $aliasMap[$p.Name] = [string]$p.Value
  }
}

function Normalize-ServerNames {
  param([string[]]$Names, $Map)
  $normalized = @()
  foreach ($n in $Names) {
    if ($Map.ContainsKey($n)) {
      $normalized += $Map[$n]
    } else {
      $normalized += $n
    }
  }
  return @($normalized | Sort-Object -Unique)
}

$codexServers = @()
if (Test-Path $codexTomlPath) {
  $content = Get-Content -Raw -Path $codexTomlPath
  $tomlMatches = [regex]::Matches($content, '^\[mcp_servers\."?([^"\]]+)"?\]', "Multiline")
  $codexServers = $tomlMatches | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
}

$claudeServers = Normalize-ServerNames -Names $claudeServers -Map $aliasMap
$mcpServers = Normalize-ServerNames -Names $mcpServers -Map $aliasMap
$codexServers = Normalize-ServerNames -Names $codexServers -Map $aliasMap

$all = @($claudeServers + $mcpServers + $codexServers) | Sort-Object -Unique

Write-Host "=== MCP Health Snapshot ==="
Write-Host "Claude (.claude.json): $($claudeServers.Count)"
Write-Host "Shared (.mcp.json):   $($mcpServers.Count)"
Write-Host "Codex (config.toml):  $($codexServers.Count)"
Write-Host ""

foreach ($name in $all) {
  $inClaude = $claudeServers -contains $name
  $inMcp = $mcpServers -contains $name
  $inCodex = $codexServers -contains $name

  $status = "{0,-16} | Claude:{1} Shared:{2} Codex:{3}" -f `
    $name, `
    ($(if ($inClaude) { "Y" } else { "-" })), `
    ($(if ($inMcp) { "Y" } else { "-" })), `
    ($(if ($inCodex) { "Y" } else { "-" }))

  Write-Host $status
}

Write-Host ""
Write-Host "Tip: servers missing in one layer are candidates for integration."
