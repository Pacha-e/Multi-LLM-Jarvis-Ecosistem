param(
  [string]$HomePath = $env:USERPROFILE
)

$claudeRoot = Join-Path $HomePath ".claude"
$codexRoot = Join-Path $HomePath ".codex"
$outDir = Join-Path $codexRoot "claude-bridge"
$outFile = Join-Path $outDir "INDEX.md"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$commandsDir = Join-Path $claudeRoot "commands"
$agentsDir = Join-Path $claudeRoot "agents"

$commands = @()
$agents = @()

if (Test-Path $commandsDir) {
  $commands = Get-ChildItem -Path $commandsDir -File -Filter "*.md" | Sort-Object Name
}

if (Test-Path $agentsDir) {
  $agents = Get-ChildItem -Path $agentsDir -File -Filter "*.md" | Sort-Object Name
}

$lines = @()
$lines += "# Claude Setup Bridge Index"
$lines += ""
$lines += "Generado automaticamente desde $claudeRoot."
$lines += "Objetivo: usar .claude como fuente, y .codex como capa operativa unificada."
$lines += ""
$lines += "## Comandos disponibles (.claude/commands)"
$lines += ""
if ($commands.Count -eq 0) {
  $lines += "- (sin comandos detectados)"
} else {
  foreach ($cmd in $commands) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($cmd.Name)
    $lines += "- /$name -> $($cmd.FullName)"
  }
}

$lines += ""
$lines += "## Agentes disponibles (.claude/agents)"
$lines += ""
if ($agents.Count -eq 0) {
  $lines += "- (sin agentes detectados)"
} else {
  foreach ($agent in $agents) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($agent.Name)
    $lines += "- $name -> $($agent.FullName)"
  }
}

$lines += ""
$lines += "## Uso recomendado en Codex"
$lines += ""
$lines += "- Interpretar slash commands como intenciones."
$lines += "- Consultar archivos en .claude/commands para flujo exacto."
$lines += "- Usar .claude/agents como criterios de especialidad."
$lines += "- Mantener MCPs en .codex/config.toml como capa primaria de ejecucion."

try {
  Set-Content -Path $outFile -Value ($lines -join "`r`n") -Encoding UTF8 -ErrorAction Stop
  Write-Host "Bridge actualizado en: $outFile"
} catch {
  Write-Error "No se pudo escribir el bridge: $_"
  exit 1
}
