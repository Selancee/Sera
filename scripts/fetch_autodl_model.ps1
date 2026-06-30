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
$optionalFiles = @(
    "training_metrics.json",
    "training_config_snapshot.json",
    "samples.json",
    "train.log",
    "baseline_score_eval.json",
    "run_status.json",
    "README.md",
    "model_card.json",
    "sha256_manifest.txt"
)

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

$manifestPath = Join-Path $Destination "sha256_manifest.txt"
if (Test-Path -LiteralPath $manifestPath) {
    $hashErrors = @()
    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $parts = $line -split "\s+", 2
        if ($parts.Count -lt 2) {
            continue
        }
        $expectedHash = $parts[0].Trim().ToLowerInvariant()
        $fileName = $parts[1].Trim()
        $localFile = Join-Path $Destination $fileName
        if (-not (Test-Path -LiteralPath $localFile)) {
            Write-Host "[Sera] Manifest file not copied locally, skipping hash: $fileName"
            continue
        }
        $actualHash = (Get-FileHash -LiteralPath $localFile -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $expectedHash) {
            $hashErrors += $fileName
        }
    }
    if ($hashErrors.Count -gt 0) {
        throw "SHA256 verification failed for: $($hashErrors -join ', ')"
    }
    Write-Host "[Sera] SHA256 manifest verification passed."
} else {
    Write-Host "[Sera] No sha256_manifest.txt found; run scripts\verify_model_artifacts.ps1 after copying if needed."
}

$envPath = Join-Path $ProjectRoot ".env"
$activeModelLine = "SERA_ACTIVE_SYMBOLIC_MODEL=$ModelName"
$modelDirLine = "SERA_SYMBOLIC_MODEL_DIR=$Destination"
$checkpointLine = "SERA_SYMBOLIC_MODEL_CHECKPOINT="
$backendLine = "SERA_GENERATOR_BACKEND=model"
$existing = @()
if (Test-Path -LiteralPath $envPath) {
    $existing = @(Get-Content -LiteralPath $envPath)
}
$filtered = @(
    $existing | Where-Object {
        $_ -notmatch "^SERA_ACTIVE_SYMBOLIC_MODEL=" -and
        $_ -notmatch "^SERA_SYMBOLIC_MODEL_DIR=" -and
        $_ -notmatch "^SERA_SYMBOLIC_MODEL_CHECKPOINT=" -and
        $_ -notmatch "^SERA_GENERATOR_BACKEND="
    }
)
($filtered + @($activeModelLine, $modelDirLine, $checkpointLine, $backendLine)) | Set-Content -LiteralPath $envPath -Encoding ASCII

Write-Host ""
Write-Host "[Sera] Model artifacts are ready in $Destination"
Write-Host "[Sera] Restart Sera, then check http://127.0.0.1:8000/model/status"
Write-Host "[Sera] Expected mode after PyTorch is installed: checkpoint"
