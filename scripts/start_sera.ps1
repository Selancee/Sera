param(
    [string]$HostName = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$MetadataDir = Join-Path $ProjectRoot "data\metadata"
$BackendLog = Join-Path $MetadataDir "sera_backend.out.log"
$BackendErr = Join-Path $MetadataDir "sera_backend.err.log"
$FrontendLog = Join-Path $MetadataDir "sera_frontend.out.log"
$FrontendErr = Join-Path $MetadataDir "sera_frontend.err.log"
$BackendPidFile = Join-Path $MetadataDir "sera_backend.pid"
$FrontendPidFile = Join-Path $MetadataDir "sera_frontend.pid"
$BackendStamp = Join-Path $MetadataDir ".backend_deps.stamp"
$FrontendStamp = Join-Path $MetadataDir ".frontend_deps.stamp"
$DefaultModelDir = Join-Path $ProjectRoot "models\sera_symbolic_small"

New-Item -ItemType Directory -Force -Path $MetadataDir | Out-Null

function Write-Step {
    param([string]$Message)
    Write-Host "[Sera] $Message"
}

function Test-PortOpen {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @($HostName, "0.0.0.0", "::", "::1") } |
        Select-Object -First 1
    return $null -ne $connection
}

function Get-PortOwnerProcesses {
    param([int]$Port)
    return @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @($HostName, "0.0.0.0", "::", "::1") } |
        Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-SeraProcess {
    param([int]$ProcessId)
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if (-not $processInfo) {
        return $false
    }
    $commandLine = [string]$processInfo.CommandLine
    return ($commandLine.Contains($ProjectRoot) -or
        $commandLine.Contains("backend.app:app") -or
        ($commandLine.Contains("vite") -and $commandLine.Contains($FrontendRoot)))
}

function Stop-SeraProcess {
    param([int]$ProcessId)
    if (-not (Test-SeraProcess -ProcessId $ProcessId)) {
        return $false
    }
    Write-Step "Stopping stale Sera process PID $ProcessId"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 500
    return $true
}

function Stop-SeraProcessesOnPort {
    param([int]$Port)
    $stopped = $false
    foreach ($ownerPid in Get-PortOwnerProcesses -Port $Port) {
        $stopped = (Stop-SeraProcess -ProcessId $ownerPid) -or $stopped
    }
    return $stopped
}

function Wait-ForPortFree {
    param([int]$Port)
    for ($i = 0; $i -lt 20; $i++) {
        if (-not (Test-PortOpen -Port $Port)) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    }
    return (-not (Test-PortOpen -Port $Port))
}

function Find-FreePort {
    param([int]$StartPort)
    for ($port = $StartPort; $port -lt ($StartPort + 30); $port++) {
        if (-not (Test-PortOpen -Port $port)) {
            return $port
        }
    }
    throw "No free port found from $StartPort to $($StartPort + 29)."
}

function Test-SeraBackend {
    param([int]$Port)
    try {
        $health = Invoke-RestMethod -Uri "http://$HostName`:$Port/health" -TimeoutSec 2
        if ($health.app -ne "Sera") {
            return $false
        }
        $openApi = Invoke-RestMethod -Uri "http://$HostName`:$Port/openapi.json" -TimeoutSec 3
        $paths = @($openApi.paths.PSObject.Properties.Name)
        # TODO: Replace this capability probe with a dedicated API version endpoint if Sera exposes one.
        return ($paths -contains "/rate")
    }
    catch {
        return $false
    }
}

function Test-SeraBackendModelEnvironment {
    param([int]$Port)
    try {
        $status = Invoke-RestMethod -Uri "http://$HostName`:$Port/model/status" -TimeoutSec 2
        if ([string]$status.generator_backend -ne [string]$env:SERA_GENERATOR_BACKEND) {
            return $false
        }
        if (-not [string]::IsNullOrWhiteSpace($env:SERA_SYMBOLIC_MODEL_CHECKPOINT)) {
            return $true
        }
        return ([string]$status.expected_model_dir -eq [string]$env:SERA_SYMBOLIC_MODEL_DIR)
    }
    catch {
        return $false
    }
}

function Test-FrontendReady {
    param([int]$Port)
    try {
        $response = Invoke-WebRequest -Uri "http://$HostName`:$Port" -UseBasicParsing -TimeoutSec 2
        return ($response.StatusCode -eq 200 -and $response.Content.Contains("root"))
    }
    catch {
        return $false
    }
}

function Ensure-BackendEnvironment {
    $venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw "Python was not found on PATH. Install Python 3.10+ or create .venv manually."
        }
        Write-Step "Creating Python virtual environment..."
        & $python.Source -m venv (Join-Path $ProjectRoot ".venv")
    }

    Write-Step "Checking Python packaging tools..."
    & $venvPython -m pip --version *> $null
    if ($LASTEXITCODE -ne 0) {
        & $venvPython -m ensurepip --upgrade | Out-Null
    }

    $requirements = Join-Path $ProjectRoot "requirements.txt"
    $needsInstall = -not (Test-Path -LiteralPath $BackendStamp)
    if ((Test-Path -LiteralPath $BackendStamp) -and (Test-Path -LiteralPath $requirements)) {
        $needsInstall = (Get-Item -LiteralPath $requirements).LastWriteTimeUtc -gt (Get-Item -LiteralPath $BackendStamp).LastWriteTimeUtc
    }
    if ($SkipInstall) {
        $needsInstall = $false
    }
    if ($needsInstall) {
        Write-Step "Installing backend dependencies..."
        & $venvPython -m pip install -r $requirements
        Set-Content -LiteralPath $BackendStamp -Value (Get-Date).ToString("o") -Encoding ASCII
    }
    return $venvPython
}

function Ensure-FrontendEnvironment {
    if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw "npm.cmd was not found on PATH. Install Node.js before launching the frontend."
    }
    $nodeModules = Join-Path $FrontendRoot "node_modules"
    $packageLock = Join-Path $FrontendRoot "package-lock.json"
    $needsInstall = -not (Test-Path -LiteralPath $nodeModules)
    if ((Test-Path -LiteralPath $FrontendStamp) -and (Test-Path -LiteralPath $packageLock)) {
        $needsInstall = $needsInstall -or ((Get-Item -LiteralPath $packageLock).LastWriteTimeUtc -gt (Get-Item -LiteralPath $FrontendStamp).LastWriteTimeUtc)
    }
    if (-not (Test-Path -LiteralPath $FrontendStamp)) {
        $needsInstall = $true
    }
    if ($SkipInstall) {
        $needsInstall = $false
    }
    if ($needsInstall) {
        Write-Step "Installing frontend dependencies..."
        Push-Location $FrontendRoot
        try {
            npm.cmd install
        }
        finally {
            Pop-Location
        }
        Set-Content -LiteralPath $FrontendStamp -Value (Get-Date).ToString("o") -Encoding ASCII
    }
}

function Configure-ModelEnvironment {
    if ([string]::IsNullOrWhiteSpace($env:SERA_ACTIVE_SYMBOLIC_MODEL)) {
        $env:SERA_ACTIVE_SYMBOLIC_MODEL = "sera_symbolic_small"
    }
    if ([string]::IsNullOrWhiteSpace($env:SERA_SYMBOLIC_MODEL_DIR) -and
        [string]::IsNullOrWhiteSpace($env:SERA_SYMBOLIC_MODEL_CHECKPOINT)) {
        $env:SERA_SYMBOLIC_MODEL_DIR = $DefaultModelDir
    }
    if ([string]::IsNullOrWhiteSpace($env:SERA_GENERATOR_BACKEND)) {
        $env:SERA_GENERATOR_BACKEND = "model"
    }
    Write-Step "Active symbolic model: $env:SERA_ACTIVE_SYMBOLIC_MODEL"
    Write-Step "Symbolic model directory: $env:SERA_SYMBOLIC_MODEL_DIR"
    Write-Step "Generator backend: $env:SERA_GENERATOR_BACKEND"
    # TODO: add a visible launcher warning when PyTorch is missing but a
    # checkpoint is present; the API currently reports that state via
    # /model/status.
}

function Start-Backend {
    param([string]$PythonExe, [int]$Port)
    if (Test-PortOpen -Port $Port) {
        if (Test-SeraBackend -Port $Port) {
            if (Test-SeraBackendModelEnvironment -Port $Port) {
                Write-Step "Backend already running on http://$HostName`:$Port"
                return $Port
            }
            Write-Step "Backend is running with stale model settings; restarting it."
            Stop-SeraProcessesOnPort -Port $Port | Out-Null
            if (-not (Wait-ForPortFree -Port $Port)) {
                $Port = Find-FreePort -StartPort ($Port + 1)
                Write-Step "Requested backend port is still busy; using $Port."
            }
        }
        else {
            Write-Step "Backend port $Port has an old or incompatible service."
            Stop-SeraProcessesOnPort -Port $Port | Out-Null
            if (-not (Wait-ForPortFree -Port $Port)) {
                $Port = Find-FreePort -StartPort ($Port + 1)
                Write-Step "Requested backend port is still busy; using $Port."
            }
        }
    }

    Write-Step "Starting backend on http://$HostName`:$Port ..."
    $process = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList @("-m", "uvicorn", "backend.app:app", "--host", $HostName, "--port", [string]$Port) `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErr `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $BackendPidFile -Value $process.Id -Encoding ASCII

    for ($i = 0; $i -lt 40; $i++) {
        if (Test-SeraBackend -Port $Port) {
            Write-Step "Backend ready."
            return $Port
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Backend did not become ready. See $BackendErr"
}

function Start-Frontend {
    param([int]$Port, [string]$BackendUrl)
    if (Test-PortOpen -Port $Port) {
        Write-Step "Frontend port $Port is already in use; refreshing Sera frontend if possible."
        Stop-SeraProcessesOnPort -Port $Port | Out-Null
        if (-not (Wait-ForPortFree -Port $Port)) {
            $Port = Find-FreePort -StartPort ($Port + 1)
            Write-Step "Requested frontend port is still busy; using $Port."
        }
    }

    Write-Step "Starting frontend on http://$HostName`:$Port ..."
    $runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $frontendRunLog = Join-Path $MetadataDir "sera_frontend_$Port`_$runStamp.out.log"
    $frontendRunErr = Join-Path $MetadataDir "sera_frontend_$Port`_$runStamp.err.log"
    $command = "set VITE_API_BASE_URL=$BackendUrl&& npm.cmd run dev -- --host $HostName --port $Port --strictPort"
    $process = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList @("/c", $command) `
        -WorkingDirectory $FrontendRoot `
        -RedirectStandardOutput $frontendRunLog `
        -RedirectStandardError $frontendRunErr `
        -WindowStyle Hidden `
        -PassThru
    Set-Content -LiteralPath $FrontendPidFile -Value $process.Id -Encoding ASCII

    for ($i = 0; $i -lt 40; $i++) {
        if (Test-FrontendReady -Port $Port) {
            Write-Step "Frontend ready."
            return $Port
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Frontend did not become ready. See $frontendRunErr"
}

Write-Step "Project root: $ProjectRoot"
$PythonExe = Ensure-BackendEnvironment
Ensure-FrontendEnvironment
Configure-ModelEnvironment

$ActualBackendPort = Start-Backend -PythonExe $PythonExe -Port $BackendPort
$BackendUrl = "http://$HostName`:$ActualBackendPort"
$ActualFrontendPort = Start-Frontend -Port $FrontendPort -BackendUrl $BackendUrl
$FrontendUrl = "http://$HostName`:$ActualFrontendPort"

Write-Host ""
Write-Host "Sera is ready."
Write-Host "Frontend: $FrontendUrl"
Write-Host "Backend:  $BackendUrl/docs"
Write-Host "Logs:     $MetadataDir"
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}
