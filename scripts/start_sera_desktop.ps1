param(
    [switch]$SkipInstall,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$frontendRoot = Join-Path $projectRoot "frontend"
$electronRoot = Join-Path $projectRoot "electron"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$requirements = Join-Path $projectRoot "requirements.txt"
$electronExe = Join-Path $electronRoot "node_modules\electron\dist\electron.exe"

function Write-Step {
    param([string]$Message)
    Write-Host "[Sera Desktop] $Message"
}

function Get-PortOwner {
    return Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::", "::1") } |
        Select-Object -First 1 -ExpandProperty OwningProcess
}

function Test-DesktopBackend {
    try {
        $status = Invoke-RestMethod -Uri "http://127.0.0.1:8000/integrations/desktop/status" -TimeoutSec 2
        return [bool]$status.desktop_available
    }
    catch {
        return $false
    }
}

function Ensure-DesktopPort {
    $ownerPid = Get-PortOwner
    if (-not $ownerPid) {
        return
    }
    if (Test-DesktopBackend) {
        Write-Step "An existing Sera Desktop instance is using port 8000; requesting window focus."
        return
    }
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ownerPid" -ErrorAction SilentlyContinue
    $commandLine = [string]$processInfo.CommandLine
    if ($processInfo -and ($commandLine.Contains($projectRoot) -or $commandLine.Contains("backend.app:app"))) {
        Write-Step "Stopping the stale Sera web backend on port 8000 (PID $ownerPid)."
        Stop-Process -Id $ownerPid -Force
        Start-Sleep -Milliseconds 500
        return
    }
    throw "Port 8000 is occupied by another application (PID $ownerPid). Close it before starting Sera Desktop."
}

Write-Step "Project root: $projectRoot"
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd was not found. Install Node.js before starting Sera Desktop."
}

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    if ($SkipInstall) {
        throw "Python virtual environment is missing: $pythonExe"
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        throw "Python 3.10+ was not found."
    }
    Write-Step "Creating Python environment..."
    & $python.Source -m venv (Join-Path $projectRoot ".venv")
}

& $pythonExe -c "import fastapi, uvicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    if ($SkipInstall) {
        throw "Backend dependencies are missing. Run without -SkipInstall once."
    }
    Write-Step "Installing backend dependencies..."
    & $pythonExe -m pip install -r $requirements
}

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules") -PathType Container)) {
    if ($SkipInstall) {
        throw "Frontend dependencies are missing. Run without -SkipInstall once."
    }
    Write-Step "Installing frontend dependencies..."
    Push-Location $frontendRoot
    try { npm.cmd install }
    finally { Pop-Location }
}

if (-not $SkipBuild) {
    Write-Step "Building the local Workbench UI..."
    Push-Location $frontendRoot
    try { npm.cmd run build }
    finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "dist\index.html") -PathType Leaf)) {
    throw "Desktop frontend build is missing. Run without -SkipBuild once."
}

if (-not (Test-Path -LiteralPath $electronExe -PathType Leaf)) {
    if ($SkipInstall) {
        throw "Electron runtime is missing. Run without -SkipInstall once."
    }
    Write-Step "Installing the Electron desktop runtime..."
    Push-Location $electronRoot
    try { npm.cmd install --no-audit --no-fund }
    finally { Pop-Location }
    if (-not (Test-Path -LiteralPath $electronExe -PathType Leaf)) {
        $electronInstaller = Join-Path $electronRoot "node_modules\electron\install.js"
        if (-not (Test-Path -LiteralPath $electronInstaller -PathType Leaf)) {
            throw "Electron package is present without its installer: $electronInstaller"
        }
        Write-Step "Completing the Electron runtime download..."
        Push-Location (Split-Path -Parent $electronInstaller)
        try { node install.js }
        finally { Pop-Location }
    }
    if (-not (Test-Path -LiteralPath $electronExe -PathType Leaf)) {
        throw "Electron runtime installation did not produce: $electronExe"
    }
}

Ensure-DesktopPort
$previousBackendPort = $env:SERA_BACKEND_PORT
$previousDesktopMode = $env:SERA_DESKTOP_MODE
$env:SERA_BACKEND_PORT = "8000"
$env:SERA_DESKTOP_MODE = "1"

Write-Step "Starting the local Sera desktop window. No external browser will be opened."
Push-Location $electronRoot
try {
    npm.cmd start
}
finally {
    Pop-Location
    $env:SERA_BACKEND_PORT = $previousBackendPort
    $env:SERA_DESKTOP_MODE = $previousDesktopMode
}
