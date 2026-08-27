[CmdletBinding()]
param(
    [string]$DestinationRoot = "",
    [switch]$UpdateExisting
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$source = Join-Path $projectRoot "integrations\musescore\SeraBridge"
if (-not (Test-Path -LiteralPath (Join-Path $source "SeraBridge.qml") -PathType Leaf)) {
    throw "SeraBridge.qml was not found under $source"
}

if ([string]::IsNullOrWhiteSpace($DestinationRoot)) {
    $documents = [Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)
    if ([string]::IsNullOrWhiteSpace($documents)) {
        throw "Windows Documents folder could not be resolved. Pass -DestinationRoot explicitly."
    }
    $DestinationRoot = Join-Path $documents "MuseScore4\Plugins"
}

$resolvedDestinationRoot = [System.IO.Path]::GetFullPath($DestinationRoot)
$destination = Join-Path $resolvedDestinationRoot "SeraBridge"
if (Test-Path -LiteralPath $destination) {
    if (-not $UpdateExisting) {
        throw "Refusing to overwrite an existing MuseScore plugin folder: $destination. Re-run with -UpdateExisting to back up and update it."
    }
    $backupName = "SeraBridge.backup_" + (Get-Date -Format "yyyyMMdd_HHmmss")
    $backup = Join-Path $resolvedDestinationRoot $backupName
    Copy-Item -LiteralPath $destination -Destination $backup -Recurse
    Copy-Item -Path (Join-Path $source "*") -Destination $destination -Recurse -Force
    Write-Host "Existing bridge backed up at: $backup"
    Write-Host "Sera MuseScore bridge updated at: $destination"
    Write-Host "Restart MuseScore Studio before testing version 0.3.3."
    exit 0
}

New-Item -ItemType Directory -Path $resolvedDestinationRoot -Force | Out-Null
Copy-Item -LiteralPath $source -Destination $destination -Recurse

Write-Host "Sera MuseScore bridge installed at: $destination"
Write-Host "Restart MuseScore Studio, then enable 'Sera Score Bridge' in Home -> Plugins."
Write-Host "The plugin expects Sera API on http://127.0.0.1:8000 by default."
