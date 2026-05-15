# Script para configurar enlaces simbólicos del ecosistema Jarvis
# Ejecutar como Administrador para crear enlaces simbólicos

$RepoPath = "C:\Users\Acer Nitro\Multi-LLM-Jarvis-Ecosistem"
$UserHome = "C:\Users\Acer Nitro"

$Links = @{
    "$UserHome\.aider.conf.yml" = "$RepoPath\configs\aider\.aider.conf.yml"
    "$UserHome\.aider.model.settings.yml" = "$RepoPath\configs\aider\.aider.model.settings.yml"
    "$UserHome\.claude\settings.json" = "$RepoPath\configs\claude\settings.json"
    "$UserHome\.codex\config.toml" = "$RepoPath\configs\codex\config.toml"
    "$UserHome\.codex\hooks.json" = "$RepoPath\configs\codex\hooks.json"
}

foreach ($Target in $Links.Keys) {
    $Source = $Links[$Target]
    
    # Asegurar que el destino no existe o borrarlo para crear el enlace
    if (Test-Path $Target) {
        Write-Host "Eliminando archivo existente: $Target"
        Remove-Item $Target -Force
    }
    
    # Crear enlace simbólico
    Write-Host "Creando enlace: $Target -> $Source"
    New-Item -ItemType SymbolicLink -Path $Target -Target $Source
}
