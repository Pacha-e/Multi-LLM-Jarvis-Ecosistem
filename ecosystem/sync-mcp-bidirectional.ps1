param(
  [string]$HomePath = $env:USERPROFILE,
  [ValidateSet("both", "claude-to-codex", "codex-to-claude")]
  [string]$Direction = "both",
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Load-JsonOrEmpty {
  param([string]$Path)
  if (-not (Test-Path $Path)) { return @{} }
  $raw = Get-Content -Raw -Path $Path
  if ([string]::IsNullOrWhiteSpace($raw)) { return @{} }
  $parsed = $raw | ConvertFrom-Json
  return ConvertTo-Hashtable -InputObject $parsed
}

function ConvertTo-Hashtable {
  param([Parameter(ValueFromPipeline = $true)]$InputObject)

  if ($null -eq $InputObject) { return $null }

  if ($InputObject -is [System.Collections.IDictionary]) {
    $h = @{}
    foreach ($k in $InputObject.Keys) {
      $h[$k] = ConvertTo-Hashtable -InputObject $InputObject[$k]
    }
    return $h
  }

  if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
    $list = @()
    foreach ($item in $InputObject) {
      $list += (ConvertTo-Hashtable -InputObject $item)
    }
    return ,$list
  }

  if ($InputObject -is [pscustomobject]) {
    $h = @{}
    foreach ($p in $InputObject.PSObject.Properties) {
      $h[$p.Name] = ConvertTo-Hashtable -InputObject $p.Value
    }
    return $h
  }

  return $InputObject
}

function To-NormalizedName {
  param([string]$Name, [hashtable]$AliasMap)
  if ($AliasMap.ContainsKey($Name)) { return [string]$AliasMap[$Name] }
  return $Name
}

function Parse-ArgsArray {
  param([string]$ArgsLiteral)
  $items = @()
  $matches = [regex]::Matches($ArgsLiteral, "'([^']*)'|`"([^`"]*)`"")
  foreach ($m in $matches) {
    if ($m.Groups[1].Success) { $items += $m.Groups[1].Value }
    elseif ($m.Groups[2].Success) { $items += $m.Groups[2].Value }
  }
  return @($items)
}

function Parse-InlineMap {
  param([string]$Literal)
  $map = @{}
  $matches = [regex]::Matches($Literal, "([A-Za-z_][A-Za-z0-9_]*)\s*=\s*'([^']*)'|([A-Za-z_][A-Za-z0-9_]*)\s*=\s*`"([^`"]*)`"")
  foreach ($m in $matches) {
    if ($m.Groups[1].Success) { $map[$m.Groups[1].Value] = $m.Groups[2].Value }
    elseif ($m.Groups[3].Success) { $map[$m.Groups[3].Value] = $m.Groups[4].Value }
  }
  return $map
}

function Get-CodexServers {
  param([string]$Path)
  $servers = @{}
  if (-not (Test-Path $Path)) { return $servers }

  $lines = Get-Content -Path $Path
  $currentName = $null
  $blockLines = @()

  function Flush-Block {
    param([string]$Name, [string[]]$Block)
    if ([string]::IsNullOrWhiteSpace($Name)) { return }
    $obj = @{
      name = $Name
      source = "codex"
    }
    foreach ($line in $Block) {
      if ($line -match "^\s*url\s*=\s*`"([^`"]+)`"\s*$") {
        $obj["url"] = $Matches[1]
      } elseif ($line -match "^\s*command\s*=\s*'([^']+)'\s*$") {
        $obj["command"] = $Matches[1]
      } elseif ($line -match "^\s*command\s*=\s*`"([^`"]+)`"\s*$") {
        $obj["command"] = $Matches[1]
      } elseif ($line -match "^\s*args\s*=\s*(\[.*\])\s*$") {
        $obj["args"] = Parse-ArgsArray -ArgsLiteral $Matches[1]
      } elseif ($line -match "^\s*env\s*=\s*(\{.*\})\s*$") {
        $obj["env"] = Parse-InlineMap -Literal $Matches[1]
      }
    }
    $servers[$Name] = $obj
  }

  foreach ($line in $lines) {
    if ($line -match '^\[mcp_servers\."?([^"\]]+)"?\]\s*$') {
      Flush-Block -Name $currentName -Block $blockLines
      $currentName = $Matches[1]
      $blockLines = @($line)
    } elseif ($null -ne $currentName) {
      if ($line -match '^\[[^\]]+\]\s*$') {
        Flush-Block -Name $currentName -Block $blockLines
        $currentName = $null
        $blockLines = @()
      } else {
        $blockLines += $line
      }
    }
  }
  Flush-Block -Name $currentName -Block $blockLines
  return $servers
}

function To-CodexBlock {
  param([string]$Name, [hashtable]$Server)
  $safeName = if ($Name -match "^[A-Za-z0-9_]+$") { $Name } else { '"' + $Name + '"' }
  $out = @()
  $out += ""
  $out += "[mcp_servers.$safeName]"

  if ($Server.ContainsKey("url") -and -not [string]::IsNullOrWhiteSpace([string]$Server["url"])) {
    $out += "url = `"$($Server["url"])`""
    $out += "default_tools_approval_mode = `"prompt`""
    return ($out -join "`r`n")
  }

  if ($Server.ContainsKey("command")) {
    $out += "command = '$($Server["command"])'"
  }

  if ($Server.ContainsKey("args")) {
    $argsPieces = @()
    foreach ($a in @($Server["args"])) {
      $escaped = ([string]$a).Replace('"', '\"')
      $argsPieces += "`"$escaped`""
    }
    $out += "args = [" + ($argsPieces -join ", ") + "]"
  }

  if ($Server.ContainsKey("env")) {
    $envPieces = @()
    foreach ($k in @($Server["env"].Keys | Sort-Object)) {
      $v = ([string]$Server["env"][$k]).Replace('"', '\"')
      $envPieces += "$k = `"$v`""
    }
    if ($envPieces.Count -gt 0) {
      $out += "env = { " + ($envPieces -join ", ") + " }"
    }
  }

  $out += "default_tools_approval_mode = `"prompt`""
  $out += "startup_timeout_sec = 60"
  $out += "tool_timeout_sec = 180"
  return ($out -join "`r`n")
}

function To-ClaudeServer {
  param([hashtable]$Server)
  if ($Server.ContainsKey("url")) {
    return @{
      type = "http"
      url = [string]$Server["url"]
    }
  }
  $obj = @{
    type = "stdio"
    command = [string]$Server["command"]
    args = @($Server["args"])
  }
  if ($Server.ContainsKey("env") -and $Server["env"].Count -gt 0) {
    $obj["env"] = $Server["env"]
  } else {
    $obj["env"] = @{}
  }
  return $obj
}

$claudeJsonPath = Join-Path $HomePath ".claude.json"
$codexTomlPath = Join-Path $HomePath ".codex\config.toml"
$aliasPath = Join-Path $HomePath ".llm-ecosystem\mcp-alias-map.json"

$aliasJson = Load-JsonOrEmpty -Path $aliasPath
$aliasMap = @{}
foreach ($k in $aliasJson.Keys) {
  if ($k -ne "_comment") { $aliasMap[$k] = [string]$aliasJson[$k] }
}

$claudeJson = Load-JsonOrEmpty -Path $claudeJsonPath
if (-not $claudeJson.ContainsKey("mcpServers")) { $claudeJson["mcpServers"] = @{} }
$claudeServersRaw = $claudeJson["mcpServers"]
$codexServersRaw = Get-CodexServers -Path $codexTomlPath

$claudeNormalized = @{}
foreach ($k in $claudeServersRaw.Keys) {
  $n = To-NormalizedName -Name $k -AliasMap $aliasMap
  if (-not $claudeNormalized.ContainsKey($n)) {
    $claudeNormalized[$n] = [hashtable]$claudeServersRaw[$k]
  }
}

$codexNormalized = @{}
foreach ($k in $codexServersRaw.Keys) {
  $n = To-NormalizedName -Name $k -AliasMap $aliasMap
  if (-not $codexNormalized.ContainsKey($n)) {
    $codexNormalized[$n] = [hashtable]$codexServersRaw[$k]
  }
}

$toCodex = @()
$toClaude = @()

if ($Direction -in @("both", "claude-to-codex")) {
  foreach ($name in $claudeNormalized.Keys) {
    if (-not $codexNormalized.ContainsKey($name)) {
      $toCodex += $name
    }
  }
}

if ($Direction -in @("both", "codex-to-claude")) {
  foreach ($name in $codexNormalized.Keys) {
    if (-not $claudeNormalized.ContainsKey($name)) {
      $toClaude += $name
    }
  }
}

$toCodex = @($toCodex | Sort-Object -Unique)
$toClaude = @($toClaude | Sort-Object -Unique)

Write-Host "=== MCP Bidirectional Sync ==="
Write-Host "Direction: $Direction"
Write-Host "DryRun:    $([bool]$DryRun)"
Write-Host "To Codex:  $($toCodex.Count)"
Write-Host "To Claude: $($toClaude.Count)"

if ($toCodex.Count -gt 0) {
  Write-Host ("Missing in Codex:  " + ($toCodex -join ", "))
}
if ($toClaude.Count -gt 0) {
  Write-Host ("Missing in Claude: " + ($toClaude -join ", "))
}

if ($DryRun) { exit 0 }

if ($toCodex.Count -gt 0) {
  $codexBackup = "$codexTomlPath.bak-sync-" + (Get-Date -Format "yyyyMMdd-HHmmss")
  Copy-Item -Path $codexTomlPath -Destination $codexBackup -Force
  $append = @()
  foreach ($name in $toCodex) {
    $append += (To-CodexBlock -Name $name -Server $claudeNormalized[$name])
  }
  Add-Content -Path $codexTomlPath -Value ($append -join "`r`n")
  Write-Host "Updated Codex config. Backup: $codexBackup"
}

if ($toClaude.Count -gt 0) {
  $claudeBackup = "$claudeJsonPath.bak-sync-" + (Get-Date -Format "yyyyMMdd-HHmmss")
  Copy-Item -Path $claudeJsonPath -Destination $claudeBackup -Force
  foreach ($name in $toClaude) {
    $claudeJson["mcpServers"][$name] = To-ClaudeServer -Server $codexNormalized[$name]
  }
  $jsonOut = $claudeJson | ConvertTo-Json -Depth 100
  Set-Content -Path $claudeJsonPath -Value $jsonOut -Encoding UTF8
  Write-Host "Updated Claude config. Backup: $claudeBackup"
}

Write-Host "Sync complete."
