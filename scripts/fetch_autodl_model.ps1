param(
    [Parameter(Mandatory = $true)]
    [string]$SshTarget,
    [int]$Port = 22,
    [string]$RemoteRunDir = "/root/autodl-tmp/sera_runs/autodl_fast_20260628_221042",
    [string]$ModelName = "sera_symbolic_small",
    [string]$Destination,
    [string]$IdentityFile = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path $ProjectRoot "models\$ModelName"
}

if (-not (Get-Command scp.exe -ErrorAction SilentlyContinue)) {
    throw "scp.exe was not found. Install OpenSSH Client or copy model.pt manually."
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$scpBaseArgs = @()
if ($Port -ne 22) {
    $scpBaseArgs += @("-P", [string]$Port)
}
if (-not [string]::IsNullOrWhiteSpace($IdentityFile)) {
    $scpBaseArgs += @("-i", $IdentityFile)
}

$requiredFiles = @("model.pt", "vocab.json")
$optionalFiles = @("training_metrics.json", "samples.json", "train.log", "baseline_score_eval.json")

foreach ($fileName in $requiredFiles) {
    $remote = "${SshTarget}:$RemoteRunDir/$fileName"
    Write-Host "[Sera] Downloading $remote -> $Destination"
    & scp.exe @scpBaseArgs $remote $Destination
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download required file: $fileName"
    }
}

foreach ($fileName in $optionalFiles) {
    $remote = "${SshTarget}:$RemoteRunDir/$fileName"
    Write-Host "[Sera] Downloading optional $remote -> $Destination"
    & scp.exe @scpBaseArgs $remote $Destination
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[Sera] Optional file not copied: $fileName"
    }
}

$envPath = Join-Path $ProjectRoot ".env"
$activeModelLine = "SERA_ACTIVE_SYMBOLIC_MODEL=$ModelName"
$modelDirLine = "SERA_SYMBOLIC_MODEL_DIR=$Destination"
$backendLine = "SERA_GENERATOR_BACKEND=model"
$existing = @()
if (Test-Path -LiteralPath $envPath) {
    $existing = @(Get-Content -LiteralPath $envPath)
}
$filtered = @(
    $existing | Where-Object {
        $_ -notmatch "^SERA_ACTIVE_SYMBOLIC_MODEL=" -and
        $_ -notmatch "^SERA_SYMBOLIC_MODEL_DIR=" -and
        $_ -notmatch "^SERA_GENERATOR_BACKEND="
    }
)
($filtered + @($activeModelLine, $modelDirLine, $backendLine)) | Set-Content -LiteralPath $envPath -Encoding ASCII

Write-Host ""
Write-Host "[Sera] Model artifacts are ready in $Destination"
Write-Host "[Sera] Restart Sera, then check http://127.0.0.1:8000/model/status"
Write-Host "[Sera] Expected mode after PyTorch is installed: checkpoint"
