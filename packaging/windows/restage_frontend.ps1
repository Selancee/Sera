param()

$ErrorActionPreference = "Stop"
$root = [System.IO.Path]::GetFullPath((Resolve-Path (Join-Path $PSScriptRoot "..\..")))
$desktopRoot = Join-Path $root "dist_desktop"
$source = Join-Path $root "frontend\dist"
$target = Join-Path $desktopRoot "frontend\dist"
$targetFull = [System.IO.Path]::GetFullPath($target)
$desktopFull = [System.IO.Path]::GetFullPath($desktopRoot)

if (!(Test-Path -LiteralPath (Join-Path $source "index.html") -PathType Leaf)) {
  throw "Frontend production build is missing: $source"
}
if (!$targetFull.StartsWith($desktopFull, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Refusing to reset a frontend staging path outside dist_desktop: $targetFull"
}
if (Test-Path -LiteralPath $targetFull) {
  Remove-Item -LiteralPath $targetFull -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $targetFull | Out-Null
Copy-Item -Recurse -Force (Join-Path $source "*") $targetFull

$previousElectronSkip = $env:ELECTRON_SKIP_BINARY_DOWNLOAD
$previousElectronCache = $env:ELECTRON_CACHE
$previousBuilderCache = $env:ELECTRON_BUILDER_CACHE
$env:ELECTRON_SKIP_BINARY_DOWNLOAD = "1"
$env:ELECTRON_CACHE = Join-Path $root ".cache\electron"
$env:ELECTRON_BUILDER_CACHE = Join-Path $root ".cache\electron-builder"
Push-Location (Join-Path $root "electron")
try {
  npm.cmd run dist
}
finally {
  Pop-Location
  $env:ELECTRON_SKIP_BINARY_DOWNLOAD = $previousElectronSkip
  $env:ELECTRON_CACHE = $previousElectronCache
  $env:ELECTRON_BUILDER_CACHE = $previousBuilderCache
}

$manifestPath = Join-Path $desktopRoot "release_manifest.json"
if (Test-Path -LiteralPath $manifestPath) {
  $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
  $manifest.generated_at = (Get-Date).ToUniversalTime().ToString("o")
  $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}

Write-Host "Restaged frontend and rebuilt Electron shell: $targetFull"
