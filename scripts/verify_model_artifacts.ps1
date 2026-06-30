param(
    [string]$ModelDir = "",
    [switch]$WriteManifest
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($ModelDir)) {
    $ModelDir = Join-Path $ProjectRoot "models\sera_symbolic_small"
}
$ModelDir = (Resolve-Path -LiteralPath $ModelDir).Path

$required = @("model.pt", "vocab.json")
foreach ($fileName in $required) {
    $path = Join-Path $ModelDir $fileName
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required model artifact: $path"
    }
}

$manifestPath = Join-Path $ModelDir "sha256_manifest.txt"
if ($WriteManifest -or -not (Test-Path -LiteralPath $manifestPath)) {
    $lines = @()
    Get-ChildItem -LiteralPath $ModelDir -File |
        Where-Object { $_.Name -ne "sha256_manifest.txt" } |
        Sort-Object Name |
        ForEach-Object {
            $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            $lines += "$hash  $($_.Name)"
        }
    $lines | Set-Content -LiteralPath $manifestPath -Encoding ASCII
}

$errors = @()
foreach ($line in Get-Content -LiteralPath $manifestPath) {
    if ([string]::IsNullOrWhiteSpace($line)) {
        continue
    }
    $parts = $line -split "\s+", 2
    if ($parts.Count -lt 2) {
        continue
    }
    $expected = $parts[0].Trim().ToLowerInvariant()
    $fileName = $parts[1].Trim()
    $path = Join-Path $ModelDir $fileName
    if (-not (Test-Path -LiteralPath $path)) {
        $errors += "missing: $fileName"
        continue
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) {
        $errors += "hash mismatch: $fileName"
    }
}

if ($errors.Count -gt 0) {
    throw "Model artifact verification failed: $($errors -join '; ')"
}

Write-Host "[Sera] Model artifact verification passed: $ModelDir"
Write-Host "[Sera] Manifest: $manifestPath"
