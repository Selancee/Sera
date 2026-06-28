param(
    [string[]]$Ports = @("8000", "5173"),
    [switch]$IncludeValidationPorts
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$MetadataDir = Join-Path $ProjectRoot "data\metadata"
$PidFiles = @(
    Join-Path $MetadataDir "sera_backend.pid"
    Join-Path $MetadataDir "sera_frontend.pid"
)
$StopPidFiles = -not $PSBoundParameters.ContainsKey("Ports")

if ($IncludeValidationPorts) {
    $Ports += @("8010", "5174")
}

function Write-Step {
    param([string]$Message)
    Write-Host "[Sera] $Message"
}

function Stop-IfSeraProcess {
    param([int]$ProcessId)
    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if (-not $processInfo) {
        return
    }
    $commandLine = [string]$processInfo.CommandLine
    $isSera = $commandLine.Contains($ProjectRoot) -or
        $commandLine.Contains("backend.app:app") -or
        ($commandLine.Contains("vite") -and $commandLine.Contains("517"))
    if (-not $isSera) {
        Write-Step "Skipped PID $ProcessId because it does not look like a Sera process."
        return
    }
    Write-Step "Stopping PID $ProcessId"
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Resolve-PortNumbers {
    param([string[]]$PortTokens)
    $resolved = New-Object System.Collections.Generic.List[int]
    foreach ($token in $PortTokens) {
        foreach ($part in ([string]$token).Split(",", [System.StringSplitOptions]::RemoveEmptyEntries)) {
            $trimmed = $part.Trim()
            $parsedPort = 0
            if ([int]::TryParse($trimmed, [ref]$parsedPort) -and $parsedPort -gt 0 -and $parsedPort -le 65535) {
                $resolved.Add($parsedPort)
            }
            else {
                Write-Step "Skipped invalid port token '$trimmed'."
            }
        }
    }
    return $resolved.ToArray()
}

if ($StopPidFiles) {
    foreach ($pidFile in $PidFiles) {
        if (Test-Path -LiteralPath $pidFile) {
            $pidText = (Get-Content -LiteralPath $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1)
            $parsedPid = 0
            if ([int]::TryParse($pidText, [ref]$parsedPid)) {
                Stop-IfSeraProcess -ProcessId $parsedPid
            }
            Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        }
    }
}

$PortNumbers = Resolve-PortNumbers -PortTokens $Ports
foreach ($port in ($PortNumbers | Select-Object -Unique)) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        Stop-IfSeraProcess -ProcessId $connection.OwningProcess
    }
}

Write-Step "Stop request complete."
